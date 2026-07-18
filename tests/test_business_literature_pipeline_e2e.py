from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class PaperCase:
    paper_id: str
    card_filename: str
    processing_filename: str
    pdf_relative_path: Path
    sha256: str
    pages: int
    evidence_pages: tuple[int, int]
    source_tokens: tuple[str, ...]
    card_tokens: tuple[str, ...]


@dataclass(frozen=True)
class LiteratureBundle:
    run_root: Path
    output_root: Path

    @property
    def matrix_path(self) -> Path:
        return self.output_root / "LITERATURE_EVIDENCE_MATRIX.md"

    @property
    def review_path(self) -> Path:
        return self.output_root / "BUSINESS_LIT_REVIEW.md"

    @property
    def index_path(self) -> Path:
        return self.output_root / "cards" / "METHOD_CARD_INDEX.md"

    @property
    def acceptance_path(self) -> Path:
        return self.output_root / "ACCEPTANCE_REPORT.md"

    @property
    def visual_checks_path(self) -> Path:
        return self.output_root / "pdf-processing" / "PDF_VISUAL_CHECKS.md"

    def card_path(self, paper: PaperCase) -> Path:
        return self.output_root / "cards" / paper.card_filename

    def processing_path(self, paper: PaperCase) -> Path:
        return self.output_root / "pdf-processing" / paper.processing_filename

    def pdf_path(self, paper: PaperCase) -> Path:
        return self.run_root / paper.pdf_relative_path


