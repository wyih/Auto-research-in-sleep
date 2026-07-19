# Grok Chrome MCP Adapter

Use this adapter only in Grok when `chrome-mcp` is healthy and connected to the user's real Chrome profile. Do not use Grok's separate `browser` MCP for login-dependent portals because it has an independent headless profile.

## Preflight

1. Confirm `chrome-mcp` is available in the current Grok tool set. When diagnosing from the CLI, `grok mcp doctor` must report a healthy handshake and discovered tools.
2. Use `get_windows_and_tabs` to locate a suitable existing tab before opening another one.
3. Keep credentials and session material inside Chrome. Never request or print cookies, tokens, passwords, or auth headers.

## Tool Invocation Order

Use Grok's dynamic `search_tool` / `use_tool` path first. It is the normal route and keeps the active tool schema visible to the model.

If `grok mcp doctor` reports `chrome-mcp` healthy but Grok's tool meta-layer returns `Tool not found`, HTTP 413, or inflates the context before a call reaches the MCP server, Grok may invoke the canonical one-shot helper from a shell:

```bash
node "$BRIDGE_SKILL_DIR/scripts/chrome_mcp_client.mjs" list-tools
node "$BRIDGE_SKILL_DIR/scripts/chrome_mcp_client.mjs" schema chrome_read_page
node "$BRIDGE_SKILL_DIR/scripts/chrome_mcp_client.mjs" tabs --url-contains "cnki.net"
node "$BRIDGE_SKILL_DIR/scripts/chrome_mcp_client.mjs" call chrome_read_page \
  --args-json '{"tabId":123}'
node "$BRIDGE_SKILL_DIR/scripts/chrome_mcp_client.mjs" exact-text \
  --tab-id 123 --scope-selector 'main' --text 'Exact visible label'
node "$BRIDGE_SKILL_DIR/scripts/chrome_mcp_client.mjs" exact-selector-click \
  --tab-id 123 --scope-selector 'main' --selector 'fresh > css' --text 'Exact visible label'
```

The helper still connects directly to `chrome-mcp` through the MCP Streamable HTTP protocol; it is not a browser substitute. It uses `ARIS_CHROME_MCP_URL` when set and otherwise `http://127.0.0.1:12306/mcp`. Do not put credentials, cookies, tokens, auth headers, or signed download URLs in command arguments. Navigation and legacy foreground-tab guards reject credential-bearing parameter names in query strings, fragments, and nested or repeatedly encoded callback/payload values, including forms such as `apiKey`, `authToken`, `sessionId`, `AWSAccessKeyId`, `access_token`, `SAMLResponse`, `code`, and `sig`; the complete URL must never reach a compatibility injection call. Its output is recursively redacted and size-limited; `tabs` requires a URL substring and returns only matching `tabId`, `windowId`, `active`, query-free URL fields, and tri-state window-focus telemetry. `windowFocused:null` with `windowFocusTelemetry:"unsupported"` means the old extension omitted the focus field; it must never be interpreted or reported as `false`. `call` is a strict production allowlist with per-tool argument allowlists; arbitrary script, network, history, cookie, and storage tools are rejected before connecting.

Keep each helper process to one short operation. Discover a tool name, fetch only that tool's schema, locate only the intended domain tab, then make one tool call. Start another process for the next state transition. This prevents a large tools list or page result from accumulating into another 413 response.

Exit codes are stable: `2` invalid arguments, `3` missing SDK, `4` MCP connection/protocol failure, `5` tool absent from the live MCP schema, `6` tool invocation/returned error, and `7` unexpected local failure. A nonzero result is not browser acceptance evidence.

## Bridge/Extension Version Skew

The native bridge and the loaded Chrome extension can have version skew: the bridge may advertise a modern tool such as `chrome_read_page`, while the extension executor returns `Tool chrome_read_page not found`. The helper detects that exact executor error and, without changing the extension or Chrome configuration, maps supported operations onto the older extension protocol:

- `chrome_switch_tab`: succeeds through the modern tool when available. Under the old executor it never imitates a switch by navigating another tab. It requires the requested `tabId` to be active, HTTP(S), and the only tab with its exact raw URL. When focus telemetry exists it also requires `focused:true`; when the old extension omits focus telemetry globally, the helper records `unsupported` and relies on the active/unique/tab-scoped lease. Otherwise it returns `target_tab_not_foreground` or `target_tab_focus_telemetry_missing` without navigating or mutating any tab.
- `chrome_read_page`: re-verifies that same active/unique/tab-scoped lease, then calls `chrome_get_interactive_elements`; use a narrow `selector`, `textQuery`, and/or `types` filter so the result stays small. The operator must keep Chrome visually in front while the old executor reports focus telemetry as unsupported.
- `chrome_computer`: maps supported single-click, fill/type, key, screenshot, and bounded-wait actions to the old click/fill/keyboard/screenshot tools. Legacy double-click is rejected because two independent calls are not atomic and are unsafe to retry. Unsupported actions, including scroll, fail explicitly.
- Existing `chrome_click_element` and `chrome_fill_or_select` calls first activate the requested tab. The legacy executor supports CSS selectors only; it cannot resolve modern element refs or XPath selectors.

