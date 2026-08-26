# Business Literature Output Template

## Literature Table

Use this table by default:

| Paper | Status | Venue/Source | Field | Question | Data/Setting | Design | Main Finding | Limitation | Delta for Us | fulltext_status |
|---|---|---|---|---|---|---|---|---|---|---|

`fulltext_status` values: `local` | `open` | `institutional_ip` | `browser_session` | `bot_challenge_passed` | `abstract_only` | `missing` | `gap` | `needs_verification`. When method detail requires full text, point next work to `method-harvest` rather than expanding this table into PDF harvest.

## Fulltext Evidence Matrix

When `fulltext_synthesis` mode is active, use the schema and acceptance rules in `fulltext-synthesis.md`. Keep the discovery table and evidence matrix separate: the discovery table can contain abstract-only candidates; the evidence matrix cannot.

For a user-authorized fixed corpus, include every supplied core paper. Do not add papers to reach the map-mode 8–15 target. Mark discovery-only or venue-positioning outputs `HANDOFF_INCOMPLETE` when the authorized corpus cannot support them.

The matrix must link per-paper audit subsections for:

- construct depth
- observation/respondent/estimand/unique-entity/cluster units
- factor/index reproducibility and questionnaire/scale provenance
- numeric consistency
- mediation evidence

Use `unknown`, `needs_verification`, or `not_applicable: <reason>` in every unsupported required cell; do not leave it blank.

## Closest-Paper Delta

| Closest Paper | Same As Us | Different From Us | Remaining Contribution | Risk |
|---|---|---|---|---|

## Synthesis Structure

1. What the literature already agrees on
2. Where findings are mixed or under-identified
3. Which constructs or settings are crowded
4. Which data or design path could still create a contribution
5. What claim ceiling the literature implies

For a fulltext synthesis, additionally explain:

6. how construct definitions and variable calculations differ
7. whether apparent result conflicts come from construct depth, measurement/index/scale provenance, sample/unit/dependence, design, timing, source inconsistency, or a genuine substantive disagreement
8. which source-grounded variable definitions and data joins can transfer to the current project
9. which numeric inconsistencies or incomplete mediation fields limit design readiness or the claim ceiling

## Practical Takeaway

End with:

- best current positioning
- most dangerous close paper
- strongest feasible contribution angle
- next search or design action
