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

## Literature Claim Matching

Use these rules for both passage-specific reference matching and auditing literature citations.

Split a compound assertion into claims whose support can be checked separately. For "X affects Y through Z", distinguish the X-Y relationship from the claimed Z mechanism. Preserve direction, constructs, population, timing, and inference strength when defining each claim.

Record the citation role separately from the verdict for each claim-paper pair:

| Citation Role | Manuscript Use |
|---|---|
| `direct_support` | Evidence supports the exact relationship, definition, fact, or method assertion at this location. |
| `theory_support` | Evidence provides the theoretical channel or conceptual foundation for the particular theory claim. |
| `literature_dialogue` | Evidence supports a stated extension, comparison, contrast, or summary of what prior work did. |
| `topic_adjacent` | The paper shares a topic, method, or dataset but supplies no support for the target assertion. |

Assign the verdict to the exact assertion the proposed citation would carry. A verified theory claim, contrast, or prior-study summary does not verify a separate empirical relationship. For a `topic_adjacent` pairing, explain the mismatch; if it is already cited as support, apply the existing distortion/unverifiable verdicts to that attribution. Access-pending evidence uses `UNVERIFIABLE_ACCESS`, not a separate citation role. Source depth (`metadata_only`, `abstract_only`, or `fulltext`) is another distinct field; metadata alone leaves support unverified.

Check the shortest sufficient source passage and its surrounding context. Establish whether it reports the authors' own finding, a hypothesis, a theoretical prediction, or a summary of another study. A cited prior finding leads to its original source when that finding is the required evidence.

Match the assertion's constructs, direction, population, timing, and strength to the evidence. Association supports associational wording; mechanism-consistent evidence and a tested indirect effect have different claim ceilings. Separate X-Z and Z-Y results do not alone establish mediation. Preserve null, mixed, and contrary findings, assigning an appropriate dialogue claim when useful.

Trace each material evidence note to the exact version read, with a short excerpt or precise paraphrase and a page, section, table, or source URL. Official abstracts can support what they explicitly state. Method, measurement, sample, detailed result, and mechanism-test assertions need the relevant fulltext evidence. Use `PDF p.<viewer-page>` for 1-based viewer pages and label different printed/article pagination.

Before accepting a citation, determine whether it can appear after the proposed sentence with its stated scope. If only a narrower assertion is supported, record `MINOR_DISTORTION` when applicable and supply a concrete wording fix; keep the original assertion unresolved until that fix or additional evidence supports it. Journal prestige, citation counts, keyword overlap, and appearing in multiple indexes do not supply semantic support.

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
| Claim ID | Source Checked / Version | Citation Role | Verdict | Evidence / Location | Required Fix |
|---|---|---|---|---|---|

## Unverified Or Distorted Claims

## Citation Repairs

## Required Follow-Up
```

Use citation roles for literature rows; other source/project-evidence rows may use `not_applicable`.
