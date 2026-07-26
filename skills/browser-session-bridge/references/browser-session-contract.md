# Codex Authenticated Browser Contract

## Semantic operations

| Operation | Required behavior | Success evidence |
|---|---|---|
| `session.attach` | Connect to the user's authorized Chrome profile through the native Codex binding | Binding and relevant tab context |
| `tab.open_or_claim` | Reuse a suitable tab or open one in the same profile | Active target tab |
| `page.inspect` | Read fresh visible or DOM state | Title, URL, and actionable controls |
| `page.navigate` | Navigate the claimed tab | Fresh state at the expected destination |
| `page.reload` | Reload the same approved page once | Fresh settled state without entering a credential flow |
| `element.act` | Use supported semantic controls; use native computer input only when necessary | Resulting page or UI state |
| `auth.submit_saved` | With user authorization, submit an already Chrome-populated form once without inspecting values | Fresh authenticated state |
| `auth.recover_soft_timeout` | Close only a recipe-identified soft-timeout overlay, reload once, and inspect | Restored session or fresh logged-out evidence |
| `download.wait` | Snapshot the approved directory and arm completion handling before the final click | New, complete, stabilized file |
| `human.handoff` | Pause for login, MFA, account choice, or hard challenge in the same tab | User confirmation plus fresh state |
| `artifact.verify` | Verify file structure, size, hash, and caller-specific meaning | Deterministic pass plus domain checks |
| `session.release` | Release control without closing user tabs unnecessarily | Native cleanup completed |

## Invariants

- Never read or emit cookies, local storage, credentials, session tokens, auth headers, or password-manager data.
- Use one native Chrome binding for the whole operation. Do not combine evidence from multiple browser backends.
- Serialize protected Chrome work against the user's profile. Do not let concurrent projects mutate its tabs.
- Re-inspect after every navigation, authentication transition, modal transition, or challenge completion.
- Treat a CAPTCHA as active only when its rendered box intersects the viewport and blocks the intended action.
- Keep site selectors and business filters in the calling skill's recipe, not in this bridge.
- Credential entry and hard CAPTCHA or challenge completion require user handoff. A user-authorized single submit of already populated fields is the only automated login transition.
- Access denial is a documented gap, not a reason to bypass controls.

## Download fallback

Before the final click, record names, sizes, and modification times only in the caller-approved landing directory. If the armed event times out:

1. inspect only that directory for a new file or one modified after the click;
2. require the expected name or extension and a modification time inside the operation window;
3. wait until size stabilizes and no partial-download suffix remains;
4. run the deterministic verifier and caller-specific identity or schema checks;
5. record `completion: fallback_directory_increment` in the receipt.

Do not search the home directory, accept an old matching file, or weaken verification because the event was absent.

## Artifact gates

| Artifact | Generic gate | Caller gate |
|---|---|---|
| PDF | `%PDF`, EOF marker, minimum size, SHA-256 | Correct paper or document and readable content |
| XLSX | Valid ZIP/XLSX structure, minimum size, SHA-256 | Expected fields, periods, grain, and non-empty rows |
| CSV | Text and delimiter sanity, non-empty, SHA-256 | Expected header, filters, grain, and plausible rows |
| ZIP | Valid archive and members, SHA-256 | Expected files and no truncation |
