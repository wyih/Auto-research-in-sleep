# CNKI Site Recipe

Use this recipe for an on-demand Chinese journal or thesis PDF. Invoke `browser-session-bridge` for every browser operation; keep this recipe independent of runtime-specific tool names.

## Entry And Search

1. Reuse an existing CNKI tab when available; otherwise open `https://kns.cnki.net/kns8s/search` in the selected persistent Chrome profile.
2. Inspect fresh page state for the search input, authenticated-access state, and an actually blocking challenge.
3. For acquisition, search the exact frozen title first. Fall back to a DOI or distinctive title fragment only when the exact title has no usable result; record the fallback rather than silently broadening it.
4. Capture a bounded structured list from the current result page. Require these fields for each hit when present: `sequence`, `title`, `authors`, `source`, `date`, `database_type`, `citations`, `downloads`, and `online_first`. Keep any action reference opaque; do not emit or persist query-bearing detail URLs or encrypted export identifiers.
5. Match the frozen title plus at least one independent identity field such as author, source, or year. Activate only that hit, then reacquire fresh detail-page state before further action.

Observed selector hints, all of which must be revalidated against current rendered page state:

| Element/data | Selector hint |
|---|---|
| Search input | `input.search-input` |
| Search action | `input.search-btn` |
| Result rows | `.result-table-list tbody tr` |
| Result title/action | `td.name a.fz14` |
| Authors | `td.author a.KnowledgeNetLink` |
| Source | `td.source a` |
| Date | `td.date` |
| Database type | `td.data` |
| Citation count | `td.quote` |
| Download count | `td.download` |
| Online-first marker | `td.name .marktip` |
| Total results | `.pagerTitleCell` |
| Page indicator | `.countPageMark` |

Selectors are current observations, not acceptance evidence. If a selector, label, count, or result structure differs, stop and re-inspect instead of guessing.

## Advanced Search

Use advanced search only when the caller requests discovery or filters beyond exact-title acquisition. Freeze the requested criteria before interacting, and record requested versus visibly applied filters. Never silently drop an unavailable criterion.

Supported dimensions:

| Dimension | Values or behavior | Selector hints |
|---|---|---|
| Search field | subject, title, keywords, title/keywords/abstract, or abstract | current field label associated with `#txt_1_value1` |
| First and second query rows | one or two terms with `AND`, `OR`, or `NOT` row logic | `#txt_1_value1`, `#txt_2_value1` |
| Author | Chinese name, English name, or pinyin | `#au_1_value1` |
| Author affiliation | full name, abbreviation, or former name | `#au_1_value2` |
| Journal/source | journal name, ISSN, or CN number | `#magazine_value1` |
| Fund | named funding source | `#base_value1` |
| Date range | inclusive start and end year | `#startYear`, `#endYear` |
| Source categories | SCI, EI, 北大核心, CSSCI, or CSCD; multiple requested categories use the portal's visible combined state | `#SCI`, `#EI`, `#hx`, `#CSSCI`, `#CSCD` |
| Advanced-search action | submit the visibly reviewed criteria once | `div.search` |

Prefer labels and visibly selected state over positional form indexes. If the current interface cannot prove that a requested field, logic operator, year, or source category was applied, return a filter gap rather than reporting an advanced-search success.

## Pagination And Sorting

Support `next`, `previous`, and a visibly offered page number. Support sorting by relevance, publication date, citation count, download count, or comprehensive rank.

1. Record the current page indicator, active sort label, and a small result signature before the action.
2. Perform one pagination or sort action.
3. Wait for the page indicator, active sort state, or result signature to change; do not infer success from the click alone.
4. Recheck challenge state and extract a new bounded result list. Never reuse result references from the prior page.
5. Pace repeated page operations and stop when a requested page is not visibly offered.

Observed hints that require live revalidation:

| Control/state | Selector hint |
|---|---|
| Page links | `.pages a` |
| Page indicator | `.countPageMark` |
| Sort options | `#orderList li` |
| Relevance | `#FFD` |
| Publication date | `#PT` |
| Citation count | `#CF` |
| Download count | `#DFR` |
| Comprehensive rank | `#ZH` |
| Active sort | `#orderList li.cur` |

## Challenge Detection

