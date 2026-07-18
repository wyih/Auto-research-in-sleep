# Business Handoff Schemas

Use these schemas when business/accounting/finance skills hand material to the next phase. Missing required fields should be marked `HANDOFF_INCOMPLETE` instead of guessed.

## BUSINESS_LIT_REVIEW.md

Required:

- `research_area`
- `target_journals`
- `core_conversation`
- `closest_papers`
- `gap_types`
- `methods_norms`
- `open_questions`
- `source_grounding` when fulltext synthesis was run
- `construct_measure_comparisons` when fulltext synthesis was run
- `agreement_conflict_diagnosis` when fulltext synthesis was run

## LITERATURE_EVIDENCE_MATRIX.md

Required per core fulltext paper:

- `paper_id_and_content_hash`
- `research_question_and_mechanism`
- `sample_setting_and_period`
- `constructs_and_exact_variable_construction`
- `data_sources_grain_and_keys`
- `design_identifying_variation_and_inference`
- `main_null_and_mixed_results`
- `robustness_limitations_and_boundaries`
- `claim_ceiling`
- `page_table_appendix_locations`

Required across papers:

- `construct_measure_comparability`
- `agreement_and_conflict_classification`
- `reusable_variable_dictionary_candidates`
- `unresolved_fulltext_fields`

## BUSINESS_IDEA_REPORT.md

Required:

- `candidate_research_questions`
- `selected_research_question`
- `setting`
- `theory_channel`
- `data_path`
- `identification_path`
- `novelty_risks`
- `decision_needed`

## FULLTEXT_MANIFEST.md

Required per target:

- `work_id` (stable across versions/channels and shared with METHOD_CARD/synthesis)
- `artifact_id` (unique acquired/gap artifact row)
- `parent_artifact_id` (`not_applicable` for the main paper; exact main artifact ID for a companion)
- `artifact_role` (`main_paper`, `online_appendix`, `questionnaire`, `codebook`, or `supplement`)
- `version_identity`
- `title`
- `identity_evidence`
- `channel`
- `status`
- `local_path_or_gap`
- `size_bytes`
- `sha256`
- `browser_receipt` when a protected session was used

Use one row per required artifact role and acquisition/version. A separate companion artifact retains its own artifact ID/path/hash and cannot be represented as part of the main PDF by implication. PDF-processing lineage must repeat the work/artifact/parent/role/version identity so the join can be checked mechanically.

## METHOD_CARD.md

Required:

- `bibliographic_identity`
- `local_pdf_path`
- `content_hash`
- `pdf_processing_receipt`
- `text_or_ocr_route_and_page_map`
- `companion_documents_and_hashes`
- `sample_and_period`
- `identification_strategy`
- `research_question_theory_and_predictions`
- `variables_and_construction`
- `fixed_effects_and_inference`
- `data_sources_and_merge_keys`
- `main_null_and_mixed_results`
- `robustness_limitations_and_claim_ceiling`
- `source_locations`
- `unknowns_and_design_implications`

## RESEARCH_DESIGN.md

Required:

- `research_question`
- `unit_of_analysis`
- `sample_definition`
- `data_sources`
- `variable_dictionary`
- `baseline_specification`
- `identification_assumptions`
- `fixed_effects`
- `clustering`
- `table_shells`
- `known_threats`

## RESULTS_SUMMARY.md

Required:

- `analysis_backend`
- `run_id`
- `sample_period`
- `sample_size`
- `tables`
- `figures`
- `headline_results`
- `null_or_mixed_results`
- `robustness_status`
- `open_analysis_issues`

## DATA_MANIFEST.md

Required per extract:

- `source_and_table`
- `query_program_or_download_spec`
- `filters_and_universe`
- `local_path`
- `format`
- `schema_and_row_grain`
- `row_and_column_counts`
- `content_hash`
- `pulled_at`
- `status_and_access_gap`
- `browser_receipt` for protected portal exports

## RESULTS_DOCX_MANIFEST.md

Required:

- `source_outputs`
- `generator_and_run_id`
- `docx_path`
- `content_hash`
- `table_and_figure_inventory`
- `rendered_pages`
- `visual_qa_status`
- `author_metadata_check`

## CLAIMS_FROM_EVIDENCE.md

Required:

- `claim_verdicts`
- `supported_level`
- `evidence_source`
- `confidence`
- `required_caveat`
- `safe_language`
- `language_to_avoid`
- `missing_evidence`

## BUSINESS_NUMBER_AUDIT.md

Required:

- `gate`
- `automated_number_check`
- `claim_trace_table`
- `specification_mismatches`
- `issues_added_to_ledger`
- `required_follow_up`

## SOURCE_CLAIM_AUDIT.md

Required:

- `gate`
- `claim_inventory`
- `source_support_table`
- `unverified_or_distorted_claims`
- `citation_repairs`
- `required_follow_up`

## BUSINESS_RUN_PASSPORT.md

Required:

- `project_identity`
- `current_stage`
- `materials`
- `data_access_level`
- `analysis_backend`
- `artifact_index`
- `decision_log`
- `audit_status`
- `repro_lock`
