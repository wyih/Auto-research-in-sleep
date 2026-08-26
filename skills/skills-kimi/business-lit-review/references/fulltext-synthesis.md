# Fulltext Literature Synthesis

Use this reference only for `fulltext_synthesis` mode.

## Input Gate

For each core paper require:

- stable paper ID and bibliographic identity
- identity-matched local PDF and exact `FULLTEXT_MANIFEST` row
- an identical artifact tuple across manifest, PDF-processing receipt, METHOD_CARD, and synthesis receipt: `work_id`, `artifact_id`, `parent_artifact_id`, `artifact_role`, `version_identity`, and `doi_or_source_id`
- SHA-256 hash
- current PDF-processing receipt with page count, text/OCR route, identity result, and visual checks
- `source_depth=fulltext`
- a current `METHOD_CARD` with source locations
- a completed numeric consistency audit and explicit audit status

An abstract-only paper may remain in the discovery map but cannot support detailed claims about samples, variable construction, identification, inference, or table results.

If the user fixes the authorized corpus, use every supplied core paper and do not add papers merely to reach a count. The fixed corpus overrides the discovery-map target of 8–15 papers. Mark any unperformed discovery, venue-positioning, or closest-paper target `HANDOFF_INCOMPLETE` instead of expanding scope.

## Evidence Matrix

Write `LITERATURE_EVIDENCE_MATRIX.md` with one row per paper and stable paper IDs. Long definitions may use linked subsections beneath the main table.

| paper_id | question_and_mechanism | construct_depth | sample_units_and_dependence | measurement_reproducibility | data_and_keys | design_and_inference | main_null_and_numeric_audit | mediation_evidence | robustness_and_boundaries | claim_ceiling | source_locations |
|---|---|---|---|---|---|---|---|---|---|---|---|

For every focal variable record, when stated:

- conceptual construct and role (`Y`, treatment/key `X`, mediator, moderator, control)
- construct depth: `espoused_value`, `promotion_artifact`, `perceived_norm`, `enacted_norm`, `domain_specific_practice`, `effectiveness_or_outcome`, `other`, or `unknown`
- paper variable name
- exact numerator, denominator, transform, aggregation, coding rule, lag, window, and unit
- winsorization, standardization, zero-value handling, missing-value handling, and sign orientation
- vendor/source, table/file, grain, years, and join key
- page, table, appendix, or equation pointer

If a formula detail is missing, write `unknown`; do not reverse-engineer it from a label.

### Required Per-Paper Audit Subsections

Keep long fields below the main matrix and link them by `paper_id`.

#### Observation And Dependence Audit

| paper_id | observation_unit | respondent_unit | response_n | unique_entity_type | unique_entity_n | respondents_per_entity | estimand_unit | dependence_structure | cluster_unit | cluster_alignment | source_locations |
|---|---|---|---|---|---|---|---|---|---|---|---|

Never equate survey answers with unique firms or entities unless the fulltext establishes that one-to-one mapping. A missing unique-firm count must be `unknown`, not the response N.

#### Factor / Index Reproducibility Audit

| paper_id | variable | inputs | input_transforms_and_zero_handling | extraction_or_aggregation | standardization | weights_or_loadings | factor_count_retention_rotation | score_method | sign_orientation | explained_variance | missing_rule | index_reproducibility | source_locations |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Use `complete`, `partial`, `not_reproducible`, or `not_applicable`. Do not infer a log-plus-one convention, equal weights, factor weights, standardization, missing-value rule, or index sign from common practice.

#### Questionnaire / Scale Provenance Audit

| paper_id | scale | administered_version | original_citation | language_translation | response_anchors | item_texts_codes | item_or_outcome_directionality | reverse_items_and_direction | composite_formula_weights | missing_item_rule | questionnaire_table_reconciliation | provenance_status | source_locations |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Use `unsigned_magnitude` when a question records perceived effect size without its sign. Use `unknown` for an undisclosed version, item wording, translation, direction, or reverse-scoring rule even when the cited original scale is familiar.

