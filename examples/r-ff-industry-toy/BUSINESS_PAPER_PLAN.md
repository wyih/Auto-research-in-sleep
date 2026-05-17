# Business Paper Plan

## Title Options

- A Toy R Workflow For Public Fama-French Industry Portfolio Analysis
- Market Exposure Across Industry Portfolios: A Reproducible R Toy Example

## One-Sentence Contribution

This toy project demonstrates an end-to-end business research workflow using public finance data, R scripts, regression tables, figures, claim calibration, and number audit.

## Claim-Evidence Matrix

| Claim | Claim Level | Evidence | Table/Figure | Section | Caveat |
|-------|-------------|----------|--------------|---------|--------|
| Industries differ in market beta. | descriptive | CAPM by industry | Table 2, Figure 1 | Results | Benchmark exposure only |
| HiTec beta is 1.082. | descriptive | HiTec CAPM row | Table 2 | Results | 2010-2024 sample |
| HiTec alpha is 0.0028. | associational benchmark | HiTec CAPM row | Table 2 | Results | Not causal or anomaly evidence |

## Section Plan

1. Motivation: use a small public finance dataset to test the workflow.
2. Data: Ken French factors and industry portfolios.
3. Research Design: industry-by-industry CAPM regressions.
4. Results: beta ranking, HiTec row, and market exposure figure.
5. Limitations: no causal identification, no robust inference, no novelty claim.

## Table And Figure Plan

- Table 1: Summary statistics
- Table 2: CAPM by industry
- Figure 1: CAPM beta by industry
- Figure 2: HiTec excess returns

## Referee-Risk Map

| Risk | Planned Answer |
|------|----------------|
| This is not novel. | Frame as a toy workflow test. |
| CAPM alpha is overinterpreted. | Keep claim at descriptive/benchmark level. |
| Standard errors are simple OLS. | Mark Newey-West inference as future robustness. |

## Missing Evidence Markers

- Add Fama-French three-factor model.
- Add robust inference.
- Add subperiod analysis.
