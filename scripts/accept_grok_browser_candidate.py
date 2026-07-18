#!/usr/bin/env python3
"""Externally accept a frozen Grok Chrome DevTools browser candidate.

The Grok invocation is intentionally limited to describing one already-landed
artifact.  This process runs outside Grok and the browser MCP, re-opens every
input, verifies provenance, confinement, immutability, file format, and stage
content, then atomically creates a candidate-only external acceptance record.
It never creates a business success receipt or updates a manifest/spec.

Candidate v1 encodes ``artifact.mtime_ns`` as a positive decimal string with
no leading zero.  This preserves epoch-nanosecond precision across Node/JSON;
the external acceptance record still stores the independently observed value
as a JSON integer.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
import posixpath
import re
import shutil
import stat
import subprocess
import sys
import unicodedata
import zipfile
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET


CANDIDATE_SCHEMA = "aris.grok-browser-candidate.v1"
SPEC_SCHEMA = "aris.grok-browser-acceptance-spec.v1"
ACCEPTANCE_SCHEMA = "aris.grok-browser-external-acceptance.v1"
EXACT_BINDINGS = {
    "runtime": "grok",
    "adapter": "grok_chrome_devtools_mcp",
    "mcp_server": "browser",
    "implementation": "chrome-devtools-mcp",
    "profile_mode": "dedicated_persistent",
}
SUPPORTED_FORMATS = {"pdf", "csv", "xlsx", "zip"}
MAX_TABLE_BYTES = 128 * 1024 * 1024
MAX_ZIP_TOTAL_BYTES = 512 * 1024 * 1024
MAX_TOOL_OUTPUT_BYTES = 64 * 1024 * 1024
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
POSITIVE_DECIMAL_RE = re.compile(r"[1-9][0-9]*\Z")
SITE_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")
COLLISION_SUFFIX_RE = re.compile(r"^(?P<stem>.+) \((?P<number>[1-9][0-9]*)\)(?P<suffix>\.[^.]+)?$")
CELL_REF_RE = re.compile(r"([A-Z]+)[1-9][0-9]*\Z")
SENSITIVE_VALUE_RE = re.compile(
    r"(?i)(?:access[_-]?token|refresh[_-]?token|password|passwd|secret|"
    r"credential|session(?:id)?|cookie|authorization|x-amz-signature|"
    r"signature)\s*[:=]|\bbearer\s+[a-z0-9._~+/-]+"
)
RAW_OUTPUT_RE = re.compile(
    r"(?i)(?:raw[_ -]?(?:tool|mcp|browser)[_ -]?output|mcp[_ -]?tool[_ -]?result|"
    r"devtools[_ -]?snapshot|<html(?:\s|>))"
)
FORBIDDEN_FIELD_PARTS = {
    "token",
    "password",
    "passwd",
    "secret",
    "credential",
    "cookie",
    "authorization",
    "session",
    "signed",
    "signature",
}
FORBIDDEN_ID_FIELDS = {
    "tabid",
    "pageid",
    "uid",
    "leaseid",
    "targetid",
    "frameid",
}
FORBIDDEN_RAW_FIELDS = {
    "rawoutput",
    "rawtooloutput",
    "tooloutput",
    "mcptooloutput",
    "browseroutput",
    "snapshot",
    "transcript",
}


class AcceptanceError(ValueError):
    """Raised when an external acceptance invariant is not satisfied."""


@dataclass(frozen=True)
class FileSnapshot:
    path: Path
    sha256: str
    size_bytes: int
    mtime_ns: int
    device: int
    inode: int

    def same_file_and_content(self, other: FileSnapshot) -> bool:
        return (
            self.path == other.path
            and self.sha256 == other.sha256
            and self.size_bytes == other.size_bytes
            and self.mtime_ns == other.mtime_ns
            and self.device == other.device
            and self.inode == other.inode
        )

    def public(self, workspace: Path) -> dict[str, object]:
        return {
            "path": self.path.relative_to(workspace).as_posix(),
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "mtime_ns": self.mtime_ns,
        }


@dataclass(frozen=True)
class AcceptanceInputs:
    workspace: Path
    run_root: Path
    candidate_path: Path
    spec_path: Path
    output_path: Path


@dataclass(frozen=True)
class TableData:
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    source_format: str
    sheet: str | None = None
    archive_member: str | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_regular_file(path: Path) -> tuple[bytes, FileSnapshot]:
    try:
        before = path.lstat()
    except OSError as error:
        raise AcceptanceError(f"cannot stat input {path}: {error}") from error
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise AcceptanceError(f"input is not a non-symlink regular file: {path}")
    try:
        data = path.read_bytes()
        after = path.lstat()
    except OSError as error:
        raise AcceptanceError(f"cannot read input {path}: {error}") from error
    signature_before = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_mode,
    )
    signature_after = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_mode,
    )
    if signature_before != signature_after or len(data) != after.st_size:
        raise AcceptanceError(f"input changed while it was read: {path}")
    return data, FileSnapshot(
        path=path,
        sha256=_sha256_bytes(data),
        size_bytes=after.st_size,
        mtime_ns=after.st_mtime_ns,
        device=after.st_dev,
        inode=after.st_ino,
    )


def _json_no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AcceptanceError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _load_frozen_json(path: Path) -> tuple[dict[str, Any], FileSnapshot]:
    raw, snapshot = _read_regular_file(path)
    try:
        text = raw.decode("utf-8")
        payload = json.loads(text, object_pairs_hook=_json_no_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AcceptanceError(f"invalid UTF-8 JSON in {path}: {error}") from error
    if not isinstance(payload, dict):
        raise AcceptanceError(f"JSON root must be an object: {path}")
    return payload, snapshot


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AcceptanceError(f"{label} must be an object")
    return value


def _require_exact_keys(
    value: Mapping[str, Any], required: set[str], optional: set[str], label: str
) -> None:
    keys = set(value)
    missing = sorted(required - keys)
    extra = sorted(keys - required - optional)
    if missing or extra:
        details: list[str] = []
        if missing:
            details.append(f"missing {missing}")
        if extra:
            details.append(f"unexpected {extra}")
        raise AcceptanceError(f"{label} fields invalid: {'; '.join(details)}")


def _require_string(value: Any, label: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value):
        raise AcceptanceError(f"{label} must be a{' non-empty' if nonempty else ''} string")
    return value


def _require_integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise AcceptanceError(f"{label} must be an integer >= {minimum}")
    return value


def _require_sha256(value: Any, label: str) -> str:
    text = _require_string(value, label)
    if not SHA256_RE.fullmatch(text):
        raise AcceptanceError(f"{label} must be a lowercase SHA-256 digest")
    return text


def _require_positive_decimal_string(value: Any, label: str) -> str:
    text = _require_string(value, label)
    if not POSITIVE_DECIMAL_RE.fullmatch(text):
        raise AcceptanceError(
            f"{label} must be a positive decimal string without leading zero"
        )
    return text


def _normalized_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.casefold())


def _scan_candidate_security(value: Any, location: str = "$candidate") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise AcceptanceError(f"non-string JSON field at {location}")
            normalized = _normalized_key(key)
            if normalized in FORBIDDEN_ID_FIELDS:
                raise AcceptanceError(f"browser tab/page/UID/lease identifier is forbidden: {location}.{key}")
            if normalized in FORBIDDEN_RAW_FIELDS or (
                normalized.startswith("raw") and ("tool" in normalized or "browser" in normalized)
            ):
                raise AcceptanceError(f"raw browser/MCP output field is forbidden: {location}.{key}")
            if any(part in normalized for part in FORBIDDEN_FIELD_PARTS):
                raise AcceptanceError(f"secret/session field is forbidden: {location}.{key}")
            _scan_candidate_security(child, f"{location}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _scan_candidate_security(child, f"{location}[{index}]")
        return
    if isinstance(value, str):
        if SENSITIVE_VALUE_RE.search(value):
            raise AcceptanceError(f"secret/token/credential/session value is forbidden at {location}")
        if RAW_OUTPUT_RE.search(value):
            raise AcceptanceError(f"raw browser/MCP output value is forbidden at {location}")
        if "://" in value:
            parsed = urlsplit(value)
            if parsed.query or parsed.fragment:
                raise AcceptanceError(f"URL query/fragment is forbidden at {location}")


def _validate_relative_artifact_path(value: Any, label: str) -> str:
    text = _require_string(value, label)
    if "\x00" in text or "?" in text or "#" in text or "\\" in text or "://" in text:
        raise AcceptanceError(f"{label} is not a safe query-free workspace-relative path")
    path = PurePosixPath(text)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise AcceptanceError(f"{label} is not a safe workspace-relative path")
    if any(any(ord(character) < 32 for character in part) for part in path.parts):
        raise AcceptanceError(f"{label} contains control characters")
    return path.as_posix()


def _validate_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    _scan_candidate_security(payload)
    required = {
        "schema_version",
        *EXACT_BINDINGS,
        "stage",
        "site",
        "acceptance_spec_sha256",
        "artifact",
    }
    _require_exact_keys(payload, required, set(), "candidate")
    if payload["schema_version"] != CANDIDATE_SCHEMA:
        raise AcceptanceError(f"candidate.schema_version must equal {CANDIDATE_SCHEMA}")
    for field, expected in EXACT_BINDINGS.items():
        if payload[field] != expected:
            raise AcceptanceError(f"candidate.{field} must equal {expected}")
    stage = _require_string(payload["stage"], "candidate.stage")
    if stage not in {"P3", "P4"}:
        raise AcceptanceError("candidate.stage must be P3 or P4")
    site = _require_string(payload["site"], "candidate.site")
    if not SITE_RE.fullmatch(site):
        raise AcceptanceError("candidate.site must be a lowercase site slug")
    _require_sha256(payload["acceptance_spec_sha256"], "candidate.acceptance_spec_sha256")
    artifact = _require_object(payload["artifact"], "candidate.artifact")
    _require_exact_keys(
        artifact,
        {"path", "format", "size_bytes", "mtime_ns", "sha256"},
        set(),
        "candidate.artifact",
    )
    _validate_relative_artifact_path(artifact["path"], "candidate.artifact.path")
    artifact_format = _require_string(artifact["format"], "candidate.artifact.format")
    if artifact_format not in SUPPORTED_FORMATS:
        raise AcceptanceError("candidate.artifact.format is unsupported")
    if stage == "P3" and artifact_format != "pdf":
        raise AcceptanceError("P3 candidates must bind a PDF artifact")
    if stage == "P4" and artifact_format not in {"csv", "xlsx", "zip"}:
        raise AcceptanceError("P4 candidates must bind a CSV, XLSX, or ZIP artifact")
    _require_integer(artifact["size_bytes"], "candidate.artifact.size_bytes", minimum=1)
    _require_positive_decimal_string(
        artifact["mtime_ns"], "candidate.artifact.mtime_ns"
    )
    _require_sha256(artifact["sha256"], "candidate.artifact.sha256")
    return dict(payload)


def _optional_expected_string(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _require_string(value, label)


def _validate_p3_spec(value: Any) -> dict[str, Any]:
    data = _require_object(value, "spec.p3")
    allowed = {
        "expected_title",
        "expected_authors",
        "expected_doi",
        "expected_pii",
        "expected_ssrn_id",
    }
    _require_exact_keys(data, set(), allowed, "spec.p3")
    title = _optional_expected_string(data.get("expected_title"), "spec.p3.expected_title")
    doi = _optional_expected_string(data.get("expected_doi"), "spec.p3.expected_doi")
    pii = _optional_expected_string(data.get("expected_pii"), "spec.p3.expected_pii")
    ssrn_id = _optional_expected_string(data.get("expected_ssrn_id"), "spec.p3.expected_ssrn_id")
    raw_authors = data.get("expected_authors", [])
    if not isinstance(raw_authors, list) or any(not isinstance(item, str) or not item for item in raw_authors):
        raise AcceptanceError("spec.p3.expected_authors must be a list of non-empty strings")
    if not any((title, raw_authors, doi, pii, ssrn_id)):
        raise AcceptanceError("spec.p3 must provide at least one expected identity")
    if doi is not None:
        canonical_doi = re.sub(r"(?i)^(?:https?://(?:dx\.)?doi\.org/|doi\s*:\s*)", "", doi).strip()
        if not re.fullmatch(r"10\.\d{4,9}/\S+", canonical_doi):
            raise AcceptanceError("spec.p3.expected_doi is not a canonical DOI")
    if pii is not None and len(re.sub(r"[^A-Za-z0-9]", "", pii)) < 8:
        raise AcceptanceError("spec.p3.expected_pii is too short")
    if ssrn_id is not None and not re.fullmatch(r"[1-9][0-9]*", ssrn_id):
        raise AcceptanceError("spec.p3.expected_ssrn_id must contain decimal digits only")
    return dict(data)


def _validate_expected_row(value: Any, headers: Sequence[str], label: str) -> tuple[str, ...]:
    if isinstance(value, dict):
        if set(value) != set(headers):
            raise AcceptanceError(f"{label} object keys must exactly match expected_headers")
        cells = [value[header] for header in headers]
    elif isinstance(value, list):
        if len(value) != len(headers):
            raise AcceptanceError(f"{label} length must equal expected_headers length")
        cells = value
    else:
        raise AcceptanceError(f"{label} must be an object or array")
    result: list[str] = []
    for index, cell in enumerate(cells):
        if cell is None:
            result.append("")
        elif isinstance(cell, str):
            result.append(cell)
        else:
            raise AcceptanceError(f"{label}[{index}] must be a string or null")
    return tuple(result)


def _validate_p4_spec(value: Any, artifact_format: str) -> dict[str, Any]:
    data = _require_object(value, "spec.p4")
    required = {"expected_headers", "exact_rows", "min_rows"}
    optional = {"sheet", "archive_member", "member_format"}
    _require_exact_keys(data, required, optional, "spec.p4")
    headers = data["expected_headers"]
    if (
        not isinstance(headers, list)
        or not headers
        or any(not isinstance(item, str) or not item for item in headers)
        or len(set(headers)) != len(headers)
    ):
        raise AcceptanceError("spec.p4.expected_headers must be unique non-empty strings")
    rows = data["exact_rows"]
    if not isinstance(rows, list):
        raise AcceptanceError("spec.p4.exact_rows must be an array")
    for index, row in enumerate(rows):
        _validate_expected_row(row, headers, f"spec.p4.exact_rows[{index}]")
    _require_integer(data["min_rows"], "spec.p4.min_rows")
    sheet = data.get("sheet")
    if sheet is not None and not (
        (isinstance(sheet, str) and bool(sheet))
        or (isinstance(sheet, int) and not isinstance(sheet, bool) and sheet >= 0)
    ):
        raise AcceptanceError("spec.p4.sheet must be a non-empty name or zero-based index")
    if artifact_format == "zip":
        member = _validate_relative_artifact_path(data.get("archive_member"), "spec.p4.archive_member")
        member_format = data.get("member_format")
        if member_format not in {"csv", "xlsx"}:
            raise AcceptanceError("spec.p4.member_format must be csv or xlsx for ZIP artifacts")
        if member_format == "csv" and sheet is not None:
            raise AcceptanceError("spec.p4.sheet is only valid for XLSX table content")
        data = dict(data)
        data["archive_member"] = member
    else:
        if "archive_member" in data or "member_format" in data:
            raise AcceptanceError("archive_member/member_format are only valid for ZIP artifacts")
        if artifact_format == "csv" and sheet is not None:
            raise AcceptanceError("spec.p4.sheet is only valid for XLSX table content")
    return dict(data)


def _validate_spec(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = {"schema_version", "stage", "site", "artifact"}
    optional = {"p3", "p4"}
    _require_exact_keys(payload, required, optional, "spec")
    if payload["schema_version"] != SPEC_SCHEMA:
        raise AcceptanceError(f"spec.schema_version must equal {SPEC_SCHEMA}")
    stage = _require_string(payload["stage"], "spec.stage")
    if stage not in {"P3", "P4"}:
        raise AcceptanceError("spec.stage must be P3 or P4")
    site = _require_string(payload["site"], "spec.site")
    if not SITE_RE.fullmatch(site):
        raise AcceptanceError("spec.site must be a lowercase site slug")
    artifact = _require_object(payload["artifact"], "spec.artifact")
    _require_exact_keys(artifact, {"path", "format", "min_bytes"}, set(), "spec.artifact")
    _validate_relative_artifact_path(artifact["path"], "spec.artifact.path")
    artifact_format = _require_string(artifact["format"], "spec.artifact.format")
    if artifact_format not in SUPPORTED_FORMATS:
        raise AcceptanceError("spec.artifact.format is unsupported")
    _require_integer(artifact["min_bytes"], "spec.artifact.min_bytes", minimum=1)
    if stage == "P3":
        if set(payload) & {"p4"} or "p3" not in payload:
            raise AcceptanceError("P3 spec must contain p3 and must not contain p4")
        if artifact_format != "pdf":
            raise AcceptanceError("P3 spec artifact format must be pdf")
        _validate_p3_spec(payload["p3"])
    else:
        if set(payload) & {"p3"} or "p4" not in payload:
            raise AcceptanceError("P4 spec must contain p4 and must not contain p3")
        if artifact_format not in {"csv", "xlsx", "zip"}:
            raise AcceptanceError("P4 spec artifact format must be csv, xlsx, or zip")
        _validate_p4_spec(payload["p4"], artifact_format)
    return dict(payload)


def _existing_directory(path: Path, label: str) -> Path:
    try:
        resolved = path.expanduser().resolve(strict=True)
    except OSError as error:
        raise AcceptanceError(f"{label} does not resolve: {error}") from error
    if not resolved.is_dir():
        raise AcceptanceError(f"{label} is not a directory")
    return resolved


def _require_within(path: Path, root: Path, label: str) -> None:
    if not path.is_relative_to(root):
        raise AcceptanceError(f"{label} escapes {root}")


def _resolve_cli_input(path: Path, boundary: Path, label: str) -> Path:
    lexical = Path(os.path.abspath(path.expanduser()))
    if lexical.is_symlink():
        raise AcceptanceError(f"{label} must not be a symlink")
    try:
        resolved = lexical.resolve(strict=True)
    except OSError as error:
        raise AcceptanceError(f"{label} does not resolve: {error}") from error
    _require_within(resolved, boundary, label)
    try:
        mode = resolved.lstat().st_mode
    except OSError as error:
        raise AcceptanceError(f"cannot stat {label}: {error}") from error
    if not stat.S_ISREG(mode) or stat.S_ISLNK(mode):
        raise AcceptanceError(f"{label} must be a non-symlink regular file")
    return resolved


def _assert_no_symlink_components(path: Path, root: Path, label: str) -> None:
    _require_within(path, root, label)
    relative = path.relative_to(root)
    current = root
    for part in relative.parts:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except OSError as error:
            raise AcceptanceError(f"cannot inspect {label} path component {current}: {error}") from error
        if stat.S_ISLNK(mode):
            raise AcceptanceError(f"{label} traverses a symlink: {current}")


def _resolve_artifact(relative_path: str, workspace: Path, run_root: Path) -> Path:
    lexical = workspace.joinpath(*PurePosixPath(relative_path).parts)
    _assert_no_symlink_components(lexical, workspace, "artifact")
    try:
        resolved = lexical.resolve(strict=True)
    except OSError as error:
        raise AcceptanceError(f"artifact does not resolve: {error}") from error
    _require_within(resolved, workspace, "artifact")
    _require_within(resolved, run_root, "artifact")
    if resolved != lexical:
        raise AcceptanceError("artifact path is not canonical inside the workspace")
    return resolved


def _resolve_output(path: Path, workspace: Path, run_root: Path) -> Path:
    lexical = Path(os.path.abspath(path.expanduser()))
    if os.path.lexists(lexical):
        raise AcceptanceError(f"output collision: {lexical}")
    try:
        parent = lexical.parent.resolve(strict=True)
    except OSError as error:
        raise AcceptanceError(f"output parent does not resolve: {error}") from error
    _require_within(parent, run_root, "output parent")
    _assert_no_symlink_components(parent, run_root, "output parent")
    canonical = parent / lexical.name
    _require_within(canonical, run_root, "output")
    _require_within(canonical, workspace, "output")
    if os.path.lexists(canonical):
        raise AcceptanceError(f"output collision: {canonical}")
    return canonical


def _prepare_inputs(
    workspace: Path, run_root: Path, candidate: Path, spec: Path, output: Path
) -> AcceptanceInputs:
    workspace_root = _existing_directory(workspace, "workspace")
    run = _existing_directory(run_root, "run-root")
    _require_within(run, workspace_root, "run-root")
    candidate_path = _resolve_cli_input(candidate, run, "candidate")
    spec_path = _resolve_cli_input(spec, workspace_root, "spec")
    output_path = _resolve_output(output, workspace_root, run)
    if len({candidate_path, spec_path, output_path}) != 3:
        raise AcceptanceError("candidate, spec, and output paths must be distinct")
    return AcceptanceInputs(workspace_root, run, candidate_path, spec_path, output_path)


def _collision_candidates(path: Path) -> list[Path]:
    match = COLLISION_SUFFIX_RE.fullmatch(path.name)
    if match is not None:
        raise AcceptanceError(f"artifact filename has a browser collision suffix: {path.name}")
    stem = path.stem
    suffix = path.suffix
    collision = re.compile(rf"{re.escape(stem)} \([1-9][0-9]*\){re.escape(suffix)}\Z")
    found = [entry for entry in path.parent.iterdir() if collision.fullmatch(entry.name)]
    for partial in (path.with_name(path.name + ".crdownload"), path.with_name(path.name + ".part")):
        if os.path.lexists(partial):
            found.append(partial)
    return sorted(set(found))


def _load_download_verifier() -> tuple[ModuleType, FileSnapshot]:
    verifier_path = (
        Path(__file__).resolve().parents[1]
        / "skills"
        / "browser-session-bridge"
        / "scripts"
        / "verify_download.py"
    )
    _, snapshot = _read_regular_file(verifier_path)
    module_spec = importlib.util.spec_from_file_location("aris_external_verify_download", verifier_path)
    if module_spec is None or module_spec.loader is None:
        raise AcceptanceError(f"cannot load download verifier: {verifier_path}")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    return module, snapshot


def _verify_download(
    artifact: Path, artifact_format: str, min_bytes: int, workspace: Path
) -> tuple[dict[str, Any], FileSnapshot]:
    module, verifier_snapshot = _load_download_verifier()
    expected = module.ExpectedFormat(artifact_format)
    result = module.verify(artifact, expected, min_bytes)
    report = asdict(result)
    report["path"] = artifact.relative_to(workspace).as_posix()
    if not result.ok:
        raise AcceptanceError(f"verify_download.py rejected artifact: {result.error}")
    return report, verifier_snapshot


def _run_pdf_tool(command: list[str], label: str) -> str:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise AcceptanceError(f"{label} failed to run: {error}") from error
    if result.returncode != 0:
        stderr = result.stderr[:4096].decode("utf-8", errors="replace").strip()
        raise AcceptanceError(f"{label} failed with exit {result.returncode}: {stderr}")
    if len(result.stdout) > MAX_TOOL_OUTPUT_BYTES:
        raise AcceptanceError(f"{label} output exceeds {MAX_TOOL_OUTPUT_BYTES} bytes")
    return result.stdout.decode("utf-8", errors="replace")


def _identity_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.sub(r"[^\w]+", " ", normalized, flags=re.UNICODE).split())


def _compact_text(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value).casefold())


def _verify_p3_pdf(path: Path, expected: Mapping[str, Any]) -> dict[str, Any]:
    pdfinfo = shutil.which("pdfinfo")
    pdftotext = shutil.which("pdftotext")
    if pdfinfo is None or pdftotext is None:
        missing = [name for name, found in (("pdfinfo", pdfinfo), ("pdftotext", pdftotext)) if found is None]
        raise AcceptanceError(f"required PDF verifier executable missing: {', '.join(missing)}")
    info = _run_pdf_tool([pdfinfo, str(path)], "pdfinfo")
    text = _run_pdf_tool([pdftotext, "-enc", "UTF-8", "-nopgbrk", str(path), "-"], "pdftotext")
    page_match = re.search(r"(?im)^Pages:\s*([1-9][0-9]*)\s*$", info)
    if page_match is None:
        raise AcceptanceError("pdfinfo did not report a positive page count")
    if len(_identity_text(text)) < 20:
        raise AcceptanceError("pdftotext produced no meaningful document text")
    corpus = f"{info}\n{text}"
    identity_corpus = _identity_text(corpus)
    compact_corpus = _compact_text(corpus)
    matches: dict[str, Any] = {}
    title = expected.get("expected_title")
    if title is not None:
        matched = _identity_text(str(title)) in identity_corpus
        matches["title"] = matched
        if not matched:
            raise AcceptanceError("PDF identity mismatch: expected title not found")
    authors = expected.get("expected_authors", [])
    author_matches = {str(author): _identity_text(str(author)) in identity_corpus for author in authors}
    if author_matches:
        matches["authors"] = author_matches
        if not all(author_matches.values()):
            raise AcceptanceError("PDF identity mismatch: one or more expected authors not found")
    doi = expected.get("expected_doi")
    if doi is not None:
        canonical = re.sub(
            r"(?i)^(?:https?://(?:dx\.)?doi\.org/|doi\s*:\s*)", "", str(doi)
        ).strip().casefold()
        matched = re.sub(r"\s+", "", canonical) in compact_corpus
        matches["doi"] = matched
        if not matched:
            raise AcceptanceError("PDF identity mismatch: expected DOI not found")
    pii = expected.get("expected_pii")
    if pii is not None:
        needle = re.sub(r"[^A-Za-z0-9]", "", str(pii)).casefold()
        haystack = re.sub(r"[^A-Za-z0-9]", "", corpus).casefold()
        path_context = re.sub(r"[^A-Za-z0-9]", "", path.name).casefold()
        # Publisher PDFs do not always print the route-level PII in their
        # document text.  The artifact path is independently frozen by the
        # acceptance spec, so it is a valid secondary context once title,
        # authors, and DOI have bound the document itself.
        matched = needle in haystack or needle in path_context
        matches["pii"] = matched
        if not matched:
            raise AcceptanceError(
                "PDF identity mismatch: expected PII not found in PDF or frozen artifact filename"
            )
    ssrn_id = expected.get("expected_ssrn_id")
    if ssrn_id is not None:
        identifier = re.escape(str(ssrn_id))
        contextual_patterns = (
            rf"ssrn\s*(?:electronic\s+journal\s*)?(?:id|abstract)?\s*[:#=_-]?\s*{identifier}\b",
            rf"abstract[_-]?id\s*[:#=_-]?\s*{identifier}\b",
        )
        matched = any(re.search(pattern, corpus, flags=re.IGNORECASE) for pattern in contextual_patterns)
        if not matched:
            matched = re.search(
                rf"(?<![0-9]){identifier}(?![0-9])", path.name
            ) is not None
        matches["ssrn_id"] = matched
        if not matched:
            raise AcceptanceError(
                "PDF identity mismatch: expected SSRN ID not found in PDF or frozen artifact filename"
            )
    return {
        "verifier": "pdfinfo+pdftotext",
        "status": "PASS",
        "pages": int(page_match.group(1)),
        "text_characters": len(text),
        "pdfinfo_output_sha256": _sha256_bytes(info.encode("utf-8")),
        "pdftotext_output_sha256": _sha256_bytes(text.encode("utf-8")),
        "identity_matches": matches,
        "raw_tool_output_recorded": False,
    }


def _safe_zip_infos(archive: zipfile.ZipFile, label: str) -> dict[str, zipfile.ZipInfo]:
    infos = archive.infolist()
    names = [item.filename for item in infos]
    if len(names) != len(set(names)):
        raise AcceptanceError(f"{label} contains duplicate member names")
    if sum(item.file_size for item in infos) > MAX_ZIP_TOTAL_BYTES:
        raise AcceptanceError(f"{label} uncompressed size exceeds safety limit")
    result: dict[str, zipfile.ZipInfo] = {}
    for item in infos:
        name = item.filename
        path = PurePosixPath(name)
        if (
            not name
            or "\\" in name
            or path.is_absolute()
            or any(part in {"", ".", ".."} for part in path.parts)
        ):
            raise AcceptanceError(f"{label} contains unsafe member path: {name}")
        mode = (item.external_attr >> 16) & 0o170000
        if mode == stat.S_IFLNK:
            raise AcceptanceError(f"{label} contains symlink member: {name}")
        if item.flag_bits & 0x1:
            raise AcceptanceError(f"{label} contains encrypted member: {name}")
        result[name] = item
    return result


def _read_zip_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo, label: str) -> bytes:
    if info.file_size > MAX_TABLE_BYTES:
        raise AcceptanceError(f"{label} exceeds {MAX_TABLE_BYTES} bytes")
    try:
        data = archive.read(info)
    except (OSError, RuntimeError, zipfile.BadZipFile) as error:
        raise AcceptanceError(f"cannot read {label}: {error}") from error
    if len(data) != info.file_size:
        raise AcceptanceError(f"{label} size changed while reading")
    return data


def _trim_row(row: Sequence[str]) -> tuple[str, ...]:
    result = list(row)
    while result and result[-1] == "":
        result.pop()
    return tuple(result)


def _table_from_rows(rows: Sequence[Sequence[str]], source_format: str, **metadata: Any) -> TableData:
    nonempty = [_trim_row(row) for row in rows if any(cell != "" for cell in row)]
    if not nonempty:
        raise AcceptanceError("table contains no non-empty rows")
    headers = list(nonempty[0])
    if headers:
        headers[0] = headers[0].lstrip("\ufeff")
    if not headers or any(not header for header in headers):
        raise AcceptanceError("table header contains an empty cell")
    if len(headers) != len(set(headers)):
        raise AcceptanceError("table header contains duplicate names")
    width = len(headers)
    data_rows: list[tuple[str, ...]] = []
    for row_number, row in enumerate(nonempty[1:], start=2):
        if len(row) > width:
            raise AcceptanceError(f"table row {row_number} has more cells than its header")
        data_rows.append(tuple(row) + ("",) * (width - len(row)))
    return TableData(tuple(headers), tuple(data_rows), source_format, **metadata)


def _parse_csv_bytes(data: bytes, download_verifier: ModuleType, **metadata: Any) -> TableData:
    if len(data) > MAX_TABLE_BYTES:
        raise AcceptanceError(f"CSV exceeds {MAX_TABLE_BYTES} bytes")
    if b"\x00" in data:
        raise AcceptanceError("CSV contains NUL bytes")
    text = download_verifier.decode_text(data)
    sample = text[:65_536]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
    except csv.Error:
        dialect = csv.excel
    try:
        rows = [tuple(row) for row in csv.reader(io.StringIO(text, newline=""), dialect)]
    except csv.Error as error:
        raise AcceptanceError(f"CSV parse failed: {error}") from error
    return _table_from_rows(rows, "csv", **metadata)


def _xlsx_member_bytes(
    archive: zipfile.ZipFile, infos: Mapping[str, zipfile.ZipInfo], name: str, required: bool = True
) -> bytes | None:
    info = infos.get(name)
    if info is None:
        if required:
            raise AcceptanceError(f"XLSX member is missing: {name}")
        return None
    return _read_zip_member(archive, info, f"XLSX member {name}")


def _xml_root(data: bytes, label: str) -> ET.Element:
    try:
        return ET.fromstring(data)
    except ET.ParseError as error:
        raise AcceptanceError(f"invalid XML in {label}: {error}") from error


def _xlsx_column_index(reference: str) -> int:
    match = CELL_REF_RE.fullmatch(reference)
    if match is None:
        raise AcceptanceError(f"invalid XLSX cell reference: {reference}")
    result = 0
    for character in match.group(1):
        result = result * 26 + ord(character) - ord("A") + 1
    return result - 1


def _xlsx_cell_text(cell: ET.Element, shared: Sequence[str], namespace: str) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(f".//{{{namespace}}}t"))
    value = cell.find(f"{{{namespace}}}v")
    raw = "" if value is None or value.text is None else value.text
    if cell_type == "s":
        try:
            index = int(raw)
            return shared[index]
        except (ValueError, IndexError) as error:
            raise AcceptanceError(f"invalid XLSX shared-string index: {raw}") from error
    if cell_type == "b":
        return "TRUE" if raw == "1" else "FALSE" if raw == "0" else raw
    return raw


def _parse_xlsx_bytes(data: bytes, sheet_selector: Any = None, **metadata: Any) -> TableData:
    if len(data) > MAX_TABLE_BYTES:
        raise AcceptanceError(f"XLSX exceeds {MAX_TABLE_BYTES} bytes")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as error:
        raise AcceptanceError("invalid XLSX ZIP container") from error
    with archive:
        infos = _safe_zip_infos(archive, "XLSX")
        workbook_data = _xlsx_member_bytes(archive, infos, "xl/workbook.xml")
        relationships_data = _xlsx_member_bytes(archive, infos, "xl/_rels/workbook.xml.rels")
        assert workbook_data is not None and relationships_data is not None
        workbook = _xml_root(workbook_data, "xl/workbook.xml")
        relationships = _xml_root(relationships_data, "xl/_rels/workbook.xml.rels")
        main_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        package_rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
        rel_targets = {
            item.attrib.get("Id", ""): item.attrib.get("Target", "")
            for item in relationships.findall(f"{{{package_rel_ns}}}Relationship")
        }
        sheets = workbook.findall(f".//{{{main_ns}}}sheet")
        if not sheets:
            raise AcceptanceError("XLSX workbook contains no sheets")
        if sheet_selector is None:
            selected = sheets[0]
        elif isinstance(sheet_selector, int) and not isinstance(sheet_selector, bool):
            if sheet_selector >= len(sheets):
                raise AcceptanceError("requested XLSX sheet index is out of range")
            selected = sheets[sheet_selector]
        else:
            selected = next(
                (item for item in sheets if item.attrib.get("name") == sheet_selector), None
            )
            if selected is None:
                raise AcceptanceError(f"requested XLSX sheet does not exist: {sheet_selector}")
        relationship_id = selected.attrib.get(f"{{{rel_ns}}}id", "")
        target = rel_targets.get(relationship_id, "")
        if not target:
            raise AcceptanceError("selected XLSX sheet has no worksheet relationship")
        if target.startswith("/"):
            worksheet_name = target.lstrip("/")
        else:
            worksheet_name = posixpath.normpath(posixpath.join("xl", target))
        if worksheet_name.startswith("../") or worksheet_name not in infos:
            raise AcceptanceError("selected XLSX worksheet target is unsafe or missing")
        shared_data = _xlsx_member_bytes(archive, infos, "xl/sharedStrings.xml", required=False)
        shared: list[str] = []
        if shared_data is not None:
            shared_root = _xml_root(shared_data, "xl/sharedStrings.xml")
            shared = [
                "".join(node.text or "" for node in item.findall(f".//{{{main_ns}}}t"))
                for item in shared_root.findall(f"{{{main_ns}}}si")
            ]
        worksheet_data = _xlsx_member_bytes(archive, infos, worksheet_name)
        assert worksheet_data is not None
        worksheet = _xml_root(worksheet_data, worksheet_name)
        rows: list[tuple[str, ...]] = []
        for row in worksheet.findall(f".//{{{main_ns}}}row"):
            values: dict[int, str] = {}
            next_column = 0
            for cell in row.findall(f"{{{main_ns}}}c"):
                reference = cell.attrib.get("r")
                column = _xlsx_column_index(reference) if reference else next_column
                if column in values:
                    raise AcceptanceError("XLSX row contains duplicate cell columns")
                values[column] = _xlsx_cell_text(cell, shared, main_ns)
                next_column = column + 1
            width = max(values, default=-1) + 1
            rows.append(tuple(values.get(index, "") for index in range(width)))
        return _table_from_rows(
            rows,
            "xlsx",
            sheet=selected.attrib.get("name"),
            **metadata,
        )


def _load_p4_table(
    artifact: Path, artifact_format: str, expected: Mapping[str, Any], download_verifier: ModuleType
) -> TableData:
    if artifact_format == "csv":
        return _parse_csv_bytes(artifact.read_bytes(), download_verifier)
    if artifact_format == "xlsx":
        return _parse_xlsx_bytes(artifact.read_bytes(), expected.get("sheet"))
    try:
        archive = zipfile.ZipFile(artifact)
    except zipfile.BadZipFile as error:
        raise AcceptanceError("invalid ZIP artifact") from error
    with archive:
        infos = _safe_zip_infos(archive, "ZIP artifact")
        member_name = str(expected["archive_member"])
        info = infos.get(member_name)
        if info is None:
            raise AcceptanceError(f"expected ZIP table member is missing: {member_name}")
        member_data = _read_zip_member(archive, info, f"ZIP member {member_name}")
    if expected["member_format"] == "csv":
        return _parse_csv_bytes(
            member_data, download_verifier, archive_member=member_name
        )
    return _parse_xlsx_bytes(
        member_data,
        expected.get("sheet"),
        archive_member=member_name,
    )


def _verify_p4_table(
    artifact: Path,
    artifact_format: str,
    expected: Mapping[str, Any],
    download_verifier: ModuleType,
) -> dict[str, Any]:
    table = _load_p4_table(artifact, artifact_format, expected, download_verifier)
    expected_headers = tuple(str(item) for item in expected["expected_headers"])
    if table.headers != expected_headers:
        raise AcceptanceError(
            f"P4 header mismatch: expected {list(expected_headers)!r}, got {list(table.headers)!r}"
        )
    minimum = int(expected["min_rows"])
    if len(table.rows) < minimum:
        raise AcceptanceError(f"P4 row count {len(table.rows)} is below minimum {minimum}")
    required_rows = Counter(
        _validate_expected_row(row, expected_headers, f"spec.p4.exact_rows[{index}]")
        for index, row in enumerate(expected["exact_rows"])
    )
    actual_rows = Counter(table.rows)
    missing = sum(max(0, count - actual_rows[row]) for row, count in required_rows.items())
    if missing:
        raise AcceptanceError(f"P4 table is missing {missing} required exact row occurrence(s)")
    canonical_table = json.dumps(
        {"headers": table.headers, "rows": table.rows},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "verifier": "independent-table-structure",
        "status": "PASS",
        "source_format": table.source_format,
        "sheet": table.sheet,
        "archive_member": table.archive_member,
        "headers": list(table.headers),
        "row_count": len(table.rows),
        "minimum_rows": minimum,
        "required_exact_row_occurrences": sum(required_rows.values()),
        "matched_exact_row_occurrences": sum(required_rows.values()),
        "table_content_sha256": _sha256_bytes(canonical_table),
    }


def _verify_snapshot_unchanged(initial: FileSnapshot, label: str) -> FileSnapshot:
    _, current = _read_regular_file(initial.path)
    if not initial.same_file_and_content(current):
        raise AcceptanceError(f"{label} changed during external acceptance")
    return current


def _atomic_write_new_json(path: Path, payload: Mapping[str, Any]) -> None:
    if os.path.lexists(path):
        raise AcceptanceError(f"output collision: {path}")
    encoded = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    temporary = path.parent / f".{path.name}.tmp.{os.getpid()}.{os.urandom(8).hex()}"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor: int | None = None
    try:
        descriptor = os.open(temporary, flags, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as destination:
            descriptor = None
            destination.write(encoded)
            destination.flush()
            os.fsync(destination.fileno())
        try:
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError as error:
            raise AcceptanceError(f"output collision: {path}") from error
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def accept_candidate(
    *, workspace: Path, run_root: Path, candidate: Path, spec: Path, output: Path
) -> dict[str, Any]:
    inputs = _prepare_inputs(workspace, run_root, candidate, spec, output)
    candidate_payload_raw, candidate_snapshot = _load_frozen_json(inputs.candidate_path)
    spec_payload_raw, spec_snapshot = _load_frozen_json(inputs.spec_path)
    candidate_payload = _validate_candidate(candidate_payload_raw)
    spec_payload = _validate_spec(spec_payload_raw)
    if candidate_payload["acceptance_spec_sha256"] != spec_snapshot.sha256:
        raise AcceptanceError("candidate acceptance_spec_sha256 does not match the frozen spec")
    for field in ("stage", "site"):
        if candidate_payload[field] != spec_payload[field]:
            raise AcceptanceError(f"candidate.{field} does not match spec.{field}")
    candidate_artifact = _require_object(candidate_payload["artifact"], "candidate.artifact")
    spec_artifact = _require_object(spec_payload["artifact"], "spec.artifact")
    for field in ("path", "format"):
        if candidate_artifact[field] != spec_artifact[field]:
            raise AcceptanceError(f"candidate.artifact.{field} does not match spec.artifact.{field}")
    artifact = _resolve_artifact(
        str(candidate_artifact["path"]), inputs.workspace, inputs.run_root
    )
    if artifact in {inputs.candidate_path, inputs.spec_path, inputs.output_path}:
        raise AcceptanceError("artifact path must be distinct from candidate, spec, and output")
    collisions = _collision_candidates(artifact)
    if collisions:
        names = [item.name for item in collisions]
        raise AcceptanceError(f"artifact download collision/incomplete sibling found: {names}")
    _, artifact_snapshot = _read_regular_file(artifact)
    if artifact_snapshot.size_bytes != candidate_artifact["size_bytes"]:
        raise AcceptanceError("artifact size does not match frozen candidate")
    if artifact_snapshot.mtime_ns != int(candidate_artifact["mtime_ns"]):
        raise AcceptanceError("artifact mtime_ns does not match frozen candidate")
    if artifact_snapshot.sha256 != candidate_artifact["sha256"]:
        raise AcceptanceError("artifact SHA-256 does not match frozen candidate")

    download_report, verifier_snapshot = _verify_download(
        artifact,
        str(candidate_artifact["format"]),
        int(spec_artifact["min_bytes"]),
        inputs.workspace,
    )
    if (
        download_report["size_bytes"] != artifact_snapshot.size_bytes
        or download_report["sha256"] != artifact_snapshot.sha256
    ):
        raise AcceptanceError("download verifier result does not match the frozen artifact")
    download_module, verifier_snapshot_again = _load_download_verifier()
    if not verifier_snapshot.same_file_and_content(verifier_snapshot_again):
        raise AcceptanceError("verify_download.py changed during external acceptance")
    if candidate_payload["stage"] == "P3":
        stage_report = _verify_p3_pdf(
            artifact, _require_object(spec_payload["p3"], "spec.p3")
        )
    else:
        stage_report = _verify_p4_table(
            artifact,
            str(candidate_artifact["format"]),
            _require_object(spec_payload["p4"], "spec.p4"),
            download_module,
        )

    _verify_snapshot_unchanged(candidate_snapshot, "candidate")
    _verify_snapshot_unchanged(spec_snapshot, "spec")
    _verify_snapshot_unchanged(artifact_snapshot, "artifact")
    verifier_snapshot_final = _verify_snapshot_unchanged(
        verifier_snapshot, "verify_download.py"
    )
    verifier_report = {
        "download": download_report,
        "stage_content": stage_report,
    }
    verifier_report_sha256 = _sha256_bytes(
        json.dumps(
            verifier_report, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    )
    verifier_path = verifier_snapshot_final.path
    implementation_root = Path(__file__).resolve().parents[1]
    payload: dict[str, Any] = {
        "schema_version": ACCEPTANCE_SCHEMA,
        "record_kind": "external_candidate_acceptance",
        "status": "passed",
        "acceptance_scope": "frozen_candidate_only",
        "generated_at": _utc_now(),
        **EXACT_BINDINGS,
        "stage": candidate_payload["stage"],
        "site": candidate_payload["site"],
        "candidate_sha256": candidate_snapshot.sha256,
        "acceptance_spec_sha256": spec_snapshot.sha256,
        "artifact_sha256": artifact_snapshot.sha256,
        "hash_inventory": {
            "candidate": candidate_snapshot.public(inputs.workspace),
            "spec": spec_snapshot.public(inputs.workspace),
            "artifact": artifact_snapshot.public(inputs.workspace),
            "download_verifier": {
                "path": verifier_path.relative_to(implementation_root).as_posix(),
                "sha256": verifier_snapshot_final.sha256,
                "size_bytes": verifier_snapshot_final.size_bytes,
            },
        },
        "immutability": {
            "candidate_unchanged": True,
            "spec_unchanged": True,
            "artifact_unchanged": True,
            "download_verifier_unchanged": True,
        },
        "verifier_report_sha256": verifier_report_sha256,
        "verifier_report": verifier_report,
        "business_success_receipt_created": False,
        "manifest_modified": False,
        "spec_modified": False,
    }
    _atomic_write_new_json(inputs.output_path, payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True, help="frozen candidate JSON")
    parser.add_argument("--spec", type=Path, required=True, help="trusted frozen acceptance spec JSON")
    parser.add_argument("--output", type=Path, required=True, help="new external acceptance JSON")
    parser.add_argument("--workspace", type=Path, required=True, help="workspace confinement root")
    parser.add_argument("--run-root", type=Path, required=True, help="run confinement root inside workspace")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        accept_candidate(
            workspace=args.workspace,
            run_root=args.run_root,
            candidate=args.candidate,
            spec=args.spec,
            output=args.output,
        )
    except (AcceptanceError, OSError, RuntimeError, zipfile.BadZipFile) as error:
        print(f"accept_grok_browser_candidate: {error}", file=sys.stderr)
        return 2
    output = Path(args.output).expanduser().resolve(strict=True)
    print(
        json.dumps(
            {"ok": True, "output": str(output), "sha256": _read_regular_file(output)[1].sha256},
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
