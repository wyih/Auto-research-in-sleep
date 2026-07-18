---
name: business-research-suite
description: Use when the user wants one entry point for business, accounting, finance, management, or economics research workflows, asks which business research skill to use, or wants an end-to-end empirical paper route without installing ML-focused ARIS skills.
---

# Business Research Suite

Request: $ARGUMENTS

## Purpose

Route business-school research work to the right focused skill while keeping the project passport, handoff schemas, and audit gates synchronized.

## Default Mode: Light Router

Default to a small-context route decision. Identify the current stage, then load one focused skill body. Load shared references only after the focused skill needs them.

Full-pipeline mode requires explicit user wording such as `full pipeline`, `end-to-end`, `all stages`, or `from topic to paper`.

## First Reads

Read these only as needed:

- `../shared-references/business-mode-registry.md` for mode routing
- `../shared-references/business-run-passport.md` when a project has no `BUSINESS_RUN_PASSPORT.md`
- `../shared-references/business-handoff-schemas.md` before handing artifacts between skills

## Routing

Use the most specific mode:

- broad topic or uncertain RQ: `business-idea-creator`
- literature discovery map or verified-card cross-paper synthesis: `business-lit-review`
- missing paper PDF or protected publisher access: `fulltext-acquire`
- method, measure, sample, or identification extraction from verified PDFs: `method-harvest`
- novelty and closest-paper delta: `business-novelty-check`
- design, sample, variables, models, table shells: `empirical-design-plan`
- WRDS data through the default R/Postgres path: `wrds-query-bridge`
- WRDS SAS Cloud after a recorded escalation condition or explicit SAS request: `wrds-sas-cloud`
- CSMAR or CNRDS variable resolution and minimal portal export: `cn-data-bridge`
- backend-neutral analysis coordination: `data-analysis-bridge`
- R analysis: `r-analysis-bridge`
- Stata analysis: `stata-analysis-bridge`
- standalone academic results Word document: `results-to-docx`
- result interpretation: `evidence-to-claim`
- project spine and reproducibility state: `business-run-passport`
- manuscript number QA: `business-number-audit`
- source and citation claim QA: `business-claim-source-audit`
- paper architecture: `business-paper-plan`
- author voice calibration: `business-author-style-profile`
- paper drafting or revision: `business-paper-writing`
- response to reviewers: `business-rebuttal`
- staged end-to-end run: `business-research-pipeline`

## Workflow

1. Identify the user's current material state: topic, literature, idea, design, data, results, draft, reviews.
2. Select the single next stage and load one focused skill body. Use `browser-session-bridge` only as the internal transport for a protected-site skill; do not route a research request there when a more specific producer owns the artifact.
3. Create or update `BUSINESS_RUN_PASSPORT.md` when working inside a project directory and writing is allowed.
4. Use `../shared-references/business-handoff-schemas.md` to mark missing required fields as `HANDOFF_INCOMPLETE` after the focused skill needs a handoff.
5. Route to `business-research-pipeline` only for explicit full-pipeline requests.
6. Before submission-facing writing, require both `BUSINESS_NUMBER_AUDIT.md` and `SOURCE_CLAIM_AUDIT.md`.

## Output

For routing-only requests, return:

```markdown
# Business Research Suite Routing

## Recommended Mode
## Skill To Use
## Required Inputs
## Expected Output
## Gate Before Next Stage
```

For project work, update the passport and then run the selected skill.

## Rules

- Keep ML/GPU workflow skills out of the route unless the business paper truly uses predictive modeling.
- Prefer one focused skill over the full pipeline when the user asks for a specific stage.
- Do not skip from literature metadata to method claims: acquire identity-matched fulltext, then run `method-harvest`.
- After multiple method cards exist, route back to `business-lit-review` in `fulltext_synthesis` mode; do not hand a stack of per-paper summaries directly to idea generation or writing.
- Do not skip from a data plan to analysis: resolve and land each required WRDS/CSMAR/CNRDS extract first, or record a concrete access gap.
- Use R/Postgres as the default WRDS route; use SAS only after the policy gate or an explicit user request.
- Treat audit gates as project evidence, not prose polish.
- Mark missing literature, citations, tables, or results as gaps.
