# Grok P3 Wiley official-DevTools browser candidate

Execute a real browser-only acquisition through MCP server `browser`. Produce one
frozen candidate for external verification; do not write a success receipt,
manifest, or root-verifier result.

## Runtime contract

- Use only these 15 safe-facade tools: `aris_health`, `aris_tabs`, `aris_select`,
  `aris_navigate`, `aris_inspect`, `aris_click`, `aris_fill`, `aris_key`,
  `aris_wait`, `aris_challenge_state`, `aris_trigger_element_download`,
  `aris_trigger_loaded_pdf_download`, `aris_download_baseline`,
  `aris_download_wait`, and `aris_copy_download`.
- Call `aris_health` first and require `safe_facade: true`, implementation
  `chrome-devtools-mcp`, and profile mode `dedicated_persistent`.
- Raw official tools mean `adapter_unsafe`.
- Never use legacy `chrome-mcp`, Bash, filesystem/read/write tools, web search,
  direct CDP, Playwright, AppleScript, or another profile.
- Freeze `runtime=grok`, `adapter=grok_chrome_devtools_mcp`,
  `mcp_server=browser`, `implementation=chrome-devtools-mcp`, and
  `profile_mode=dedicated_persistent` for the whole candidate.
- Do not emit raw tool output, cookies, storage, credentials, account/session
  identifiers, auth headers, URL queries/fragments, reader/delivery/signed URLs,
  or tab/page/lease/snapshot/element/challenge identifiers.
- Every opaque lease/snapshot/element reference is one-action-only. Reacquire
  after every navigation, wait, click, timeout, new page, or challenge change.

## Frozen target

- Title: `Corporate culture: The interview evidence`
- Authors: John R. Graham; Jillian A. Grennan; Campbell R. Harvey; Shivaram Rajgopal
- DOI: `10.1111/jacf.12528`
- Stable entry: `https://onlinelibrary.wiley.com/doi/10.1111/jacf.12528`
- Destination:
  `.aris/business-e2e/20260718T011517Z/grok-workspace/artifacts/fulltext/wiley/grok-devtools-graham-et-al-2023-corporate-culture-interview-evidence.pdf`
- External reconciliation requires a valid 20-page PDF with the frozen
  title/authors/DOI. Wiley has emitted identity-equivalent serializations with
  different byte counts and hashes, so a historical hash is not a byte-equality
  requirement; return the fresh candidate's actual size and SHA-256.
- Frozen external acceptance-spec SHA-256:
  `2b9847d1734479b6f268f2b6f0dc27078a4c2c9d1a3050bf125963eb8c2de6b3`.

Never read or copy a prior Codex/legacy artifact.

## Browser flow

1. Acquire one selectable `onlinelibrary.wiley.com` page through `aris_tabs`;
   otherwise use one unique `about:blank` page. Zero/multiple pages is
   `target_tab_ambiguous`. Select and navigate only to the frozen DOI entry.
2. Reacquire, inspect with a narrow target-title query, and call
   `aris_challenge_state`. Allow a bounded passive wait up to 20 seconds.
3. If the first DOI-page load shows an ordinary Wiley login shell while the
   target article identity and PDF entitlement control are absent, reacquire
   and navigate to the exact same frozen DOI entry one more time. This is the
   only permitted same-page refresh. Reacquire and re-inspect; if the article
   and PDF control return, continue, but a persistent login shell is
   `login_required`. Do not submit, inspect, or type credentials, and never make
   a refresh loop.
4. If one rendered, supported ordinary checkbox still blocks the article after
   that wait, this invocation carries action-time confirmation for exactly one
   click on that already-observed Wiley checkbox. Reacquire challenge state and
   make one `aris_click` with its fresh element reference, snapshot ID, challenge
   token, `challenge_observed: true`, and `action_time_confirmation: true`; then
   reacquire and re-inspect. Never retry the checkbox. An unsupported or
   persisting challenge is `captcha_required`. Never automate sliders,
   press-and-hold, image puzzles, hard CAPTCHAs, MFA, or credentials.
5. Require exact title, all four authors, DOI, access state, and the current
   visible target PDF control. HTML article text or an access badge is not proof.
6. Reacquire and inspect the exact fresh article-page `Download PDF` control,
   then call `aris_trigger_element_download` exactly once. It must atomically
   snapshot the download directory, click that one control, and return an opaque
   baseline. The control may either download directly or navigate to a wrapper.
   Do not construct or emit `/doi/pdf/`, `/doi/epdf/`, `/doi/pdfdirect/`,
   query-bearing, iframe, reader, or delivery URLs.
7. Reacquire and inspect post-state. If a file landed directly, keep the
   element-trigger baseline. If the selected page is Wiley's allowlisted HTML PDF
   wrapper at `/doi/pdf/` or `/doi/epdf/`, call
   `aris_trigger_loaded_pdf_download` and use its replacement opaque baseline.
   The facade-owned fixed action must find exactly one same-origin
   `/doi/pdfdirect/` iframe internally without exposing its URL; no visible
   reader control or Chrome PDF-viewer toolbar click is required. Only if a
   different post-state exposes a genuine direct file link/button may
   `aris_trigger_element_download` be used once on that fresh control. Otherwise
   do not add clicks.
8. Call `aris_download_wait` against the active baseline with `Graham` as the
   narrow filename token and a bounded timeout. This candidate permits no click retry.
9. Call `aris_copy_download` once to the frozen destination. Require collision-
   safe success and exact returned destination, format `pdf`, positive
   `size_bytes`, decimal-string `mtime_ns`, and lowercase 64-hex `sha256`.
   External verification will check PDF structure, pages, text identity, and hash.

## Candidate output

Return exactly one compact JSON object and no prose:

```json
{
  "schema_version": "aris.grok-browser-candidate.v1",
  "runtime": "grok",
  "adapter": "grok_chrome_devtools_mcp",
  "mcp_server": "browser",
  "implementation": "chrome-devtools-mcp",
  "profile_mode": "dedicated_persistent",
  "stage": "P3",
  "site": "wiley",
  "acceptance_spec_sha256": "2b9847d1734479b6f268f2b6f0dc27078a4c2c9d1a3050bf125963eb8c2de6b3",
  "artifact": {
    "path": ".aris/business-e2e/20260718T011517Z/grok-workspace/artifacts/fulltext/wiley/grok-devtools-graham-et-al-2023-corporate-culture-interview-evidence.pdf",
    "format": "pdf",
    "size_bytes": 1,
    "mtime_ns": "1",
    "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
  }
}
```

The sentinels must be replaced with returned copy metadata. On failure do not
emit candidate schema; return one compact redacted blocked object with exactly
one blocker: `adapter_unavailable`,
`adapter_unsafe`, `target_tab_ambiguous`, `login_required`, `captcha_required`,
`subscription_denied`, `no_pdf_control`, `reader_failed`, `download_failed`, or
`destination_collision`.
