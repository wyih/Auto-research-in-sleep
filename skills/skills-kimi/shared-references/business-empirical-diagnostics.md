# Design-specific empirical diagnostics

Read the section for the design being planned, implemented, interpreted, or described. Use the project's selected estimand and supported method; add a diagnostic when its result can change that interpretation.

## Panel construction and inference

Establish the observation unit and key uniqueness before merges. Use date-valid identifier links, inspect unmatched/ambiguous records and join expansion, and record attrition at consequential filters. Specify missing codes, denominators, winsorization/trimming, and lag availability from the design rather than generic defaults.

Before estimation state the identifying variation, fixed effects, treatment/assignment level, and dependence motivating clustering. Record the estimation sample and actual cluster count. For few independent clusters, use a justified small-sample correction, bootstrap, or randomization approach supported by the design and installed implementation.

## Difference-in-differences and dynamic treatment effects

Specify treatment cohorts, first-treatment coding, anticipation window, control group, and whether treatment is absorbing. Define ATT(g,t), event-time aggregation, or the other target estimand before selecting an estimator.

For staggered adoption with heterogeneous effects, use an estimator designed for the intended comparisons, such as Callaway–Sant'Anna or Sun–Abraham. Document never-treated versus not-yet-treated controls and cohort support at each event time. Use a TWFE comparison/decomposition when it answers a substantive question about weighting or an existing result. Treatment reversals and continuous intensity require a method that accommodates those features.

Plot the chosen estimator's event-time effects with the reference period, support, and pointwise or simultaneous interval convention. Interpret pre-period estimates with their precision and the underlying economic parallel-trends argument. Sensitivity analysis for plausible trend deviations is useful when those deviations could change the conclusion.

Keep policy announcement, effective date, actual exposure, and anticipation distinguishable. Controls must reflect their role in the identification argument; conditioning on a treatment-induced variable can alter the estimand.

## Instrumental variables

State instrument, endogenous variable, first-stage variation, exclusion argument, and population to which the IV estimand applies. When interpreting a LATE, specify the monotonicity and complier interpretation relevant to the setting.

Report first stage, reduced form, and IV estimates on comparable samples when those comparisons matter. Use heteroskedasticity/cluster-appropriate relevance and weak-instrument diagnostics, with critical values justified for the model. Apply weak-instrument-robust inference, such as supported Anderson–Rubin confidence sets, when strength is uncertain. Overidentification diagnostics test their maintained restrictions and complement the economic exclusion argument.

## Regression discontinuity

State running variable, cutoff, sharp/fuzzy assignment, and the local estimand. Inspect observations and treatment/outcome behavior around the cutoff, possible sorting, other threshold changes, and discrete support/mass points where relevant.

Use an appropriate local-polynomial estimator and robust bias-corrected inference when selected by the design. Record effective observations on each side, bandwidth, kernel, polynomial order, and interval convention. Test meaningful bandwidth choices and sorting/covariate concerns. For fuzzy RD, retain the treatment first stage and the local complier interpretation.

## Finance event studies

A market-return event study requires an event timestamp mapped to trading days, a specified estimation window separate from the event window, expected-return benchmark, and treatment of overlapping events and missing returns. Define CAR/BHAR and the horizon. Use inference appropriate to cross-sectional/event dependence and the design's causal claim.

Dynamic policy DiD and abnormal-return studies use different counterfactuals. Select the correct branch from the research question and data.

## Magnitudes, nulls, and multiple outcomes

Translate coefficients using the model's actual scale: percentage points for a proportion outcome, `100 * (exp(beta * delta_x) - 1)` for a modeled log-outcome change where that interpretation is appropriate, and stated baseline/SD/IQR inputs for rescaling. Label approximations and retain the relevant sample and horizon. Fixed effects and nonlinear link functions may require a model-based contrast rather than direct coefficient rescaling.

Read confidence intervals against economically meaningful effects. A wide interval and a narrow interval excluding material effects support different conclusions. For related outcome/subgroup families, define the family and choose an error-control procedure consistent with confirmatory/exploratory use. Heterogeneity claims should use the relevant interaction or difference test.

## Implementations and primary references

Check installed versions and current interfaces before generating package-specific calls.

- R: [did ATT(g,t)](https://bcallaway11.github.io/did/reference/att_gt.html), [fixest](https://lrberge.github.io/fixest/), [HonestDiD](https://github.com/asheshrambachan/HonestDiD).
- Stata: the design-appropriate `csdid`/`eventstudyinteract`, IV/weak-instrument commands, and `rdrobust`/`rddensity`; inspect local help for options and return values.
- Python: [PyFixest estimation reference](https://pyfixest.org/reference/), [linearmodels](https://bashtage.github.io/linearmodels/).
- RD: [RD Packages](https://rdpackages.github.io/) documentation for R, Stata, and Python implementations.

Adaptation credits: [Barrios sources](business-source-attribution.md).
