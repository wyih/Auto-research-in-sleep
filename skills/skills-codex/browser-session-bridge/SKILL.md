---
name: browser-session-bridge
description: Reuse an authorized browser session for authenticated web navigation and verified downloads across Codex, Grok, OpenClaw, and OpenCode/OpenScience. Use for CNKI, SSRN, ScienceDirect, Wiley, CSMAR, CNRDS, library portals, or other protected sites when Codex should use native Chrome, parallel non-Codex agents on macOS may use isolated ego lite Task Spaces, an MCP-capable runtime should use the official Chrome DevTools MCP through the project safety facade, or Grok needs the legacy real-Chrome bridge as an explicitly recorded fallback.
---

# Browser Session Bridge

Execute one authenticated browser operation through the current runtime while preserving a platform-neutral site recipe and a verifiable local artifact.

## Required Inputs

- target site and intended operation
- site recipe supplied by the calling skill
- expected artifact type and landing directory
- any search, date, universe, or field filters
- `browser_required_reason`: `authenticated_session` | `protected_schema` | `interactive_export` | `entitled_download` | `active_challenge`

Read `../shared-references/browser-session-contract.md` before execution. Read `../shared-references/business-helper-resolution.md` before invoking the verifier outside the ARIS repository. Then read exactly one runtime adapter:

- Codex with native Chrome available: `references/codex-chrome.md`
- Grok, OpenClaw, or OpenCode/OpenScience on macOS with onboarded ego lite: `references/ego-lite.md`
- Grok primary path with the official `chrome-devtools-mcp` and dedicated persistent profile: `references/grok-chrome-devtools-mcp.md`
- OpenCode/OpenScience with the same safe facade exposed as a native OpenCode MCP server: `references/grok-chrome-devtools-mcp.md`
- Grok fallback path with the legacy real-Chrome bridge: `references/grok-chrome-mcp.md`

Do not infer a runtime from the provider/model name or prose alone. In particular, a Grok model running inside OpenCode is still `client_runtime: opencode`, not Grok Build. Select from the client and capabilities actually available in the current session.

## Admission Gate

Invoke this bridge only after the caller has used or ruled out project-local evidence, model-native web search/fetch, and a bounded public API/direct-download path. If those lighter channels answer the discovery question or land the required open artifact, return without acquiring a browser lease. A browser is justified only by the recorded `browser_required_reason`; convenience or generic web search is not sufficient.

Public web evidence may identify a candidate page, table, or paper. It does not prove current authenticated access, live subscription state, protected field availability, or completion of a portal export.

## Runtime Gate

| Runtime | Required path | Forbidden substitution |
|---|---|---|
| Codex | Installed `chrome:control-chrome` capability and its native browser client | External Chrome MCP, standalone Playwright, or a separate browser profile |
| Grok / OpenClaw / OpenCode with ego lite (macOS only) | `uname -s` is exactly `Darwin`; installed `ego-browser` Skill and CLI; one uniquely named agent-owned Task Space per run | Selecting or installing ego lite on Windows, WSL, or native Linux; sharing a Task Space across concurrent runs; claiming another run's space; or mixing ego lite with another adapter in one receipt |
| Grok primary | Project safety facade backed by healthy official `chrome-devtools-mcp`, registered as `browser`, using the dedicated visible persistent profile | Raw official MCP tools, a temporary/headless profile, or the legacy adapter identity |
| OpenCode / OpenScience | Project safety facade backed by healthy official `chrome-devtools-mcp`, registered in the current OpenCode runtime as `browser`, using the dedicated visible persistent profile | Running `grok mcp`, choosing an adapter from the model vendor, raw CDP/DevTools HTTP, ad hoc browser scripts, or silently switching to the legacy real-Chrome bridge |
| Grok fallback | Healthy legacy `chrome-mcp` connected to the user's real Chrome, selected before the run because existing real-Chrome state is required | Claiming the result as the official DevTools adapter or changing adapters mid-receipt |

