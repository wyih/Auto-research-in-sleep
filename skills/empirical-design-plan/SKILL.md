---
name: empirical-design-plan
description: Plan empirical research designs for accounting, finance, management, economics, and business papers. Use when the user needs identification strategy, sample construction, variable definitions, regression specifications, fixed effects, clustering, robustness tests, placebo tests, event studies, DiD, IV, RD, table shells, or a business replacement for ML experiment planning.
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
5. user-provided data dictionaries or sample notes

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

### Phase 3: Build Table Shells

Design a compact table sequence:

1. sample construction and descriptive statistics
2. correlation or validation table when needed
3. main result
4. identification or event-study diagnostics
5. robustness
6. mechanism
7. heterogeneity or cross-sectional tests

For each table, specify columns, sample, equation, variables, and expected claim.

### Phase 4: Plan Robustness and Placebos

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

### Phase 5: Write Outputs

When writing is allowed, create:

- `empirical-design/RESEARCH_DESIGN.md`
- `empirical-design/DATA_PLAN.md`
- `empirical-design/TABLE_SHELLS.md`
- `empirical-design/ROBUSTNESS_PLAN.md`

## Output Summary

End with:

- strongest feasible claim
- weakest link in the design
- first three analyses to implement
- data or manual decisions needed before coding

## Rules

- Design tables around claims, not around available variables.
- State what the design can and cannot identify.
- Treat clustering and fixed effects as design decisions.
- Prefer a small number of decisive robustness checks over a long appendix list.
- Flag any result that would require causal language beyond the design.
