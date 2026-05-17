# Claims From Evidence

## Claim Verdicts

| Intended Claim | Supported Level | Evidence | Confidence | Required Caveat |
|----------------|-----------------|----------|------------|-----------------|
| Industry portfolios differ in market exposure. | descriptive | `tables/table_capm_by_industry.csv`; beta ranges from 0.502 for Utils to 1.667 for Durbl | high | This is a CAPM benchmark, not a causal estimate. |
| HiTec has high market exposure in 2010-2024. | descriptive | HiTec beta is 1.082 in `tables/table_capm_by_industry.csv` | high | "High" is relative to the CAPM beta scale and industry comparison. |
| HiTec has positive abnormal monthly return. | associational benchmark | HiTec alpha is 0.0028 with t-statistic 1.743 | medium | This should be described as CAPM alpha, not as proof of mispricing. |

## Safe Language

- "The industry portfolios differ in estimated market beta."
- "Durbl has the highest estimated beta in this toy sample."
- "HiTec has a positive CAPM alpha in this benchmark regression."

## Language To Avoid

- "Industry causes higher returns."
- "HiTec earns abnormal returns because of technology fundamentals."
- "The model proves mispricing."

## Missing Evidence

- Three-factor and five-factor models
- Newey-West standard errors
- Subperiod stability
- Multiple-testing adjustment

## Recommended Paper Framing

Frame this as a reproducible public-data demonstration of the business research workflow and R backend.
