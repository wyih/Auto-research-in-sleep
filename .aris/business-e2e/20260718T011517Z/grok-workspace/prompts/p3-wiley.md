# Grok P3 Wiley protected-session acceptance

Use the installed project skills `$fulltext-acquire` and `$browser-session-bridge`. Read their Wiley recipe, shared browser-session contract, and Grok adapter before acting. Execute a real independent Grok download; do not merely describe the flow.

## Hard runtime boundary

- The only allowed browser path is the project helper below, which connects to `chrome-mcp` attached to the user's real Chrome:

  ```text
  $PWD/.agents/skills/browser-session-bridge/scripts/chrome_mcp_client.mjs
  ```

- Do not use Grok `search_tool` / `use_tool`, the separate `browser` MCP, web search/fetch, curl, requests, Playwright, AppleScript, direct CDP/MCP HTTP, or another browser profile.
- Never inspect or persist cookies, storage, credentials, auth headers, account/session identifiers, raw reader/download URL queries, or signed URLs.
- Never place raw helper output in a receipt.

Use these paths without changing configuration:

```bash
BRIDGE_SKILL_DIR="$PWD/.agents/skills/browser-session-bridge"
MCP_CLIENT="$BRIDGE_SKILL_DIR/scripts/chrome_mcp_client.mjs"
DOWNLOAD_VERIFIER="$BRIDGE_SKILL_DIR/scripts/verify_download.py"
```

Run the helper self-test first. Keep all subsequent calls one-shot and schema-driven. A nonzero helper exit is a failure, not evidence of success.

Every shorthand below is a helper subprocess: `schema TOOL` means `node "$MCP_CLIENT" schema TOOL`; `tabs ...` means `node "$MCP_CLIENT" tabs ...`; and a browser call means `node "$MCP_CLIENT" call TOOL --args-json '<object matching the live schema>'`. Never invoke a Chrome MCP tool by any other route.

## Foreground-only legacy-safe rules

The installed extension may be the legacy executor. Its compatibility path cannot safely focus a background tab: it only verifies that the requested tab is already active in the focused Chrome window. Before the run, the operator must therefore leave exactly one Wiley tab open and in the foreground. Never open a replacement tab, call `chrome_switch_tab` to imitate a switch, navigate a background tab, or act on an arbitrary active tab.

1. Before **every** navigation, read, scroll check, challenge click, PDF click, reader action, or post-click state check, run `tabs --url-contains "onlinelibrary.wiley.com"`. Require exactly one match with `active: true`. Zero, multiple, or inactive matches require foreground handoff; never select a tab heuristically.
2. Treat the returned `tabId` as a one-operation lease. Use it only in the immediately following helper call, then discard it and run `tabs` again. Never write, cache, hard-code, or reuse a tab ID across calls or state transitions.
3. Inspect every tool's live schema before first use and pass only helper-allowlisted fields. Read only with compact `chrome_read_page` calls using a narrow CSS `selector`, `textQuery`, and/or `types` filter. `chrome_get_web_content` is not a public helper operation and must never be called directly.
4. Never call `chrome_javascript`, `chrome_inject_script`, XPath selectors, element `ref`/`refId`, stale snapshot identifiers, or coordinate clicks. Never use `chrome_computer` to click a challenge, article control, or reader control.
5. Every action starts with one native `chrome_click_element` call using a CSS selector freshly returned or confirmed by the immediately preceding compact read, with `selectorType: "css"`. After any nonzero/uncertain mutating result, reacquire and reread state before deciding what happened; never blindly retry. If the expected transition provably did not occur, one bounded `exact-selector-click` fallback is permitted with that fresh selector, exact text, one narrow scope, and a newly reacquired tab ID; immediately verify post-state and never treat `effect_state:attempted` as acceptance evidence. This fallback is not permitted for a challenge checkbox or other challenge.
6. `exact-text` is permitted only to inspect and scroll one uniquely scoped rendered label. It never clicks and is not acceptance evidence. After `ready`, reacquire, compact-read, obtain a current CSS selector, and issue one native click. Do not use it as a selector generator or as article/download proof.
7. After every navigation, challenge transition, article-to-reader transition, or new-tab event, reacquire the Wiley domain and require the intended result to be the unique foreground match. If Chrome leaves it in the background, stop for foreground handoff rather than switching it automatically.

## Frozen target identity

