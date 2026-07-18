from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS = REPO_ROOT / "skills"


class BusinessLiteratureSynthesisContractTests(unittest.TestCase):
    @staticmethod
    def _read(*parts: str) -> str:
        return (SKILLS.joinpath(*parts)).read_text(encoding="utf-8")

    def test_lit_review_has_distinct_map_and_fulltext_modes(self) -> None:
        skill = (SKILLS / "business-lit-review" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("`map`", skill)
        self.assertIn("`fulltext_synthesis`", skill)
        self.assertIn("LITERATURE_EVIDENCE_MATRIX.md", skill)
        self.assertIn("Do not let abstract-only rows", skill)

    def test_fulltext_matrix_preserves_variable_and_result_provenance(self) -> None:
        reference = (
            SKILLS / "business-lit-review" / "references" / "fulltext-synthesis.md"
        ).read_text(encoding="utf-8")
        for required in (
            "exact numerator, denominator, transform",
            "winsorization, standardization",
            "Main, null, and mixed results",
            "source_locations",
            "claim_ceiling",
        ):
            self.assertIn(required, reference)

    def test_method_card_covers_synthesis_fields(self) -> None:
        template = self._read(
            "method-harvest", "references", "method-card-template.md"
        )
        for required in (
            "Research Question, Theory, And Predictions",
            "exact_formula_or_coding",
            "Main And Null/Mixed Results",
            "Limitations And Claim Ceiling",
            "business-lit-review",
        ):
            self.assertIn(required, template)

    def test_artifact_identity_joins_manifest_processing_card_and_synthesis(self) -> None:
        template = self._read(
            "method-harvest", "references", "method-card-template.md"
        )
        synthesis = self._read(
            "business-lit-review", "references", "fulltext-synthesis.md"
        )
        for required in (
            "work_id",
            "artifact_id",
            "parent_artifact_id",
            "artifact_role",
            "version_identity",
            "doi_or_source_id",
        ):
            self.assertIn(required, template)
            self.assertIn(required, synthesis)
        self.assertIn("joins exactly to one manifest row", synthesis)
        self.assertIn("Same-work alternate downloads", synthesis)

    def test_pdf_processing_is_deterministic_and_page_grounded(self) -> None:
        skill = self._read("method-harvest", "SKILL.md")
        reference = self._read(
            "method-harvest", "references", "pdf-processing.md"
        )
        template = self._read(
            "method-harvest", "references", "method-card-template.md"
        )
        for required in (
            "scripts/inspect_pdf.py",
            "text-layer coverage",
            "source PDF immutable",
            "Render and visually check",
        ):
            self.assertIn(required, skill)
        for required in (
            "native_text",
            "mixed_text_review",
            "ocr_required",
            "original-viewer-page → derivative-page map",
            "OCR is a transcription aid, not ground truth",
            "Two-Pass Reading",
        ):
            self.assertIn(required, reference)
        for required in (
            "pdf_processing_receipt",
            "source_pdf_sha256",
            "text_layer_classification",
            "extracted_text_sha256",
            "original_to_derivative_page_map",
            "visual_spot_checks",
        ):
            self.assertIn(required, template)

    def test_zotero_parent_attachment_and_hash_lineage_is_explicit(self) -> None:
        fulltext = self._read("fulltext-acquire", "SKILL.md")
        zotero = self._read("fulltext-acquire", "references", "zotero.md")
        template = self._read(
            "method-harvest", "references", "method-card-template.md"
        )
        self.assertIn("references/zotero.md", fulltext)
        for required in (
            "Bibliographic parent item",
            "Attachment child item",
            "storage:<filename>",
            "attachments:<relative-path>",
            "do not silently create/import a Zotero item",
            "no Zotero write occurred",
        ):
            self.assertIn(required, zotero)
        self.assertIn("zotero_parent_item_key", template)
        self.assertIn("zotero_attachment_item_key", template)
        self.assertIn("never treat the attachment child as the bibliographic parent", template)

    def test_fulltext_manifest_preserves_companion_roles_and_browser_receipt(self) -> None:
        fulltext = self._read("fulltext-acquire", "SKILL.md")
        manifest = self._read("fulltext-acquire", "references", "manifest.md")
        template = self._read(
            "method-harvest", "references", "method-card-template.md"
        )
        self.assertIn("for each required artifact role", fulltext)
        self.assertIn("main_paper", fulltext)
        self.assertIn("online_appendix", fulltext)
        self.assertIn("does not satisfy a separately hosted required appendix", fulltext)
        for required in (
            "work_id",
            "artifact_id",
            "parent_artifact_id",
            "artifact_role",
            "version_identity",
            "identity_evidence",
            "browser_receipt",
            "local_path_or_gap",
        ):
            self.assertIn(required, manifest)
        self.assertIn("### Companion Documents", template)
        self.assertIn("relationship_to_main", template)

    def test_method_card_requires_construct_and_unit_audits(self) -> None:
        template = self._read(
            "method-harvest", "references", "method-card-template.md"
        )
        for required in (
            "construct_depth",
            "espoused_value",
            "promotion_artifact",
            "enacted_norm",
            "domain_specific_practice",
            "respondent_unit",
            "response_n",
            "unique_entity_n",
            "estimand_unit",
            "cluster_unit",
            "cluster_matches_dependence",
        ):
            self.assertIn(required, template)

    def test_method_card_requires_index_and_questionnaire_provenance(self) -> None:
        template = self._read(
            "method-harvest", "references", "method-card-template.md"
        )
        for required in (
            "Factor / Index Construction Audit",
            "input_transforms_and_zero_handling",
            "weights_or_loadings",
            "factor_count_and_retention",
            "rotation",
            "score_method",
            "explained_variance",
            "index_reproducibility",
            "Questionnaire / Scale Provenance Audit",
            "administered_version_identity",
            "item_texts_and_item_codes",
            "unsigned_magnitude",
            "reverse_coded_items_and_direction",
            "missing_item_rule",
            "questionnaire_vs_table_reconciliation",
        ):
            self.assertIn(required, template)

    def test_method_card_requires_numeric_consistency_hard_gate(self) -> None:
        template = self._read(
            "method-harvest", "references", "method-card-template.md"
        )
        skill = self._read("method-harvest", "SKILL.md")
        for required in (
            "numeric_audit_status",
            "recomputed_estimate_over_se",
            "p_or_star_check",
            "prose_vs_table",
            "sample_n_check",
            "indirect_effect_check",
        ):
            self.assertIn(required, template)
        self.assertIn("numeric consistency audit for every material reported estimate", skill)
        self.assertIn("ready_for_design=no", skill)
        self.assertIn("not a typo to repair", skill)

    def test_method_card_requires_complete_mediation_fields(self) -> None:
        template = self._read(
            "method-harvest", "references", "method-card-template.md"
        )
        for required in (
            "Mediation Evidence Audit",
            "temporal_order",
            "path_a",
            "path_b",
            "total_effect_c",
            "direct_effect_c_prime",
            "indirect_effect_a_times_b",
            "indirect_se",
            "bootstrap_resamples",
            "confidence_interval",
            "common_method_assessment",
            "significance_steps_only",
        ):
            self.assertIn(required, template)

    def test_unknowns_are_explicit_and_never_backfilled_by_convention(self) -> None:
        method = self._read("method-harvest", "SKILL.md")
        synthesis = self._read(
            "business-lit-review", "references", "fulltext-synthesis.md"
        )
        self.assertIn("Do not use domain convention to fill a required field", method)
        self.assertIn("A blank cell is not an accepted unknown", synthesis)
        self.assertIn("Do not infer a log-plus-one convention", synthesis)
        self.assertIn("unique-firm count must be `unknown`", synthesis)

    def test_fulltext_synthesis_propagates_all_method_audits(self) -> None:
        synthesis = self._read(
            "business-lit-review", "references", "fulltext-synthesis.md"
        )
        for required in (
            "Observation And Dependence Audit",
            "Factor / Index Reproducibility Audit",
            "Questionnaire / Scale Provenance Audit",
            "Numeric Consistency Audit",
            "Mediation Evidence Audit",
            "construct_depth",
            "numeric_audit_status",
            "mediation_evidence_status",
        ):
            self.assertIn(required, synthesis)

    def test_fixed_corpus_overrides_map_count_without_scope_expansion(self) -> None:
        skill = self._read("business-lit-review", "SKILL.md")
        synthesis = self._read(
            "business-lit-review", "references", "fulltext-synthesis.md"
        )
        self.assertIn("In `map` mode, include", skill)
        self.assertIn("fixed corpus overrides the 8–15 discovery target", skill)
        self.assertIn("fixed corpus overrides the discovery-map target", synthesis)
        self.assertIn("HANDOFF_INCOMPLETE", synthesis)

    def test_pdf_and_printed_page_locations_are_unambiguous(self) -> None:
        template = self._read(
            "method-harvest", "references", "method-card-template.md"
        )
        synthesis = self._read(
            "business-lit-review", "references", "fulltext-synthesis.md"
        )
        self.assertIn("`PDF p.<viewer-page>`", template)
        self.assertIn("printed p.<page>", template)
        self.assertIn("never use an unlabeled page number", synthesis)

    def test_pipeline_returns_to_lit_review_after_method_cards(self) -> None:
        pipeline = (SKILLS / "business-research-pipeline" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("business-lit-review fulltext_synthesis", pipeline)
        self.assertIn("Stage 2 is incomplete", pipeline)

    def test_acceptance_has_fulltext_synthesis_gate(self) -> None:
        acceptance = (REPO_ROOT / "docs" / "BUSINESS_RESEARCH_E2E_ACCEPTANCE.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("P3 fulltext literature synthesis", acceptance)
        self.assertIn("Exact variable construction", acceptance)


if __name__ == "__main__":
    unittest.main()
