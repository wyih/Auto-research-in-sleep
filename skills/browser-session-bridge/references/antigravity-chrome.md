# Antigravity Native Browser Adapter

Use this adapter only when the current runtime is Google Antigravity and its official native browser capability — the built-in Browser Subagent (`/browser`, `browser_*` tools) or the official Chrome DevTools plugin (`antigravity-plugins-official/plugin/chrome-devtools-plugin`) — is available. Under Codex use [codex-chrome.md](codex-chrome.md); under Kimi Code use [kimi-webbridge.md](kimi-webbridge.md); under Claude Code use [claude-in-chrome.md](claude-in-chrome.md). Never mix bindings in one operation.

## Availability And Official-Only Boundary

- Antigravity provides official browser automation through its built-in **Browser Subagent** (`/browser` workflow and `browser_*` tools) and the official **Chrome DevTools** plugin (`antigravity-plugins-official/plugin/chrome-devtools-plugin`).
- **Never use third-party browser MCP servers** (such as `mcp-chrome-bridge`, community extension bridges, or standalone Playwright MCP servers), even if they are mounted in the user's global `mcp_config.json`.
- By default, Antigravity's Browser Subagent may launch a separate, neutral Chrome profile to isolate automation. A neutral profile does not inherit the user's personal sign-ins:
  - When the official Chrome DevTools plugin or Browser Subagent is attached to the user's authorized Chrome session (`existing_user_chrome`), reuse that session's existing sign-ins.
  - When the Browser Subagent opens an isolated profile that lacks the user's login state, either pause via `human.handoff` so the user can complete one-time sign-in in that tab, or record `browser_unavailable` / `data_access_gap` if the operation requires an already signed-in personal profile that cannot be attached. Never fall back to a third-party MCP bridge to read the user's browser.

## Binding Rules

1. Use only Antigravity's official native Browser Subagent (`/browser` delegation, `browser_*` primitives such as `browser_navigate`, `browser_read`, `browser_click`) or the official `antigravity-plugins-official/plugin/chrome-devtools-plugin`.
2. Respect the user's explicit browser and account choice. Verify identity when the account matters: inspect only the target site's own visible account indicator without reading unrelated private content.
3. Do not read cookies, local storage, passwords, browser profile files, or session stores. Any DOM inspection must remain read-only as allowed by the caller's site recipe; never extract `document.cookie`, storage APIs, or credential fields, or make authenticated network requests through script evaluation.
4. Serialize protected browser work against the selected profile. Do not dispatch multiple subagents or projects to mutate its tabs concurrently.

## Semantic Mapping

| Contract operation | Antigravity native browser action |
|---|---|
| `session.attach` | Attach through the official Browser Subagent (`/browser`) or official `chrome-devtools-plugin` to the authorized Chrome instance |
| `tab.list` | Inspect open tabs in the attached official browser session |
| `tab.open_or_claim` | Reuse a matching tab or open/navigate a tab in the same official session (`browser_navigate`) |
| `page.inspect` | `browser_read` (DOM / accessibility / text state) and native screenshot capture when rendered state is uncertain |
| `page.navigate` | `browser_navigate` to the approved URL |
| `page.reload` | Reload the same approved URL once, wait for settled state, then inspect |
| `element.act` | `browser_click` and supported native input/form controls on non-credential elements; re-inspect afterward |
| `auth.submit_saved` | Not used under Antigravity; route to `human.handoff` |
| `auth.recover_soft_timeout` | Click only the recipe-identified close control, reload once, then inspect before any login branch |
| `script.evaluate` | Read-only DOM inspection through the official browser subagent when the recipe allows it |
| `download.wait` | Snapshot the landing directory before the final click and verify disk completion via `fallback_directory_increment` |
| `artifact.verify` | `<skill-dir>/scripts/verify_download.py` plus caller-specific checks |
| `human.handoff` | Pause in the same tab, tell the user exactly what to complete (login, MFA, account choice, hard challenge, download-warning override), and resume only after their confirmation and a fresh inspection |
| `session.release` | Stop issuing commands; close only temporary tabs opened by this operation, never the user's tabs |

## Landing Directory And Sandbox Boundary

Chrome saves to its configured download directory, usually `~/Downloads`. Because Antigravity's `run_command` executes inside a workspace-scoped sandbox by default (`BypassSandbox: false`), any shell step that snapshots `~/Downloads` or moves a verified download from `~/Downloads` into the project deliverable directory must run as a minimal single command with `BypassSandbox: true`, while local verification and processing inside the workspace remain sandboxed (`BypassSandbox: false`). Record only names, sizes, and modification times in the landing directory before the final click, apply the contract's `fallback_directory_increment` completion, and move the verified file to the requested project directory.

## Acceptance Evidence

Set `client_runtime: antigravity` and `adapter: antigravity_chrome` only when the operation actually ran through Antigravity's official native browser binding, with `mcp_server: native`, `implementation: antigravity_browser_subagent`, and `profile_mode: existing_user_chrome`. Keep the non-sensitive final page URL or title, the verified artifact path, size, and hash, and the caller-specific verification. A generic web search/fetch, `curl` trace, or third-party MCP browser call is not an Antigravity native browser pass.

## Known Limits

- Antigravity's Browser Subagent pauses at login pages and CAPTCHAs for the user; login submission always goes to `human.handoff`, including forms Chrome has already populated.
- When the Browser Subagent runs in an isolated neutral profile without the user's existing login session and the user does not sign in via `human.handoff`, record `browser_unavailable` or `data_access_gap` rather than invoking any third-party MCP bridge.
- Confirm rendered viewport intersection (using a screenshot from the Browser Subagent when uncertain) before classifying a CAPTCHA as active.
