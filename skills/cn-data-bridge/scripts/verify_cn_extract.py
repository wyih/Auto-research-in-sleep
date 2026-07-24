#!/usr/bin/env python3
"""Independently verify the fixed P4 CNRDS/CSMAR acceptance extracts.

This verifier is intentionally narrower than a generic download checker.  It
re-opens the landed ZIP and CSV, compares the inner member with the separately
landed CSV, and re-evaluates the frozen P4 slice instead of trusting receipt
row counts or mismatch counters.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import stat
import sys
import zipfile
import zlib
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any, Literal, Mapping, Sequence


Runtime = Literal["codex", "grok"]
Site = Literal["cnrds", "csmar"]

SCHEMA_VERSION = "aris.cn-data-bridge.extract-verification.v1"
GROK_CHROME_DEVTOOLS_ADAPTER = "grok_chrome_devtools_mcp"
EGO_LITE_ADAPTER = "ego_lite_task_space"
GROK_ADAPTERS = frozenset(
    {"grok_chrome_mcp", GROK_CHROME_DEVTOOLS_ADAPTER, EGO_LITE_ADAPTER}
)
GROK_CHROME_DEVTOOLS_BINDINGS: Mapping[str, str] = {
    "mcp_server": "browser",
    "implementation": "chrome-devtools-mcp",
    "profile_mode": "dedicated_persistent",
}
EGO_LITE_BINDINGS: Mapping[str, str] = {
    "mcp_server": "none",
    "implementation": "ego-browser",
    "profile_mode": "shared_login_isolated_task_space",
}
MAX_ARCHIVE_MEMBERS = 100
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
MAX_SINGLE_MEMBER_BYTES = 128 * 1024 * 1024
MAX_CSV_BYTES = 8 * 1024 * 1024
MAX_COMPRESSION_RATIO = 1_000
MAX_DOWNLOAD_AGE = timedelta(hours=2)
FUTURE_SLOP = timedelta(minutes=5)
START_SLOP = timedelta(seconds=5)

CNRDS_HEADER = (
    "Scode",
    "Year",
    "Ftyp",
    "Aplctm",
    "Invia",
    "Umia",
    "Desia",
    "Invja",
    "Umja",
    "Desja",
)
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
CNRDS_COMPANY_TYPES = frozenset({"上市公司本身", "集团公司合计"})
CSMAR_HEADER = ("Stkcd", "ShortName", "Accper", "Typrep", "A001000000")
CSMAR_DESCRIPTION_ROW = ("证券代码", "证券简称", "统计截止日期", "报表类型", "资产总计")


@dataclass(frozen=True)
class VerificationCheck:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class VerificationReport:
    schema_version: str
    ok: bool
    site: str
    runtime: str
    receipt_path: str
    checks: tuple[VerificationCheck, ...]
    facts: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "ok": self.ok,
            "site": self.site,
            "runtime": self.runtime,
            "receipt_path": self.receipt_path,
            "checks": [asdict(check) for check in self.checks],
            "facts": dict(self.facts),
        }


class Audit:
    """Collect deterministic checks while keeping the public API small."""

    def __init__(self) -> None:
        self._checks: list[VerificationCheck] = []

    def check(self, name: str, condition: bool, detail: str) -> bool:
        self._checks.append(VerificationCheck(name=name, ok=bool(condition), detail=detail))
        return bool(condition)

    @property
    def checks(self) -> tuple[VerificationCheck, ...]:
        return tuple(self._checks)

    @property
    def ok(self) -> bool:
        return bool(self._checks) and all(check.ok for check in self._checks)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _receipt_start(data: Mapping[str, Any]) -> datetime | None:
    timestamps = _mapping(data.get("timestamps"))
    for value in (
        data.get("started_at"),
        data.get("run_started_at"),
        data.get("download_started_at"),
        timestamps.get("started_at"),
        timestamps.get("run_started_at"),
        timestamps.get("download_started_at"),
    ):
        parsed = _parse_timestamp(value)
        if parsed is not None:
            return parsed
    return None


def _normalize_site(data: Mapping[str, Any]) -> Site | None:
    value = str(data.get("site") or data.get("source") or "").strip().lower()
    if "cnrds" in value:
        return "cnrds"
    if "csmar" in value:
        return "csmar"
    return None


def _verify_runtime_adapter(
    data: Mapping[str, Any], expected_runtime: Runtime, audit: Audit
) -> None:
    """Verify an exact adapter identity and any identity-specific bindings."""

    adapter = str(data.get("adapter") or "")
    allowed = (
        frozenset({"codex_native_chrome"})
        if expected_runtime == "codex"
        else GROK_ADAPTERS
    )
    audit.check(
        "runtime adapter",
        adapter in allowed,
        f"adapter={adapter!r}, expected_one_of={sorted(allowed)!r}",
    )
    if adapter == GROK_CHROME_DEVTOOLS_ADAPTER:
        for field, expected in GROK_CHROME_DEVTOOLS_BINDINGS.items():
            observed = data.get(field)
            audit.check(
                f"runtime adapter binding:{field}",
                observed == expected,
                f"{field}={observed!r}, expected={expected!r}",
            )
    if adapter == EGO_LITE_ADAPTER:
        for field, expected in EGO_LITE_BINDINGS.items():
            observed = data.get(field)
            audit.check(
                f"runtime adapter binding:{field}",
                observed == expected,
                f"{field}={observed!r}, expected={expected!r}",
            )
        task_space_isolated = data.get("task_space_isolated")
        audit.check(
            "ego lite isolated task space",
            task_space_isolated is True,
            f"task_space_isolated={task_space_isolated!r}",
        )


def _resolve_artifact_path(
    raw: object, receipt_path: Path, repo_root: Path, run_dir: Path
) -> tuple[Path | None, str | None]:
    if not isinstance(raw, str) or not raw.strip() or raw.startswith("~"):
        return None, "artifact path is missing"
    given = Path(raw)
    candidates = (
        (given,)
        if given.is_absolute()
        else (receipt_path.parent / given, run_dir / given, repo_root / given)
    )
    existing: list[Path] = []
    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if resolved not in existing:
            existing.append(resolved)
    if not existing:
        return None, "artifact does not exist"
    if len(existing) != 1:
        return None, "artifact path is ambiguous across receipt/run/repository roots"
    resolved = existing[0]
    try:
        resolved.relative_to(repo_root)
    except ValueError:
        return None, "artifact resolves outside repository"
    if not resolved.is_file():
        return None, "artifact is not a regular file"
    return resolved, None


def _record_format(record: Mapping[str, Any]) -> str:
    detected = str(record.get("detected_format") or "").strip().lower()
    if detected:
        return detected
    raw_path = str(record.get("path") or "")
    return Path(raw_path).suffix.lower().lstrip(".")


def _select_record(
    artifacts: Sequence[Mapping[str, Any]], expected_format: str, audit: Audit
) -> Mapping[str, Any] | None:
    selected = [record for record in artifacts if _record_format(record) == expected_format]
    audit.check(
        f"one {expected_format} artifact",
        len(selected) == 1,
        f"found {len(selected)} {expected_format} artifact record(s)",
    )
    return selected[0] if len(selected) == 1 else None


def _verify_record(
    record: Mapping[str, Any], path: Path, label: str, max_bytes: int, audit: Audit
) -> bytes | None:
    expected_hash = str(record.get("sha256") or "").strip().lower()
    expected_size = record.get("size_bytes", record.get("bytes", record.get("byte_size")))
    valid_hash = re.fullmatch(r"[0-9a-f]{64}", expected_hash) is not None
    audit.check(f"{label} hash recorded", valid_hash, "receipt contains a full SHA-256")
    audit.check(
        f"{label} size recorded",
        isinstance(expected_size, int) and not isinstance(expected_size, bool) and expected_size >= 0,
        f"recorded size={expected_size!r}",
    )
    actual_size = path.stat().st_size
    if not audit.check(
        f"{label} bounded size",
        actual_size <= max_bytes,
        f"actual bytes={actual_size}, maximum={max_bytes}",
    ):
        return None
    try:
        data = path.read_bytes()
    except OSError as error:
        audit.check(f"{label} readable", False, f"read failed: {type(error).__name__}")
        return None
    actual_hash = _sha256_bytes(data)
    audit.check(
        f"{label} SHA-256",
        valid_hash and actual_hash == expected_hash,
        f"actual sha256={actual_hash}",
    )
    audit.check(
        f"{label} byte size",
        isinstance(expected_size, int) and len(data) == expected_size,
        f"actual bytes={len(data)}",
    )
    audit.check(f"{label} nonempty", bool(data), f"actual bytes={len(data)}")
    return data


def _safe_member_name(name: str) -> bool:
    if not name or "\x00" in name or "\\" in name or name.startswith(("/", "~")):
        return False
    if re.match(r"^[A-Za-z]:", name):
        return False
    parts = PurePosixPath(name).parts
    return bool(parts) and all(part not in {"", ".", ".."} for part in parts)


def _read_matching_csv_member(zip_path: Path, csv_path: Path, audit: Audit) -> bytes | None:
    if zip_path.stat().st_size > MAX_ARCHIVE_BYTES:
        audit.check("ZIP readable", False, f"ZIP exceeds {MAX_ARCHIVE_BYTES} byte acceptance limit")
        return None
    try:
        with zipfile.ZipFile(zip_path) as archive:
            infos = archive.infolist()
            member_count_ok = audit.check(
                "ZIP member count bounded",
                0 < len(infos) <= MAX_ARCHIVE_MEMBERS,
                f"members={len(infos)}",
            )
            canonical_names: set[str] = set()
            safe = member_count_ok
            total_size = 0
            for info in infos:
                canonical = str(PurePosixPath(info.filename))
                mode = info.external_attr >> 16
                member_safe = (
                    _safe_member_name(info.filename)
                    and canonical not in canonical_names
                    and not (mode and stat.S_ISLNK(mode))
                    and not (info.flag_bits & 0x1)
                    and info.file_size <= MAX_SINGLE_MEMBER_BYTES
                )
                if not info.is_dir():
                    total_size += info.file_size
                    ratio = info.file_size / max(info.compress_size, 1)
                    member_safe = member_safe and ratio <= MAX_COMPRESSION_RATIO
                canonical_names.add(canonical)
                safe = safe and member_safe
            safe = safe and total_size <= MAX_ARCHIVE_UNCOMPRESSED_BYTES
            audit.check(
                "ZIP members safe",
                safe,
                f"members={len(infos)}, uncompressed_bytes={total_size}",
            )
            all_csv_members = [
                info
                for info in infos
                if not info.is_dir()
                and PurePosixPath(info.filename).suffix.lower() == ".csv"
            ]
            csv_members = [
                info
                for info in all_csv_members
                if PurePosixPath(info.filename).name == csv_path.name
            ]
            audit.check(
                "ZIP contains exact landed CSV",
                len(all_csv_members) == len(csv_members) == 1,
                f"CSV members={len(all_csv_members)}, matching members={len(csv_members)}",
            )
            if not safe:
                audit.check("ZIP CRC", False, "CRC scan skipped because member safety checks failed")
                return None
            bad_member = archive.testzip()
            audit.check("ZIP CRC", bad_member is None, f"bad_member={bad_member!r}")
            if bad_member is not None or len(csv_members) != 1:
                return None
            member = csv_members[0]
            if member.file_size > MAX_CSV_BYTES:
                audit.check(
                    "ZIP CSV member bounded size",
                    False,
                    f"CSV member bytes={member.file_size}, maximum={MAX_CSV_BYTES}",
                )
                return None
            return archive.read(member)
    except (OSError, EOFError, RuntimeError, zipfile.BadZipFile, zipfile.LargeZipFile, zlib.error) as error:
        audit.check("ZIP readable", False, f"ZIP validation failed: {type(error).__name__}")
        return None


def _parse_csv(data: bytes, site: Site, audit: Audit) -> list[list[str]] | None:
    if b"\x00" in data:
        audit.check("CSV text encoding", False, "CSV contains NUL bytes")
        return None
    encodings = ("utf-8-sig", "gb18030") if site == "cnrds" else ("utf-8-sig",)
    text: str | None = None
    detected_encoding = ""
    for encoding in encodings:
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        detected_encoding = encoding
        break
    if text is None:
        audit.check(
            "CSV text encoding",
            False,
            f"CSV is not one of the accepted encodings: {', '.join(encodings)}",
        )
        return None
    try:
        rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    except csv.Error as error:
        audit.check("CSV parse", False, f"strict CSV parse failed: {type(error).__name__}")
        return None
    audit.check("CSV text encoding", True, f"CSV parsed as {detected_encoding}")
    if not rows:
        audit.check("CSV nonempty rows", False, "CSV has no rows")
        return None
    columns = len(rows[0])
    rectangular = columns > 0 and all(len(row) == columns for row in rows)
    audit.check("CSV rectangular", rectangular, f"physical_rows={len(rows)}, columns={columns}")
    return rows if rectangular else None


def _temporary_url_persisted(
    data: Mapping[str, Any], transport: Mapping[str, Any]
) -> object:
    values = [
        mapping.get("temporary_url_persisted")
        for mapping in (transport, data, _mapping(data.get("security")))
        if "temporary_url_persisted" in mapping
    ]
    if any(value is True for value in values):
        return True
    if any(value is False for value in values):
        return False
    return None


def _verify_cnrds(
    data: Mapping[str, Any], rows: list[list[str]], audit: Audit
) -> Mapping[str, Any]:
    query = _mapping(data.get("query"))
    audit.check(
        "CNRDS exact header",
        tuple(rows[0]) == CNRDS_HEADER,
        f"actual_columns={len(rows[0])}",
    )
    description_ok = len(rows) >= 2 and tuple(rows[1]) == CNRDS_DESCRIPTION_ROW
    audit.check("CNRDS description row", description_ok, "vendor description row matches 10 fields")
    data_rows = rows[2:] if description_ok else rows[1:]
    audit.check("CNRDS row count", len(data_rows) == 2, f"data_rows={len(data_rows)}")
    module = str(query.get("module") or "")
    audit.check(
        "CNRDS table identity",
        "CIRD" in module and query.get("table") == "上市公司专利申请情况",
        f"module={module!r}, table={query.get('table')!r}",
    )
    code = str(query.get("security_code") or "")
    audit.check("CNRDS frozen security", code == "000001", f"query security_code={code!r}")
    audit.check(
        "CNRDS frozen dates",
        query.get("date_start") == "2020-01-01" and query.get("date_end") == "2020-12-31",
        f"date_start={query.get('date_start')!r}, date_end={query.get('date_end')!r}",
    )
    selected_fields = query.get("selected_fields", query.get("fields"))
    field_selection_ok = (
        selected_fields == list(CNRDS_HEADER)
        if isinstance(selected_fields, list)
        else query.get("selected_field_count") == len(CNRDS_HEADER)
    )
    audit.check(
        "CNRDS field selection",
        field_selection_ok,
        f"selected_fields={selected_fields!r}, "
        f"selected_field_count={query.get('selected_field_count')!r}",
    )
    row_codes = [row[0] for row in data_rows]
    row_years = [row[1] for row in data_rows]
    row_types = [row[2] for row in data_rows]
    audit.check("CNRDS code slice", bool(data_rows) and set(row_codes) == {code}, f"codes={sorted(set(row_codes))}")
    audit.check("CNRDS year slice", bool(data_rows) and set(row_years) == {"2020"}, f"years={sorted(set(row_years))}")
    audit.check(
        "CNRDS company types",
        len(row_types) == 2 and set(row_types) == CNRDS_COMPANY_TYPES,
        f"company_types={sorted(set(row_types))}",
    )
    keys = [(row[0], row[1], row[2]) for row in data_rows]
    audit.check("CNRDS row grain", len(keys) == len(set(keys)) == 2, f"unique_keys={len(set(keys))}")
    numeric_ok = all(
        value == "" or (value.isascii() and value.isdigit())
        for row in data_rows
        for value in row[4:]
    )
    audit.check("CNRDS count fields", numeric_ok, "six count fields are blank or non-negative integers")

    portal = _mapping(data.get("portal_evidence"))
    preview_codes = portal.get("preview_codes")
    preview_years = portal.get("preview_years")
    company_types = portal.get("company_types")
    audit.check(
        "CNRDS preview row evidence",
        portal.get("preview_rows") == len(data_rows),
        f"preview_rows={portal.get('preview_rows')!r}",
    )
    preview_code_ok = preview_codes == ["000001"] or portal.get("preview_code") == "000001"
    preview_year_ok = preview_years == [2020] or portal.get("preview_year") == 2020
    audit.check("CNRDS preview code evidence", preview_code_ok, f"preview_codes={preview_codes!r}")
    audit.check("CNRDS preview year evidence", preview_year_ok, f"preview_years={preview_years!r}")
    audit.check(
        "CNRDS preview company-type evidence",
        isinstance(company_types, list) and set(company_types) == CNRDS_COMPANY_TYPES,
        f"company_types={company_types!r}",
    )
    audit.check(
        "CNRDS export queue evidence",
        portal.get("queue_status") == "压缩完成"
        or portal.get("queue_compression_complete") is True,
        f"queue_status={portal.get('queue_status')!r}, "
        f"queue_compression_complete={portal.get('queue_compression_complete')!r}",
    )
    transport = _mapping(data.get("download_transport"))
    audit.check("CNRDS UI export", transport.get("ui_export_completed") is True, "ui_export_completed must be true")
    audit.check(
        "CNRDS temporary URL hygiene",
        _temporary_url_persisted(data, transport) is False,
        "temporary_url_persisted must be false",
    )
    return {
        "rows": len(data_rows),
        "columns": len(CNRDS_HEADER),
        "codes": sorted(set(row_codes)),
        "years": sorted(set(row_years)),
        "company_types": sorted(set(row_types)),
    }


def _verify_csmar(
    data: Mapping[str, Any], rows: list[list[str]], audit: Audit
) -> Mapping[str, Any]:
    query = _mapping(data.get("query"))
    audit.check(
        "CSMAR exact header",
        tuple(rows[0]) == CSMAR_HEADER,
        f"actual_columns={len(rows[0])}",
    )
    has_description_row = len(rows) >= 2 and tuple(rows[1]) == CSMAR_DESCRIPTION_ROW
    data_rows = rows[2:] if has_description_row else rows[1:]
    audit.check(
        "CSMAR metadata-row classification",
        not rows[1:] or has_description_row or rows[1][0] == "000001",
        f"description_row_present={has_description_row}",
    )
    audit.check("CSMAR row count", len(data_rows) == 1, f"data_rows={len(data_rows)}")
    audit.check(
        "CSMAR table identity",
        query.get("module") == "财务报表"
        and query.get("table") == "资产负债表"
        and query.get("table_id") == "FS_Combas",
        f"module={query.get('module')!r}, table={query.get('table')!r}, "
        f"table_id={query.get('table_id')!r}",
    )
    audit.check(
        "CSMAR frozen security",
        query.get("security_code") == "000001",
        f"security_code={query.get('security_code')!r}",
    )
    audit.check(
        "CSMAR frozen date",
        query.get("date_start") == "2020-12-31" and query.get("date_end") == "2020-12-31",
        f"date_start={query.get('date_start')!r}, date_end={query.get('date_end')!r}",
    )
    audit.check(
        "CSMAR report condition",
        str(query.get("condition") or "").replace(" ", "") == "Typrep=A",
        f"condition={query.get('condition')!r}",
    )
    audit.check(
        "CSMAR selected fields",
        query.get("selected_fields") == list(CSMAR_HEADER),
        f"selected_fields={query.get('selected_fields')!r}",
    )
    row = data_rows[0] if len(data_rows) == 1 else [""] * len(CSMAR_HEADER)
    audit.check("CSMAR code slice", row[0] == "000001", f"Stkcd={row[0]!r}")
    audit.check("CSMAR date slice", row[2] == "2020-12-31", f"Accper={row[2]!r}")
    audit.check("CSMAR report type", row[3] == "A", f"Typrep={row[3]!r}")
    amount = row[4]
    try:
        parsed_amount = Decimal(amount)
        amount_ok = bool(amount.strip()) and parsed_amount.is_finite()
    except InvalidOperation:
        amount_ok = False
    audit.check("CSMAR total assets nonempty", amount_ok, "A001000000 is a finite numeric value")
    audit.check("CSMAR row grain", len(data_rows) == 1, "one security-date-report row")

    portal = _mapping(data.get("portal_evidence"))
    audit.check(
        "CSMAR preview row evidence",
        portal.get("preview_rows") == 1,
        f"preview_rows={portal.get('preview_rows')!r}",
    )
    audit.check(
        "CSMAR preview code evidence",
        portal.get("preview_code") == row[0],
        f"preview_code={portal.get('preview_code')!r}",
    )
    audit.check(
        "CSMAR preview date evidence",
        portal.get("preview_date") == row[2],
        f"preview_date={portal.get('preview_date')!r}",
    )
    audit.check(
        "CSMAR preview report evidence",
        portal.get("preview_report_type") == row[3],
        f"preview_report_type={portal.get('preview_report_type')!r}",
    )
    audit.check(
        "CSMAR preview asset evidence",
        portal.get("preview_total_assets_nonempty") is True and amount_ok,
        "preview and CSV both report a nonempty asset value",
    )
    result_page = _mapping(portal.get("result_page") or portal.get("sdownload_summary"))
    export_rows = portal.get("export_summary_rows")
    if not isinstance(export_rows, int) or isinstance(export_rows, bool):
        export_rows = result_page.get(
            "export_summary_rows", result_page.get("record_count", result_page.get("rows"))
        )
    export_format = str(
        portal.get("export_summary_format")
        or result_page.get("export_summary_format")
        or result_page.get("format")
        or result_page.get("output_format")
        or ""
    )
    explicit_result = (
        portal.get("result_page_verified") is True
        or result_page.get("verified") is True
        or result_page.get("reconciled") is True
    )
    legacy_structured_result = export_rows == 1 and "csv" in export_format.lower()
    audit.check(
        "CSMAR result-page evidence",
        explicit_result or legacy_structured_result,
        f"export_summary_rows={export_rows!r}, export_summary_format={export_format!r}",
    )
    audit.check("CSMAR result-page row count", export_rows == 1, f"export_summary_rows={export_rows!r}")
    audit.check(
        "CSMAR result-page format",
        "csv" in export_format.lower(),
        f"export_summary_format={export_format!r}",
    )
    result_fields = result_page.get("selected_fields", result_page.get("field_ids"))
    result_codes = result_page.get("security_codes")
    result_code_ok = result_page.get("code_count") == 1 and (
        result_codes in (None, ["000001"])
    )
    result_condition = str(result_page.get("condition") or "").replace(" ", "")
    structured_summary_ok = (
        (result_page.get("reconciled") is True or result_page.get("verified") is True)
        and result_page.get("table_id") == "FS_Combas"
        and result_page.get("date_start") == "2020-12-31"
        and result_page.get("date_end") == "2020-12-31"
        and result_code_ok
        and result_fields == list(CSMAR_HEADER)
        and result_condition == "Typrep=A"
        and export_rows == 1
        and "csv" in export_format.lower()
    )
    requires_structured_summary = str(data.get("adapter") or "") in GROK_ADAPTERS or bool(
        result_page
    )
    audit.check(
        "CSMAR structured result-page reconciliation",
        structured_summary_ok if requires_structured_summary else legacy_structured_result,
        "require table/date/code/fields/Typrep/format/record-count reconciliation for Grok",
    )
    transport = _mapping(data.get("download_transport"))
    audit.check("CSMAR UI export", transport.get("ui_export_completed") is True, "ui_export_completed must be true")
    audit.check(
        "CSMAR final local save",
        transport.get("ui_local_save_clicked") is True,
        "ui_local_save_clicked must be true",
    )
    browser_event = transport.get("browser_download_event_observed") is True
    legacy_fallback = (
        str(transport.get("download_event") or "").lower() == "unsupported"
        and transport.get("completion") == "fallback_directory_increment"
    )
    audit.check(
        "CSMAR browser download completion",
        browser_event or legacy_fallback,
        "require browser event or legacy fallback_directory_increment evidence",
    )
    audit.check(
        "CSMAR temporary URL hygiene",
        _temporary_url_persisted(data, transport) is False,
        "temporary_url_persisted must be false",
    )
    return {
        "rows": len(data_rows),
        "columns": len(CSMAR_HEADER),
        "codes": [row[0]] if row[0] else [],
        "dates": [row[2]] if row[2] else [],
        "report_types": [row[3]] if row[3] else [],
        "total_assets_nonempty": amount_ok,
    }


def _verify_freshness(
    receipt_path: Path,
    data: Mapping[str, Any],
    zip_path: Path,
    run_dir: Path,
    runtime: Runtime,
    audit: Audit,
) -> Mapping[str, Any]:
    completed = _parse_timestamp(data.get("completed_at"))
    audit.check(
        "receipt completion timestamp",
        completed is not None,
        "completed_at is timezone-aware ISO-8601",
    )
    started = _receipt_start(data)
    audit.check(
        "Grok explicit run start timestamp",
        runtime != "grok" or started is not None,
        "Grok freshness requires started_at/run_started_at/download_started_at",
    )
    zip_mtime = datetime.fromtimestamp(zip_path.stat().st_mtime, timezone.utc)
    now = datetime.now(timezone.utc)
    audit.check(
        "receipt completion not in future",
        completed is not None and completed <= now + FUTURE_SLOP,
        f"completed_at={completed.isoformat() if completed else '<invalid>'}, now={now.isoformat()}",
    )
    if completed is not None and started is not None:
        audit.check(
            "run timestamp order",
            started <= completed,
            f"started_at={started.isoformat()}, completed_at={completed.isoformat()}",
        )
    if completed is not None:
        lower_bound = completed - MAX_DOWNLOAD_AGE
        if started is not None:
            lower_bound = max(lower_bound, started - START_SLOP)
        audit.check(
            "download freshness window",
            lower_bound <= zip_mtime <= completed + FUTURE_SLOP,
            f"zip_mtime={zip_mtime.isoformat()}, "
            f"window={lower_bound.isoformat()}..{(completed + FUTURE_SLOP).isoformat()}",
        )
    receipt_mtime = datetime.fromtimestamp(receipt_path.stat().st_mtime, timezone.utc)
    audit.check(
        "receipt follows landed ZIP",
        zip_mtime <= receipt_mtime + FUTURE_SLOP,
        f"zip_mtime={zip_mtime.isoformat()}, receipt_mtime={receipt_mtime.isoformat()}",
    )
    run_match = re.fullmatch(r"(\d{8}T\d{6}Z)", run_dir.name)
    if run_match:
        run_start = datetime.strptime(run_match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        audit.check(
            "artifact not older than evidence run",
            zip_mtime >= run_start - FUTURE_SLOP,
            f"zip_mtime={zip_mtime.isoformat()}, run_start={run_start.isoformat()}",
        )
    partials = [
        Path(str(zip_path) + suffix)
        for suffix in (".crdownload", ".part", ".partial", ".tmp")
        if Path(str(zip_path) + suffix).exists()
    ]
    audit.check("no partial download sibling", not partials, f"partial_siblings={len(partials)}")
    return {
        "zip_mtime_utc": zip_mtime.isoformat(),
        "completed_at_utc": completed.isoformat() if completed else None,
        "started_at_utc": started.isoformat() if started else None,
    }


def verify_receipt(
    receipt_path: Path,
    repo_root: Path,
    run_dir: Path,
    expected_runtime: Runtime,
) -> VerificationReport:
    receipt = receipt_path.resolve(strict=True)
    repo = repo_root.resolve(strict=True)
    run = run_dir.resolve(strict=True)
    audit = Audit()
    try:
        receipt.relative_to(run)
        run.relative_to(repo)
    except ValueError:
        audit.check("verification roots", False, "receipt must be inside the repository evidence run")
        return VerificationReport(
            SCHEMA_VERSION, False, "unknown", expected_runtime, str(receipt), audit.checks, {}
        )
    try:
        payload = json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        audit.check("receipt JSON", False, f"receipt read failed: {type(error).__name__}")
        return VerificationReport(
            SCHEMA_VERSION, False, "unknown", expected_runtime, str(receipt), audit.checks, {}
        )
    if not isinstance(payload, dict):
        audit.check("receipt JSON", False, "receipt is not a JSON object")
        return VerificationReport(
            SCHEMA_VERSION, False, "unknown", expected_runtime, str(receipt), audit.checks, {}
        )
    data: Mapping[str, Any] = payload
    site = _normalize_site(data)
    audit.check("known P4 source", site in {"cnrds", "csmar"}, f"source={data.get('source')!r}")
    _verify_runtime_adapter(data, expected_runtime, audit)
    declared_runtime = str(data.get("runtime") or "").strip().lower()
    audit.check(
        "runtime declaration",
        declared_runtime == expected_runtime
        if expected_runtime == "grok"
        else not declared_runtime or declared_runtime == expected_runtime,
        f"runtime={declared_runtime or '<implicit-from-adapter>'}",
    )
    artifacts_raw = data.get("artifacts")
    artifacts = (
        [item for item in artifacts_raw if isinstance(item, Mapping)]
        if isinstance(artifacts_raw, list)
        else []
    )
    audit.check("artifact list", bool(artifacts), f"artifact_records={len(artifacts)}")
    zip_record = _select_record(artifacts, "zip", audit)
    csv_record = _select_record(artifacts, "csv", audit)
    if site is None or zip_record is None or csv_record is None:
        return VerificationReport(
            SCHEMA_VERSION,
            False,
            site or "unknown",
            expected_runtime,
            str(receipt),
            audit.checks,
            {},
        )

    zip_path, zip_error = _resolve_artifact_path(zip_record.get("path"), receipt, repo, run)
    csv_path, csv_error = _resolve_artifact_path(csv_record.get("path"), receipt, repo, run)
    audit.check("ZIP path", zip_path is not None, zip_error or "ZIP resolves inside repository")
    audit.check("CSV path", csv_path is not None, csv_error or "CSV resolves inside repository")
    if zip_path is None or csv_path is None:
        return VerificationReport(SCHEMA_VERSION, False, site, expected_runtime, str(receipt), audit.checks, {})
    try:
        zip_relative = zip_path.relative_to(run)
        csv_relative = csv_path.relative_to(run)
    except ValueError:
        zip_relative = Path("outside-run")
        csv_relative = Path("outside-run")
    expected_prefix = Path("cn-data") / "raw" / site
    base_paths_ok = (
        zip_relative.parts[: len(expected_prefix.parts)] == expected_prefix.parts
        and csv_relative.parts[: len(expected_prefix.parts)] == expected_prefix.parts
    )
    zip_version_dir = (
        zip_relative.parts[len(expected_prefix.parts)]
        if len(zip_relative.parts) > len(expected_prefix.parts)
        else ""
    )
    csv_version_dir = (
        csv_relative.parts[len(expected_prefix.parts)]
        if len(csv_relative.parts) > len(expected_prefix.parts)
        else ""
    )
    version_pattern = (
        r"\d{4}-\d{2}-\d{2}"
        if expected_runtime == "codex"
        else r"\d{4}-\d{2}-\d{2}_grok_v[1-9]\d*"
    )
    runtime_paths_ok = (
        base_paths_ok
        and zip_version_dir == csv_version_dir
        and re.fullmatch(version_pattern, zip_version_dir) is not None
    )
    audit.check(
        "runtime-owned artifact paths",
        runtime_paths_ok,
        f"expected prefix={expected_prefix}, version_dir_pattern={version_pattern}",
    )
    audit.check("artifact paths are distinct", zip_path != csv_path, "ZIP and CSV are separate landed files")
    zip_bytes = _verify_record(zip_record, zip_path, "ZIP", MAX_ARCHIVE_BYTES, audit)
    csv_bytes = _verify_record(csv_record, csv_path, "CSV", MAX_CSV_BYTES, audit)
    audit.check("ZIP magic", bool(zip_bytes) and zip_bytes.startswith(b"PK"), "ZIP starts with PK signature")
    inner_csv = _read_matching_csv_member(zip_path, csv_path, audit)
    same_csv = inner_csv is not None and csv_bytes is not None and inner_csv == csv_bytes
    audit.check(
        "landed CSV equals ZIP member",
        same_csv,
        f"inner_sha256={_sha256_bytes(inner_csv) if inner_csv is not None else '<unavailable>'}",
    )
    facts: dict[str, Any] = {
        "zip_path": str(zip_relative),
        "zip_sha256": _sha256_bytes(zip_bytes) if zip_bytes is not None else None,
        "csv_path": str(csv_relative),
        "csv_sha256": _sha256_bytes(csv_bytes) if csv_bytes is not None else None,
    }
    facts.update(_verify_freshness(receipt, data, zip_path, run, expected_runtime, audit))
    if csv_bytes is not None:
        rows = _parse_csv(csv_bytes, site, audit)
        if rows is not None:
            if site == "cnrds":
                facts.update(_verify_cnrds(data, rows, audit))
            else:
                facts.update(_verify_csmar(data, rows, audit))
    return VerificationReport(
        schema_version=SCHEMA_VERSION,
        ok=audit.ok,
        site=site,
        runtime=expected_runtime,
        receipt_path=str(receipt),
        checks=audit.checks,
        facts=facts,
    )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--runtime", required=True, choices=("codex", "grok"))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        report = verify_receipt(args.receipt, args.repo_root, args.run_dir, args.runtime)
    except (OSError, ValueError) as error:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "site": "unknown",
            "runtime": args.runtime,
            "receipt_path": str(args.receipt),
            "checks": [
                {
                    "name": "verification input",
                    "ok": False,
                    "detail": f"{type(error).__name__}: {error}",
                }
            ],
            "facts": {},
        }
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(report.as_dict(), ensure_ascii=False, sort_keys=True))
    return 0 if report.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
