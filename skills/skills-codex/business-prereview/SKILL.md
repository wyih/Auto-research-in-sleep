---
name: business-prereview
description: Reviewer-side pre-review for business, accounting, finance, management, and economics manuscripts — master's theses (MPAcc rubric built in) AND journal papers (referee-report mode with target-journal fit). Use when a draft exists and the author needs pre-defense or pre-submission evaluation, dimension scoring, review comments, and a prioritized revision plan routed back to the business research suite skills.
---

# Business Paper Pre-Review (Thesis & Journal)

Manuscript target: $ARGUMENTS

## Purpose

Run a reviewer-side pre-review of a draft using the suite's own verified artifacts, then convert findings into a revision plan routed back to the producing skills. This closes the loop: topic selection → design → data → analysis → writing → pre-review → guided revision → re-review.

Two modes, picked at intake:

- **Thesis mode** — master's theses (committee voice, degree-rubric scoring, 送审 verdict).
- **Journal mode** — papers aimed at a journal (referee voice, referee-report structure, target-journal fit and recommendation).

Never fabricate evidence, citations, or conclusions. Not a substitute for the official degree review or the journal's own peer review.

## Inputs

Read what exists; mark anything missing as `EVIDENCE_GAP` and lower confidence instead of guessing:

1. manuscript files under `paper/` or the project's main document
2. `BUSINESS_RUN_PASSPORT.md` — stage state, gate registry, decision cards
3. `empirical-design/RESEARCH_DESIGN.md` — including the Phase 0 method route; `empirical-design/CASE_PROTOCOL.md` for case-study work
4. `CLAIMS_FROM_EVIDENCE.md` — claim levels and ceilings
5. `BUSINESS_NUMBER_AUDIT.md` and `SOURCE_CLAIM_AUDIT.md`
6. novelty artifacts (`business-novelty-check` output, literature map) — especially in journal mode
7. thesis mode: school/program rules (format requirements, pass thresholds), supervisor or committee focus areas when provided
8. journal mode: target journal name and its aims/recent neighbor papers when provided

## Workflow

### Step 1: Scope And Intake

Fix the review frame before scoring:

- **mode**: degree thesis or journal manuscript; if unclear from the materials, ask one question (degree or journal? which program / which target journal?)
- paper form: quantitative empirical / case or qualitative / interdisciplinary applied
- research area: accounting, auditing, corporate finance, governance, capital markets, or adjacent
- candidate stage: draft / pre-submission / revised resubmission
- material completeness: full text, abstract, references, key tables, appendix
- the suite state: unresolved audit blockers and pending decision cards from the passport stay visible in the review

### Step 2: Dimension Scoring

**Thesis mode**: score with `references/mpacc_rubric.md` for MPAcc and accounting-adjacent theses; otherwise fall back to the generic master's rubric in `references/evaluation_framework.md`.

**Journal mode**: score with `references/journal_referee_rubric.md` — contribution and incremental novelty (checked against the novelty artifacts, not the author's claims), theory and hypothesis development, research design and identification, execution and robustness, exposition and structure, and fit to the target journal's aims and current conversation.

For each dimension record at least one evidence pointer, one strength, and one or two problems, each with a confidence level.

Method-aware scoring (both modes):

- archival/quantitative papers: identification strategy, variable construction, robustness coverage, and number-audit consistency
- case-study papers: judge against the case claim ceilings — within-case explanatory inference only, triangulation per claim, predeclared replication logic, evidence chain from conclusions to case material; do not demand statistical representativeness
- a claim exceeding its `CLAIMS_FROM_EVIDENCE.md` ceiling is a scoring deduction, not a writing preference

### Step 3: Review Comments

**Thesis mode**: draft committee-style comments using `references/comment_patterns.md`: evidence → judgment → revision action → expected improvement. Cover overall evaluation, strengths, weaknesses, revision requests, and a submission recommendation (可送审 / 大修后送审 / 暂不建议送审). Chinese comments by default for Chinese programs; keep the tone strict but non-emotional.

**Journal mode**: draft a referee report — one-paragraph summary of the paper as the referee understands it, then major comments (each: issue → why it threatens the conclusion → what evidence or analysis would resolve it), then minor comments. End with a pre-submission recommendation: ready to submit / minor revision before submission / major revision before submission / not ready for this journal. Add a journal-fit note: does the paper join the target journal's current conversation, and if not, which venue fits better. Match the working language of the manuscript.

### Step 4: Routed Revision Plan

Convert findings into a P0/P1/P2 plan. Every item names its target location, what to change, why it matters, how to verify completion, and the owning suite skill:

- wrong or inconsistent numbers, specification mismatches → `business-number-audit` fix path
- claims above the evidence ceiling, hedged or overclaimed language → `evidence-to-claim`
- unsupported citations, institutional or case-fact claims → `business-claim-source-audit`
- contribution/novelty positioning weaknesses (journal mode) → `business-novelty-check` and `business-lit-review`
- design or identification weaknesses → `empirical-design-plan`
- paper architecture problems → `business-paper-plan`
- prose, structure, or style issues → `business-paper-writing`
- case evidence-chain gaps → `empirical-design-plan` case branch and `business-claim-source-audit`

P0 = must fix before submission; P1 = strong quality improvements; P2 = polish and formatting.

### Step 5: Verdict And Re-Review Loop

State the recommendation with its conditions. After the author revises, rerun `business-number-audit` and `business-claim-source-audit` first, then rerun this pre-review; update the passport's Audit Status and Decision Cards. Do not mark the loop complete while a P0 item is open.

## Output

Thesis mode writes `THESIS_PREREVIEW.md`; journal mode writes `JOURNAL_PREREVIEW.md` when writing is allowed:

```markdown
# Thesis / Journal Pre-Review

## Review Scope And Evidence Gaps
(mode, venue or program, materials read, EVIDENCE_GAP list)
## Verdict
总分 / 等级 / 送审建议(附条件) — thesis mode
recommendation + journal-fit note — journal mode
## Dimension Scores
| Dimension | Score | Evidence | Confidence | Key Risk |
## Review Comments
thesis mode: Overall / Strengths / Weaknesses / Revision Requests
journal mode: Summary / Major Comments / Minor Comments
## Routed Revision Plan
| Priority | Location | Action | Verify By | Owning Skill |
## Re-Review Conditions
```

## Rules

- Degree-thesis review is master's level only; decline undergraduate review and say so. Journal mode has no degree restriction.
- Evidence before judgment: every criticism carries a location pointer; label missing material `EVIDENCE_GAP`.
- Every revision item routes to an owning suite skill; a comment that cannot be acted on inside the suite must say what external input it needs.
- Do not raise a claim above its recorded evidence ceiling, and do not let politeness flatten real deductions.
- Keep the verdict conditional on the provided materials and stated program rules or target journal.
