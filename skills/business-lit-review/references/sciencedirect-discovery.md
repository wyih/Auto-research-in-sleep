# ScienceDirect Discovery Recipe

Use this reference only when a literature-map task is deliberately scoped to
ScienceDirect search, article metadata, a journal issue, or citation export.
Fulltext acquisition remains in `fulltext-acquire`; method and variable claims
still require a verified PDF plus `method-harvest`.

## Search Contract

Start with the stable public search route:

```text
/search?qs=<encoded query>&show=25
```

Capture a bounded hit list with title, authors, source title, publication date,
article type, DOI when visible, PII, and the stable article route. Keep result
rank separate from identity. Do not return session-bound PDF, reader, export, or
delivery URLs.

Candidate advanced-search dimensions observed in the publisher interface are:

| Dimension | Candidate parameter |
|---|---|
| general query | `qs` |
| title/abstract/keywords | `tak` |
| title | `title` |
| authors | `authors` |
| publication or journal | `pub` |
| date or date range | `date` |
| volume | `volume` |
| issue | `issue` |
| first page | `page` |
| DOI/PII or other document ID | `docId` |
| affiliation | `affiliations` |
| references | `references` |

Treat this as an allowlisted field map, not a promise that every parameter is
accepted forever. Encode values, omit empty fields, and revalidate the rendered
filters and result identity after navigation. Never put credentials, cookies,
signed parameters, or export tokens in a constructed URL.

## Pagination And Sort

- Allowed page sizes are `25`, `50`, and `100`.
- For 1-based page `n`, calculate `offset=(n-1)*show`.
- Preserve the frozen query and filters when changing `offset` or `show`.
- Use `sortBy=date` only when the user requests newest-first. Omit `sortBy` for
  relevance rather than inventing another sort value.
- Verify the displayed page/range after every change; a computed URL alone is
  not navigation evidence.

## Article Metadata

Use the stable `/science/article/pii/<PII>` route after selecting an
identity-matched result. Candidate fields for bounded extraction are:

- title and complete displayed author list
- affiliations
- journal, publication date, volume, issue, and article type
- DOI and PII
- abstract, highlights, and keywords
- section headings
- presence and access state of the PDF control

Abstract, highlights, headings, and a reference count remain discovery-level
evidence. They must not populate sample construction, variable formulas,
identification, robustness, or result cells in a fulltext synthesis.

## Journal Routes

When the task is journal browsing, resolve the official journal slug from an
observed publisher link; do not derive it by lowercasing a journal title.
Candidate stable routes are:

```text
/journal/<official-slug>
/journal/<official-slug>/issues
/journal/<official-slug>/vol/<volume>/issue/<issue>
/journal/<official-slug>/about/editorial-board
/journal/<official-slug>/about/insights
```

Treat impact-factor or CiteScore labels as current page metadata, not venue
tiering or permanent facts. Reconcile them by label; never select the first
unlabelled metric card heuristically.

## Citation Export

RIS, BibTeX, or text export is optional and outside the P1–P5 acceptance chain.
Use the visible article/search export UI and verify the landed file. Do not
surface or replay an export token, do not send cookies or signed PDF URLs to a
local script, and do not mutate Zotero unless the user separately authorizes
that external write.

## Boundary

- Discovery metadata may establish title/version/venue identity.
- A visible viewer, abstract, HTML article, citation file, or PDF click is not
  verified fulltext.
- Route a needed paper to `fulltext-acquire`, then route the verified local PDF
  to `method-harvest`.
