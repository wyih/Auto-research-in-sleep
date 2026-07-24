# Grok and OpenCode Safe Chrome DevTools MCP Adapter

Use this adapter as Grok's or OpenCode/OpenScience's primary browser path when
the configured `browser` server is the project safety facade backed by official
`chrome-devtools-mcp`.
The facade connects to an externally managed visible dedicated persistent Chrome
profile, or launches that same dedicated profile in managed mode. It is not the
user's ordinary Chrome profile and it is not the legacy extension bridge.

## Preflight

1. Identify the host client before looking at the model provider. A Grok model
   hosted by OpenCode/OpenScience is `client_runtime: opencode`; do not run
   `grok mcp`, read Grok configuration, or select a Grok-only fallback in that
   session. For Grok Build, require `grok mcp doctor browser`. For OpenCode,
   require the current session's MCP tool catalog to expose the `browser`
   server's bounded `aris_*` surface; `opencode mcp list` is only diagnostic
   when it is run with the same XDG configuration as the host application.
   If the safe tools are absent, stop with `adapter_unavailable` rather than
   spawning an ad hoc DevTools/CDP client.
2. Require a healthy handshake and only the bounded `aris_*` tool surface
   documented below. If raw official tools such as
   `evaluate_script`, `list_network_requests`, or `take_heapsnapshot` are visible,
   stop with `adapter_unsafe`; the safety facade is not active.
   Then require `aris_health` to return `safe_facade: true`, adapter
   family `safe_chrome_devtools_mcp`, server `browser`, implementation
   `chrome-devtools-mcp`, profile mode `dedicated_persistent`, and a verified
   external browser transport when direct mode is configured.
3. Require the configured profile to be visible and persistent. Never copy or
   mount the user's ordinary Chrome profile.
4. Prefer an externally managed dedicated-profile Chrome listening only on a
   loopback CDP port, with the facade in direct `browserUrl` mode. This keeps the
   browser alive across client invocations and lets the client retain its
   workspace sandbox. Verify the exact profile/port/PID through the bundled lifecycle
   command before connecting; never attach to an arbitrary debugging port.
   Configure the MCP process with an explicit `ARIS_WORKSPACE_ROOT` so copies
   remain under the repository run even when the client's working directory is
   an isolated workspace.
5. If a platform cannot use the external profile service, a browser-only
   invocation may launch the visible profile without the workspace sandbox only
   when the model is restricted to the facade MCP and no Bash, raw browser,
   filesystem, web-search, or other MCP tools are exposed. Do not use that mode
   for a combined browser-and-filesystem run.
6. Freeze these receipt fields before the first browser action:

   ```yaml
   client_runtime: grok | opencode
   adapter: grok_chrome_devtools_mcp | opencode_chrome_devtools_mcp
   mcp_server: browser
   implementation: chrome-devtools-mcp
   profile_mode: dedicated_persistent
   ```

Grok or OpenCode may invoke the public facade tools directly or use a checked-in bounded
helper as an MCP client. The helper does not create a new adapter: it must expose
no raw child tools, preserve the same page leases and opaque download handles,
and produce the same redacted receipt. Shell orchestration alone is not a failure.

## Safe Tool Surface

The facade, not the client prompt, enforces URL redaction, page leases, fresh
snapshot identifiers, UID freshness, download-directory bounds, and action
invalidation. Use only:

