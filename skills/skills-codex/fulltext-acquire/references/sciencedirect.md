# ScienceDirect Site Recipe

Use this recipe for an entitled or open ScienceDirect article PDF. Invoke `browser-session-bridge`; do not embed Codex or MCP calls here.

## Base URL

Prefer the ScienceDirect origin already open in the user's Chrome because it may be an institutional proxy. If none is open, use `https://www.sciencedirect.com` unless the project records another authorized library entry point.

## Search And Identity

1. Navigate to `{base}/search?qs={url_encoded_query}&show=25`.
2. Inspect for search results, a login redirect, an access page, or a human challenge.
3. Capture only the needed hit fields: title, authors, journal/date, DOI, PII, and OA indicator.
4. Navigate to the identity-matched article page.
5. Confirm title and DOI/PII before download.

Current selector hints:

| Element | Selector hint |
|---|---|
| Result | `li.ResultItem` |
| Result title | `a.result-list-title-link` |
| Authors | `.Authors .author` |
| Article title | `.title-text` |
| DOI | `a[href*="doi.org"]` |
| PDF URL/control | `a[href*="pdfft"]` |
| Access prompt | `.access-options`, `.get-access`, or a visible Get Access control |

When identity is ambiguous, current candidate fields include author
affiliations, abstract, highlights, keywords, article type, publication date,
volume/issue, and section headings. Use them only to reconcile the work and
required artifact roles. Selector hints are not proof and must be revalidated
against fresh page state.

## Challenge And Access

- A login or institutional redirect requires `human.handoff` in the same Chrome tab.
- First wait and re-inspect a bounded number of times because a passive challenge may clear automatically.
- A visible Cloudflare/Turnstile/press-and-hold/hard CAPTCHA that remains and requires a click or gesture requires action-time confirmation/human handoff; do not attempt anti-bot evasion or webdriver masking.
- Hidden/preloaded verification markup is not a challenge unless its rendered box intersects the viewport and blocks the intended action.
- A paywall without entitlement is `subscription_denied`, not a browser failure.

## Download

1. Use the current session-bound PDF control from the article page; do not
   construct the `pdfft` hash, because its hash/signature is article- and
   session-bound.
2. Activate that control once. It may start a download or open an inline PDF
   whose `document.contentType` is `application/pdf`.
3. For a direct download, snapshot the approved landing directory immediately
   before the click and await the local file. For an inline PDF, reacquire the
   PDF tab without exposing its signed query, then use the runtime's bounded
   fixed loaded-PDF download action. Do not depend on Chrome viewer-toolbar
   accessibility or arbitrary page JavaScript.
4. Land under `literature/fulltext/publisher/` or `literature/fulltext/session/`.
5. Verify PDF integrity and identity, then record the runtime receipt and manifest row.

## Failure Mapping

Use `login_required`, `captcha_required`, `subscription_denied`, `no_pdf_control`, `download_failed`, `artifact_invalid`, or `identity_mismatch`.

An Elsevier API result may accelerate OA acquisition, but an API 403 or HTML page is not acceptance and does not replace the signed-in browser path when the user has browser entitlement.
