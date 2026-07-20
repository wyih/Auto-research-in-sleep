# Authenticated Browser Session Contract

This contract separates stable research intent from runtime-specific browser tool names. Calling skills own site navigation and business filters; `browser-session-bridge` owns runtime selection, login-state reuse, download completion, and artifact verification.

## Semantic Operations

| Operation | Required behavior | Success evidence |
|---|---|---|
| `session.attach` | Connect to the selected authorized persistent Chrome profile | Adapter identity, implementation, profile mode, and available tab context |
| `tab.list` | Enumerate open tabs without inspecting private storage | Titles/URLs needed for target selection only |
| `tab.open_or_claim` | Reuse a suitable tab or open one in the same profile | Active target tab |
| `page.inspect` | Read fresh visible/DOM state | Page title, URL, and actionable controls |
| `page.navigate` | Navigate the active tab | Fresh state at the expected destination |
| `page.reload` | Reload the active tab once, or navigate once to the same recipe-approved stable URL when the adapter has no native reload primitive | Fresh settled state from the same site without entering a credential flow |
| `element.act` | Click, type, select, or scroll through supported UI controls | Resulting page/UI state |
| `auth.submit_saved` | With user authorization, click one normal login/continue control when Chrome has already populated the form; never inspect, extract, copy, or type credential values | Fresh authenticated state after the click |
| `auth.recover_soft_timeout` | When a site recipe identifies a dismissible inactivity/auto-logout overlay on a persistent-session or IP-authenticated portal, click only its non-destructive close control, call `page.reload` once, wait, and inspect before entering any login branch; never choose the overlay's re-login action during this probe | `dismiss_refresh_restored` or `dismiss_refresh_still_logged_out`, backed by fresh post-reload page evidence |
| `script.evaluate` | Run only adapter-owned fixed, bounded, non-secret probes when semantic inspection is insufficient; never accept caller-supplied code | Redacted fixed-shape return value |
| `download.wait` | Snapshot the controlled landing directory and arm runtime completion handling before the final download action | Completed new/stabilized local file, not a notification alone |
| `human.handoff` | Pause for login or hard challenge in the same tab | User confirmation plus fresh authenticated state |
| `artifact.verify` | Verify content, size, hash, and caller-specific schema | Deterministic verifier pass plus domain checks |
| `session.release` | Release browser resources without closing user tabs unnecessarily | Runtime cleanup completed |

## Invariants

- Never read or emit cookies, local storage, credentials, session tokens, auth headers, or password-manager data.
- Freeze one adapter, implementation, MCP server, and profile mode before the first browser action. Never splice multiple browser backends into one success receipt.
- One persistent browser profile has at most one active controller across projects and processes. Use a runtime-enforced hard lease where available; otherwise the orchestrator must serialize protected browser work and must not dispatch concurrent controllers against that profile. Hold ownership through download landing/copy verification, then release it before local analysis or public-web work. Selected tabs, foreground state, and prose coordination files are not ownership proof.
- `auth.submit_saved` is a submit-only operation: do not read form values or password-manager UI, do not fill missing fields, and do not retry after an error. Empty fields, MFA, account choice requiring identity disclosure, or a hard challenge require `human.handoff`.
- A visible inactivity/auto-logout overlay is not by itself proof that the underlying browser or institutional-IP session is unusable. When the site recipe classifies it as a soft timeout, run `auth.recover_soft_timeout` exactly once before `auth.submit_saved`, `human.handoff`, or `access_denied`. Reacquire controls after the close and reload; never create a recovery loop or assume that pre-refresh form filters survived.
- Never treat successful navigation, HTTP status, a button click, or a `.pdf`/`.xlsx` extension as download success.
- Re-inspect after every navigation, authentication transition, modal transition, or challenge completion.
- Classify a CAPTCHA as active only when its rendered box intersects the current viewport and it blocks the intended action. DOM text, preloaded markup, or a locator-level `isVisible()` result alone is insufficient; record hidden/offscreen challenge components as non-blocking observations.
- Keep one site recipe usable across runtimes; do not place MCP or Codex-native tool names in site recipes.
- Credential entry and hard CAPTCHA completion are explicit handoffs, not agent failures and not automation targets. A user-authorized submit of Chrome-autofilled credentials is the narrow exception above; it is not credential entry. An ordinary rendered checkbox challenge may be clicked once only after the user confirms that already-observed challenge at action time; reacquire and re-inspect immediately afterward.
- Access denial remains a documented access gap; do not bypass subscriptions or institutional controls.
- One runtime pass cannot stand in for another runtime's acceptance.

## Download Completion Fallback

Runtime download events are preferred but are not universal. Before the final click, record a narrow inventory of the caller-approved landing directory (names, sizes, and modification times). If the armed event times out:

1. inspect only that directory for a new file or a file modified after the click;
2. require a plausible expected filename/extension and a modification time within the operation window;
3. poll until the size is stable and no partial-download suffix remains;
4. run the same deterministic verifier and caller identity/schema checks;
5. record `download_event=timeout` and `completion=fallback_directory_increment` in the receipt.

Do not search the whole home directory, accept an old matching file, or downgrade verification because the event was absent.

## Artifact Gate

The runtime bridge verifies generic file integrity. The caller must additionally verify domain meaning:

| Artifact | Generic gate | Caller gate |
|---|---|---|
| Paper PDF | `%PDF`, EOF marker, minimum size, SHA-256 | Correct title/article and readable method content |
| XLSX export | Valid ZIP/XLSX structure, minimum size, SHA-256 | Expected fields, periods, grain, and non-empty rows |
| CSV export | Text/delimiter sanity, non-empty, SHA-256 | Expected header, filters, grain, and plausible rows |
| ZIP bundle | Valid archive and members, SHA-256 | Expected vendor files and no truncation |

## Redacted Receipt

Each operation returns adapter, implementation, MCP server, profile mode, site, session reuse, `session_recovery: not_needed|dismiss_refresh_restored|dismiss_refresh_still_logged_out`, `saved_login_submitted: true|false`, login-state category, operation, artifact path, expected format, size, hash, verification status, and blocker. `saved_login_submitted` records only that the authorized submit-only transition occurred; it never records form values, account identity, or password-manager state. It omits all authentication material and account identifiers.
