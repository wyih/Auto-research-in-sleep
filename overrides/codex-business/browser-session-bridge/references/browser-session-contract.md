# Authenticated Browser Contract

This contract is host-adaptive. Exactly two bindings are trusted: `codex_native_chrome` (Codex, `client_runtime: codex`) and `kimi_webbridge` (Kimi Code, `client_runtime: kimi`). Any other browser backend — standalone Playwright, a clean profile, a third-party bridge — is forbidden regardless of host.

## Semantic operations

| Operation | Required behavior | Success evidence |
|---|---|---|
| `session.attach` | Connect to the user's authorized browser profile through the host CLI's trusted binding | Binding and relevant tab context |
| `tab.open_or_claim` | Reuse a suitable tab or open one in the same profile | Active target tab |
| `page.inspect` | Read fresh visible or DOM state | Title, URL, and actionable controls |
| `page.navigate` | Navigate the claimed tab | Fresh state at the expected destination |
| `page.reload` | Reload the same approved page once | Fresh settled state without entering a credential flow |
| `element.act` | Use the selected binding's supported AX/semantic controls or native visual input as appropriate | Resulting page or UI state |
| `auth.submit_saved` | With user authorization, submit an already Chrome-populated form once without inspecting values | Fresh authenticated state |
| `auth.recover_soft_timeout` | Close only a recipe-identified soft-timeout overlay, reload once, and inspect | Restored session or fresh logged-out evidence |
| `download.wait` | Use documented completion handling; snapshot the approved directory before clicking when a filesystem fallback may be needed | New, complete, stabilized file |
| `human.handoff` | Pause for login, MFA, account choice, or hard challenge in the same tab | User confirmation plus fresh state |
| `artifact.verify` | Verify file structure, size, hash, and caller-specific meaning | Deterministic pass plus domain checks |
| `session.release` | Release control without closing user tabs unnecessarily | Native cleanup completed |

## Invariants

- Never read or emit cookies, local storage, credentials, session tokens, auth headers, or password-manager data.
- Use one trusted browser binding for the whole operation. Do not combine evidence from multiple browser backends.
- Serialize protected browser work against the user's profile. Do not let concurrent projects mutate its tabs.
- Re-inspect after every navigation, authentication transition, modal transition, or challenge completion.
- Treat a CAPTCHA as active only when its rendered box intersects the viewport and blocks the intended action.
- Keep site selectors and business filters in the calling skill's recipe, not in this bridge.
- Credential entry and hard CAPTCHA or challenge completion require user handoff. A user-authorized single submit of already populated fields is the only automated login transition.
- Access denial is a documented gap, not a reason to bypass controls.

## Download fallback

Before the final click, establish the browser's actual landing directory for this operation and record only names, sizes, and modification times there. A task's final deliverable folder does not automatically change where Chrome downloads. Use this fallback if the binding exposes no completion event, an armed event times out, or the event has no documented file-saving/path API:

1. inspect only that directory for a new file or one modified after the click;
2. require the expected name or extension and a modification time inside the operation window;
3. wait until size stabilizes and no partial-download suffix remains;
4. run the deterministic verifier and caller-specific identity or schema checks;
5. record `completion: fallback_directory_increment` in the receipt.

If an event was observed, record that separately; directory-based completion does not imply that no event occurred. After verification, place the file in the requested deliverable directory without overwriting unrelated files and confirm the final path. Do not search the home directory, accept an old matching file, or weaken verification because the event was absent.

## Native download recovery

When a download click leaves no completed file, inspect the same browser's download panel/history and native UI before repeating it or treating an event timeout as failure. Chrome can conditionally flag uncommon, suspicious, dangerous, unverified, or insecure downloads; record the actual displayed reason for the matching file. A normal Save/Save As confirmation is part of the authorized download. A browser security-warning override such as Keep/Download anyway requires user handoff under the current Computer Use policy: retain the relevant page, explain the warning, and let the user perform the override. Then resume disk-completion and content verification. This check does not require a warning on every download. See [Google's download-warning explanation](https://support.google.com/chrome/answer/6261569).

If an authorized direct or automated download fails (for example, `ERR_BLOCKED_BY_CLIENT`), inspect the actual failure and try an appropriate visible native download control in the same browser instance and website account before reporting a blocker. Check for an already landed file before retrying an uncertain download. Use the site's file menu, preview Download button, library, or export panel as available; a rendered PDF viewer's native Download control is a valid route. Read fresh UI state and use the selected binding's supported actions.

For ChatGPT-generated files, use **Library / 资料库 → search the exact filename → file action menu → Download / 下载**, or the preview's native Download button. This recovery applies whether or not Oracle generated the file. Continue through normal site controls; an actual access restriction or browser security warning requires its applicable handoff, not a workaround. If native recovery also fails, report the specific remaining blocker and attempted routes.

Completion requires the file saved on disk with its expected type and contents verified; ZIP files must pass archive integrity checks. A click, event, toast, or preview alone does not satisfy completion.

## Artifact gates

| Artifact | Generic gate | Caller gate |
|---|---|---|
| PDF | `%PDF`, EOF marker, minimum size, SHA-256 | Correct paper or document and readable content |
| XLSX | Valid ZIP/XLSX structure, minimum size, SHA-256 | Expected fields, periods, grain, and non-empty rows |
| CSV | Text and delimiter sanity, non-empty, SHA-256 | Expected header, filters, grain, and plausible rows |
| ZIP | Valid archive and members, SHA-256 | Expected files and no truncation |
