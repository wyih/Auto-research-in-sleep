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
3. `BUSINESS_NUMBER_AUDIT.md`
4. `SOURCE_CLAIM_AUDIT.md`
5. `AUTHOR_STYLE_PROFILE.md`
6. `empirical-design/RESEARCH_DESIGN.md`
7. `analysis/output/TABLE_INDEX.md`
8. `analysis/output/RESULTS_SUMMARY.md`
9. `BUSINESS_LIT_REVIEW.md`
10. `BUSINESS_RUN_PASSPORT.md`

If the user gives a specific section, load only the files needed for that section.

Read `../shared-references/business-style-calibration.md` when applying an author style profile. Read `../shared-references/business-handoff-schemas.md` when required inputs are incomplete.

## Workflow

### Step 1: Confirm Claim Ceiling

Before writing, check `CLAIMS_FROM_EVIDENCE.md`. Match verbs to evidence:

- descriptive: document, show, report
- associational: is associated with, is related to
- plausibly causal: increases, decreases, affects, only with stated design assumptions
- mechanism evidence: is consistent with, suggests, supports the mechanism

If `SOURCE_CLAIM_AUDIT.md` exists, fix or avoid any claim marked `MAJOR_DISTORTION`, `UNVERIFIABLE`, or `UNVERIFIABLE_ACCESS`. If it does not exist and the draft relies on literature, institutional facts, or citation-supported claims, route through `business-claim-source-audit` before submission-facing prose.

If `AUTHOR_STYLE_PROFILE.md` exists, apply it after claim ceilings are set. Journal and discipline norms override personal style.

### Step 2: Apply Style Profile

When style calibration is requested and `AUTHOR_STYLE_PROFILE.md` is missing, route to `business-author-style-profile`. Apply only style choices that preserve clarity, evidence strength, and journal norms.

### Step 3: Draft by Section

Use the business paper plan and any approved style profile:

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

### Step 4: Table Traceability

Every numeric statement must point to a table, figure, or output file.

If a planned claim lacks a table:

```latex
<!-- DATA_NEEDED: describe the missing table or empirical check -->
```

### Step 5: Referee Pass

Before finalizing, scan for:

- causal overstatement
- weak construct validity
- vague economic magnitude
- missing sample-construction detail
- unsupported mechanism language
- related-work overclaim
- source claims with unresolved source-audit issues

## Output

Create or update `paper/` using the existing ARIS LaTeX conventions when full manuscript generation is requested. For section-only work, update the requested section file.

## Rules

- For local tasks, complete only the requested stage and mark downstream gaps as next-stage inputs.
- Prefer concise, direct journal prose.
- Keep tables and claims synchronized.
- Preserve null or mixed findings.
- State assumptions in the design section.
- Use `DATA_NEEDED` comments for genuine gaps.
- Use `SOURCE_NEEDED` comments for citation or source support gaps.
