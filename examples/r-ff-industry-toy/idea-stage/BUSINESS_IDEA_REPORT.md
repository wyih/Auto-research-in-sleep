# Business Idea Report

## Candidate Ideas

| Rank | Question | Data | Feasibility | Claim Ceiling |
|------|----------|------|-------------|---------------|
| 1 | Do Fama-French industry portfolios differ in market beta after controlling for the market factor? | Ken French 10 industry portfolios and factors | High | Descriptive / benchmark |
| 2 | Did industry betas shift after 2020? | Same data with subsample split | Medium | Descriptive, needs robustness |
| 3 | Do HiTec returns show positive CAPM alpha in 2010-2024? | Same data | Medium | Associational benchmark, no causal claim |

## Selected Idea

Estimate industry-specific CAPM regressions from 2010 through 2024 using public monthly Fama-French data.

## Why This Idea

- Data are public and small enough for a toy workflow.
- The regression is easy to audit.
- The output naturally tests R scripts, tables, figures, result summaries, and number audit.
- The claim ceiling is clear: descriptive market exposure, not causal inference.

## Data Path

- `data/raw/`: downloaded Ken French zip files
- `data/final/industry_month_panel.csv`: final industry-month panel
- `tables/`: regression and summary outputs
- `figures/`: beta bar chart and HiTec time-series figure

## First Analyses

1. Download and parse public Ken French data.
2. Estimate `excess_return ~ mkt_rf` separately by industry.
3. Compare estimated CAPM betas and alphas.