| Contract operation | Facade tool |
|---|---|
| health/capability check | `aris_health` |
| sanitized page list | `aris_tabs` |
| bounded same-profile blank-tab bootstrap | `aris_open_blank` |
| unique page selection and bring-to-front | `aris_select` |
| credential-free stable navigation or same-stable-page reload | `aris_navigate` |
| bounded sanitized accessibility state | `aris_inspect` |
| one fresh-UID click | `aris_click` |
| one non-credential field fill plus non-echoing boolean value match | `aris_fill` |
| one workspace-scoped verified file upload through a fresh upload control | `aris_upload_file` |
| one bounded key action plus prior-fill continuity booleans | `aris_key` |
| bounded passive state wait | `aris_wait` |
| rendered challenge classification | `aris_challenge_state` |
| atomic baseline plus one fresh download-control click | `aris_trigger_element_download` |
| fixed download action for a selected loaded HTTP(S) PDF or allowlisted Wiley wrapper | `aris_trigger_loaded_pdf_download` |
| opaque `~/Downloads` baseline | `aris_download_baseline` |
| stable post-click download delta | `aris_download_wait` |
| collision-safe copy into this run's `.aris/` tree | `aris_copy_download` |
| explicit controller release after artifact verification | `aris_release` |

Never call raw `chrome-devtools-mcp` tools. In particular, never expose or call
raw/arbitrary `evaluate_script` or `initScript`, network/console/heap inspection,
emulation, drag, bulk form fill, raw `upload_file`, cookies, storage, history,
or raw page output. Upload is available only through facade-owned
`aris_upload_file`, which requires a fresh upload-control reference and a
verified regular file inside the active workspace. The loaded-PDF/wrapper tool
is also a facade-owned fixed function: the caller cannot supply JavaScript, a
URL, a filename, or page content.

## Page Lease and Action Order

For every navigation, login submit, challenge action, ordinary click, fill, key,
or post-action read:

1. Call `aris_tabs` with a narrow stable origin/path filter. Accept either one
   exact sanitized match (`selection_basis=only_match`) or, when duplicate
   matching tabs exist, the sole currently selected match
   (`selection_basis=only_selected_match`). The CSMAR result-page exception may
   return `selection_basis=identical_url_matches` only for exact duplicate
   `https://data.csmar.com/sdownload.html` tabs; select the claimed page by page
   identity and verify its visible export summary before downloading. Outside
   that exception, the facade must withhold a page
   reference when zero or multiple selected matches remain. If no site tab
   exists, call `aris_tabs` once for exact `about:blank`. Select a unique blank
   match normally. If no blank match exists, or `aris_tabs` returns
   `no_http_pages_visible`, call `aris_open_blank` with no arguments. It may
   claim one unambiguous existing blank tab or privately invoke official
   `new_page` with the fixed URL `about:blank`; it returns the selected page
   lease directly. Never call raw `new_page`, `curl /json/new`, a CDP endpoint,
   AppleScript, or the legacy bridge to bootstrap a page.
2. Call `aris_select` for a page returned by `aris_tabs` and require the page
   lease, or use the lease returned directly by `aris_open_blank`. Bringing
   a DevTools page forward is not proof that the macOS Chrome window has OS focus;
   record only `page_selected_and_brought_to_front`. `aris_select` also claims an
   atomic controller lease shared by every facade process using this dedicated
   profile. If another run owns it, stop browser actions with
   `waiting_browser_turn`; do not retry page mutations in parallel. A prose grant
   file or a selected tab is not a controller lease.
3. Call `aris_inspect` and use only the returned bounded state plus its fresh
   snapshot identifier and UID set. Every new `aris_inspect` call immediately
   invalidates all identifiers from every earlier inspection, even when no
   browser mutation occurred. The next element action must use the snapshot and
   element references returned by the immediately preceding inspection only.
   Operationally, make one final targeted `aris_inspect` the last tool call
   before any click, fill, or element-download trigger, and make that action the
   very next tool call. If any other inspection or page-selection call occurs,
   discard the intended action and start this final pair again.
4. Perform at most one action with that page lease and snapshot identifier.
5. Treat the prior snapshot and all of its UIDs as invalid after the action,
   timeout, navigation, modal change, new page, or challenge transition. Start
   again at step 1 and verify the intended post-state before retrying.
6. After the protected action and any download copy/verification complete, call
   `aris_release` with the current page lease. Release before public web search,
   local analysis, or report writing so another project can claim the profile.

`aris_health` proves the transport and facade contract; it does not prove that a
target or blank tab already exists. A zero-tab result is therefore a bootstrap
branch, not a reason to abandon the selected adapter or the protected task.