- Title: `Corporate culture: The interview evidence`
- Authors: John R. Graham; Jillian A. Grennan; Campbell R. Harvey; Shivaram Rajgopal
- DOI: `10.1111/jacf.12528`
- Stable article entry: `https://onlinelibrary.wiley.com/doi/10.1111/jacf.12528`
- Access state observed in the Codex acceptance: open access
- Current independently verified Codex reference: 20 pages, 351270 bytes, SHA-256 `e147dbb6ce77284830f320354e8d22a3a056ef05eacf6c4970f7a6acb8efe53f`

These reference facts freeze identity only. Do not read or copy the Codex artifact. A matching hash is acceptable only with an independently new file landed after this Grok run's Wiley download click.

## Required browser flow

1. Record the start time and a narrow baseline inventory of `/Users/wyih/Downloads` containing names, sizes, and modification times only.
2. Reacquire the unique foreground Wiley tab, inspect `schema chrome_navigate`, navigate that same leased tab to the stable DOI page with `newWindow: false`, then reacquire and perform a compact `chrome_read_page` identity read.
3. If the page initially shows a shell or passive verification, wait in bounded steps, reacquiring the unique foreground tab and rereading compact state each time. The Codex run observed no viewport-blocking challenge and required no login.
4. If an ordinary visible checkbox challenge blocks the article, stop with `captcha_required` unless the current Grok launch includes a separate action-time rule recording that the user confirmed this already-observed challenge. Earlier general authorization is not that launch-time rule. With that explicit rule only, reacquire and compact-read the foreground tab, require a current CSS selector for the visible checkbox, and make one native `chrome_click_element` click with `selectorType: "css"`; then wait, reacquire, and reread. If no fresh CSS selector is exposed, stop rather than using screenshots, coordinates, refs, XPath, or JavaScript. Do not automate sliders, press-and-hold, image puzzles, hard CAPTCHAs, MFA, or credential entry. Hidden/offscreen markup is not a blocker.
5. Confirm exact title, all four authors, DOI, access state, and a visible PDF control on the article page. An Open Access label or HTML article alone is not download proof.
6. Do **not** arm `chrome_handle_download`: the legacy implementation is a post-click `~/Downloads` increment detector, not an event waiter. Refresh the narrow `/Users/wyih/Downloads` baseline and record the click time immediately before the article PDF click because that click may itself land the file.
7. Reacquire and compact-read the foreground article tab, then click its current visible PDF control exactly once through `chrome_click_element` with a freshly confirmed CSS selector. The `/doi/epdf/` shape is only a hint. Do not construct or persist a reader URL.
8. Reacquire the resulting Wiley reader tab/page only if it is already the unique foreground Wiley match, then compact-read and confirm target title/DOI. If it remains in the background, stop for handoff; do not switch it automatically.
9. Immediately before the final reader download click, refresh the narrow `/Users/wyih/Downloads` inventory and record the click time. Reacquire and compact-read the reader, then click its current visible `Download PDF` control exactly once using a fresh CSS selector through `chrome_click_element`. The `/doi/pdfdirect/` shape is only a hint; never construct, print, or persist a query-bearing download URL.
10. If the reader control lacks a current CSS selector, use `exact-text` only to inspect/scroll it, then reacquire and reread for a CSS selector. If none is exposed or the helper refuses the reader URL under legacy compatibility, stop with `reader_failed`; never use screenshots, coordinates, refs, XPath, JavaScript, or a background switch.
11. After the final click, reacquire and inspect post-state before any retry. Then inspect `schema chrome_handle_download`. If it accepts `filenameContains`, call it **after** the click with a narrow query-free target-derived filename token, `directory: "/Users/wyih/Downloads"`, bounded `lookbackMs`, and `waitForComplete: true`. Under legacy compatibility, record success only as `fallback_directory_increment`, never a native event. If unavailable, unsuitable, or timed out, independently diff only `/Users/wyih/Downloads` against the most recent pre-click baseline. Require a post-click plausible PDF, no partial suffix, and stable size. Set `handler_called_after_click` in the receipt to the observed boolean; it is `false` when the handler was skipped.
12. Accept only that new landing delta. Never copy from `.aris/business-e2e/20260718T011517Z/artifacts/fulltext/`, another acceptance artifact, cache, or prior runtime output.

## Independent artifact gate

Preferred destination:

```text
/Users/wyih/Projects/Auto-research-in-sleep/.aris/business-e2e/20260718T011517Z/grok-workspace/artifacts/fulltext/wiley/grok-graham-et-al-2023-corporate-culture-interview-evidence.pdf
```

Do not overwrite an existing accepted artifact; use blocker `destination_collision` if the preferred path exists.

