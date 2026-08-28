---
name: business-thesis-prereview
description: Committee-style pre-review for master's theses in accounting, finance, management, and economics (MPAcc rubric built in). Use when a draft thesis exists and the student needs pre-defense or pre-submission evaluation, dimension scoring, review comments, and a prioritized revision plan routed back to the business research suite skills.
---

# Business Thesis Pre-Review

Thesis target: $ARGUMENTS

## Purpose

Run a reviewer-side pre-review of a master's thesis draft using the suite's own verified artifacts, then convert findings into a revision plan routed back to the producing skills. This closes the student loop: topic selection → design → data → analysis → writing → pre-review → guided revision → re-review.

Scope: master's theses only. Not a substitute for the official degree review process. Never fabricate evidence, citations, or conclusions.

## Inputs

Read what exists; mark anything missing as `EVIDENCE_GAP` and lower confidence instead of guessing:

1. manuscript files under `paper/` or the project's thesis document
2. `BUSINESS_RUN_PASSPORT.md` — stage state, gate registry, decision cards
3. `empirical-design/RESEARCH_DESIGN.md` — including the Phase 0 method route; `empirical-design/CASE_PROTOCOL.md` for case-study theses
4. `CLAIMS_FROM_EVIDENCE.md` — claim levels and ceilings
5. `BUSINESS_NUMBER_AUDIT.md` and `SOURCE_CLAIM_AUDIT.md`
6. school or program rules (format requirements, pass thresholds) when provided
7. supervisor or committee focus areas when provided

## Workflow

### Step 1: Scope And Intake

Fix the review frame before scoring:

- thesis form: quantitative empirical / case or qualitative / interdisciplinary applied
- research area: accounting, auditing, corporate finance, governance, capital markets, or adjacent
- candidate stage: draft / pre-submission / revised resubmission
- material completeness: full text, abstract, table of contents, key tables, references, appendix
- the suite state: unresolved audit blockers and pending decision cards from the passport stay visible in the review

### Step 2: Dimension Scoring

Score with `references/mpacc_rubric.md` for MPAcc and accounting-adjacent theses; otherwise fall back to the generic master's rubric in `references/evaluation_framework.md`. For each dimension record at least one evidence pointer, one strength, and one or two problems, each with a confidence level.

Method-aware scoring:

- archival/quantitative theses: identification strategy, variable construction, robustness coverage, and number-audit consistency
- case-study theses: judge against the case claim ceilings — within-case explanatory inference only, triangulation per claim, predeclared replication logic, evidence chain from conclusions to case material; do not demand statistical representativeness
- a claim exceeding its `CLAIMS_FROM_EVIDENCE.md` ceiling is a scoring deduction, not a writing preference

### Step 3: Review Comments

Draft committee-style comments using `references/comment_patterns.md`: evidence → judgment → revision action → expected improvement. Cover overall evaluation, strengths, weaknesses, revision requests, and a submission recommendation (可送审 / 大修后送审 / 暂不建议送审). Chinese comments by default for Chinese programs; keep the tone strict but non-emotional.

### Step 4: Routed Revision Plan

Convert findings into a P0/P1/P2 plan. Every item names its target location, what to change, why it matters, how to verify completion, and the owning suite skill:

- wrong or inconsistent numbers, specification mismatches → `business-number-audit` fix path
- claims above the evidence ceiling, hedged or overclaimed language → `evidence-to-claim`
- unsupported citations, institutional or case-fact claims → `business-claim-source-audit`
- design or identification weaknesses → `empirical-design-plan`
- paper architecture problems → `business-paper-plan`
- prose, structure, or style issues → `business-paper-writing`
- case evidence-chain gaps → `empirical-design-plan` case branch and `business-claim-source-audit`

P0 = must fix before submission; P1 = strong quality improvements; P2 = polish and formatting.

### Step 5: Verdict And Re-Review Loop

State the submission recommendation with its conditions. After the student revises, rerun `business-number-audit` and `business-claim-source-audit` first, then rerun this pre-review; update the passport's Audit Status and Decision Cards. Do not mark the loop complete while a P0 item is open.

## Output

Write `THESIS_PREREVIEW.md` when writing is allowed:

```markdown
# Thesis Pre-Review

## Review Scope And Evidence Gaps
## Verdict
总分 / 等级 / 送审建议(附条件)
## Dimension Scores
| Dimension | Score | Evidence | Confidence | Key Risk |
## Review Comments
### Overall / Strengths / Weaknesses / Revision Requests
## Routed Revision Plan
| Priority | Location | Action | Verify By | Owning Skill |
## Re-Review Conditions
```

## Rules

- Master's theses only; decline undergraduate review and say so.
- Evidence before judgment: every criticism carries a location pointer; label missing material `EVIDENCE_GAP`.
- Every revision item routes to an owning suite skill; a comment that cannot be acted on inside the suite must say what external input it needs.
- Do not raise a claim above its recorded evidence ceiling, and do not let politeness flatten real deductions.
- Keep the verdict conditional on the provided materials and stated school rules.
