# R Fama-French Industry Toy Project

This toy project demonstrates the `r-analysis-bridge` lane on public finance data.

## Question

Do Fama-French industry portfolios differ in market beta and abnormal monthly return after controlling for the market factor?

## Public Data

The script downloads public Ken French Data Library files:

- `F-F_Research_Data_Factors_CSV.zip`
- `10_Industry_Portfolios_CSV.zip`

## Run

From this project directory:

```bash
R_SUBMIT="../../skills/r-analysis-bridge/scripts/r_submit.sh"
JOBID=$("$R_SUBMIT" R/04_main_results.R)
"$R_SUBMIT" --wait "$JOBID"
```

Or run directly:

```bash
Rscript R/04_main_results.R
```

## Expected Outputs

- `tables/table_capm_by_industry.csv`
- `tables/table_capm_by_industry.tex`
- `tables/table_summary_stats.csv`
- `figures/capm_beta_by_industry.pdf`
- `figures/hitec_excess_returns.pdf`
- `analysis/ANALYSIS_LOG.md`
- `analysis/output/TABLE_INDEX.md`
- `analysis/output/RESULTS_SUMMARY.md`
- `paper/toy_results.md`

After outputs exist, run:

```bash
python3 ../../skills/business-number-audit/scripts/verify_numbers.py \
  --project . \
  --paper paper/toy_results.md \
  --output BUSINESS_NUMBER_AUDIT.md \
  --allow-unmatched
```
