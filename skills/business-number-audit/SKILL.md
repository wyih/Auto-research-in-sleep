---
name: business-number-audit
description: Audit manuscript numbers, regression claims, samples, fixed effects, clustering, controls, tables, figures, and logs for business, accounting, finance, management, and economics papers. Use before paper writing completion, revisions, submission, or response letters when empirical outputs must match the text.
---

# Business Number Audit

Audit target: $ARGUMENTS

## Purpose

Verify that paper claims match the empirical outputs on disk. This is the replication and number QA gate for the business research workflow.

## Inputs

Read what exists:

1. manuscript files in `paper/`, `.tex`, `.md`, or `.qmd`
2. `analysis/output/RESULTS_SUMMARY.md`
3. `analysis/output/TABLE_INDEX.md`
4. `empirical-design/RESEARCH_DESIGN.md`
5. `empirical-design/TABLE_SHELLS.md`
6. Stata, R, or Python logs under `logs/` or `analysis/output/logs/`
7. tables under `tables/` or `analysis/output/tables/`
8. `audit_issue_ledger.md` if present

Read `references/number-audit-checklist.md` when the audit is high-stakes or the paper is near submission.

## Workflow

### Step 1: Run Automated Number Extraction

Use the bundled checker when the manuscript is text-like:

```bash
python3 skills/business-number-audit/scripts/verify_numbers.py \
  --project . \
  --paper paper/main.tex \
  --output BUSINESS_NUMBER_AUDIT.md
```

The script flags numbers in prose that do not appear in logs or tables within tolerance. Treat flagged numbers as review targets, not automatic errors.

### Step 2: Manual Claim Trace

For every empirical claim, statistic, coefficient, standard error, p-value, sample size, and economic magnitude in the manuscript:

- identify the source table, figure, log, or result summary
- confirm the number matches after rounding
- confirm the manuscript describes the same dependent variable, sample, treatment, controls, fixed effects, and clustering
- confirm null, mixed, and fragile findings are not presented as stronger than the outputs support

### Step 3: Specification Audit

Check:

- sample restrictions in prose vs code
- fixed effects in prose vs code
- clustering in prose vs code
- controls in prose vs code
- event windows and treatment timing
- dropped observations and merge attrition
- omitted variables or empty cells in logs
- figure labels, table captions, and appendix references

### Step 4: Update The Ledger

Create or update `audit_issue_ledger.md` with:

```markdown
| Issue ID | First Raised In | Category | Severity | Blocking Until | Status | Notes |
```

Use `Severity = BLOCKING` for any issue that makes a headline claim numerically wrong, unsupported by the cited output, or inconsistent with the implemented specification.

### Step 5: Fix Or Route

- Fix paper text directly when the correct number or label is clear from existing outputs.
- Return to `stata-analysis-bridge` or `data-analysis-bridge` when code or generated outputs must change.
- Return to `evidence-to-claim` when the number is correct but the claim is too strong.

## Output

Write or update `BUSINESS_NUMBER_AUDIT.md`:

```markdown
# Business Number Audit

## Gate
GATE1: PASS | REOPEN_TEXT | REOPEN_ANALYSIS

## Automated Number Check
## Claim Trace Table
| Manuscript Claim | Source Output | Match | Issue | Fix |

## Specification Mismatches
## Issues Added To Ledger
## Direct Fixes Made
## Required Follow-Up
```

## Rules

- Matching numbers are necessary; they do not by themselves validate causal or theoretical claims.
- Keep conceptual claim ceilings in `CLAIMS_FROM_EVIDENCE.md` open unless the underlying issue is resolved.
- Preserve audit issues in the ledger until they are explicitly resolved, reframed, or dropped.
- Do not delete inconvenient null results or failed robustness checks.
