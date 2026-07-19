---
name: business-research-pipeline
description: Complete end-to-end business, accounting, finance, management, and economics research workflow for Codex or Grok. Use when the user wants one entry point that routes literature review, verified fulltext and method synthesis, idea and novelty, empirical design, WRDS or CSMAR/CNRDS acquisition, analysis, evidence audits, paper planning, writing, rebuttal, or resubmission.
---

# Business Research Pipeline

Research direction: $ARGUMENTS

## Purpose

Orchestrate a business-school research lifecycle while reusing ARIS artifact discipline.

## Default Mode: Current Stage

When the request names a stage, artifact, or local problem, load only the current stage skill and the minimum existing artifacts needed for that stage. Stop at the next checkpoint with produced output, missing inputs, and the next recommended skill.

## Full Pipeline Mode

Run the whole chain only when the user explicitly asks for a full pipeline, end-to-end run, or all stages. In full-pipeline mode, advance stage by stage and keep later-stage references unloaded until their stage begins.

## Shared Contracts

Read these references when the stage touches them:

- `../shared-references/business-run-passport.md` for the Business Run Passport
- `../shared-references/business-handoff-schemas.md` for stage artifact schemas
- `../shared-references/business-repro-lock.md` for final artifact reproducibility records

## Pipeline

```text
business-run-passport
  -> business-lit-review
     -> fulltext-acquire when a required PDF is missing
     -> method-harvest for design-relevant papers
     -> business-lit-review fulltext_synthesis from verified method cards
  -> business-idea-creator
  -> business-novelty-check
  -> empirical-design-plan
     -> wrds-query-bridge for WRDS (R/Postgres default)
        -> wrds-sas-cloud only after a recorded escalation or explicit SAS request
     -> cn-data-bridge for CSMAR/CNRDS gaps
  -> data-analysis-bridge
     -> r-analysis-bridge when R is the backend
     -> stata-analysis-bridge when Stata or .dta is the backend
     -> results-to-docx for a standalone academic results document
  -> evidence-to-claim
     -> business-number-audit before submission-ready writing
     -> business-claim-source-audit before submission-ready writing
  -> business-paper-plan
     -> business-author-style-profile when writing samples or target-journal style are available
  -> business-paper-writing
```

Use `business-rebuttal` after reviews arrive. Use `resubmit-pipeline` for text-only cross-venue resubmission of an already polished paper.

## Stages

### Stage 0: Business Run Passport

Run `business-run-passport`.

Output:

- `BUSINESS_RUN_PASSPORT.md`
- data access level map
- artifact index
- audit gate dashboard

### Stage 1: Literature and Positioning

Run `business-lit-review`.

Output:

- `BUSINESS_LIT_REVIEW.md`
- closest-paper delta
- journal conversation map

### Stage 2: Fulltext and Method Evidence

For papers whose methods, measures, data, or identification affect the design, run `fulltext-acquire` until each target has either an identity-matched verified PDF or a precise access gap. Then run `method-harvest` only on verified local PDFs.

Output:

- `literature/fulltext/FULLTEXT_MANIFEST.md`
- protected-session browser receipts when applicable
- `method-harvest/cards/*_METHOD_CARD.md`
- `method-harvest/METHOD_CARD_INDEX.md` for multiple papers
- `LITERATURE_EVIDENCE_MATRIX.md`
- updated source-grounded `BUSINESS_LIT_REVIEW.md`

This stage cannot pass from abstracts, metadata, a visible PDF viewer, or an unverified download click.
After cards exist, re-enter `business-lit-review` in `fulltext_synthesis` mode. Stage 2 is incomplete when the pipeline has only per-paper cards but no cross-paper comparison of constructs, variable calculations, designs, findings, boundaries, and claim ceilings.

### Stage 3: Idea Generation

Run `business-idea-creator`.

Output:

- `idea-stage/BUSINESS_IDEA_REPORT.md`
- top research question and data path

### Stage 4: Novelty Check

Run `business-novelty-check` on the top idea.

Output:

- novelty verdict
- risky framing to avoid
- closest working papers

### Stage 5: Empirical Design

Run `empirical-design-plan`.

Output:

- `empirical-design/RESEARCH_DESIGN.md`
- `empirical-design/DATA_PLAN.md`
- `empirical-design/TABLE_SHELLS.md`
- `empirical-design/ROBUSTNESS_PLAN.md`

### Stage 6: Data Acquisition

Resolve every required source in `empirical-design/DATA_PLAN.md` before estimation:

