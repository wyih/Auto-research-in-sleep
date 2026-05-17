# Source Claim Audit

## Gate
GATE2: PASS

## Claim Inventory
| Claim ID | Location | Claim Type | Claim Text | Cited Support |
|---|---|---|---|---|
| C1 | `paper/toy_results.md` | factual | Public Ken French monthly data are used. | `R/04_main_results.R`, Ken French data download URLs |
| C2 | `paper/toy_results.md` | numeric | The final panel contains 1800 industry-month observations. | `analysis/output/RESULTS_SUMMARY.md`, `tables/table_capm_by_industry.csv` |
| C3 | `paper/toy_results.md` | numeric | The highest market beta is Durbl at 1.667. | `tables/table_capm_by_industry.csv` |
| C4 | `paper/toy_results.md` | numeric | HiTec beta is 1.082 and monthly alpha is 0.0028. | `tables/table_capm_by_industry.csv` |
| C5 | `paper/toy_results.md` | claim ceiling | The results describe benchmark market exposure and do not support causal claims. | `CLAIMS_FROM_EVIDENCE.md`, CAPM design |

## Source Support Table
| Claim ID | Source Checked | Verdict | Evidence | Required Fix |
|---|---|---|---|---|
| C1 | `R/04_main_results.R` | VERIFIED | Script downloads public Ken French factor and industry portfolio files. | none |
| C2 | `analysis/output/RESULTS_SUMMARY.md` | VERIFIED | Results summary reports 1,800 observations. | none |
| C3 | `tables/table_capm_by_industry.csv` | VERIFIED | Durbl has the largest market beta. | none |
| C4 | `tables/table_capm_by_industry.csv` | VERIFIED | HiTec beta and alpha match the table. | none |
| C5 | `CLAIMS_FROM_EVIDENCE.md` | VERIFIED | Claim ceiling is descriptive. | none |

## Unverified Or Distorted Claims

None.

## Citation Repairs

None.

## Required Follow-Up

None for the toy project.
