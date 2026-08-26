---
name: browser-session-bridge
description: Reuse the user's authorized browser session from the host CLI — Codex's native Chrome plugin or Kimi Code's WebBridge — for authenticated web navigation and verified downloads. Use for CNKI, SSRN, ScienceDirect, Wiley, CSMAR, CNRDS, library portals, subscription pages, protected fields, interactive exports, or entitled downloads that require existing browser state. Route public pages to web-fetcher and open research-paper retrieval to fulltext-acquire first.
---

# Browser Session Bridge

Perform one authenticated browser operation through the host CLI's trusted browser binding, land the requested artifact, and return verifiable evidence. The selected model does not change the browser route: the host CLI alone selects the adapter.

`<skill-dir>` is the directory containing this file.

## Host-adaptive adapter selection

Exactly two adapters are trusted. Choose by the host CLI, never by convenience or model:

| Host CLI | Binding | `client_runtime` | `adapter` |
|---|---|---|---|
| Codex | `chrome:control-chrome` native Chrome plugin | `codex` | `codex_native_chrome` |
| Kimi Code | `kimi-webbridge` local daemon driving the user's real browser | `kimi` | `kimi_webbridge` |

Every other browser backend remains forbidden: standalone Playwright, a clean or automation-only profile, and any third-party browser bridge or MCP browser server. `kimi_webbridge` is a second trusted backend, not an opening for arbitrary ones.

## Required references

Read the shared contract and the adapter reference for the current host before acting:

- [references/browser-session-contract.md](references/browser-session-contract.md) for semantic operations and acceptance gates.
- [references/codex-chrome.md](references/codex-chrome.md) for the Codex native Chrome binding.
- [references/kimi-webbridge.md](references/kimi-webbridge.md) for the Kimi Code WebBridge binding.

## Admission gate

Use this skill only when the operation requires one of these recorded reasons:

- `authenticated_session`
- `protected_schema`
- `interactive_export`
- `entitled_download`
- `active_challenge`

Record the selected value as `browser_required_reason` before acquiring the browser.

Use `web-fetcher` for public page acquisition. Let `fulltext-acquire` try local and open-access paper routes before it calls this bridge. Convenience or generic web search is not a browser-session reason.

Use or rule out project-local evidence, then model-native web search/fetch, then bounded public API/direct-download routes. Acquire the authenticated browser only after those lighter channels are insufficient.

## Workflow

1. Freeze the target site, requested operation, filters, expected format, and landing directory.
2. Select the adapter for the current host CLI and load its binding: `chrome:control-chrome` under Codex, `kimi-webbridge` under Kimi Code. Do not substitute another browser backend, standalone Playwright, or another profile.
3. Reuse or claim one relevant user tab. Inspect visible page state without reading cookies, storage, credentials, auth headers, or password-manager data.
4. Classify the page as usable, logged out, access denied, or blocked by an active rendered challenge. Offscreen or preloaded challenge markup is not a blocker.
5. If a caller-approved site recipe identifies a soft timeout overlay, run `auth.recover_soft_timeout`: close only that overlay, reload the same stable page once, and inspect again before entering a login branch.
6. If the user has authorized submission and the browser has already populated a normal login form, click its login control once without reading or typing field values. Pause for the user when fields are empty, MFA or account choice is required, the attempt errors, or a hard CAPTCHA is active.
7. Execute only the caller's site recipe and minimal requested export or download.
8. Snapshot the approved landing directory and arm download handling before the final click. On event timeout — or under `kimi_webbridge`, which has no download event — use only the contract's narrow new-and-stabilized-file fallback.
9. Verify the landed file:

   ```bash
   python3 "<skill-dir>/scripts/verify_download.py" artifact.pdf --expect pdf --min-bytes 10240
   ```

10. Recheck caller-specific identity, columns, periods, grain, or content. Release the browser binding after verification.

## Receipt

Return the trusted pair for the host that actually ran: `client_runtime: codex` with `adapter: codex_native_chrome` under Codex, or `client_runtime: kimi` with `adapter: kimi_webbridge` under Kimi Code. Add the binding fields from the adapter reference (`mcp_server`, `implementation`, `profile_mode`), followed by the site, operation, browser-required reason, session reuse, login-state category, artifact path, expected format, size, SHA-256, generic verification result, caller-specific verification result, download completion mode, and blocker if any.

Never include cookies, tokens, account identifiers, raw IP addresses, auth headers, signed download URLs, or credential values.

## Stop conditions

- Do not automate credential entry or hard CAPTCHAs.
- Do not bypass subscriptions or institutional access controls.
- Do not accept a click, notification, file extension, or HTTP success as download proof.
- Do not switch browser backends inside one receipt.
- After two failures using the same route, change the route within the caller's allowed channels or report the blocker.
