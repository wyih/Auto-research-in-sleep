# Codex Native Chrome Adapter

Use this adapter only when the current runtime is Codex and the installed `chrome:control-chrome` capability is available. The user's explicit Chrome choice remains in force.

## Binding Rules

1. Invoke and follow the current `chrome:control-chrome` skill before browser work.
2. Use its native browser-client Chrome binding. Never route this adapter through an external MCP browser server.
3. Reuse an existing Chrome binding when present. Claim a relevant user tab or open a tab in the same Chrome profile.
4. Name the browser session when the current Chrome documentation requires it.
5. Use the native tab inspection, Playwright, or computer-input facilities documented by that skill.
6. Do not inspect cookies, local storage, passwords, profiles, or session stores.

## Semantic Mapping

| Contract operation | Codex action |
|---|---|
| `session.attach` | Reuse the native Chrome binding |
| `tab.list` | Enumerate open user Chrome tabs through the native binding |
| `tab.open_or_claim` | Claim the matching user tab or open a tab in Chrome |
| `page.inspect` | Capture fresh native DOM/page state |
| `page.navigate` | Navigate the claimed native Chrome tab |
| `element.act` | Use native locators first; use native computer input only when needed |
| `script.evaluate` | Evaluate through the native tab API when allowed by the current documentation |
| `download.wait` | Snapshot the approved landing directory, register the native download event before the final click, then await completion; on timeout use only the contract's narrow directory-increment fallback |
| `session.release` | Finalize/release tabs according to the current Chrome documentation |

## Acceptance Evidence

Set `adapter: codex_native_chrome` only when the operation actually ran through this binding. Record the final page URL or title in the local acceptance log when it is non-sensitive, plus the verified artifact path, size, and hash. A generic web fetch or an MCP trace is not a Codex-native pass.

If Chrome is unavailable or authentication blocks navigation, follow the current Chrome skill's recovery or human sign-in protocol. Do not switch browsers without user approval.

For challenge detection, native semantic snapshots may expose offscreen components and locator `isVisible()` may still return true. Inspect the rendered bounding rectangle/viewport intersection (and a screenshot when uncertain) before classifying a CAPTCHA as active.
