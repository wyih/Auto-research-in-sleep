---
name: business-prereview
description: Reviewer-side pre-review for business, accounting, finance, management, and economics manuscripts — master's theses (MPAcc rubric built in) AND journal papers (referee-report mode with target-journal fit). Use when a draft exists and the author needs pre-defense or pre-submission evaluation, dimension scoring, review comments, and a prioritized revision plan routed back to the business research suite skills.
---

# Business Paper Pre-Review (Thesis & Journal)

Manuscript target: $ARGUMENTS

## Purpose

Run a reviewer-side pre-review of a draft using the suite's own verified artifacts, then convert findings into a revision plan routed back to the producing skills. This closes the loop: topic selection → design → data → analysis → writing → pre-review → guided revision → re-review.

Two modes, picked at intake:

- **Thesis mode** — master's theses (committee voice, degree-rubric evaluation, 送审 verdict).
- **Journal mode** — papers aimed at a journal (referee voice, referee-report structure, target-journal fit and recommendation).

Never fabricate evidence, citations, or conclusions. Not a substitute for the official degree review or the journal's own peer review.

## Inputs

Read available materials or their project equivalents. Mark a missing item `EVIDENCE_GAP` only when its evidence is needed for the requested judgment; missing suite artifact names alone do not lower the paper's assessment:

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

Establish the review frame:

- **mode**: degree thesis or journal manuscript; if unclear from the materials, ask one question (degree or journal? which program / which target journal?)
- paper form: quantitative empirical / case or qualitative / interdisciplinary applied
- research area: accounting, auditing, corporate finance, governance, capital markets, or adjacent
- candidate stage: draft / pre-submission / revised resubmission
- material completeness: full text, abstract, references, key tables, appendix
- the suite state: unresolved audit blockers and pending decision cards from the passport stay visible in the review

### Step 2: Evidence-Based Evaluation

Use numerical scores only when the user requests them or a supplied review form requires them. Otherwise use the rubric's substantive criteria for written judgments.

**Thesis mode**: evaluate with `references/mpacc_rubric.md` for MPAcc and accounting-adjacent theses; otherwise use the generic master's rubric in `references/evaluation_framework.md`.

**Journal mode**: evaluate with `references/journal_referee_rubric.md` — contribution and incremental novelty checked against the actual nearest literature, theory and hypothesis development, research design and identification, execution and robustness, exposition and structure, and journal fit when requested or part of an agreed submission review.

Read [field referee checks](references/field-referee-checks.md) for journal review or a concrete accounting/finance issue in a thesis. Compare the contribution the author claims with what the design, exhibits, and closest studies establish. Use the relevant accounting, corporate-finance, asset-pricing, banking, or text-measure checks; recommend additional analysis only when it resolves a substantive issue.

Report the strengths and problems supported by the manuscript, with evidence locations. Do not require a fixed count for each dimension; distinguish an absent problem from insufficient evidence to assess it.

Method-aware evaluation (both modes):

- archival/quantitative papers: identification strategy, variable construction, robustness coverage, and number-audit consistency
- case-study papers: judge against the case claim ceilings — within-case explanatory inference only, triangulation per claim, predeclared replication logic, evidence chain from conclusions to case material; do not demand statistical representativeness
- a claim exceeding its evidence ceiling is a substantive issue; use `CLAIMS_FROM_EVIDENCE.md` when available

### Step 3: Review Comments

**Thesis mode**: draft committee-style comments using `references/comment_patterns.md`: evidence → judgment → revision action → expected improvement. Cover overall evaluation, strengths, weaknesses, revision requests, and a submission recommendation (可送审 / 大修后送审 / 暂不建议送审). Chinese comments by default for Chinese programs; keep the tone strict but non-emotional.

**Journal mode**: for a full referee report, give a short summary of the question, claimed contribution, and supported finding, then major comments and minor comments. Each substantive comment names the location, observed issue, supporting evidence, effect on the conclusion or contribution, and what correction or verification would resolve it. Distinguish verified failures from questions requiring verification. Keep substantive and editorial comments separate within the requested report; a separate editing file is optional. Match the working language of the manuscript.

When submission readiness is requested, state a supported recommendation: ready to submit / minor revision before submission / major revision before submission / not ready for this journal. Assess journal fit when requested or part of the agreed submission review; suggest alternative venues only when asked.

### Step 4: Routed Revision Plan

For a full review or requested revision plan, convert findings into a P0/P1/P2 plan. Every item names its target location, what to change, why it matters, how to verify completion, and the owning suite skill. Record dependencies when one correction changes another: verify the information date before rebuilding a variable, rerun the affected model, then revise its interpretation.

Route actual findings:

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

State the recommendation with its conditions. When re-review is requested, check the revised issues and affected claims; run separate number or source audits when needed to resolve those issues or required by the project's workflow. Update the passport's Audit Status and Decision Cards when the project already maintains them. Unresolved P0 issues prevent a submission-ready verdict.

## Output

Match the requested deliverable. A full thesis review may use `THESIS_PREREVIEW.md`; a full journal review may use `JOURNAL_PREREVIEW.md`. Omit score sections unless scoring was requested or required by the supplied form:

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
