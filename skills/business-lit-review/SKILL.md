---
name: business-lit-review
description: Discover and synthesize literature for business, accounting, finance, management, economics, and empirical social-science papers. Use when finding related work, building a literature map, checking journal positioning, comparing working papers, deciding where an idea fits, or turning verified fulltext method cards into a source-grounded cross-paper evidence matrix and narrative review with construct depth, measurement provenance, unit/dependence, numeric-audit, mediation, and claim-ceiling checks.
---

# Business Lit Review

Research topic: $ARGUMENTS

## Purpose

Use this skill for business-school research where the unit of evaluation is a journal-style empirical or theory paper rather than an ML benchmark paper.

This skill is knowledge-base-first and journal-aware. It supports a discovery map and a later fulltext synthesis. Search the user's own library first, then working-paper sources, then journal and publisher sources, then broad web.

## References

Load only the reference needed for the current task:

- `references/source-policy.md` for source order, search rules, and `fulltext_status` labels.
- `references/venue-tiering.md` for accounting, finance, management, and economics venue tiers.
- `references/domain-taxonomy.md` for topic grouping and trigger boundaries.
- `references/output-template.md` for the default literature table and synthesis structure.
- `references/fulltext-synthesis.md` when verified PDFs or method cards are available and the task needs a literature evidence matrix or review prose.
- `references/sciencedirect-discovery.md` when discovery is intentionally scoped to ScienceDirect search, article metadata, journal issues, or citation export.
- `../shared-references/business-handoff-schemas.md` for the required `BUSINESS_LIT_REVIEW.md` fields when this review feeds a pipeline.
- `../method-harvest/SKILL.md` and its references when fulltext acquisition or method cards are needed (do not expand this skill into PDF harvesting).

## Select Mode

Use `map` by default when the corpus is still being discovered. Use `fulltext_synthesis` when the request asks what papers actually do, how constructs are measured, how variables are calculated, why findings differ, or when verified method cards already exist.

- `map`: discover, deduplicate, position, and assign `fulltext_status`.
- `fulltext_synthesis`: consume verified `METHOD_CARD` artifacts, spot-check material claims against local PDFs, and produce a cross-paper evidence matrix plus grounded synthesis.

Do not let abstract-only rows supply method, variable-construction, or result-detail claims in `fulltext_synthesis` mode.

## Source Selection

Parse `$ARGUMENTS` for `— sources:`.

If omitted, search in this order:

1. Zotero, Obsidian, and local `papers/` or `literature/`
2. SSRN and NBER
3. RePEc, Google Scholar, Crossref, OpenAlex, Semantic Scholar
4. Publisher and journal pages
5. Broader web only for tracing papers already identified

Valid source values:

- `zotero`
- `obsidian`
- `local`
- `ssrn`
- `nber`
- `repec`
- `scholar`
- `openalex`
- `crossref`
- `publisher`
- `web`
- `all`

Interpret `all` as the full default source set.

## Workflow

### Step 0: Load Local Knowledge

Search local sources before web search.

Extract:

- title, authors, year, venue or working-paper source
- user annotations, notes, tags, and collections
- key question, setting, data, method, result, and limitation
- why the paper matters for this project

Treat user-owned notes and annotations as high-priority context.

### Step 1: Search Working Papers

Search SSRN and NBER early. Many accounting and finance ideas circulate as working papers for years before journal publication.

For each hit, capture:

- current version date
- earlier title variants when visible
- author institution
- abstract-level method and data
- journal publication status if known

Label source status as `published`, `forthcoming`, `working_paper`, or `preprint`.

### Step 2: Search Formal Literature

Use venue tiering from `references/venue-tiering.md`.

Prefer formal versions when a working paper and a journal article refer to the same work. Keep the working-paper link when it has newer appendices, data details, or an accessible PDF.

### Step 3: Build the Landscape

Group papers by research design and mechanism rather than search order.

Common grouping axes:

- theory channel
- institutional setting
- data source
- identification strategy
- construct or measure
- outcome family
- journal conversation

### Step 4: Run Fulltext Synthesis When Requested

Read `references/fulltext-synthesis.md`. Require a current identity-matched PDF hash and `METHOD_CARD` for each core paper. Route missing or incomplete cards through `method-harvest`; do not silently fill method fields from abstracts.

Build `LITERATURE_EVIDENCE_MATRIX.md` before writing narrative synthesis. Preserve each paper's:

