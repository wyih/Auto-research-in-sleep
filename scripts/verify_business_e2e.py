#!/usr/bin/env python3
"""Deterministically verify a business-research E2E evidence run.

The verifier is read-only.  It trusts neither prose summaries nor a receipt's
``status`` field alone: accepted artifacts are re-hashed and, where recorded,
their dimensions/page counts are checked. Browser evidence is accepted only
from the trusted host adapters: Codex native Chrome or Kimi WebBridge.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import shutil
import struct
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Sequence
from xml.etree import ElementTree as ET


Status = Literal["PASS", "FAIL", "INCOMPLETE"]
PASS_WORDS = {"pass", "passed", "verified", "complete", "completed"}
RUNTIME_INVOCATION_SCHEMA = "aris.business-e2e.runtime-invocation.v1"
P3_SYNTHESIS_SCHEMA = "aris.business-e2e.literature-synthesis.v2"
P3_PDF_INSPECTION_SCHEMA = "aris.method-harvest.pdf-inspection.v2"
P3_RENDER_EVIDENCE_SCHEMA = "aris.method-harvest.render-evidence.v1"
P3_ARTIFACT_IDENTITY_FIELDS = (
    "work_id",
    "artifact_id",
    "parent_artifact_id",
    "artifact_role",
    "version_identity",
    "doi_or_source_id",
)
P3_FULLTEXT_MANIFEST_HEADER = (
    "work_id",
    "artifact_id",
    "parent_artifact_id",
    "artifact_role",
    "version_identity",
    "title",
    "doi_or_source_id",
    "identity_evidence",
    "channel",
    "runtime",
    "adapter",
    "local_path_or_gap",
    "size_bytes",
    "pages",
    "sha256",
    "acquired_at",
    "provenance_receipt",
    "browser_receipt",
    "status",
    "blocker",
    "notes",
)
P3_BROWSER_SITES = ("cnki", "ssrn", "sciencedirect", "wiley")
P4_BROWSER_SITES = ("cnrds", "csmar")
RUNTIMES = ("codex", "kimi")
# Codex evidence keeps the legacy root layout (<evidence-root>/<run-id>); other
# runtimes own a subdirectory of the evidence root (<evidence-root>/<runtime>/<run-id>).
RUNTIME_EVIDENCE_SUBDIRS: Mapping[str, str] = {"codex": "", "kimi": "kimi"}
RUNTIME_SUBDIR_NAMES = frozenset(name for name in RUNTIME_EVIDENCE_SUBDIRS.values() if name)
P4_EXTRACT_VERIFIER_SCHEMA = "aris.cn-data-bridge.extract-verification.v1"
CN_EXTRACT_VERIFIER = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "cn-data-bridge"
    / "scripts"
    / "verify_cn_extract.py"
)
P3_METHOD_CARD_TOKENS = (
    "## Bibliographic",
    "## Fulltext",
    "## PDF Processing",
    "### Construct Map",
    "## Sample",
    "## Identification",
    "## Variables",
    "### Factor / Index Construction Audit",
    "### Questionnaire / Scale Provenance Audit",
    "### Mediation Evidence Audit",
    "## Numeric Consistency Audit",
    "## Limitations And Claim Ceiling",
    "## Handoff",
)
P3_METHOD_CARD_FIELDS = (
    "fulltext_status",
    "local_path",
    "content_hash",
    "size_bytes",
    "pages",
    "source_depth",
    "pdf_processing_receipt",
    "work_id",
    "artifact_id",
    "parent_artifact_id",
    "artifact_role",
    "version_identity",
    "doi_or_source_id",
    "unit_of_observation",
    "response_n",
    "unique_entity_n",
    "estimand_unit",
    "cluster_unit",
    "scale_provenance_status",
    "numeric_audit_status",
    "safe_claim",
    "unsafe_claim",
)
P3_OUTPUT_CONTRACTS: Mapping[str, tuple[str, ...]] = {
    "method_card_index": (
        "# METHOD_CARD_INDEX",
        "## Corpus Gate",
        "numeric_audit_status",
        "index_reproducibility",
        "ready_for_design",
    ),
    "evidence_matrix": (
        "# LITERATURE_EVIDENCE_MATRIX",
        "## Corpus And Source Gate",
        "## Exact Variable Construction",
        "#### Observation And Dependence Audit",
        "#### Factor / Index Reproducibility Audit",
        "#### Questionnaire / Scale Provenance Audit",
        "#### Numeric Consistency Audit",
        "#### Mediation Evidence Audit",
        "## Agreement And Conflict Classification",
        "## Unresolved Fulltext Fields",
        "## Evidence-Matrix Bottom Line",
    ),
    "literature_review": (
        "# BUSINESS_LIT_REVIEW",
        "## Conclusion",
        "## Required Handoff Fields",
        "## 2. How Variable Calculation Changes The Question",
        "## 3. Observation Units, Dependence, And Identification",
        "## 4. Findings, Nulls, And Apparent Contradictions",
        "## 5. Does The Corpus Establish A Mediation Mechanism?",
        "## 6. Claim Ceilings And Safe Language",
        "## Source Grounding",
    ),
    "acceptance_report": (
        "# P3 V2 OFFLINE ACCEPTANCE REPORT",
        "## Source Gate",
        "## Artifact Inventory",
        "## Contract Gates",
        "## Material Paper-Level Status",
        "## Real Source-Evidence Spot Checks",
        "## Remaining Evidence Gaps",
    ),
    "pdf_visual_checks": (
        "# P3 PDF Visual Checks",
        "visually checked source pages",
        "rendered source pages",
        "OCR was not used",
    ),
}


@dataclass(frozen=True)
class Check:
    name: str
    status: Status
    summary: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "summary": self.summary}


@dataclass(frozen=True)
class Gate:
    name: str
    status: Status
    summary: str
    checks: tuple[Check, ...]

    @classmethod
    def from_checks(cls, name: str, checks: Iterable[Check]) -> "Gate":
        materialized = tuple(checks)
        status = combine_status(check.status for check in materialized)
        problem = next((c for c in materialized if c.status == "FAIL"), None)
        if problem is None:
            problem = next((c for c in materialized if c.status == "INCOMPLETE"), None)
        summary = problem.summary if problem else f"{len(materialized)} evidence checks passed"
        return cls(name=name, status=status, summary=summary, checks=materialized)

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "summary": self.summary,
            "checks": [check.as_dict() for check in self.checks],
        }


@dataclass(frozen=True)
class Report:
    run_id: str
    run_path: str
    status: Status
    shared: Mapping[str, Gate]
    runtimes: Mapping[str, Mapping[str, object]]

    def as_dict(self) -> dict[str, object]:
        runtime_payload: dict[str, object] = {}
        for runtime, payload in self.runtimes.items():
            stages = payload["stages"]
            browser = payload["browser"]
            assert isinstance(stages, Mapping) and isinstance(browser, Mapping)
            runtime_payload[runtime] = {
                "status": payload["status"],
                "stages": {name: gate.as_dict() for name, gate in stages.items()},
                "browser": {name: gate.as_dict() for name, gate in browser.items()},
            }
        return {
            "schema_version": "aris.business-e2e.verifier.v1",
            "run_id": self.run_id,
            "run_path": self.run_path,
            "status": self.status,
            "shared": {name: gate.as_dict() for name, gate in self.shared.items()},
            "runtimes": runtime_payload,
        }


@dataclass(frozen=True)
class Context:
    repo_root: Path
    run_dir: Path


@dataclass(frozen=True)
class Receipt:
    path: Path
    data: Mapping[str, Any]


class VerificationInputError(ValueError):
    """Raised for an invalid evidence root or run selector."""


def combine_status(statuses: Iterable[Status]) -> Status:
    values = tuple(statuses)
    if any(value == "FAIL" for value in values):
        return "FAIL"
    if not values or any(value == "INCOMPLETE" for value in values):
        return "INCOMPLETE"
    return "PASS"


def _accepted_status(value: object) -> bool:
    normalized = str(value or "").strip().lower().replace("-", "_")
    return normalized in PASS_WORDS or normalized.startswith("pass") or normalized.startswith("complete")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _display_path(path: Path, context: Context) -> str:
    for root in (context.repo_root, context.run_dir):
        try:
            return str(path.relative_to(root))
        except ValueError:
            pass
    return path.name


def _resolve_path(raw: object, receipt_path: Path, context: Context) -> Path | None:
    if not isinstance(raw, str) or not raw.strip() or raw.startswith("~"):
        return None
    given = Path(raw)
    candidates = [given] if given.is_absolute() else [
        receipt_path.parent / given,
        context.run_dir / given,
        context.repo_root / given,
    ]
    selected = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
    resolved = selected.resolve(strict=False)
    try:
        resolved.relative_to(context.repo_root)
    except ValueError:
        return None
    return resolved


def _load_receipt(path: Path, label: str) -> tuple[Receipt | None, Check]:
    if not path.is_file():
        return None, Check(label, "INCOMPLETE", f"missing receipt: {path.name}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return None, Check(label, "FAIL", f"unreadable receipt {path.name}: {type(error).__name__}")
    if not isinstance(payload, dict):
        return None, Check(label, "FAIL", f"receipt is not a JSON object: {path.name}")
    return Receipt(path=path, data=payload), Check(label, "PASS", f"loaded {path.name}")


def _numeric(mapping: Mapping[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def _nested(mapping: Mapping[str, Any], *keys: str) -> Any:
    value: Any = mapping
    for key in keys:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _csv_dimensions(path: Path, encoding: str, security_code: str | None) -> tuple[int, int, str | None]:
    codec = "utf-8-sig" if encoding.lower() in {"utf-8-bom", "utf8-bom"} else encoding
    try:
        with path.open("r", encoding=codec or "utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
    except (OSError, UnicodeError, csv.Error) as error:
        return 0, 0, f"CSV parse failed: {type(error).__name__}"
    if not rows:
        return 0, 0, "CSV is empty"
    columns = len(rows[0])
    if any(len(row) != columns for row in rows):
        return 0, columns, "CSV has ragged rows"
    if security_code:
        data_rows = sum(bool(row) and row[0].lstrip("\ufeff") == security_code for row in rows)
    else:
        data_rows = max(len(rows) - 1, 0)
    return data_rows, columns, None


def _parquet_dimensions(path: Path) -> tuple[int, int, str | None]:
    try:
        import pyarrow.parquet as parquet  # type: ignore[import-not-found]

        metadata = parquet.read_metadata(path)
        return metadata.num_rows, metadata.num_columns, None
    except ImportError:
        pass
    rscript = shutil.which("Rscript")
    if not rscript:
        return 0, 0, "neither pyarrow nor R/arrow is available for Parquet dimensions"
    expression = (
        "a<-commandArgs(trailingOnly=TRUE);"
        "if(!requireNamespace('arrow',quietly=TRUE))quit(status=9);"
        "x<-arrow::read_parquet(a[[1]],as_data_frame=FALSE);"
        "cat(nrow(x),'\\t',ncol(x),sep='')"
    )
    result = subprocess.run(
        [rscript, "-e", expression, str(path)], capture_output=True, text=True, timeout=60, check=False
    )
    if result.returncode != 0 or not re.fullmatch(r"\d+\t\d+", result.stdout.strip()):
        return 0, 0, "R/arrow could not read Parquet dimensions"
    rows, columns = result.stdout.strip().split("\t")
    return int(rows), int(columns), None


def _pdf_page_count(path: Path) -> tuple[int | None, str | None]:
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]

        return len(PdfReader(str(path)).pages), None
    except ImportError:
        pass
    pdfinfo = shutil.which("pdfinfo")
    if not pdfinfo:
        return None, "neither pypdf nor pdfinfo is available for page verification"
    result = subprocess.run([pdfinfo, str(path)], capture_output=True, text=True, timeout=60, check=False)
    match = re.search(r"^Pages:\s*(\d+)\s*$", result.stdout, flags=re.MULTILINE)
    if result.returncode != 0 or match is None:
        return None, "pdfinfo could not read the PDF page count"
    return int(match.group(1)), None


def _word_count(path: Path) -> tuple[int | None, str | None]:
    wc = shutil.which("wc")
    if not wc:
        return None, "wc is unavailable for receipt-compatible word counting"
    result = subprocess.run([wc, "-w", str(path)], capture_output=True, text=True, timeout=30, check=False)
    match = re.match(r"\s*(\d+)", result.stdout)
    if result.returncode != 0 or match is None:
        return None, "wc could not count words"
    return int(match.group(1)), None


def _artifact_mapping(mapping: Mapping[str, Any], *, path_key: str = "path") -> dict[str, Any]:
    normalized = dict(mapping)
    normalized["path"] = mapping.get(path_key)
    if "size_bytes" not in normalized:
        normalized["size_bytes"] = mapping.get("bytes", mapping.get("byte_size"))
    if "pages" not in normalized:
        normalized["pages"] = mapping.get("page_count")
    return normalized


def _complete_artifact_ref(mapping: Mapping[str, Any]) -> bool:
    size = _numeric(mapping, "size_bytes", "bytes", "byte_size")
    return (
        isinstance(mapping.get("path"), str)
        and bool(str(mapping.get("path")).strip())
        and re.fullmatch(r"[0-9a-f]{64}", str(mapping.get("sha256") or "").lower()) is not None
        and size is not None
        and size >= 0
    )


def _verify_artifact(
    mapping: Mapping[str, Any], receipt_path: Path, context: Context, *, security_code: str | None = None
) -> Check:
    raw_path = mapping.get("path")
    path = _resolve_path(raw_path, receipt_path, context)
    label = f"artifact:{Path(str(raw_path)).name}" if raw_path else "artifact"
    if path is None:
        return Check(label, "FAIL", "artifact path is missing or outside the repository")
    shown = _display_path(path, context)
    if not path.is_file():
        return Check(label, "FAIL", f"artifact does not exist: {shown}")

    issues: list[str] = []
    incomplete: list[str] = []
    expected_hash = str(mapping.get("sha256") or "").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        issues.append("missing valid SHA-256")
    elif _sha256(path) != expected_hash:
        issues.append("SHA-256 mismatch")
    expected_size = _numeric(mapping, "size_bytes", "bytes", "byte_size")
    if expected_size is not None and path.stat().st_size != expected_size:
        issues.append(f"bytes {path.stat().st_size} != {expected_size}")

    suffix = path.suffix.lower()
    expected_rows = _numeric(mapping, "data_rows", "rows")
    expected_columns = _numeric(mapping, "columns", "columns_count")
    if expected_rows is not None or expected_columns is not None:
        if suffix == ".csv":
            actual_rows, actual_columns, error = _csv_dimensions(
                path, str(mapping.get("encoding") or "utf-8-sig"), security_code
            )
        elif suffix in {".parquet", ".pq"}:
            actual_rows, actual_columns, error = _parquet_dimensions(path)
        else:
            actual_rows, actual_columns, error = 0, 0, f"unsupported tabular format {suffix or '<none>'}"
        if error:
            incomplete.append(error)
        else:
            if expected_rows is not None and actual_rows != expected_rows:
                issues.append(f"rows {actual_rows} != {expected_rows}")
            if expected_columns is not None and actual_columns != expected_columns:
                issues.append(f"columns {actual_columns} != {expected_columns}")

    expected_pages = _numeric(mapping, "pages", "page_count")
    if expected_pages is not None:
        actual_pages, error = _pdf_page_count(path)
        if error:
            incomplete.append(error)
        elif actual_pages != expected_pages:
            issues.append(f"pages {actual_pages} != {expected_pages}")

    expected_lines = _numeric(mapping, "lines")
    if expected_lines is not None:
        try:
            actual_lines = len(path.read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeError) as error:
            incomplete.append(f"line count failed: {type(error).__name__}")
        else:
            if actual_lines != expected_lines:
                issues.append(f"lines {actual_lines} != {expected_lines}")
    expected_words = _numeric(mapping, "words")
    if expected_words is not None:
        actual_words, error = _word_count(path)
        if error:
            incomplete.append(error)
        elif actual_words != expected_words:
            issues.append(f"words {actual_words} != {expected_words}")

    detected = str(mapping.get("detected_format") or "").lower()
    if detected == "pdf" or suffix == ".pdf":
        data = path.read_bytes()
        if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-4096:]:
            issues.append("invalid PDF magic or EOF marker")
    if detected == "zip" or suffix == ".zip":
        try:
            with zipfile.ZipFile(path) as archive:
                if archive.testzip() is not None:
                    issues.append("ZIP CRC verification failed")
        except (OSError, zipfile.BadZipFile):
            issues.append("invalid ZIP container")
    for key, value in mapping.items():
        if key.endswith("_mismatches") and value != 0:
            issues.append(f"{key}={value}")
    if mapping.get("verified") is False:
        issues.append("receipt marks artifact unverified")

    if issues:
        return Check(label, "FAIL", f"{shown}: {'; '.join(issues)}")
    if incomplete:
        return Check(label, "INCOMPLETE", f"{shown}: {'; '.join(incomplete)}")
    facts = ["SHA-256"]
    if expected_rows is not None:
        facts.append(f"{expected_rows} rows")
    if expected_columns is not None:
        facts.append(f"{expected_columns} columns")
    if expected_pages is not None:
        facts.append(f"{expected_pages} pages")
    return Check(label, "PASS", f"verified {shown} ({', '.join(facts)})")


def _receipt_status(receipt: Receipt, *fields: str) -> Check:
    values = [receipt.data.get(field) for field in fields]
    accepted = any(_accepted_status(value) for value in values)
    return Check(
        f"status:{receipt.path.name}",
        "PASS" if accepted else "FAIL",
        f"accepted status in {receipt.path.name}" if accepted else f"receipt is not accepted: {receipt.path.name}",
    )


def _bool_check(name: str, value: object, expected: bool = True) -> Check:
    if value is expected:
        return Check(name, "PASS", f"{name}={str(expected).lower()}")
    return Check(name, "FAIL", f"{name} is not {str(expected).lower()}")


def _manifest_check(
    manifest: Path, records: Sequence[Mapping[str, Any]], receipt_path: Path, context: Context, name: str
) -> Check:
    if not manifest.is_file():
        return Check(name, "INCOMPLETE", f"missing manifest: {manifest.name}")
    try:
        text = manifest.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        return Check(name, "FAIL", f"manifest unreadable: {type(error).__name__}")
    missing: list[str] = []
    for record in records:
        expected_hash = str(record.get("sha256") or "")
        resolved = _resolve_path(record.get("path"), receipt_path, context)
        spellings = [str(record.get("path") or "")]
        if resolved is not None:
            for root in (context.repo_root, context.run_dir):
                try:
                    spellings.append(str(resolved.relative_to(root)))
                except ValueError:
                    pass
        if expected_hash not in text or not any(spelling and spelling in text for spelling in spellings):
            missing.append(Path(str(record.get("path") or "artifact")).name)
    if missing:
        return Check(name, "FAIL", f"manifest lacks artifact path/hash entries: {', '.join(missing)}")
    return Check(name, "PASS", f"manifest links {len(records)} accepted artifact(s)")


def _p1_gate(context: Context) -> Gate:
    checks: list[Check] = []
    manifest_records: list[Mapping[str, Any]] = []
    r_path = context.run_dir / "wrds/receipts/p1-wrds-r.json"
    r_receipt, loaded = _load_receipt(r_path, "P1 R receipt")
    checks.append(loaded)
    if r_receipt:
        checks.extend(
            [
                _receipt_status(r_receipt, "status"),
                _bool_check("WRDS minimal query", _nested(r_receipt.data, "connection", "minimal_query_passed")),
                _bool_check(
                    "WRDS secret values absent",
                    _nested(r_receipt.data, "credentials", "secret_values_recorded"),
                    False,
                ),
            ]
        )
        for extract in r_receipt.data.get("extracts", []):
            if not isinstance(extract, dict):
                continue
            artifacts = extract.get("artifacts") or (
                [extract["artifact"]] if isinstance(extract.get("artifact"), dict) else []
            )
            normalized = [_artifact_mapping(item) for item in artifacts if isinstance(item, dict)]
            checks.extend(_verify_artifact(item, r_receipt.path, context) for item in normalized)
            if normalized:
                manifest_records.append(normalized[-1])

    sas_path = context.run_dir / "wrds/receipts/p1-wrds-sas-cloud.json"
    sas_receipt, loaded = _load_receipt(sas_path, "P1 SAS receipt")
    checks.append(loaded)
    if sas_receipt:
        checks.extend(
            [
                _receipt_status(sas_receipt, "status"),
                _bool_check(
                    "SAS noninteractive SSH",
                    _nested(sas_receipt.data, "ssh", "ordinary_noninteractive_command_passed"),
                ),
                _bool_check(
                    "SAS log has zero errors",
                    _nested(sas_receipt.data, "sas_log_audit", "error_count") == 0,
                ),
                _bool_check(
                    "SAS remote/local hash match",
                    _nested(sas_receipt.data, "transfer", "remote_local_hash_match"),
                ),
            ]
        )
        files = _nested(sas_receipt.data, "transfer", "files")
        files = files if isinstance(files, list) else []
        normalized = [_artifact_mapping(item) for item in files if isinstance(item, dict)]
        checks.extend(_verify_artifact(item, sas_receipt.path, context) for item in normalized)
        if normalized:
            manifest_records.append(normalized[0])
        program = sas_receipt.data.get("submit", {})
        if isinstance(program, dict) and program.get("program"):
            checks.append(
                _verify_artifact(
                    {"path": program.get("program"), "sha256": program.get("program_sha256")},
                    sas_receipt.path,
                    context,
                )
            )
    if manifest_records:
        checks.append(
            _manifest_check(
                context.run_dir / "wrds/DATA_MANIFEST.md", manifest_records, r_path, context, "P1 data manifest"
            )
        )
    return Gate.from_checks("P1", checks)


def _docx_structure_check(
    path: Path,
    document: Mapping[str, Any],
    metadata_receipt: Mapping[str, Any],
) -> Check:
    issues: list[str] = []
    try:
        with zipfile.ZipFile(path) as package:
            root = ET.fromstring(package.read("word/document.xml"))
            core = ET.fromstring(package.read("docProps/core.xml"))
            app = ET.fromstring(package.read("docProps/app.xml"))
    except (OSError, KeyError, zipfile.BadZipFile, ET.ParseError) as error:
        return Check("P2 DOCX structure", "FAIL", f"DOCX package invalid: {type(error).__name__}")
    tables = len(root.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tbl"))
    figures = len(root.findall(".//{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}docPr"))
    if tables != document.get("tables"):
        issues.append(f"tables {tables} != {document.get('tables')}")
    if figures != document.get("figures"):
        issues.append(f"figures {figures} != {document.get('figures')}")
    creator = core.findtext("{http://purl.org/dc/elements/1.1/}creator")
    modifier = core.findtext("{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}lastModifiedBy")
    company = app.findtext("{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Company") or ""
    manager = app.findtext("{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Manager") or ""
    expected_author = metadata_receipt.get("creator")
    if (
        not isinstance(expected_author, str)
        or not expected_author.strip()
        or creator != expected_author
        or modifier != expected_author
        or metadata_receipt.get("lastModifiedBy") != expected_author
    ):
        issues.append("Author/Last Modified By does not match the configured receipt identity")
    if company or manager:
        issues.append("Company/Manager metadata is not empty")
    return Check(
        "P2 DOCX structure",
        "FAIL" if issues else "PASS",
        "; ".join(issues) if issues else f"DOCX has {tables} tables, {figures} figure(s), normalized identity",
    )


def _p2_render_checks(context: Context) -> list[Check]:
    acceptance = context.run_dir / "p2/qa/P2_ACCEPTANCE.md"
    if not acceptance.is_file():
        return [Check("P2 render receipt", "INCOMPLETE", "missing P2_ACCEPTANCE.md")]
    text = acceptance.read_text(encoding="utf-8")
    path_match = re.search(r"- PDF: `([^`]+)`", text)
    hash_match = re.search(r"- PDF SHA-256: `([0-9a-f]{64})`", text)
    pages_match = re.search(r"- Pages: `(\d+)`", text)
    if not path_match or not hash_match or not pages_match or "Status: **PASS**" not in text:
        return [Check("P2 render receipt", "FAIL", "P2 acceptance lacks status/PDF/hash/page facts")]
    record = {
        "path": path_match.group(1),
        "sha256": hash_match.group(1),
        "pages": int(pages_match.group(1)),
        "detected_format": "pdf",
    }
    checks = [_verify_artifact(record, acceptance, context)]
    for page, digest in re.findall(r"\|\s*(\d+)\s*\|\s*`([0-9a-f]{64})`\s*\|", text):
        checks.append(
            _verify_artifact(
                {"path": f"../rendered/page-{page}.png", "sha256": digest}, acceptance, context
            )
        )
    return checks


def _p2_gate(context: Context) -> Gate:
    receipt_path = context.run_dir / "p2/output/results_docx/RESULTS_DOCX_RECEIPT.json"
    receipt, loaded = _load_receipt(receipt_path, "P2 results receipt")
    checks = [loaded]
    manifest_records: list[Mapping[str, Any]] = []
    if receipt:
        document = receipt.data.get("document", {})
        if not isinstance(document, dict):
            return Gate.from_checks("P2", checks + [Check("P2 document", "FAIL", "document record is absent")])
        doc_record = _artifact_mapping(document)
        checks.append(_verify_artifact(doc_record, receipt.path, context))
        manifest_records.append(doc_record)
        doc_path = _resolve_path(doc_record.get("path"), receipt.path, context)
        metadata = _mapping(receipt.data.get("metadata"))
        if doc_path and doc_path.is_file():
            checks.append(_docx_structure_check(doc_path, document, metadata))
        checks.extend(
            [
                _bool_check("P2 metadata audit", metadata.get("passed")),
                _bool_check(
                    "P2 manuscript untouched",
                    _nested(receipt.data, "safety", "manuscript_files_modified"),
                    False,
                ),
                _bool_check(
                    "P2 narrative count",
                    len(receipt.data.get("narrative_claims", [])) == document.get("narrative_claims"),
                ),
            ]
        )
        for item in receipt.data.get("inputs", []):
            if isinstance(item, dict):
                normalized = _artifact_mapping(item)
                checks.append(_verify_artifact(normalized, receipt.path, context))
                manifest_records.append(normalized)
        for item in receipt.data.get("tables", []):
            if isinstance(item, dict):
                checks.append(_verify_artifact(_artifact_mapping(item, path_key="source"), receipt.path, context))
        a11y_path = context.run_dir / "p2/qa/a11y_report.json"
        a11y, a11y_loaded = _load_receipt(a11y_path, "P2 accessibility receipt")
        checks.append(a11y_loaded)
        if a11y:
            counts = _mapping(a11y.data.get("counts"))
            checks.append(
                _bool_check(
                    "P2 accessibility findings",
                    sum(counts.values()) == 0 and not a11y.data.get("findings"),
                )
            )
        checks.extend(_p2_render_checks(context))
        checks.append(
            _manifest_check(
                context.run_dir / "p2/output/results_docx/RESULTS_DOCX_MANIFEST.md",
                manifest_records,
                receipt.path,
                context,
                "P2 results manifest",
            )
        )
    return Gate.from_checks("P2", checks)


def _markdown_fields(text: str, names: Sequence[str]) -> dict[str, str]:
    """Parse required ``- field: value`` scalars without treating ``unknown`` as blank."""
    fields: dict[str, str] = {}
    for name in names:
        match = re.search(rf"^- {re.escape(name)}:[ \t]*([^\r\n]*)$", text, flags=re.MULTILINE)
        if match is None:
            continue
        value = match.group(1).strip()
        if value.startswith("`") and value.endswith("`") and len(value) >= 2:
            value = value[1:-1].strip()
        if value:
            fields[name] = value
    return fields


def _read_text_artifact(
    record: Mapping[str, Any], receipt_path: Path, context: Context, label: str
) -> tuple[Path | None, str | None, Check | None]:
    path = _resolve_path(record.get("path"), receipt_path, context)
    if path is None or not path.is_file():
        return None, None, Check(label, "FAIL", f"{label} path is missing or outside the repository")
    try:
        return path, path.read_text(encoding="utf-8"), None
    except (OSError, UnicodeError) as error:
        return path, None, Check(label, "FAIL", f"{label} is unreadable: {type(error).__name__}")


def _png_dimensions(path: Path) -> tuple[int | None, int | None, str | None]:
    """Read PNG dimensions from the independently parsed IHDR header."""
    try:
        header = path.read_bytes()[:24]
    except OSError as error:
        return None, None, f"PNG read failed: {type(error).__name__}"
    if (
        len(header) != 24
        or header[:8] != b"\x89PNG\r\n\x1a\n"
        or header[12:16] != b"IHDR"
    ):
        return None, None, "invalid PNG signature or IHDR"
    width, height = struct.unpack(">II", header[16:24])
    if width <= 0 or height <= 0:
        return None, None, "PNG dimensions are not positive"
    return width, height, None


def _junit_counts(path: Path) -> tuple[dict[str, int] | None, str | None]:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError, ValueError) as error:
        return None, f"JUnit parse failed: {type(error).__name__}"
    if root.tag not in {"testsuite", "testsuites"}:
        return None, "unexpected JUnit root"

    def count(name: str) -> int:
        direct = root.attrib.get(name)
        if direct is not None:
            return int(direct)
        return sum(int(suite.attrib.get(name, "0")) for suite in root.findall("testsuite"))

    try:
        return {
            "tests": count("tests"),
            "failures": count("failures"),
            "errors": count("errors"),
            "skipped": count("skipped"),
            "xfailed": 0,
        }, None
    except ValueError:
        return None, "JUnit counts are not integers"


def _p3_render_evidence_issues(
    payload: Mapping[str, Any],
    pdf_path: Path,
    expected_pdf_hash: str,
    context: Context,
    expected_viewer_pages: object,
) -> tuple[list[str], int]:
    """Validate every visual derivative against current PDF/PNG files."""
    issues: list[str] = []
    evidence = _mapping(payload.get("render_evidence"))
    if evidence.get("schema") != P3_RENDER_EVIDENCE_SCHEMA:
        return ["render_evidence is missing or has the wrong schema"], 0
    if evidence.get("page_number_basis") != "1-based PDF viewer page":
        issues.append("render_evidence page-number basis is not 1-based PDF viewer page")
    pages = evidence.get("pages")
    if not isinstance(pages, list) or not pages:
        return issues + ["render_evidence pages are absent or malformed"], 0
    if evidence.get("count") != len(pages):
        issues.append(f"render_evidence count {evidence.get('count')} != {len(pages)}")
    if (
        not isinstance(expected_viewer_pages, list)
        or not expected_viewer_pages
        or any(
            not isinstance(page, int) or isinstance(page, bool) or page < 1
            for page in expected_viewer_pages
        )
        or len(expected_viewer_pages) != len(set(expected_viewer_pages))
    ):
        issues.append("synthesis expected_render_pages are absent or malformed")
        expected_pages: list[int] = []
    else:
        expected_pages = expected_viewer_pages

    actual_pdf_hash = _sha256(pdf_path)
    actual_page_count, page_error = _pdf_page_count(pdf_path)
    if page_error or actual_page_count is None:
        issues.append(f"source PDF page count could not be independently checked: {page_error}")
    expected_page_count = _numeric(payload, "page_count", "pages")
    if actual_page_count is not None and actual_page_count != expected_page_count:
        issues.append(f"source PDF pages {actual_page_count} != {expected_page_count}")

    seen_paths: set[Path] = set()
    seen_pages: set[int] = set()
    recorded_pages: list[int] = []
    verified = 0
    for index, raw_page in enumerate(pages, 1):
        if not isinstance(raw_page, Mapping):
            issues.append(f"render page {index}: record is not an object")
            continue
        page_issues: list[str] = []
        if raw_page.get("source_pdf_sha256") != expected_pdf_hash:
            page_issues.append("source_pdf_sha256 does not match synthesis input")
        if raw_page.get("source_pdf_sha256") != actual_pdf_hash:
            page_issues.append("source_pdf_sha256 does not match current PDF")

        viewer_page = _numeric(raw_page, "viewer_page")
        if viewer_page is None or viewer_page < 1:
            page_issues.append("viewer_page is not a positive integer")
        else:
            recorded_pages.append(viewer_page)
            if actual_page_count is not None and viewer_page > actual_page_count:
                page_issues.append(f"viewer_page {viewer_page} exceeds current PDF pages {actual_page_count}")
            elif viewer_page in seen_pages:
                page_issues.append(f"duplicate viewer_page {viewer_page}")
            else:
                seen_pages.add(viewer_page)

        raw_png_path = raw_page.get("png_path")
        png_is_repo_relative = (
            isinstance(raw_png_path, str)
            and bool(raw_png_path.strip())
            and not Path(raw_png_path).is_absolute()
            and (context.repo_root / raw_png_path).resolve(strict=False).is_relative_to(
                context.repo_root
            )
        )
        png_path = (
            (context.repo_root / raw_png_path).resolve(strict=False)
            if png_is_repo_relative
            else None
        )
        if not png_is_repo_relative:
            page_issues.append("PNG path is not repository-relative")
        if png_path is None:
            page_issues.append("PNG path is missing or outside the repository")
        elif not png_path.is_file():
            page_issues.append(f"render PNG missing: {_display_path(png_path, context)}")
        else:
            if png_path in seen_paths:
                page_issues.append("duplicate PNG path")
            seen_paths.add(png_path)
            if png_path.suffix.lower() != ".png":
                page_issues.append("render artifact is not .png")
            filename_page = re.search(r"(?:^|-)p(\d+)(?:-|\.png$)", png_path.name)
            if viewer_page is not None and (
                filename_page is None or int(filename_page.group(1)) != viewer_page
            ):
                page_issues.append("viewer_page does not match the PNG filename")
            expected_png_hash = str(raw_page.get("png_sha256") or "").lower()
            if not re.fullmatch(r"[0-9a-f]{64}", expected_png_hash):
                page_issues.append("missing valid PNG SHA-256")
            elif _sha256(png_path) != expected_png_hash:
                page_issues.append("PNG SHA-256 mismatch")
            expected_bytes = _numeric(raw_page, "png_bytes")
            if expected_bytes is None:
                page_issues.append("png_bytes is missing")
            elif png_path.stat().st_size != expected_bytes:
                page_issues.append(f"PNG bytes {png_path.stat().st_size} != {expected_bytes}")
            actual_width, actual_height, png_error = _png_dimensions(png_path)
            if png_error:
                page_issues.append(png_error)
            else:
                expected_width = _numeric(raw_page, "width_px")
                expected_height = _numeric(raw_page, "height_px")
                if actual_width != expected_width or actual_height != expected_height:
                    page_issues.append(
                        f"PNG dimensions {actual_width}x{actual_height} != "
                        f"{expected_width}x{expected_height}"
                    )

        for key in ("renderer_tool", "renderer_version"):
            value = raw_page.get(key)
            if not isinstance(value, str) or not value.strip():
                page_issues.append(f"{key} is blank")
        if page_issues:
            issues.append(f"render page {index}: {'; '.join(page_issues)}")
        else:
            verified += 1
    if expected_pages and recorded_pages != expected_pages:
        issues.append(f"render viewer pages {recorded_pages} != synthesis expected pages {expected_pages}")
    return issues, verified


def _p3_pdf_processing_check(
    record: Mapping[str, Any],
    pdf_record: Mapping[str, Any],
    receipt_path: Path,
    context: Context,
    paper_id: str,
    expected_render_pages: object,
) -> Check:
    processing_path = _resolve_path(record.get("path"), receipt_path, context)
    pdf_path = _resolve_path(pdf_record.get("path"), receipt_path, context)
    if processing_path is None or not processing_path.is_file() or pdf_path is None or not pdf_path.is_file():
        return Check(f"P3 PDF processing:{paper_id}", "FAIL", "processing receipt or source PDF is missing")
    try:
        payload = json.loads(processing_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return Check(
            f"P3 PDF processing:{paper_id}",
            "FAIL",
            f"PDF processing receipt is unreadable: {type(error).__name__}",
        )
    if not isinstance(payload, dict):
        return Check(f"P3 PDF processing:{paper_id}", "FAIL", "PDF processing receipt is not an object")

    issues: list[str] = []
    if payload.get("schema") != P3_PDF_INSPECTION_SCHEMA:
        issues.append("wrong schema")
    if payload.get("ok") is not True:
        issues.append("ok is not true")
    if payload.get("ready_for_method_harvest") is not True:
        issues.append("ready_for_method_harvest is not true")
    if payload.get("source_pdf_preserved") is not True:
        issues.append("source_pdf_preserved is not true")
    if _nested(payload, "identity", "status") != "pass":
        issues.append("identity status is not pass")
    classification = _nested(payload, "text_layer", "classification")
    if not isinstance(classification, str) or not classification.strip():
        issues.append("text_layer.classification is blank")

    recorded_pdf = _resolve_path(payload.get("source_pdf"), processing_path, context)
    if recorded_pdf != pdf_path:
        issues.append("source_pdf does not match the v2 input PDF")
    expected_hash = str(pdf_record.get("sha256") or "").lower()
    if payload.get("source_pdf_sha256") != expected_hash or _sha256(pdf_path) != expected_hash:
        issues.append("source PDF hash lineage mismatch")
    expected_pages = _numeric(pdf_record, "pages", "page_count")
    if payload.get("page_count") != expected_pages:
        issues.append("source PDF page-count lineage mismatch")
    expected_size = _numeric(pdf_record, "size_bytes", "bytes", "byte_size")
    if payload.get("size_bytes") != expected_size or pdf_path.stat().st_size != expected_size:
        issues.append("source PDF byte-size lineage mismatch")
    render_issues, verified_renders = _p3_render_evidence_issues(
        payload,
        pdf_path,
        expected_hash,
        context,
        expected_render_pages,
    )
    issues.extend(render_issues)

    return Check(
        f"P3 PDF processing:{paper_id}",
        "FAIL" if issues else "PASS",
        "; ".join(issues)
        if issues
        else (
            f"inspection receipt is ready ({classification}, {expected_pages} pages, source preserved, "
            f"{verified_renders} render PNGs independently verified)"
        ),
    )


def _p3_method_card_check(
    item: Mapping[str, Any], receipt_path: Path, context: Context
) -> Check:
    paper_id = str(item.get("paper_id") or "").strip()
    pdf_record = _mapping(item.get("pdf"))
    card_record = _mapping(item.get("method_card"))
    processing_record = _mapping(item.get("pdf_processing"))
    card_path, text, error = _read_text_artifact(
        card_record, receipt_path, context, f"P3 method card:{paper_id or '<missing>'}"
    )
    pdf_path = _resolve_path(pdf_record.get("path"), receipt_path, context)
    processing_path = _resolve_path(processing_record.get("path"), receipt_path, context)
    if error:
        return error
    assert card_path is not None and text is not None

    issues: list[str] = []
    if not paper_id or f"# METHOD_CARD: {paper_id}" not in text:
        issues.append("paper_id/header mismatch")
    missing_tokens = [token for token in P3_METHOD_CARD_TOKENS if token not in text]
    if missing_tokens:
        issues.append(f"missing contract tokens: {', '.join(missing_tokens)}")
    fields = _markdown_fields(text, P3_METHOD_CARD_FIELDS)
    missing_fields = [name for name in P3_METHOD_CARD_FIELDS if name not in fields]
    if missing_fields:
        issues.append(f"missing or blank fields: {', '.join(missing_fields)}")

    expected_fields = _mapping(item.get("expected_fields"))
    for name, expected in expected_fields.items():
        if fields.get(name) != expected:
            issues.append(f"{name}={fields.get(name, '<missing>')} != {expected}")
    if fields.get("source_depth") != "fulltext":
        issues.append("source_depth is not fulltext")

    expected_hash = str(pdf_record.get("sha256") or "").lower()
    card_hash = fields.get("content_hash", "").removeprefix("sha256:")
    if card_hash != expected_hash:
        issues.append("card content_hash does not match input PDF")
    if pdf_path is None or not pdf_path.is_file():
        issues.append("input PDF is missing")
    else:
        card_pdf_path = _resolve_path(fields.get("local_path"), card_path, context)
        if card_pdf_path != pdf_path:
            issues.append("card local_path does not match input PDF")
        if fields.get("size_bytes") != str(pdf_path.stat().st_size):
            issues.append("card size_bytes does not match input PDF")
        page_count, page_error = _pdf_page_count(pdf_path)
        if page_error:
            issues.append(page_error)
        elif fields.get("pages") != str(page_count):
            issues.append("card pages do not match input PDF")
    if processing_path is None or fields.get("pdf_processing_receipt") is None:
        issues.append("PDF processing receipt lineage is absent")
    else:
        card_processing_path = _resolve_path(fields["pdf_processing_receipt"], card_path, context)
        if card_processing_path != processing_path:
            issues.append("card PDF processing receipt path mismatch")

    literature_root = context.run_dir / "literature-v2" / "cards"
    try:
        card_path.relative_to(literature_root)
    except ValueError:
        issues.append("method card is not under literature-v2/cards")
    return Check(
        f"P3 method card contract:{paper_id or '<missing>'}",
        "FAIL" if issues else "PASS",
        "; ".join(issues)
        if issues
        else f"parsed {len(P3_METHOD_CARD_TOKENS)} tokens and {len(fields)} nonblank fields with PDF lineage",
    )


def _p3_output_contract_check(
    role: str,
    record: Mapping[str, Any],
    receipt_path: Path,
    context: Context,
    inputs: Sequence[Mapping[str, Any]],
) -> Check:
    path, text, error = _read_text_artifact(record, receipt_path, context, f"P3 {role}")
    if error:
        return error
    assert path is not None and text is not None
    issues: list[str] = []
    try:
        path.relative_to(context.run_dir / "literature-v2")
    except ValueError:
        issues.append(f"{role} is not under literature-v2")
    missing_tokens = [token for token in P3_OUTPUT_CONTRACTS[role] if token not in text]
    if missing_tokens:
        issues.append(f"missing contract tokens: {', '.join(missing_tokens)}")
    for item in inputs:
        paper_id = str(item.get("paper_id") or "")
        pdf_hash = str(_mapping(item.get("pdf")).get("sha256") or "")
        if paper_id not in text:
            issues.append(f"missing paper_id {paper_id or '<blank>'}")
        if role in {"evidence_matrix", "acceptance_report"} and pdf_hash not in text:
            issues.append(f"missing PDF hash for {paper_id or '<blank>'}")
        if role == "method_card_index":
            card_name = Path(str(_mapping(item.get("method_card")).get("path") or "")).name
            if card_name not in text:
                issues.append(f"missing method-card link for {paper_id or '<blank>'}")
    if role == "evidence_matrix":
        for item in inputs:
            status = str(_mapping(item.get("expected_fields")).get("numeric_audit_status") or "")
            if status and f"numeric_audit_status={status}" not in text:
                issues.append(f"missing numeric audit status for {item.get('paper_id')}")
    if role == "literature_review" and "PDF p." not in text:
        issues.append("review has no PDF page grounding")
    if role == "acceptance_report":
        statuses = re.findall(r"^\|[^\n|]+\|\s*([^|\n]+?)\s*\|", text, flags=re.MULTILINE)
        if not statuses or any(not value.strip() for value in statuses):
            issues.append("acceptance tables have blank status cells")
    return Check(
        f"P3 {role} contract",
        "FAIL" if issues else "PASS",
        "; ".join(issues)
        if issues
        else f"parsed {len(P3_OUTPUT_CONTRACTS[role])} contract tokens and {len(inputs)} paper identities",
    )


def _markdown_table_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return [cell.strip().strip("`").strip() for cell in stripped[1:-1].split("|")]


def _p3_manifest_rows(path: Path) -> tuple[list[Mapping[str, str]], Check]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        return [], Check(
            "P3 fulltext manifest schema",
            "FAIL",
            f"manifest is unreadable: {type(error).__name__}",
        )
    table_lines = [line for line in lines if line.strip().startswith("|")]
    if len(table_lines) < 2:
        return [], Check("P3 fulltext manifest schema", "FAIL", "21-column table is absent")
    header = _markdown_table_cells(table_lines[0])
    if header != list(P3_FULLTEXT_MANIFEST_HEADER):
        return [], Check(
            "P3 fulltext manifest schema",
            "FAIL",
            f"manifest header is not the exact {len(P3_FULLTEXT_MANIFEST_HEADER)}-column contract",
        )
    separator = _markdown_table_cells(table_lines[1])
    if separator is None or len(separator) != len(P3_FULLTEXT_MANIFEST_HEADER) or any(
        re.fullmatch(r":?-{3,}:?", cell) is None for cell in separator
    ):
        return [], Check("P3 fulltext manifest schema", "FAIL", "manifest separator is malformed")
    rows: list[Mapping[str, str]] = []
    malformed: list[int] = []
    for line_number, line in enumerate(table_lines[2:], 3):
        cells = _markdown_table_cells(line)
        if cells is None or len(cells) != len(P3_FULLTEXT_MANIFEST_HEADER):
            malformed.append(line_number)
            continue
        rows.append(dict(zip(P3_FULLTEXT_MANIFEST_HEADER, cells, strict=True)))
    if malformed or not rows:
        return rows, Check(
            "P3 fulltext manifest schema",
            "FAIL",
            f"manifest has malformed/no data rows; table_lines={malformed}",
        )
    return rows, Check(
        "P3 fulltext manifest schema",
        "PASS",
        f"parsed {len(rows)} exact 21-column row(s)",
    )


def _artifact_identity_tuple(mapping: Mapping[str, Any]) -> tuple[str, ...] | None:
    values: list[str] = []
    for field in P3_ARTIFACT_IDENTITY_FIELDS:
        value = mapping.get(field)
        if not isinstance(value, str) or not value.strip():
            return None
        values.append(value.strip())
    return tuple(values)


def _p3_artifact_identity_chain_check(
    item: Mapping[str, Any],
    receipt_path: Path,
    context: Context,
    manifest_path: Path,
    manifest_rows: Sequence[Mapping[str, str]],
) -> Check:
    paper_id = str(item.get("paper_id") or "<missing>")
    identity = _mapping(item.get("artifact_identity"))
    expected = _artifact_identity_tuple(identity)
    issues: list[str] = []
    if expected is None:
        issues.append("synthesis artifact_identity is absent or incomplete")
    elif identity.get("work_id") != paper_id:
        issues.append("artifact_identity.work_id does not match paper_id")

    pdf_record = _mapping(item.get("pdf"))
    processing_record = _mapping(item.get("pdf_processing"))
    card_record = _mapping(item.get("method_card"))
    processing_path = _resolve_path(processing_record.get("path"), receipt_path, context)
    card_path = _resolve_path(card_record.get("path"), receipt_path, context)
    pdf_path = _resolve_path(pdf_record.get("path"), receipt_path, context)

    processing_identity: tuple[str, ...] | None = None
    if processing_path is None or not processing_path.is_file():
        issues.append("PDF-processing artifact is missing")
    else:
        try:
            processing_payload = json.loads(processing_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            issues.append(f"PDF-processing identity is unreadable: {type(error).__name__}")
        else:
            if isinstance(processing_payload, dict):
                processing_identity = _artifact_identity_tuple(
                    _mapping(processing_payload.get("artifact_identity"))
                )
            if processing_identity is None:
                issues.append("PDF-processing artifact_identity is absent or incomplete")
    if expected is not None and processing_identity != expected:
        issues.append("PDF-processing artifact_identity differs from synthesis input")

    card_identity: tuple[str, ...] | None = None
    if card_path is None or not card_path.is_file():
        issues.append("method card is missing")
    else:
        try:
            card_text = card_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            issues.append(f"method-card identity is unreadable: {type(error).__name__}")
        else:
            card_identity = _artifact_identity_tuple(
                _markdown_fields(card_text, P3_ARTIFACT_IDENTITY_FIELDS)
            )
            if card_identity is None:
                issues.append("method-card artifact identity fields are absent or incomplete")
    if expected is not None and card_identity != expected:
        issues.append("method-card artifact identity differs from synthesis input")

    matches = [
        row
        for row in manifest_rows
        if _artifact_identity_tuple(row) == expected
    ] if expected is not None else []
    if len(matches) != 1:
        issues.append(f"FULLTEXT_MANIFEST exact artifact-identity matches={len(matches)}, expected 1")
    else:
        row = matches[0]
        manifest_pdf = _resolve_path(row.get("local_path_or_gap"), manifest_path, context)
        expected_hash = str(pdf_record.get("sha256") or "").lower()
        expected_size = _numeric(pdf_record, "size_bytes", "bytes", "byte_size")
        expected_pages = _numeric(pdf_record, "pages", "page_count")
        if manifest_pdf != pdf_path:
            issues.append("manifest local_path_or_gap differs from synthesis PDF")
        if row.get("sha256", "").lower() != expected_hash:
            issues.append("manifest SHA-256 differs from synthesis PDF")
        if row.get("size_bytes") != str(expected_size):
            issues.append("manifest size_bytes differs from synthesis PDF")
        if row.get("pages") != str(expected_pages):
            issues.append("manifest pages differs from synthesis PDF")
        if row.get("status") != "verified":
            issues.append("manifest row status is not verified")

    return Check(
        f"P3 artifact identity chain:{paper_id}",
        "FAIL" if issues else "PASS",
        "; ".join(issues)
        if issues
        else "synthesis, PDF-processing, method-card, and exact manifest row identities join",
    )


def _p3_synthesis_checks(
    synthesis: Receipt, context: Context
) -> tuple[list[Check], list[Mapping[str, Any]]]:
    checks: list[Check] = []
    manifest_records: list[Mapping[str, Any]] = []
    if synthesis.data.get("schema_version") != P3_SYNTHESIS_SCHEMA:
        return (
            [
                Check(
                    "P3 synthesis schema",
                    "FAIL",
                    f"expected {P3_SYNTHESIS_SCHEMA}; legacy synthesis receipt is not v2 evidence",
                )
            ],
            manifest_records,
        )
    checks.append(Check("P3 synthesis schema", "PASS", f"schema={P3_SYNTHESIS_SCHEMA}"))
    inputs = synthesis.data.get("inputs")
    if not isinstance(inputs, list) or not inputs or not all(isinstance(item, dict) for item in inputs):
        return checks + [Check("P3 synthesis inputs", "FAIL", "inputs are absent or malformed")], manifest_records
    typed_inputs = [item for item in inputs if isinstance(item, dict)]
    contract = _mapping(synthesis.data.get("contract"))
    contract_ok = (
        contract.get("name") == "p3-fulltext-to-literature-review"
        and contract.get("version") == 2
        and contract.get("paper_count") == len(typed_inputs)
        and contract.get("required_nonempty_method_card_fields") == list(P3_METHOD_CARD_FIELDS)
        and contract.get("required_output_roles") == list(P3_OUTPUT_CONTRACTS)
    )
    checks.append(
        Check(
            "P3 synthesis declared contract",
            "PASS" if contract_ok else "FAIL",
            "receipt declares the exact built-in v2 field/output contract"
            if contract_ok
            else "receipt contract is absent, weakened, or inconsistent with its inputs",
        )
    )
    paper_ids = [str(item.get("paper_id") or "") for item in typed_inputs]
    if len(paper_ids) != len(set(paper_ids)) or any(not paper_id for paper_id in paper_ids):
        checks.append(Check("P3 synthesis paper IDs", "FAIL", "paper IDs are blank or duplicated"))
    else:
        checks.append(Check("P3 synthesis paper IDs", "PASS", f"{len(paper_ids)} unique paper IDs"))

    manifest_record = _mapping(synthesis.data.get("fulltext_manifest"))
    if manifest_record:
        checks.append(_verify_artifact(_artifact_mapping(manifest_record), synthesis.path, context))
        manifest_path = _resolve_path(manifest_record.get("path"), synthesis.path, context)
    else:
        manifest_path = context.run_dir / "manifests" / "FULLTEXT_MANIFEST.md"
    if manifest_path is None or not manifest_path.is_file():
        manifest_rows: list[Mapping[str, str]] = []
        checks.append(
            Check("P3 fulltext manifest schema", "FAIL", "fulltext manifest is missing")
        )
        manifest_path = context.run_dir / "manifests" / "FULLTEXT_MANIFEST.md"
    else:
        manifest_rows, manifest_check = _p3_manifest_rows(manifest_path)
        checks.append(manifest_check)

    for item in typed_inputs:
        paper_id = str(item.get("paper_id") or "<missing>")
        pdf_record = _mapping(item.get("pdf"))
        card_record = _mapping(item.get("method_card"))
        processing_record = _mapping(item.get("pdf_processing"))
        checks.extend(
            [
                _verify_artifact(pdf_record, synthesis.path, context),
                _verify_artifact(card_record, synthesis.path, context),
                _verify_artifact(processing_record, synthesis.path, context),
                _p3_pdf_processing_check(
                    processing_record,
                    pdf_record,
                    synthesis.path,
                    context,
                    paper_id,
                    item.get("expected_render_pages"),
                ),
                _p3_method_card_check(item, synthesis.path, context),
                _p3_artifact_identity_chain_check(
                    item,
                    synthesis.path,
                    context,
                    manifest_path,
                    manifest_rows,
                ),
            ]
        )
        if pdf_record:
            manifest_records.append(pdf_record)

    outputs = _mapping(synthesis.data.get("outputs"))
    expected_roles = set(P3_OUTPUT_CONTRACTS)
    if set(outputs) != expected_roles:
        missing = sorted(expected_roles - set(outputs))
        extra = sorted(set(outputs) - expected_roles)
        checks.append(
            Check(
                "P3 synthesis output roles",
                "FAIL",
                f"output role mismatch; missing={missing}, extra={extra}",
            )
        )
    else:
        checks.append(Check("P3 synthesis output roles", "PASS", f"{len(outputs)} exact v2 outputs"))
    for role in sorted(expected_roles):
        record = outputs.get(role)
        if not isinstance(record, dict):
            checks.append(Check(f"P3 {role}", "FAIL", "output artifact record is absent"))
            continue
        checks.append(_verify_artifact(_artifact_mapping(record), synthesis.path, context))
        checks.append(_p3_output_contract_check(role, record, synthesis.path, context, typed_inputs))

    required = _mapping(synthesis.data.get("checks"))
    for key in (
        "identity_matched_fulltext_only",
        "artifact_identity_chain_joined",
        "all_paper_hashes_recorded",
        "pdf_processing_ready",
        "pdf_source_preserved",
        "exact_variable_construction_or_unknown",
        "main_null_and_mixed_results_preserved",
        "source_locations_present",
        "agreement_conflict_diagnosed",
        "claim_ceiling_preserved",
    ):
        checks.append(_bool_check(f"P3 synthesis {key}", required.get(key)))
    checks.append(
        _bool_check(
            "P3 abstract-only method claims",
            required.get("abstract_only_method_claims"),
            False,
        )
    )
    return checks, manifest_records


def _p3_shared_gate(context: Context) -> Gate:
    checks: list[Check] = []
    manifest_records: list[Mapping[str, Any]] = []
    oa_path = context.run_dir / "receipts/p3-open-download.json"
    oa, loaded = _load_receipt(oa_path, "P3 open-access receipt")
    checks.append(loaded)
    if oa:
        checks.append(_receipt_status(oa, "verification", "status"))
        record = _artifact_mapping(oa.data, path_key="artifact_path")
        checks.append(_verify_artifact(record, oa.path, context))
        manifest_records.append(record)

    synthesis_path = context.run_dir / "receipts/p3-literature-synthesis.json"
    synthesis, loaded = _load_receipt(synthesis_path, "P3 synthesis receipt")
    checks.append(loaded)
    if synthesis:
        checks.append(_receipt_status(synthesis, "status"))
        synthesis_checks, synthesis_manifest = _p3_synthesis_checks(synthesis, context)
        checks.extend(synthesis_checks)
        manifest_records.extend(synthesis_manifest)

    zotero_path = context.run_dir / "receipts/p3-zotero-semantics.json"
    zotero, loaded = _load_receipt(zotero_path, "P3 Zotero receipt")
    checks.append(loaded)
    if zotero:
        checks.extend(
            [
                _receipt_status(zotero, "status"),
                _bool_check(
                    "Zotero library not mutated",
                    _nested(zotero.data, "database_access", "library_mutated"),
                    False,
                ),
                _bool_check(
                    "Zotero source file found",
                    _nested(zotero.data, "semantic_probe", "source_file_found"),
                ),
            ]
        )
        artifact = zotero.data.get("accepted_artifact", {})
        if isinstance(artifact, dict):
            record = _artifact_mapping(artifact)
            checks.append(_verify_artifact(record, zotero.path, context))
            manifest_records.append(record)
        card = zotero.data.get("method_card", {})
        if isinstance(card, dict):
            checks.append(_verify_artifact(_artifact_mapping(card), zotero.path, context))

    if manifest_records:
        checks.append(
            _manifest_check(
                context.run_dir / "manifests/FULLTEXT_MANIFEST.md",
                manifest_records,
                synthesis_path,
                context,
                "P3 fulltext manifest",
            )
        )
    return Gate.from_checks("P3", checks)


def _normalize_runtime(data: Mapping[str, Any]) -> str | None:
    values = [data.get("executor_runtime"), data.get("host_runtime"), data.get("runtime"), data.get("client_runtime")]
    for value in values:
        normalized = str(value or "").lower()
        if "codex" in normalized:
            return "codex"
        if "kimi" in normalized:
            return "kimi"
    adapter = str(data.get("adapter") or "").lower()
    if adapter == "codex_native_chrome":
        return "codex"
    if adapter == "kimi_webbridge":
        return "kimi"
    return None


TRUSTED_BROWSER_ADAPTERS: Mapping[str, str] = {
    "codex": "codex_native_chrome",
    "kimi": "kimi_webbridge",
}
KIMI_BROWSER_BINDINGS: Mapping[str, str] = {
    "mcp_server": "local_daemon",
    "implementation": "kimi_webbridge",
    "profile_mode": "user_browser",
}
KIMI_DOWNLOAD_VERIFIER = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "browser-session-bridge"
    / "scripts"
    / "verify_download.py"
)


def _browser_adapter_checks(
    data: Mapping[str, Any], runtime: str, gate_name: str
) -> list[Check]:
    """Validate the trusted browser adapter identity for the host runtime."""

    adapter = str(data.get("adapter") or "")
    expected = TRUSTED_BROWSER_ADAPTERS.get(runtime)
    accepted = expected is not None and adapter == expected
    checks = [
        Check(
            f"{gate_name} adapter",
            "PASS" if accepted else "FAIL",
            f"adapter={adapter}"
            if accepted
            else f"unsupported browser adapter for runtime {runtime!r}: {adapter or '<missing>'}",
        )
    ]
    if runtime == "kimi":
        client_runtime = str(data.get("client_runtime") or "")
        checks.append(
            Check(
                f"{gate_name} client_runtime",
                "PASS" if client_runtime == "kimi" else "FAIL",
                "client_runtime=kimi"
                if client_runtime == "kimi"
                else "kimi receipts must declare client_runtime=kimi, "
                f"got {client_runtime or '<missing>'}",
            )
        )
        for field, expected_value in KIMI_BROWSER_BINDINGS.items():
            value = str(data.get(field) or "")
            checks.append(
                Check(
                    f"{gate_name} binding:{field}",
                    "PASS" if value == expected_value else "FAIL",
                    f"{field}={value}"
                    if value == expected_value
                    else f"{field}={value or '<missing>'}, expected {expected_value}",
                )
            )
    return checks


def _kimi_verify_download_check(
    name: str, record: Mapping[str, Any], receipt: Receipt, context: Context
) -> Check:
    """Re-verify the landed kimi download with the deterministic verify_download tool."""

    label = f"{name} deterministic download"
    if not KIMI_DOWNLOAD_VERIFIER.is_file():
        return Check(label, "FAIL", "browser-session-bridge verify_download.py is missing")
    path = _resolve_path(record.get("path"), receipt.path, context)
    if path is None or not path.is_file():
        return Check(label, "FAIL", "download artifact is missing or outside the repository")
    detected = str(record.get("detected_format") or path.suffix.lstrip(".")).lower()
    expect = detected if detected in {"pdf", "csv", "zip", "xlsx"} else "any"
    try:
        result = subprocess.run(
            [sys.executable, str(KIMI_DOWNLOAD_VERIFIER), str(path), "--expect", expect],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return Check(label, "FAIL", f"verify_download failed to run: {type(error).__name__}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return Check(label, "FAIL", "verify_download returned malformed JSON")
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        error = payload.get("error") if isinstance(payload, dict) else None
        detail = error or f"exit={result.returncode}"
        return Check(label, "FAIL", f"verify_download rejected artifact: {detail}")
    issues: list[str] = []
    expected_hash = str(record.get("sha256") or "").lower()
    if re.fullmatch(r"[0-9a-f]{64}", expected_hash) and str(
        payload.get("sha256") or ""
    ).lower() != expected_hash:
        issues.append("verify_download SHA-256 differs from the receipt")
    expected_size = _numeric(record, "size_bytes", "bytes", "byte_size")
    if expected_size is not None and payload.get("size_bytes") != expected_size:
        issues.append(f"verify_download bytes {payload.get('size_bytes')} != {expected_size}")
    if issues:
        return Check(label, "FAIL", "; ".join(issues))
    return Check(
        label,
        "PASS",
        f"verify_download ok ({payload.get('detected_format')}, {payload.get('size_bytes')} bytes)",
    )


def _kimi_download_checks(
    name: str, receipt: Receipt, artifacts: Sequence[Mapping[str, Any]], context: Context
) -> list[Check]:
    """kimi_webbridge has no download-event hook: require directory-increment
    fallback evidence plus a deterministic verify_download re-check instead."""

    checks: list[Check] = []
    transport = _mapping(receipt.data.get("download_transport"))
    fallback = transport.get("completion") == "fallback_directory_increment"
    checks.append(
        Check(
            f"{name} download fallback",
            "PASS" if fallback else "FAIL",
            "directory-increment fallback completion recorded"
            if fallback
            else "kimi_webbridge cannot observe download events; "
            "download_transport.completion must be fallback_directory_increment",
        )
    )
    event_claimed = transport.get("browser_download_event_observed") is True
    checks.append(
        Check(
            f"{name} download event claim",
            "FAIL" if event_claimed else "PASS",
            "kimi_webbridge cannot observe browser download events"
            if event_claimed
            else "no download-event claim, as expected for kimi_webbridge",
        )
    )
    if artifacts:
        primary = next(
            (item for item in artifacts if _numeric(item, "data_rows", "rows") is not None),
            artifacts[-1],
        )
        checks.append(_kimi_verify_download_check(name, primary, receipt, context))
    return checks


def _normalize_site(data: Mapping[str, Any]) -> str | None:
    value = str(data.get("site") or data.get("source") or "").lower().replace(" ", "")
    for site in (*P3_BROWSER_SITES, *P4_BROWSER_SITES):
        if site in value:
            return site
    return None


def _candidate_receipts(context: Context, stage: str, site: str, runtime: str) -> list[Receipt]:
    candidates: list[Receipt] = []
    for path in sorted(context.run_dir.rglob("*.json")):
        lower_name = path.name.lower()
        filename_match = stage.lower() in lower_name and site in lower_name and runtime in lower_name
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            if filename_match:
                candidates.append(Receipt(path, {}))
            continue
        if not isinstance(data, dict):
            continue
        data_match = _normalize_site(data) == site and _normalize_runtime(data) == runtime
        gate_text = " ".join(str(data.get(key) or "") for key in ("stage", "gate", "acceptance_id")).lower()
        stage_match = stage.lower() in lower_name or stage.lower() in gate_text
        if data_match and stage_match:
            candidates.append(Receipt(path, data))
    return candidates


def _p4_semantic_extract_check(receipt: Receipt, context: Context, runtime: str, site: str) -> Check:
    """Re-open the P4 ZIP/CSV and verify the frozen slice outside receipt prose."""

    name = f"P4_{site.upper()} deterministic extract"
    if runtime not in TRUSTED_BROWSER_ADAPTERS:
        return Check(name, "FAIL", f"unsupported runtime for P4 extract verification: {runtime}")
    if not CN_EXTRACT_VERIFIER.is_file():
        return Check(name, "FAIL", "cn-data-bridge deterministic verifier is missing")
    command = [
        sys.executable,
        str(CN_EXTRACT_VERIFIER),
        "--receipt",
        str(receipt.path),
        "--repo-root",
        str(context.repo_root),
        "--run-dir",
        str(context.run_dir),
        "--runtime",
        runtime,
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return Check(name, "FAIL", f"deterministic verifier failed to run: {type(error).__name__}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return Check(name, "FAIL", "deterministic verifier returned malformed JSON")
    if not isinstance(payload, dict):
        return Check(name, "FAIL", "deterministic verifier response is not an object")
    reported_site = str(payload.get("site") or "")
    reported_runtime = str(payload.get("runtime") or "")
    checks = payload.get("checks")
    failures = [
        check
        for check in checks
        if isinstance(check, dict) and check.get("ok") is not True
    ] if isinstance(checks, list) else []
    response_ok = (
        result.returncode == 0
        and payload.get("schema_version") == P4_EXTRACT_VERIFIER_SCHEMA
        and payload.get("ok") is True
        and reported_site == site
        and reported_runtime == runtime
        and isinstance(checks, list)
        and bool(checks)
        and not failures
    )
    if response_ok:
        facts = _mapping(payload.get("facts"))
        rows = facts.get("rows")
        columns = facts.get("columns")
        return Check(name, "PASS", f"re-verified {site} ZIP/CSV semantics ({rows} rows x {columns} columns)")
    if failures:
        first = failures[0]
        failure_name = str(first.get("name") or "unknown check")
        detail = str(first.get("detail") or "failed")
        return Check(name, "FAIL", f"{failure_name}: {detail}")
    stderr = result.stderr.strip()
    suffix = f": {stderr[:200]}" if stderr else ""
    return Check(
        name,
        "FAIL",
        f"deterministic verifier rejected receipt (exit={result.returncode}, site={reported_site or '<missing>'}){suffix}",
    )


def _receipt_timestamp(receipt: Receipt) -> str:
    data = receipt.data
    timestamps = data.get("timestamps", {}) if isinstance(data.get("timestamps"), dict) else {}
    return str(
        data.get("completed_at")
        or data.get("acquired_at")
        or data.get("verified_at")
        or timestamps.get("receipt_written_utc")
        or receipt.path
    )


def _browser_gate(context: Context, stage: str, site: str, runtime: str) -> Gate:
    name = f"{stage}_{site.upper()}"
    candidates = _candidate_receipts(context, stage, site, runtime)
    if not candidates:
        return Gate.from_checks(
            name,
            [Check(name, "INCOMPLETE", f"no {runtime} {site} receipt with runtime/adapter provenance")],
        )
    receipt = max(candidates, key=lambda item: (_receipt_timestamp(item), str(item.path)))
    if not receipt.data:
        return Gate.from_checks(name, [Check(name, "FAIL", f"malformed browser receipt: {receipt.path.name}")])
    checks = [_receipt_status(receipt, "status", "verification", "completion")]
    checks.extend(_browser_adapter_checks(receipt.data, runtime, name))
    artifacts: list[Mapping[str, Any]] = []
    if isinstance(receipt.data.get("artifact"), dict):
        artifacts.append(_artifact_mapping(receipt.data["artifact"]))
    if isinstance(receipt.data.get("artifacts"), list):
        artifacts.extend(_artifact_mapping(item) for item in receipt.data["artifacts"] if isinstance(item, dict))
    if receipt.data.get("artifact_path"):
        artifacts.append(_artifact_mapping(receipt.data, path_key="artifact_path"))
    if not artifacts:
        checks.append(Check(f"{name} artifact", "FAIL", "accepted browser receipt has no artifact record"))
    query = receipt.data.get("query")
    security_code = str(query.get("security_code") or "") or None if isinstance(query, dict) else None
    checks.extend(_verify_artifact(item, receipt.path, context, security_code=security_code) for item in artifacts)

    if stage == "P3" and artifacts:
        checks.append(
            _manifest_check(
                context.run_dir / "manifests/FULLTEXT_MANIFEST.md",
                [artifacts[0]],
                receipt.path,
                context,
                f"{name} manifest",
            )
        )
        verifier = receipt.data.get("verifier")
        if isinstance(verifier, dict):
            checks.append(_bool_check(f"{name} content verifier", verifier.get("ok")))
    if stage == "P4" and artifacts:
        primary = next(
            (item for item in artifacts if _numeric(item, "data_rows", "rows") is not None), artifacts[-1]
        )
        checks.append(
            _manifest_check(
                context.run_dir / "cn-data/DATA_MANIFEST.md",
                [primary],
                receipt.path,
                context,
                f"{name} manifest",
            )
        )
        transport = _mapping(receipt.data.get("download_transport"))
        checks.append(_bool_check(f"{name} UI export", transport.get("ui_export_completed")))
        preview_rows = _nested(receipt.data, "portal_evidence", "preview_rows")
        checks.append(_bool_check(f"{name} preview rows", isinstance(preview_rows, int) and preview_rows > 0))
        checks.append(_p4_semantic_extract_check(receipt, context, runtime, site))
    if runtime == "kimi":
        checks.extend(_kimi_download_checks(name, receipt, artifacts, context))
    for location in (receipt.data, receipt.data.get("security", {}), receipt.data.get("access", {})):
        if isinstance(location, dict):
            for key in (
                "credentials_persisted",
                "credentials_or_cookies_persisted",
                "secrets_or_session_material_persisted",
            ):
                if location.get(key) is True:
                    checks.append(Check(f"{name} security", "FAIL", f"receipt reports {key}=true"))
    return Gate.from_checks(name, checks)


def _p5_shared_gate(context: Context) -> Gate:
    checks: list[Check] = []
    install_path = context.run_dir / "p5/install-receipt.json"
    install, loaded = _load_receipt(install_path, "P5 install receipt")
    checks.append(loaded)
    if install:
        checks.append(_receipt_status(install, "status"))
        manifest = _mapping(install.data.get("manifest"))
        if manifest:
            checks.append(_verify_artifact(_artifact_mapping(manifest), install.path, context))
            resolved = _resolve_path(manifest.get("path"), install.path, context)
            if resolved and resolved.is_file():
                lines = resolved.read_text(encoding="utf-8").splitlines()
                skill_count = sum(line.startswith("skill\t") for line in lines)
                support_count = sum(line.startswith("support\t") for line in lines)
                expected = (manifest.get("skill_count"), manifest.get("support_count"))
                checks.append(
                    _bool_check("P5 install manifest counts", (skill_count, support_count) == expected)
                )
        fs = _mapping(install.data.get("filesystem_verification"))
        checks.extend(
            [
                _bool_check("P5 no broken symlinks", fs.get("broken_symlinks") == 0),
                _bool_check(
                    "P5 exact portable set",
                    _nested(install.data, "selection", "group") == "business-research"
                    and manifest.get("exact_portable_set") is True,
                ),
            ]
        )

    validation_path = context.run_dir / "p5/validation-receipt.json"
    validation, loaded = _load_receipt(validation_path, "P5 validation receipt")
    checks.append(loaded)
    if validation:
        checks.append(_receipt_status(validation, "status"))
        for key in ("mirror", "inventory", "shell_syntax"):
            checks.append(
                _bool_check(f"P5 {key}", _nested(validation.data, key, "result") == "pass")
            )
        checks.extend(
            [
                _bool_check(
                    "P5 skill validation failures",
                    _nested(validation.data, "skill_validation", "failed") == 0,
                ),
                _bool_check("P5 pytest failures", _nested(validation.data, "pytest", "failed") == 0),
            ]
        )
        for raw_path, digest in _mapping(validation.data.get("source_hashes")).items():
            checks.append(
                _verify_artifact({"path": raw_path, "sha256": digest}, validation.path, context)
            )
    return Gate.from_checks("P5", checks)


def _p5_runtime_gate(context: Context, runtime: str, shared: Gate) -> Gate:
    path = context.run_dir / "p5" / f"{runtime}-discovery-receipt.json"
    receipt, loaded = _load_receipt(path, f"P5 {runtime} discovery")
    checks = [Check("P5 shared", shared.status, f"shared P5: {shared.summary}"), loaded]
    if receipt:
        checks.append(_receipt_status(receipt, "status"))
        checks.append(_bool_check(f"P5 {runtime} runtime identity", _normalize_runtime(receipt.data) == runtime))
        checks.extend(
            [
                _bool_check(f"P5 {runtime.capitalize()} exact set", receipt.data.get("exact_portable_set")),
                _bool_check(f"P5 {runtime.capitalize()} discovered count", receipt.data.get("discovered_count") == 24),
            ]
        )
        raw = receipt.data.get("raw_output")
        if isinstance(raw, dict):
            checks.append(_verify_artifact(_artifact_mapping(raw), receipt.path, context))
    return Gate.from_checks("P5", checks)


def _runtime_invocation_gate(context: Context, runtime: str, stage: str) -> Gate:
    candidates: list[Receipt] = []
    for path in sorted(context.run_dir.rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict) or data.get("schema_version") != RUNTIME_INVOCATION_SCHEMA:
            continue
        if _normalize_runtime(data) == runtime and str(data.get("stage") or "").upper() == stage:
            candidates.append(Receipt(path, data))
    name = f"{stage} {runtime} invocation"
    if not candidates:
        return Gate.from_checks(
            name,
            [
                Check(
                    name,
                    "INCOMPLETE",
                    f"no explicit {runtime} canonical-skill invocation receipt for {stage}; "
                    "shared output is not runtime proof",
                )
            ],
        )
    receipt = max(candidates, key=lambda item: (_receipt_timestamp(item), str(item.path)))
    checks = [_receipt_status(receipt, "status")]
    skill = receipt.data.get("skill")
    checks.append(_bool_check(f"{name} skill", isinstance(skill, (str, list)) and bool(skill)))
    evidence = receipt.data.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        checks.append(Check(f"{name} evidence", "FAIL", "runtime invocation receipt has no hashed evidence"))
    else:
        for item in evidence:
            if isinstance(item, dict):
                checks.append(_verify_artifact(_artifact_mapping(item), receipt.path, context))
            else:
                checks.append(Check(f"{name} evidence", "FAIL", "runtime evidence entry is not an object"))
    return Gate.from_checks(name, checks)


def _dependency_check(name: str, gate: Gate) -> Check:
    return Check(name, gate.status, f"{gate.name}: {gate.summary}")


def _runtime_payload(context: Context, runtime: str, shared: Mapping[str, Gate]) -> Mapping[str, object]:
    browser = {
        f"P3_{site.upper()}": _browser_gate(context, "P3", site, runtime) for site in P3_BROWSER_SITES
    }
    browser.update(
        {f"P4_{site.upper()}": _browser_gate(context, "P4", site, runtime) for site in P4_BROWSER_SITES}
    )
    p1_invocation = _runtime_invocation_gate(context, runtime, "P1")
    p2_invocation = _runtime_invocation_gate(context, runtime, "P2")
    p3_invocation = _runtime_invocation_gate(context, runtime, "P3")
    stages = {
        "P1": Gate.from_checks(
            "P1",
            [
                _dependency_check("P1 shared", shared["P1"]),
                _dependency_check("P1 invocation", p1_invocation),
            ],
        ),
        "P2": Gate.from_checks(
            "P2",
            [
                _dependency_check("P2 shared", shared["P2"]),
                _dependency_check("P2 invocation", p2_invocation),
            ],
        ),
        "P3": Gate.from_checks(
            "P3",
            [_dependency_check("P3 shared", shared["P3"]), _dependency_check("P3 invocation", p3_invocation)]
            + [_dependency_check(name, browser[name]) for name in browser if name.startswith("P3_")],
        ),
        "P4": Gate.from_checks(
            "P4", [_dependency_check(name, browser[name]) for name in browser if name.startswith("P4_")]
        ),
        "P5": _p5_runtime_gate(context, runtime, shared["P5"]),
    }
    status = combine_status(gate.status for gate in stages.values())
    return {"status": status, "stages": stages, "browser": browser}


def select_run(evidence_root: Path, run_id: str | None = None) -> Path:
    root = evidence_root.resolve(strict=False)
    if run_id is not None:
        if Path(run_id).name != run_id or run_id in {"", ".", ".."}:
            raise VerificationInputError("--run-id must be one directory name")
        run = root / run_id
        if not run.is_dir():
            raise VerificationInputError(f"run not found: {run_id}")
        return run
    if not root.is_dir():
        raise VerificationInputError(f"evidence root not found: {root}")
    runs = sorted(
        (
            path
            for path in root.iterdir()
            if path.is_dir() and path.name not in RUNTIME_SUBDIR_NAMES
        ),
        key=lambda path: path.name,
    )
    if not runs:
        raise VerificationInputError(f"no evidence runs under: {root}")
    return runs[-1]


def verify_business_e2e(
    repo_root: Path,
    evidence_root: Path,
    run_id: str | None = None,
    runtime: str = "codex",
) -> Report:
    repo = repo_root.resolve(strict=True)
    selected = RUNTIMES if runtime == "all" else (runtime,)
    unknown = next((name for name in selected if name not in RUNTIME_EVIDENCE_SUBDIRS), None)
    if unknown is not None:
        raise VerificationInputError(f"unsupported runtime: {unknown}")
    contexts: dict[str, Context] = {}
    for name in selected:
        subdir = RUNTIME_EVIDENCE_SUBDIRS[name]
        run = select_run(evidence_root / subdir if subdir else evidence_root, run_id)
        try:
            run.resolve().relative_to(repo)
        except ValueError as error:
            raise VerificationInputError("evidence run must be inside --repo-root") from error
        contexts[name] = Context(repo_root=repo, run_dir=run.resolve())
    shared_by_runtime = {
        name: {
            "P1": _p1_gate(context),
            "P2": _p2_gate(context),
            "P3": _p3_shared_gate(context),
            "P5": _p5_shared_gate(context),
        }
        for name, context in contexts.items()
    }
    runtimes = {
        name: _runtime_payload(contexts[name], name, shared_by_runtime[name]) for name in contexts
    }
    primary = "codex" if "codex" in contexts else selected[0]
    primary_run = contexts[primary].run_dir
    status = combine_status(payload["status"] for payload in runtimes.values())  # type: ignore[arg-type]
    return Report(
        run_id=primary_run.name,
        run_path=str(primary_run.relative_to(repo)),
        status=status,
        shared=shared_by_runtime[primary],
        runtimes=runtimes,
    )


def format_human(report: Report) -> str:
    lines = [f"Business E2E {report.run_id}: {report.status}", "", "Shared artifact gates:"]
    for name, gate in report.shared.items():
        lines.append(f"  {name:<3} {gate.status:<10} {gate.summary}")
    for runtime, payload in report.runtimes.items():
        lines.extend(["", f"{runtime.capitalize()} runtime: {payload['status']}"])
        stages = payload["stages"]
        assert isinstance(stages, Mapping)
        for name, gate in stages.items():
            lines.append(f"  {name:<3} {gate.status:<10} {gate.summary}")
        lines.append("  Browser gates:")
        browser = payload["browser"]
        assert isinstance(browser, Mapping)
        for name, gate in browser.items():
            lines.append(f"    {name:<20} {gate.status:<10} {gate.summary}")
    return "\n".join(lines)


def _parser(default_repo: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=default_repo, help="repository root")
    parser.add_argument("--evidence-root", type=Path, help="default: <repo>/.aris/business-e2e")
    parser.add_argument("--run-id", help="explicit run directory name; default: latest lexicographic run")
    parser.add_argument(
        "--runtime",
        choices=(*RUNTIMES, "all"),
        default="codex",
        help="host-runtime gate group to build; kimi evidence is read from "
        "<evidence-root>/kimi/<run-id>, 'all' verifies both runtime trees",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON to stdout instead of human text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    default_repo = Path(__file__).resolve().parents[1]
    args = _parser(default_repo).parse_args(argv)
    evidence_root = args.evidence_root or args.repo_root / ".aris/business-e2e"
    try:
        report = verify_business_e2e(args.repo_root, evidence_root, args.run_id, runtime=args.runtime)
    except (OSError, VerificationInputError) as error:
        print(f"verify_business_e2e: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(format_human(report))
    return 0 if report.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
