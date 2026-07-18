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