Keep Codex on native Chrome. On macOS, Grok, OpenClaw, and OpenCode may prefer ego lite when it is onboarded and parallel isolation is useful; give every concurrent project its own Task Space. On Windows, WSL, and native Linux, never install, select, or default to ego lite: use an already-supported non-ego path instead. Retain the safe official-DevTools path for compatibility, least-privilege runs, unsupported operating systems, or sites not yet accepted through ego lite. Select the Grok fallback only when the frozen Grok run explicitly requires existing real-Chrome state, or a site-specific primary-path smoke records a blocking challenge/session gap and the caller authorizes fallback. OpenCode must not inherit this Grok-only fallback implicitly. If the selected path is unavailable, return `adapter_unavailable`; never switch adapters inside one receipt.

## Workflow

1. Freeze the target, filters, expected format, and destination.
2. Select and load one runtime adapter. Freeze its client runtime, adapter identity, implementation, MCP server, and profile mode before the first browser action.
3. Attach to the selected runtime. For ego lite, create or reuse only this run's uniquely named Task Space and keep all tabs inside it. On the safe DevTools facade, if neither a target tab nor an exact unique `about:blank` tab exists, call its bounded blank-page bootstrap operation, then navigate that returned lease. A healthy MCP handshake alone is not proof of an actionable tab. Never use raw CDP `/json/new`, raw `new_page`, or a different adapter to fill this gap.
4. Navigate and inspect visible page state without reading cookies, storage, passwords, or auth headers.
5. Detect whether the page is usable, logged out, access-denied, or blocked by a human challenge. A preloaded/offscreen challenge component is not a blocker; require viewport intersection plus an obstructed intended action.
6. If the caller's site recipe identifies a dismissible inactivity/auto-logout overlay on a persistent-session or institutional-IP portal, treat it as a soft timeout rather than proven logout and run `auth.recover_soft_timeout`. Re-inspect, click only its close control, reload the same recipe-approved stable page once, wait, and re-inspect. Continue when the underlying session is restored; enter the normal login/access branch only when fresh post-reload state still proves it necessary. Never click the overlay's re-login action during this recovery probe or loop the probe.
7. If the user has authorized saved-login submission and Chrome has already populated the normal login form, click its login/continue control once without reading or typing any field value, then re-inspect. If fields are empty, the attempt errors, MFA/account choice is required, or a hard CAPTCHA is active, pause once and ask the user to complete it in the same Chrome tab. Resume from fresh page state after confirmation.
8. Execute the caller's site recipe using semantic operations from the shared contract.
9. Snapshot the approved landing directory and arm download handling before the final click when the runtime supports download events.
10. Land the file in the caller's requested directory without overwriting an accepted raw artifact. If no event arrives, use the contract's narrow new/stabilized-file fallback and record that path in the receipt.
11. Run `scripts/verify_download.py` with the expected format and minimum size.
12. Record a redacted execution receipt and return control to the calling skill.

Release the runtime controller lease as soon as the protected operation and any armed download verification finish; do not retain it while doing local analysis, public web search, or writing artifacts.

The caller may execute these steps as direct runtime tool calls or through a checked-in, bounded helper that acts as a client of the selected bridge. The browser owns authenticated page state and portal actions; helpers may own deterministic waiting, collision-safe copying, hashing, archive inspection, and verifier execution. Apply the same adapter freeze, redaction, and receipt requirements in either form.

## Download Verification

Examples:

```bash
python3 "$BRIDGE_SKILL_DIR/scripts/verify_download.py" \
  literature/fulltext/cnki/paper.pdf --expect pdf --min-bytes 10240

python3 "$BRIDGE_SKILL_DIR/scripts/verify_download.py" \
  Data/raw/csmar/2026-07-18/export.xlsx --expect xlsx
```

A click, download notification, or file extension is not acceptance. The verifier must return `ok: true`; the calling skill must also verify the expected columns or content.

## Execution Receipt

Return this structure to the caller:

