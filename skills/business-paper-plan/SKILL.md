---
name: business-paper-plan
description: Build a journal-style paper outline for business, accounting, finance, management, and economics research. Use when planning a paper from a research design, regression tables, evidence-to-claim report, literature review, or when adapting paper-plan to business-school journal structure.
---

# Business Paper Plan

Paper context: $ARGUMENTS

## Purpose

Create a table-first, claim-disciplined outline for a business-school journal paper.

## Inputs

Read available files:

1. `CLAIMS_FROM_EVIDENCE.md`
2. `empirical-design/RESEARCH_DESIGN.md`
3. `empirical-design/TABLE_SHELLS.md`
4. `BUSINESS_LIT_REVIEW.md`
5. `analysis/output/RESULTS_SUMMARY.md`
6. `NARRATIVE_REPORT.md`

If `— style-ref: <source>` is provided, use the existing ARIS style-reference workflow for structural guidance only.

## Standard Structure

Choose the shortest structure that fits the evidence:

1. Introduction
2. Institutional Background or Setting
3. Theory and Hypothesis Development
4. Data and Sample
5. Research Design
6. Main Results
7. Robustness and Additional Analyses
8. Mechanisms or Cross-sectional Tests
9. Conclusion

Merge sections when the paper is short. Split sections when the design or journal convention requires it.

## Workflow

### Step 1: Claim-Evidence Matrix

Create:

| Claim | Claim Level | Evidence | Table/Figure | Section | Caveat |

### Step 2: Table-First Story

Plan the table order before prose:

- Table 1: sample and descriptives
- Table 2: main result
- Table 3: identification diagnostics or event study
- Table 4: robustness
- Table 5: mechanism
- Table 6: heterogeneity or additional analysis

Use only tables supported by existing evidence or a clear data-analysis plan.

### Step 3: Introduction Logic

Force the Introduction to answer:

- what question is asked
- why existing literature leaves it open
- what setting or shock identifies it
- what the paper finds
- why the finding matters economically and theoretically

### Step 4: Referee Risk Map

For each major section, list the likely referee objection and the planned answer.

## Output

Write `BUSINESS_PAPER_PLAN.md` when writing is allowed.

Include:

- title options
- one-sentence contribution
- abstract skeleton
- section plan
- claim-evidence matrix
- table and figure plan
- related-work positioning
- referee-risk map
- missing evidence markers

## Rules

- Put data and identification before decorative prose.
- Avoid promising tests that are absent from the table plan.
- Make contribution type explicit: theory, construct, setting, identification, data, or reconciliation.
- Keep the Introduction front-loaded with the actual finding.
- Mark missing evidence as `DATA_NEEDED` rather than inventing content.
