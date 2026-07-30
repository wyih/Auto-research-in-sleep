# Business Research Feasibility And Gate Calibration

Use this contract before freezing a go/no-go rule, starting bulk or protected data acquisition, or treating a failed diagnostic as a project STOP.

## Required Artifact

Create `empirical-design/FEASIBILITY_AND_GATE_CALIBRATION.md`. A frozen gate is incomplete without this artifact.

## 1. Calibrate Against Existing Research

Use verified fulltext and method cards for the closest empirical studies. Record, where comparable:

| Study | Claim level | Unit | Observations | Firms | Events / shocks / clusters | Treated and comparison support | Match coverage and attrition | Estimate precision / CI / MDE | Design difference from this project |
|---|---|---|---:|---:|---:|---|---|---|---|

Do not copy a published sample size mechanically. Explain why this project needs similar, greater, or lesser support given its observation unit, treatment variation, clustering, measurement error, and identification strength. Literature used only for novelty does not satisfy this requirement.

## 2. Freeze A Claim Ladder Before A Threshold

Define at least these tiers when they are substantively available:

1. flagship or broad causal design;
2. scoped causal, predictive, or associational design;
3. descriptive, measurement, data, or case-based contribution;
4. no meaningful research claim.

For each tier, list the minimum data and identification requirements. A failed flagship gate normally moves the project down the ladder; it does not terminate the whole project unless every defensible lower tier is also infeasible.

## 3. Classify Every Gate

Every threshold must have an evidence basis and a branch-specific consequence.

| Class | Meaning | Default consequence |
|---|---|---|
| `validity_hard` | A violation makes the evidence wrong, such as look-ahead, wrong unit, duplicate shock, or invalid source identity | repair or kill the affected design |
| `design_hard` | The named estimator or claim lacks required variation or precision | kill or redesign that claim branch |
| `quality_target` | Preferred coverage, precision, or completeness | disclose, narrow, weight, or run sensitivity |
| `aspirational` | Ideal journal-facing standard | never an automatic STOP |

Round numbers, convention, caution, or the word `frozen` are not evidence. Support a `design_hard` threshold with closest-study benchmarks, power/MDE or precision calculations, a validated measurement standard, or a clear identification argument. If none is available, label it `quality_target`.

Statistical insignificance is not a project kill test. Interpret the confidence interval against economically meaningful effects. A wide interval is inconclusive; a narrow interval that rules out meaningful effects may kill the named claim.

## 4. Run A Bounded Feasibility Preflight

Before full production, test a small representative set spanning easy, typical, and difficult cases. Measure the actual end-to-end yield, including source availability, linkage, timing, support, and likely attrition. Do not pilot only convenient positives.

For count gates, maintain this arithmetic from the beginning and after every closure:

| Quantity | Count |
|---|---:|
| verified pass | |
| terminal no-go for this branch | |
| unresolved but recoverable | |
| waiting on an external source | |
| best-case attainable | |
| required threshold | |

If the best-case attainable count is already below the threshold, stop or redesign that branch immediately. If it remains feasible, authorize only the next bounded tranche and state what result would change the decision.

## 5. Apply A QA Relevance Test

Before adding a QA task, record:

- the research decision it can change;
- the failure it can detect;
- the cheapest sufficient check;
- whether the same fact was already independently verified;
- the stopping condition for further QA.

Prioritize research-validity QA: source identity, economic unit, treatment timing, leakage, duplicate shocks, linkage validity, outcome construction, and inference. Artifact-integrity QA such as hashes, manifests, immutable runs, and receipts should normally occur once at handoff and once at finalization, or after a material mutation. QA must not recursively create more QA merely to certify its own packaging.

Skip a proposed check when neither a pass nor a failure would change the claim, design, data decision, or handoff integrity. Do not spend more effort proving a file unchanged than testing whether the research design is viable.

## 6. Use Precise STOP Semantics

- `not_evaluable`: current evidence cannot decide; this is not a failure.
- `branch_stop`: one outcome, mechanism, data route, or estimator ends; the project remains active.
- `design_killed`: the named research design is defeated; evaluate the frozen fallback ladder.
- `scope_down`: continue with a weaker but defensible claim or smaller pre-specified universe.
- `terminal_stop`: every meaningful pre-specified or defensible claim tier is infeasible, or the user stops.

Never convert a source gap, quality target, null p-value, or failed aspirational threshold directly into `terminal_stop`.

## 7. Report In Plain Language

Lead every checkpoint with five short fields:

1. **Goal:** the research question being decided.
2. **What changed:** the new fact or result.
3. **Why it matters:** which claim or branch it affects.
4. **Current decision:** continue, narrow, rework, branch stop, or project stop.
5. **Next action:** the smallest action that could change the decision, with its stopping condition.

Define unavoidable technical terms on first use. Keep hashes, manifests, and receipt details in linked artifacts unless they are themselves the issue under review.

## Completion Test

Do not freeze a go/no-go contract until:

- closest-study sample and precision benchmarks are recorded;
- the claim ladder and fallback designs are explicit;
- each gate has a class, evidence basis, and branch-specific consequence;
- a representative feasibility preflight or an explicit reason it cannot be run is recorded;
- best-case gate arithmetic is current;
- proposed QA is decision-relevant and bounded;
- the project-level STOP rule requires failure of all meaningful claim tiers.
