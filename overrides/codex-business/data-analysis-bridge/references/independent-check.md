# Independent Implementation Of A Key Analysis

Use when the user requests independent reproduction or a concrete uncertainty warrants rebuilding a selected table, variable, or sample-construction step. Select the smallest analysis that answers that question; this is not a requirement to duplicate every table or rebuild a whole project.

## Prepare The Specification

The coordinator prepares a separate verification directory and a result-free input packet from the research design, relevant methods text, data dictionary, and authorized source data. State:

- the exact target and starting data, observation unit, keys, date conventions, and sample rules
- variable formulas, units, missing-value rules, treatment/event time, and merge timing/cardinality
- equation or transformation, controls, fixed effects, weights, clustering and standard-error conventions, as applicable
- required diagnostic and result outputs, including identifiers needed to compare estimation samples

Use the documented research specification as the basis. Do not reconstruct missing design choices by reading the original code and presenting its choices as requirements. Record consequential ambiguities and resolve them from authorized design evidence or the user; proceed with independent parts while a necessary decision is pending.

Give the implementer access only to this packet, the named input data, and its own output directory. Raw inputs are needed to verify construction from raw data. If only an analysis-ready dataset is available, explicitly scope the exercise to estimation conditional on that dataset; do not claim the upstream construction was independently reproduced. Keep restricted data in its authorized environment.

## Implement In A Fresh Context

Use a fresh worker/session that does not inherit the original conversation, analysis code, result-bearing manuscript sections, tables, logs, previous reviews, or expected coefficient values. Use the runtime's no-history option when available. Pass neutral paths and the specification, not the executor's account of the answer. Keep the original results with the coordinator until the independent implementation and its outputs are saved.

Prefer another available language for the same specification, such as R versus Stata. Read the corresponding analysis bridge for execution mechanics only; its ordinary original-project inventory does not apply. A fresh implementation in the same language can still provide a useful check when another backend is unavailable, but report that scope accurately. If a fresh context cannot be obtained, prepare the packet and report the execution gap; do not label a rewrite by the original agent as independent verification or claim agreement without a run.

The implementer writes separate scripts, logs, sample diagnostics, and machine-readable results in the verification directory and runs them on the named inputs. Preserve the production scripts, raw data, and original outputs. Do not copy original functions, reuse the original derived variables when their construction is the target, or tune the implementation toward the expected result.

## Compare After Both Implementations Exist

The coordinator compares the saved independent outputs with the original outputs in this order:

1. Input population and time coverage; intermediate counts; entity/cluster counts and actual sample IDs, not N alone.
2. Constructed variables, missingness, treatment/event-time assignment, units, and transformations.
3. Estimator and model sample; weights; fixed effects; clustering, degrees of freedom, singleton rules, and finite-sample corrections.
4. Unrounded coefficients, standard errors/intervals, and the numerical quantities underlying the paper's claims.

Adapt this sequence to the selected target: a variable-construction check need not estimate regressions. Align intended definitions before interpreting differences, and make any material specification clarification available to both implementations. Establish numerical tolerances from solver precision, output precision, and documented estimator conventions rather than widening them until results match. Do not require identical random draws across languages for stochastic methods; compare the estimand and appropriate simulation uncertainty.

Investigate the earliest divergence. A discrepancy does not establish which implementation is wrong. Use design evidence, a minimal diagnostic, or a hand-checkable example to resolve it, preserving the original independent outputs before any correction. Fix verified issues within the authorized task and rerun only the affected comparison. Agreement supports the checked implementation, not identification assumptions or errors shared by the specification.

## Deliver And Finish

Report the target and input scope, context/language independence actually achieved, paths to the separate implementation and logs, aligned quantities that agree, and discrepancies with their resolution or remaining evidence gap. Use existing analysis notes or a concise comparison report. Finish when the selected target is compared and material differences are resolved or precisely documented; do not create a new audit cycle merely to package the result.

Based on the independent-reimplementation exercise in Claes Bäckman's *Practical AI for Academics*, Day 1, PDF page 79 (slide 67/72), which credits Scott Cunningham; [course materials](https://claesbackman.com/aarhus).
