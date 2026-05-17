---
name: business-paper-writing
description: Draft or revise journal-style business, accounting, finance, management, and economics papers from a business paper plan, empirical design, and table outputs. Use when writing a manuscript, Introduction, hypothesis section, research design, results narrative, or adapting paper-writing to business-school journals.
---

# Business Paper Writing

Writing target: $ARGUMENTS

## Purpose

Convert business research evidence into a journal-style manuscript while preserving claim discipline and table traceability.

## Inputs

Prefer:

1. `BUSINESS_PAPER_PLAN.md`
2. `CLAIMS_FROM_EVIDENCE.md`
3. `empirical-design/RESEARCH_DESIGN.md`
4. `analysis/output/TABLE_INDEX.md`
5. `analysis/output/RESULTS_SUMMARY.md`
6. `BUSINESS_LIT_REVIEW.md`

If the user gives a specific section, load only the files needed for that section.

## Workflow

### Step 1: Confirm Claim Ceiling

Before writing, check `CLAIMS_FROM_EVIDENCE.md`. Match verbs to evidence:

- descriptive: document, show, report
- associational: is associated with, is related to
- plausibly causal: increases, decreases, affects, only with stated design assumptions
- mechanism evidence: is consistent with, suggests, supports the mechanism

### Step 2: Draft by Section

Use the business paper plan:

- Abstract: question, setting, design, finding, contribution
- Introduction: gap, setting, design, results, contribution
- Background: institutional details that support identification and mechanism
- Hypotheses: theory channel and directional predictions
- Data: sources, sample, variable construction, attrition
- Research Design: equation, identification, fixed effects, clustering
- Results: table-first narrative with economic magnitude
- Robustness: compact, risk-driven checks
- Mechanisms: evidence consistent with the proposed channel
- Conclusion: contribution and limits

### Step 3: Table Traceability

Every numeric statement must point to a table, figure, or output file.

If a planned claim lacks a table:

```latex
<!-- DATA_NEEDED: describe the missing table or empirical check -->
```

### Step 4: Referee Pass

Before finalizing, scan for:

- causal overstatement
- weak construct validity
- vague economic magnitude
- missing sample-construction detail
- unsupported mechanism language
- related-work overclaim

## Output

Create or update `paper/` using the existing ARIS LaTeX conventions when full manuscript generation is requested. For section-only work, update the requested section file.

## Rules

- Prefer concise, direct journal prose.
- Keep tables and claims synchronized.
- Preserve null or mixed findings.
- State assumptions in the design section.
- Use `DATA_NEEDED` comments for genuine gaps.
