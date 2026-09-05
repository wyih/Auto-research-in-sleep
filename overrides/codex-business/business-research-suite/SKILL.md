---
name: business-research-suite
description: Choose and run the next stage of business, accounting, finance, management, or economics research. Use for workflow routing or an explicitly requested end-to-end research pipeline.
---

# Business Research Suite

Identify the user's material state and requested outcome, then load the focused skill for the next necessary stage. Routing alone does not require project files or a full pipeline.

## Routes

- Topic or research question: `business-idea-creator`
- Literature discovery or cross-paper synthesis: `business-lit-review`
- Missing paper or publisher access: `fulltext-acquire`
- Method, measure, sample, or identification extraction: `method-harvest`
- Novelty and closest-paper comparison: `business-novelty-check`
- Research design or feasibility: `empirical-design-plan`
- WRDS: `wrds-query-bridge` using R/Postgres by default; `wrds-sas-cloud` only after a documented escalation or explicit SAS request
- CSMAR/CNRDS variable resolution or export: `cn-data-bridge`
- Licensed/public data through Kimi Code: the `kimi-datasource` plugin when available
- Analysis: `data-analysis-bridge`, `r-analysis-bridge`, or `stata-analysis-bridge`
- Standalone results Word document: `results-to-docx`
- Interpretation: `evidence-to-claim`
- Paper structure, voice, or writing: `business-paper-plan`, `business-author-style-profile`, or `business-paper-writing`
- Pre-review or response to reviewers: `business-prereview` or `business-rebuttal`
- Requested number/source audits: `business-number-audit` or `business-claim-source-audit`
- Project continuity: `business-run-passport`
- Explicit end-to-end work: `business-research-pipeline`

Check the focused skill is available before routing. Read [the mode registry](../shared-references/business-mode-registry.md) only when selection remains unclear.

## Project records and handoffs

Use the existing project workflow. Maintain `BUSINESS_RUN_PASSPORT.md` when that project already uses it, the user requests it, or an actual downstream stage needs it; directory access alone is not a reason to create it.

Read [handoff schemas](../shared-references/business-handoff-schemas.md) when producing artifacts for a consumer that requires them. Mark material missing fields rather than treating a light standalone result as pipeline-ready.

Check submission-facing numbers and source support. Produce separate `BUSINESS_NUMBER_AUDIT.md` and `SOURCE_CLAIM_AUDIT.md` files only when requested or required by the project's submission workflow.

## Research decisions

- Do not infer detailed methods from metadata or abstracts. Acquire the necessary fulltext, then extract supported details.
- Keep `browser-session-bridge` as transport for the protected-site producer, not the top-level research task.
- Before analysis, land the required data or identify the concrete access gap.
- Before expensive acquisition or adopting a hard go/no-go threshold, use a representative feasibility pilot and closest-study evidence, power/precision, measurement standards, or identification logic. Read [feasibility guidance](../shared-references/business-feasibility-gates.md) when that decision needs calibration; record it in the project's existing design artifact unless a specific file is required.
- A failed research branch does not by itself invalidate the project. Consider supported scope reductions; distinguish missing evidence from a failed test.
- Add QA only when it can change a research decision or protect a material handoff. Stop once the requested stage and its necessary evidence are complete.

For routing-only requests, state the selected skill, any blocking input, and expected result concisely. For an execution request, continue with the selected stage.