#### Numeric Consistency Audit

| paper_id | claim_or_cell_id | estimate_se_vs_stat | sign | p_value_stars_ci | prose_vs_table | sample_n | indirect_effect_arithmetic | numeric_audit_status | discrepancy_and_claim_impact | source_locations |
|---|---|---|---|---|---|---|---|---|---|---|

Check every material main, null, mechanism, and mediation result. Recompute `estimate / SE` when estimate and SE are on the reported statistic's scale; check sign, p-value/stars/CI, prose versus table, and sample-N consistency. Record distribution and rounding tolerance. Do not silently repair source conflicts. A failed or unresolved material check must remain visible and lower design readiness or the claim ceiling.

#### Mediation Evidence Audit

| paper_id | mediator | temporal_order | path_a | path_b | total_effect_c | direct_effect_c_prime | indirect_effect_a_times_b | estimator_scale | indirect_se | test_method | bootstrap_resamples | confidence_interval | common_method_assessment | mediation_evidence_status | source_locations |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Distinguish `complete`, `partial`, `significance_steps_only`, `conflicting`, and `not_applicable`. Never describe a sequence of significant paths as a verified indirect effect when `a * b`, its estimator/test, and uncertainty are absent.

Every required cell must contain a source-supported value, `unknown`, `needs_verification`, or `not_applicable: <reason>`. A blank cell is not an accepted unknown.

## Comparison Discipline

Before comparing findings, check whether papers use the same:

1. construct depth rather than merely a similar label; distinguish espoused values, promotion artifacts, perceived or enacted norms, domain-specific practices, and effectiveness/outcomes
2. measurement source and respondent/data grain
3. observation, respondent, estimand, unique-entity, and cluster units
4. factor/index reproducibility or questionnaire version/item direction
5. outcome horizon and unit
6. sample population and institutional setting
7. identifying variation and comparison group
8. estimator, fixed effects, clustering, and weighting
9. numeric-audit and mediation-evidence status

Classify apparent disagreements as one of:

- `substantive_conflict`
- `measurement_difference`
- `sample_or_setting_difference`
- `design_or_estimand_difference`
- `timing_difference`
- `not_comparable`
- `needs_verification`

## Narrative Synthesis

Organize `BUSINESS_LIT_REVIEW.md` around questions, not paper order:

1. construct and theory conversation
2. measurement families and validity tradeoffs
3. data/settings and identification strength
4. findings, nulls, and genuine contradictions
5. boundary conditions and external-validity limits
6. closest-paper delta and remaining contribution
7. implications for the project's variable dictionary and design

Attach `(paper_id, PDF p.<viewer-page>, Table/Appendix)` pointers to material source-derived claims. If printed pagination differs, add `printed p.<page>` or `article p.<page>`; never use an unlabeled page number. Clearly label an inference made across papers as synthesis rather than a paper's own claim.

## Acceptance

- Matrix includes all core fulltext papers and content hashes.
- Every synthesis input is hash-bound to its PDF, processing receipt, and METHOD_CARD, and its artifact tuple joins exactly to one manifest row. Same-work alternate downloads are separate artifacts, never silently interchangeable inputs.
- Variable definitions preserve exact construction details or explicit unknowns.
- Construct depth and observation/respondent/unique-entity/cluster units are explicit.
- Factor/index and questionnaire audits expose weights, standardization, zero/missing rules, administered versions, items, and reverse scoring or explicit unknowns.
- Numeric consistency is an explicit hard gate; source conflicts are preserved and affect design readiness.
- Mediation claims expose temporal order, a, b, c, c-prime, indirect effect, test/CI, and common-method assessment or explicit unknowns.
- Main, null, and mixed results have source locations.
- Cross-paper disagreements are diagnosed before being narrated.
- Every narrative claim can be traced to matrix rows and source locations.
- Every core card traces to a current PDF-processing receipt; formulas and material table claims were visually checked rather than trusted from extraction alone.
- Claim language does not exceed the strongest relevant design's supported ceiling.
