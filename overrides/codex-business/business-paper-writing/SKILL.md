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

Read `../shared-references/business-style-calibration.md` when applying an author style profile. Read `../shared-references/writing-principles.md` before drafting or revising prose, especially when the draft feels generic, templated, or AI-shaped. Read `../shared-references/business-handoff-schemas.md` when an actual pipeline consumer requires those schemas; equivalent supplied evidence is sufficient for standalone writing.

## Workflow

### Step 1: Confirm Claim Ceiling

Before writing, establish the claim ceiling from the supplied design and results, using `CLAIMS_FROM_EVIDENCE.md` when available. Match verbs to evidence:

- descriptive: document, show, report
- associational: is associated with, is related to
- plausibly causal: increases, decreases, affects, only with stated design assumptions
- mechanism evidence: is consistent with, suggests, supports the mechanism

If `SOURCE_CLAIM_AUDIT.md` exists, fix or avoid any claim marked `MAJOR_DISTORTION`, `UNVERIFIABLE`, or `UNVERIFIABLE_ACCESS`. Otherwise verify the relevant claims against their sources while writing. Missing support is a substantive gap; a missing audit file alone is not. Produce separate source or number audits only when requested or required by the project's submission workflow. Route unresolved source verification to `business-claim-source-audit` when its focused workflow is needed.

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

This list defines content coverage, not a paragraph template or section quota. Let the available evidence determine the order, length, and number of rhetorical moves. Do not manufacture a mechanism, implication, or contribution category to fill the list.

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
- manufactured contrasts such as "not X, but Y" or `不是……而是……` when X is not a real interpretation or claim that the paper must reject
- repeated background -> gap -> contribution -> generic implication scaffolds across paragraphs
- automatic "first, second, finally," "on the one hand/on the other hand," rule-of-three, or paired theoretical/practical contribution structures without distinct supporting content
- defensive wording, per the scan list in `../shared-references/business-confident-prose.md`: stacked hedges, per-paragraph caveats outside the limits discussion, self-defence ("we do not claim", "our goal is merely"), reviewer-facing prebuttals that apologize for the sample, setting, or design

For each style finding, quote the exact sentence or paragraph and explain which contrast or scaffold lacks substantive support. If the affirmative claim stands after removing the setup, state it directly. Rewrite from the paper's claim, evidence, or boundary; do not replace one stock phrase with another.

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

### Confident prose, honest limits

Apply `../shared-references/business-confident-prose.md` whenever drafting or revising prose — that contract is binding, not advisory. In short: calibrate each claim to the evidence, then state it directly; generic caveats live only in the limits paragraph of the Conclusion; no "we do not claim X" self-defence or reviewer-facing prebuttals; tone edits never alter facts, numbers, scope, or citations, and never hide null or mixed findings.
