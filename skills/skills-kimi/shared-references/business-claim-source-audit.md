# Business Claim Source Audit

This audit checks whether prose claims are supported by cited sources, project evidence, or verified institutional facts.

## Claim Types

- `numeric`: number, percentage, coefficient, p-value, sample size
- `factual`: institutional detail, rule, date, data-source fact
- `literature`: what a cited paper finds, argues, measures, or contributes
- `trend`: increase, decrease, growth, decline, market shift
- `causal`: because, leads to, affects, increases, decreases
- `mechanism`: channel, explanation, mediation, theory-consistent process

## Verdicts

- `VERIFIED`: source directly supports the claim
- `MINOR_DISTORTION`: broadly supported but wording is too broad, too precise, or missing a caveat
- `MAJOR_DISTORTION`: source says something materially different
- `UNVERIFIABLE`: cited or implied support is absent from available materials
- `UNVERIFIABLE_ACCESS`: source may exist but cannot be accessed or checked

## Pass Criteria

For submission-facing text:

- zero `MAJOR_DISTORTION`
- zero `UNVERIFIABLE` for headline claims
- zero causal claims above the ceiling in `CLAIMS_FROM_EVIDENCE.md`
- all `MINOR_DISTORTION` rows have concrete wording fixes

## Output Template

```markdown
# Source Claim Audit

## Gate
GATE2: PASS | REOPEN_TEXT | REOPEN_SOURCES | REOPEN_ANALYSIS

## Claim Inventory
| Claim ID | Location | Claim Type | Claim Text | Cited Support |
|---|---|---|---|---|

## Source Support Table
| Claim ID | Source Checked | Verdict | Evidence | Required Fix |
|---|---|---|---|---|

## Unverified Or Distorted Claims

## Citation Repairs

## Required Follow-Up
```