If the legacy click executor rejects an identity-matched element only because it is outside the viewport, first bring the intended tab to the foreground, then run the restricted `exact-text` operation once. It requires exactly one scope and one deepest rendered match and uses a fixed MAIN-world script only to validate and scroll the candidate because the 0.0.6 executor cannot read DOM markers created in its isolated injection world. The script has no click, network, storage, credential, or arbitrary-code interface. Hidden, disabled, inert, pointer-disabled, obscured, ambiguous, oversized, or scan-timeout targets fail closed. Its bounded, integrity-tagged marker is advisory only and is not hostile-page authentication: `acceptance_evidence:false`. `exact-text` never clicks. Re-read the foreground tab through `chrome_read_page`, obtain a current semantic selector, then issue one native click and independently verify the resulting page state before any retry.

If that native CSS click then fails or times out, treat its effect as unknown and independently re-read the page. Only when the expected transition did not occur may the old executor use `exact-selector-click` as a different, bounded fallback. It requires the exact visible text, the immediately preceding fresh CSS selector, one narrow scope, one unique in-scope target, rendered/enabled/viewport/hit-test checks, and performs exactly one fixed `HTMLElement.prototype.click`. It accepts no coordinates, refs, XPath, JavaScript, or arbitrary event payload. Its success means only `effect_state:"attempted"`, `acceptance_evidence:false`, and `state_check_required:true`; reacquire the route-specific tab and prove the post-click state before continuing or retrying.

The old extension has no download-event waiter. For `chrome_handle_download`, the helper therefore offers only a post-click filesystem fallback restricted to `~/Downloads`. It requires a narrow non-empty `filenameContains`, optionally accepts `lookbackMs`, ignores `.crdownload` files, and requires a stable file size when `waitForComplete` is not false. Inventory the approved landing directory immediately before the final click: this fallback proves a new/stabilized file, not a Chrome runtime download event. Never accept it without the shared deterministic artifact verification.

There is deliberately no arbitrary `chrome_javascript` downgrade: the legacy injection tool cannot safely return a general evaluation result. The only DOM-injection exceptions are the fixed locate-and-scroll `exact-text` operation and the separately constrained, post-failure `exact-selector-click` operation above. The scroll marker is HMAC integrity-tagged with an ephemeral key and Node projects only fixed bounded fields, but MAIN-world execution means it is advisory rather than hostile-page authentication. Neither operation emits page text or URL fingerprints or can auto-switch tabs. A compatibility-marked response is execution evidence only after the resulting page state or artifact is independently verified.

## Semantic Mapping

Use the exact current tool schema shown by Grok; the common mapping is:

| Contract operation | Grok `chrome-mcp` tool |
|---|---|
| `session.attach`, `tab.list` | `get_windows_and_tabs` |
| `tab.open_or_claim`, `page.navigate`, `page.reload` | `chrome_navigate` to the recipe-approved stable URL; use a native refresh only when the live schema exposes it |
| `page.inspect` | `chrome_read_page` |
| `element.act` | `chrome_click_element` or `chrome_computer` |
| `auth.recover_soft_timeout` | Fresh read → click only the recipe-identified close control → one stable-page reload → fresh read before login |
| `script.evaluate` | `chrome_javascript` |
| `download.wait` | `chrome_handle_download` armed before the final click when required by its schema |

Prefer semantic page reads and element clicks. Use `chrome_computer` only when the portal exposes a canvas, native picker, or otherwise lacks stable semantic elements. Refresh page state after every navigation or modal transition.

Before the final click, also inventory only the approved landing directory. If `chrome_handle_download` does not return a completion event but Chrome lands a file, accept it only through the shared new/stabilized-file fallback plus deterministic verification, and record the missing event.

## Human Handoff

- Logged out: first complete any recipe-identified soft-timeout recovery. If fresh post-reload state still proves logout, ask the user to sign in in the same Chrome tab, then inspect again.
- Hard CAPTCHA, slider, or press-and-hold challenge that visibly intersects the viewport and blocks the intended operation: stop and ask the user; do not automate it. Hidden/preloaded challenge markup is not a handoff.
- Subscription or institutional access denial: return `access_denied`; do not switch to an unauthorized source.

## Acceptance Evidence

Set `adapter: grok_chrome_mcp` only when the successful operation trace contains `chrome-mcp` tool calls and the landed artifact passes deterministic verification. A response that merely describes intended MCP calls is not a pass. A successful run through the separate `browser` MCP is not a protected-session pass.

Calls made through `scripts/chrome_mcp_client.mjs` count as `chrome-mcp` calls only when they exit successfully and the resulting browser state or artifact is independently verified under the shared contract. Never persist the helper's raw output as a receipt.
