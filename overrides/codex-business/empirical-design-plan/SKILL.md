---
name: empirical-design-plan
description: Plan and feasibility-test empirical research designs for accounting, finance, management, economics, and business papers. Use for method routing across archival, experiment, survey, field, case-study, design-science, and normative research; identification, sample construction, variables, models, table shells, robustness, event studies, DiD, IV, RD, case-study design and protocols, gate calibration, sample benchmarks, power or precision, claim ladders, scope-down choices, and defensible STOP decisions.
---

# Empirical Design Plan

Research idea: $ARGUMENTS

## Purpose

Turn a business research idea into a referee-readable empirical design and table plan.

For a local question or revision, address the requested design decision and update the relevant existing artifact. Use the full phases and separate output files for a complete design or an actual pipeline handoff. Reuse established method choices and supported feasibility work unless the requested change affects them.

## Inputs

Read available files in this order:

1. `idea-stage/BUSINESS_IDEA_REPORT.md`
2. `BUSINESS_LIT_REVIEW.md`
3. `BUSINESS_NOVELTY_CHECK.md`
4. `RESEARCH_BRIEF.md`
5. `BUSINESS_RUN_PASSPORT.md` when present
6. `method-harvest/cards/*_METHOD_CARD.md` and `LITERATURE_EVIDENCE_MATRIX.md` when sample or design benchmarks affect feasibility
7. user-provided data dictionaries or sample notes

Read `../shared-references/business-handoff-schemas.md` when an actual consumer requires those schemas.
Read `../shared-references/business-feasibility-gates.md` before proposing a numerical gate, kill test, high-cost acquisition, or STOP rule.
Read `../shared-references/business-method-routing.md` when selecting or reconsidering the first-level method.

## Workflow

### Phase 0: Route the Method

Classify the idea into exactly one first-level method — archival, experiment, survey, field research, case study, design science, or normative — using the criteria and boundary rules in `business-method-routing.md`. Record the routed method, the primary criterion that fired, and the rejected alternatives at the top of `RESEARCH_DESIGN.md`.

- Archival (including quasi-natural experiments and textual analysis) → continue with Phases 1–6 below.
- Case study → use the Case Study Branch below; Phases 1, 3, and 6 still apply with the branch's adaptations.
- Experiment or survey → continue with Phases 1–6; acquisition runs through project-managed instruments, not WRDS/CSMAR bridges.
- Field research, design science, or normative → this skill has no dedicated design path; record the gap in `RESEARCH_DESIGN.md` and route back to `business-research-suite` instead of forcing the archival template.

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

Use this phase for a full design, costly acquisition, new hard gate, or a change affecting feasibility. Reuse still-applicable calibration for local revisions.

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

### Case Study Branch

Use when Phase 0 routes to case study. Follow the case-study design contract in `business-method-routing.md` and adapt the phases:

- Claims (Phase 1): causal language is capped at within-case explanatory inference; cross-case conclusions generalize to theory through replication logic, never to populations. Replace "robustness" with rival-explanation handling, triangulation, and negative-case analysis.
- Design specification (Phase 2): replace the variable/FE/clustering list with the required case design elements — research question, case boundary, unit of analysis, theory role, case type, selection logic, data sources, analysis strategy, quality plan.
- Feasibility (Phase 3): benchmark against verified closest case studies for site access, informant coverage, evidence volume per source type, and case count justification; freeze the claim ladder (within-case explanation → cross-case replication → theory contribution); access failure to the primary site is a recoverable gate with named backup cases, not an automatic stop.
- Table shells (Phase 4): replace with evidence displays — event timeline, construct tables, evidence–claim matrix, replication matrix for multi-case work.
- Outputs (Phase 6): additionally write `empirical-design/CASE_PROTOCOL.md` covering questions, field procedures, interview/observation topics, required documents, data storage, analysis templates, and the evidence-chain plan from conclusions back to case material.

### Phase 6: Write Outputs

For a full design or a pipeline requiring these artifacts, create or update:

- `empirical-design/RESEARCH_DESIGN.md`
- `empirical-design/DATA_PLAN.md`
- `empirical-design/TABLE_SHELLS.md`
- `empirical-design/ROBUSTNESS_PLAN.md`
- `empirical-design/FEASIBILITY_AND_GATE_CALIBRATION.md`

For a local revision, update only the affected design content; keep calibration in that artifact unless the project requires a separate file. Maintain `BUSINESS_RUN_PASSPORT.md` through `business-run-passport` when the project already uses it, the user requests it, or an actual downstream consumer requires it.

## Output Summary

Report the design decision and next necessary action. For a complete design, also cover:

- strongest feasible claim
- closest-study benchmark and expected precision
- weakest link in the design
- best-case attainable gate result and fallback claim tier
- next analyses needed to implement the design
- data or manual decisions needed before coding

## Rules

- Establish or reuse the first-level method (Phase 0). DID, IV, RDD, PSM, event studies, and textual analysis are techniques inside archival research, not parallel paradigms; never escalate method choice by technique sophistication.
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
