# Grok P3 ScienceDirect protected-session acceptance

Use the installed project skills `$fulltext-acquire` and `$browser-session-bridge`. Read their ScienceDirect recipe, shared browser-session contract, and Grok adapter before acting. This must be a real Grok-runtime download through the user's Chrome session.

## Hard runtime boundary

- All browser operations must be one-shot calls through:

  ```text
  $PWD/.agents/skills/browser-session-bridge/scripts/chrome_mcp_client.mjs
  ```

  That helper must connect to the configured `chrome-mcp`; it is the only allowed browser path.
- Do not use Grok `search_tool` / `use_tool`, the separate `browser` MCP, web search/fetch, curl, requests, Playwright, AppleScript, direct CDP, direct MCP HTTP, or another browser profile.
- Never inspect or persist cookies, storage, credentials, headers, account/session identifiers, raw delivery URLs, URL queries, or signed URLs.
- Do not persist raw helper output in the receipt.

Use these local command paths without modifying configuration:

```bash
BRIDGE_SKILL_DIR="$PWD/.agents/skills/browser-session-bridge"
MCP_CLIENT="$BRIDGE_SKILL_DIR/scripts/chrome_mcp_client.mjs"
DOWNLOAD_VERIFIER="$BRIDGE_SKILL_DIR/scripts/verify_download.py"
```

Run `node "$MCP_CLIENT" self-test` first. Keep each subsequent helper process to one short schema/tab/tool operation. Any nonzero helper exit is a failed operation, not acceptance.

Every shorthand below is a helper subprocess: `schema TOOL` means `node "$MCP_CLIENT" schema TOOL`; `tabs ...` means `node "$MCP_CLIENT" tabs ...`; and a browser call means `node "$MCP_CLIENT" call TOOL --args-json '<object matching the live schema>'`. Do not invoke a Chrome MCP tool directly.

## Foreground-only legacy-safe rules

The installed extension may be the legacy executor. Its compatibility path cannot safely focus a background tab: it only verifies that the requested tab is already active in the focused Chrome window. Before the run, the operator must therefore leave exactly one ScienceDirect tab open and in the foreground. Never open a replacement tab, call `chrome_switch_tab` to imitate a switch, navigate a background tab, or act on an arbitrary active tab.

1. Before **every** navigation, read, scroll check, challenge click, PDF click, viewer action, or post-click state check, run `tabs --url-contains "sciencedirect.com"` (or the already observed query-free viewer domain). Require exactly one match with `active: true`. Zero, multiple, or inactive matches require foreground handoff; never select a tab heuristically.
2. Treat the returned `tabId` as a one-operation lease. Use it only in the immediately following helper call, then discard it and run `tabs` again. Never write, cache, hard-code, or reuse a tab ID across calls or state transitions.
3. Inspect each tool's live schema before first use and pass only helper-allowlisted fields. Read only with compact `chrome_read_page` calls using a narrow CSS `selector`, `textQuery`, and/or `types` filter. `chrome_get_web_content` is not a public helper operation and must never be called directly.
4. Never call `chrome_javascript`, `chrome_inject_script`, XPath selectors, element `ref`/`refId`, stale snapshot identifiers, or coordinate clicks. Never use `chrome_computer` to click a challenge, article control, or viewer control.
5. Every action starts with one native `chrome_click_element` call using a CSS selector freshly returned or confirmed by the immediately preceding compact read, with `selectorType: "css"`. After any nonzero/uncertain mutating result, reacquire and reread state before deciding what happened; never blindly retry. If the expected transition provably did not occur, one bounded `exact-selector-click` fallback is permitted with that fresh selector, exact text, one narrow scope, and a newly reacquired tab ID; immediately verify post-state and never treat `effect_state:attempted` as acceptance evidence. This fallback is not permitted for a Cloudflare checkbox or other challenge.
6. `exact-text` is permitted only to inspect and scroll one uniquely scoped rendered label. It never clicks and is not acceptance evidence. After `ready`, reacquire, compact-read, obtain a current CSS selector, and issue one native click. Do not use it as a selector generator or as article/download proof.
7. After every navigation, challenge transition, PDF click, or new-tab event, reacquire the intended domain and require the resulting tab to be the unique foreground match. If the viewer opens in the background, stop for foreground handoff instead of switching it automatically.

## Frozen target identity