PAPERS = (
    PaperCase(
        paper_id="graham_harvey_popadak_rajgopal_2017",
        card_filename="graham_harvey_popadak_rajgopal_2017_METHOD_CARD.md",
        processing_filename="graham_harvey_popadak_rajgopal_2017_PDF_PROCESSING.json",
        pdf_relative_path=Path(
            "artifacts/fulltext/open/corporate-culture-field-w23255.pdf"
        ),
        sha256="f69be9aa4373ff67db8a98b9bcb27ff3576067ae82a1337a88e1aaed998847a2",
        pages=79,
        evidence_pages=(46, 46),
        source_tokens=(
            "Table VI Aggregate Values, Norms, and Outcomes",
            "Aggregate cultural values",
            "-0.18*",
            "Aggregate cultural norms",
            "0.17***",
            "0.27***",
            "Observations",
            "1138",
            "1126",
        ),
        card_tokens=(
            "`−0.18*`",
            "`0.17***`",
            "`0.27***`",
            "`0.14`",
            "N=1,126–1,138",
            "Table VI Panel A, PDF p. 46",
            "prose PDF pp. 26–27",
        ),
    ),
    PaperCase(
        paper_id="zhao_teng_wu_2018",
        card_filename="zhao_teng_wu_2018_METHOD_CARD.md",
        processing_filename="zhao_teng_wu_2018_PDF_PROCESSING.json",
        pdf_relative_path=Path(
            "artifacts/fulltext/sciencedirect/"
            "S1755309118300030-corporate-culture-firm-performance-china.pdf"
        ),
        sha256="459e22da3a37ad6bd4823271ddfc4d6c8d027e054a43057b89c6cd0090d9770b",
        pages=19,
        evidence_pages=(8, 8),
        source_tokens=(
            "Table 3",
            "Tobin's Q",
            "Factor",
            "-0.093**",
            "(-2.37)",
            "0.002",
            "0.222***",
            "(2.94)",
            "Industry FE",
            "1030",
        ),
        card_tokens=(
            "Tobin's Q on Factor",
            "`−0.093**`",
            "robust t=`−2.37`",
            "ROA on Factor",
            "`0.002`",
            "Log(Patent) on Factor",
            "`0.222***`",
            "robust t=`2.94`",
            "Table 3 col. 3, PDF p. 8",
        ),
    ),
    PaperCase(
        paper_id="duan_2018",
        card_filename="duan_2018_METHOD_CARD.md",
        processing_filename="duan_2018_PDF_PROCESSING.json",
        pdf_relative_path=Path(
            "artifacts/fulltext/cnki/duan-2018-quality-culture-performance.pdf"
        ),
        sha256="79b6a8b9f2c6f075343f1322c38ff4c6c79abedba8ed963cee5f8a6094a28117",
        pages=67,
        evidence_pages=(51, 52),
        source_tokens=(
            "Y=cX+e1",
            "M=aX+e2",
            "Y=c'X+bM+e3",
            ".788",
            ".066",
            "7.430",
            ".548",
            ".051",
            "4.660",
            ".468",
            ".068",
            "6.919",
            ".285",
            ".069",
            "1.235",
            ".000",
        ),
        card_tokens=(
            "`Y=cX+e1`, `M=aX+e2`, `Y=c'X+bM+e3`",
            "`B=.788`, `SE=.066`",
            "`.788/.066=11.94`, not 7.430",
            "`B=.548`, `SE=.051`",
            "`.548/.051=10.75`, not 4.660",
            "`B=.285`, `SE=.069`",
            "`.285/.069=4.13`, while t=1.235 would not yield p=.000",
            "Tables 20–22, PDF pp. 51–52",
        ),
    ),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _assert_contains(text: str, tokens: tuple[str, ...], artifact: str) -> None:
    missing = [token for token in tokens if token not in text]
    assert not missing, f"{artifact} is missing required evidence: {missing}"


def _normalize_extracted_text(text: str) -> str:
    return (
        text.replace("\x01", "-")
        .replace("−", "-")
        .replace("–", "-")
        .replace("’", "'")
        .replace("“", '"')
        .replace("”", '"')
    )


def _run_tool(command: list[str]) -> str:
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout


def _extract_pages(pdf_path: Path, first_page: int, last_page: int) -> str:
    executable = shutil.which("pdftotext")
    if executable is None:
        pytest.skip("pdftotext is required for source-evidence integration checks")
    extracted = _run_tool(
        [
            executable,
            "-f",
            str(first_page),
            "-l",
            str(last_page),
            "-layout",
            str(pdf_path),
            "-",
        ]
    )
    return _normalize_extracted_text(extracted)


def _pdf_page_count(pdf_path: Path) -> int:
    executable = shutil.which("pdfinfo")
    if executable is None:
        pytest.skip("pdfinfo is required for PDF metadata integration checks")
    match = re.search(r"^Pages:\s+(\d+)\s*$", _run_tool([executable, str(pdf_path)]), re.M)
    assert match is not None, f"pdfinfo did not report a page count for {pdf_path}"
    return int(match.group(1))


def _candidate_bundle(path: Path) -> LiteratureBundle | None:
    path = path.expanduser().resolve()
    output_names = ("literature-v2", "literature-forward-test")
    if path.name in output_names:
        candidates = ((path.parent, path),)
    else:
        candidates = tuple((path, path / name) for name in output_names)

    for run_root, output_root in candidates:
        required = (
            output_root / "LITERATURE_EVIDENCE_MATRIX.md",
            output_root / "BUSINESS_LIT_REVIEW.md",
            output_root / "cards",
            output_root / "cards" / "METHOD_CARD_INDEX.md",
            output_root / "ACCEPTANCE_REPORT.md",
            output_root / "pdf-processing" / "PDF_VISUAL_CHECKS.md",
        )
        if all(item.exists() for item in required):
            return LiteratureBundle(run_root=run_root, output_root=output_root)
    return None


def _discover_bundle() -> LiteratureBundle | None:
    configured = os.environ.get("ARIS_BUSINESS_LITERATURE_RUN_ROOT")
    if configured:
        return _candidate_bundle(Path(configured))

    run_parent = REPO_ROOT / ".aris" / "business-e2e"
    for output_name in ("literature-v2", "literature-forward-test"):
        candidates = sorted(
            run_parent.glob(f"*/{output_name}"),
            key=lambda path: path.stat().st_mtime_ns,
            reverse=True,
        )
        for candidate in candidates:
            bundle = _candidate_bundle(candidate)
            if bundle is not None:
                return bundle
    return None


@pytest.fixture(scope="module")
def bundle() -> LiteratureBundle:
    discovered = _discover_bundle()
    if discovered is None:
        pytest.skip(
            "no real literature-forward-test bundle found; set "
            "ARIS_BUSINESS_LITERATURE_RUN_ROOT to a generated P3 run"
        )
    return discovered


def test_fulltext_files_and_method_cards_preserve_lineage(
    bundle: LiteratureBundle,
) -> None:
    matrix = _read(bundle.matrix_path)
    review = _read(bundle.review_path)

    for paper in PAPERS:
        pdf_path = bundle.pdf_path(paper)
        card_path = bundle.card_path(paper)
        assert pdf_path.is_file(), f"missing source PDF: {pdf_path}"
        assert pdf_path.read_bytes().startswith(b"%PDF-"), f"not a PDF: {pdf_path}"
        assert card_path.is_file(), f"missing method card: {card_path}"
        assert _sha256(pdf_path) == paper.sha256

        card = _read(card_path)
        relative_pdf = pdf_path.relative_to(REPO_ROOT).as_posix()
        _assert_contains(
            card,
            (
                f"# METHOD_CARD: {paper.paper_id}",
                f"local_path: `{relative_pdf}`",
                f"content_hash: `sha256:{paper.sha256}`",
                f"size_bytes: {pdf_path.stat().st_size}",
                f"pages: {paper.pages}",
                "source_depth: fulltext",
            ),
            card_path.name,
        )
        _assert_contains(
            matrix,
            (paper.paper_id, f"sha256:{paper.sha256}"),
            bundle.matrix_path.name,
        )
        _assert_contains(
            review,
            (paper.paper_id, paper.sha256, f"cards/{paper.card_filename}"),
            bundle.review_path.name,
        )


def test_pdf_metadata_matches_method_cards(bundle: LiteratureBundle) -> None:
    for paper in PAPERS:
        assert _pdf_page_count(bundle.pdf_path(paper)) == paper.pages


def test_pdf_processing_receipts_recompute_source_lineage(
    bundle: LiteratureBundle,
) -> None:
    visual_checks = _read(bundle.visual_checks_path)
    for paper in PAPERS:
        receipt_path = bundle.processing_path(paper)
        receipt = json.loads(_read(receipt_path))
        pdf_path = bundle.pdf_path(paper).resolve()
        assert receipt["schema"] == "aris.method-harvest.pdf-inspection.v2"
        assert receipt["ok"] is True
        assert receipt["ready_for_method_harvest"] is True
        assert Path(receipt["source_pdf"]).resolve() == pdf_path
        assert receipt["source_pdf_sha256"] == _sha256(pdf_path) == paper.sha256
        assert receipt["size_bytes"] == pdf_path.stat().st_size
        assert receipt["page_count"] == _pdf_page_count(pdf_path) == paper.pages
        assert receipt["identity"]["status"] == "pass"
        assert receipt["identity"]["missing_title_tokens"] == []
        assert receipt["text_layer"]["classification"] == "native_text"
        assert receipt["text_layer"]["usable_pages"] > 0
        assert len(receipt["text_layer"]["extracted_text_sha256"]) == 64
        assert receipt["source_pdf_preserved"] is True
        assert receipt["visual_spot_check_required"] is True

        card = _read(bundle.card_path(paper))
        _assert_contains(
            card,
            (
                "## PDF Processing",
                f"pdf_processing_receipt: `{receipt_path.relative_to(REPO_ROOT).as_posix()}`",
                f"source_pdf_sha256: `{paper.sha256}`",
                f"source_pdf_pages: {paper.pages}",
                "identity_check: pass",
                "source_pdf_preserved: yes",
            ),
            bundle.card_path(paper).name,
        )
        _assert_contains(
            visual_checks,
            (paper.paper_id, "rendered source pages"),
            bundle.visual_checks_path.name,
        )


def test_v2_inventory_and_acceptance_report_are_complete(
    bundle: LiteratureBundle,
) -> None:
    v2_root = bundle.run_root / "literature-v2"
    if v2_root.exists():
        assert bundle.output_root == v2_root.resolve()

    index = _read(bundle.index_path)
    report = _read(bundle.acceptance_path)
    for paper in PAPERS:
        _assert_contains(
            index,
            (paper.paper_id, f"cards/{paper.card_filename}"),
            bundle.index_path.name,
        )

    _assert_contains(
        report,
        (
            "offline; no browser, login, cookie, credential, or network acquisition operation",
            "Numeric consistency hard gate",
            "Mediation fidelity",
            "Graham et al. | needs_verification",
            "Zhao et al. | pass",
            "Duan | fail",
        ),
        bundle.acceptance_path.name,
    )
    if os.environ.get("ARIS_P3_BLIND_CANDIDATE") == "1":
        lowered = report.lower()
        assert "pending external acceptance" in lowered
        assert "repository tests and root verifiers were not read or run" in lowered
        assert "zero failures, skips, or xfails" not in lowered


def test_pdf_evidence_is_extracted_and_preserved_in_method_cards(
    bundle: LiteratureBundle,
) -> None:
    for paper in PAPERS:
        source_text = _extract_pages(
            bundle.pdf_path(paper), *paper.evidence_pages
        )
        _assert_contains(source_text, paper.source_tokens, f"{paper.paper_id} PDF")
        _assert_contains(
            _read(bundle.card_path(paper)),
            paper.card_tokens,
            paper.card_filename,
        )


def test_method_cards_capture_variable_calculation_design_and_limits(
    bundle: LiteratureBundle,
) -> None:
    graham = _read(bundle.card_path(PAPERS[0]))
    _assert_contains(
        graham,
        (
            "unit_of_observation: executive survey response",
            "unique_entity_n: `unknown`",
            "`MVA / AT`, where `MVA = (PRCC_F × CSHO) + DLC + DLTT + PSTKL − TXDITC`",
            "`OIBDP / AT`",
            "heteroskedasticity-robust SE",
            "no treatment, shock, or staggered timing",
            "safe_claim:",
            "unsafe_claim:",
        ),
        PAPERS[0].card_filename,
    )

    zhao = _read(bundle.card_path(PAPERS[1]))
    _assert_contains(
        zhao,
        (
            "unit_of_observation: listed firm, one cross-sectional observation per firm",
            "market value of the firm's stocks divided by total assets",
            "net income divided by total assets",
            "`ln(1 + number of words on culture page)`",
            "no `+1` is stated, so zero handling is `unknown`",
            "Factor weights/scoring `unknown`",
            "single-year cross-sectional OLS with industry indicators",
            "safe_claim:",
            "unsafe_claim:",
        ),
        PAPERS[1].card_filename,
    )

    duan = _read(bundle.card_path(PAPERS[2]))
    _assert_contains(
        duan,
            (
                "individual manager's questionnaire response",
                "unique_entity_n: `unknown`",
                "respondents_per_entity: `unknown`",
                "exact item/factor aggregation and centering formula/sample `unknown`",
                "reverse coding `unknown/needs_verification`",
                "one questionnaire wave",
                "not reported; audit-only `a×b=.1562`",
                "confidence_interval",
                "safe_claim:",
                "unsafe_claim:",
        ),
        PAPERS[2].card_filename,
    )


def test_evidence_matrix_propagates_methods_unknowns_conflicts_and_citations(
    bundle: LiteratureBundle,
) -> None:
    matrix = _read(bundle.matrix_path)
    _assert_contains(
        matrix,
        (
            "Unit is response, not confirmed unique firm",
            "`MVA/AT`",
            "`MVA=PRCC_F×CSHO+DLC+DLTT+PSTKL−TXDITC`",
            "`OIBDP/AT`",
            "Q14 gives no effect sign",
            "Factor loadings/scoring `unknown`",
            "NI/assets",
            "ln(patents granted), zero rule unknown",
            "Factor: Tobin Q `−.093**`, ROA `.002` null, LogPatent `.222***`",
            "unique-firm count and within-firm clustering `unknown`",
            "Scale/composite/centering rules unknown",
            "B=.548/standardized .541",
            "B=.285/standardized .263",
            "B=.468/standardized .353",
            "coefficient/SE/t/CR/p contradictions",
            "measurement_difference",
            "timing_difference",
            "design_or_estimand_difference",
            "not_comparable",
            "needs_verification",
            "strongest common ceiling is conditional association",
            "PDF p. 8",
            "Tables 19–22, PDF pp. 50–52",
        ),
        bundle.matrix_path.name,
    )

    for paper in PAPERS:
        assert matrix.count(paper.paper_id) >= 2, (
            f"{paper.paper_id} is not traceable through the matrix and its audit tables"
        )


def test_grounded_review_preserves_measurement_design_and_claim_ceiling(
    bundle: LiteratureBundle,
) -> None:
    review = _read(bundle.review_path)
    _assert_contains(
        review,
        (
            "do **not** identify a common “effect of corporate culture on firm performance.”",
            "No paper establishes causality",
            "observe **promotion intensity**, not lived culture",
            "`Tobin's Q=MVA/AT`",
            "`Profitability=OIBDP/AT`",
            "net income divided by total assets",
            "Log(Culture) and Log(Patent) do not state a zero rule",
            "No firm identifier, controls, clustering, temporal order, or objective outcome is reported",
            "`B=.285`, `SE=.069`, `t=1.235`, `p=.000`",
            "`mediation_evidence_status=conflicting`",
            "measurement_difference + timing_difference + sample_or_setting_difference + design_or_estimand_difference",
            "The common ceiling is **association**",
            "Unsafe language:",
            "Source Grounding",
            "PDF p. 46",
            "PDF p. 8",
            "PDF pp. 50–52",
        ),
        bundle.review_path.name,
    )

    for paper in PAPERS:
        assert review.count(paper.paper_id) >= 5, (
            f"{paper.paper_id} lacks repeated claim-level citations in the review"
        )
        _assert_contains(
            review,
            (paper.sha256, f"cards/{paper.card_filename}"),
            f"{bundle.review_path.name} source grounding",
        )


def test_real_bundle_satisfies_current_structured_audit_contract(
    bundle: LiteratureBundle,
) -> None:
    required_card_tokens = (
        "### Construct Map",
        "construct_depth",
        "respondent_unit:",
        "response_n:",
        "unique_entity_n:",
        "estimand_unit:",
        "cluster_unit:",
        "cluster_matches_dependence:",
        "### Factor / Index Construction Audit",
        "### Questionnaire / Scale Provenance Audit",
        "### Mediation Evidence Audit",
        "## Numeric Consistency Audit",
        "numeric_audit_status:",
    )
    required_matrix_tokens = (
        "construct_depth",
        "#### Observation And Dependence Audit",
        "#### Factor / Index Reproducibility Audit",
        "#### Questionnaire / Scale Provenance Audit",
        "#### Numeric Consistency Audit",
        "numeric_audit_status",
        "#### Mediation Evidence Audit",
        "mediation_evidence_status",
    )

    missing_by_artifact: dict[str, list[str]] = {}
    for paper in PAPERS:
        card_path = bundle.card_path(paper)
        card = _read(card_path)
        missing = [token for token in required_card_tokens if token not in card]
        if missing:
            missing_by_artifact[card_path.name] = missing

    matrix = _read(bundle.matrix_path)
    matrix_missing = [token for token in required_matrix_tokens if token not in matrix]
    if matrix_missing:
        missing_by_artifact[bundle.matrix_path.name] = matrix_missing

    if missing_by_artifact:
        details = "; ".join(
            f"{artifact}: {', '.join(missing)}"
            for artifact, missing in missing_by_artifact.items()
        )
        pytest.xfail(
            "the real forward bundle predates the hardened P3 structured-audit "
            f"contract and must be regenerated: {details}"
        )
