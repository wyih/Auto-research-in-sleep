# Business Mode Registry

Use this registry for the `business-research-suite` router and for staged pipeline work.

| Mode | Use When | Primary Skill | Main Output |
|---|---|---|---|
| `scope` | Broad topic, unclear RQ, early business idea | `business-idea-creator` | candidate RQs |
| `lit-review` | Need field map, closest papers, journal conversation | `business-lit-review` | `BUSINESS_LIT_REVIEW.md` |
| `novelty` | Need closest-paper delta and risk framing | `business-novelty-check` | `BUSINESS_NOVELTY_CHECK.md` |
| `design` | Need sample, variables, model, tables | `empirical-design-plan` | `RESEARCH_DESIGN.md` |
| `analysis` | Need R/Stata/Python analysis execution | `data-analysis-bridge` | `RESULTS_SUMMARY.md` |
| `r-analysis` | R, Quarto, Rmd, fixest, tidyverse workflow | `r-analysis-bridge` | R outputs |
| `stata-analysis` | Stata, do-files, dta workflow | `stata-analysis-bridge` | Stata outputs |
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
- When the user has data or results, route to `analysis`, then `claims`.
- Before submission-ready writing, run `number-audit` and `source-claim-audit`.
- When the user asks for "which skill should I use", start with this registry and choose one mode.
