#!/usr/bin/env python3
"""Deterministically verify a business-research E2E evidence run.

The verifier is read-only.  It trusts neither prose summaries nor a receipt's
``status`` field alone: accepted artifacts are re-hashed and, where recorded,
their dimensions/page counts are checked.  Runtime evidence is deliberately
not transferable between Codex and Grok.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import shutil
import stat
import struct
import subprocess
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Literal, Mapping, Sequence
from xml.etree import ElementTree as ET


Status = Literal["PASS", "FAIL", "INCOMPLETE"]
PASS_WORDS = {"pass", "passed", "verified", "complete", "completed"}
RUNTIME_INVOCATION_SCHEMA = "aris.business-e2e.runtime-invocation.v1"
P3_SYNTHESIS_SCHEMA = "aris.business-e2e.literature-synthesis.v2"
P3_CANDIDATE_SCHEMA = "aris.business-e2e.p3-synthesis-candidate.v2"
P3_GENERATION_SCHEMA = "aris.business-e2e.p3-generation-record.v1"
P3_ISOLATION_SCHEMA = "aris.business-e2e.p3-isolation-preparation.v1"
P3_EXTERNAL_ACCEPTANCE_SCHEMA = "aris.business-e2e.p3-external-acceptance.v1"
P3_CANDIDATE_VERIFIER_SCHEMA = "aris.business-e2e.p3-candidate-verifier-report.v1"
P3_BUNDLE_TEST_SCHEMA = "aris.business-e2e.p3-bundle-test-report.v1"
P3_PDF_INSPECTION_SCHEMA = "aris.method-harvest.pdf-inspection.v2"
P3_RENDER_EVIDENCE_SCHEMA = "aris.method-harvest.render-evidence.v1"
P3_GROK_FIXED_CORPUS: Mapping[str, tuple[str, int]] = {
    "graham_harvey_popadak_rajgopal_2017": (
        "f69be9aa4373ff67db8a98b9bcb27ff3576067ae82a1337a88e1aaed998847a2",
        79,
    ),
    "zhao_teng_wu_2018": (
        "459e22da3a37ad6bd4823271ddfc4d6c8d027e054a43057b89c6cd0090d9770b",
        19,
    ),
    "duan_2018": (
        "79b6a8b9f2c6f075343f1322c38ff4c6c79abedba8ed963cee5f8a6094a28117",
        67,
    ),
}
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
GROK_CHROME_DEVTOOLS_ADAPTER = "grok_chrome_devtools_mcp"
GROK_CHROME_DEVTOOLS_BINDINGS: Mapping[str, str] = {
    "mcp_server": "browser",
    "implementation": "chrome-devtools-mcp",
    "profile_mode": "dedicated_persistent",
}
P4_EXTRACT_VERIFIER_SCHEMA = "aris.cn-data-bridge.extract-verification.v1"
GROK_BROWSER_SCHEMA_NAMESPACE = "aris.grok-browser-"
GROK_BROWSER_RUNTIME_RECEIPT_SCHEMA = (
    "aris.business-e2e.grok-browser-runtime-receipt.v1"
)
GROK_BROWSER_INTERMEDIATE_SCHEMA_PREFIXES = (
    "aris.grok-browser-candidate.",
    "aris.grok-browser-external-acceptance.",
)
GROK_BROWSER_P3_SITES = frozenset(P3_BROWSER_SITES)
GROK_BROWSER_P4_SITES = frozenset(P4_BROWSER_SITES)
CNRDS_DESCRIPTION_ROW = (
    "股票代码",
    "会计年度",
    "公司类型",
    "申请时间",
    "当年独立申请的发明数量",
    "当年独立申请的实用新型数量",
    "当年独立申请的外观设计数量",
    "当年联合申请的发明数量",
    "当年联合申请的实用新型数量",
    "当年联合申请的外观设计数量",
)
CSMAR_DESCRIPTION_ROW = ("证券代码", "证券简称", "统计截止日期", "报表类型", "资产总计")
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


@dataclass(frozen=True)
class P3CandidateState:
    root: Path
    receipt: Receipt
    generation: Receipt
    bundle_digest: str
    frozen_at: datetime
    candidate_created_at: datetime


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


def _docx_structure_check(path: Path, document: Mapping[str, Any]) -> Check:
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
    if creator != "Yihong Wang" or modifier != "Yihong Wang":
        issues.append("Author/Last Modified By is not Yihong Wang")
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
        if doc_path and doc_path.is_file():
            checks.append(_docx_structure_check(doc_path, document))
        metadata = _mapping(receipt.data.get("metadata"))
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


def _utc_datetime(value: object) -> datetime | None:
    """Parse a strict, timezone-aware UTC timestamp used for evidence ordering."""
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        return None
    return parsed


def _inventory_projection(records: Sequence[Mapping[str, Any]]) -> list[dict[str, object]]:
    return sorted(
        (
            {
                "path": str(record.get("path") or ""),
                "sha256": str(record.get("sha256") or "").lower(),
                "size_bytes": _numeric(record, "size_bytes", "bytes", "byte_size"),
            }
            for record in records
        ),
        key=lambda record: str(record["path"]),
    )


def _inventory_digest(records: Sequence[Mapping[str, Any]]) -> str:
    encoded = json.dumps(
        _inventory_projection(records),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _p3_candidate_root(candidate: Receipt, context: Context) -> Path | None:
    root = _resolve_path(candidate.data.get("candidate_root"), candidate.path, context)
    if root is None or not root.is_dir():
        return None
    expected_parent = (context.run_dir / "grok-workspace" / "p3-synthesis-v2").resolve(strict=False)
    if root.parent != expected_parent:
        return None
    if candidate.path.resolve(strict=False).parent != root / "receipts":
        return None
    if candidate.path.name != "p3-synthesis-grok-v2-candidate.json":
        return None
    return root


def _p3_inventory_checks(
    raw_records: object,
    *,
    candidate: Receipt,
    generation_path: Path,
    root: Path,
    context: Context,
) -> tuple[list[Check], list[Mapping[str, Any]]]:
    label = "P3 frozen artifact inventory"
    if not isinstance(raw_records, list) or not raw_records or not all(
        isinstance(item, dict) for item in raw_records
    ):
        return [Check(label, "FAIL", "frozen_artifacts are absent or malformed")], []
    records = [item for item in raw_records if isinstance(item, dict)]
    projected = _inventory_projection(records)
    paths = [str(item["path"]) for item in projected]
    issues: list[str] = []
    if any(not path for path in paths) or len(paths) != len(set(paths)):
        issues.append("artifact paths are blank or duplicated")
    if any(
        not re.fullmatch(r"[0-9a-f]{64}", str(item["sha256"]))
        or not isinstance(item["size_bytes"], int)
        or isinstance(item["size_bytes"], bool)
        or int(item["size_bytes"]) < 0
        for item in projected
    ):
        issues.append("each frozen artifact requires a valid SHA-256 and nonnegative size_bytes")

    excluded = {candidate.path.resolve(strict=False), generation_path.resolve(strict=False)}
    actual_paths: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            issues.append(f"candidate bundle contains symlink: {path.relative_to(root)}")
            continue
        if path.is_file() and path.resolve(strict=False) not in excluded:
            actual_paths.add(path.relative_to(context.repo_root).as_posix())
    recorded_paths = set(paths)
    if recorded_paths != actual_paths:
        missing = sorted(actual_paths - recorded_paths)
        extra = sorted(recorded_paths - actual_paths)
        issues.append(f"inventory path mismatch; unrecorded={missing}, nonexistent_or_excluded={extra}")

    checks = [
        _verify_artifact(_artifact_mapping(record), candidate.path, context) for record in records
    ]
    for record in records:
        raw_path = record.get("path")
        resolved = _resolve_path(raw_path, candidate.path, context)
        canonical = (
            resolved.relative_to(context.repo_root).as_posix()
            if resolved is not None and resolved.is_relative_to(context.repo_root)
            else None
        )
        if resolved is None or not resolved.is_relative_to(root) or raw_path != canonical:
            issues.append(f"artifact path is not canonical and inside candidate root: {raw_path}")
        if resolved in excluded:
            issues.append(f"self-referential freeze artifact is forbidden: {raw_path}")
    checks.append(
        Check(
            label,
            "FAIL" if issues else "PASS",
            "; ".join(issues) if issues else f"{len(records)} files exactly cover the immutable candidate root",
        )
    )
    return checks, records


def _p3_isolation_checks(
    candidate: Receipt,
    root: Path,
    tag: str,
    context: Context,
) -> list[Check]:
    checks: list[Check] = []
    record = _mapping(candidate.data.get("isolation_preparation"))
    checks.append(_bool_check("P3 isolation artifact reference", _complete_artifact_ref(record)))
    checks.append(_verify_artifact(_artifact_mapping(record), candidate.path, context))
    path = _resolve_path(record.get("path"), candidate.path, context)
    expected_path = root / "inputs" / "isolation-preparation.json"
    if path != expected_path:
        return checks + [
            Check(
                "P3 isolation receipt location",
                "FAIL",
                "isolation preparation must be inputs/isolation-preparation.json",
            )
        ]
    isolation, loaded = _load_receipt(path, "P3 isolation preparation")
    checks.append(loaded)
    if isolation is None:
        return checks
    data = isolation.data
    launch = data.get("launch_command")
    def launch_value(flag: str) -> str | None:
        if not isinstance(launch, list):
            return None
        try:
            index = launch.index(flag)
        except ValueError:
            return None
        return str(launch[index + 1]) if index + 1 < len(launch) else None

    disabled_tools = launch_value("--disallowed-tools")
    launch_ok = (
        isinstance(launch, list)
        and launch_value("--sandbox") == "strict"
        and launch_value("--permission-mode") == "bypassPermissions"
        and launch_value("--cwd") is not None
        and Path(str(launch_value("--cwd"))).resolve(strict=False) == root
        and "--disable-web-search" in launch
        and disabled_tools is not None
        and {
            "web_search",
            "web_fetch",
            "search_tool",
            "use_tool",
            "Agent",
        }.issubset(set(disabled_tools.split(",")))
        and "--no-memory" in launch
        and "--no-subagents" in launch
        and launch_value("--prompt-file") is not None
        and Path(str(launch_value("--prompt-file"))).resolve(strict=False) == root / "PROMPT.md"
    )
    checks.extend(
        [
            _bool_check("P3 isolation schema", data.get("schema_version") == P3_ISOLATION_SCHEMA),
            _bool_check(
                "P3 isolation identity",
                _normalize_runtime(data) == "grok"
                and str(data.get("stage") or "").upper() == "P3"
                and data.get("grok_run_tag") == tag
                and _resolve_path(data.get("candidate_root"), path, context) == root,
            ),
            _bool_check("P3 strict-sandbox launch", launch_ok),
            _bool_check(
                "P3 isolation-generation ordering",
                _utc_datetime(data.get("prepared_at")) is not None
                and _utc_datetime(candidate.data.get("generation_started_at")) is not None
                and _utc_datetime(data.get("prepared_at"))
                <= _utc_datetime(candidate.data.get("generation_started_at")),
            ),
        ]
    )
    for key in (
        "network_tools_disabled",
        "mcp_meta_tools_disabled",
        "memory_disabled",
        "subagents_disabled",
    ):
        checks.append(_bool_check(f"P3 isolation flag {key}", data.get(key)))
    for key in (
        "repository_tests_copied",
        "root_verifier_copied",
        "prior_synthesis_outputs_copied",
    ):
        checks.append(_bool_check(f"P3 isolation flag {key}", data.get(key), False))

    for key in ("minimal_manifest", "prompt", "local_pdf_verifier"):
        artifact = _mapping(data.get(key))
        checks.append(_verify_artifact(_artifact_mapping(artifact), path, context))
        artifact_path = _resolve_path(artifact.get("path"), path, context)
        checks.append(
            _bool_check(
                f"P3 isolation {key} is local",
                artifact_path is not None and artifact_path.is_relative_to(root),
            )
        )
    skills = data.get("skill_snapshot")
    skill_records = [item for item in skills if isinstance(item, dict)] if isinstance(skills, list) else []
    checks.append(_bool_check("P3 isolation skill snapshot present", bool(skill_records)))
    skill_roots: set[str] = set()
    for artifact in skill_records:
        checks.append(_verify_artifact(_artifact_mapping(artifact), path, context))
        skill_path = _resolve_path(artifact.get("path"), path, context)
        if skill_path is not None:
            try:
                skill_roots.add(skill_path.relative_to(root / "skills").parts[0])
            except (ValueError, IndexError):
                skill_roots.add("<outside>")
    checks.append(
        _bool_check(
            "P3 isolation exact skill roots",
            skill_roots == {"method-harvest", "business-lit-review"},
        )
    )

    lineage = data.get("pdf_lineage")
    observed: dict[str, tuple[str, int | None]] = {}
    snapshot_paths: set[Path] = set()
    if isinstance(lineage, list):
        for item in lineage:
            if not isinstance(item, dict):
                continue
            source = _mapping(item.get("source"))
            snapshot = _mapping(item.get("snapshot"))
            checks.extend(
                [
                    _verify_artifact(_artifact_mapping(source), path, context),
                    _verify_artifact(_artifact_mapping(snapshot), path, context),
                    _bool_check(
                        f"P3 isolation byte identity:{item.get('paper_id')}",
                        item.get("byte_identical") is True
                        and source.get("sha256") == snapshot.get("sha256"),
                    ),
                ]
            )
            snapshot_path = _resolve_path(snapshot.get("path"), path, context)
            if snapshot_path is None or not snapshot_path.is_relative_to(root / "artifacts/fulltext"):
                checks.append(
                    Check(
                        f"P3 isolation snapshot:{item.get('paper_id')}",
                        "FAIL",
                        "snapshot is outside candidate artifacts/fulltext",
                    )
                )
            else:
                snapshot_paths.add(snapshot_path)
            observed[str(item.get("paper_id") or "")] = (
                str(snapshot.get("sha256") or "").lower(),
                _numeric(item, "pages"),
            )
    checks.append(_bool_check("P3 isolation fixed PDF snapshots", observed == dict(P3_GROK_FIXED_CORPUS)))

    protected_expected = snapshot_paths | {
        expected_path,
        root / "PROMPT.md",
    }
    for artifact in (
        _mapping(data.get("minimal_manifest")),
        _mapping(data.get("prompt")),
        _mapping(data.get("local_pdf_verifier")),
        *skill_records,
    ):
        artifact_path = _resolve_path(artifact.get("path"), path, context)
        if artifact_path is not None:
            protected_expected.add(artifact_path)
    protected_actual = {
        item.resolve(strict=False)
        for item in root.rglob("*")
        if item.is_file()
        and (
            item.parent == root
            or item.relative_to(root).parts[0] in {"artifacts", "inputs", "skills", "tools"}
        )
    }
    checks.append(
        Check(
            "P3 isolation protected input surface",
            "PASS" if protected_actual == protected_expected else "FAIL",
            "protected input surface exactly matches the preparation receipt"
            if protected_actual == protected_expected
            else (
                "protected input mismatch; added="
                f"{sorted(str(item.relative_to(root)) for item in protected_actual - protected_expected)}, "
                "missing="
                f"{sorted(str(item.relative_to(root)) for item in protected_expected - protected_actual)}"
            ),
        )
    )
    allowed_topology = {
        "PROMPT.md",
        "artifacts",
        "inputs",
        "skills",
        "tools",
        "extracted",
        "literature-v2",
        "receipts",
        "qa",
    }
    unexpected_topology = sorted(
        item.name for item in root.iterdir() if item.name not in allowed_topology
    )
    checks.append(
        _bool_check("P3 isolation candidate topology", not unexpected_topology)
    )

    forbidden = [
        item.relative_to(root).as_posix()
        for item in root.rglob("*")
        if item.is_file()
        and (
            item.relative_to(root).parts[0] == "tests"
            or item.name == "verify_business_e2e.py"
            or "literature-forward-test" in item.relative_to(root).parts
        )
    ]
    checks.append(
        Check(
            "P3 isolation forbidden repository material",
            "PASS" if not forbidden else "FAIL",
            "no tests, root verifier, or prior forward-test outputs are exposed"
            if not forbidden
            else f"forbidden files exposed: {forbidden}",
        )
    )
    return checks


def _p3_candidate_checks(
    candidate: Receipt, context: Context
) -> tuple[Gate, P3CandidateState | None]:
    """Revalidate a blind Grok candidate without trusting its self-reported status."""
    checks: list[Check] = []
    data = candidate.data
    skills = data.get("skills")
    exact_skills = (
        isinstance(skills, list)
        and all(isinstance(skill, str) for skill in skills)
        and set(skills) == {"method-harvest", "business-lit-review"}
    )
    checks.extend(
        [
            _bool_check("P3 candidate schema", data.get("schema_version") == P3_CANDIDATE_SCHEMA),
            _bool_check("P3 candidate Grok runtime", _normalize_runtime(data) == "grok"),
            _bool_check("P3 candidate stage", str(data.get("stage") or "").upper() == "P3"),
            _bool_check(
                "P3 candidate pending status",
                data.get("status") == "candidate_pending_external_acceptance",
            ),
            _bool_check("P3 candidate synthesis mode", data.get("mode") == "fulltext_synthesis"),
            _bool_check(
                "P3 candidate exact skills",
                exact_skills,
            ),
        ]
    )
    for key, expected in (
        ("repository_tests_read_or_run", False),
        ("external_acceptance_pending", True),
        ("prior_codex_synthesis_reused", False),
        ("browser_or_mcp_used", False),
        ("network_acquisition_performed", False),
    ):
        checks.append(_bool_check(f"P3 candidate flag {key}", data.get(key), expected))

    root = _p3_candidate_root(candidate, context)
    if root is None:
        checks.append(
            Check(
                "P3 candidate root",
                "FAIL",
                "candidate_root/path must be one tagged directory under grok-workspace/p3-synthesis-v2",
            )
        )
        return Gate.from_checks("P3 Grok blind candidate", checks), None
    checks.append(Check("P3 candidate root", "PASS", _display_path(root, context)))
    tag = str(data.get("grok_run_tag") or "")
    checks.append(
        _bool_check(
            "P3 candidate tag",
            bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", tag)) and tag == root.name,
        )
    )
    checks.extend(_p3_isolation_checks(candidate, root, tag, context))

    generation_record = _mapping(data.get("generation_record"))
    checks.append(
        _bool_check("P3 generation artifact reference", _complete_artifact_ref(generation_record))
    )
    generation_path = _resolve_path(generation_record.get("path"), candidate.path, context)
    checks.append(_verify_artifact(_artifact_mapping(generation_record), candidate.path, context))
    if generation_path is None or generation_path != root / "qa" / "grok-generation-record.json":
        checks.append(
            Check(
                "P3 generation record location",
                "FAIL",
                "generation record must be qa/grok-generation-record.json in the candidate root",
            )
        )
        return Gate.from_checks("P3 Grok blind candidate", checks), None
    generation, loaded = _load_receipt(generation_path, "P3 generation record")
    checks.append(loaded)
    if generation is None:
        return Gate.from_checks("P3 Grok blind candidate", checks), None
    generation_data = generation.data
    checks.extend(
        [
            _bool_check(
                "P3 generation schema",
                generation_data.get("schema_version") == P3_GENERATION_SCHEMA,
            ),
            _bool_check("P3 generation Grok runtime", _normalize_runtime(generation_data) == "grok"),
            _bool_check(
                "P3 generation identity",
                str(generation_data.get("stage") or "").upper() == "P3"
                and generation_data.get("grok_run_tag") == tag,
            ),
        ]
    )
    for key in (
        "repository_tests_read_or_run",
        "prior_codex_synthesis_reused",
        "browser_or_mcp_used",
        "network_acquisition_performed",
    ):
        checks.append(_bool_check(f"P3 generation flag {key}", generation_data.get(key), False))

    started_at = _utc_datetime(generation_data.get("generation_started_at"))
    frozen_at = _utc_datetime(generation_data.get("frozen_at"))
    candidate_created_at = _utc_datetime(data.get("candidate_receipt_created_at"))
    ordered = (
        started_at is not None
        and frozen_at is not None
        and candidate_created_at is not None
        and started_at <= frozen_at <= candidate_created_at
        and data.get("generation_started_at") == generation_data.get("generation_started_at")
        and data.get("frozen_at") == generation_data.get("frozen_at")
    )
    checks.append(_bool_check("P3 candidate freeze ordering", ordered))

    inventory_checks, candidate_inventory = _p3_inventory_checks(
        data.get("frozen_artifacts"),
        candidate=candidate,
        generation_path=generation.path,
        root=root,
        context=context,
    )
    checks.extend(inventory_checks)
    generation_inventory = generation_data.get("frozen_artifacts")
    generation_records = (
        [item for item in generation_inventory if isinstance(item, dict)]
        if isinstance(generation_inventory, list)
        else []
    )
    inventory_equal = _inventory_projection(candidate_inventory) == _inventory_projection(
        generation_records
    )
    checks.append(_bool_check("P3 candidate-generation inventory binding", inventory_equal))
    digest = _inventory_digest(candidate_inventory) if candidate_inventory else ""
    checks.append(
        _bool_check(
            "P3 candidate bundle digest",
            bool(candidate_inventory)
            and re.fullmatch(r"[0-9a-f]{64}", digest) is not None
            and data.get("bundle_digest") == digest
            and generation_data.get("bundle_digest") == digest,
        )
    )

    synthesis = data.get("synthesis")
    if not isinstance(synthesis, dict):
        checks.append(Check("P3 candidate synthesis", "FAIL", "embedded synthesis v2 is absent"))
    else:
        candidate_context = Context(repo_root=context.repo_root, run_dir=root)
        synthesis_checks, _ = _p3_synthesis_checks(Receipt(candidate.path, synthesis), candidate_context)
        checks.extend(synthesis_checks)
        inputs = synthesis.get("inputs")
        observed: dict[str, tuple[str, int | None]] = {}
        if isinstance(inputs, list):
            for item in inputs:
                if not isinstance(item, dict):
                    continue
                pdf = _mapping(item.get("pdf"))
                observed[str(item.get("paper_id") or "")] = (
                    str(pdf.get("sha256") or "").lower(),
                    _numeric(pdf, "pages", "page_count"),
                )
        checks.append(
            _bool_check(
                "P3 candidate fixed corpus",
                observed == dict(P3_GROK_FIXED_CORPUS),
            )
        )
        declaration = _mapping(data.get("fixed_corpus"))
        checks.append(
            _bool_check(
                "P3 candidate fixed-corpus declaration",
                declaration.get("closed") is True
                and declaration.get("paper_count") == len(P3_GROK_FIXED_CORPUS)
                and declaration.get("paper_ids") == list(P3_GROK_FIXED_CORPUS),
            )
        )
        acceptance = _mapping(_mapping(synthesis.get("outputs")).get("acceptance_report"))
        _, acceptance_text, acceptance_error = _read_text_artifact(
            acceptance,
            candidate.path,
            candidate_context,
            "P3 blind candidate acceptance report",
        )
        if acceptance_error:
            checks.append(acceptance_error)
        else:
            assert acceptance_text is not None
            report_ok = (
                "pending external acceptance" in acceptance_text.lower()
                and "repository tests and root verifiers were not read or run" in acceptance_text.lower()
                and "zero failures, skips, or xfails" not in acceptance_text.lower()
            )
            checks.append(_bool_check("P3 candidate truthful pending report", report_ok))

    gate = Gate.from_checks("P3 Grok blind candidate", checks)
    if gate.status != "PASS" or frozen_at is None or candidate_created_at is None:
        return gate, None
    return (
        gate,
        P3CandidateState(
            root=root,
            receipt=candidate,
            generation=generation,
            bundle_digest=digest,
            frozen_at=frozen_at,
            candidate_created_at=candidate_created_at,
        ),
    )


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
    values = [data.get("executor_runtime"), data.get("host_runtime"), data.get("runtime")]
    for value in values:
        normalized = str(value or "").lower()
        if "codex" in normalized:
            return "codex"
        if "grok" in normalized:
            return "grok"
    adapter = str(data.get("adapter") or "").lower()
    if adapter == "codex_native_chrome":
        return "codex"
    if adapter in {"grok_chrome_mcp", GROK_CHROME_DEVTOOLS_ADAPTER}:
        return "grok"
    return None


def _browser_adapter_checks(
    data: Mapping[str, Any], runtime: str, gate_name: str
) -> list[Check]:
    """Validate one browser adapter identity without changing legacy semantics."""

    adapter = str(data.get("adapter") or "")
    allowed = (
        {"codex_native_chrome"}
        if runtime == "codex"
        else {"chrome-mcp", "grok_chrome_mcp", GROK_CHROME_DEVTOOLS_ADAPTER}
    )
    accepted = adapter in allowed
    checks = [
        Check(
            f"{gate_name} adapter",
            "PASS" if accepted else "FAIL",
            f"adapter={adapter}" if accepted else f"wrong {runtime} adapter: {adapter or '<missing>'}",
        )
    ]
    if adapter == GROK_CHROME_DEVTOOLS_ADAPTER:
        for field, expected in GROK_CHROME_DEVTOOLS_BINDINGS.items():
            observed = data.get(field)
            checks.append(
                Check(
                    f"{gate_name} adapter binding:{field}",
                    "PASS" if observed == expected else "FAIL",
                    f"{field}={observed!r}, expected={expected!r}",
                )
            )
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
        schema_version = data.get("schema_version")
        if isinstance(schema_version, str) and schema_version.startswith(
            GROK_BROWSER_INTERMEDIATE_SCHEMA_PREFIXES
        ):
            # These are frozen hand-off records for the external acceptor, not
            # business success receipts.  They deliberately carry stage, site,
            # and runtime identity, so discovery must exclude them by schema.
            continue
        data_match = _normalize_site(data) == site and _normalize_runtime(data) == runtime
        gate_text = " ".join(str(data.get(key) or "") for key in ("stage", "gate", "acceptance_id")).lower()
        stage_match = stage.lower() in lower_name or stage.lower() in gate_text
        if data_match and stage_match:
            candidates.append(Receipt(path, data))
    return candidates


def _strict_json_object(path: Path) -> tuple[Mapping[str, Any] | None, str | None]:
    def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON field: {key}")
            result[key] = value
        return result

    try:
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=no_duplicates)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        return None, f"{type(error).__name__}: {error}"
    if not isinstance(payload, Mapping):
        return None, "JSON root is not an object"
    return payload, None


def _canonical_json_sha256(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _promoted_workspace_path(
    raw: object, context: Context
) -> tuple[Path | None, str | None]:
    if not isinstance(raw, str) or not raw or raw.startswith("~"):
        return None, "path is missing or home-relative"
    if "\\" in raw or "?" in raw or "#" in raw or "://" in raw:
        return None, "path contains a forbidden URL/path component"
    relative = PurePosixPath(raw)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        return None, "path is not canonical workspace-relative"
    current = context.repo_root
    for part in relative.parts:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except OSError as error:
            return None, f"path component is unavailable: {type(error).__name__}"
        if stat.S_ISLNK(mode):
            return None, "path traverses a symlink"
    try:
        resolved = current.resolve(strict=True)
        resolved.relative_to(context.repo_root)
    except (OSError, ValueError):
        return None, "path is missing or outside the repository"
    return resolved, None


def _promoted_lineage_json(
    receipt: Receipt,
    context: Context,
    key: str,
) -> tuple[Mapping[str, Any] | None, Path | None, list[Check]]:
    name = f"promoted lineage:{key}"
    lineage = _mapping(receipt.data.get("lineage"))
    record = _mapping(lineage.get(key))
    checks: list[Check] = []
    if set(record) != {"path", "sha256", "size_bytes", "mtime_ns"}:
        return None, None, [Check(name, "FAIL", "lineage file reference has wrong fields")]
    path, path_error = _promoted_workspace_path(record.get("path"), context)
    if path is None or not path.is_file():
        return None, path, [Check(name, "FAIL", path_error or "lineage file is missing")]
    try:
        path.relative_to(context.run_dir)
    except ValueError:
        return None, path, [Check(name, "FAIL", "lineage file is outside the evidence run")]
    expected_hash = str(record.get("sha256") or "")
    expected_size = _numeric(record, "size_bytes")
    expected_mtime = _numeric(record, "mtime_ns")
    intact = (
        re.fullmatch(r"[0-9a-f]{64}", expected_hash) is not None
        and expected_size == path.stat().st_size
        and expected_mtime == path.stat().st_mtime_ns
        and _sha256(path) == expected_hash
    )
    checks.append(
        Check(
            name,
            "PASS" if intact else "FAIL",
            "hash/size/mtime match the promoted lineage"
            if intact
            else "lineage hash, size, or mtime does not match",
        )
    )
    payload, error = _strict_json_object(path)
    checks.append(
        Check(
            f"{name} JSON",
            "PASS" if payload is not None else "FAIL",
            "strict JSON object loaded" if payload is not None else f"invalid lineage JSON: {error}",
        )
    )
    return payload, path, checks


def _promoted_expected_row(
    value: object, headers: Sequence[str]
) -> tuple[str, ...] | None:
    if isinstance(value, Mapping):
        if set(value) != set(headers):
            return None
        cells = [value[header] for header in headers]
    elif isinstance(value, list) and len(value) == len(headers):
        cells = value
    else:
        return None
    if any(cell is not None and not isinstance(cell, str) for cell in cells):
        return None
    return tuple("" if cell is None else str(cell) for cell in cells)


def _promoted_p4_table_checks(
    receipt: Receipt,
    context: Context,
    spec: Mapping[str, Any],
    acceptance: Mapping[str, Any],
) -> list[Check]:
    name = f"{receipt.data.get('stage')}_{str(receipt.data.get('site')).upper()} promoted table"
    checks: list[Check] = []
    artifacts = receipt.data.get("artifacts")
    records = [item for item in artifacts if isinstance(item, Mapping)] if isinstance(artifacts, list) else []
    archives = [record for record in records if record.get("role") == "accepted_download"]
    tables = [record for record in records if record.get("role") == "accepted_table"]
    if len(archives) != 1 or len(tables) != 1:
        return [Check(name, "FAIL", "promoted P4 receipt must bind one archive and one table")]
    archive_record, table_record = archives[0], tables[0]
    archive_path = _resolve_path(archive_record.get("path"), receipt.path, context)
    table_path = _resolve_path(table_record.get("path"), receipt.path, context)
    if archive_path is None or table_path is None or not archive_path.is_file() or not table_path.is_file():
        return [Check(name, "FAIL", "promoted archive or table is missing")]
    artifact_spec = _mapping(spec.get("artifact"))
    p4 = _mapping(spec.get("p4"))
    headers_raw = p4.get("expected_headers")
    exact_rows_raw = p4.get("exact_rows")
    member = p4.get("archive_member")
    if (
        artifact_spec.get("format") != "zip"
        or p4.get("member_format") != "csv"
        or not isinstance(member, str)
        or not isinstance(headers_raw, list)
        or not headers_raw
        or any(not isinstance(item, str) or not item for item in headers_raw)
        or not isinstance(exact_rows_raw, list)
    ):
        return [Check(name, "FAIL", "frozen P4 spec is not the promotable ZIP/CSV contract")]
    headers = tuple(headers_raw)
    expected_rows: list[tuple[str, ...]] = []
    for value in exact_rows_raw:
        row = _promoted_expected_row(value, headers)
        if row is None:
            return [Check(name, "FAIL", "frozen P4 exact row is malformed")]
        expected_rows.append(row)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            matching = [info for info in archive.infolist() if info.filename == member and not info.is_dir()]
            unsafe = [
                info
                for info in archive.infolist()
                if info.flag_bits & 0x1
                or ((info.external_attr >> 16) & 0o170000) == stat.S_IFLNK
                or PurePosixPath(info.filename).is_absolute()
                or any(part in {"", ".", ".."} for part in PurePosixPath(info.filename).parts)
            ]
            member_bytes = archive.read(matching[0]) if len(matching) == 1 and not unsafe else None
    except (OSError, RuntimeError, zipfile.BadZipFile, KeyError):
        member_bytes = None
    table_bytes = table_path.read_bytes()
    byte_identical = member_bytes is not None and member_bytes == table_bytes
    checks.append(
        Check(
            f"{name} ZIP member",
            "PASS" if byte_identical else "FAIL",
            "landed CSV is byte-identical to the one safe accepted ZIP member"
            if byte_identical
            else "landed CSV does not equal one safe accepted ZIP member",
        )
    )
    rows: list[list[str]] | None = None
    if byte_identical:
        for encoding in ("utf-8-sig", "gb18030"):
            try:
                text = table_bytes.decode(encoding)
                parsed = list(csv.reader(io.StringIO(text, newline=""), strict=True))
            except (UnicodeDecodeError, csv.Error):
                continue
            if parsed and all(len(row) == len(parsed[0]) for row in parsed):
                rows = parsed
                break
    if rows is None:
        checks.append(Check(f"{name} CSV", "FAIL", "promoted CSV is not accepted rectangular text"))
        return checks
    actual_header = tuple(rows[0])
    business_rows = [tuple(row) for row in rows[1:]]
    site = str(receipt.data.get("site") or "")
    description = CNRDS_DESCRIPTION_ROW if site == "cnrds" else CSMAR_DESCRIPTION_ROW
    if business_rows and business_rows[0] == description:
        business_rows = business_rows[1:]
    exact_slice = actual_header == headers and Counter(business_rows) == Counter(expected_rows)
    checks.append(
        Check(
            f"{name} exact slice",
            "PASS" if exact_slice else "FAIL",
            f"headers={len(actual_header)}, business_rows={len(business_rows)}",
        )
    )
    promotion = _mapping(receipt.data.get("promotion"))
    receipt_dimensions = (
        promotion.get("archive_member") == member
        and promotion.get("table_path") == table_record.get("path")
        and promotion.get("data_rows") == len(business_rows)
        and promotion.get("columns") == len(headers)
    )
    checks.append(
        Check(
            f"{name} receipt dimensions",
            "PASS" if receipt_dimensions else "FAIL",
            "promotion member/path/dimensions match the reopened table"
            if receipt_dimensions
            else "promotion member/path/dimensions differ from the reopened table",
        )
    )
    stage_report = _mapping(_mapping(acceptance.get("verifier_report")).get("stage_content"))
    report_bound = (
        stage_report.get("status") == "PASS"
        and stage_report.get("headers") == list(headers)
        and stage_report.get("archive_member") == member
        and stage_report.get("matched_exact_row_occurrences") == len(expected_rows)
        and stage_report.get("required_exact_row_occurrences") == len(expected_rows)
    )
    checks.append(
        Check(
            f"{name} external report",
            "PASS" if report_bound else "FAIL",
            "external stage verifier is bound to the same member/header/exact rows"
            if report_bound
            else "external stage verifier is not bound to the promoted table",
        )
    )
    return checks


def _promoted_browser_receipt_checks(
    receipt: Receipt,
    context: Context,
    stage: str,
    site: str,
) -> list[Check]:
    name = f"{stage}_{site.upper()} promoted runtime"
    data = receipt.data
    required = {
        "schema_version",
        "receipt_kind",
        "status",
        "runtime",
        "adapter",
        "mcp_server",
        "implementation",
        "profile_mode",
        "stage",
        "site",
        "artifact_landed_at",
        "completed_at",
        "lineage",
        "external_verification",
        "promotion",
        "verifier",
        "artifact" if stage == "P3" else "artifacts",
    }
    checks: list[Check] = []
    exact_shape = set(data) == required
    checks.append(
        Check(
            f"{name} schema",
            "PASS" if exact_shape else "FAIL",
            "exact promoted runtime receipt shape"
            if exact_shape
            else f"promoted receipt fields differ: {sorted(set(data) ^ required)}",
        )
    )
    expected_location = (
        context.run_dir / "receipts"
        if stage == "P3"
        else context.run_dir / "cn-data" / "receipts"
    )
    identity_ok = (
        data.get("schema_version") == GROK_BROWSER_RUNTIME_RECEIPT_SCHEMA
        and data.get("receipt_kind") == "externally_promoted_grok_browser_runtime"
        and data.get("status") == "passed"
        and data.get("runtime") == "grok"
        and data.get("stage") == stage
        and data.get("site") == site
        and receipt.path.parent.resolve(strict=False) == expected_location.resolve(strict=False)
    )
    checks.append(
        Check(
            f"{name} identity",
            "PASS" if identity_ok else "FAIL",
            "stage/site/runtime/location are exact" if identity_ok else "promoted identity or location mismatch",
        )
    )
    if any(key in data for key in ("query", "portal_evidence", "download_transport")):
        checks.append(Check(f"{name} observation boundary", "FAIL", "promoter synthesized portal evidence"))
    candidate, candidate_path, candidate_checks = _promoted_lineage_json(
        receipt, context, "candidate"
    )
    spec, spec_path, spec_checks = _promoted_lineage_json(
        receipt, context, "acceptance_spec"
    )
    acceptance, acceptance_path, acceptance_checks = _promoted_lineage_json(
        receipt, context, "external_acceptance"
    )
    checks.extend(candidate_checks + spec_checks + acceptance_checks)
    if candidate is None or spec is None or acceptance is None:
        return checks
    candidate_artifact = _mapping(candidate.get("artifact"))
    spec_artifact = _mapping(spec.get("artifact"))
    receipt_artifacts = (
        [data.get("artifact")]
        if stage == "P3"
        else data.get("artifacts") if isinstance(data.get("artifacts"), list) else []
    )
    records = [item for item in receipt_artifacts if isinstance(item, Mapping)]
    accepted_records = [
        item
        for item in records
        if item.get("role") in {"accepted_pdf", "accepted_download"}
    ]
    accepted_record = accepted_records[0] if len(accepted_records) == 1 else {}
    artifact_path, _ = _promoted_workspace_path(candidate_artifact.get("path"), context)
    exact_bindings = {
        "runtime": "grok",
        "adapter": GROK_CHROME_DEVTOOLS_ADAPTER,
        **GROK_CHROME_DEVTOOLS_BINDINGS,
    }
    candidate_binding_ok = all(candidate.get(key) == value for key, value in exact_bindings.items())
    candidate_shape_ok = set(candidate) == {
        "schema_version",
        *exact_bindings,
        "stage",
        "site",
        "acceptance_spec_sha256",
        "artifact",
    } and set(candidate_artifact) == {"path", "format", "size_bytes", "mtime_ns", "sha256"}
    spec_shape_ok = set(spec) == {
        "schema_version",
        "stage",
        "site",
        "artifact",
        "p3" if stage == "P3" else "p4",
    } and set(spec_artifact) == {"path", "format", "min_bytes"}
    artifact_bound = (
        candidate.get("schema_version") == "aris.grok-browser-candidate.v1"
        and spec.get("schema_version") == "aris.grok-browser-acceptance-spec.v1"
        and candidate_shape_ok
        and spec_shape_ok
        and candidate_binding_ok
        and candidate.get("stage") == spec.get("stage") == stage
        and candidate.get("site") == spec.get("site") == site
        and candidate.get("acceptance_spec_sha256") == (_sha256(spec_path) if spec_path else None)
        and candidate_artifact.get("path") == spec_artifact.get("path") == accepted_record.get("path")
        and candidate_artifact.get("format") == spec_artifact.get("format") == accepted_record.get("detected_format")
        and candidate_artifact.get("sha256") == accepted_record.get("sha256")
        and candidate_artifact.get("size_bytes") == accepted_record.get("size_bytes")
        and artifact_path is not None
        and artifact_path.is_file()
        and str(candidate_artifact.get("mtime_ns") or "").isdigit()
        and int(str(candidate_artifact.get("mtime_ns") or "0")) == artifact_path.stat().st_mtime_ns
        and accepted_record.get("mtime_ns") == artifact_path.stat().st_mtime_ns
    )
    if artifact_bound and artifact_path is not None:
        try:
            relative = artifact_path.relative_to(context.run_dir)
        except ValueError:
            artifact_bound = False
        else:
            if stage == "P3":
                prefix = Path("grok-workspace") / "artifacts" / "fulltext" / site
                artifact_bound = relative.parts[: len(prefix.parts)] == prefix.parts
            else:
                prefix = Path("cn-data") / "raw" / site
                version = relative.parts[len(prefix.parts)] if len(relative.parts) > len(prefix.parts) else ""
                artifact_bound = (
                    relative.parts[: len(prefix.parts)] == prefix.parts
                    and re.fullmatch(r"\d{4}-\d{2}-\d{2}_grok_v[1-9]\d*", version) is not None
                )
    checks.append(
        Check(
            f"{name} candidate/spec artifact binding",
            "PASS" if artifact_bound else "FAIL",
            "candidate, spec, receipt, runtime-owned path, and landed file agree"
            if artifact_bound
            else "candidate/spec/receipt artifact binding mismatch",
        )
    )
    report = _mapping(acceptance.get("verifier_report"))
    report_hash = _canonical_json_sha256(report)
    inventory = _mapping(acceptance.get("hash_inventory"))
    lineage = _mapping(data.get("lineage"))
    immutability = _mapping(acceptance.get("immutability"))
    acceptance_required = {
        "schema_version",
        "record_kind",
        "status",
        "acceptance_scope",
        "generated_at",
        *exact_bindings,
        "stage",
        "site",
        "candidate_sha256",
        "acceptance_spec_sha256",
        "artifact_sha256",
        "hash_inventory",
        "immutability",
        "verifier_report_sha256",
        "verifier_report",
        "business_success_receipt_created",
        "manifest_modified",
        "spec_modified",
    }
    acceptance_shape_ok = set(acceptance) == acceptance_required
    acceptance_binding_ok = all(
        acceptance.get(key) == value for key, value in exact_bindings.items()
    )
    acceptance_bound = (
        acceptance.get("schema_version") == "aris.grok-browser-external-acceptance.v1"
        and acceptance_shape_ok
        and acceptance_binding_ok
        and acceptance.get("record_kind") == "external_candidate_acceptance"
        and acceptance.get("status") == "passed"
        and acceptance.get("acceptance_scope") == "frozen_candidate_only"
        and acceptance.get("stage") == stage
        and acceptance.get("site") == site
        and acceptance.get("candidate_sha256") == (_sha256(candidate_path) if candidate_path else None)
        and acceptance.get("acceptance_spec_sha256") == (_sha256(spec_path) if spec_path else None)
        and acceptance.get("artifact_sha256") == accepted_record.get("sha256")
        and inventory.get("candidate") == lineage.get("candidate")
        and inventory.get("spec") == lineage.get("acceptance_spec")
        and inventory.get("artifact")
        == {
            "path": accepted_record.get("path"),
            "sha256": accepted_record.get("sha256"),
            "size_bytes": accepted_record.get("size_bytes"),
            "mtime_ns": accepted_record.get("mtime_ns"),
        }
        and acceptance.get("verifier_report_sha256") == report_hash
        and acceptance.get("business_success_receipt_created") is False
        and acceptance.get("manifest_modified") is False
        and acceptance.get("spec_modified") is False
        and set(immutability)
        == {
            "candidate_unchanged",
            "spec_unchanged",
            "artifact_unchanged",
            "download_verifier_unchanged",
        }
        and all(value is True for value in immutability.values())
    )
    verifier_inventory = _mapping(inventory.get("download_verifier"))
    verifier_relative = "skills/browser-session-bridge/scripts/verify_download.py"
    verifier_path = context.repo_root / verifier_relative
    try:
        verifier_mode = verifier_path.lstat().st_mode
    except OSError:
        verifier_mode = 0
    verifier_bound = (
        verifier_inventory.get("path") == verifier_relative
        and verifier_path.is_file()
        and not stat.S_ISLNK(verifier_mode)
        and verifier_inventory.get("sha256") == _sha256(verifier_path)
        and verifier_inventory.get("size_bytes") == verifier_path.stat().st_size
    )
    external = _mapping(data.get("external_verification"))
    verifier = _mapping(data.get("verifier"))
    promoted_report_bound = (
        external.get("acceptance_schema") == "aris.grok-browser-external-acceptance.v1"
        and external.get("verifier_report_sha256") == report_hash
        and external.get("download_ok") is True
        and external.get("stage_content_status") == "PASS"
        and external.get("reverified_during_promotion") is True
        and verifier.get("ok") is True
        and verifier.get("source") == "external_candidate_acceptance"
        and verifier.get("report_sha256") == report_hash
    )
    checks.extend(
        [
            Check(
                f"{name} external acceptance",
                "PASS" if acceptance_bound else "FAIL",
                "external acceptance exactly binds frozen candidate/spec/artifact/report"
                if acceptance_bound
                else "external acceptance lineage is inconsistent",
            ),
            Check(
                f"{name} download verifier",
                "PASS" if verifier_bound else "FAIL",
                "external download verifier implementation hash matches"
                if verifier_bound
                else "external download verifier implementation changed",
            ),
            Check(
                f"{name} promotion verification",
                "PASS" if promoted_report_bound else "FAIL",
                "promotion re-verification is bound to the external report"
                if promoted_report_bound
                else "promotion verification flags/report hash mismatch",
            ),
        ]
    )
    promotion = _mapping(data.get("promotion"))
    expected_manifest = (
        context.run_dir / "manifests" / "FULLTEXT_MANIFEST.md"
        if stage == "P3"
        else context.run_dir / "cn-data" / "DATA_MANIFEST.md"
    )
    manifest_path = _resolve_path(promotion.get("manifest_path"), receipt.path, context)
    manifest_hash = str(promotion.get("manifest_row_sha256") or "")
    manifest_line_bound = False
    if manifest_path == expected_manifest and manifest_path.is_file() and re.fullmatch(r"[0-9a-f]{64}", manifest_hash):
        try:
            manifest_line_bound = any(
                hashlib.sha256(line.encode("utf-8")).hexdigest() == manifest_hash
                for line in manifest_path.read_text(encoding="utf-8").splitlines()
            )
        except (OSError, UnicodeError):
            manifest_line_bound = False
    observation_boundary = (
        promotion.get("promoter") == "scripts/promote_grok_browser_candidate.py"
        and promotion.get("portal_observations_synthesized") is False
    )
    checks.extend(
        [
            Check(
                f"{name} manifest row",
                "PASS" if manifest_line_bound else "FAIL",
                "exact promoted manifest row is present"
                if manifest_line_bound
                else "promoted manifest row hash is absent",
            ),
            Check(
                f"{name} observation boundary",
                "PASS" if observation_boundary else "FAIL",
                "no portal observations were synthesized"
                if observation_boundary
                else "promotion observation boundary is absent",
            ),
        ]
    )
    if stage == "P3":
        stage_report = _mapping(report.get("stage_content"))
        matches = stage_report.get("identity_matches")

        def all_true(value: object) -> bool:
            if isinstance(value, Mapping):
                return bool(value) and all(all_true(item) for item in value.values())
            return value is True

        p3_bound = (
            stage_report.get("status") == "PASS"
            and isinstance(stage_report.get("pages"), int)
            and stage_report.get("pages") == accepted_record.get("pages")
            and stage_report.get("raw_tool_output_recorded") is False
            and all_true(matches)
        )
        checks.append(
            Check(
                f"{name} PDF identity",
                "PASS" if p3_bound else "FAIL",
                "external PDF identity/page checks bind the promoted artifact"
                if p3_bound
                else "external PDF identity/page checks are incomplete",
            )
        )
    else:
        checks.extend(_promoted_p4_table_checks(receipt, context, spec, acceptance))
    return checks


def _p4_semantic_extract_check(receipt: Receipt, context: Context, runtime: str, site: str) -> Check:
    """Re-open the P4 ZIP/CSV and verify the frozen slice outside receipt prose."""

    name = f"P4_{site.upper()} deterministic extract"
    if runtime not in {"codex", "grok"}:
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
    schema_version = receipt.data.get("schema_version")
    if schema_version == GROK_BROWSER_RUNTIME_RECEIPT_SCHEMA:
        checks = [_receipt_status(receipt, "status")]
        checks.extend(_browser_adapter_checks(receipt.data, runtime, name))
        checks.extend(_promoted_browser_receipt_checks(receipt, context, stage, site))
        artifacts: list[Mapping[str, Any]] = []
        if isinstance(receipt.data.get("artifact"), dict):
            artifacts.append(_artifact_mapping(receipt.data["artifact"]))
        if isinstance(receipt.data.get("artifacts"), list):
            artifacts.extend(
                _artifact_mapping(item)
                for item in receipt.data["artifacts"]
                if isinstance(item, dict)
            )
        if not artifacts:
            checks.append(Check(f"{name} artifact", "FAIL", "promoted receipt has no artifact record"))
        checks.extend(_verify_artifact(item, receipt.path, context) for item in artifacts)
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
        if stage == "P4" and artifacts:
            primary = next(
                (item for item in artifacts if item.get("role") == "accepted_table"),
                artifacts[-1],
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
        return Gate.from_checks(name, checks)
    if isinstance(schema_version, str) and schema_version.startswith(GROK_BROWSER_SCHEMA_NAMESPACE):
        return Gate.from_checks(
            name,
            [
                Check(
                    name,
                    "FAIL",
                    f"unsupported Grok browser intermediate schema: {schema_version}",
                )
            ],
        )
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
    filename = "codex-discovery-receipt.json" if runtime == "codex" else "grok-discovery-receipt.json"
    path = context.run_dir / "p5" / filename
    receipt, loaded = _load_receipt(path, f"P5 {runtime} discovery")
    checks = [Check("P5 shared", shared.status, f"shared P5: {shared.summary}"), loaded]
    if receipt:
        checks.append(_receipt_status(receipt, "status"))
        checks.append(_bool_check(f"P5 {runtime} runtime identity", _normalize_runtime(receipt.data) == runtime))
        if runtime == "codex":
            checks.extend(
                [
                    _bool_check("P5 Codex exact set", receipt.data.get("exact_portable_set")),
                    _bool_check("P5 Codex discovered count", receipt.data.get("discovered_count") == 24),
                ]
            )
            raw = receipt.data.get("raw_output")
            if isinstance(raw, dict):
                checks.append(_verify_artifact(_artifact_mapping(raw), receipt.path, context))
        else:
            inspect = _mapping(receipt.data.get("inspect"))
            mcp = _mapping(_nested(receipt.data, "mcp", "chrome_mcp"))
            checks.extend(
                [
                    _bool_check("P5 Grok exact set", inspect.get("exact_portable_set")),
                    _bool_check("P5 Grok project count", inspect.get("project_source_count") == 24),
                    _bool_check(
                        "P5 Grok chrome-mcp healthy",
                        mcp.get("status") == "healthy" and mcp.get("tools_discovered", 0) > 0,
                    ),
                ]
            )
    return Gate.from_checks("P5", checks)


def _same_artifact(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    projected = _inventory_projection([left, right])
    return (
        all(
            re.fullmatch(r"[0-9a-f]{64}", str(item["sha256"])) is not None
            and isinstance(item["size_bytes"], int)
            and not isinstance(item["size_bytes"], bool)
            and int(item["size_bytes"]) >= 0
            for item in projected
        )
        and _inventory_projection([left]) == _inventory_projection([right])
    )


def _p3_grok_external_checks(
    wrapper: Receipt,
    context: Context,
) -> list[Check]:
    checks: list[Check] = []
    data = wrapper.data
    candidate_record = _mapping(data.get("candidate_receipt"))
    generation_record = _mapping(data.get("generation_record"))
    external_record = _mapping(data.get("external_acceptance_receipt"))
    verifier_report_record = _mapping(data.get("candidate_verifier_report"))
    bundle_report_record = _mapping(data.get("bundle_test_report"))
    dedicated = {
        "candidate": candidate_record,
        "generation": generation_record,
        "external_acceptance": external_record,
        "candidate_verifier_report": verifier_report_record,
        "bundle_test_report": bundle_report_record,
    }
    for label, record in dedicated.items():
        if not record:
            checks.append(Check(f"P3 Grok {label}", "FAIL", "dedicated artifact binding is absent"))
        else:
            checks.append(
                _bool_check(f"P3 Grok {label} complete reference", _complete_artifact_ref(record))
            )
            checks.append(_verify_artifact(_artifact_mapping(record), wrapper.path, context))

    candidate_path = _resolve_path(candidate_record.get("path"), wrapper.path, context)
    if candidate_path is None:
        return checks
    candidate, loaded = _load_receipt(candidate_path, "P3 Grok candidate receipt")
    checks.append(loaded)
    if candidate is None:
        return checks
    candidate_gate, candidate_state = _p3_candidate_checks(candidate, context)
    checks.append(_dependency_check("P3 Grok candidate revalidation", candidate_gate))
    if candidate_state is None:
        return checks
    checks.append(
        _bool_check(
            "P3 wrapper generation binding",
            _same_artifact(generation_record, _mapping(candidate.data.get("generation_record"))),
        )
    )

    external_path = _resolve_path(external_record.get("path"), wrapper.path, context)
    verifier_report_path = _resolve_path(verifier_report_record.get("path"), wrapper.path, context)
    bundle_report_path = _resolve_path(bundle_report_record.get("path"), wrapper.path, context)
    if external_path is None or verifier_report_path is None or bundle_report_path is None:
        return checks
    expected_external_root = (
        context.run_dir / "receipts" / "p3-grok-external" / candidate_state.root.name
    ).resolve(strict=False)
    location_ok = (
        external_path == expected_external_root / "external-acceptance.json"
        and verifier_report_path == expected_external_root / "candidate-verifier.json"
        and bundle_report_path == expected_external_root / "bundle-tests.json"
        and not external_path.is_relative_to(candidate_state.root)
    )
    checks.append(_bool_check("P3 external evidence locations", location_ok))

    external, loaded = _load_receipt(external_path, "P3 external acceptance receipt")
    checks.append(loaded)
    verifier_report, verifier_loaded = _load_receipt(
        verifier_report_path, "P3 candidate verifier report"
    )
    bundle_report, bundle_loaded = _load_receipt(bundle_report_path, "P3 bundle test report")
    checks.extend([verifier_loaded, bundle_loaded])
    if external is None or verifier_report is None or bundle_report is None:
        return checks

    current_candidate_sha = _sha256(candidate.path)
    external_data = external.data
    checks.extend(
        [
            _bool_check(
                "P3 external acceptance schema",
                external_data.get("schema_version") == P3_EXTERNAL_ACCEPTANCE_SCHEMA,
            ),
            _bool_check("P3 external acceptance status", external_data.get("status") == "pass"),
            _bool_check(
                "P3 external acceptance identity",
                _normalize_runtime(external_data) == "grok"
                and str(external_data.get("stage") or "").upper() == "P3"
                and external_data.get("grok_run_tag") == candidate_state.root.name,
            ),
            _bool_check(
                "P3 external candidate binding",
                _same_artifact(_mapping(external_data.get("candidate_receipt")), candidate_record),
            ),
            _bool_check(
                "P3 external generation binding",
                _same_artifact(_mapping(external_data.get("generation_record")), generation_record),
            ),
            _bool_check(
                "P3 external verifier-report binding",
                _same_artifact(
                    _mapping(external_data.get("candidate_verifier_report")), verifier_report_record
                ),
            ),
            _bool_check(
                "P3 external bundle-report binding",
                _same_artifact(_mapping(external_data.get("bundle_test_report")), bundle_report_record),
            ),
        ]
    )
    for key in (
        "candidate_hash_unchanged",
        "bundle_digest_unchanged",
        "repository_tests_run_externally",
        "general_verifier_run_externally",
        "candidate_remained_immutable",
    ):
        checks.append(_bool_check(f"P3 external flag {key}", external_data.get(key)))
    checks.append(
        _bool_check(
            "P3 external pre/post hash binding",
            external_data.get("candidate_sha256_before") == current_candidate_sha
            and external_data.get("candidate_sha256_after") == current_candidate_sha
            and external_data.get("bundle_digest_before") == candidate_state.bundle_digest
            and external_data.get("bundle_digest_after") == candidate_state.bundle_digest,
        )
    )

    acceptance_started = _utc_datetime(external_data.get("acceptance_started_at"))
    acceptance_completed = _utc_datetime(external_data.get("acceptance_completed_at"))
    wrapper_created = _utc_datetime(data.get("wrapper_created_at"))
    checks.append(
        _bool_check(
            "P3 external acceptance ordering",
            acceptance_started is not None
            and acceptance_completed is not None
            and wrapper_created is not None
            and candidate_state.candidate_created_at <= acceptance_started <= acceptance_completed <= wrapper_created,
        )
    )

    verifier_data = verifier_report.data
    verifier_checks = verifier_data.get("checks")
    verifier_completed = _utc_datetime(verifier_data.get("verified_at"))
    checks.append(
        _bool_check(
            "P3 external general verifier result",
            verifier_data.get("schema_version") == P3_CANDIDATE_VERIFIER_SCHEMA
            and verifier_data.get("status") == "PASS"
            and verifier_data.get("candidate_sha256") == current_candidate_sha
            and verifier_data.get("bundle_digest") == candidate_state.bundle_digest
            and isinstance(verifier_checks, list)
            and bool(verifier_checks)
            and acceptance_started is not None
            and acceptance_completed is not None
            and verifier_completed is not None
            and acceptance_started <= verifier_completed <= acceptance_completed
            and all(
                isinstance(item, dict) and item.get("status") == "PASS"
                for item in verifier_checks
            ),
        )
    )
    bundle_data = bundle_report.data
    counts = _mapping(bundle_data.get("counts"))
    bundle_started = _utc_datetime(bundle_data.get("started_at"))
    bundle_completed = _utc_datetime(bundle_data.get("completed_at"))
    command = bundle_data.get("command")
    junit_record = _mapping(bundle_data.get("junit_report"))
    output_record = _mapping(bundle_data.get("command_output"))
    checks.extend(
        [
            _verify_artifact(_artifact_mapping(junit_record), bundle_report.path, context),
            _verify_artifact(_artifact_mapping(output_record), bundle_report.path, context),
        ]
    )
    junit_path = _resolve_path(junit_record.get("path"), bundle_report.path, context)
    junit_counts, junit_error = (
        _junit_counts(junit_path) if junit_path is not None and junit_path.is_file() else (None, "missing")
    )
    checks.append(
        Check(
            "P3 external JUnit recomputation",
            "PASS" if junit_error is None and junit_counts == dict(counts) else "FAIL",
            "JUnit counts independently match the structured bundle-test report"
            if junit_error is None and junit_counts == dict(counts)
            else f"JUnit mismatch: {junit_error or f'{junit_counts} != {dict(counts)}'}",
        )
    )
    command_ok = (
        isinstance(command, list)
        and len(command) >= 5
        and command[1:3] == ["-m", "pytest"]
        and "tests/test_business_literature_pipeline_e2e.py" in command
        and any(str(part).startswith("--junitxml=") for part in command)
    )
    checks.append(
        _bool_check(
            "P3 external real-bundle tests",
            bundle_data.get("schema_version") == P3_BUNDLE_TEST_SCHEMA
            and bundle_data.get("status") == "PASS"
            and bundle_data.get("candidate_sha256") == current_candidate_sha
            and bundle_data.get("bundle_digest") == candidate_state.bundle_digest
            and bundle_data.get("test_file") == "tests/test_business_literature_pipeline_e2e.py"
            and bundle_data.get("returncode") == 0
            and bundle_data.get("candidate_root")
            == candidate_state.root.relative_to(context.repo_root).as_posix()
            and _nested(bundle_data, "environment", "ARIS_P3_BLIND_CANDIDATE") == "1"
            and _nested(bundle_data, "environment", "ARIS_BUSINESS_LITERATURE_RUN_ROOT")
            == candidate_state.root.relative_to(context.repo_root).as_posix()
            and command_ok
            and acceptance_started is not None
            and acceptance_completed is not None
            and bundle_started is not None
            and bundle_completed is not None
            and acceptance_started <= bundle_started <= bundle_completed <= acceptance_completed
            and _numeric(counts, "tests") is not None
            and (_numeric(counts, "tests") or 0) > 0
            and _numeric(counts, "failures") == 0
            and _numeric(counts, "errors") == 0
            and _numeric(counts, "skipped") == 0
            and _numeric(counts, "xfailed") == 0,
        )
    )
    return checks


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
    if runtime == "grok" and stage == "P3":
        exact_skill_chain = (
            isinstance(skill, list)
            and all(isinstance(item, str) for item in skill)
            and set(skill) == {"method-harvest", "business-lit-review"}
        )
        checks.append(
            _bool_check(
                "P3 Grok exact skill chain",
                exact_skill_chain,
            )
        )
        checks.extend(_p3_grok_external_checks(receipt, context))
        return Gate.from_checks(name, checks)
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
    runs = sorted((path for path in root.iterdir() if path.is_dir()), key=lambda path: path.name)
    if not runs:
        raise VerificationInputError(f"no evidence runs under: {root}")
    return runs[-1]


def verify_business_e2e(repo_root: Path, evidence_root: Path, run_id: str | None = None) -> Report:
    repo = repo_root.resolve(strict=True)
    run = select_run(evidence_root, run_id)
    try:
        run.resolve().relative_to(repo)
    except ValueError as error:
        raise VerificationInputError("evidence run must be inside --repo-root") from error
    context = Context(repo_root=repo, run_dir=run.resolve())
    shared = {
        "P1": _p1_gate(context),
        "P2": _p2_gate(context),
        "P3": _p3_shared_gate(context),
        "P5": _p5_shared_gate(context),
    }
    runtimes = {runtime: _runtime_payload(context, runtime, shared) for runtime in ("codex", "grok")}
    status = combine_status(payload["status"] for payload in runtimes.values())  # type: ignore[arg-type]
    return Report(
        run_id=run.name,
        run_path=str(run.relative_to(repo)),
        status=status,
        shared=shared,
        runtimes=runtimes,
    )


def verify_p3_candidate(repo_root: Path, candidate_path: Path) -> Mapping[str, object]:
    repo = repo_root.resolve(strict=True)
    candidate_file = candidate_path.resolve(strict=True)
    try:
        relative = candidate_file.relative_to(repo)
    except ValueError as error:
        raise VerificationInputError("P3 candidate must be inside --repo-root") from error
    parts = relative.parts
    if len(parts) < 4 or parts[:2] != (".aris", "business-e2e"):
        raise VerificationInputError("P3 candidate must belong to a business-e2e run")
    run_dir = repo.joinpath(*parts[:3])
    if not run_dir.is_dir():
        raise VerificationInputError("P3 candidate run directory is missing")
    candidate, loaded = _load_receipt(candidate_file, "P3 candidate receipt")
    if candidate is None:
        gate = Gate.from_checks("P3 Grok blind candidate", [loaded])
        state = None
    else:
        gate, state = _p3_candidate_checks(
            candidate,
            Context(repo_root=repo, run_dir=run_dir),
        )
    return {
        "schema_version": P3_CANDIDATE_VERIFIER_SCHEMA,
        "status": gate.status,
        "verified_at": datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z"),
        "candidate_path": relative.as_posix(),
        "candidate_sha256": _sha256(candidate_file),
        "bundle_digest": state.bundle_digest if state is not None else None,
        "checks": [check.as_dict() for check in gate.checks],
    }


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
        "--p3-candidate",
        type=Path,
        help="verify one frozen Grok P3 candidate instead of the aggregate business-e2e run",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON to stdout instead of human text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    default_repo = Path(__file__).resolve().parents[1]
    args = _parser(default_repo).parse_args(argv)
    if args.p3_candidate is not None:
        if args.evidence_root is not None or args.run_id is not None:
            print(
                "verify_business_e2e: --p3-candidate cannot be combined with --evidence-root/--run-id",
                file=sys.stderr,
            )
            return 2
        try:
            payload = verify_p3_candidate(args.repo_root, args.p3_candidate)
        except (OSError, VerificationInputError) as error:
            print(f"verify_business_e2e: {error}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"P3 Grok blind candidate: {payload['status']}")
            for check in payload["checks"]:
                assert isinstance(check, Mapping)
                print(f"  {check['status']:<10} {check['name']}: {check['summary']}")
        return 0 if payload["status"] == "PASS" else 1
    evidence_root = args.evidence_root or args.repo_root / ".aris/business-e2e"
    try:
        report = verify_business_e2e(args.repo_root, evidence_root, args.run_id)
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
