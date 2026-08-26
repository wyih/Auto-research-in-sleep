# Kimi WebBridge Adapter

Use this adapter only when the current runtime is Kimi Code and the user-level `kimi-webbridge` skill is installed. It drives the user's real browser — with the user's existing login sessions — through a local daemon at `http://127.0.0.1:10086`. The user's explicit browser choice remains in force. When the host is Codex, use [codex-chrome.md](codex-chrome.md) instead; never mix the two bindings in one operation.

## Binding Rules

1. Follow the current `kimi-webbridge` skill before browser work. Every command is a POST to `http://127.0.0.1:10086/command` with a top-level `session` naming the task.
2. Pick one session name at the task's start, put it on every command, and never switch mid-task.
3. If the daemon is unreachable (connection refused), start it once with `~/.kimi-webbridge/bin/kimi-webbridge start` (macOS/Linux) and retry. Never run `stop`, `restart`, or `uninstall` automatically.
4. Claim a relevant user tab with `find_tab` (`active:true` borrows the tab the user is viewing) or open one with `navigate` (`newTab:true`).
5. Never route this adapter through a standalone Playwright, a clean profile, or any other browser backend.
6. Do not inspect cookies, local storage, passwords, profiles, or session stores. `evaluate` must not be used to read `document.cookie`, storage APIs, or credential fields.
7. Serialize protected browser work against this user profile. Release the session (stop issuing commands; leave tabs open) before another project takes its browser turn.

## Semantic Mapping

| Contract operation | Kimi WebBridge action |
|---|---|
| `session.attach` | Confirm the daemon answers at `http://127.0.0.1:10086`; start it once if connection is refused |
| `tab.list` | `list_tabs` for this session's tabs |
| `tab.open_or_claim` | `find_tab` (with `active:true` to borrow the user's current tab) or `navigate` with `newTab:true` |
| `page.inspect` | `snapshot` (accessibility tree with `@e` refs); `screenshot` when the rendered state is uncertain |
| `page.navigate` | `navigate` to the approved URL |
| `page.reload` | `evaluate` `location.reload()` once, wait for settle, then `snapshot` |
| `element.act` | `click` / `fill` on `@e` refs from the snapshot first; `evaluate` only for targets without refs or missing attributes |
| `auth.submit_saved` | With user authorization, `click` the already-populated login form's submit control once without inspecting values |
| `auth.recover_soft_timeout` | `click` only the recipe-identified close control, reload once, then `snapshot` the post-reload auth state before any login action |
| `script.evaluate` | `evaluate` (wrap in an IIFE; compact `JSON.stringify`) when allowed by the recipe |
| `download.wait` | No native download event exists: snapshot the approved landing directory before the final click, then use only the contract's narrow `fallback_directory_increment` completion mode |
| `artifact.verify` | `<skill-dir>/scripts/verify_download.py` plus caller-specific checks |
| `human.handoff` | Pause in the same tab for login, MFA, account choice, or hard challenge; resume only on user confirmation plus fresh `snapshot` |
| `session.release` | Stop issuing commands. Call `close_session` only when the user explicitly asks |

## Acceptance Evidence

Set `adapter: kimi_webbridge` only when the operation actually ran through this binding. Record the binding fields `mcp_server: local_daemon`, `implementation: kimi_webbridge`, and `profile_mode: user_browser`, plus the final page URL or title in the local acceptance log when it is non-sensitive, and the verified artifact path, size, and hash. A generic web fetch or a curl-only trace without browser interaction is not a WebBridge pass.

If the daemon or extension is unavailable, or authentication blocks navigation, follow the `kimi-webbridge` recovery or human sign-in protocol. Do not switch browsers without user approval.

For a recipe-identified soft-timeout overlay, do not click its re-login button. Close the overlay, reload once through the daemon, and inspect first; enter login/handoff only when the fresh page still proves it necessary.

For challenge detection, the `snapshot` accessibility tree may expose offscreen components. Confirm the rendered bounding rectangle/viewport intersection — take a `screenshot` when uncertain — before classifying a CAPTCHA as active.

## Known Limits

- `click`/`fill` fire synthetic events (`isTrusted=false`). Sites that strictly require trusted input (some banking portals, captchas) ignore them: hand off to the user in the same tab.
- Cross-origin iframes are out of reach for `snapshot`/`click`/`fill`/`evaluate`; navigate to the iframe URL directly when the recipe requires it.
- There is no download-event hook, so every download completion uses the contract's directory-increment fallback with the deterministic verifier. Never accept a click, toast, or notification as download proof.
