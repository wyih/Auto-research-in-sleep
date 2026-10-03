# Business Source Policy

## Default Priority

1. User-owned sources: Zotero, Obsidian, local PDFs, local notes
2. Working papers: SSRN, NBER, RePEc
3. Metadata and discovery: Google Scholar, Crossref, OpenAlex, Semantic Scholar
4. Publisher and journal pages
5. Broader web for tracing already-identified papers

## Source Intent

- `SSRN`: strongest default for accounting, finance, management, and business working papers.
- `NBER`: strong for finance, economics, macro-accounting, corporate finance, labor, and policy papers.
- `RePEc`: useful for economics and finance working paper trails.
- `Google Scholar`: useful for broad discovery and title variants; verify through publisher or working-paper source.
- `Crossref` and `OpenAlex`: metadata cross-checks, DOI, venue, and version reconciliation.
- Publisher pages: formal publication status and final journal metadata.

## Search Layering

Search by combinations:

- construct + outcome
- setting + shock
- data source + method
- author + title phrase
- treatment + identification design
- journal abbreviation + topic

Prefer precise queries over broad field labels.

For passage-specific matching, follow [reference-match.md](reference-match.md). Select query families from the claims and retain null/contrary findings through nondirectional queries.

## Journal Requirements

Treat explicit eligibility conditions as hard filters and preferred outlets as quality preferences. Preserve the user's scope, including permission to cite working papers; there is no automatic SSCI or journal-only restriction.

Apply joint conditions as an intersection and alternative conditions as a union, preserving grouped requirements such as `(SSCI and JCR Q1/Q2) or AJG 3+`. Ask only when ambiguous wording would change eligibility. An article passing an allowed alternative is eligible even when another branch fails.

Record the source, edition/year, and relevant subject category for an SSCI, JCR, AJG/ABS, FT50, UTD24, whitelist, or blacklist check. Use authorized lists or traceable official records and label a user's list as user-provided. Unknown ranking status remains unverified; discovery-index membership does not establish journal eligibility. Keep papers with unverified required eligibility outside the confirmed eligible list.

Among similarly supported eligible matches, prefer the user's quality targets. A useful match outside a preference needs a concrete evidence advantage; papers failing hard filters may remain discovery leads. Journal reputation cannot compensate for a failed claim match.

## Status Labels

Use:

- `published`
- `forthcoming`
- `working_paper`
- `preprint`
- `dissertation_or_chapter`
- `needs_verification`

## Version Rules

- Prefer final journal metadata for citation.
- Keep working-paper metadata when it includes an accessible PDF, appendix, or newer version.
- Track title changes and merged working-paper versions explicitly.
- Treat missing full text as a search gap **and** as a `fulltext_status` value (see below).
- For a promising working paper, check its original record, exact title/authors, title variants, and author/publisher pages for a journal version. Confirm the version relationship using explicit links or corroborating study details, then verify the formal record. A missing version link is not evidence of non-publication.
- Tie every quoted passage, page, and finding to the version actually read. Before citing journal metadata for evidence read in a working paper, verify that the journal text retains that evidence. If access blocks the check, its support remains `UNVERIFIABLE_ACCESS`; cite the verified working-paper version only when the user's scope permits it.
- Record an unresolved journal-version search with the routes checked and date. Preserve online-first publication, accepted/forthcoming status, and working-paper status as documented. Deduplicate repeated publication records by DOI or strong title-author evidence while retaining distinct version identities.

## Fulltext Status (Map Layer)

`business-lit-review` records whether full text is available; it does **not** run the acquisition ladder.

Use `fulltext_status` on literature rows:

- `local`
- `open`
- `institutional_ip` (includes CNKI 知网 journal/thesis PDF when IP works)
- `browser_session`
- `bot_challenge_passed`
- `abstract_only`
- `missing`
- `gap`
- `needs_verification`

Optional: `fulltext_channel` such as `zotero`, `ssrn`, `nber`, `cnki`, `sciencedirect`, `publisher`.

### Boundary

| Task | Skill |
|---|---|
| Discover papers, venue, gaps | `business-lit-review` (this policy) |
| Acquire and verify PDF | `fulltext-acquire` |
| Extract grounded method card from verified PDF | `method-harvest` |
| Chinese microdata (CSMAR/CNRDS) | `cn-data-bridge` |
| CNKI paper PDF | `fulltext-acquire` → `method-harvest` (fulltext, not microdata) |

Fulltext priority is owned by `fulltext-acquire`:

```text
local → open PDF → institutional IP (incl. CNKI) → browser session → bot challenge → gap
```
