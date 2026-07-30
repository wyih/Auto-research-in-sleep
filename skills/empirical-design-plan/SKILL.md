---
name: empirical-design-plan
description: Plan and feasibility-test empirical research designs for accounting, finance, management, economics, and business papers. Use for identification, sample construction, variables, models, table shells, robustness, event studies, DiD, IV, RD, gate calibration, sample benchmarks, power or precision, claim ladders, scope-down choices, and defensible STOP decisions.
---

# Empirical Design Plan

Research idea: $ARGUMENTS

## Purpose

Turn a business research idea into a referee-readable empirical design and table plan.

## Inputs

Read available files in this order:

1. `idea-stage/BUSINESS_IDEA_REPORT.md`
2. `BUSINESS_LIT_REVIEW.md`
3. `BUSINESS_NOVELTY_CHECK.md`
4. `RESEARCH_BRIEF.md`
5. `BUSINESS_RUN_PASSPORT.md` when present
6. `method-harvest/cards/*_METHOD_CARD.md` and `LITERATURE_EVIDENCE_MATRIX.md` when sample or design benchmarks affect feasibility
7. user-provided data dictionaries or sample notes

Read `../shared-references/business-handoff-schemas.md` when writing design artifacts.
Read `../shared-references/business-feasibility-gates.md` before proposing a numerical gate, kill test, high-cost acquisition, or STOP rule.

## Workflow

### Phase 1: Freeze Claims

Write only claims the design could plausibly support.

Claim levels:

- descriptive pattern
- association
- plausibly causal effect
- mechanism evidence
- boundary condition
- theory contribution

### Phase 2: Specify the Research Design

Define:

- unit of observation
- sample period and filters
- treatment or key independent variable
- outcome variables
- control variables
- fixed effects
- clustering level
- identification source
- required assumptions
- main threats

Common designs:

- panel OLS with high-dimensional fixed effects
- difference-in-differences
- event study
- instrumental variables
- regression discontinuity
- matched sample
- staggered adoption design
- textual or disclosure measure validation
- survey or experiment with business outcomes

### Phase 3: Benchmark And Calibrate Feasibility

Create a comparable closest-study table covering observations, firms, events/shocks/clusters, treated/comparison support, match coverage, attrition, precision/CI/MDE, and claim level. Explain differences in observation unit, measurement error, clustering, and identification rather than copying sample sizes.

Freeze a claim ladder: flagship, scoped, descriptive/measurement, and no meaningful claim. For every proposed gate, record its class, evidence basis, and branch-specific consequence. Statistical significance alone is not a valid project continuation rule; interpret confidence intervals against economically meaningful effects.

Run a small representative end-to-end feasibility preflight when possible. Maintain the best-case attainable count from the start. If the named design cannot reach its threshold, redesign or stop that branch before full production.

### Phase 4: Build Table Shells

Design a compact table sequence:

1. sample construction and descriptive statistics
2. correlation or validation table when needed
3. main result
4. identification or event-study diagnostics
5. robustness
6. mechanism
7. heterogeneity or cross-sectional tests

For each table, specify columns, sample, equation, variables, and expected claim.

### Phase 5: Plan Robustness and Placebos

Include:

- alternative variable definitions
- alternative fixed effects
- alternative clustering
- pre-trend or falsification tests
- placebo outcomes or placebo dates
- sample restrictions
- influential observation checks
- timing windows
- mechanism alternatives

### Phase 6: Write Outputs

When writing is allowed, create:

- `empirical-design/RESEARCH_DESIGN.md`
- `empirical-design/DATA_PLAN.md`
- `empirical-design/TABLE_SHELLS.md`
- `empirical-design/ROBUSTNESS_PLAN.md`
- `empirical-design/FEASIBILITY_AND_GATE_CALIBRATION.md`
- update `BUSINESS_RUN_PASSPORT.md` through `business-run-passport` when the design is accepted

## Output Summary

End with:

- strongest feasible claim
- closest-study benchmark and expected precision
- weakest link in the design
- best-case attainable gate result and fallback claim tier
- first three analyses to implement
- data or manual decisions needed before coding

## Rules

- For local tasks, complete only the requested stage and mark downstream gaps as next-stage inputs.
- Design tables around claims, not around available variables.
- State what the design can and cannot identify.
- Treat clustering and fixed effects as design decisions.
- Prefer a small number of decisive robustness checks over a long appendix list.
- Flag any result that would require causal language beyond the design.
- Keep data access levels visible when raw data cannot be shared with downstream writing or audit stages.
- Do not freeze a numerical gate without a closest-study, power/MDE or precision, measurement-standard, or identification basis. Otherwise label it a quality target.
- Distinguish research-validity QA from packaging QA. Add a check only when its outcome can change the claim, design, data decision, or handoff integrity.
- A failed flagship design triggers the frozen fallback ladder. Use project `terminal_stop` only after all meaningful claim tiers fail.
- Write gate summaries in plain language before technical details.
