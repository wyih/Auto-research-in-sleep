# Grok P3 SSRN protected-session acceptance

Use the installed project skills `$fulltext-acquire` and `$browser-session-bridge`. Read their SSRN recipe, shared browser-session contract, and Grok adapter before acting. This is a real Grok-runtime acceptance run, not a plan or a simulation.

## Hard runtime boundary

- All browser work must go through this one-shot helper and therefore the configured `chrome-mcp` server attached to the user's real Chrome:

  ```text
  $PWD/.agents/skills/browser-session-bridge/scripts/chrome_mcp_client.mjs
  ```

- Do not use Grok `search_tool` / `use_tool`, the separate `browser` MCP, built-in web search/fetch, curl, requests, Playwright, AppleScript, direct CDP, or another browser profile.
- Do not call the MCP HTTP endpoint directly. Invoke it only through `node chrome_mcp_client.mjs ...`.
- Browser helper output is transient state, never receipt content.
- Never request, inspect, print, or persist cookies, storage, passwords, auth headers, account identifiers, session identifiers, query-bearing delivery URLs, or signed URLs.

Set local command paths without changing user configuration:

```bash
BRIDGE_SKILL_DIR="$PWD/.agents/skills/browser-session-bridge"
MCP_CLIENT="$BRIDGE_SKILL_DIR/scripts/chrome_mcp_client.mjs"
DOWNLOAD_VERIFIER="$BRIDGE_SKILL_DIR/scripts/verify_download.py"
```

Run the helper redaction self-test, then use `list-tools` only if needed. Every operation must be a short one-shot process. A nonzero helper exit is not acceptance evidence.

Every shorthand below means a helper subprocess: `schema TOOL` means `node "$MCP_CLIENT" schema TOOL`; `tabs ...` means `node "$MCP_CLIENT" tabs ...`; and a browser call means `node "$MCP_CLIENT" call TOOL --args-json '<object matching the live schema>'`. Never invoke a Chrome MCP tool by another route.

## Foreground-only legacy-safe rules

The installed extension may be the legacy executor. Its compatibility path cannot safely focus a background tab: it only verifies that the requested tab is already active in the focused Chrome window. Before the run, the operator must therefore leave exactly one SSRN tab open and in the foreground. Never open a replacement tab, call `chrome_switch_tab` to imitate a switch, navigate a background tab, or act on an arbitrary active tab.

1. Before **every** navigation, read, scroll check, click, or post-click state check, run `tabs --url-contains "papers.ssrn.com"`. Require exactly one match with `active: true`. If there are zero, multiple, or inactive matches, stop for foreground handoff; do not choose one heuristically.
2. Treat the returned `tabId` as a one-operation lease. Use it only in the immediately following helper call, then discard it and run `tabs` again. Never write, cache, hard-code, or reuse a tab ID across calls or state transitions.
3. Inspect each tool's live schema before its first use and pass only helper-allowlisted fields. Use only compact `chrome_read_page` calls with a narrow CSS `selector`, `textQuery`, and/or `types` filter. `chrome_get_web_content` is not a public helper operation and must never be called directly.
4. Never call `chrome_javascript`, `chrome_inject_script`, XPath selectors, element `ref`/`refId`, stale snapshot identifiers, or coordinate clicks. Never use `chrome_computer` to click.
5. Every action starts with one native `chrome_click_element` call using a CSS selector freshly returned or confirmed by the immediately preceding compact page read, with `selectorType: "css"`. After any nonzero/uncertain mutating result, reacquire and reread state before deciding what happened; never blindly retry. If the expected transition provably did not occur, one bounded `exact-selector-click` fallback is permitted with that fresh selector, exact text, one narrow scope, and a newly reacquired tab ID; immediately verify post-state and never treat `effect_state:attempted` as acceptance evidence.
6. `exact-text` is permitted only when a uniquely scoped, visible label must be inspected and scrolled into view. It never clicks and is not acceptance evidence. After it returns `ready`, reacquire the foreground tab, reread compact state, obtain a current CSS selector, and make one native click. Do not use it as a selector generator or as identity/download proof.
7. After navigation or a click that may change the page or open a tab, run `tabs` again and require the intended SSRN tab to be the unique foreground match before rereading. If Chrome leaves the result in the background, stop for foreground handoff instead of switching it automatically.

