# Wiley Online Library Site Recipe

Use this recipe for an authorized or open Wiley article PDF. Invoke `browser-session-bridge`; keep runtime-specific calls out of this file.

## Entry And Identity

1. Prefer the stable DOI article URL: `https://onlinelibrary.wiley.com/doi/<DOI>`.
2. Inspect the page for title, authors, DOI, publication date/status, access label, and a PDF control.
3. Treat an institutional logo or Open Access label as access context, not download proof.
4. Confirm the frozen title and DOI before opening the PDF.

Observed route, which must be re-inspected on each run:

| Stage | Current shape |
|---|---|
| Article | `/doi/<DOI>` |
| PDF wrapper | article-page `Download PDF` link, currently `/doi/pdf/<DOI>`; `/doi/epdf/<DOI>` is another observed wrapper shape |
| Embedded delivery | exactly one same-origin iframe, currently `/doi/pdfdirect/<DOI>` |

Do not manufacture the wrapper, iframe, or delivery URL. Activate the current
page control because Wiley may change delivery paths or attach session state.
The runtime may use a fixed, caller-nonprogrammable wrapper action, but it must
not expose the embedded URL or depend on Chrome's PDF-viewer toolbar.

## Challenge And Login

- Wait and re-inspect a bounded number of times when the page initially exposes only a document shell.
- A first DOI-page load can transiently show an ordinary Wiley login shell even
  when the persistent profile has article access. Reload the same stable DOI
  entry exactly once and reacquire the page. If the article identity and PDF
  control return, continue; if the login shell persists, use `login_required`.
  Never create a refresh loop.
- Treat a challenge as active only when it intersects the viewport and blocks the intended article/PDF action.
- A login button alone does not mean the article is unavailable; inspect the article's access state and PDF control.
- A persistent login, MFA, or hard CAPTCHA requires the shared handoff policy. A paywall without entitlement is `subscription_denied`.

## Download

1. Snapshot the approved landing directory immediately before activating the
   article-page `Download PDF` control once.
2. If that control directly downloads a file, await only the new stable landing.
   If it opens a Wiley HTML PDF wrapper, reacquire that wrapper and use the
   runtime's bounded fixed loaded-PDF/wrapper action. That action may follow
   exactly one same-origin embedded delivery internally; do not click a hidden
   iframe, construct `/doi/pdfdirect/`, or hunt for a reader-toolbar control.
3. Prefer a native download event. If none is emitted, accept only a newly
   landed stable file in the controlled directory and record
   `fallback_directory_increment`.
4. Land the accepted copy under `literature/fulltext/wiley/` or the project's publisher directory.
5. Verify `%PDF`, EOF, minimum size, page count, title/DOI text, SHA-256, and provenance. A publisher reserialization may change bytes or hash while preserving identity, so compare an old hash only when the frozen acceptance contract explicitly requires byte equality.

## Failure Mapping

Use `login_required`, `captcha_required`, `subscription_denied`, `no_pdf_control`, `reader_failed`, `download_failed`, `artifact_invalid`, or `identity_mismatch`.

An HTML article page, loaded reader, institutional logo, or Open Access badge is not a landed-file pass.