- question, theory/mechanism, and prediction
- construct hierarchy/depth, not just the paper's construct label
- observation, respondent, estimand, unique-entity, and cluster units; period, geography, filters, and final sample
- construct-to-variable mapping and exact calculation or coding rule, including factor/index and questionnaire provenance
- data source, grain, identifiers, and merge hints
- design, identifying variation, assumptions, estimator, fixed effects, and inference
- main and null/mixed results with table/PDF-page locations and numeric-consistency status
- complete mediation evidence fields when the paper makes a mediation claim
- robustness, boundary conditions, limitations, and claim ceiling

### Step 5: Synthesize Across Papers

Explain agreement, disagreement, and why results may differ. Compare construct depth, measurement sources and reproducibility, questionnaire versions/item direction, observation/respondent/unique-entity/cluster units, samples, designs, and outcome timing before treating coefficients as comparable. Separate evidence strength from publication status or citation count.

Every material statement in the fulltext synthesis must cite a paper ID plus a page, section, table, or appendix pointer from its card. Use `PDF p.<viewer-page>` and label any different printed/article page explicitly. Use `unknown` or `needs_verification` rather than inferring an unstated formula, index component, reverse-coded item, unique-entity count, cluster, mediation path, or causal design.

### Step 6: Diagnose the Gap

For each potential gap, state:

- what the closest paper already does
- what the user's project changes
- whether the gap is theoretical, empirical, data-driven, setting-driven, identification-driven, or measurement-driven
- what evidence would make the gap credible to a referee

### Step 7: Record Fulltext Status (Map Only)

In `map` mode, stay **discovery-first**. Do not download paywalled PDFs or extract full method cards here.

For each paper in the literature table, set `fulltext_status` when known:

| Label | Meaning |
|---|---|
| `local` | PDF/notes already in user library |
| `open` | open PDF URL known or obtained |
| `institutional_ip` | obtainable via institutional/IP access (includes CNKI 知网 fulltext) |
| `browser_session` | needs existing browser login |
| `bot_challenge_passed` | bot Verify cleared and fulltext held (usually after `method-harvest`) |
| `abstract_only` | only abstract/metadata used |
| `missing` | not yet checked |
| `gap` | ladder exhausted or human PDF still required |
| `needs_verification` | status uncertain |

Optional companion field: `fulltext_channel` (`zotero`, `ssrn`, `nber`, `cnki`, `sciencedirect`, `publisher`, …).

When the user needs sample construction, identification, variable definitions, or data-source clues from full text, route a missing PDF to `fulltext-acquire`, then hand the verified local PDF to `method-harvest`. CNKI paper PDF is literature fulltext, not CSMAR/CNRDS microdata (`cn-data-bridge`).

## Output

Use the table and synthesis shape in `references/output-template.md`.

In `map` mode, include:

1. top 8-15 closest papers (with `fulltext_status` when known)
2. closest-paper delta table
3. venue-positioning note
4. unresolved search gaps
5. recommended next search or design action
6. papers that should run through `method-harvest` next (if method detail is blocked by missing fulltext)

In `fulltext_synthesis` mode, write:

1. `LITERATURE_EVIDENCE_MATRIX.md`
2. a source-grounded synthesis in `BUSINESS_LIT_REVIEW.md`
3. a list of non-comparable measures/results and unresolved fulltext fields

A user-authorized fixed corpus overrides the 8–15 discovery target. Include every supplied core paper and do not add papers solely to meet a count. When discovery, venue positioning, or a closest-paper target was not authorized or supplied, mark that output `HANDOFF_INCOMPLETE` with the missing input instead of inventing it.

Update `BUSINESS_RUN_PASSPORT.md` through `business-run-passport` when writing is allowed and this review becomes a project input.

## Rules

- For local tasks, complete only the requested stage and mark downstream gaps as next-stage inputs.
- Prefer journal and working-paper primary sources over tertiary summaries.
- Preserve working-paper status instead of smoothing it into publication status.
- Separate accounting, finance, management, and economics conversations when they use different constructs or referee standards.
- Flag duplicate title variants and author-version drift.
- Mark papers as `needs_verification` when metadata or claims are uncertain.
- Record `fulltext_status`; do not collapse fulltext harvest into this skill—route deep method extraction to `method-harvest`.
- Do not summarize papers one by one and call it synthesis. Organize prose around constructs, mechanisms, designs, findings, and contradictions.
- Preserve null and mixed findings. Do not vote-count significance across non-comparable measures or samples.
- Treat the method card's numeric audit as a hard gate. Preserve failed estimate/SE, sign, p/star/CI, prose/table, sample-N, or indirect-effect checks and lower design readiness or the narrative claim ceiling.
- Never fill a required synthesis cell from domain convention. Use explicit `unknown`, `needs_verification`, or `not_applicable: <reason>`; blank required cells fail acceptance.
- Keep a paper's descriptive, associational, mechanism-consistent, or plausibly causal ceiling visible in every cross-paper conclusion.
