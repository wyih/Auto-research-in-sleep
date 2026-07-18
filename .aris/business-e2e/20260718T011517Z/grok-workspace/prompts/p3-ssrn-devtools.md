# Grok P3 SSRN official-DevTools browser candidate

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
  identifiers, auth headers, URL queries/fragments, signed/delivery URLs, or
  tab/page/lease/snapshot/element/challenge identifiers.
- Every opaque lease/snapshot/element reference is one-action-only. Reacquire
  after every navigation, wait, click, timeout, new page, or challenge change.

## Frozen target

- Title: `Corporate Culture: Evidence from the Field`
- Frozen PDF authors: John R. Graham; Campbell R. Harvey; Jillian Popadak;
  Shivaram Rajgopal
- Current abstract-page alias accepted only after title/ID/coauthor
  reconciliation: Jillian Grennan for Jillian Popadak. The live and frozen
  forms both use Shivaram Rajgopal.
- SSRN abstract ID: `2937525`
- Stable entry (the sole allowed benign navigation query):
  `https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2937525`
- Destination:
  `.aris/business-e2e/20260718T011517Z/grok-workspace/artifacts/fulltext/ssrn/grok-devtools-ssrn-2937525-corporate-culture-evidence-field.pdf`
- External reconciliation reference: PDF, 79 pages, 875844 bytes, SHA-256
  `f69be9aa4373ff67db8a98b9bcb27ff3576067ae82a1337a88e1aaed998847a2`.
- Frozen external acceptance-spec SHA-256:
  `ae32058ec25ded2d810d41933bd37d6a662cae0c91fb7373b81c06f441cdb485`.

Never read or copy a prior Codex/legacy artifact.

## Browser flow

1. Acquire one selectable `papers.ssrn.com` page through `aris_tabs`; otherwise
   use one unique `about:blank` page. Zero/multiple pages is
   `target_tab_ambiguous`. Select it and navigate only to the frozen entry.
2. Reacquire and inspect with a narrow target-title query. If SSRN shows its
   expected passive challenge, do not click during the bounded passive phase.
   Use `aris_wait` for at most 20 seconds total, reacquiring and re-inspecting
   each time; continue immediately if it clears automatically.
3. If `aris_challenge_state` still reports one rendered, supported ordinary
   checkbox after that wait, this launch carries action-time confirmation for
   exactly one click on that already-observed SSRN checkbox. Reacquire the fresh
   challenge state and call `aris_click` once with its element reference,
   snapshot ID, challenge token, `challenge_observed: true`, and
   `action_time_confirmation: true`; then reacquire and re-inspect. Never retry
   the checkbox and never automate a slider, press-and-hold, image puzzle, hard
   CAPTCHA, MFA, or credential UI. An unsupported or persisting challenge is
   `captcha_required`.
4. Require exact title and abstract ID. Reconcile the live-page author set using
   the frozen aliases above; the later external verifier still requires the
   frozen historical author text in the downloaded PDF. Require the current
   visible paper/PDF download control.
5. Reacquire and inspect the fresh target download control, then call
   `aris_trigger_element_download` once. It must atomically snapshot the download
   directory, click that one fresh control, and return an opaque baseline. Do not
   construct or emit a delivery URL.
6. Reacquire and inspect post-state. If the click opened a selected loaded PDF
   tab instead of directly landing a file, call
   `aris_trigger_loaded_pdf_download` on that tab and use its replacement opaque
   baseline. Otherwise keep the element-trigger baseline. Call
   `aris_download_wait` with the active baseline, a narrow title/ID-derived
   filename token and bounded timeout. This candidate permits no click retry.
7. Call `aris_copy_download` once to the frozen destination. Require collision-
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
  "site": "ssrn",
  "acceptance_spec_sha256": "ae32058ec25ded2d810d41933bd37d6a662cae0c91fb7373b81c06f441cdb485",
  "artifact": {
    "path": ".aris/business-e2e/20260718T011517Z/grok-workspace/artifacts/fulltext/ssrn/grok-devtools-ssrn-2937525-corporate-culture-evidence-field.pdf",
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
`access_denied`, `no_pdf_control`, `download_failed`, or
`destination_collision`.
