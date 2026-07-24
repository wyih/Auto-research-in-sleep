# ego lite Task-Space Adapter

This adapter is macOS only. Use it for Grok, OpenClaw, or
OpenCode/OpenScience when ego lite has completed onboarding. It is the
preferred parallel path on a supported Mac because every run owns an isolated
Task Space while inheriting the browser's authorized login state.
Codex continues to use its native Chrome plugin.

## Preflight

1. Require `uname -s` to return exactly `Darwin`. On Windows, WSL, or native
   Linux, never install, select, or default to this adapter. Return
   `adapter_unavailable` with the local reason `platform_unsupported`, then
   select an already-supported non-ego adapter before the run is frozen.
2. Read the installed `ego-browser` `SKILL.md` completely. Its bundled helper
   names are authoritative because the app and CLI update together. Do not mix
   examples from a different ego-browser release.
3. Require one successful `ego-browser nodejs` invocation. Do not require
   `ego-browser --doctor`; not every bundled CLI version exposes that command.
4. Freeze:

   ```yaml
   client_runtime: grok | openclaw | opencode
   adapter: ego_lite_task_space
   mcp_server: none
   implementation: ego-browser
   profile_mode: shared_login_isolated_task_space
   ```

5. Create a fresh, non-sensitive Task Space name containing the client, project
   slug, site, and run suffix. Never reuse the same name across concurrent
   runs. If that name already belongs to the user or another active run, choose
   a new suffix; never claim it.
6. Use one Task Space for the whole protected operation. Keep its numeric ID
   only in the local execution receipt, not in published manifests.

## Isolation And Ownership

- Parallel agents may run concurrently only in different Task Spaces.
- Do not switch into, claim, close, or complete another run's Task Space.
- User control of the selected Task Space is a hard stop. Do not retry or call
  a takeover helper until the user explicitly says to continue.
- For login or a hard challenge, use the installed ego-browser Skill's handoff
  operation, report the exact page/action needed, and wait. Resume the same
  Task Space after explicit confirmation.
- Complete the Task Space in a dedicated final invocation only after the
  browser artifact and caller-specific checks pass. Default to `keep: false`;
  use `keep: true` only when the user must inspect or finish that live page.

## Semantic Operation Mapping

Use the installed ego-browser Skill's current documented helpers to implement
the shared contract:

| Contract operation | ego lite behavior |
|---|---|
| `session.attach` | Select the run's own agent-controlled Task Space |
| `tab.list` | List tabs inside that Task Space only |
| `tab.open_or_claim` | Open or reuse a tab inside that Task Space |
| `page.inspect` | Take a fresh semantic snapshot or bounded page-state read |
| `page.navigate` / `page.reload` | Use the documented navigation helpers |
| `element.act` | Use fresh semantic refs/locators; re-inspect after mutation |
| `auth.submit_saved` | Click one user-authorized, already-populated submit control without reading values |
| `human.handoff` | Hand off the same Task Space and wait for explicit continuation |
| `download.wait` | Use the documented download event/save operation when present; otherwise use the shared narrow landing-directory fallback |
| `artifact.verify` | Run the bridge verifier plus the caller's identity/schema gate |
| `session.release` | Complete the run's Task Space in a separate final invocation |

Prefer semantic snapshots and locators. Use screenshot-guided coordinates only
for a genuinely visual or accessibility-poor control. For protected research
sites, do not use raw CDP, page JavaScript, browser-origin fetch, Node-side
fetch, or direct endpoint reconstruction merely because ego-browser exposes
them; use those only when the site recipe explicitly requires a bounded,
reviewed operation and the receipt records it.

## Authentication And Challenges

- Never inspect or emit cookies, storage, passwords, autofilled values, auth
  headers, account identifiers, or browser-profile files.
- An already authenticated page may proceed.
- A user-authorized saved-login submit is one normal click only. Missing fields,
  MFA, account selection, login errors, sliders, image puzzles, and hard
  CAPTCHAs require handoff.
- Apply the shared viewport/blocking test before classifying a challenge.
- Apply a caller-approved soft-timeout close → one reload → fresh inspection
  exactly once before declaring logout.

## Downloads

1. Freeze the expected artifact, approved landing directory, and minimum
   verifier before the final click.
2. If the installed ego-browser Skill documents an event-backed download
   object with a bounded save operation, arm it before the click and save
   directly under the active project.
3. Otherwise snapshot only the approved browser landing directory, click once,
   then apply the shared new/stabilized-file fallback. This fallback directory
   is shared across Task Spaces, so serialize only this short final
   click-to-copy interval when parallel runs lack event-backed saves; browser
   navigation and filtering remain parallel.
4. Copy without overwrite into the project run, run
   `scripts/verify_download.py`, then apply the caller's title/schema/filter
   checks.
5. A browser notification, plausible filename, extension, or open PDF viewer is
   not acceptance.

## Acceptance

Set `adapter: ego_lite_task_space` only when the trace proves:

- the installed ego-browser Skill was used;
- one run-owned isolated Task Space performed the operation;
- any handoff returned to that same Task Space;
- the fresh artifact passed deterministic and domain-specific verification;
- the Task Space was completed or intentionally kept for a stated user action.
