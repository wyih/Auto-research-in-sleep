# Number Audit Checklist

## Automated Check

Run `scripts/verify_numbers.py` against the main manuscript and review every unmatched prose number. False positives are acceptable; unexplained coefficients, p-values, sample sizes, and economic magnitudes are audit issues.

## Manual Trace

For each numeric claim:

- locate the exact source table, figure, log, or result summary
- compare rounded values
- compare dependent variable, treatment, controls, fixed effects, clustering, and sample
- confirm the reported economic magnitude uses the right scale
- confirm signs and units are described correctly

## Specification Consistency

Flag mismatches between manuscript and code:

- sample period
- observation unit
- treatment timing
- fixed effects
- clustering level
- control set
- event window
- winsorization or outlier handling
- merge restrictions or attrition

## Claim Discipline

Numerical agreement does not clear conceptual issues. Keep an issue open when:

- the result is based on a shared denominator
- an outcome is a complement or residual component
- the analysis has no usable counterfactual for a causal claim
- pre-trends, balance, or first-stage diagnostics fail
- the sample support is too thin for the stated claim

## Gate Labels

- `GATE1: PASS`: text, numbers, and implemented specifications match.
- `GATE1: REOPEN_TEXT`: outputs are usable, but the manuscript needs correction.
- `GATE1: REOPEN_ANALYSIS`: code or generated empirical outputs must change.
