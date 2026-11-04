# Antigravity Chrome Adapter

Use this adapter only when the current runtime is Google Antigravity and its built-in `chrome-mcp` browser integration is connected. It drives the user's real Chrome through the Antigravity Chrome extension, reusing that profile's existing sign-ins. The user's explicit browser choice remains in force. Under Codex use [codex-chrome.md](codex-chrome.md); under Kimi Code use [kimi-webbridge.md](kimi-webbridge.md); under Claude Code use [claude-in-chrome.md](claude-in-chrome.md). Never mix bindings in one operation.

## Availability

- Antigravity Chrome integration requires the `chrome-mcp` MCP server mounted in the current Antigravity session and connected to the user's signed-in Chrome window.
- When `chrome-mcp` tools are absent or return a disconnected-extension error, record `browser_unavailable` for the protected route; do not substitute standalone Playwright, a clean automation profile, or a third-party browser backend.

## Binding Rules

1. The browser tools are exposed as lazy-loaded MCP tools under `ServerName: "chrome-mcp"` and invoked through `call_mcp_tool`. Read the needed schema under `<appDataDir>/mcp/chrome-mcp/<toolName>.json` before first use.
2. Call `get_windows_and_tabs` first to inspect live windows and tabs. Match the user's requested Chrome window or existing site tab against that live inventory; numeric `windowId` and `tabId` values must come from the current call. If the requested browser instance is absent, report it as unconnected and do not silently use another browser.
3. Verify identity when the account matters: a Chrome window or profile label does not establish the website account. Inspect only the site's own visible account indicator; do not read unrelated private content.
4. Claim an existing relevant tab with `chrome_switch_tab` or pass its explicit `tabId` to subsequent calls, or open/navigate a tab in the same window with `chrome_navigate`.
5. Do not read cookies, local storage, passwords, browser profile files, or session stores. `chrome_javascript` is for read-only DOM inspection allowed by the recipe; never use it to read `document.cookie`, storage APIs, or credential fields, or to make authenticated network requests.
6. Serialize protected browser work against the selected profile. Do not dispatch multiple agents or projects to mutate its tabs concurrently.

## Semantic Mapping

| Contract operation | Antigravity `chrome-mcp` action |
|---|---|
| `session.attach` | Call `get_windows_and_tabs` through `call_mcp_tool` (`ServerName: "chrome-mcp"`) to verify live connection and window/tab inventory |
| `tab.list` | `get_windows_and_tabs` |
| `tab.open_or_claim` | Reuse a matching `tabId` (with `chrome_switch_tab` when needed) or navigate a tab in the target `windowId` with `chrome_navigate` |
| `page.inspect` | `chrome_read_page` (accessibility tree with `ref` IDs) or `chrome_get_web_content`; `chrome_screenshot` or `chrome_computer` (`action: "screenshot"`) when rendered state is uncertain |
| `page.navigate` | `chrome_navigate` with `url` and target `tabId` |
| `page.reload` | `chrome_navigate` with `refresh: true` and target `tabId`, wait for settle, then inspect |
| `element.act` | `chrome_click_element` or `chrome_fill_or_select` by `ref` or selector for non-credential controls, or `chrome_computer` for coordinate/key/scroll actions; re-inspect afterward |
| `auth.submit_saved` | Not used under Antigravity; route to `human.handoff` |
| `auth.recover_soft_timeout` | Click only the recipe-identified close control, reload once with `chrome_navigate` (`refresh: true`), then inspect before any login branch |
| `script.evaluate` | `chrome_javascript`, read-only, when the recipe allows it |
| `download.wait` | Snapshot the landing directory before the final click, optionally pair with `chrome_handle_download`, and verify disk completion via `fallback_directory_increment` |
| `artifact.verify` | `<skill-dir>/scripts/verify_download.py` plus caller-specific checks |
| `human.handoff` | Stop in the same tab, tell the user exactly what to complete (login, MFA, account choice, hard challenge, download-warning override), and resume only after their confirmation and a fresh inspection |
| `session.release` | Stop issuing commands; close only temporary tabs this operation opened (`chrome_close_tabs` with explicit `tabIds`), never the user's tabs |

## Landing Directory And Sandbox Boundary

Chrome saves to its configured download directory, usually `~/Downloads`. Because Antigravity's `run_command` executes inside a workspace-scoped sandbox by default (`BypassSandbox: false`), any shell step that snapshots `~/Downloads` or moves a verified download from `~/Downloads` into the project deliverable directory must run as a minimal single command with `BypassSandbox: true`, while local verification and processing inside the workspace remain sandboxed (`BypassSandbox: false`). Record only names, sizes, and modification times in the landing directory before the final click, apply the contract's `fallback_directory_increment` completion, and move the verified file to the requested project directory.

## Acceptance Evidence

Set `client_runtime: antigravity` and `adapter: antigravity_chrome` only when the operation actually ran through this binding, with `mcp_server: chrome-mcp`, `implementation: antigravity_chrome_extension`, and `profile_mode: existing_user_chrome`. Keep the non-sensitive final page URL or title, the verified artifact path, size, and hash, and the caller-specific verification. A generic web search/fetch or `curl` trace without browser interaction is not an Antigravity Chrome pass.

## Known Limits

- Antigravity Chrome pauses at login pages and CAPTCHAs for the user; login submission always goes to `human.handoff`, including forms Chrome has already populated.
- Accessibility snapshots from `chrome_read_page` return viewport elements; confirm rendered viewport intersection with `chrome_screenshot` when uncertain before classifying a CAPTCHA as active.