```yaml
client_runtime: codex | grok | openclaw | opencode
adapter: ego_lite_task_space | codex_native_chrome | grok_chrome_devtools_mcp | opencode_chrome_devtools_mcp | grok_chrome_mcp
mcp_server: none | native | browser | chrome-mcp
implementation: ego-browser | codex_chrome | chrome-devtools-mcp | legacy_chrome_extension_bridge
profile_mode: shared_login_isolated_task_space | user_chrome | dedicated_persistent
site: cnki | sciencedirect | csmar | cnrds | other
session_reused: true | false
session_recovery: not_needed | dismiss_refresh_restored | dismiss_refresh_still_logged_out
saved_login_submitted: true | false
login_state: already_authenticated | soft_timeout_recovered | saved_login_submitted_and_verified | human_handoff_completed | not_required
operation: search | inspect | export | download
browser_required_reason: authenticated_session | protected_schema | interactive_export | entitled_download | active_challenge
artifact_path: relative/or/redacted/path
expected_format: pdf | xlsx | zip | csv | any
size_bytes: 0
sha256: hex
verification: passed | failed
download_event: completed | timeout | unsupported
completion: runtime_event | fallback_directory_increment
blocker: null | adapter_unavailable | login_required | captcha_required | access_denied | download_failed | artifact_invalid
```

Never include cookies, tokens, account identifiers, raw IP addresses, or auth headers.

## Grok Release Gate

Before committing, pushing, tagging, or releasing a change that affects the
Grok/ego adapter or its routing, run a fresh Grok Build forward acceptance on a
supported Mac:

```bash
skills/browser-session-bridge/scripts/verify_grok_ego_forward.sh \
  --cwd "$PWD"
```

Use `--model MODEL_ALIAS` or `ARIS_GROK_MODEL` only when the local Grok config
does not already select the intended model. Never publish a personal model
alias, API key, endpoint, or credential in this command or in the Skill.

A pass requires Grok itself—not Codex and not a direct ego CLI smoke—to load
both Skills, create its own isolated Task Space, observe the expected page
identity through fresh page state, complete the Task Space in a dedicated
final invocation, and pass the independent absence probe. Codex acceptance,
Skill discovery alone, direct `ego-browser` execution, or Grok's unverified
prose report cannot substitute for this gate.

## Rules

- Keep site selectors and business filters in the calling site's recipe, not in runtime adapters.
- Select ego lite only when the host platform is macOS (`uname -s` is exactly `Darwin`). Never install, select, or default to it on Windows, WSL, or native Linux.
- Under ego lite, allocate one unique Task Space per concurrent non-Codex run. Never reuse or claim another run's space; serialize only a shared landing-directory fallback interval when the installed runtime lacks event-backed saves.
- Identify the client runtime from the actual host process/tool catalog, never from the selected LLM provider. OpenScience uses OpenCode even when its model is Grok.
- Never expose Grok or OpenCode directly to raw `evaluate_script`, `initScript`, network,
  console, heap, emulation, drag, bulk-form, raw upload, cookie, storage, or
  history tools. The official MCP path must go through the project safety
  facade; file upload is permitted only through bounded `aris_upload_file`.
- Treat a dedicated persistent profile as reusable, not permanent: site expiry, IP/institution changes, MFA, and fresh challenges may require another handoff.
- Do not infer logout or missing institutional access from a dismissible inactivity overlay alone. Run the caller-approved close → single reload → fresh inspection recovery before login or access-gap classification.
- Re-read page state after navigation, login, challenge completion, or modal changes; do not reuse stale element identifiers.
- Do not automate hard CAPTCHAs or credential entry. A user-authorized one-time submit of an already Chrome-autofilled form is permitted by `auth.submit_saved`; never inspect the saved values.
- Do not ask for CAPTCHA handoff from hidden/offscreen markup alone; prove that the rendered challenge intersects the viewport and blocks the requested operation.
- Download only the user-requested paper or minimal data extract; no bulk crawl.
- Treat HTML masquerading as PDF/data, partial files, empty exports, and wrong formats as failures.
- Judge acceptance from the fresh verified artifact and its receipt, not from whether orchestration used an interactive browser tool call or a checked-in helper client.
- Do not claim cross-runtime acceptance from a single runtime receipt.
