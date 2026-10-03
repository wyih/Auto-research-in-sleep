# Business Literature Output Template

## Literature Table

Use this table in `map` mode:

| Paper | Status | Venue/Source | Field | Question | Data/Setting | Design | Main Finding | Limitation | Delta for Us | fulltext_status |
|---|---|---|---|---|---|---|---|---|---|---|

`fulltext_status` values: `local` | `open` | `institutional_ip` | `browser_session` | `bot_challenge_passed` | `abstract_only` | `missing` | `gap` | `needs_verification`. When method detail requires full text, point next work to `method-harvest` rather than expanding this table into PDF harvest.

## Reference-Match Output

For `reference_match`, preserve the target passage and its manuscript location, then provide a compact claim map:

| Claim ID | Assertion Needing Support | Claim Type | Intended Citation Role |
|---|---|---|---|

Use one row per claim-paper pair in the match table:

| Claim ID | Paper / Cited Version | Citation Role | Verdict | Evidence / Source Location | Usable Citation Wording |
|---|---|---|---|---|---|

Use the roles and verdicts in [shared claim matching](../../shared-references/business-claim-source-audit.md#literature-claim-matching). Identify the version read, source depth, DOI/source link, and any material journal-filter evidence beside the row when they would make the table too wide. A short excerpt or precise paraphrase must explain the match; title similarity alone does not.

Keep verified usable references distinct from access-pending or topic-adjacent candidates. Include rejected examples only when they explain a material choice. State unsupported claims or necessary wording changes explicitly, with a concise account of the searches that exhausted accessible useful routes when relevant.

For English manuscripts or requested citation wording, include sentences that preserve the evidence's population, setting, direction, and inference strength. Contribution wording must follow the user's actual study and the verified prior finding. Supply APA/BibTeX only when requested or needed by the manuscript, using verified metadata and the cited version.

Return this result in chat for a standalone request; update an existing project artifact or save a separate file only when requested or needed by its consumer. The literature-map count, closest-paper table, and fulltext-synthesis matrix do not apply to this mode.

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
