---
name: method-harvest
description: Extract source-grounded methods, measures, sample definitions, identification, and findings from research-paper fulltext. Use a focused note for standalone analysis and the full method-card contract when a research pipeline consumes it.
---

# Method Harvest

Read the supplied paper to answer the user's method or design question. Preserve exact definitions, source locations, null/mixed findings, and the strength of the evidence.

## Choose the output scope

- **Standalone analysis:** answer in chat or write a focused note when requested. Include paper/version identity, source depth, the requested fields, source locations, and material gaps. Do not generate manifests, hashes, inspection receipts, or unused schema blocks by default.
- **Pipeline method card:** use when the user requests the full contract or an actual consumer requires it, including `business-lit-review` in `fulltext_synthesis` mode or a project handoff governed by the business schemas. Read [PDF processing](references/pdf-processing.md), [the card template](references/method-card-template.md), and the applicable [handoff schema](../shared-references/business-handoff-schemas.md). Preserve the required artifact identities, hashes, receipts, and complete fields.

A standalone note is not a validated pipeline card. If it later enters a pipeline, acquire the missing evidence and satisfy that consumer's contract at handoff.

## Read the source

1. Confirm the title, authors, DOI/source record, and version from the document's opening pages. Do not identify a paper from a title found only in its bibliography. Keep separately used appendices/questionnaires identifiable.
2. If fulltext is missing, use `fulltext-acquire`. If only an abstract is available, state `source_depth=abstract_only` and leave unsupported method details unknown.
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