## Frozen target identity

- Title: `Corporate Culture: Evidence from the Field`
- Authors: John R. Graham; Campbell R. Harvey; Jillian Popadak; Shiva Rajgopal
- SSRN abstract ID: `2937525`
- Stable abstract entry: `https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2937525`
- Current independently verified Codex reference: 79 pages, 875844 bytes, SHA-256 `f69be9aa4373ff67db8a98b9bcb27ff3576067ae82a1337a88e1aaed998847a2`

The reference facts identify the target; they do not authorize copying the Codex artifact. A byte-identical fresh SSRN download is acceptable only when its provenance is a new file landed after this Grok run's download click.

## Required browser flow

1. Record the operation start time and a narrow baseline inventory of `/Users/wyih/Downloads` containing only names, sizes, and modification times. Do not search the rest of the home directory.
2. Reacquire the unique foreground SSRN tab, inspect `schema chrome_navigate`, navigate that same leased tab to the stable abstract entry with `newWindow: false`, then reacquire it and perform a compact `chrome_read_page` identity read.
3. SSRN's expected challenge is passive. If an interstitial appears, do not click it and do not reload repeatedly. Wait in bounded steps, reacquiring the unique foreground tab and rereading compact state each time. The Codex observation cleared automatically after about 12 seconds; use a bounded total wait and record the observed duration.
4. If the passive challenge clears, verify the exact title, all four authors, and abstract ID before touching a download control.
5. If a visible interactive or hard CAPTCHA remains and blocks the intended action, stop with `captcha_required`. Do not bypass it. Hidden or offscreen challenge markup is not a blocker.
6. Immediately before the final click, refresh the narrow `/Users/wyih/Downloads` inventory and record the click time. Do **not** arm `chrome_handle_download`: the legacy implementation is a post-click `~/Downloads` increment detector, not an event waiter.
7. Reacquire and compact-read the unique foreground SSRN tab. Click the current visible `Download This Paper` / PDF control exactly once with a fresh CSS selector through `chrome_click_element`. Do not manufacture or persist a delivery URL, and do not fall back to refs, XPath, JavaScript, screenshots, or coordinates.
8. After the click, reacquire and inspect post-state before any retry. Then inspect `schema chrome_handle_download`. If the helper schema accepts `filenameContains`, call it **after** the click with a narrow query-free filename token derived from the visible target, `directory: "/Users/wyih/Downloads"`, bounded `lookbackMs`, and `waitForComplete: true`. Under legacy compatibility, classify a success only as `fallback_directory_increment`, never as a native runtime event. If the tool is unavailable, unsuitable, or times out, independently diff only `/Users/wyih/Downloads` against the pre-click baseline. Require a post-click file, plausible PDF name, no partial suffix, and stable size across polls. Set `handler_called_after_click` in the receipt to the observed boolean; it is `false` when the handler was skipped.
9. The source of the accepted file must be that new directory delta. Never use or copy any file from `.aris/business-e2e/20260718T011517Z/artifacts/fulltext/` or another prior acceptance directory.

## Independent artifact gate

Preferred destination:

```text
/Users/wyih/Projects/Auto-research-in-sleep/.aris/business-e2e/20260718T011517Z/grok-workspace/artifacts/fulltext/ssrn/grok-ssrn-2937525-corporate-culture-evidence-field.pdf
```

Create the destination directory only after a new landing candidate exists. Do not overwrite an existing accepted artifact; report `destination_collision` instead.

1. Run `verify_download.py <new-landing-path> --expect pdf --min-bytes 10240` before copying it.
2. Require `%PDF` magic, an EOF marker, stable size, no partial suffix, and verifier `ok: true`.
3. Use `pdfinfo` to record the observed page count and `pdftotext` to verify the title and author identity from the newly landed PDF. Do not infer identity from the browser page alone.
4. Copy only the verified new landing candidate to the preferred destination, then rerun the same verifier and SHA-256 check on the destination.
5. Expect 79 pages and the reference SHA above for the current target. Any discrepancy requires explicit content-level reconciliation; never silently accept a different paper.

