# Codex Native Chrome Adapter

Use this adapter under Codex with the app-provided Computer Use tools connected to Chrome, or the legacy `chrome:control-chrome` skill when its native binding is actually available. Discover capability from callable tools and their returned documentation; an absent old skill name is insufficient to diagnose a connection failure. The user's explicit Chrome choice remains in force. Kimi Code uses [kimi-webbridge.md](kimi-webbridge.md).

## Choose the available binding

Reuse an established, working Chrome binding for this task. Otherwise select one of the paths actually exposed by the current environment:

| Environment | Entry path |
|---|---|
| Current CUA tools are callable | Use `mcp__cua_repl` and its documented `cua` entrypoints to select Chrome. The first call contains one entrypoint only; read its returned documentation before acting. Resolve existing tabs through the supported inventory, and follow the binding's session naming and cleanup rules. |
| Legacy Chrome skill and runtime are callable | Read the installed `chrome:control-chrome` SKILL.md and use its documented native browser-client binding, bootstrap, and APIs. |

If only one path is available, use that path. If both are available, reuse the established binding; when none is established, use the current CUA path. If one fails, inspect its documented troubleshooting guidance and the actual failure. Switch to the other only if it is available, it preserves the authorized Chrome profile, and no write or download is pending with an uncertain result. Never replay an uncertain action just to test the other binding.

Do not infer an API from the other path or hardcode plugin-cache versions. If neither path can connect, report the specific missing capability and continue independent work. A missing old skill may reflect packaging, rollout, or a fault; this adapter does not assume which cause applies.

## Current CUA entry and instance selection

Follow the live tool's entrypoint rules; the first invocation after initialization or reset contains exactly one entrypoint. An explicit tab mention takes precedence: pass its complete `plugin://...` URL to `cua.getTab({ mention: ... })`. For an existing tab identified by URL or live tab ID, use the documented `cua.getTab` form with the requested browser. For opening a URL in a named browser, use `cua.createBrowserTab` with the documented session options. Use `cua.getState()` when browser inventory is needed, then read the returned API documentation before continuing. After context compaction, restore documentation with `cua.rewriteDocumentation()` before continuing UI work.

When the user names a particular Chrome instance, resolve that choice from live browser inventory before selecting a tab. Match user-provided aliases against current profile/extension metadata; saved extension IDs are hints, and numeric browser/tab IDs must come from the current inventory. A Chrome profile name does not establish the website account. Verify the relevant URL/account when needed, without reading credential values. If the requested instance is absent, report it as unconnected and investigate that connection; do not silently use another instance or infer that no other Chrome process exists.

Reuse the selected browser binding across turns. A stale tab calls for a fresh tab in that browser, not a new browser selection. Follow the binding's session naming requirement before opening or claiming tabs, and its cleanup/marking rules when finishing.

## Binding Rules

1. Follow the selected binding's current documentation. Under the legacy path, invoke and follow the installed `chrome:control-chrome` skill before browser work.
2. Use native Chrome through that binding. The app-provided CUA tool is supported; arbitrary external browser MCP servers, standalone Playwright profiles, and third-party bridges are not this adapter. The in-app browser has a separate profile and cannot substitute for an existing Chrome login.
3. Reuse an existing Chrome binding when present. Claim a relevant user tab or open a tab in the same Chrome profile.
4. Name the browser session when the current Chrome documentation requires it.
5. For current CUA, prefer accessibility (AX) state and element-index actions for ordinary tasks. Refresh AX state after actions before deciding the next step. Use the binding's documented Playwright locators when AX is unavailable or repetitive work benefits from them; use screenshots and native coordinate actions when visual controls require them. Ground each action in fresh state. Read-only DOM evaluation cannot replace interaction APIs or make authenticated network requests.
6. Do not inspect cookies, local storage, passwords, browser profile files, or session stores.
7. Serialize protected Chrome work against this user profile. Do not dispatch multiple Codex agents or projects to mutate its tabs concurrently. Release or finalize the native session before another project takes its browser turn.

## Semantic Mapping

| Contract operation | Codex action |
|---|---|
| `session.attach` | Reuse the native Chrome binding |
| `tab.list` | Enumerate open user Chrome tabs through the native binding |
| `tab.open_or_claim` | Claim the matching user tab or open a tab in Chrome |
| `page.inspect` | Read fresh AX state, or the binding's documented DOM/screenshot representation for the task |
| `page.navigate` | Navigate the claimed native Chrome tab |
| `page.reload` | Reload the claimed native Chrome tab once and wait for settled state |
| `element.act` | Use supported AX actions, documented locators for suitable tasks, or native visual controls; then inspect the resulting state |
| `auth.recover_soft_timeout` | Freshly inspect and click only the recipe-identified close control, reload once, then inspect the post-reload auth state before any login action |
| `script.evaluate` | Use documented read-only DOM evaluation for page inspection; never extract session material or mutate the page through it |
| `download.wait` | Inspect the documented event and file-saving capabilities separately; verify actual disk completion through the shared contract |
| `session.release` | Finalize/release tabs according to the current Chrome documentation |

## Download capability

The inspected CUA Chrome API exposes `tab.playwright.waitForEvent("download")`, but its `PlaywrightDownload` interface documents no `saveAs()` or `path()` methods. Check the current returned documentation each run; never import the standalone Playwright download API by assumption. When supported, arm the event before the click, but use the shared contract's directory completion when no file-saving/path API is available. An event alone is not a completed local artifact.

For a failed direct or automated download, use [the shared native recovery rules](browser-session-contract.md#native-download-recovery), including the visible PDF viewer controls or ChatGPT Library when relevant. Use only operations advertised by the selected binding; site recipes cannot require an undocumented fixed PDF/wrapper action.

## Acceptance Evidence

Set `client_runtime: codex` and `adapter: codex_native_chrome` only when the operation actually used native Chrome. Record which path ran and the actual `mcp_server`/`implementation`, with `profile_mode: existing_user_chrome`; do not copy runtime identifiers from the other path. Keep the non-sensitive final page URL/title, verified artifact path, size, hash, and caller-specific verification in the acquisition evidence. Generic HTTP fetching does not establish use of the Chrome session.

If Chrome is unavailable or authentication blocks navigation, follow the selected binding's recovery or human sign-in protocol. Do not switch browsers or profiles without user authorization. Continue independent work while a dependent operation waits.

For a recipe-identified soft-timeout overlay, do not click its re-login button. Close the overlay, reload once through the native binding, and inspect first; enter login/handoff only when the fresh page still proves it necessary.

For challenge detection, native semantic snapshots may expose offscreen components and locator `isVisible()` may still return true. Inspect the rendered bounding rectangle/viewport intersection (and a screenshot when uncertain) before classifying a CAPTCHA as active.
