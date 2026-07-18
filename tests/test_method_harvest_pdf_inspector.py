from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "method-harvest" / "scripts" / "inspect_pdf.py"


def _pdf_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _write_pdf(path: Path, page_texts: list[str]) -> None:
    font_id = 3 + 2 * len(page_texts)
    page_ids = [3 + 2 * index for index in range(len(page_texts))]
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: (
            f"<< /Type /Pages /Count {len(page_ids)} /Kids "
            f"[{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] >>"
        ).encode("ascii"),
        font_id: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for index, text in enumerate(page_texts):
        page_id = page_ids[index]
        content_id = page_id + 1
        lines = text.splitlines() or [""]
        commands = ["BT /F1 10 Tf 12 TL 50 750 Td"]
        for line in lines:
            commands.append(f"({_pdf_string(line)}) Tj T*")
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1")
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        ).encode("ascii")
        objects[content_id] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream"
        )

    payload = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0] * (font_id + 1)
    for object_id in range(1, font_id + 1):
        offsets[object_id] = len(payload)
        payload.extend(f"{object_id} 0 obj\n".encode("ascii"))
        payload.extend(objects[object_id])
        payload.extend(b"\nendobj\n")
    xref_offset = len(payload)
    payload.extend(f"xref\n0 {font_id + 1}\n".encode("ascii"))
    payload.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        payload.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    payload.extend(
        (
            f"trailer\n<< /Size {font_id + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    path.write_bytes(payload)


def _long_page(prefix: str) -> str:
    return "\n".join(
        f"{prefix} line {index:02d} " + "evidence " * 12 for index in range(12)
    )


def _base_cli(pdf: Path, repo_root: Path) -> list[str]:
    return [
        sys.executable,
        str(SCRIPT),
        str(pdf),
        "--work-id",
        "work-alpha",
        "--artifact-id",
        "acquisition-paper-alpha",
        "--parent-artifact-id",
        "not_applicable",
        "--artifact-role",
        "main_paper",
        "--version-identity",
        "Accepted working paper, March 2026",
        "--doi-or-source-id",
        "10.1000/alpha.2026",
        "--expect-title-token",
        "Target Paper Alpha",
        "--expect-author-token",
        "Rivera",
        "--repo-root",
        str(repo_root),
    ]


def _load_module():
    spec = importlib.util.spec_from_file_location("inspect_pdf", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_page_split_preserves_declared_page_count() -> None:
    module = _load_module()
    assert module.split_page_text("one\ftwo\f", 2) == ["one", "two"]
    assert module.split_page_text("one", 3) == ["one", "", ""]


def test_text_layer_routes_native_mixed_and_ocr() -> None:
    module = _load_module()
    usable = "A" * 100

    native = module.classify_text_layer(
        [usable] * 10,
        min_page_chars=80,
        min_usable_ratio=0.8,
    )
    assert native.classification == "native_text"
    assert native.ocr_candidate_pages == []
    assert native.visual_review_required_pages == []
    assert native.visual_review_pending_pages == []

    native_with_sparse_page = module.classify_text_layer(
        [usable] * 9 + [""],
        min_page_chars=80,
        min_usable_ratio=0.8,
    )
    assert native_with_sparse_page.classification == "native_text"
    assert native_with_sparse_page.ocr_candidate_pages == []
    assert native_with_sparse_page.visual_review_required_pages == [10]
    assert native_with_sparse_page.visual_review_pending_pages == [10]

    cleared_sparse_page = module.classify_text_layer(
        [usable] * 9 + [""],
        min_page_chars=80,
        min_usable_ratio=0.8,
        visually_cleared_pages=[10],
    )
    assert cleared_sparse_page.visual_review_cleared_pages == [10]
    assert cleared_sparse_page.visual_review_pending_pages == []

    mixed = module.classify_text_layer(
        [usable] * 6 + ["x"] * 4,
        min_page_chars=80,
        min_usable_ratio=0.8,
    )
    assert mixed.classification == "mixed_text_review"
    assert mixed.ocr_candidate_pages == [7, 8, 9, 10]
    assert mixed.visual_review_required_pages == [7, 8, 9, 10]
    assert mixed.visual_review_pending_pages == [7, 8, 9, 10]

    scanned = module.classify_text_layer(
        [""] * 10,
        min_page_chars=80,
        min_usable_ratio=0.8,
    )
    assert scanned.classification == "ocr_required"
    assert scanned.ocr_candidate_pages == list(range(1, 11))
    assert scanned.visual_review_required_pages == list(range(1, 11))


def test_identity_matching_is_unicode_and_punctuation_tolerant() -> None:
    module = _load_module()
    result = module.inspect_identity(
        ["Corporate-Culture, Evidence from the Field / 公司文化 — John Graham"],
        ["corporate culture", "公司文化"],
        expected_author_tokens=["John Graham"],
    )
    assert result.status == "pass"
    assert result.missing_title_tokens == []
    assert result.missing_author_tokens == []
    assert result.viewer_pages_checked == [1]

    failure = module.inspect_identity(["A different paper"], ["target title"])
    assert failure.status == "fail"
    assert failure.missing_title_tokens == ["target title"]


def test_identity_is_limited_to_initial_pages_and_not_checked_is_not_pass() -> None:
    module = _load_module()
    reference_only_match = module.inspect_identity(
        ["Wrong title page", "Methods", "References: Target Title"],
        ["Target Title"],
        max_pages=2,
    )
    assert reference_only_match.status == "fail"
    assert reference_only_match.viewer_pages_checked == [1, 2]

    unchecked = module.inspect_identity(["Some paper"], [])
    assert unchecked.status == "not_checked"
    assert unchecked.expected_doi is None


def test_identity_accepts_normalized_doi_on_title_pages() -> None:
    module = _load_module()
    result = module.inspect_identity(
        ["Target title\nDOI: 10.1000 / Example.1"],
        ["Target title"],
        expected_doi="https://doi.org/10.1000/example.1",
    )
    assert result.status == "pass"
    assert result.doi_matched is True


def test_png_ihdr_parser_rejects_wrong_chunk_length(tmp_path: Path) -> None:
    module = _load_module()
    png = tmp_path / "fake.png"
    png.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", 12)
        + b"IHDR"
        + struct.pack(">II", 100, 200)
    )
    with pytest.raises(module.PdfInspectionError, match="invalid PNG"):
        module.png_ihdr_dimensions(png)


def test_cli_generates_identity_bound_native_render_evidence(tmp_path: Path) -> None:
    assert shutil.which("pdfinfo")
    assert shutil.which("pdftotext")
    assert shutil.which("pdftoppm")
    pdf = tmp_path / "paper.pdf"
    _write_pdf(
        pdf,
        [
            _long_page("Target Paper Alpha by Rivera"),
            _long_page("Methods and results"),
        ],
    )
    source_before = pdf.read_bytes()
    receipt_path = tmp_path / "receipts" / "paper.json"
    command = _base_cli(pdf, tmp_path) + [
        "--render-page",
        "1",
        "--render-output-dir",
        str(tmp_path / "renders"),
        "--output",
        str(receipt_path),
    ]

    result = subprocess.run(command, check=False, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr or result.stdout
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    expected_identity = {
        "status": "pass",
        "work_id": "work-alpha",
        "artifact_id": "acquisition-paper-alpha",
        "parent_artifact_id": "not_applicable",
        "paper_id": "work-alpha",
        "parent_paper_id": "not_applicable",
        "artifact_role": "main_paper",
        "version_identity": "Accepted working paper, March 2026",
        "doi_or_source_id": "10.1000/alpha.2026",
    }
    assert receipt["schema"] == "aris.method-harvest.pdf-inspection.v2"
    for field in (
        "work_id",
        "artifact_id",
        "parent_artifact_id",
        "paper_id",
        "parent_paper_id",
        "artifact_role",
        "version_identity",
        "doi_or_source_id",
    ):
        assert receipt[field] == expected_identity[field]
    assert receipt["artifact_identity"] == expected_identity
    assert receipt["source_pdf"] == "paper.pdf"
    assert receipt["source_pdf_sha256"] == hashlib.sha256(source_before).hexdigest()
    assert receipt["page_count"] == 2
    assert receipt["source_pdf_preserved"] is True
    assert pdf.read_bytes() == source_before

    render_evidence = receipt["render_evidence"]
    assert render_evidence["schema"] == "aris.method-harvest.render-evidence.v1"
    assert render_evidence["page_number_basis"] == "1-based PDF viewer page"
    assert render_evidence["source_pdf_sha256"] == receipt["source_pdf_sha256"]
    assert render_evidence["source_pdf_page_count"] == 2
    assert render_evidence["count"] == 1
    page = render_evidence["pages"][0]
    assert page["source_pdf_sha256"] == receipt["source_pdf_sha256"]
    assert page["source_pdf_page_count"] == 2
    assert page["viewer_page"] == 1
    assert page["png_path"] == "renders/acquisition-paper-alpha-p1.png"
    png = tmp_path / page["png_path"]
    png_bytes = png.read_bytes()
    assert page["png_sha256"] == hashlib.sha256(png_bytes).hexdigest()
    assert page["png_bytes"] == len(png_bytes)
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
    assert png_bytes[12:16] == b"IHDR"
    assert (page["width_px"], page["height_px"]) == struct.unpack(
        ">II", png_bytes[16:24]
    )
    assert page["renderer_tool"] == "pdftoppm"
    assert "pdftoppm" in page["renderer_version"].casefold()


def test_required_sparse_page_is_rendered_and_cleared_in_same_run(
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "paper.pdf"
    _write_pdf(pdf, [_long_page("Target Paper Alpha by Rivera"), ""])
    receipt_path = tmp_path / "paper.json"
    command = _base_cli(pdf, tmp_path) + [
        "--min-usable-ratio",
        "0.5",
        "--render-required-pages",
        "--visual-review-cleared-page",
        "2",
        "--render-output-dir",
        str(tmp_path / "renders"),
        "--output",
        str(receipt_path),
    ]

    result = subprocess.run(command, check=False, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr or result.stdout
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["ready_for_method_harvest"] is True
    assert receipt["text_layer"]["visual_review_required_pages"] == [2]
    assert receipt["text_layer"]["visual_review_cleared_pages"] == [2]
    assert receipt["text_layer"]["visual_review_pending_pages"] == []
    assert [page["viewer_page"] for page in receipt["render_evidence"]["pages"]] == [2]
    assert (tmp_path / "renders" / "acquisition-paper-alpha-p2.png").is_file()


def test_cli_accepts_companion_join_to_distinct_main_artifact(tmp_path: Path) -> None:
    pdf = tmp_path / "questionnaire.pdf"
    _write_pdf(pdf, [_long_page("Target Paper Alpha questionnaire by Rivera")])
    command = _base_cli(pdf, tmp_path) + [
        "--artifact-id",
        "acquisition-paper-alpha-questionnaire",
        "--parent-artifact-id",
        "acquisition-paper-alpha",
        "--artifact-role",
        "questionnaire",
        "--version-identity",
        "Publisher questionnaire supplement, March 2026",
        "--doi-or-source-id",
        "Publisher supplement record A-17",
    ]

    result = subprocess.run(command, check=False, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr or result.stdout
    receipt = json.loads(result.stdout)
    assert receipt["artifact_identity"]["work_id"] == "work-alpha"
    assert (
        receipt["artifact_identity"]["artifact_id"]
        == "acquisition-paper-alpha-questionnaire"
    )
    assert (
        receipt["artifact_identity"]["parent_artifact_id"]
        == "acquisition-paper-alpha"
    )
    assert receipt["artifact_identity"]["artifact_role"] == "questionnaire"


@pytest.mark.parametrize(
    ("extra_args", "expected_error"),
    [
        (
            ["--parent-artifact-id", "some-parent"],
            "main_paper requires parent_artifact_id=not_applicable",
        ),
        (
            [
                "--artifact-role",
                "questionnaire",
                "--parent-artifact-id",
                "acquisition-paper-alpha",
            ],
            "must differ from artifact_id",
        ),
        (
            ["--version-identity", "unknown"],
            "version_identity must be a specific non-placeholder value",
        ),
        (
            ["--expect-doi", "10.9999/wrong"],
            "expect-doi does not match the DOI embedded in doi_or_source_id",
        ),
    ],
)
def test_cli_rejects_inconsistent_artifact_identity(
    tmp_path: Path,
    extra_args: list[str],
    expected_error: str,
) -> None:
    pdf = tmp_path / "paper.pdf"
    _write_pdf(pdf, [_long_page("Target Paper Alpha by Rivera")])
    receipt_path = tmp_path / "error.json"
    command = _base_cli(pdf, tmp_path) + extra_args + ["--output", str(receipt_path)]

    result = subprocess.run(command, check=False, capture_output=True, text=True)

    assert result.returncode == 2
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["ok"] is False
    assert expected_error in receipt["error"]


def test_cli_rejects_visual_clear_without_same_run_render(tmp_path: Path) -> None:
    pdf = tmp_path / "paper.pdf"
    _write_pdf(pdf, [_long_page("Target Paper Alpha by Rivera"), ""])
    receipt_path = tmp_path / "error.json"
    command = _base_cli(pdf, tmp_path) + [
        "--min-usable-ratio",
        "0.5",
        "--visual-review-cleared-page",
        "2",
        "--output",
        str(receipt_path),
    ]

    result = subprocess.run(command, check=False, capture_output=True, text=True)

    assert result.returncode == 2
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert "must be rendered by the same inspector run" in receipt["error"]
    assert not (tmp_path / "renders").exists()


def test_cli_rejects_out_of_range_or_non_repository_render_targets(
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "paper.pdf"
    _write_pdf(pdf, [_long_page("Target Paper Alpha by Rivera")])

    out_of_range = subprocess.run(
        _base_cli(pdf, tmp_path)
        + [
            "--render-page",
            "2",
            "--render-output-dir",
            str(tmp_path / "renders"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert out_of_range.returncode == 2
    assert "outside the 1-based PDF viewer-page range" in out_of_range.stdout

    outside_dir = tmp_path.parent / f"{tmp_path.name}-outside"
    outside = subprocess.run(
        _base_cli(pdf, tmp_path)
        + [
            "--render-page",
            "1",
            "--render-output-dir",
            str(outside_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert outside.returncode == 2
    assert "render output must remain inside repository root" in outside.stdout
    assert not outside_dir.exists()


def test_cli_never_overwrites_different_render_bytes(tmp_path: Path) -> None:
    pdf = tmp_path / "paper.pdf"
    _write_pdf(pdf, [_long_page("Target Paper Alpha by Rivera")])
    render_dir = tmp_path / "renders"
    render_dir.mkdir()
    destination = render_dir / "acquisition-paper-alpha-p1.png"
    destination.write_bytes(b"existing-user-bytes")

    result = subprocess.run(
        _base_cli(pdf, tmp_path)
        + [
            "--render-page",
            "1",
            "--render-output-dir",
            str(render_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "already exists with different bytes" in result.stdout
    assert destination.read_bytes() == b"existing-user-bytes"