CNKI may preload Tencent challenge markup far outside the viewport (one observed container was near `y=-1000000`). Two observed container hints are `#tcaptcha_transform_dy` and `#tCaptchaDyMainWrap`; either or both may be present without an active challenge.

Classify a challenge as active only when all four conditions hold:

1. a candidate challenge container exists in the current document;
2. its rendered box has non-zero width and height and is not hidden;
3. its rendered box intersects the current viewport on both axes; and
4. it actually blocks the intended search, detail, or PDF action.

Element presence, challenge text in a DOM/accessibility snapshot, locator visibility, or a non-negative top coordinate alone is insufficient. A container below the viewport is not active merely because its top coordinate is positive. Record hidden, zero-size, or off-screen challenge components as non-blocking observations; use a current screenshot when obstruction is uncertain.

A genuinely visible slider, image puzzle, or press-and-hold challenge requires human handoff in the same tab. Do not drag, solve, or repeatedly activate it automatically. After handoff, reacquire fresh page and challenge state before resuming.

## Detail Verification

On the article detail page:

- wait for `.brief h1` or equivalent current title state;
- normalize only display suffixes such as `网络首发` or `附视频`;
- confirm the frozen title and at least one of author, source, year, DOI, or CNKI source identity;
- capture only the bounded metadata needed for identity or downstream review.

Structured detail metadata may include `title`, `authors`, `affiliations`, `abstract`, `keywords`, `fund`, `classification`, `source`, `publication_info`, `online_first`, `table_of_contents`, and `citation_network`. Missing optional metadata is not permission to infer it.

Observed hints that require live revalidation:

| Data/control | Selector hint |
|---|---|
| Title | `.brief h1` |
| Authors | `.brief h3.author:first-of-type a` |
| Affiliations | `.brief h3.author:nth-of-type(2) a` |
| Abstract | `.abstract-text` |
| Keywords | `p.keywords a` |
| Fund | `p.funds` |
| Classification | `.clc-code` |
| Source | `.doc-top a` |
| Publication information | `.head-time` |
| Online-first marker | `.brief .icon-shoufa` |
| Article outline | `.catalog-list` or `.catalog-listDiv` |
| Citation network | `ul.module-tab.tpl_lieteratures li` |
| PDF action | `#pdfDown` or `.btn-dlpdf a` |
| CAJ action | `#cajDown` or `.btn-dlcaj a` |
| Logged-out marker | `.downloadlink.icon-notlogged` or a visibly logged-out control |

Selectors and page text support identity matching; they never replace local-artifact verification.

## PDF Download

1. Reject list-page download controls and reject a CAJ-only result for the default PDF acquisition path. CAJ is not a PDF fallback.
2. Confirm a named PDF action on the identity-matched detail page.
3. If authentication or entitlement is absent, keep the same tab and use the shared saved-login or human-handoff contract without reading credential or session material.
4. Immediately before the final PDF action, snapshot the approved landing directory and arm completion handling.
5. Activate the PDF action once, then require a new file from the operation window, no partial-download suffix, and stable non-zero size. CNKI may land a file without a runtime completion event; after timeout use only the shared controlled-directory increment and stable-size fallback.
6. Land under `literature/fulltext/cnki/<year>/` without overwriting an accepted file or following an untrusted link.
7. Verify PDF magic, EOF, minimum size, SHA-256, page readability, and title/content identity. Reject HTML, CAJ, partial data, or a mismatched paper regardless of filename.
8. Record `channel=cnki`, completion mode, artifact path, size, pages, hash, identity evidence, runtime receipt, and blocker in the fulltext manifest.

Never export browser session material, replay a session-bearing download address outside the selected browser, or treat a click, notification, viewer tab, extension, or HTTP status as acquisition success.

## Failure Mapping

| Condition | Blocker |
|---|---|
| Visible blocking slider/puzzle | `captcha_required` |
| Login/download entitlement absent | `not_logged_in` or `subscription_denied` |
| Requested advanced filter not visibly applied | `filter_not_applied` |
| Requested result page not visibly offered | `page_not_available` |
| Only CAJ offered | `caj_only` |
| PDF control missing | `no_pdf_control` |
| Landed HTML, CAJ, or partial file | `artifact_invalid` |
| Paper differs from target | `identity_mismatch` |
