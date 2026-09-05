# Business Mode Registry

Use this registry for the `business-research-suite` router and for staged pipeline work.

Named outputs describe full-stage artifacts. Standalone requests may use existing project files or a direct answer; produce formal handoffs only for consumers that require them.

| Mode | Use When | Primary Skill | Main Output |
|---|---|---|---|
| `scope` | Broad topic, unclear RQ, early business idea | `business-idea-creator` | candidate RQs |
| `lit-review` | Need field map, closest papers, journal conversation | `business-lit-review` | `BUSINESS_LIT_REVIEW.md` |
| `fulltext` | Need a verified local PDF from OA, CNKI, ScienceDirect, or another authorized channel | `fulltext-acquire` | `FULLTEXT_MANIFEST.md` + PDF/gap |
| `method` | Need sample, variables, measures, identification, or merge keys from verified fulltext | `method-harvest` | `*_METHOD_CARD.md` |
| `novelty` | Need closest-paper delta and risk framing | `business-novelty-check` | `BUSINESS_NOVELTY_CHECK.md` |
| `design` | Need sample, variables, model, tables | `empirical-design-plan` | `RESEARCH_DESIGN.md` |
| `feasibility-gates` | Need literature-calibrated sample benchmarks, a pilot, QA bounds, scope-down choices, or STOP rules | `empirical-design-plan` | `FEASIBILITY_AND_GATE_CALIBRATION.md` |
| `wrds` | Need WRDS data; R/Postgres is the default route | `wrds-query-bridge` | landed extract + `DATA_MANIFEST.md` |
| `wrds-sas` | Recorded R-path escalation or explicit SAS request | `wrds-sas-cloud` | SAS log + transferred extract + handoff |
| `cn-data` | Need CSMAR/CNRDS fields or a minimal authorized portal export | `cn-data-bridge` | `DOWNLOAD_SPEC` + raw extract + manifest |
| `analysis` | Need R/Stata/Python analysis execution | `data-analysis-bridge` | `RESULTS_SUMMARY.md` |
| `r-analysis` | R, Quarto, Rmd, fixest, tidyverse workflow | `r-analysis-bridge` | R outputs |
| `stata-analysis` | Stata, do-files, dta workflow | `stata-analysis-bridge` | Stata outputs |
| `results-docx` | Need standalone academic regression/descriptive tables in Word | `results-to-docx` | verified results `.docx` + manifest |
| `claims` | Need result interpretation and claim ceiling | `evidence-to-claim` | `CLAIMS_FROM_EVIDENCE.md` |
| `number-audit` | Need prose numbers checked against outputs | `business-number-audit` | `BUSINESS_NUMBER_AUDIT.md` |
| `source-claim-audit` | Need prose/citation claims checked against sources | `business-claim-source-audit` | `SOURCE_CLAIM_AUDIT.md` |
| `paper-plan` | Need journal paper architecture | `business-paper-plan` | `BUSINESS_PAPER_PLAN.md` |
| `style-profile` | Need writing sample calibration | `business-author-style-profile` | `AUTHOR_STYLE_PROFILE.md` |
| `write` | Need manuscript section or full paper drafting | `business-paper-writing` | paper text |
| `rebuttal` | Reviews arrived | `business-rebuttal` | response plan or letter |
| `full-pipeline` | User wants staged end-to-end workflow | `business-research-pipeline` | staged artifacts |

## Routing Rules

- When the user has only a broad topic, start with `scope` or `lit-review`.
- When a design claim depends on a paper's method, route `fulltext` then `method`; metadata alone is insufficient.
- Before freezing a numerical gate, starting high-cost acquisition, or declaring STOP, route `feasibility-gates` and apply `business-feasibility-gates.md`.
- When a data plan names WRDS, route `wrds` first and use `wrds-sas` only after its escalation gate. Route CSMAR/CNRDS to `cn-data`.
- Route data requiring computation to `analysis`; route existing results requiring interpretation directly to `claims`.
- Route Word packaging to `results-docx` only after reproducible tidy outputs exist.
- Verify submission-facing numbers and source support. Run separate `number-audit` and `source-claim-audit` workflows when requested, required by the project's submission workflow, or needed to resolve a substantive verification gap.
- When the user asks for "which skill should I use", start with this registry and choose one mode.