The facade fails closed if a mutating or download-helper call lacks ownership of
the shared controller lease. It reclaims an abandoned owner only after bounded
staleness/dead-process checks; callers must never delete or overwrite the lock.

Do not place signed URLs, credential-bearing queries/fragments, passwords,
tokens, cookies, auth headers, or autofilled values in tool arguments or receipts.

For a field whose accessibility snapshot omits its current value, require
`aris_fill` to return both `value_confirmation_available: true` and
`value_matches_supplied: true`. After reacquiring the same page and taking a
fresh inspection, use `aris_key` to commit the value and require its before-key
and after-key match booleans. The facade compares the active non-credential
field internally, pins only that element across the key action, checks the same
element after focus may move, and then discards the pin. It never returns either
the supplied or observed value. A navigation, different page, unrelated
mutation, sensitive field, detached element, or changed value invalidates this
continuity proof.

## Login and Persistent State

The first visit to each protected site may require one manual login in the
dedicated visible profile. Let the user enter credentials, MFA, account choice,
or other sensitive values. The client must not inspect or type those values. A normal
login/continue button already populated by Chrome may be submitted once only
when the caller authorized `auth.submit_saved`; re-inspect after the action.

The profile persists cookies and site storage across independent client launches,
but the receipt must not promise permanent login. Site expiry, IP or institution
changes, MFA, and renewed bot checks can require another handoff.

For a recipe-identified inactivity/auto-logout overlay, use a final targeted
`aris_inspect`, `aris_click` only on its fresh close-control UID, reacquire the
page, then call `aris_navigate` once with the same recipe-approved stable,
credential-free URL and inspect again. This is the facade mapping for
`auth.recover_soft_timeout`; do not click the overlay's re-login action or infer
lost IP access before the post-reload inspection. If the SPA builder resets,
replay the frozen business filters from the caller's spec rather than assuming
they survived.

## Challenges

Use `aris_challenge_state`; hidden or offscreen challenge markup is not a blocker.
Require a rendered control that intersects the viewport and obstructs the intended
article, PDF, or export action.

For an observed ordinary checkbox challenge, ask for action-time confirmation.
Only after confirmation may `aris_click` receive both the observed-challenge
evidence and the explicit confirmation flag, and it may click that fresh checkbox
UID once. Reacquire and re-inspect afterward. Never use selector fallbacks,
coordinates, JavaScript, or repeated clicks for a challenge. Never automate a
slider, press-and-hold, image puzzle, hard CAPTCHA, MFA, or credential entry.

## Downloads

The official MCP has no accepted download-completion event. For an ordinary
article/export control that directly starts a file download:

1. Reacquire and inspect the exact page, then call
   `aris_trigger_element_download` with the fresh PDF/export link or button. It
   atomically inventories `~/Downloads`, performs one ordinary click, and returns
   only an opaque baseline. It rejects challenge controls and non-link/button
   targets.
2. Call `aris_download_wait` with that baseline, a narrow filename token, and a
   bounded timeout. Require a new file after the click, stable nonzero size, and
   no partial suffix.
3. Call `aris_copy_download` once with the opaque download handle and a new target
   under the current run's `.aris/` tree. It must fail on collision and never
   overwrite an accepted artifact. Require exact returned destination, format,
   positive `size_bytes`, decimal-string `mtime_ns`, and lowercase SHA-256; never
   estimate or reconstruct those fields in the model.
4. Run the shared deterministic verifier and the caller's content/column identity
   checks. Record `download_event: unsupported` and
   `completion: fallback_directory_increment`.
5. Call `aris_release` immediately after the verified copy and receipt fields are
   captured.

Prefer the atomic element trigger when the final action is a normal link or
button. Use `aris_download_baseline` for a portal flow whose final mutation
cannot be represented by that trigger, including a verified queue icon or a
checked-in helper client. In that case, freeze the baseline immediately before
the single final action and require the same fresh-file, stability, copy, hash,
and semantic checks. Record the non-atomic transport in the receipt; do not fail
an otherwise verified artifact solely because the flow required this form.

