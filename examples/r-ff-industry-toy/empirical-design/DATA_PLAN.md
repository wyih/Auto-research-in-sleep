# Data Plan

## Sources

- Ken French Data Library Fama-French research factors
- Ken French Data Library 10 industry portfolios

## Construction

1. Download zip files into `data/raw/`.
2. Parse monthly return sections.
3. Convert percentage returns to decimal returns.
4. Merge factors and industry returns by `yyyymm`.
5. Keep January 2010 through December 2024.
6. Reshape industry returns into a long industry-month panel.
7. Compute excess return as industry return minus risk-free rate.

## Files

- `data/final/industry_month_panel.csv`
- `data/final/factors_monthly.csv`