## Receipt and manifest

On success, write:

```text
/Users/wyih/Projects/Auto-research-in-sleep/.aris/business-e2e/20260718T011517Z/grok-workspace/receipts/p3-ssrn-grok.json
```

The JSON must include:

- `schema_version`, gate `p3_ssrn_grok`, `status: pass`
- `runtime: grok`, `adapter: grok_chrome_mcp`, `mcp_server: chrome-mcp`, and the helper's project-relative path
- `site: SSRN`, operation, exact target title/authors/abstract ID
- a query-free `source_origin` such as `https://papers.ssrn.com/sol3/papers.cfm`; do not store the navigation query string
- passive-challenge observation, actual bounded wait, and `challenge_clicked: false`
- session reuse/login-state category and whether human handoff occurred
- download event result and fallback classification
- project-relative artifact path, detected format, byte size, pages, SHA-256, verifier result, and the local identity checks performed
- timestamps, `blocker: null`, and explicit false security flags for persisted credentials/session material, query-bearing delivery URLs, and signed URLs

Use this success shape, replacing every observed value rather than copying placeholders:

```json
{
  "schema_version": 1,
  "gate": "p3_ssrn_grok",
  "status": "pass",
  "runtime": "grok",
  "adapter": "grok_chrome_mcp",
  "mcp_server": "chrome-mcp",
  "helper": "skills/skills-codex/browser-session-bridge/scripts/chrome_mcp_client.mjs",
  "site": "SSRN",
  "operation": "abstract_detail_pdf_download",
  "target": {
    "title": "Corporate Culture: Evidence from the Field",
    "authors": ["John R. Graham", "Campbell R. Harvey", "Jillian Popadak", "Shiva Rajgopal"],
    "ssrn_abstract_id": "2937525",
    "source_origin": "https://papers.ssrn.com/sol3/papers.cfm"
  },
  "challenge_observation": {
    "kind": "passive_cloudflare_interstitial",
    "wait_seconds": 0,
    "challenge_clicked": false,
    "automatic_clear": true
  },
  "download_detection": {
    "native_download_event": "success_or_timeout_or_unsupported_legacy",
    "completion": "runtime_event_or_fallback_directory_increment",
    "handler_called_after_click": true
  },
  "artifact": {
    "path": ".aris/business-e2e/20260718T011517Z/grok-workspace/artifacts/fulltext/ssrn/grok-ssrn-2937525-corporate-culture-evidence-field.pdf",
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
    "credentials_or_session_material_persisted": false,
    "query_bearing_delivery_url_persisted": false,
    "signed_url_persisted": false
  },
  "acquired_at": "observed_ISO_8601"
}
```

Do not include raw helper output, tab/window IDs, Downloads source filename if it contains query data, URL queries/fragments, delivery URLs, cookies, headers, credentials, or session material.

After the receipt exists, append exactly one success row for this Grok artifact to `.aris/business-e2e/20260718T011517Z/manifests/FULLTEXT_MANIFEST.md`, including exact runtime, adapter, artifact path, size, pages, hash, time, and receipt path. Do not edit or reuse a Codex row.

Finally run:

```bash
python3 /Users/wyih/Projects/Auto-research-in-sleep/scripts/verify_business_e2e.py --run-id 20260718T011517Z --json
```

Confirm specifically that `runtimes.grok.browser.P3_SSRN.status` is `PASS`; the overall run may remain incomplete because other Grok gates are independent.

If any required step fails, do not add a success manifest row and do not claim pass. Write a redacted failure/blocked receipt with the exact last verified state, `verification: failed`, and one blocker from `adapter_unavailable`, `login_required`, `captcha_required`, `access_denied`, `no_pdf_control`, `download_failed`, `artifact_invalid`, `identity_mismatch`, or `destination_collision`.
