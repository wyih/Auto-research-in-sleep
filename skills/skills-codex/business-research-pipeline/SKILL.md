---
name: business-research-pipeline
description: End-to-end business, accounting, finance, management, and economics research workflow. Use when the user wants a business-school paper pipeline from literature review to idea, novelty, empirical design, data analysis, evidence-to-claim, paper plan, writing, rebuttal, or resubmission.
---

# Business Research Pipeline

Research direction: $ARGUMENTS

## Purpose

Orchestrate a business-school research lifecycle while reusing ARIS artifact discipline.

## Pipeline

```text
business-lit-review
  -> business-idea-creator
  -> business-novelty-check
  -> empirical-design-plan
  -> data-analysis-bridge
     -> r-analysis-bridge when R is the backend
     -> stata-analysis-bridge when Stata or .dta is the backend
  -> evidence-to-claim
     -> business-number-audit before submission-ready writing
  -> business-paper-plan
  -> business-paper-writing
```

Use `business-rebuttal` after reviews arrive. Use `resubmit-pipeline` for text-only cross-venue resubmission of an already polished paper.

## Stages

### Stage 1: Literature and Positioning

Run `business-lit-review`.

Output:

- `BUSINESS_LIT_REVIEW.md`
- closest-paper delta
- journal conversation map

### Stage 2: Idea Generation

Run `business-idea-creator`.

Output:

- `idea-stage/BUSINESS_IDEA_REPORT.md`
- top research question and data path

### Stage 3: Novelty Check

Run `business-novelty-check` on the top idea.

Output:

- novelty verdict
- risky framing to avoid
- closest working papers

### Stage 4: Empirical Design

Run `empirical-design-plan`.

Output:

- `empirical-design/RESEARCH_DESIGN.md`
- `empirical-design/DATA_PLAN.md`
- `empirical-design/TABLE_SHELLS.md`
- `empirical-design/ROBUSTNESS_PLAN.md`

### Stage 5: Data Analysis

Run `data-analysis-bridge` when data or a working dataset exists.

Output:

- analysis scripts
- regression tables
- `analysis/output/RESULTS_SUMMARY.md`

When the project uses R, `.R`, `.Rmd`, `.qmd`, `.rds`, tidyverse, or `fixest`, route execution through `r-analysis-bridge`. When the project uses Stata, `.dta` files, or `.do` files, route execution through `stata-analysis-bridge`.

### Stage 6: Evidence Gate

Run `evidence-to-claim`. Run `business-number-audit` once manuscript prose or numeric result text exists.

Output:

- `CLAIMS_FROM_EVIDENCE.md`
- `BUSINESS_NUMBER_AUDIT.md` when paper text exists
- safe claim language
- missing evidence list

### Stage 7: Paper Plan and Writing

Run `business-paper-plan`, then `business-paper-writing`.

Output:

- `BUSINESS_PAPER_PLAN.md`
- manuscript sections or full `paper/` directory

## Checkpoints

Pause for user decision after:

- top idea selection
- novelty verdict
- empirical design before coding
- evidence-to-claim verdict
- paper plan before full manuscript drafting

## Rules

- Keep ML/GPU workflows out of the path unless the project truly needs predictive modeling.
- Route empirical execution through `data-analysis-bridge`.
- Route claim interpretation through `evidence-to-claim`.
- Preserve ARIS audit discipline: source claims, table claims, and citation claims stay traceable.
