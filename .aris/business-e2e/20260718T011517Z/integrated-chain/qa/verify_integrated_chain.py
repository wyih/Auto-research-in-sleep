#!/usr/bin/env python3
"""Independently verify the integrated-chain pipeline transport artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import posixpath
import re
import statistics
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


RUN_ID = "20260718T011517Z-integrated-chain"
EXPECTED_WRDS_SHA256 = "bec638fbdc559866a61037383be74c728966877d32c9ee346f7f9504ed37ced3"
TOLERANCE = 1e-10
TRANSPORT_BOUNDARY = "Pipeline transport verification only; model outputs are reproduced without assessment"
PROHIBITED_DOCX_TEXT = (
    "estimated association",
    "statistically",
    "significance",
    "significant",
    "economic",
    "causal",
    "substantive",
)
EXPECTED_AUTHOR = os.environ.get("ARIS_OFFICE_AUTHOR")
NS_CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
NS_DC = "http://purl.org/dc/elements/1.1/"
NS_EP = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
IDENTITY_PART_RE = re.compile(
    r"^(?:word/(?:comments[^/]*\.xml|people\.xml|_rels/comments[^/]*\.xml\.rels)|docProps/custom\.xml)$",
    re.IGNORECASE,
)
IDENTITY_RELATIONSHIP_TERMS = ("comments", "people", "custom-properties")
COMMENT_TAGS = {"commentRangeStart", "commentRangeEnd", "commentReference"}
TRACKED_CHANGE_TAGS = {"ins", "del", "moveFrom", "moveTo"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def inverse(matrix: list[list[float]]) -> list[list[float]]:
    size = len(matrix)
    augmented = [
        [float(value) for value in row]
        + [1.0 if row_index == column_index else 0.0 for column_index in range(size)]
        for row_index, row in enumerate(matrix)
    ]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-15:
            raise AssertionError("Matrix is singular")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        pivot_value = augmented[column][column]
        augmented[column] = [value / pivot_value for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                value - factor * pivot_component
                for value, pivot_component in zip(augmented[row], augmented[column], strict=True)
            ]
    return [row[size:] for row in augmented]


def matmul(left: list[list[float]], right: list[list[float]]) -> list[list[float]]:
    right_transposed = list(zip(*right, strict=True))
    return [
        [sum(a * b for a, b in zip(row, column, strict=True)) for column in right_transposed]
        for row in left
    ]


def transpose(matrix: list[list[float]]) -> list[list[float]]:
    return [list(column) for column in zip(*matrix, strict=True)]


def quantile_type7(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def project_root(start: Path) -> Path:
    candidate = start.resolve()
    for parent in (candidate, *candidate.parents):
        if (parent / ".aris").is_dir() and (parent / "skills").is_dir():
            return parent
    raise RuntimeError("Could not locate project root")


def relative(project: Path, path: Path) -> str:
    return str(path.resolve().relative_to(project.resolve()))


def artifact(project: Path, path: Path, **facts: object) -> dict[str, object]:
    result: dict[str, object] = {
        "path": relative(project, path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }
    result.update(facts)
    return result


def _artifact_records(payload: object) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    if isinstance(payload, dict):
        if isinstance(payload.get("path"), str) and isinstance(payload.get("sha256"), str):
            records.append(payload)
        for value in payload.values():
            records.extend(_artifact_records(value))
    elif isinstance(payload, list):
        for value in payload:
            records.extend(_artifact_records(value))
    return records


def _record_path(project: Path, record: dict[str, object]) -> Path:
    raw_path = record["path"]
    assert isinstance(raw_path, str)
    candidate = Path(raw_path)
    resolved = candidate.resolve() if candidate.is_absolute() else (project / candidate).resolve()
    resolved.relative_to(project.resolve())
    if not resolved.is_file():
        raise AssertionError(f"Recorded artifact is missing: {raw_path}")
    return resolved


def canonical_json_bytes(payload: object) -> bytes:
    """Serialize a receipt deterministically; time must already be a frozen input fact."""
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def compare_receipt_bytes(path: Path, expected: bytes, label: str) -> None:
    """Read-only receipt check. It must never repair or refresh a mismatching file."""
    if not path.is_file():
        raise AssertionError(f"Missing {label} receipt: {path}")
    actual = path.read_bytes()
    if actual != expected:
        raise AssertionError(
            f"{label} receipt mismatch: actual sha256={sha256_bytes(actual)}, "
            f"expected sha256={sha256_bytes(expected)}; run with --write-receipts to regenerate"
        )


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        temp_path.write_bytes(payload)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def write_receipts(
    lineage_path: Path,
    lineage_bytes: bytes,
    root_path: Path,
    root_bytes: bytes,
) -> None:
    atomic_write_bytes(lineage_path, lineage_bytes)
    atomic_write_bytes(root_path, root_bytes)


def build_root_payload(
    *,
    project: Path,
    lineage_path: Path,
    lineage_bytes: bytes,
    lineage_report: dict[str, object],
    generated_at_utc: str,
) -> dict[str, object]:
    """Pure root receipt constructor. Existing receipt content is intentionally not an input."""
    return {
        "schema_version": "aris.business-e2e.integrated-chain-root.v2",
        "run_id": RUN_ID,
        "status": "pass",
        "verification_basis_generated_at_utc": generated_at_utc,
        "scope": "Real 10-row WRDS/Compustat cross-stage pipeline transport verification chain",
        "transport_boundary": TRANSPORT_BOUNDARY,
        "receipt_dag": "artifacts + verifier + acceptance + visual QA -> lineage -> root",
        "canonical_path": ".aris/business-e2e/20260718T011517Z/integrated-chain/INTEGRATED_CHAIN_RECEIPT.json",
        "lineage_receipt": {
            "path": relative(project, lineage_path),
            "sha256": sha256_bytes(lineage_bytes),
            "bytes": len(lineage_bytes),
            "status": lineage_report["status"],
            "check_summary": lineage_report["check_summary"],
        },
        "generation": {
            "pure_from_current_facts": True,
            "existing_root_receipt_used_as_input": False,
            "lineage_hash_source": "canonical expected lineage bytes",
            "self_hash_included": False,
        },
    }


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _relationship_target(part_name: str, target: str) -> str:
    rels_dir = posixpath.dirname(part_name)
    source_dir = posixpath.dirname(rels_dir)
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(source_dir, target))


def audit_docx_identity(
    path: Path,
    expected_author: str | None = EXPECTED_AUTHOR,
) -> dict[str, object]:
    """Independently inspect the DOCX package; no builder receipt fields are trusted."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        core = ET.fromstring(archive.read("docProps/core.xml"))
        app = ET.fromstring(archive.read("docProps/app.xml"))
        creator = core.findtext(f"{{{NS_DC}}}creator") or ""
        modified_by = core.findtext(f"{{{NS_CP}}}lastModifiedBy") or ""
        company = app.findtext(f"{{{NS_EP}}}Company") or ""
        manager = app.findtext(f"{{{NS_EP}}}Manager") or ""

        identity_parts = sorted(name for name in names if IDENTITY_PART_RE.match(name))
        comment_markers: list[str] = []
        tracked_changes: list[str] = []
        rsid_attributes: list[str] = []
        identity_attributes: list[str] = []
        identity_relationships: list[dict[str, str]] = []
        content_type_overrides: list[dict[str, str]] = []
        xml_parse_errors: list[str] = []

        for name in names:
            if not name.endswith((".xml", ".rels")):
                continue
            try:
                root = ET.fromstring(archive.read(name))
            except ET.ParseError:
                xml_parse_errors.append(name)
                continue
            for node in root.iter():
                node_name = _local_name(node.tag)
                if node_name in COMMENT_TAGS:
                    comment_markers.append(f"{name}:{node_name}")
                if node_name in TRACKED_CHANGE_TAGS and node.tag.startswith(f"{{{NS_W}}}"):
                    tracked_changes.append(f"{name}:{node_name}")
                for attribute, value in node.attrib.items():
                    attribute_name = _local_name(attribute)
                    if attribute_name.startswith("rsid"):
                        rsid_attributes.append(f"{name}:{attribute_name}")
                    if attribute_name in {"author", "initials", "userId", "providerId"} and value:
                        identity_attributes.append(f"{name}:{attribute_name}")
            if name.endswith(".rels"):
                for relationship in root:
                    rel_type = relationship.get("Type", "")
                    target = relationship.get("Target", "")
                    resolved = _relationship_target(name, target)
                    if (
                        any(term in rel_type.lower() for term in IDENTITY_RELATIONSHIP_TERMS)
                        or IDENTITY_PART_RE.match(resolved)
                    ):
                        identity_relationships.append(
                            {"part": name, "type": rel_type, "target": target, "resolved": resolved}
                        )
            if name == "[Content_Types].xml":
                for node in root:
                    part_name = node.get("PartName", "").lstrip("/")
                    content_type = node.get("ContentType", "")
                    if IDENTITY_PART_RE.match(part_name) or any(
                        term in content_type.lower() for term in IDENTITY_RELATIONSHIP_TERMS
                    ):
                        content_type_overrides.append(
                            {"part_name": part_name, "content_type": content_type}
                        )

    passed = (
        bool(creator)
        and creator == modified_by
        and (expected_author is None or creator == expected_author)
        and not company
        and not manager
        and not identity_parts
        and not comment_markers
        and not tracked_changes
        and not rsid_attributes
        and not identity_attributes
        and not identity_relationships
        and not content_type_overrides
        and not xml_parse_errors
    )
    return {
        "file": str(path),
        "creator": creator,
        "lastModifiedBy": modified_by,
        "company": company,
        "manager": manager,
        "identity_parts": identity_parts,
        "comment_markers": sorted(set(comment_markers)),
        "tracked_changes": sorted(set(tracked_changes)),
        "rsid_attributes": sorted(set(rsid_attributes)),
        "identity_attributes": sorted(set(identity_attributes)),
        "identity_relationships": identity_relationships,
        "content_type_overrides": content_type_overrides,
        "xml_parse_errors": xml_parse_errors,
        "passed": passed,
    }


