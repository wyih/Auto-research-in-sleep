---
name: method-harvest
description: Deep-read external research papers or extract source-grounded methods, measures, sample definitions, identification, and findings from fulltext. Use study mode to learn from an external paper, a focused note for targeted Q&A, and the full method-card contract when a research pipeline consumes it.
---

# Method Harvest

Read the supplied paper to answer the user's method or design question. Preserve exact definitions, source locations, null/mixed findings, and the strength of the evidence.

## Choose the output scope

- **External-paper study (`study` mode — default when asked to read, learn from, or dissect an external paper without a narrow field question or pipeline consumer):** answer in chat (or write a note only when requested) using a three-part structure without role-play personas, mandatory pre-reading confirmation pauses, generic implication filler, or ungrounded cross-disciplinary speculation:
  1. **Paper reconstruction (`精读还原`)**: bibliographic/version identity and `source_depth`, research question, institutional context, concrete increment over nearest studies, theoretical mechanism and predictions, sample/cohort filters, exact variable/index formulas, identification strategy, fixed effects/clustering, and main + mechanism + null/mixed results (separating statistical significance from economic magnitude, citing `PDF p.<viewer-page>`, and running the numeric consistency check below). Adapt emphasis by field (accounting/finance: institutional background, endogeneity, comparison group, economic magnitude, database mapping; management/strategy: theoretical tension, construct depth, measurement validity), leaning toward technical replication or theoretical logic when the user requests one.
  2. **Identification & claim-ceiling assessment (`识别得失评估`)**: reuse [field referee checks](../business-prereview/references/field-referee-checks.md), [empirical diagnostics](../shared-references/business-empirical-diagnostics.md), and the claim-ceiling levels in [evidence-to-claim](../evidence-to-claim/SKILL.md) (`descriptive`, `associational`, `plausibly_causal`, `mechanism_consistent`, `not_supported`) to evaluate (a) clever design moves worth learning, (b) substantive identification, comparison-group, measurement, attrition, or inference weaknesses (comparing claimed vs. established contribution), and (c) the highest claim level supported by the evidence. Do not generate an author-side P0/P1/P2 manuscript revision plan.
  3. **Reusable variable/data dictionary & follow-up entry points (`可复用的变量/数据字典与后续研究切入点`)**: extract portable construct-to-variable recipes, data sources, and merge keys (adding concise R/Stata/Python replication skeletons when requested), plus 2–3 concrete, testable follow-up research entry points motivated by the paper's identification gaps or boundary conditions.
- **Standalone focused note (`focused_note` mode):** answer a narrow method, measure, sample, or finding question in chat or write a focused note when requested. Include paper/version identity, source depth, the requested fields, source locations, and material gaps. Do not generate manifests, hashes, inspection receipts, or unused schema blocks by default.
- **Pipeline method card (`method_card` mode):** use when the user requests the full contract or an actual consumer requires it, including `business-lit-review` in `fulltext_synthesis` mode or a project handoff governed by the business schemas. Read [PDF processing](references/pdf-processing.md), [the card template](references/method-card-template.md), and the applicable [handoff schema](../shared-references/business-handoff-schemas.md). Preserve the required artifact identities, hashes, receipts, and complete fields.

A study note or focused note is not a validated pipeline card. If it later enters a pipeline, acquire the missing evidence and satisfy that consumer's contract at handoff.

## Read the source

1. Confirm the title, authors, DOI/source record, and version from the document's opening pages. Do not identify a paper from a title found only in its bibliography. Keep separately used appendices/questionnaires identifiable.
2. If fulltext is missing, use `fulltext-acquire` with the current scope (standalone `study` or `focused_note`, or pipeline `method_card`), then resume the requested mode with the verified PDF or documented gap. If only an abstract is available, state `source_depth=abstract_only` and leave unsupported method details unknown.
3. Use a local PDF reader or page-preserving extraction such as `pdftotext -layout`. Visually inspect formulas, table alignment, key numbers, and any OCR-sensitive passage used in the answer. Use authorized local OCR when necessary; retain the original and its page mapping.
4. Cite `PDF p.<viewer-page>` using 1-based viewer pages, adding printed page numbers only when useful. Preserve the source file; do not upload licensed papers to an unrelated processing service.

## Extract what the question requires

| Field | Evidence to preserve |
|---|---|
| Question and theory | Research question, mechanism, predictions, construct definitions and depth |
| Sample | Observation, respondent, estimand, unique-entity and cluster units; response N versus entity N; period, filters and dependence |
| Identification | Variation, comparison, treatment/timing, assumptions and threats |
| Variables | Exact formula/coding, transforms, lags/windows, aggregation, units, sign and missing/zero handling |
| Index or questionnaire | Inputs/items, administered version, translation, reverse scoring, weights/loadings, standardization and scoring; extraction/rotation/retention when applicable |
| Inference and data | Fixed effects, clustering, other uncertainty estimates, sources, grain and keys |
| Findings | Main, null/mixed and relevant mechanism results, tied to the exact outcome, model, sample and uncertainty |
| Mediation | Temporal order, paths a/b/c/c-prime, indirect effect, compatible scales, test/CI and common-method evidence |
| Boundaries and reuse | Supported claim, material limitations, and implications for the current question |

Select relevant fields for a focused request; complete the full template for a pipeline handoff. Never infer an unstated formula, weight, sample count, cluster unit, questionnaire version, or mediation path from convention. Use `unknown` for unstated details and `needs_verification` for conflicting evidence.

## Verify material claims

Compare extracted statements with the actual methods, table notes, and relevant appendix. Check arithmetic when a quantitative claim depends on it: estimate/SE versus the stated statistic on a compatible scale, sign and uncertainty, prose/table agreement, sample counts, and a-times-b for applicable indirect effects. Account for rounding and the test distribution. Preserve conflicting source values instead of repairing them.

A sequence of significant regressions does not establish a tested indirect effect. Distinguish statistical from economic magnitude and the paper's choices from recommendations for the user's project.

## Pipeline completion

Follow the linked processing and card contracts; reuse current accepted evidence for unchanged files. Write `method-harvest/cards/<short_id>_METHOD_CARD.md` and an index when producing multiple cards. Keep stable `work_id` separate from each version/role's `artifact_id`; companions point to the main artifact. Do not claim receipt acceptance until its required checks pass.

Route cross-paper synthesis to `business-lit-review`, design implications to `empirical-design-plan`, WRDS details to `wrds-query-bridge`, and Chinese microdata gaps to `cn-data-bridge` only when the requested next stage needs that handoff.