1. Run `verify_download.py <new-landing-path> --expect pdf --min-bytes 10240` before copying.
2. Require `%PDF`, EOF marker, stable size, no partial suffix, and verifier `ok: true`.
3. Run `pdfinfo` for observed pages and `pdftotext` for title, DOI, and author identity from the new file. Browser-reader identity alone is insufficient.
4. Copy only the verified new landing candidate to the preferred destination; rerun the verifier and SHA-256 check on the destination.
5. Expect the current target to reconcile to 20 pages and the reference SHA above. Investigate any discrepancy as a possible version/identity mismatch; never silently accept it.

## Receipt and manifest

On success write:

```text
/Users/wyih/Projects/Auto-research-in-sleep/.aris/business-e2e/20260718T011517Z/grok-workspace/receipts/p3-wiley-grok.json
```

Required receipt facts:

- `schema_version`, gate `p3_wiley_grok`, `status: pass`
- `runtime: grok`, `adapter: grok_chrome_mcp`, `mcp_server: chrome-mcp`, helper project-relative path
- `site: Wiley Online Library`, operation, exact title/authors/DOI/access state
- query-free stable DOI article URL only; no reader/download URL, query, fragment, or signed URL
- challenge/login observations, session reuse, and human-handoff state
- article-to-reader flow, download event or controlled-directory fallback classification
- project-relative artifact path, detected format, exact size/pages/SHA-256, verifier output summary, and PDF-text identity checks
- timestamps, `blocker: null`, and explicit false security flags for persisted credentials/session material, query-bearing reader/delivery URLs, and signed URLs

Use this success shape and replace all observed values; no placeholder may remain:

```json
{
  "schema_version": 1,
  "gate": "p3_wiley_grok",
  "status": "pass",
  "runtime": "grok",
  "adapter": "grok_chrome_mcp",
  "mcp_server": "chrome-mcp",
  "helper": "skills/skills-codex/browser-session-bridge/scripts/chrome_mcp_client.mjs",
  "site": "Wiley Online Library",
  "operation": "article_reader_pdf_download",
  "target": {
    "title": "Corporate culture: The interview evidence",
    "authors": ["John R. Graham", "Jillian A. Grennan", "Campbell R. Harvey", "Shivaram Rajgopal"],
    "doi": "10.1111/jacf.12528",
    "source_url": "https://onlinelibrary.wiley.com/doi/10.1111/jacf.12528",
    "access_state": "open_access"
  },
  "challenge_observation": {
    "kind": "none_or_passive_or_ordinary_checkbox",
    "challenge_clicked": false,
    "viewport_blocking_challenge": false
  },
  "download_detection": {
    "reader_opened": true,
    "native_download_event": "success_or_timeout_or_unsupported_legacy",
    "completion": "runtime_event_or_fallback_directory_increment",
    "handler_called_after_click": true
  },
  "artifact": {
    "path": ".aris/business-e2e/20260718T011517Z/grok-workspace/artifacts/fulltext/wiley/grok-graham-et-al-2023-corporate-culture-interview-evidence.pdf",
    "detected_format": "pdf",
    "size_bytes": 0,
    "pages": 0,
    "sha256": "observed_64_hex",
    "identity_verified_by": ["article_detail", "reader_identity", "pdf_text"],
    "verified": true
  },
  "verifier": {"ok": true, "expected": "pdf", "min_bytes": 10240},
  "session_reused": true,
  "login_state": "already_authenticated_or_not_required",
  "human_handoff": false,
  "blocker": null,
  "security": {
    "credentials_or_session_material_persisted": false,
    "query_bearing_reader_or_delivery_url_persisted": false,
    "signed_url_persisted": false
  },
  "acquired_at": "observed_ISO_8601"
}
```

Do not record raw MCP output, tab/window IDs, headers, credentials, session identifiers, temporary URLs, or Downloads names containing query material.

Append exactly one Grok success row to `.aris/business-e2e/20260718T011517Z/manifests/FULLTEXT_MANIFEST.md` only after artifact and receipt verification. Include exact runtime, adapter, artifact path, size, pages, hash, time, and receipt path; preserve the existing Codex Wiley row.

Run:

```bash
python3 /Users/wyih/Projects/Auto-research-in-sleep/scripts/verify_business_e2e.py --run-id 20260718T011517Z --json
```

Confirm `runtimes.grok.browser.P3_WILEY.status` is `PASS`; unrelated missing Grok gates may keep the overall report incomplete.

On failure, do not append a success manifest row or claim pass. Write a redacted failed/blocked receipt with the last verified state, `verification: failed`, and exactly one blocker from `adapter_unavailable`, `login_required`, `captcha_required`, `subscription_denied`, `no_pdf_control`, `reader_failed`, `download_failed`, `artifact_invalid`, `identity_mismatch`, or `destination_collision`.
