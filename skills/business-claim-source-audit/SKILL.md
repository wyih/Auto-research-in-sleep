---
name: business-claim-source-audit
description: Use when auditing whether prose claims, literature claims, institutional facts, causal wording, mechanism statements, and cited-source summaries in business, accounting, finance, management, or economics papers are supported by sources and project evidence.
---

# Business Claim Source Audit

Audit target: $ARGUMENTS

## Purpose

Verify that manuscript claims are supported by cited sources, empirical outputs, or verified project materials. This complements `business-number-audit`, which checks numeric consistency.

## Inputs

Read what exists:

1. manuscript files in `paper/`, `.tex`, `.md`, or `.qmd`
2. `CLAIMS_FROM_EVIDENCE.md`
3. `BUSINESS_NUMBER_AUDIT.md`
4. `BUSINESS_LIT_REVIEW.md`
5. bibliography files, source PDFs, notes, and literature matrix
6. `empirical-design/RESEARCH_DESIGN.md`
7. `analysis/output/RESULTS_SUMMARY.md`
8. `BUSINESS_RUN_PASSPORT.md`

Read `../shared-references/business-claim-source-audit.md` for verdicts and output schema.

## Workflow

### Step 1: Build Claim Inventory

Extract claims that need support:

- cited-paper findings or arguments
- institutional facts
- market, regulatory, or accounting-setting facts
- trend claims
- mechanism statements
- causal or quasi-causal language
- headline empirical interpretations

### Step 2: Verify Support

For each claim, check the cited source or project artifact. Assign:

- `VERIFIED`
- `MINOR_DISTORTION`
- `MAJOR_DISTORTION`
- `UNVERIFIABLE`
- `UNVERIFIABLE_ACCESS`

### Step 3: Check Claim Ceiling

Compare causal and mechanism language against `CLAIMS_FROM_EVIDENCE.md`. A supported citation still cannot raise the empirical claim above the project evidence ceiling.

### Step 4: Repair Or Route

- Fix wording when support exists but the prose overstates it.
- Add `SOURCE_NEEDED` when support is missing.
- Return to `business-lit-review` or source collection when literature support is absent.
- Return to `evidence-to-claim` when empirical wording is too strong.

## Output

Write or update `SOURCE_CLAIM_AUDIT.md`:

```markdown
# Source Claim Audit

## Gate
GATE2: PASS | REOPEN_TEXT | REOPEN_SOURCES | REOPEN_ANALYSIS

## Claim Inventory
| Claim ID | Location | Claim Type | Claim Text | Cited Support |

## Source Support Table
| Claim ID | Source Checked | Verdict | Evidence | Required Fix |

## Unverified Or Distorted Claims
## Citation Repairs
## Required Follow-Up
```

## Rules

- For local tasks, complete only the requested stage and mark downstream gaps as next-stage inputs.
- Do not fabricate references or source passages.
- Use short quotes only when necessary; prefer paraphrased evidence notes.
- Keep unverifiable claims visible.
- Treat `MAJOR_DISTORTION` and headline `UNVERIFIABLE` claims as blocking before submission-facing writing.
