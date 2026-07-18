#!/usr/bin/env python3
"""Inspect a local research PDF before evidence extraction.

The script never changes the source PDF and never uploads it.  It records
content identity on the initial viewer pages, page count, text-layer coverage,
likely OCR pages, work/artifact/version identity, and inspector-rendered PNG
evidence in a machine-readable receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


class PdfInspectionError(RuntimeError):
    """Raised when a deterministic PDF inspection step cannot complete."""


@dataclass(frozen=True)
class PageTextMetric:
    page: int
    non_whitespace_chars: int
    alphanumeric_chars: int
    status: str


@dataclass(frozen=True)
class TextLayerInspection:
    classification: str
    total_non_whitespace_chars: int
    usable_pages: int
    usable_page_ratio: float
    sparse_or_empty_pages: list[int]
    ocr_candidate_pages: list[int]
    visual_review_required_pages: list[int]
    visual_review_cleared_pages: list[int]
    visual_review_pending_pages: list[int]
    extracted_text_sha256: str
    page_metrics: list[PageTextMetric]


@dataclass(frozen=True)
class IdentityInspection:
    status: str
    expected_title_tokens: list[str]
    missing_title_tokens: list[str]
    expected_author_tokens: list[str]
    missing_author_tokens: list[str]
    expected_doi: str | None
    doi_matched: bool | None
    viewer_pages_checked: list[int]


@dataclass(frozen=True)
class ArtifactIdentity:
    status: str
    work_id: str
    artifact_id: str
    parent_artifact_id: str
    paper_id: str
    parent_paper_id: str
    artifact_role: str
    version_identity: str
    doi_or_source_id: str


@dataclass(frozen=True)
class RenderPageEvidence:
    source_pdf_sha256: str
    source_pdf_page_count: int
    viewer_page: int
    png_path: str
    png_sha256: str
    png_bytes: int
    width_px: int
    height_px: int
    renderer_tool: str
    renderer_version: str


@dataclass(frozen=True)
class RenderSettings:
    format: str
    dpi: int
    single_file: bool
    command_template: str


@dataclass(frozen=True)
class RenderEvidence:
    schema: str
    page_number_basis: str
    source_pdf_sha256: str
    source_pdf_page_count: int
    render_settings: RenderSettings
    count: int
    pages: list[RenderPageEvidence]


@dataclass(frozen=True)
class PdfInspectionReceipt:
    schema: str
    ok: bool
    ready_for_method_harvest: bool
    work_id: str
    artifact_id: str
    parent_artifact_id: str
    paper_id: str
    parent_paper_id: str
    artifact_role: str
    version_identity: str
    doi_or_source_id: str
    artifact_identity: ArtifactIdentity
    source_pdf: str
    source_pdf_sha256: str
    size_bytes: int
    page_count: int
    encrypted: str
    pdf_version: str
    extraction_tool: str
    extraction_tool_version: str
    text_layer: TextLayerInspection
    identity: IdentityInspection
    render_evidence: RenderEvidence
    visual_spot_check_required: bool
    visual_spot_check_targets: list[str]
    source_pdf_preserved: bool
    error: str | None


ARTIFACT_ROLES = {
    "main_paper",
    "online_appendix",
    "questionnaire",
    "codebook",
    "supplement",
}
ARTIFACT_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
UNUSABLE_VERSION_IDENTITIES = {
    "",
    "n/a",
    "na",
    "none",
    "not_applicable",
    "unknown",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_artifact_identity(
    *,
    work_id: str,
    artifact_id: str,
    parent_artifact_id: str,
    artifact_role: str,
    version_identity: str,
    doi_or_source_id: str,
) -> ArtifactIdentity:
    """Validate the manifest identity tuple before inspecting any PDF bytes."""
    if ARTIFACT_ID_PATTERN.fullmatch(work_id) is None:
        raise PdfInspectionError(
            "work_id must be a 1-128 character ASCII identifier using letters, "
            "digits, dot, underscore, or hyphen"
        )
    if ARTIFACT_ID_PATTERN.fullmatch(artifact_id) is None:
        raise PdfInspectionError(
            "artifact_id must be a 1-128 character ASCII identifier using letters, "
            "digits, dot, underscore, or hyphen"
        )
    if artifact_role not in ARTIFACT_ROLES:
        raise PdfInspectionError(
            "artifact_role must be one of: " + ", ".join(sorted(ARTIFACT_ROLES))
        )
    normalized_version = " ".join(version_identity.split())
    if (
        normalized_version.casefold() in UNUSABLE_VERSION_IDENTITIES
        or len(normalized_version) > 300
    ):
        raise PdfInspectionError(
            "version_identity must be a specific non-placeholder value of at most "
            "300 characters"
        )
    normalized_source_id = " ".join(doi_or_source_id.split())
    if (
        normalized_source_id.casefold() in UNUSABLE_VERSION_IDENTITIES
        or len(normalized_source_id) > 300
    ):
        raise PdfInspectionError(
            "doi_or_source_id must be a specific non-placeholder value of at most "
            "300 characters"
        )
    if artifact_role == "main_paper":
        if parent_artifact_id != "not_applicable":
            raise PdfInspectionError(
                "main_paper requires parent_artifact_id=not_applicable"
            )
    else:
        if ARTIFACT_ID_PATTERN.fullmatch(parent_artifact_id) is None:
            raise PdfInspectionError(
                "a companion artifact requires a valid parent_artifact_id"
            )
        if parent_artifact_id == artifact_id:
            raise PdfInspectionError(
                "a companion artifact's parent_artifact_id must differ from artifact_id"
            )
    return ArtifactIdentity(
        status="pass",
        work_id=work_id,
        artifact_id=artifact_id,
        parent_artifact_id=parent_artifact_id,
        paper_id=work_id,
        parent_paper_id=parent_artifact_id,
        artifact_role=artifact_role,
        version_identity=normalized_version,
        doi_or_source_id=normalized_source_id,
    )


def repository_relative_path(path: Path, repo_root: Path) -> str:
    resolved_root = repo_root.expanduser().resolve()
    resolved_path = path.expanduser().resolve()
    try:
        return resolved_path.relative_to(resolved_root).as_posix()
    except ValueError as exc:
        raise PdfInspectionError(
            f"render output must remain inside repository root: {resolved_root}"
        ) from exc


def default_repository_root() -> Path:
    for starting_point in (Path.cwd(), Path(__file__).resolve()):
        for candidate in (starting_point, *starting_point.parents):
            if (candidate / ".git").exists():
                return candidate
    return Path.cwd()


def png_ihdr_dimensions(path: Path) -> tuple[int, int]:
    try:
        header = path.read_bytes()[:24]
    except OSError as exc:
        raise PdfInspectionError(f"failed to read rendered PNG: {exc}") from exc
    if (
        len(header) != 24
        or header[:8] != b"\x89PNG\r\n\x1a\n"
        or struct.unpack(">I", header[8:12])[0] != 13
        or header[12:16] != b"IHDR"
    ):
        raise PdfInspectionError("rendered file has an invalid PNG signature or IHDR")
    width, height = struct.unpack(">II", header[16:24])
    if width <= 0 or height <= 0:
        raise PdfInspectionError("rendered PNG dimensions must be positive")
    return width, height


def normalize_for_identity(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in normalized if character.isalnum())


def verify_pdf_container(path: Path) -> None:
    if not path.is_file():
        raise PdfInspectionError("source PDF does not exist or is not a regular file")
    if path.stat().st_size < 1024:
        raise PdfInspectionError("source PDF is unexpectedly small")
    with path.open("rb") as handle:
        prefix = handle.read(8)
        tail_size = min(path.stat().st_size, 4096)
        handle.seek(-tail_size, 2)
        tail = handle.read()
    if not prefix.startswith(b"%PDF-"):
        raise PdfInspectionError("source file is missing PDF magic bytes")
    if b"%%EOF" not in tail:
        raise PdfInspectionError("source PDF has no EOF marker and may be partial")


def run_tool(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        raise PdfInspectionError(f"failed to run {command[0]}: {exc}") from exc


def require_tool(name: str) -> str:
    resolved = shutil.which(name)
    if resolved is None:
        raise PdfInspectionError(f"required local tool is unavailable: {name}")
    return resolved


def tool_version(executable: str) -> str:
    result = run_tool((executable, "-v"))
    output = (result.stderr or result.stdout).strip().splitlines()
    return output[0] if output else "unknown"


def render_pdf_pages(
    path: Path,
    *,
    source_pdf_sha256: str,
    source_pdf_page_count: int,
    viewer_pages: Sequence[int],
    artifact_id: str,
    output_dir: Path | None,
    repo_root: Path,
    dpi: int,
) -> RenderEvidence:
    """Render deterministic 1-based viewer pages and bind their PNG facts."""
    pages = sorted(set(viewer_pages))
    invalid_pages = [
        page
        for page in pages
        if isinstance(page, bool) or page < 1 or page > source_pdf_page_count
    ]
    if invalid_pages:
        raise PdfInspectionError(
            "render pages are outside the 1-based PDF viewer-page range: "
            f"{invalid_pages}"
        )
    settings = RenderSettings(
        format="png",
        dpi=dpi,
        single_file=True,
        command_template=(
            "pdftoppm -f <viewer_page> -l <viewer_page> -singlefile -png "
            "-r <dpi> <source_pdf> <output_prefix>"
        ),
    )
    if not pages:
        return RenderEvidence(
            schema="aris.method-harvest.render-evidence.v1",
            page_number_basis="1-based PDF viewer page",
            source_pdf_sha256=source_pdf_sha256,
            source_pdf_page_count=source_pdf_page_count,
            render_settings=settings,
            count=0,
            pages=[],
        )
    if output_dir is None:
        raise PdfInspectionError(
            "--render-output-dir is required when rendering viewer pages"
        )

    resolved_root = repo_root.expanduser().resolve()
    resolved_output = output_dir.expanduser().resolve()
    repository_relative_path(resolved_output, resolved_root)
    resolved_output.mkdir(parents=True, exist_ok=True)
    pdftoppm = require_tool("pdftoppm")
    renderer_version = tool_version(pdftoppm)
    staged: list[tuple[int, Path, Path]] = []
    with tempfile.TemporaryDirectory(prefix=".inspect-pdf-", dir=resolved_output) as temp:
        temp_dir = Path(temp)
        for viewer_page in pages:
            destination = resolved_output / f"{artifact_id}-p{viewer_page}.png"
            prefix = temp_dir / f"render-p{viewer_page}"
            result = run_tool(
                (
                    pdftoppm,
                    "-f",
                    str(viewer_page),
                    "-l",
                    str(viewer_page),
                    "-singlefile",
                    "-png",
                    "-r",
                    str(dpi),
                    str(path),
                    str(prefix),
                )
            )
            if result.returncode != 0:
                raise PdfInspectionError(
                    "pdftoppm failed for viewer page "
                    f"{viewer_page}: {(result.stderr or result.stdout).strip()}"
                )
            rendered = prefix.with_suffix(".png")
            if not rendered.is_file():
                raise PdfInspectionError(
                    f"pdftoppm did not create a PNG for viewer page {viewer_page}"
                )
            png_ihdr_dimensions(rendered)
            if destination.exists():
                if destination.is_symlink() or not destination.is_file():
                    raise PdfInspectionError(
                        f"render destination is not a regular file: {destination}"
                    )
                if sha256_file(destination) != sha256_file(rendered):
                    raise PdfInspectionError(
                        "render destination already exists with different bytes: "
                        f"{destination}"
                    )
            staged.append((viewer_page, rendered, destination))

        if sha256_file(path) != source_pdf_sha256:
            raise PdfInspectionError("source PDF changed while pages were being rendered")
        for _, rendered, destination in staged:
            if not destination.exists():
                rendered.replace(destination)

        evidence_pages: list[RenderPageEvidence] = []
        for viewer_page, _, destination in staged:
            width, height = png_ihdr_dimensions(destination)
            evidence_pages.append(
                RenderPageEvidence(
                    source_pdf_sha256=source_pdf_sha256,
                    source_pdf_page_count=source_pdf_page_count,
                    viewer_page=viewer_page,
                    png_path=repository_relative_path(destination, resolved_root),
                    png_sha256=sha256_file(destination),
                    png_bytes=destination.stat().st_size,
                    width_px=width,
                    height_px=height,
                    renderer_tool=Path(pdftoppm).name,
                    renderer_version=renderer_version,
                )
            )

    return RenderEvidence(
        schema="aris.method-harvest.render-evidence.v1",
        page_number_basis="1-based PDF viewer page",
        source_pdf_sha256=source_pdf_sha256,
        source_pdf_page_count=source_pdf_page_count,
        render_settings=settings,
        count=len(evidence_pages),
        pages=evidence_pages,
    )


def parse_pdfinfo(output: str) -> tuple[int, str, str]:
    values: dict[str, str] = {}
    for line in output.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    try:
        pages = int(values["Pages"])
    except (KeyError, ValueError) as exc:
        raise PdfInspectionError("pdfinfo did not report a valid page count") from exc
    if pages <= 0:
        raise PdfInspectionError("PDF page count must be positive")
    return pages, values.get("Encrypted", "unknown"), values.get("PDF version", "unknown")


def split_page_text(text: str, page_count: int) -> list[str]:
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    if len(pages) < page_count:
        pages.extend([""] * (page_count - len(pages)))
    if len(pages) > page_count:
        pages = pages[: page_count - 1] + ["\f".join(pages[page_count - 1 :])]
    return pages


def classify_text_layer(
    pages: Sequence[str],
    *,
    min_page_chars: int,
    min_usable_ratio: float,
    visually_cleared_pages: Sequence[int] = (),
) -> TextLayerInspection:
    metrics: list[PageTextMetric] = []
    sparse_pages: list[int] = []
    usable_pages = 0
    total_chars = 0
    for page_number, text in enumerate(pages, start=1):
        non_whitespace = len(re.sub(r"\s+", "", text))
        alphanumeric = sum(character.isalnum() for character in text)
        total_chars += non_whitespace
        if alphanumeric >= min_page_chars:
            status = "usable_text"
            usable_pages += 1
        elif alphanumeric:
            status = "sparse_text"
            sparse_pages.append(page_number)
        else:
            status = "no_text"
            sparse_pages.append(page_number)
        metrics.append(
            PageTextMetric(
                page=page_number,
                non_whitespace_chars=non_whitespace,
                alphanumeric_chars=alphanumeric,
                status=status,
            )
        )

    page_count = len(pages)
    usable_ratio = usable_pages / page_count if page_count else 0.0
    minimum_total = max(500, page_count * 20)
    if total_chars < minimum_total or usable_ratio < 0.25:
        classification = "ocr_required"
        ocr_pages = list(range(1, page_count + 1))
    elif usable_ratio < min_usable_ratio:
        classification = "mixed_text_review"
        ocr_pages = list(sparse_pages)
    else:
        classification = "native_text"
        ocr_pages = []

    visual_review_required = (
        list(range(1, page_count + 1))
        if classification == "ocr_required"
        else list(sparse_pages)
    )
    cleared = sorted(set(visually_cleared_pages))
    out_of_range = [page for page in cleared if page < 1 or page > page_count]
    if out_of_range:
        raise PdfInspectionError(
            f"visually cleared pages are outside the PDF page range: {out_of_range}"
        )
    unexpected_clears = [page for page in cleared if page not in visual_review_required]
    if unexpected_clears:
        raise PdfInspectionError(
            "visually cleared pages were not flagged by text-layer inspection: "
            f"{unexpected_clears}"
        )
    pending = [page for page in visual_review_required if page not in cleared]

    joined_text = "\f".join(pages).encode("utf-8")
    return TextLayerInspection(
        classification=classification,
        total_non_whitespace_chars=total_chars,
        usable_pages=usable_pages,
        usable_page_ratio=round(usable_ratio, 6),
        sparse_or_empty_pages=sparse_pages,
        ocr_candidate_pages=ocr_pages,
        visual_review_required_pages=visual_review_required,
        visual_review_cleared_pages=cleared,
        visual_review_pending_pages=pending,
        extracted_text_sha256=sha256_bytes(joined_text),
        page_metrics=metrics,
    )


def normalize_doi(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    normalized = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", normalized)
    normalized = re.sub(r"^doi\s*:\s*", "", normalized)
    return re.sub(r"\s+", "", normalized).rstrip(".,;)")


def doi_from_source_identity(value: str) -> str | None:
    match = re.search(
        r"10\.\d{4,9}/[-._;()/:A-Z0-9]+",
        unicodedata.normalize("NFKC", value),
        flags=re.IGNORECASE,
    )
    return normalize_doi(match.group(0)) if match else None


def inspect_identity(
    pages: Sequence[str],
    expected_title_tokens: Sequence[str],
    *,
    expected_author_tokens: Sequence[str] = (),
    expected_doi: str | None = None,
    max_pages: int = 2,
) -> IdentityInspection:
    title_tokens = [token.strip() for token in expected_title_tokens if token.strip()]
    author_tokens = [token.strip() for token in expected_author_tokens if token.strip()]
    doi = normalize_doi(expected_doi) if expected_doi and expected_doi.strip() else None
    pages_checked = list(range(1, min(len(pages), max_pages) + 1))
    if not title_tokens and not author_tokens and doi is None:
        return IdentityInspection(
            "not_checked", [], [], [], [], None, None, pages_checked
        )
    identity_text = "\f".join(pages[:max_pages])
    normalized_text = normalize_for_identity(identity_text)
    missing_title = [
        token
        for token in title_tokens
        if normalize_for_identity(token) not in normalized_text
    ]
    missing_author = [
        token
        for token in author_tokens
        if normalize_for_identity(token) not in normalized_text
    ]
    doi_matched = None if doi is None else doi in normalize_doi(identity_text)
    passed = not missing_title and not missing_author and doi_matched is not False
    return IdentityInspection(
        status="pass" if passed else "fail",
        expected_title_tokens=title_tokens,
        missing_title_tokens=missing_title,
        expected_author_tokens=author_tokens,
        missing_author_tokens=missing_author,
        expected_doi=doi,
        doi_matched=doi_matched,
        viewer_pages_checked=pages_checked,
    )


def inspect_pdf(
    path: Path,
    *,
    work_id: str,
    artifact_id: str,
    parent_artifact_id: str,
    artifact_role: str,
    version_identity: str,
    doi_or_source_id: str,
    expected_title_tokens: Sequence[str],
    expected_author_tokens: Sequence[str],
    expected_doi: str | None,
    identity_pages: int,
    min_page_chars: int,
    min_usable_ratio: float,
    visually_cleared_pages: Sequence[int],
    render_pages: Sequence[int],
    render_required_pages: bool,
    render_output_dir: Path | None,
    repo_root: Path,
    render_dpi: int,
) -> PdfInspectionReceipt:
    artifact_identity = validate_artifact_identity(
        work_id=work_id,
        artifact_id=artifact_id,
        parent_artifact_id=parent_artifact_id,
        artifact_role=artifact_role,
        version_identity=version_identity,
        doi_or_source_id=doi_or_source_id,
    )
    manifest_doi = doi_from_source_identity(artifact_identity.doi_or_source_id)
    if (
        expected_doi
        and manifest_doi is not None
        and normalize_doi(expected_doi) != manifest_doi
    ):
        raise PdfInspectionError(
            "expect-doi does not match the DOI embedded in doi_or_source_id"
        )
    resolved = path.expanduser().resolve()
    verify_pdf_container(resolved)
    source_hash = sha256_file(resolved)
    pdfinfo = require_tool("pdfinfo")
    pdftotext = require_tool("pdftotext")

    info = run_tool((pdfinfo, str(resolved)))
    if info.returncode != 0:
        raise PdfInspectionError(f"pdfinfo failed: {(info.stderr or info.stdout).strip()}")
    page_count, encrypted, pdf_version = parse_pdfinfo(info.stdout)

    extraction = run_tool((pdftotext, "-layout", str(resolved), "-"))
    if extraction.returncode != 0:
        raise PdfInspectionError(
            f"pdftotext failed: {(extraction.stderr or extraction.stdout).strip()}"
        )
    pages = split_page_text(extraction.stdout, page_count)
    text_layer = classify_text_layer(
        pages,
        min_page_chars=min_page_chars,
        min_usable_ratio=min_usable_ratio,
        visually_cleared_pages=visually_cleared_pages,
    )
    identity = inspect_identity(
        pages,
        expected_title_tokens,
        expected_author_tokens=expected_author_tokens,
        expected_doi=expected_doi,
        max_pages=identity_pages,
    )
    requested_render_pages = list(render_pages)
    if render_required_pages:
        requested_render_pages.extend(text_layer.visual_review_required_pages)
    requested_render_pages = sorted(set(requested_render_pages))
    cleared_without_render = [
        page
        for page in text_layer.visual_review_cleared_pages
        if page not in requested_render_pages
    ]
    if cleared_without_render:
        raise PdfInspectionError(
            "visually cleared pages must be rendered by the same inspector run: "
            f"{cleared_without_render}"
        )
    render_evidence = render_pdf_pages(
        resolved,
        source_pdf_sha256=source_hash,
        source_pdf_page_count=page_count,
        viewer_pages=requested_render_pages,
        artifact_id=artifact_identity.artifact_id,
        output_dir=render_output_dir,
        repo_root=repo_root,
        dpi=render_dpi,
    )
    if sha256_file(resolved) != source_hash:
        raise PdfInspectionError("source PDF changed during inspection")
    identity_ready = identity.status == "pass"
    ready = (
        text_layer.classification != "ocr_required"
        and not text_layer.visual_review_pending_pages
        and identity_ready
    )

    return PdfInspectionReceipt(
        schema="aris.method-harvest.pdf-inspection.v2",
        ok=True,
        ready_for_method_harvest=ready,
        work_id=artifact_identity.work_id,
        artifact_id=artifact_identity.artifact_id,
        parent_artifact_id=artifact_identity.parent_artifact_id,
        paper_id=artifact_identity.paper_id,
        parent_paper_id=artifact_identity.parent_paper_id,
        artifact_role=artifact_identity.artifact_role,
        version_identity=artifact_identity.version_identity,
        doi_or_source_id=artifact_identity.doi_or_source_id,
        artifact_identity=artifact_identity,
        source_pdf=repository_relative_path(resolved, repo_root),
        source_pdf_sha256=source_hash,
        size_bytes=resolved.stat().st_size,
        page_count=page_count,
        encrypted=encrypted,
        pdf_version=pdf_version,
        extraction_tool=pdftotext,
        extraction_tool_version=tool_version(pdftotext),
        text_layer=text_layer,
        identity=identity,
        render_evidence=render_evidence,
        visual_spot_check_required=True,
        visual_spot_check_targets=[
            "construct and variable definitions",
            "sample construction",
            "main specification or equation",
            "main and null-result tables",
            "material appendix or questionnaire pages",
        ],
        source_pdf_preserved=True,
        error=None,
    )


def error_receipt(path: Path, message: str) -> dict[str, object]:
    return {
        "schema": "aris.method-harvest.pdf-inspection.v2",
        "ok": False,
        "ready_for_method_harvest": False,
        "source_pdf": str(path.expanduser().resolve()),
        "error": message,
    }


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, help="local source PDF")
    parser.add_argument(
        "--work-id",
        required=True,
        help="stable METHOD_CARD/synthesis work ID",
    )
    parser.add_argument(
        "--artifact-id",
        required=True,
        help="FULLTEXT_MANIFEST row ID for this exact PDF artifact",
    )
    parser.add_argument(
        "--parent-artifact-id",
        required=True,
        help=(
            "not_applicable for main_paper; main artifact_id for a companion"
        ),
    )
    parser.add_argument(
        "--artifact-role",
        required=True,
        choices=sorted(ARTIFACT_ROLES),
        help="manifest role for this exact PDF artifact",
    )
    parser.add_argument(
        "--version-identity",
        required=True,
        help="specific edition/version identity shown by the source or manifest",
    )
    parser.add_argument(
        "--doi-or-source-id",
        required=True,
        help="specific DOI, repository number, or publisher/source record ID",
    )
    parser.add_argument(
        "--expect-title-token",
        action="append",
        default=[],
        help="repeatable title/identity token that must occur in extracted text",
    )
    parser.add_argument(
        "--expect-author-token",
        action="append",
        default=[],
        help="repeatable author token that must occur on the checked identity pages",
    )
    parser.add_argument(
        "--expect-doi",
        help="DOI that must occur on the checked identity pages",
    )
    parser.add_argument(
        "--identity-pages",
        type=int,
        default=2,
        help="number of initial viewer pages used for identity checks (default 2)",
    )
    parser.add_argument(
        "--min-page-chars",
        type=int,
        default=80,
        help="minimum alphanumeric characters for a page to count as usable text",
    )
    parser.add_argument(
        "--min-usable-ratio",
        type=float,
        default=0.8,
        help="usable-page ratio below which sparse pages require review",
    )
    parser.add_argument(
        "--visual-review-cleared-page",
        action="append",
        default=[],
        type=int,
        help="repeat after visually checking a page flagged as sparse/empty",
    )
    parser.add_argument(
        "--render-page",
        action="append",
        default=[],
        type=int,
        help="repeat to render a specific 1-based PDF viewer page",
    )
    parser.add_argument(
        "--render-required-pages",
        action="store_true",
        help="render every page flagged in visual_review_required_pages",
    )
    parser.add_argument(
        "--render-output-dir",
        type=Path,
        help="repository-contained directory for inspector-generated PNG evidence",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="root used to record PNG paths as repository-relative",
    )
    parser.add_argument(
        "--render-dpi",
        type=int,
        default=144,
        help="PNG rendering resolution from 72 through 600 DPI (default 144)",
    )
    parser.add_argument("--output", type=Path, help="optional JSON receipt path")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.min_page_chars < 1:
        print(json.dumps(error_receipt(args.pdf, "--min-page-chars must be positive")))
        return 2
    if not 0 < args.min_usable_ratio <= 1:
        print(
            json.dumps(
                error_receipt(args.pdf, "--min-usable-ratio must be in (0, 1]")
            )
        )
        return 2
    if not 1 <= args.identity_pages <= 5:
        print(json.dumps(error_receipt(args.pdf, "--identity-pages must be between 1 and 5")))
        return 2
    if not 72 <= args.render_dpi <= 600:
        print(json.dumps(error_receipt(args.pdf, "--render-dpi must be between 72 and 600")))
        return 2

    try:
        receipt: dict[str, object] = asdict(
            inspect_pdf(
                args.pdf,
                work_id=args.work_id,
                artifact_id=args.artifact_id,
                parent_artifact_id=args.parent_artifact_id,
                artifact_role=args.artifact_role,
                version_identity=args.version_identity,
                doi_or_source_id=args.doi_or_source_id,
                expected_title_tokens=args.expect_title_token,
                expected_author_tokens=args.expect_author_token,
                expected_doi=args.expect_doi,
                identity_pages=args.identity_pages,
                min_page_chars=args.min_page_chars,
                min_usable_ratio=args.min_usable_ratio,
                visually_cleared_pages=args.visual_review_cleared_page,
                render_pages=args.render_page,
                render_required_pages=args.render_required_pages,
                render_output_dir=args.render_output_dir,
                repo_root=args.repo_root or default_repository_root(),
                render_dpi=args.render_dpi,
            )
        )
    except (OSError, PdfInspectionError) as exc:
        receipt = error_receipt(args.pdf, str(exc))

    rendered = json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if not receipt["ok"]:
        return 2
    return 0 if receipt["ready_for_method_harvest"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
