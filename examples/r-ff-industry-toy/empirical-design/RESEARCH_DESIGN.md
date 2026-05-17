# Research Design

## Research Question

Do Fama-French industry portfolios differ in market beta and abnormal monthly return after controlling for the market factor?

## Design

- Unit of observation: industry portfolio by month
- Sample: monthly returns from January 2010 through December 2024
- Outcome: industry portfolio excess return, computed as industry return minus risk-free rate
- Treatment or key variable: market excess return (`Mkt-RF`)
- Main specification: industry-specific CAPM regressions

```text
R_it - RF_t = alpha_i + beta_i * (MktRF_t) + epsilon_it
```

## Identification And Interpretation

This is a descriptive asset-pricing exercise. It estimates industry market exposure and abnormal returns within a simple CAPM benchmark. It does not support causal claims.

## Inference

The toy project reports conventional OLS standard errors. For a submission-grade project, add heteroskedasticity and autocorrelation robust inference.
