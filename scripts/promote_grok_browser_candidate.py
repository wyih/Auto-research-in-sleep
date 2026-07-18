#!/usr/bin/env python3
"""Promote one externally accepted Grok browser candidate into run evidence.

The browser candidate and its external-acceptance record are deliberately not
business receipts.  This script re-opens and re-verifies that frozen chain,
then creates exactly one root-verifier receipt and appends one manifest row.
It never invents portal observations from an acceptance spec.  For P4, the
only currently promotable shape is an accepted ZIP containing one CSV member;
the member is extracted byte-for-byte and bound to the receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
import tempfile
import unicodedata
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Any, Mapping, Sequence


RECEIPT_SCHEMA = "aris.business-e2e.grok-browser-runtime-receipt.v1"
P3_SITES = frozenset({"cnki", "ssrn", "sciencedirect", "wiley"})
P4_SITES = frozenset({"cnrds", "csmar"})
P3_MANIFEST_HEADER = (
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
P4_MANIFEST_HEADER = (
    "extract_id",
    "source",
    "module_or_db",
    "table_or_dataset",
    "fields_or_query",
    "local_path",
    "format",
    "n_rows",
    "n_cols",
    "content_hash",
    "pulled_at",
    "filters",
    "gap_ids",
    "adapter",
    "receipt_path",
    "status",
    "notes",
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
CSMAR_DESCRIPTION_ROW = ("证券代码", "证券简称", "统计截止日期", "报表类型", "资产总计")


class PromotionError(ValueError):
    """Raised when the accepted chain cannot be promoted safely."""


def _load_acceptor() -> ModuleType:
    path = Path(__file__).with_name("accept_grok_browser_candidate.py")
    module_name = "aris_promoter_accept_grok_browser_candidate"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise PromotionError(f"cannot load external acceptor: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_hash(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return _sha256_bytes(encoded)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _timestamp_from_ns(value: int) -> str:
    seconds, nanoseconds = divmod(value, 1_000_000_000)
    moment = datetime.fromtimestamp(seconds, timezone.utc).replace(
        microsecond=nanoseconds // 1_000
    )
    return moment.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _relative(path: Path, workspace: Path) -> str:
    return path.resolve(strict=True).relative_to(workspace).as_posix()


def _snapshot_ref(snapshot: Any, workspace: Path) -> dict[str, object]:
    return snapshot.public(workspace)


def _require_exact_keys(
    value: Mapping[str, Any], required: set[str], optional: set[str], label: str
) -> None:
    missing = sorted(required - set(value))
    extra = sorted(set(value) - required - optional)
    if missing or extra:
        details: list[str] = []
        if missing:
            details.append(f"missing {missing}")
        if extra:
            details.append(f"unexpected {extra}")
        raise PromotionError(f"{label} fields invalid: {'; '.join(details)}")


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PromotionError(f"{label} must be an object")
    return value


def _validate_acceptance(
    acceptor: ModuleType,
    acceptance: Mapping[str, Any],
    *,
    candidate: Mapping[str, Any],
    spec: Mapping[str, Any],
    candidate_snapshot: Any,
    spec_snapshot: Any,
    artifact_snapshot: Any,
    verifier_snapshot: Any,
    verifier_report: Mapping[str, Any],
    workspace: Path,
) -> None:
    required = {
        "schema_version",
        "record_kind",
        "status",
        "acceptance_scope",
        "generated_at",
        *acceptor.EXACT_BINDINGS,
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
    _require_exact_keys(acceptance, required, set(), "external acceptance")
    expected_scalars = {
        "schema_version": acceptor.ACCEPTANCE_SCHEMA,
        "record_kind": "external_candidate_acceptance",
        "status": "passed",
        "acceptance_scope": "frozen_candidate_only",
        **acceptor.EXACT_BINDINGS,
        "stage": candidate["stage"],
        "site": candidate["site"],
        "candidate_sha256": candidate_snapshot.sha256,
        "acceptance_spec_sha256": spec_snapshot.sha256,
        "artifact_sha256": artifact_snapshot.sha256,
        "verifier_report_sha256": _canonical_hash(verifier_report),
    }
    for field, expected in expected_scalars.items():
        if acceptance.get(field) != expected:
            raise PromotionError(f"external acceptance {field} does not match reverified input")
    if acceptance.get("verifier_report") != verifier_report:
        raise PromotionError("external acceptance verifier_report differs from fresh verification")
    if acceptance.get("business_success_receipt_created") is not False:
        raise PromotionError("external acceptor must not have created a business receipt")
    if acceptance.get("manifest_modified") is not False or acceptance.get("spec_modified") is not False:
        raise PromotionError("external acceptor reports a forbidden manifest/spec mutation")
    immutability = _mapping(acceptance.get("immutability"), "external acceptance.immutability")
    if set(immutability) != {
        "candidate_unchanged",
        "spec_unchanged",
        "artifact_unchanged",
        "download_verifier_unchanged",
    } or not all(value is True for value in immutability.values()):
        raise PromotionError("external acceptance immutability inventory is not all true")
    inventory = _mapping(acceptance.get("hash_inventory"), "external acceptance.hash_inventory")
    _require_exact_keys(
        inventory,
        {"candidate", "spec", "artifact", "download_verifier"},
        set(),
        "external acceptance.hash_inventory",
    )
    expected_inventory = {
        "candidate": candidate_snapshot.public(workspace),
        "spec": spec_snapshot.public(workspace),
        "artifact": artifact_snapshot.public(workspace),
        "download_verifier": {
            "path": verifier_snapshot.path.relative_to(Path(__file__).resolve().parents[1]).as_posix(),
            "sha256": verifier_snapshot.sha256,
            "size_bytes": verifier_snapshot.size_bytes,
        },
    }
    if dict(inventory) != expected_inventory:
        raise PromotionError("external acceptance hash inventory differs from fresh snapshots")
    if candidate["acceptance_spec_sha256"] != spec_snapshot.sha256:
        raise PromotionError("candidate is not bound to the frozen acceptance spec")
    if candidate["stage"] != spec["stage"] or candidate["site"] != spec["site"]:
        raise PromotionError("candidate stage/site differs from the frozen spec")


def _validate_runtime_owned_artifact(
    artifact: Path, run_root: Path, stage: str, site: str
) -> None:
    relative = artifact.relative_to(run_root)
    if stage == "P3":
        expected = Path("grok-workspace") / "artifacts" / "fulltext" / site
        if relative.parts[: len(expected.parts)] != expected.parts:
            raise PromotionError(f"P3 artifact is not in the official Grok-owned {site} path")
        return
    expected = Path("cn-data") / "raw" / site
    if relative.parts[: len(expected.parts)] != expected.parts:
        raise PromotionError(f"P4 artifact is not in the Grok-owned {site} raw path")
    if len(relative.parts) <= len(expected.parts) or re.fullmatch(
        r"\d{4}-\d{2}-\d{2}_grok_v[1-9]\d*", relative.parts[len(expected.parts)]
    ) is None:
        raise PromotionError("P4 artifact version directory is not *_grok_vN")


def _safe_markdown_cell(value: object) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    if "|" in text:
        text = text.replace("|", "｜")
    return text or "not_applicable"


def _manifest_header(lines: Sequence[str]) -> tuple[int, tuple[str, ...]] | None:
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = tuple(cell.strip() for cell in stripped[1:-1].split("|"))
        if cells:
            return index, cells
    return None


def _read_manifest(path: Path, expected_header: Sequence[str]) -> tuple[bytes, os.stat_result, list[str]]:
    before = path.lstat()
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise PromotionError(f"manifest is not a non-symlink regular file: {path}")
    raw = path.read_bytes()
    after = path.lstat()
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise PromotionError("manifest changed while it was read")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PromotionError("manifest is not UTF-8") from error
    lines = text.splitlines()
    located = _manifest_header(lines)
    if located is None or located[1] != tuple(expected_header):
        raise PromotionError("manifest header does not match the exact stage contract")
    header_index = located[0]
    if header_index + 1 >= len(lines):
        raise PromotionError("manifest separator row is missing")
    separator = tuple(
        cell.strip() for cell in lines[header_index + 1].strip()[1:-1].split("|")
    )
    if len(separator) != len(expected_header) or any(
        re.fullmatch(r":?-{3,}:?", cell) is None for cell in separator
    ):
        raise PromotionError("manifest separator row is malformed")
    return raw, after, lines


def _same_stat(path: Path, expected: os.stat_result) -> bool:
    current = path.lstat()
    return (
        current.st_dev,
        current.st_ino,
        current.st_size,
        current.st_mtime_ns,
    ) == (
        expected.st_dev,
        expected.st_ino,
        expected.st_size,
        expected.st_mtime_ns,
    )


def _replace_manifest(
    path: Path,
    original: bytes,
    snapshot: os.stat_result,
    row: str,
    expected_header: Sequence[str],
) -> None:
    if not _same_stat(path, snapshot) or path.read_bytes() != original:
        raise PromotionError("manifest changed before promotion commit")
    text = original.decode("utf-8")
    lines = text.splitlines()
    located = _manifest_header(lines)
    if located is None or located[1] != tuple(expected_header):
        raise PromotionError("manifest table moved before promotion commit")
    insertion = located[0] + 2
    while insertion < len(lines) and lines[insertion].strip().startswith("|"):
        insertion += 1
    lines.insert(insertion, row)
    encoded = ("\n".join(lines) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as destination:
            destination.write(encoded)
            destination.flush()
            os.fsync(destination.fileno())
        if not _same_stat(path, snapshot) or path.read_bytes() != original:
            raise PromotionError("manifest changed during promotion commit")
        os.replace(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _write_new_bytes(path: Path, data: bytes) -> None:
    try:
        parent_status = path.parent.lstat()
    except OSError as error:
        raise PromotionError(f"output parent is unavailable: {path.parent}") from error
    if stat.S_ISLNK(parent_status.st_mode) or not stat.S_ISDIR(parent_status.st_mode):
        raise PromotionError(f"output parent is not a non-symlink directory: {path.parent}")
    if os.path.lexists(path):
        raise PromotionError(f"output collision: {path}")
    temporary = path.parent / f".{path.name}.tmp.{os.getpid()}.{os.urandom(8).hex()}"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor: int | None = None
    linked = False
    try:
        descriptor = os.open(temporary, flags, 0o600)
        with os.fdopen(descriptor, "wb", closefd=False) as destination:
            destination.write(data)
            destination.flush()
            os.fsync(destination.fileno())
        try:
            os.link(temporary, path, follow_symlinks=False)
            linked = True
        except FileExistsError as error:
            raise PromotionError(f"output collision: {path}") from error
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except BaseException:
        if linked:
            try:
                path.unlink()
            except OSError:
                pass
        raise
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> None:
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    _write_new_bytes(path, encoded)


def _identity_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.sub(r"[^\w]+", " ", normalized, flags=re.UNICODE).split())


def _manifest_rows(lines: Sequence[str], header: Sequence[str]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip().strip("`") for cell in stripped[1:-1].split("|")]
        if len(cells) == len(header) and tuple(cells) != tuple(header) and not all(
            re.fullmatch(r":?-{3,}:?", cell) for cell in cells
        ):
            result.append(dict(zip(header, cells, strict=True)))
    return result


def _p3_source_id(spec: Mapping[str, Any]) -> str:
    expected = _mapping(spec.get("p3"), "spec.p3")
    identifiers: list[str] = []
    if expected.get("expected_doi"):
        identifiers.append(str(expected["expected_doi"]))
    if expected.get("expected_ssrn_id"):
        identifiers.append(f"SSRN {expected['expected_ssrn_id']}")
    if expected.get("expected_pii"):
        identifiers.append(f"PII {expected['expected_pii']}")
    return " / ".join(identifiers) or "externally accepted PDF identity"


def _p3_manifest_row(
    *,
    spec: Mapping[str, Any],
    site: str,
    artifact_ref: Mapping[str, Any],
    artifact_landed_at: str,
    receipt_path: str,
    manifest_lines: Sequence[str],
) -> str:
    expected = _mapping(spec.get("p3"), "spec.p3")
    title = str(expected.get("expected_title") or f"Externally accepted {site} PDF")
    existing = _manifest_rows(manifest_lines, P3_MANIFEST_HEADER)
    matching_work_ids = {
        row["work_id"] for row in existing if _identity_key(row.get("title", "")) == _identity_key(title)
    }
    if len(matching_work_ids) > 1:
        raise PromotionError("existing manifest has ambiguous work identities for the accepted title")
    if matching_work_ids:
        work_id = next(iter(matching_work_ids))
    else:
        work_id = f"{site}_{_sha256_bytes(_identity_key(title).encode('utf-8'))[:16]}"
    artifact_id = f"{work_id}-{site}-grok-devtools-{str(artifact_ref['sha256'])[:12]}"
    if any(row.get("local_path_or_gap") == artifact_ref["path"] for row in existing):
        raise PromotionError("P3 manifest already contains the promoted artifact path")
    values = (
        work_id,
        artifact_id,
        "not_applicable",
        "main_paper",
        f"Externally accepted {site} PDF acquired by Grok official DevTools",
        title,
        _p3_source_id(spec),
        "External pdfinfo/pdftotext identity verification against the frozen acceptance spec",
        "browser_session",
        "grok",
        "grok_chrome_devtools_mcp",
        f"`{artifact_ref['path']}`",
        artifact_ref["size_bytes"],
        artifact_ref["pages"],
        artifact_ref["sha256"],
        artifact_landed_at,
        f"`{receipt_path}`",
        f"`{receipt_path}`",
        "verified",
        "not_applicable",
        "Promoted only after independent frozen-candidate acceptance; no portal prose was synthesized.",
    )
    return "| " + " | ".join(_safe_markdown_cell(value) for value in values) + " |"


def _p4_manifest_row(
    *,
    spec: Mapping[str, Any],
    site: str,
    archive_ref: Mapping[str, Any],
    table_ref: Mapping[str, Any],
    artifact_landed_at: str,
    receipt_path: str,
    data_rows: int,
    columns: int,
    manifest_lines: Sequence[str],
) -> str:
    existing = _manifest_rows(manifest_lines, P4_MANIFEST_HEADER)
    if any(row.get("local_path") == table_ref["path"] for row in existing):
        raise PromotionError("P4 manifest already contains the promoted table path")
    p4 = _mapping(spec.get("p4"), "spec.p4")
    headers = [str(value) for value in p4["expected_headers"]]
    values = (
        f"{site}_{str(archive_ref['sha256'])[:16]}_grok",
        site,
        f"official {site.upper()} portal export",
        "externally accepted frozen slice",
        f"`{','.join(headers)}`",
        f"`{table_ref['path']}`",
        "csv",
        data_rows,
        columns,
        f"`sha256:{table_ref['sha256']}`",
        artifact_landed_at,
        f"`frozen_spec_sha256={spec['_snapshot_sha256']}`",
        "not_applicable",
        "grok_chrome_devtools_mcp",
        f"`{receipt_path}`",
        "complete",
        f"Accepted ZIP sha256 {archive_ref['sha256']}; extracted member is byte-identical and exact-slice verified.",
    )
    return "| " + " | ".join(_safe_markdown_cell(value) for value in values) + " |"


def _p4_csv_payload(
    acceptor: ModuleType,
    artifact: Path,
    spec: Mapping[str, Any],
    site: str,
) -> tuple[bytes, str, int, int, str]:
    artifact_spec = _mapping(spec.get("artifact"), "spec.artifact")
    p4 = _mapping(spec.get("p4"), "spec.p4")
    if artifact_spec.get("format") != "zip" or p4.get("member_format") != "csv":
        raise PromotionError("P4 promotion currently requires an accepted ZIP containing CSV")
    member_name = str(p4.get("archive_member") or "")
    try:
        archive = zipfile.ZipFile(artifact)
    except zipfile.BadZipFile as error:
        raise PromotionError("accepted P4 artifact is not a readable ZIP") from error
    with archive:
        infos = acceptor._safe_zip_infos(archive, "accepted P4 ZIP")
        info = infos.get(member_name)
        if info is None:
            raise PromotionError("accepted P4 ZIP no longer contains the frozen CSV member")
        csv_bytes = acceptor._read_zip_member(archive, info, f"ZIP member {member_name}")
    download_module, _ = acceptor._load_download_verifier()
    table = acceptor._parse_csv_bytes(csv_bytes, download_module, archive_member=member_name)
    headers = tuple(str(value) for value in p4["expected_headers"])
    if table.headers != headers:
        raise PromotionError("P4 CSV header differs from the frozen acceptance spec")
    expected_rows = Counter(
        acceptor._validate_expected_row(row, headers, f"spec.p4.exact_rows[{index}]")
        for index, row in enumerate(p4["exact_rows"])
    )
    actual_rows = list(table.rows)
    description = CNRDS_DESCRIPTION_ROW if site == "cnrds" else CSMAR_DESCRIPTION_ROW
    if actual_rows and tuple(actual_rows[0]) == description:
        actual_rows = actual_rows[1:]
    if Counter(actual_rows) != expected_rows:
        raise PromotionError("P4 CSV contains rows outside the exact accepted business slice")
    encoding = ""
    for candidate_encoding in ("utf-8-sig", "gb18030"):
        try:
            csv_bytes.decode(candidate_encoding)
        except UnicodeDecodeError:
            continue
        encoding = "utf-8-bom" if candidate_encoding == "utf-8-sig" and csv_bytes.startswith(b"\xef\xbb\xbf") else candidate_encoding
        break
    if not encoding:
        raise PromotionError("P4 CSV encoding is not promotable")
    return csv_bytes, member_name, len(actual_rows), len(headers), encoding


def promote_candidate(
    *,
    workspace: Path,
    run_root: Path,
    candidate: Path,
    spec: Path,
    acceptance: Path,
    output: Path,
) -> dict[str, Any]:
    acceptor = _load_acceptor()
    inputs = acceptor._prepare_inputs(workspace, run_root, candidate, spec, output)
    acceptor._require_within(inputs.spec_path, inputs.run_root, "spec")
    acceptance_path = acceptor._resolve_cli_input(acceptance, inputs.run_root, "external acceptance")
    if acceptance_path in {inputs.candidate_path, inputs.spec_path, inputs.output_path}:
        raise PromotionError("candidate, spec, acceptance, and output must be distinct")
    candidate_raw, candidate_snapshot = acceptor._load_frozen_json(inputs.candidate_path)
    spec_raw, spec_snapshot = acceptor._load_frozen_json(inputs.spec_path)
    acceptance_raw, acceptance_snapshot = acceptor._load_frozen_json(acceptance_path)
    candidate_data = acceptor._validate_candidate(candidate_raw)
    spec_data = acceptor._validate_spec(spec_raw)
    stage = str(candidate_data["stage"])
    site = str(candidate_data["site"])
    if site not in (P3_SITES if stage == "P3" else P4_SITES):
        raise PromotionError(f"{stage} site is not a root-verifier browser gate: {site}")
    expected_parent = (
        inputs.run_root / "receipts"
        if stage == "P3"
        else inputs.run_root / "cn-data" / "receipts"
    )
    if inputs.output_path.parent != expected_parent.resolve(strict=True):
        raise PromotionError(f"{stage} runtime receipt must be written to {expected_parent}")
    candidate_artifact = _mapping(candidate_data["artifact"], "candidate.artifact")
    spec_artifact = _mapping(spec_data["artifact"], "spec.artifact")
    if candidate_data["acceptance_spec_sha256"] != spec_snapshot.sha256:
        raise PromotionError("candidate acceptance_spec_sha256 does not match the frozen spec")
    if candidate_data["stage"] != spec_data["stage"] or candidate_data["site"] != spec_data["site"]:
        raise PromotionError("candidate stage/site does not match the frozen spec")
    if any(candidate_artifact[field] != spec_artifact[field] for field in ("path", "format")):
        raise PromotionError("candidate artifact path/format does not match the frozen spec")
    artifact = acceptor._resolve_artifact(
        str(candidate_artifact["path"]), inputs.workspace, inputs.run_root
    )
    _validate_runtime_owned_artifact(artifact, inputs.run_root, stage, site)
    collisions = acceptor._collision_candidates(artifact)
    if collisions:
        raise PromotionError("accepted artifact has a collision or partial-download sibling")
    _, artifact_snapshot = acceptor._read_regular_file(artifact)
    if (
        artifact_snapshot.sha256 != candidate_artifact["sha256"]
        or artifact_snapshot.size_bytes != candidate_artifact["size_bytes"]
        or artifact_snapshot.mtime_ns != int(candidate_artifact["mtime_ns"])
    ):
        raise PromotionError("accepted artifact no longer matches the frozen candidate")
    download_report, verifier_snapshot = acceptor._verify_download(
        artifact,
        str(candidate_artifact["format"]),
        int(spec_artifact["min_bytes"]),
        inputs.workspace,
    )
    download_module, verifier_snapshot_again = acceptor._load_download_verifier()
    if not verifier_snapshot.same_file_and_content(verifier_snapshot_again):
        raise PromotionError("download verifier changed during promotion")
    if stage == "P3":
        stage_report = acceptor._verify_p3_pdf(
            artifact, _mapping(spec_data["p3"], "spec.p3")
        )
    else:
        stage_report = acceptor._verify_p4_table(
            artifact,
            str(candidate_artifact["format"]),
            _mapping(spec_data["p4"], "spec.p4"),
            download_module,
        )
    verifier_report = {"download": download_report, "stage_content": stage_report}
    _validate_acceptance(
        acceptor,
        acceptance_raw,
        candidate=candidate_data,
        spec=spec_data,
        candidate_snapshot=candidate_snapshot,
        spec_snapshot=spec_snapshot,
        artifact_snapshot=artifact_snapshot,
        verifier_snapshot=verifier_snapshot,
        verifier_report=verifier_report,
        workspace=inputs.workspace,
    )
    for snapshot, label in (
        (candidate_snapshot, "candidate"),
        (spec_snapshot, "spec"),
        (acceptance_snapshot, "external acceptance"),
        (artifact_snapshot, "artifact"),
    ):
        try:
            acceptor._verify_snapshot_unchanged(snapshot, label)
        except acceptor.AcceptanceError as error:
            raise PromotionError(str(error)) from error

    manifest = (
        inputs.run_root / "manifests" / "FULLTEXT_MANIFEST.md"
        if stage == "P3"
        else inputs.run_root / "cn-data" / "DATA_MANIFEST.md"
    )
    acceptor._assert_no_symlink_components(manifest, inputs.run_root, "manifest")
    manifest_header = P3_MANIFEST_HEADER if stage == "P3" else P4_MANIFEST_HEADER
    manifest_raw, manifest_snapshot, manifest_lines = _read_manifest(manifest, manifest_header)
    receipt_relative = _relative(inputs.output_path.parent, inputs.workspace) + f"/{inputs.output_path.name}"
    artifact_landed_at = _timestamp_from_ns(artifact_snapshot.mtime_ns)
    artifact_ref: dict[str, Any] = {
        "role": "accepted_download",
        "path": artifact_snapshot.path.relative_to(inputs.workspace).as_posix(),
        "sha256": artifact_snapshot.sha256,
        "size_bytes": artifact_snapshot.size_bytes,
        "mtime_ns": artifact_snapshot.mtime_ns,
        "detected_format": str(candidate_artifact["format"]),
        "verified": True,
    }
    table_path: Path | None = None
    table_bytes: bytes | None = None
    table_ref: dict[str, Any] | None = None
    p4_details: dict[str, Any] = {}
    if stage == "P3":
        artifact_ref["role"] = "accepted_pdf"
        artifact_ref["pages"] = int(stage_report["pages"])
        manifest_row = _p3_manifest_row(
            spec=spec_data,
            site=site,
            artifact_ref=artifact_ref,
            artifact_landed_at=artifact_landed_at,
            receipt_path=receipt_relative,
            manifest_lines=manifest_lines,
        )
        receipt_artifacts: dict[str, Any] = {"artifact": artifact_ref}
    else:
        table_bytes, member_name, data_rows, columns, encoding = _p4_csv_payload(
            acceptor, artifact, spec_data, site
        )
        member_basename = PurePosixPath(member_name).name
        table_path = artifact.parent / "extracted" / member_basename
        if table_path.exists() or table_path.is_symlink():
            raise PromotionError(f"extracted table collision: {table_path}")
        table_ref = {
            "role": "accepted_table",
            "path": table_path.relative_to(inputs.workspace).as_posix(),
            "sha256": _sha256_bytes(table_bytes),
            "size_bytes": len(table_bytes),
            "detected_format": "csv",
            "encoding": encoding,
            "verified": True,
        }
        spec_with_snapshot = dict(spec_data)
        spec_with_snapshot["_snapshot_sha256"] = spec_snapshot.sha256
        manifest_row = _p4_manifest_row(
            spec=spec_with_snapshot,
            site=site,
            archive_ref=artifact_ref,
            table_ref=table_ref,
            artifact_landed_at=artifact_landed_at,
            receipt_path=receipt_relative,
            data_rows=data_rows,
            columns=columns,
            manifest_lines=manifest_lines,
        )
        receipt_artifacts = {"artifacts": [artifact_ref, table_ref]}
        p4_details = {
            "archive_member": member_name,
            "table_path": table_ref["path"],
            "data_rows": data_rows,
            "columns": columns,
        }
    promoted_at = _utc_now()
    payload: dict[str, Any] = {
        "schema_version": RECEIPT_SCHEMA,
        "receipt_kind": "externally_promoted_grok_browser_runtime",
        "status": "passed",
        **acceptor.EXACT_BINDINGS,
        "stage": stage,
        "site": site,
        "artifact_landed_at": artifact_landed_at,
        "completed_at": promoted_at,
        **receipt_artifacts,
        "lineage": {
            "candidate": _snapshot_ref(candidate_snapshot, inputs.workspace),
            "acceptance_spec": _snapshot_ref(spec_snapshot, inputs.workspace),
            "external_acceptance": _snapshot_ref(acceptance_snapshot, inputs.workspace),
        },
        "external_verification": {
            "acceptance_schema": acceptor.ACCEPTANCE_SCHEMA,
            "verifier_report_sha256": _canonical_hash(verifier_report),
            "download_ok": download_report.get("ok") is True,
            "stage_content_status": stage_report.get("status"),
            "reverified_during_promotion": True,
        },
        "promotion": {
            "promoter": "scripts/promote_grok_browser_candidate.py",
            "manifest_path": manifest.relative_to(inputs.workspace).as_posix(),
            "manifest_row_sha256": _sha256_bytes(manifest_row.encode("utf-8")),
            "portal_observations_synthesized": False,
            **p4_details,
        },
        "verifier": {
            "ok": True,
            "source": "external_candidate_acceptance",
            "report_sha256": _canonical_hash(verifier_report),
        },
    }

    table_created = False
    table_directory_created = False
    receipt_created = False
    try:
        if table_path is not None and table_ref is not None and table_bytes is not None:
            if not os.path.lexists(table_path.parent):
                table_path.parent.mkdir(mode=0o700)
                table_directory_created = True
            parent_status = table_path.parent.lstat()
            if stat.S_ISLNK(parent_status.st_mode) or not stat.S_ISDIR(parent_status.st_mode):
                raise PromotionError("P4 extracted-table parent is not a non-symlink directory")
            resolved_parent = table_path.parent.resolve(strict=True)
            acceptor._require_within(resolved_parent, inputs.run_root, "P4 extracted-table parent")
            _write_new_bytes(table_path, table_bytes)
            table_created = True
        _write_new_json(inputs.output_path, payload)
        receipt_created = True
        _replace_manifest(
            manifest,
            manifest_raw,
            manifest_snapshot,
            manifest_row,
            manifest_header,
        )
    except BaseException:
        if receipt_created:
            try:
                inputs.output_path.unlink()
            except OSError:
                pass
        if table_created and table_path is not None:
            try:
                table_path.unlink()
            except OSError:
                pass
        if table_directory_created and table_path is not None:
            try:
                table_path.parent.rmdir()
            except OSError:
                pass
        raise
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--acceptance", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = promote_candidate(
            workspace=args.workspace,
            run_root=args.run_root,
            candidate=args.candidate,
            spec=args.spec,
            acceptance=args.acceptance,
            output=args.output,
        )
    except (PromotionError, OSError, RuntimeError, zipfile.BadZipFile) as error:
        print(f"promote_grok_browser_candidate: {error}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(Path(args.output).expanduser().resolve(strict=True)),
                "schema_version": payload["schema_version"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