- Run `wrds-query-bridge` for WRDS. Use its R/Postgres path by default.
- Run `wrds-sas-cloud` only when the R path has a recorded timeout, OOM, hard failure, authentication blocker after retries, or the user explicitly requires SAS.
- Run `cn-data-bridge` for minimal CSMAR/CNRDS exports. It must route protected portal actions through `browser-session-bridge`, which selects Codex native Chrome or Grok's official DevTools safety facade at runtime; the legacy Grok bridge is an explicitly recorded fallback.

Output:

- immutable or rebuildable landed extracts
- query/program/filter records
- file hashes and schema/row checks
- `data/**/DATA_MANIFEST.md` or the project's established `Data/**` equivalent
- separate browser receipts for each protected runtime acceptance run

A login page, portal preview, successful query submission, or download toast is not a landed-data pass.

### Stage 7: Data Analysis and Results Packaging

Run `data-analysis-bridge` when data or a working dataset exists.

Output:

- analysis scripts
- regression tables
- `analysis/output/RESULTS_SUMMARY.md`

When the project uses R, `.R`, `.Rmd`, `.qmd`, `.rds`, tidyverse, or `fixest`, route execution through `r-analysis-bridge`. When the project uses Stata, `.dta` files, or `.do` files, route execution through `stata-analysis-bridge`.

When a standalone academic Word artifact is requested or required by the acceptance run, export tidy coefficient/descriptive inputs and run `results-to-docx`. Keep the Word output separate from the manuscript, normalize OOXML identity metadata to `Yihong Wang`, render it, and inspect the rendered pages.

### Stage 8: Evidence Gate

Run `evidence-to-claim`. Run `business-number-audit` once manuscript prose or numeric result text exists. Run `business-claim-source-audit` once the draft contains literature claims, institutional claims, or citation-supported prose.

Output:

- `CLAIMS_FROM_EVIDENCE.md`
- `BUSINESS_NUMBER_AUDIT.md` when paper text exists
- `SOURCE_CLAIM_AUDIT.md` when citation or source-supported claims exist
- safe claim language
- missing evidence list

### Stage 9: Paper Plan and Writing

Run `business-paper-plan`. Run `business-author-style-profile` when the user provides prior writing samples, advisor examples, or target journal exemplars. Then run `business-paper-writing`.

Output:

- `BUSINESS_PAPER_PLAN.md`
- `AUTHOR_STYLE_PROFILE.md` when style calibration is used
- manuscript sections or full `paper/` directory

## Checkpoints

Pause for user decision after:

- top idea selection
- novelty verdict
- empirical design before coding
- data acquisition plan before protected or high-cost exports
- evidence-to-claim verdict
- source-claim audit verdict when the draft is source-heavy
- paper plan before full manuscript drafting

## Rules

- Keep ML/GPU workflows out of the path unless the project truly needs predictive modeling.
- Keep the Business Run Passport updated at stage boundaries.
- Route empirical execution through `data-analysis-bridge`.
- Route missing fulltext through `fulltext-acquire` and method extraction through `method-harvest`; never infer method fields from abstracts.
- Route WRDS through `wrds-query-bridge` first and record any `wrds-sas-cloud` escalation reason.
- Route CSMAR/CNRDS through `cn-data-bridge`; its browser transport must come from `browser-session-bridge`.
- Browser UI is required for authenticated navigation, login-state reuse, and portal mutations that depend on the visible session. Checked-in helper scripts may orchestrate the selected bridge, wait for and copy downloads, hash files, inspect archives, and run deterministic semantic checks. Do not fail an otherwise valid stage merely because the same approved bridge calls were issued by a helper script instead of one-by-one model tool calls.
- Treat `results-to-docx` as a reproducible results package, not permission to overwrite a manuscript.
- Route claim interpretation through `evidence-to-claim`.
- Preserve ARIS audit discipline: source claims, table claims, citation claims, and reproducibility locks stay traceable.
- For local tasks, complete only the requested stage and mark downstream gaps as next-stage inputs.

## Full-Pipeline Acceptance

The complete entry point passes only when a fresh session can discover this skill, route every requested stage through its named child skill, and leave independently checkable artifacts. Each stage must be either `passed` with its required evidence or `blocked` with a precise unresolved gap; inherited logs, old files, browser toasts, and unverified clicks are not fresh acceptance evidence. For protected sources, verify the landed PDF or data slice by identity, structure or required columns, size, and hash before allowing downstream synthesis or analysis.