- Title: `The effect of corporate culture on firm performance: Evidence from China`
- Authors: Hailin Zhao; Haimeng Teng; Qiang Wu
- DOI: `10.1016/j.cjar.2018.01.003`
- PII: `S1755309118300030`
- Stable article entry: `https://www.sciencedirect.com/science/article/pii/S1755309118300030`
- Current independently verified Codex reference: 19 pages, 526357 bytes, SHA-256 `459e22da3a37ad6bd4823271ddfc4d6c8d027e054a43057b89c6cd0090d9770b`

These facts identify the target. Do not read or copy the Codex PDF. A matching hash counts only when this Grok run produces a new post-click landing file.

## Required browser flow

1. Record the start time and a narrow baseline inventory of `${HOME}/Downloads` with names, sizes, and modification times only.
2. Reacquire the unique foreground ScienceDirect tab, inspect `schema chrome_navigate`, navigate that same leased tab to the stable PII entry with `newWindow: false`, then reacquire and perform a compact `chrome_read_page` identity read.
3. First allow a bounded passive wait and reinspection if Cloudflare is still resolving.
4. If an ordinary visible Cloudflare checkbox still blocks the article, stop with `captcha_required` unless the current Grok launch includes a separate action-time rule recording that the user confirmed this already-observed challenge. Earlier general authorization is not that launch-time rule. With that explicit rule only, reacquire and compact-read the foreground tab, require a current CSS selector for the visible checkbox, and issue one native `chrome_click_element` click with `selectorType: "css"`; then wait, reacquire, and reread. If no fresh CSS selector is exposed, stop rather than using a screenshot, coordinates, refs, XPath, or JavaScript.
5. Do not automate sliders, press-and-hold, image puzzles, hard CAPTCHAs, MFA, or credential entry. Stop with `captcha_required` or `login_required` if one blocks the action. Hidden/offscreen challenge markup is not blocking evidence.
6. Confirm the exact article title, all three authors, DOI, and PII on the article page. Confirm that a PDF/View PDF control is actually available; an institutional logo or article HTML is not download proof.
7. Immediately before the final article or viewer download click, refresh the narrow `${HOME}/Downloads` inventory and record the click time. Do **not** arm `chrome_handle_download`: the legacy implementation is a post-click `~/Downloads` increment detector, not an event waiter.
8. Reacquire and compact-read the foreground article tab, then click its current visible PDF control exactly once through `chrome_click_element` with a freshly confirmed CSS selector. A shape such as `a[href*="pdfft"]` is only a hint and must be confirmed in current state. Never construct, print, or persist the `pdfft` delivery URL or hash.
9. If an inline viewer or new tab opens, reacquire its already observed query-free domain and require it to be the unique foreground match. Compact-read target identity. If a separate viewer download control is required, refresh the narrow `${HOME}/Downloads` baseline and click time again, then click it only with a fresh CSS selector through one native `chrome_click_element` call. If the control exists only as browser UI/canvas or the helper refuses a signed/query-bearing viewer under legacy compatibility, stop with `viewer_failed`; do not use screenshots, coordinates, refs, XPath, JavaScript, or background switching.
10. After the final click, reacquire and inspect post-state before any retry. Then inspect `schema chrome_handle_download`. If it accepts `filenameContains`, call it **after** the click with a narrow query-free target-derived filename token, `directory: "${HOME}/Downloads"`, bounded `lookbackMs`, and `waitForComplete: true`. Under legacy compatibility, record success only as `fallback_directory_increment`, never a native event. If unavailable, unsuitable, or timed out, independently diff only `${HOME}/Downloads` against the most recent pre-click baseline. Require a post-click plausible PDF, stable size, and no partial suffix. Set `handler_called_after_click` in the receipt to the observed boolean; it is `false` when the handler was skipped.
11. The accepted source must be that new landing delta. Never copy from `.aris/business-e2e/20260718T011517Z/artifacts/fulltext/`, a previous acceptance artifact, cache, or another runtime's output.

## Independent artifact gate

Preferred destination:

```text
${ARIS_REPO_ROOT}/.aris/business-e2e/20260718T011517Z/grok-workspace/artifacts/fulltext/sciencedirect/grok-S1755309118300030-corporate-culture-firm-performance-china.pdf
```

Do not overwrite an existing accepted file; report `destination_collision` if the preferred path already exists.

1. Run `verify_download.py <new-landing-path> --expect pdf --min-bytes 10240` before copying.
2. Require verifier `ok: true`, `%PDF`, EOF marker, stable size, and no partial suffix.
3. Use `pdfinfo` for the page count and `pdftotext` for title, authors, DOI or PII, and article identity from the newly landed file. Browser-page identity alone is insufficient.
4. Copy only that verified post-click landing candidate to the preferred destination; rerun the verifier and hash on the destination.
5. Expect the current target to reconcile to 19 pages and the reference SHA above. Any discrepancy must be investigated as a possible version/identity mismatch, never silently accepted.

