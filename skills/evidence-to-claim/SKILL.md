---
name: evidence-to-claim
description: Judge what claims empirical evidence supports in business, accounting, finance, management, and economics papers. Use after regressions, robustness tests, event studies, DiD, IV, RD, textual analyses, surveys, case-study evidence displays, or table outputs are available and before writing causal or theoretical claims.
---

# Evidence To Claim

Evidence context: $ARGUMENTS

## Purpose

Translate tables and empirical outputs into defensible paper claims.

## Inputs

Read:

1. `analysis/output/RESULTS_SUMMARY.md`
2. `analysis/output/TABLE_INDEX.md`
3. `empirical-design/RESEARCH_DESIGN.md`
4. `empirical-design/TABLE_SHELLS.md`
5. table files, regression logs, and figure outputs
6. `BUSINESS_RUN_PASSPORT.md` when present

Read `../shared-references/business-handoff-schemas.md` when producing or validating `CLAIMS_FROM_EVIDENCE.md`.

## Claim Levels

Use the highest supported level:

- `descriptive`: documents a pattern or institutional fact
- `associational`: shows a conditional relation
- `plausibly_causal`: design supports causal interpretation under stated assumptions
- `mechanism_consistent`: mechanism tests align with the theory but remain indirect
- `not_supported`: evidence is too weak, unstable, or mismatched

### Case-Study Claim Levels

When Phase 0 of `empirical-design-plan` routed the project to case study, use these levels instead of the statistical ones above:

- `within_case_descriptive`: documents what happened inside the case boundary from triangulated sources
- `within_case_explanatory`: explains how/why inside the case via pattern matching, explanation building, or process analysis, with rival explanations addressed
- `cross_case_replication`: a pattern repeats across cases per the predeclared replication logic (literal or theoretical)
- `theory_contribution`: extends, revises, or builds theoretical constructs; generalizes to theory, never to populations
- `not_supported`: evidence is single-source, contradicts the case record, or rests only on management narrative

Case claims never reach `plausibly_causal` in the statistical sense; causal verbs stay inside the case boundary.

## Workflow

### Step 1: Map Evidence

For each table or figure:

- identify the exact claim it can support
- record sample, specification, and dependent variable
- record sign, magnitude, standard error, and economic magnitude
- record robustness status

For case-study projects, map evidence displays instead — event timeline, construct tables, replication matrix:

- identify the exact claim each display can support
- record which source types (documents, archival records, interviews, observation, artifacts) support it, per claim
- record conflicting or negative evidence per claim
- record which case(s) and which analytic unit the claim covers

### Step 2: Stress the Claim

Check:

- alternative explanations
- sample selection
- measurement error
- omitted variables
- reverse causality
- timing and pre-trends
- clustering and inference
- multiple testing
- external validity

For case-study claims, stress instead:

- rival explanations and whether the analysis addressed them
- survivor and selection bias in case choice
- single-source dependence and missing triangulation
- negative cases and disconfirming evidence
- analytic (not statistical) generalization limits
- narrative polish substituting for event anchors

### Step 3: Assign Claim Ceiling

For each intended claim, assign:

- supported claim level
- confidence: high, medium, low
- required caveat
- language to use
- language to avoid
- missing evidence

### Step 4: Route

- `descriptive` or `associational`: write cautious finding language.
- `plausibly_causal`: state assumptions and identification source.
- `mechanism_consistent`: frame as mechanism evidence, not proof.
- case-study levels: keep `within_case_*` claims inside the case boundary; frame `cross_case_replication` as replication under the predeclared logic; frame `theory_contribution` as analytic generalization to theory.
- `not_supported`: revise the paper claim or return to `empirical-design-plan`.
- citation-heavy, institutional, or literature claims: route to `business-claim-source-audit` after drafting exists.

## Output

Write `CLAIMS_FROM_EVIDENCE.md` when writing is allowed:

```markdown
# Claims From Evidence

## Claim Verdicts
| Intended Claim | Supported Level | Evidence | Confidence | Required Caveat |

## Case Claim Matrix (case-study projects)
| Intended Claim | Supported Level | Cases Covered | Source Types | Conflicting Evidence | Required Caveat |

## Safe Language

## Language to Avoid

## Missing Evidence

## Recommended Paper Framing
```

## Rules

- For local tasks, complete only the requested stage and mark downstream gaps as next-stage inputs.
- Keep causal verbs reserved for designs that support them.
- Report null and mixed results as design information.
- Treat economic magnitude as separate from statistical significance.
- State when a result supports a mechanism only indirectly.
- Preserve uncertainty in the final claim language.
- Leave source-support verification to `business-claim-source-audit`; keep this skill focused on empirical evidence ceilings.