A click, viewer page, browser PDF tab, filename, or facade success is not artifact
acceptance by itself.

For a publisher control that opens an inline HTTP(S) PDF or the allowlisted
Wiley HTML PDF wrapper instead of downloading:

1. Click the article's PDF control once, then reacquire the new PDF or wrapper
   tab using a query-free stable origin/path token. Never print or pass its
   signed query or embedded delivery URL.
2. Select that tab and call `aris_trigger_loaded_pdf_download`. For a direct PDF,
   it requires a `.pdf` path and `application/pdf`. For Wiley only, it also
   accepts an `onlinelibrary.wiley.com` `/doi/pdf/` or `/doi/epdf/` HTML wrapper,
   finds exactly one same-origin `/doi/pdfdirect/` iframe internally, and never
   returns that URL. The fixed non-programmable child action snapshots
   `~/Downloads`, triggers one browser download, and returns only an opaque
   baseline.
3. Use `aris_download_wait` and `aris_copy_download` exactly as above. Treat the
   server's content-disposition filename as authoritative; a caller-suggested
   filename may be ignored.
4. Run the same deterministic structure, identity, page-count, and hash checks.

Do not replace this bounded loaded-PDF/wrapper action with raw JavaScript, a
constructed delivery URL, network-response capture, direct HTTP, or a click on
Chrome's PDF viewer toolbar.

## Uploads

Use `aris_upload_file` only after selecting the page and taking one final
targeted inspection of the intended upload control. Supply one
workspace-relative path to an existing non-empty regular file. The facade
rejects absolute paths, parent traversal, symlinks, unsupported or executable
extensions, and files larger than 100 MiB. It verifies size, modification time
and SHA-256 across the upload attempt and consumes the fresh snapshot. The
facade negotiates the same canonical workspace with the official child through
the MCP `roots` capability; do not use `--allowUnrestrictedPaths`.
Re-inspect the page afterward to verify that the intended attachment appears.
Never automate the native file chooser, call raw `upload_file`, or upload
credentials or unrelated data.

For ChatGPT's current attachment menu, use this exact bounded sequence:

1. Inspect for `Add files and more`, then click that fresh button reference.
2. Call `aris_wait` for `Add photos & files`. Because waiting invalidates the
   prior inspection, immediately take one new targeted `aris_inspect` for that
   exact text.
3. Pass the returned `Add photos & files` element directly to
   `aris_upload_file`. A `StaticText` role is an accepted proxy: the facade
   resolves the owning menu row or hidden file input. Do not insert
   `aris_tabs`, `aris_select`, another inspection, or any other browser call
   between this final targeted inspection and the upload.
4. Re-inspect for the exact `Remove file N: <filename>` control. Only that
   post-state proves that the intended attachment is present.
5. If the upload reports `browser_operation_failed` or an unknown effect, first
   inspect for the exact `Remove file N: <filename>` control. If it is absent,
   reopen the menu from fresh page state and repeat steps 2–4 once. After that
   single retry, release the lease and report `upload_failed`; do not explore
   broad snapshots, automate the native chooser, or keep clicking menu text.
6. If the exact `Remove file N: <filename>` control is already present, do not
   upload that file again. Remove an unintended attachment before proceeding;
   never submit duplicate or ambiguous attachments.

## Fallback Boundary

If a Grok Build run records a blocking challenge/session gap and the caller
chooses the user's existing real-Chrome state, end this receipt as blocked.
Start a new run using `grok-chrome-mcp.md` and
`adapter: grok_chrome_mcp`. OpenCode/OpenScience has no implicit legacy
fallback: report `adapter_unavailable` unless the caller explicitly configures
and authorizes a separate supported adapter. Never splice actions from both
backends into one success receipt or relabel legacy evidence as official
DevTools evidence.