## Receipt and manifest

On success write:

```text
${ARIS_REPO_ROOT}/.aris/business-e2e/20260718T011517Z/grok-workspace/receipts/p3-sciencedirect-grok.json
```

Required receipt facts:

- `schema_version`, gate `p3_sciencedirect_grok`, `status: pass`
- `runtime: grok`, `adapter: grok_chrome_mcp`, `mcp_server: chrome-mcp`, helper project-relative path
- `site: ScienceDirect`, operation, exact target title/authors/DOI/PII
- query-free stable article URL only; no viewer/delivery URL, URL query, fragment, or signed URL
- challenge kind, whether the ordinary checkbox was clicked, and post-click result
- session reuse/login-state category and human-handoff state
- article-to-viewer flow, download event or approved fallback classification
- project-relative artifact path, detected format, size, pages, SHA-256, verifier result, and PDF-text identity checks
- timestamps, `blocker: null`, and explicit false flags for persisted credentials/cookies/session material, query-bearing delivery URLs, and signed URLs

Use this success shape, replacing all observed fields and never leaving placeholders:

```json
{
  "schema_version": 1,
  "gate": "p3_sciencedirect_grok",
  "status": "pass",
  "runtime": "grok",
  "adapter": "grok_chrome_mcp",
  "mcp_server": "chrome-mcp",
  "helper": "skills/skills-codex/browser-session-bridge/scripts/chrome_mcp_client.mjs",
  "site": "ScienceDirect",
  "operation": "article_viewer_pdf_download",
  "target": {
    "title": "The effect of corporate culture on firm performance: Evidence from China",
    "authors": ["Hailin Zhao", "Haimeng Teng", "Qiang Wu"],
    "doi": "10.1016/j.cjar.2018.01.003",
    "pii": "S1755309118300030",
    "source_url": "https://www.sciencedirect.com/science/article/pii/S1755309118300030"
  },
  "challenge_observation": {
    "kind": "none_or_passive_or_interactive_cloudflare_checkbox",
    "challenge_clicked": false,
    "automatic_clear_after_click_or_wait": true
  },
  "download_detection": {
    "viewer_opened": true,
    "native_download_event": "success_or_timeout_or_unsupported_legacy",
    "completion": "runtime_event_or_fallback_directory_increment",
    "handler_called_after_click": true
  },
  "artifact": {
    "path": ".aris/business-e2e/20260718T011517Z/grok-workspace/artifacts/fulltext/sciencedirect/grok-S1755309118300030-corporate-culture-firm-performance-china.pdf",
    "detected_format": "pdf",
    "size_bytes": 0,
    "pages": 0,
    "sha256": "observed_64_hex",
    "identity_verified_by": ["article_detail", "pdf_text"],
    "verified": true
  },
  "verifier": {"ok": true, "expected": "pdf", "min_bytes": 10240},
  "session_reused": true,
  "login_state": "already_authenticated_or_not_required",
  "human_handoff": false,
  "blocker": null,
  "security": {
    "credentials_or_cookies_persisted": false,
    "query_bearing_delivery_url_persisted": false,
    "signed_url_persisted": false
  },
  "acquired_at": "observed_ISO_8601"
}
```

Do not include raw MCP output, tab/window IDs, headers, credentials, session identifiers, temporary URLs, or Downloads filenames containing query material.

Append exactly one new Grok success row to `.aris/business-e2e/20260718T011517Z/manifests/FULLTEXT_MANIFEST.md` only after the receipt and artifact pass. Include exact runtime, adapter, artifact path, size, pages, hash, acquisition time, and receipt path; do not alter or reuse the Codex ScienceDirect row.

Run the deterministic verifier and inspect only this gate:

```bash
python3 ${ARIS_REPO_ROOT}/scripts/verify_business_e2e.py --run-id 20260718T011517Z --json
```

`runtimes.grok.browser.P3_SCIENCEDIRECT.status` must be `PASS`. Overall incompleteness from unrelated Grok gates is allowed.

On any failure, do not write a success manifest row or claim pass. Write a redacted failed/blocked receipt with the exact last verified state, `verification: failed`, and one blocker from `adapter_unavailable`, `login_required`, `captcha_required`, `subscription_denied`, `no_pdf_control`, `viewer_failed`, `download_failed`, `artifact_invalid`, `identity_mismatch`, or `destination_collision`.