def png_dimensions(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise AssertionError(f"Not a valid PNG with IHDR: {path}")
    return struct.unpack(">II", header[16:24])


def parse_pdf_info(path: Path) -> dict[str, object]:
    environment = os.environ.copy()
    environment["LC_ALL"] = "C"
    output = subprocess.run(
        ["pdfinfo", str(path)],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    ).stdout
    fields = {
        key.strip(): value.strip()
        for line in output.splitlines()
        if ":" in line
        for key, value in [line.split(":", 1)]
    }
    size_match = re.match(r"([0-9.]+) x ([0-9.]+) pts", fields.get("Page size", ""))
    if not size_match:
        raise AssertionError(f"Could not parse PDF page size: {fields.get('Page size')!r}")
    return {
        "pages": int(fields["Pages"]),
        "tagged": fields.get("Tagged", "").lower() == "yes",
        "page_size_points": [float(size_match.group(1)), float(size_match.group(2))],
        "page_size_text": fields["Page size"],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-receipts",
        action="store_true",
        help="Write deterministic lineage/root receipts after all independent checks pass; default is read-only check",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    script_path = Path(__file__).resolve()
    project = project_root(script_path)
    run_root = project / ".aris/business-e2e/20260718T011517Z"
    chain = run_root / "integrated-chain"

    wrds_source = run_root / "wrds/sas/landed/comp_funda_2020_smoke_v1_sas.csv"
    wrds_receipt_path = run_root / "wrds/receipts/p1-wrds-sas-cloud.json"
    processed_path = chain / "processed/wrds_compustat_2020_smoke_derived.csv"
    coefficient_path = chain / "tables/roa_ols_conventional_coefficients.csv"
    descriptive_path = chain / "tables/wrds_compustat_descriptives.csv"
    checks_path = chain / "tables/engineering_checks.csv"
    analysis_script = chain / "analysis/run_integrated_chain_smoke.R"
    analysis_log = chain / "logs/analysis_log.txt"
    figure_path = chain / "figures/roa_vs_asset_turnover.png"
    build_spec = chain / "results_docx/build_spec.json"
    docx_path = chain / "results_docx/integrated_chain_results.docx"
    docx_receipt_path = chain / "results_docx/RESULTS_DOCX_RECEIPT.json"
    docx_manifest_path = chain / "results_docx/RESULTS_DOCX_MANIFEST.md"
    a11y_path = chain / "results_docx/a11y_report.json"
    extracted_descriptives_path = chain / "results_docx/qa/docx_table_0_descriptives.csv"
    extracted_coefficients_path = chain / "results_docx/qa/docx_table_1_coefficients.csv"
    rendered_pdf = chain / "results_docx/rendered/integrated_chain_results.pdf"
    rendered_pages = sorted(
        (chain / "results_docx/rendered").glob("page-*.png"),
        key=lambda path: int(re.search(r"page-(\d+)\.png\Z", path.name).group(1)),  # type: ignore[union-attr]
    )
    visual_receipt_path = chain / "results_docx/VISUAL_QA_RECEIPT.json"
    acceptance_path = chain / "INTEGRATED_CHAIN_ACCEPTANCE.md"
    cnrds_receipt_path = run_root / "cn-data/receipts/p4-cnrds-codex.json"
    csmar_receipt_path = run_root / "cn-data/receipts/p4-csmar-codex.json"
    lineage_path = chain / "lineage/INTEGRATED_CHAIN_RECEIPT.json"
    root_receipt_path = chain / "INTEGRATED_CHAIN_RECEIPT.json"

    required = [
        wrds_source,
        wrds_receipt_path,
        processed_path,
        coefficient_path,
        descriptive_path,
        checks_path,
        analysis_script,
        analysis_log,
        figure_path,
        build_spec,
        docx_path,
        docx_receipt_path,
        docx_manifest_path,
        a11y_path,
        extracted_descriptives_path,
        extracted_coefficients_path,
        rendered_pdf,
        visual_receipt_path,
        acceptance_path,
        cnrds_receipt_path,
        csmar_receipt_path,
    ]
    if not args.write_receipts:
        required.extend([lineage_path, root_receipt_path])
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise AssertionError(f"Missing required artifacts: {missing}")

    checks: list[dict[str, object]] = []

    def check(name: str, observed: object, expected: object, passed: bool) -> None:
        checks.append(
            {"check": name, "observed": observed, "expected": expected, "passed": bool(passed)}
        )
        if not passed:
            raise AssertionError(f"{name}: observed={observed!r}, expected={expected!r}")

    wrds_receipt = json.loads(wrds_receipt_path.read_text(encoding="utf-8"))
    wrds_transfer = next(
        item
        for item in wrds_receipt["transfer"]["files"]
        if item["path"].endswith("comp_funda_2020_smoke_v1_sas.csv")
    )
    source_digest = sha256(wrds_source)
    check("wrds_source_sha256_expected", source_digest, EXPECTED_WRDS_SHA256, source_digest == EXPECTED_WRDS_SHA256)
    check("wrds_source_sha256_matches_receipt", source_digest, wrds_transfer["sha256"], source_digest == wrds_transfer["sha256"])

    source_rows = read_csv(wrds_source)
    processed_rows = read_csv(processed_path)
    coefficient_rows = read_csv(coefficient_path)
    descriptive_rows = read_csv(descriptive_path)
    engineering_checks = read_csv(checks_path)
    build_spec_payload = json.loads(build_spec.read_text(encoding="utf-8"))
    check(
        "build_spec_narrative_mode",
        build_spec_payload.get("narrative_mode"),
        "transport-only",
        build_spec_payload.get("narrative_mode") == "transport-only",
    )
    check(
        "build_spec_transport_figure_opt_in",
        build_spec_payload.get("figures", [{}])[0].get("transport_figure"),
        True,
        build_spec_payload.get("figures", [{}])[0].get("transport_figure") is True,
    )
    check("wrds_source_row_count", len(source_rows), 10, len(source_rows) == 10)
    check("processed_row_count", len(processed_rows), 10, len(processed_rows) == 10)
    check("coefficient_row_count", len(coefficient_rows), 3, len(coefficient_rows) == 3)
    check("descriptive_row_count", len(descriptive_rows), 6, len(descriptive_rows) == 6)
    check(
        "engineering_checks_all_pass",
        [row["status"] for row in engineering_checks],
        ["PASS"] * len(engineering_checks),
        bool(engineering_checks) and all(row["status"] == "PASS" for row in engineering_checks),
    )

    for source, processed in zip(source_rows, processed_rows, strict=True):
        check(
            f"source_identity_{source['gvkey']}",
            [processed[key] for key in ("gvkey", "datadate", "fyear")],
            [source[key] for key in ("gvkey", "datadate", "fyear")],
            all(processed[key] == source[key] for key in ("gvkey", "datadate", "fyear")),
        )
        at = float(source["at"])
        sale = float(source["sale"])
        ni = float(source["ni"])
        expected_values = {
            "roa": ni / at,
            "asset_turnover": sale / at,
            "log_assets": math.log(at),
        }
        for key, expected in expected_values.items():
            observed = float(processed[key])
            check(
                f"derived_{key}_{source['gvkey']}",
                observed,
                expected,
                math.isfinite(observed) and math.isclose(observed, expected, rel_tol=0, abs_tol=1e-12),
            )

    x = [
        [1.0, float(row["asset_turnover"]), float(row["log_assets"])]
        for row in processed_rows
    ]
    y = [[float(row["roa"])] for row in processed_rows]
    xt = transpose(x)
    xtx = matmul(xt, x)
    xtx_inverse = inverse(xtx)
    beta = [row[0] for row in matmul(matmul(xtx_inverse, xt), y)]
    residuals = [
        response[0] - sum(value * coefficient for value, coefficient in zip(row, beta, strict=True))
        for row, response in zip(x, y, strict=True)
    ]
    residual_df = len(y) - len(beta)
    sigma_squared = sum(value * value for value in residuals) / residual_df
    standard_errors = [math.sqrt(sigma_squared * xtx_inverse[index][index]) for index in range(3)]
    terms = ["(Intercept)", "asset_turnover", "log_assets"]
    by_term = {row["term"]: row for row in coefficient_rows}
    for index, term in enumerate(terms):
        observed_beta = float(by_term[term]["estimate"])
        observed_se = float(by_term[term]["std.error"])
        check(
            f"ols_estimate_{term}",
            observed_beta,
            beta[index],
            math.isclose(observed_beta, beta[index], rel_tol=0, abs_tol=TOLERANCE),
        )
        check(
            f"conventional_se_{term}",
            observed_se,
            standard_errors[index],
            math.isclose(observed_se, standard_errors[index], rel_tol=0, abs_tol=TOLERANCE),
        )
        p_value = float(by_term[term]["p.value"])
        check(f"finite_p_value_{term}", p_value, "0 <= p <= 1", math.isfinite(p_value) and 0 <= p_value <= 1)
    check("residual_degrees_of_freedom", residual_df, 7, residual_df == 7)

    descriptive_by_variable = {row["variable"]: row for row in descriptive_rows}
    for variable in ("roa", "asset_turnover", "log_assets", "at", "sale", "ni"):
        values = [float(row[variable]) for row in processed_rows]
        expected_statistics = {
            "n": len(values),
            "mean": statistics.mean(values),
            "sd": statistics.stdev(values),
            "p25": quantile_type7(values, 0.25),
            "p50": quantile_type7(values, 0.50),
            "p75": quantile_type7(values, 0.75),
            "min": min(values),
            "max": max(values),
        }
        row = descriptive_by_variable[variable]
        for field, expected in expected_statistics.items():
            observed = float(row[field])
            check(
                f"descriptive_{variable}_{field}",
                observed,
                expected,
                math.isclose(observed, expected, rel_tol=0, abs_tol=TOLERANCE),
            )

    extracted_descriptives = read_csv(extracted_descriptives_path)
    extracted_coefficients = list(csv.reader(extracted_coefficients_path.open(encoding="utf-8-sig", newline="")))
    expected_descriptive_display = {
        "roa": ["10", "-0.19", "0.74", "-0.04", "0.02", "0.05", "-2.27", "0.38"],
        "asset_turnover": ["10", "0.68", "0.76", "0.12", "0.38", "0.99", "0.00", "2.04"],
        "log_assets": ["10", "7.15", "3.56", "6.06", "7.26", "9.76", "-0.37", "11.19"],
        "at": ["10", "16941.15", "27417.87", "430.67", "1428.55", "17778.49", "0.69", "72548.00"],
        "sale": ["10", "6111.22", "11292.96", "141.01", "1347.79", "3311.39", "0.00", "34608.00"],
        "ni": ["10", "-377.63", "3301.04", "-46.49", "5.41", "142.78", "-8885.00", "4495.00"],
    }
    for row in extracted_descriptives:
        label = row["Variable ID"]
        observed = [row[key] for key in ("N", "Mean", "SD", "P25", "Median", "P75", "Min", "Max")]
        expected = expected_descriptive_display[label]
        check(f"docx_descriptive_display_{label}", observed, expected, observed == expected)

    coefficient_pairs = {row[0]: row[1] for row in extracted_coefficients[1:] if len(row) >= 2 and row[0]}
    check(
        "docx_model_column_label",
        extracted_coefficients[0],
        ["Variable", "m1"],
        extracted_coefficients[0] == ["Variable", "m1"],
    )
    expected_coefficient_display = {
        "(Intercept)": "-1.5463**",
        "asset_turnover": "0.3775",
        "log_assets": "0.1541**",
        "Observations": "10",
        "Adjusted R-squared": "0.492",
    }
    for label, expected in expected_coefficient_display.items():
        observed = coefficient_pairs.get(label)
        check(f"docx_coefficient_display_{label}", observed, expected, observed == expected)
    observed_se_rows = [row[1] for row in extracted_coefficients if row and row[0] == ""]
    expected_se_rows = ["(0.4475)", "(0.2357)", "(0.0501)"]
    check("docx_conventional_se_display", observed_se_rows, expected_se_rows, observed_se_rows == expected_se_rows)

    docx_receipt = json.loads(docx_receipt_path.read_text(encoding="utf-8"))
    docx_digest = sha256(docx_path)
    check("docx_sha256_matches_receipt", docx_digest, docx_receipt["document"]["sha256"], docx_digest == docx_receipt["document"]["sha256"])
    check(
        "docx_builder_version",
        docx_receipt.get("builder_version"),
        "1.2.0",
        docx_receipt.get("builder_version") == "1.2.0",
    )
    check(
        "docx_narrative_mode",
        docx_receipt.get("narrative_mode"),
        "transport-only",
        docx_receipt.get("narrative_mode") == "transport-only",
    )
    narrative_text = " ".join(
        str(claim.get("text", "")) for claim in docx_receipt.get("narrative_claims", [])
    ).lower()
    for phrase in PROHIBITED_DOCX_TEXT:
        check(
            f"generated_prose_transport_language_{phrase.replace(' ', '_')}",
            phrase in narrative_text,
            False,
            phrase not in narrative_text,
        )
    check("docx_table_count", docx_receipt["document"]["tables"], 2, docx_receipt["document"]["tables"] == 2)
    check("docx_figure_count", docx_receipt["document"]["figures"], 1, docx_receipt["document"]["figures"] == 1)
    transport_policy = docx_receipt.get("transport_policy", {})
    check(
        "docx_transport_structured_output_only",
        transport_policy.get("structured_output_only"),
        True,
        transport_policy.get("structured_output_only") is True,
    )
    check(
        "docx_transport_figure_semantics_not_audited",
        transport_policy.get("embedded_image_pixels_semantically_audited"),
        False,
        transport_policy.get("embedded_image_pixels_semantically_audited") is False,
    )
    check(
        "docx_receipt_fixed_table_titles",
        [table["title"] for table in docx_receipt["tables"]],
        ["Coefficient output C1", "Descriptive output D1"],
        [table["title"] for table in docx_receipt["tables"]]
        == ["Coefficient output C1", "Descriptive output D1"],
    )
    check(
        "docx_receipt_fixed_figure_wrapper",
        [
            docx_receipt["figures"][0]["title"],
            docx_receipt["figures"][0]["alt_text"],
            docx_receipt["figures"][0]["embedded"],
            docx_receipt["figures"][0]["image_pixels_semantically_audited"],
        ],
        [
            "Transport figure F1",
            "Transported figure F1. Image pixels are not semantically audited.",
            True,
            False,
        ],
        docx_receipt["figures"][0]["title"] == "Transport figure F1"
        and docx_receipt["figures"][0]["alt_text"]
        == "Transported figure F1. Image pixels are not semantically audited."
        and docx_receipt["figures"][0]["embedded"] is True
        and docx_receipt["figures"][0]["image_pixels_semantically_audited"] is False,
    )

    metadata = audit_docx_identity(docx_path)
    expected_author = EXPECTED_AUTHOR or metadata["creator"]
    for field, expected in (
        ("creator", expected_author),
        ("lastModifiedBy", expected_author),
        ("company", ""),
        ("manager", ""),
    ):
        observed = metadata[field]
        check(f"docx_independent_metadata_{field}", observed, expected, observed == expected)
    for field in (
        "identity_parts",
        "comment_markers",
        "tracked_changes",
        "rsid_attributes",
        "identity_attributes",
        "identity_relationships",
        "content_type_overrides",
        "xml_parse_errors",
    ):
        observed = metadata[field]
        check(f"docx_independent_metadata_{field}_empty", observed, [], observed == [])
    check("docx_independent_metadata_passed", metadata["passed"], True, metadata["passed"] is True)
    builder_metadata = docx_receipt.get("metadata", {})
    for field in ("creator", "lastModifiedBy", "company", "manager"):
        check(
            f"builder_metadata_corrobates_actual_{field}",
            builder_metadata.get(field),
            metadata[field],
            builder_metadata.get(field) == metadata[field],
        )

    a11y = json.loads(a11y_path.read_text(encoding="utf-8"))
    check("a11y_high", a11y["counts"]["high"], 0, a11y["counts"]["high"] == 0)
    check("a11y_medium", a11y["counts"]["medium"], 0, a11y["counts"]["medium"] == 0)
    check("a11y_low", a11y["counts"]["low"], 0, a11y["counts"]["low"] == 0)

    namespaces = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    }
    with zipfile.ZipFile(docx_path) as archive:
        document_xml_bytes = archive.read("word/document.xml")
        document_xml = ET.fromstring(document_xml_bytes)
        document_text = "".join(document_xml.itertext()).lower()
        for phrase in PROHIBITED_DOCX_TEXT:
            check(
                f"docx_transport_language_{phrase.replace(' ', '_')}",
                phrase in document_text,
                False,
                phrase not in document_text,
            )
        tables = document_xml.findall(".//w:tbl", namespaces)
        check("ooxml_table_count", len(tables), 2, len(tables) == 2)
        header_markers = [table.find("./w:tr/w:trPr/w:tblHeader", namespaces) is not None for table in tables]
        check("ooxml_table_headers", header_markers, [True, True], header_markers == [True, True])
        descriptions = [
            node.attrib.get("descr", "").strip()
            for node in document_xml.findall(".//wp:docPr", namespaces)
        ]
        check("ooxml_image_alt_count", len(descriptions), 1, len(descriptions) == 1)
        expected_alt = "Transported figure F1. Image pixels are not semantically audited."
        check("ooxml_image_alt_fixed", descriptions, [expected_alt], descriptions == [expected_alt])
        all_xml_text = b"\n".join(
            archive.read(name)
            for name in archive.namelist()
            if name.endswith((".xml", ".rels"))
        ).decode("utf-8", errors="replace")

    effective_artifact_text = "\n".join(
        (
            all_xml_text,
            docx_manifest_path.read_text(encoding="utf-8"),
            docx_receipt_path.read_text(encoding="utf-8"),
        )
    )
    ignored_spec_values = [
        build_spec_payload["title"],
        build_spec_payload["subtitle"],
        build_spec_payload["coefficient_tables"][0]["title"],
        build_spec_payload["coefficient_tables"][0]["note"],
        build_spec_payload["descriptive_tables"][0]["title"],
        build_spec_payload["descriptive_tables"][0]["note"],
        build_spec_payload["figures"][0]["title"],
        build_spec_payload["figures"][0]["alt_text"],
        build_spec_payload["figures"][0]["note"],
    ]
    ignored_csv_values = [
        "(1) OLS transport check",
        "ROA (ni/at)",
        "None; conventional homoskedastic OLS SE",
        "Asset turnover + log assets",
        "Conventional OLS (homoskedastic)",
        "Real WRDS/Compustat 2020 landed smoke extract; n=10",
        "Return on assets (ni/at)",
        "Asset turnover (sale/at)",
        "Log total assets (ln(at))",
        "Total assets (at)",
        "Sales (sale)",
        "Net income (ni)",
        "Real WRDS/Compustat landed smoke extract; unfiltered n=10",
    ]
    for index, ignored_value in enumerate(ignored_spec_values + ignored_csv_values, 1):
        check(
            f"transport_ignored_free_text_{index}",
            ignored_value in effective_artifact_text,
            False,
            ignored_value not in effective_artifact_text,
        )

    pdf_facts = parse_pdf_info(rendered_pdf)
    pdf_pages = int(pdf_facts["pages"])
    check("rendered_pdf_page_count", pdf_pages, 3, pdf_pages == 3)
    check("rendered_pdf_tagged", pdf_facts["tagged"], True, pdf_facts["tagged"] is True)
    check(
        "rendered_pdf_letter_points",
        pdf_facts["page_size_points"],
        [612.0, 792.0],
        pdf_facts["page_size_points"] == [612.0, 792.0],
    )
    check("rendered_png_page_count", len(rendered_pages), pdf_pages, len(rendered_pages) == pdf_pages)
    rendered_dimensions = [png_dimensions(path) for path in rendered_pages]
    check(
        "rendered_png_dimensions",
        rendered_dimensions,
        [(1547, 2002)] * pdf_pages,
        rendered_dimensions == [(1547, 2002)] * pdf_pages,
    )

    visual_receipt = json.loads(visual_receipt_path.read_text(encoding="utf-8"))
    for field, expected in (
        ("schema_version", "aris.business-e2e.visual-qa.v1"),
        ("run_id", RUN_ID),
        ("status", "pass"),
        ("all_pages_reviewed", True),
        ("figure_pixels_semantically_audited", False),
    ):
        observed = visual_receipt.get(field)
        check(f"visual_receipt_{field}", observed, expected, observed == expected)
    visual_document = visual_receipt["document"]
    expected_visual_document = artifact(project, docx_path)
    for field in ("path", "sha256", "bytes"):
        check(
            f"visual_receipt_document_{field}",
            visual_document.get(field),
            expected_visual_document[field],
            visual_document.get(field) == expected_visual_document[field],
        )
    visual_pdf = visual_receipt["pdf"]
    expected_visual_pdf = artifact(
        project,
        rendered_pdf,
        pages=pdf_pages,
        tagged=True,
        page_size_points=[612.0, 792.0],
        page_size_name="Letter",
    )
    for field in ("path", "sha256", "bytes", "pages", "tagged", "page_size_points", "page_size_name"):
        check(
            f"visual_receipt_pdf_{field}",
            visual_pdf.get(field),
            expected_visual_pdf[field],
            visual_pdf.get(field) == expected_visual_pdf[field],
        )
    visual_pages = visual_receipt["pages"]
    check("visual_receipt_page_count", len(visual_pages), pdf_pages, len(visual_pages) == pdf_pages)
    expected_layout_checks = {
        "clipping": False,
        "overlap": False,
        "missing_glyphs": False,
        "table_overflow": False,
        "broken_page_furniture": False,
    }
    for page_number, (page_path, dimensions, recorded) in enumerate(
        zip(rendered_pages, rendered_dimensions, visual_pages, strict=True),
        1,
    ):
        expected_page = artifact(
            project,
            page_path,
            page_number=page_number,
            width_px=dimensions[0],
            height_px=dimensions[1],
            verdict="pass",
        )
        for field in ("path", "sha256", "bytes", "page_number", "width_px", "height_px", "verdict"):
            check(
                f"visual_receipt_page_{page_number}_{field}",
                recorded.get(field),
                expected_page[field],
                recorded.get(field) == expected_page[field],
            )
        check(
            f"visual_receipt_page_{page_number}_layout_checks",
            recorded.get("checks"),
            expected_layout_checks,
            recorded.get("checks") == expected_layout_checks,
        )

    china_lanes: list[dict[str, object]] = []
    for lane_name, receipt_path in (("cnrds", cnrds_receipt_path), ("csmar", csmar_receipt_path)):
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        artifacts = []
        for item in receipt["artifacts"]:
            item_path = project / item["path"]
            actual_digest = sha256(item_path)
            check(
                f"{lane_name}_artifact_hash_{item_path.name}",
                actual_digest,
                item["sha256"],
                actual_digest == item["sha256"],
            )
            artifact_facts = {
                key: value for key, value in item.items() if key not in {"path", "sha256", "size_bytes"}
            }
            artifacts.append(artifact(project, item_path, **artifact_facts))
        data_rows = next(item.get("data_rows") for item in receipt["artifacts"] if "data_rows" in item)
        expected_rows = 2 if lane_name == "cnrds" else 1
        check(f"{lane_name}_receipt_data_rows", data_rows, expected_rows, data_rows == expected_rows)
        china_lanes.append(
            {
                "lane": lane_name,
                "relationship_to_wrds_model": "lineage-only gap-fill; zero rows merged",
                "receipt": artifact(project, receipt_path),
                "status": receipt["status"],
                "adapter": receipt["adapter"],
                "query": receipt["query"],
                "data_rows": data_rows,
                "artifacts": artifacts,
            }
        )

    acceptance_text = acceptance_path.read_text(encoding="utf-8")
    check(
        "acceptance_excludes_lineage_self_hash_row",
        "| Lineage receipt |" in acceptance_text,
        False,
        "| Lineage receipt |" not in acceptance_text,
    )
    check(
        "acceptance_excludes_root_self_hash_row",
        "| Root receipt |" in acceptance_text,
        False,
        "| Root receipt |" not in acceptance_text,
    )
    check(
        "acceptance_links_visual_receipt",
        "VISUAL_QA_RECEIPT.json" in acceptance_text,
        True,
        "VISUAL_QA_RECEIPT.json" in acceptance_text,
    )

    generated_at_utc = str(docx_receipt["generated_at_utc"])
    report = {
        "schema_version": "aris.business-e2e.integrated-chain-lineage.v2",
        "run_id": RUN_ID,
        "generated_at_utc": generated_at_utc,
        "status": "passed",
        "scope": "offline cross-stage pipeline transport verification using real landed data",
        "transport_boundary": TRANSPORT_BOUNDARY,
        "sample_separation": {
            "wrds_model_rows": 10,
            "cnrds_rows_merged": 0,
            "csmar_rows_merged": 0,
            "passed": True,
        },
        "wrds_lane": {
            "source": artifact(project, wrds_source, rows=10, columns=6),
            "source_receipt": artifact(project, wrds_receipt_path),
            "transformations": ["roa=ni/at", "asset_turnover=sale/at", "log_assets=ln(at)"],
            "processed": artifact(project, processed_path, rows=10, columns=9),
            "model": {
                "formula": "roa ~ asset_turnover + log_assets",
                "nobs": 10,
                "parameters": 3,
                "residual_df": 7,
                "matrix_rank": 3,
                "standard_errors": "conventional homoskedastic OLS",
            },
            "artifacts": [
                artifact(project, analysis_script),
                artifact(project, analysis_log),
                artifact(project, coefficient_path, rows=3),
                artifact(project, descriptive_path, rows=6),
                artifact(project, checks_path, rows=len(engineering_checks)),
                artifact(project, figure_path),
            ],
        },
        "results_docx": {
            "document": artifact(
                project,
                docx_path,
                tables=2,
                figures=1,
                narrative_mode="transport-only",
            ),
            "build_spec": artifact(project, build_spec),
            "manifest": artifact(project, docx_manifest_path),
            "receipt": artifact(project, docx_receipt_path),
            "a11y_report": artifact(project, a11y_path, high=0, medium=0, low=0),
            "extracted_tables": [
                artifact(project, extracted_descriptives_path, table_index=0),
                artifact(project, extracted_coefficients_path, table_index=1),
            ],
            "render": {
                "pdf": artifact(
                    project,
                    rendered_pdf,
                    pages=pdf_pages,
                    tagged=pdf_facts["tagged"],
                    page_size_points=pdf_facts["page_size_points"],
                    page_size_name="Letter",
                ),
                "pages": [
                    artifact(
                        project,
                        path,
                        page_number=index,
                        width_px=rendered_dimensions[index - 1][0],
                        height_px=rendered_dimensions[index - 1][1],
                        visual_verdict=visual_pages[index - 1]["verdict"],
                    )
                    for index, path in enumerate(rendered_pages, 1)
                ],
                "all_pages_rasterized": True,
            },
            "metadata_independent_audit": {
                key: value for key, value in metadata.items() if key != "file"
            },
            "generated_prose_audit": {
                "prohibited_phrases": list(PROHIBITED_DOCX_TEXT),
                "matches": 0,
                "passed": True,
            },
        },
        "china_gap_fill_lanes": china_lanes,
        "verification_artifacts": {
            "verifier": artifact(project, script_path),
            "acceptance": artifact(project, acceptance_path),
            "visual_qa_receipt": artifact(
                project,
                visual_receipt_path,
                status=visual_receipt["status"],
                pages=len(visual_pages),
                figure_pixels_semantically_audited=visual_receipt[
                    "figure_pixels_semantically_audited"
                ],
            ),
        },
        "receipt_dag": {
            "lineage_inputs": [
                "data and analysis artifacts",
                "DOCX and independent OOXML audit",
                "rendered PDF and PNGs",
                "visual QA receipt",
                "acceptance report",
                "verifier source",
            ],
            "lineage_excludes": ["lineage receipt", "root receipt"],
            "root_input": "canonical expected lineage bytes",
            "self_hash_cycle": False,
        },
        "checks": checks,
        "check_summary": {"total": len(checks), "passed": len(checks), "failed": 0},
    }

    lineage_bytes = canonical_json_bytes(report)
    root_payload = build_root_payload(
        project=project,
        lineage_path=lineage_path,
        lineage_bytes=lineage_bytes,
        lineage_report=report,
        generated_at_utc=generated_at_utc,
    )
    root_bytes = canonical_json_bytes(root_payload)
    if args.write_receipts:
        write_receipts(lineage_path, lineage_bytes, root_receipt_path, root_bytes)
    else:
        compare_receipt_bytes(lineage_path, lineage_bytes, "lineage")
        compare_receipt_bytes(root_receipt_path, root_bytes, "root")

    artifact_records = _artifact_records(report)
    artifact_paths = {record["path"] for record in artifact_records}
    print(
        json.dumps(
            {
                "status": report["status"],
                "mode": "write" if args.write_receipts else "check",
                "checks": report["check_summary"],
                "receipt": relative(project, lineage_path),
                "receipt_sha256": sha256_bytes(lineage_bytes),
                "receipt_bytes": len(lineage_bytes),
                "root_receipt": relative(project, root_receipt_path),
                "root_receipt_sha256": sha256_bytes(root_bytes),
                "root_receipt_bytes": len(root_bytes),
                "lineage_artifact_records": len(artifact_records),
                "lineage_unique_artifacts": len(artifact_paths),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise
