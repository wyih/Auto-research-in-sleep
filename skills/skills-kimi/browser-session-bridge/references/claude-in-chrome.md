# Claude in Chrome Adapter

Use this adapter only when the current runtime is Claude Code and its Claude in Chrome integration is connected. It drives the user's real Chrome (or another supported Chromium browser) through the Claude in Chrome extension, reusing that profile's existing sign-ins. The user's explicit browser choice remains in force. Under Codex use [codex-chrome.md](codex-chrome.md); under Kimi Code use [kimi-webbridge.md](kimi-webbridge.md). Never mix bindings in one operation.

## Availability

- Claude in Chrome requires a Claude Code session signed in through `/login` with a claude.ai plan (Pro, Max, Team, or Enterprise), the Claude in Chrome extension, and Chrome integration enabled with `claude --chrome` or `/chrome` → "Enabled by default".
- Sessions authenticated by an API key or a `claude setup-token` token, and sessions running only through Bedrock, Vertex, or Foundry, have no Chrome integration. Record `browser_unavailable` for the protected route; do not substitute another backend.
- The Claude desktop app's built-in browser pane keeps its own sign-ins and is not this binding.

## Binding Rules

1. The browser tools are `mcp__claude-in-chrome__*` and may be deferred. Load the needed set in one ToolSearch call before the first browser step, and follow Claude Code's Chrome tool guidance when it is shown.
2. Resolve the browser instance before acting. `list_connected_browsers` returns each connected extension's live `deviceId` and display name. Match the user's requested instance against that live list; saved names and device IDs are hints. When the user named the instance, `select_browser` its live `deviceId`. When several browsers are connected and the user has not chosen one, ask the user or use `switch_browser` so they confirm inside Chrome; never pick one yourself. If the requested instance is absent, report it as unconnected and do not use another browser.
3. Verify identity when the account matters: a Chrome profile name does not establish the website account. Inspect only the site's own account indicator; do not read unrelated private content.
4. Call `tabs_context_mcp` first; `createIfEmpty: true` opens this session's tab group. The binding sees only tabs in that group, so open a new tab there and navigate it to the approved URL. It shares the profile's login state with the user's other tabs.
5. Do not read cookies, local storage, passwords, browser profile files, or session stores. `javascript_tool` is for read-only DOM inspection allowed by the recipe; never use it to read `document.cookie`, storage APIs, or credential fields, or to make authenticated network requests.
6. Do not trigger JavaScript `alert`, `confirm`, or `prompt` dialogs; they block the extension until the user dismisses them.
7. Serialize protected browser work against the selected profile. Do not dispatch several agents or projects to mutate its tabs concurrently.

## Semantic Mapping

| Contract operation | Claude in Chrome action |
|---|---|
| `session.attach` | Load the tools; `list_connected_browsers` then `select_browser` when an instance must be chosen |
| `tab.list` | `tabs_context_mcp` |
| `tab.open_or_claim` | `tabs_create_mcp` (or the empty tab from `tabs_context_mcp` with `createIfEmpty`), then `navigate` |
| `page.inspect` | `read_page` (accessibility tree with `ref` IDs), `find`, or `get_page_text`; a `computer` screenshot when rendered state is uncertain |
| `page.navigate` | `navigate` to the approved URL |
| `page.reload` | `navigate` to the same URL once, wait for settle, then inspect |
| `element.act` | `computer` click/type/scroll on a `ref` or screenshot coordinate, or `form_input` for non-credential fields; re-inspect afterward |
| `auth.submit_saved` | Not used under Claude Code; route to `human.handoff` |
| `auth.recover_soft_timeout` | Click only the recipe-identified close control, reload once, then inspect before any login branch |
| `script.evaluate` | `javascript_tool`, read-only, when the recipe allows it |
| `download.wait` | No download event is exposed: snapshot the landing directory before the final click and use the contract's `fallback_directory_increment` completion |
| `artifact.verify` | `<skill-dir>/scripts/verify_download.py` plus caller-specific checks |
| `human.handoff` | Stop in the same tab, tell the user exactly what to complete (login, MFA, account choice, hard challenge, download-warning override, site permission), and resume only after their confirmation and a fresh inspection |
| `session.release` | Stop issuing commands; close only tabs this operation opened (`tabs_close_mcp`), never the user's tabs |

## Site Permissions

The extension's per-site permissions apply. A DOM-reading tool can return `Permission denied for reading pages on this domain` even on a public page while navigation and screenshots still work. Record `site_permission_required`; when the recipe needs DOM state or refs, ask the user to allow the site in the extension or approve Claude Code's `Claude in Chrome wants to` prompt. Screenshot inspection may confirm visible state that the extension permits. A denial is a channel result, not a reason to switch backends.

## Landing Directory

Chrome saves to its configured download directory, usually `~/Downloads`. Confirm it from where a verified file actually lands or from the browser's own download UI; do not read Chrome profile files. Record only names, sizes, and modification times there before the final click, apply the contract's directory-increment completion, then move the verified file to the requested landing directory.

## Acceptance Evidence

Set `client_runtime: claude_code` and `adapter: claude_in_chrome` only when the operation actually ran through this binding, with `mcp_server: claude-in-chrome`, `implementation: claude_in_chrome_extension`, and `profile_mode: existing_user_chrome`. Keep the non-sensitive final page URL or title, the verified artifact path, size, and hash, and the caller-specific verification. A WebFetch result, `curl` trace, or other HTTP fetch without browser interaction is not a Claude in Chrome pass.

## Known Limits

- Claude in Chrome pauses at login pages and CAPTCHAs for the user; login submission always goes to `human.handoff`, including forms Chrome has already populated.
- Some sites ignore automated input or require trusted user gestures; hand those steps to the user in the same tab.
- Accessibility snapshots may expose offscreen components. Confirm the rendered viewport intersection, with a screenshot when uncertain, before classifying a CAPTCHA as active.
- If the extension stops responding after idle time, the user runs `/chrome` → "Reconnect extension". Chrome integration is unavailable under WSL.
