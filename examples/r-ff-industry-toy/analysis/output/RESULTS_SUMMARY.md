# Results Summary

## Data Build
The analysis uses monthly Ken French factors and 10 industry portfolio returns from 201001 to 202412.
The final panel contains 1800 industry-month observations across 10 industries.

## Tables And Figures
| Output | R Script | Log | Sample | Specification | Key Numbers | Claim Supported |
|--------|----------|-----|--------|---------------|-------------|-----------------|
| `tables/table_capm_by_industry.csv` | `R/04_main_results.R` | `logs/04_main_results.log` | 201001-202412 | `excess_return ~ mkt_rf` by industry | highest beta Durbl = 1.667; HiTec beta = 1.082; HiTec alpha = 0.0028 | Industry portfolios differ in market exposure. |
| `figures/capm_beta_by_industry.pdf` | `R/04_main_results.R` | `logs/04_main_results.log` | 201001-202412 | CAPM beta estimates | lowest beta Utils = 0.502 | Market exposure varies across industries. |

## Main Findings
The highest estimated CAPM beta is Durbl at 1.667.
HiTec has an estimated beta of 1.082 and an alpha of 0.0028.

## Robustness And Placebos
This toy run does not implement robustness checks. The robustness plan recommends adding Fama-French three-factor models and Newey-West standard errors.

## Null Or Mixed Results
Alpha estimates in this toy CAPM exercise should be treated descriptively and should not be framed as causal evidence.

## Issues For Audit Ledger
No blocking replication issues. Conceptual issue: CAPM alpha is descriptive benchmark evidence.

## Next Analyses
Add SMB and HML factors, Newey-West inference, and pre/post-2020 subsample checks.
