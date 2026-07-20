---
name: business-run-passport
description: Use when creating, updating, or checking the project-level passport for a business, accounting, finance, management, or economics research project, especially when tracking materials, data access levels, stages, artifact handoffs, audit gates, or reproducibility locks.
---

# Business Run Passport

Passport target: $ARGUMENTS

## Purpose

Maintain `BUSINESS_RUN_PASSPORT.md` as the project spine for materials, stage state, artifacts, decisions, audit gates, and reproducibility.

## References

Read as needed:

- `../shared-references/business-run-passport.md` for the passport schema
- `../shared-references/business-repro-lock.md` for `repro_lock`
- `../shared-references/business-handoff-schemas.md` for artifact requirements

## Workflow

### Step 1: Locate Project Materials

Look for:

- `BUSINESS_LIT_REVIEW.md`
- `idea-stage/BUSINESS_IDEA_REPORT.md`
- `BUSINESS_NOVELTY_CHECK.md`
- `literature/fulltext/FULLTEXT_MANIFEST.md`
- `method-harvest/METHOD_CARD_INDEX.md` and `method-harvest/cards/*_METHOD_CARD.md`
- `empirical-design/RESEARCH_DESIGN.md`
- `data/**/DATA_MANIFEST.md`, `Data/**/DATA_MANIFEST.md`, and protected-session receipts
- `analysis/output/RESULTS_SUMMARY.md`
- `analysis/output/results_docx/RESULTS_DOCX_MANIFEST.md`
- `CLAIMS_FROM_EVIDENCE.md`
- `BUSINESS_NUMBER_AUDIT.md`
- `SOURCE_CLAIM_AUDIT.md`
- `AUTHOR_STYLE_PROFILE.md`
- manuscript files under `paper/`

### Step 2: Create Or Update The Passport

Use `../shared-references/business-run-passport.md`. Fill only fields supported by available materials. Mark unknown required fields as `HANDOFF_INCOMPLETE`.

### Step 3: Add Repro Lock

When a final report, manuscript section, audit file, or analysis output is produced, add or refresh the `repro_lock` block. Use hashes for source materials and generated outputs when practical.

### Step 4: Update Gates

Record gate status:

- novelty
- fulltext and method evidence
- empirical design
- data acquisition
- results Word rendering and identity metadata
- evidence-to-claim
- number audit
- source-claim audit
- writing/style profile

Apply the shared run-state contract separately from stage gates. A stage can have an honest blocker while the project remains `waiting_external_gate` or `blocked_source` and the Goal stays active.

## Output

Create or update:

- `BUSINESS_RUN_PASSPORT.md`

When writing is not allowed, return a proposed passport patch.

## Rules

- For local tasks, complete only the requested stage and mark downstream gaps as next-stage inputs.
- Do not include secrets, credentials, cookies, or raw private data.
- Prefer `verified_only` materials for writing and audit skills.
- Keep unresolved issues visible in `Audit Status`.
- Treat `repro_lock` as a configuration record, not byte-identical replay.
- Never convert a missing browser turn, pending user checkpoint, or unattempted source into `terminal_stop` or project completion.
- When a design kill test fails, record `design_killed` for that design and evaluate viable pivots before changing the overall project state.
