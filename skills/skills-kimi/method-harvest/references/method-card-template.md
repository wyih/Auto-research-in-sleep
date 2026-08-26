# Method Card Template

Write one card per paper. Filename: `method-harvest/cards/<short_id>_METHOD_CARD.md` or a single `METHOD_CARD.md` when only one paper was requested.

Do not invent fields. Use `unknown` or `needs_verification` when the fulltext does not state the detail. If only abstract/metadata was available, set `source_depth: abstract_only`.

```markdown
# METHOD_CARD: <short_id>

## Bibliographic
- title:
- authors:
- year:
- venue_or_wp:
- doi_or_url:
- status: published | forthcoming | working_paper | preprint | needs_verification

## Fulltext
- fulltext_status: local | open | institutional_ip | browser_session | bot_challenge_passed | abstract_only | missing | gap | needs_verification
- fulltext_channel: zotero | ssrn | nber | author_page | cnki | sciencedirect | wiley | jstor | publisher | local | unknown
- zotero_parent_item_key: (required when `fulltext_channel=zotero`; otherwise `not_applicable`)
- zotero_attachment_item_key: (required when `fulltext_channel=zotero`; otherwise `not_applicable`)
- zotero_attachment_semantics: child attachment + stored/imported/linked locator semantics, or `unknown`; never treat the attachment child as the bibliographic parent
- local_path:
- content_hash:
- source_depth: fulltext | abstract_only | metadata_only
- location_convention: `PDF p.<viewer-page>` for the 1-based PDF viewer page; add `printed p.<page>` or `article p.<page>` when the source prints a different page number

## PDF Processing
- pdf_processing_receipt:
- work_id: stable METHOD_CARD/synthesis ID
- artifact_id: exact `FULLTEXT_MANIFEST` row for this PDF
- parent_artifact_id: `not_applicable` for a main paper; otherwise the main PDF's `artifact_id`
- artifact_role: main_paper | online_appendix | questionnaire | codebook | supplement
- version_identity:
- doi_or_source_id:
- source_pdf_sha256:
- source_pdf_pages:
- text_layer_classification: native_text | mixed_text_review | ocr_required
- extraction_tool_and_version:
- extracted_text_sha256:
- identity_check: pass | fail | needs_verification
- identity_evidence: title/authors/DOI/source record plus `PDF p.<viewer-page>`
- ocr_derivative_path_and_sha256: (`not_applicable` when native text)
- original_to_derivative_page_map: (`identity` when unchanged; otherwise explicit mapping)
- sparse_or_ocr_pages_reviewed:
- visual_spot_checks: definitions, sample flow, equation, result tables, and material appendices with viewer pages
- source_pdf_preserved: yes | no

### Companion Documents
| work_id | artifact_id | parent_artifact_id | artifact_role | version_identity | doi_or_source_id | local_path_or_gap | sha256 | pages | pdf_processing_receipt | relationship_to_main | source_locations_used |
|---|---|---|---|---|---|---|---|---:|---|---|---|
| | | not_applicable | main_paper | | | | | | | primary | |
| | | | online_appendix \| questionnaire \| codebook \| supplement | | | | | | | | |

List only roles required for this card. Copy the six identity fields exactly from the artifact's manifest row and inspector receipt. A separate appendix/questionnaire/codebook must retain its own artifact ID, parent link, hash, and processing receipt; never attribute its contents to the main PDF without its own viewer-page label.

## Why This Paper Matters For Us
- design / measure / setting / data angle (1–3 bullets)

## Research Question, Theory, And Predictions
- research_question:
- focal_constructs:
- proposed_mechanism:
- hypotheses_or_predictions:
- construct_definition_locations:

### Construct Map
| construct | role | construct_depth | operational_proxy | definition_and_boundary | source_location |
|---|---|---|---|---|---|
| | Y \| key_X \| mediator \| moderator \| control | espoused_value \| promotion_artifact \| perceived_norm \| enacted_norm \| domain_specific_practice \| effectiveness_or_outcome \| other \| unknown | | | |

## Sample
- unit_of_observation:
- respondent_unit: (or `not_applicable`)
- response_n: (or `unknown` / `not_applicable`)
- unique_entity_type: firm | person | facility | country | other | not_applicable | unknown
- unique_entity_n: (for example, unique-firm N; never equate responses with firms unless verified)
- respondents_per_entity:
- repeated_or_nested_responses:
- estimand_unit:
- dependence_structure:
- cluster_unit:
- cluster_matches_dependence: yes | no | unknown | not_applicable
- sample_period:
- geography_or_market:
- inclusion_filters:
- exclusion_filters:
- final_n: (or unknown)
- final_n_definition: observations | responses | unique_entities | other | unknown
- sample_notes:

## Identification
- design_family: panel_fe | did | staggered_did | event_study | iv | rd | matching | rct_or_survey | other
- treatment_or_key_x:
- timing_and_shock:
- control_or_comparison_group:
- identifying_variation:
- key_assumptions:
- threats_acknowledged:
- main_spec_summary: (conceptual; not necessarily LaTeX)

## Variables
### Outcomes
| name_in_paper | construct | exact_formula_or_coding | transform_lag_window_unit | source_and_grain | page_table_appendix |

### Treatments / Key Independent Variables
| name_in_paper | construct | exact_formula_or_coding | transform_lag_window_unit | source_and_grain | page_table_appendix |

### Mediators / Moderators
| name_in_paper | role | exact_formula_or_coding | interaction_or_timing | page_table_appendix |

### Controls
| name_in_paper | exact_formula_or_coding | transform_lag_window_unit | page_table_appendix |

### Construction Policies
- winsorization:
- standardization:
- aggregation_or_index_weights:
- zero_value_handling:
- missing_value_rule:
- sign_orientation:
- details_not_stated:

### Factor / Index Construction Audit
Complete one row for every factor, index, scale, or composite. Use `not_applicable` only when the variable is not constructed; otherwise use `unknown` for every unstated component.

| variable | input_items_or_variables | input_transforms_and_zero_handling | extraction_or_aggregation_method | standardization | weights_or_loadings | factor_count_and_retention | rotation | score_method | sign_orientation | explained_variance | missing_rule | index_reproducibility | source_location |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | | | | complete \| partial \| not_reproducible \| not_applicable | |

### Questionnaire / Scale Provenance Audit
Complete this block for every administered questionnaire or survey scale.

- administered_version_identity:
- original_scale_citation:
- language_and_translation_method:
- response_anchors:
- item_texts_and_item_codes:
- item_or_outcome_directionality: signed | unsigned_magnitude | ordered_direction | mixed | unknown | not_applicable
- reverse_coded_items_and_direction:
- composite_formula_and_weights:
- missing_item_rule:
- questionnaire_vs_table_reconciliation:
- scale_provenance_status: verified | partial | conflicting | unknown | not_applicable
- source_locations:

### Fixed Effects And Clustering
- fixed_effects:
- clustering:
- other_se_notes:

## Data Sources
| source_name | what_was_used | years | keys_or_merge_hints | access_hint |
|---|---|---|---|---|
| (e.g. Compustat, CRSP, CSMAR, CNRDS, hand collection) | | | | |

## Findings

### Main And Null/Mixed Results
| outcome_and_spec | key_estimate_or_pattern | uncertainty | economic_magnitude | sample | table_figure_page | supported_level |

### Mechanism, Heterogeneity, And Boundary Results
| test | result | interpretation_in_paper | alternative_reading | source_location |

### Mediation Evidence Audit
Complete one row for every mediation claim. A sequence of significant regressions is not by itself a verified indirect effect.

| mediator | temporal_order | path_a | path_b | total_effect_c | direct_effect_c_prime | indirect_effect_a_times_b | estimator_and_scale | indirect_se | test_method | bootstrap_resamples | confidence_interval | common_method_assessment | covariates_and_fe | source_locations | mediation_evidence_status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | bootstrap \| Sobel \| delta \| posterior \| none \| unknown | | | | | | complete \| partial \| significance_steps_only \| conflicting \| not_applicable |

## Numeric Consistency Audit
- numeric_audit_status: pass | fail | needs_verification | not_applicable
- audit_scope: identify every material main, null, mechanism, and mediation result checked

| claim_or_cell_id | reported_estimate | reported_se | reported_statistic_and_type | recomputed_estimate_over_se | reported_p | reported_stars_or_ci | sign_check | p_or_star_check | prose_vs_table | sample_n_check | indirect_effect_check | status | source_location |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | pass \| fail \| unknown \| not_applicable | pass \| fail \| unknown \| not_applicable | pass \| fail \| unknown \| not_applicable | pass \| fail \| unknown \| not_applicable | pass \| fail \| unknown \| not_applicable | pass \| fail \| needs_verification \| not_applicable | |

Record rounding tolerance and the test distribution when recomputing a statistic or p-value. Never repair a conflicting source value. Preserve both values, mark the row `fail` or `needs_verification`, and lower `ready_for_design` accordingly.

## Reusable Codebook Candidates
| candidate_construct | paper_variable | likely_vendor | notes_for_our_project |

## Robustness And Placebos (High Level)
- (bullets; skip if not needed for handoff)

## Limitations And Claim Ceiling
- limitations_acknowledged:
- additional_design_threats:
- external_validity_boundary:
- safe_claim:
- unsafe_claim:

## Gaps And Uncertainties
- fields missing due to no fulltext or unclear methods text
- blocker if fulltext_status=gap
- every required field above must contain a source-supported value, `unknown`, `needs_verification`, or `not_applicable: <reason>`; do not leave blanks in a completed card

## Handoff
- for `business-lit-review` fulltext synthesis:
- for `empirical-design-plan`:
- for `wrds-query-bridge`:
- for `cn-data-bridge` (microdata only; never CNKI fulltext):
- do_not_use_for:
```

