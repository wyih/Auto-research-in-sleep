# Python empirical panels

Use this reference only when Python is the selected estimation backend. R with `fixest` remains the default for a new analysis and the preferred route for an existing R project. Python parsing or text scoring can export inputs to R without changing the estimator. Retain Stata for projects whose replication workflow uses it.

## Select an implementation

- `linearmodels.PanelOLS`: established panel workflows with entity/time effects and explicit panel indexing.
- `pyfixest`: high-dimensional fixed effects, IV, PPML, and supported modern DiD implementations. Read [the current reference](https://pyfixest.org/reference/) and inspect the installed version before using its DiD interfaces.
- `statsmodels`: supported model classes and diagnostics when those match the design.

Reuse installed libraries and project dependencies. Add a package only when the requested model needs it. Match the formula, covariance estimator, sample, and small-sample adjustments to the design; record absorbed/singleton/missing-value drops.

Minimal OLS/FE pattern, with a firm-cluster choice that must match the actual design:

```python
import pyfixest as pf

fit = pf.feols(
    "outcome ~ exposure + size | firm_id + year",
    data=panel,
    vcov={"CRV1": "firm_id"},
)
```

For a state-assigned policy, choose covariance and cluster variables from that assignment/dependence structure. Specify them explicitly; library defaults can differ across versions.

## Verify and hand off

Validate observation-key uniqueness and date-valid joins before estimation. Capture the actual regression sample, cluster count, fixed effects, omitted terms, estimate, standard error, confidence interval, and model ID. Retain a machine-readable table using the existing `results-to-docx` coefficient contract when that output is requested.

Compare implementations only after aligning missingness, singleton handling, weights, absorbed effects, covariance corrections, and degrees of freedom. Reuse [design diagnostics](../../shared-references/business-empirical-diagnostics.md) for the selected method and [empirical figures](empirical-figures.md) when plotting results.

Adaptation credits: [Barrios sources](../../shared-references/business-source-attribution.md).
