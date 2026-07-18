# SSRN Site Recipe

Use this recipe when an SSRN abstract or delivery URL is blocked for a direct HTTP client but is expected to work in the user's real Chrome session. Invoke `browser-session-bridge`; do not embed runtime-specific calls here.

## Identity

1. Open the SSRN abstract page in the existing Chrome profile.
2. Confirm title, authors, abstract ID, DOI when present, and version/date against the frozen target.
3. Use the page's current download control; do not manufacture a delivery URL from stale query parameters.

SSRN may update an author's displayed name after a working-paper PDF was
posted. Reconcile a live-page alias against the frozen abstract ID, title,
coauthor set, version/date, and the PDF's own author text. Record the alias; do
not reject the right PDF solely because the current abstract page uses a later
surname or a longer given-name form.

## Cloudflare Challenge

SSRN commonly shows a challenge that completes automatically without a click.

1. Keep the tab on the challenge page and wait a bounded interval.
2. Re-inspect the page/URL after each wait; do not repeatedly reload.
3. Continue when the abstract/download page appears.
4. If a rendered ordinary checkbox remains after the bounded wait, classify it
   through the shared challenge contract. With explicit action-time confirmation,
   click that fresh checkbox at most once, then reacquire and re-inspect. There
   is no retry loop.
5. A slider, press-and-hold, image puzzle, hard CAPTCHA, MFA, or credential UI
   requires the shared handoff policy.

A direct-client HTTP 403 plus a successful browser passage is `browser_session`, not `access_denied`. A passive challenge that clears without interaction is not a CAPTCHA handoff.

## Download

Snapshot the controlled landing directory, arm download completion, and activate the SSRN PDF control. If the runtime event is absent, use the shared narrow directory-increment fallback. Verify PDF integrity, title/authors, size, hash, and manifest provenance.