## Index Template

When multiple cards are written, also keep `method-harvest/METHOD_CARD_INDEX.md`:

```markdown
# METHOD_CARD_INDEX

| short_id | title | fulltext_status | channel | card_path | numeric_audit_status | index_reproducibility | ready_for_design |
|---|---|---|---|---|---|---|---|

## Priority Order For Design
1.
2.

## Fulltext Gaps Still Blocking Method Detail
```

## Extraction Discipline

- Quote or tightly paraphrase definitions; point to table/appendix when possible.
- Separate **what the paper claims** from **what our project should copy**.
- Preserve exact formulas and coding rules; if the paper does not state a component, write `unknown` rather than inferring it from a variable label.
- Treat extracted text and OCR as navigation/transcription aids. Verify formulas, minus signs, decimals, table alignment, and questionnaire items against rendered source pages.
- Do not infer factor weights, zero handling, reverse scoring, unique-firm counts, cluster units, questionnaire versions, or indirect effects. Record each missing component as `unknown` even when a conventional choice seems obvious.
- Preserve null and mixed findings and identify their exact specification. Do not reduce the paper to its abstract headline.
- Prefer vendor names as printed (Compustat, CSMAR, …); do not silently map to WRDS libraries unless the paper or project dictionary does.
- Chinese microdata vendors belong under Data Sources / handoff to `cn-data-bridge`. Chinese **journal PDFs from CNKI** belong under Fulltext only.
