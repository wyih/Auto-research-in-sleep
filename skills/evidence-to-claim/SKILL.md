---
name: evidence-to-claim
description: Judge what claims empirical evidence supports in business, accounting, finance, management, and economics papers. Use after regressions, robustness tests, event studies, DiD, IV, RD, textual analyses, surveys, or table outputs are available and before writing causal or theoretical claims.
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

## Workflow

### Step 1: Map Evidence

For each table or figure:

- identify the exact claim it can support
- record sample, specification, and dependent variable
- record sign, magnitude, standard error, and economic magnitude
- record robustness status

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
- `not_supported`: revise the paper claim or return to `empirical-design-plan`.
- citation-heavy, institutional, or literature claims: route to `business-claim-source-audit` after drafting exists.

## Output

Write `CLAIMS_FROM_EVIDENCE.md` when writing is allowed:

```markdown
# Claims From Evidence

## Claim Verdicts
| Intended Claim | Supported Level | Evidence | Confidence | Required Caveat |

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
