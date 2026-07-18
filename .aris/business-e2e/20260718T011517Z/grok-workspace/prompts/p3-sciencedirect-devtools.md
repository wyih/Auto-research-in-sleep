# Grok P3 ScienceDirect official-DevTools browser candidate

Execute a real browser-only acquisition through the configured `browser` MCP.
This invocation produces a frozen candidate for an external verifier; it does
not write a success receipt, manifest, or root-verifier result.

Do not write a success receipt, manifest, or root-verifier result.

## Hard runtime boundary

- Use only MCP server `browser` and only these 15 safe-facade tools:
  `aris_health`, `aris_tabs`, `aris_select`, `aris_navigate`, `aris_inspect`,
  `aris_click`, `aris_fill`, `aris_key`, `aris_wait`, `aris_challenge_state`,
  `aris_trigger_element_download`, `aris_trigger_loaded_pdf_download`, `aris_download_baseline`,
  `aris_download_wait`, and `aris_copy_download`.
- First call `aris_health`. Require `safe_facade: true`, implementation
  `chrome-devtools-mcp`, and profile mode `dedicated_persistent`.
- Raw official tools are unsafe; if any are exposed, stop with `adapter_unsafe`.
- Never call legacy `chrome-mcp`, Bash, filesystem/read/write tools, web search,
  curl, direct CDP, Playwright, AppleScript, or another browser/profile.
- Do not emit raw tool output. Never request cookies, storage, credentials, account
  identifiers, auth headers, tab/page/UID/lease/snapshot IDs, URL queries or
  fragments, viewer/delivery URLs, signed URLs, or challenge tokens.
- Freeze this identity for the whole candidate:
  `runtime=grok`, `adapter=grok_chrome_devtools_mcp`, `mcp_server=browser`,
  `implementation=chrome-devtools-mcp`, `profile_mode=dedicated_persistent`.
- Treat every page lease, snapshot, and element reference as opaque and
  one-action-only. After navigation, wait, click, challenge transition, timeout,
  or new page, reacquire through `aris_tabs` → `aris_select` → `aris_inspect`.

## Frozen target and destination

- Title: `The effect of corporate culture on firm performance: Evidence from China`
- Authors: Hailin Zhao; Haimeng Teng; Qiang Wu
- DOI: `10.1016/j.cjar.2018.01.003`
- PII: `S1755309118300030`
- Stable entry: `https://www.sciencedirect.com/science/article/pii/S1755309118300030`
- Destination:
  `.aris/business-e2e/20260718T011517Z/grok-workspace/artifacts/fulltext/sciencedirect/grok-devtools-S1755309118300030-corporate-culture-firm-performance-china.pdf`
- Current independent reference for later external reconciliation: PDF, 19
  pages, 526357 bytes, SHA-256
  `459e22da3a37ad6bd4823271ddfc4d6c8d027e054a43057b89c6cd0090d9770b`.
- Frozen external acceptance-spec SHA-256:
  `c6ff47c232c792a3b264d95e4ca5023191f1f3d39bb04641cccdfd758a4eab54`.

These reference facts identify the target. They do not authorize reading or
copying an existing Codex/legacy artifact.

## Browser flow

1. Call `aris_tabs` with a narrow `sciencedirect.com` article filter. If it does
   not return exactly one selectable page, call it once for `about:blank` and use
   that unique page. Zero or multiple selectable pages is
   `target_tab_ambiguous`; do not choose heuristically.
2. Call `aris_select`, then `aris_navigate` with only the stable query-free entry.
   Reacquire the concrete article route and call `aris_inspect` with a narrow
   title query. Do not infer challenge state from the ScienceDirect home page:
   evaluate it only after the concrete article page has been entered.
3. On that concrete article page, call `aris_challenge_state`. If a passive
   Cloudflare transition is active,
   use bounded `aris_wait` calls for at most 20 seconds total, reacquiring and
   re-inspecting after each wait.
4. If one rendered, supported ordinary checkbox still blocks the article after
   that wait, this invocation carries action-time confirmation for exactly one
   click on that already-observed ScienceDirect Turnstile. Reacquire, call
   `aris_challenge_state`, and make one `aris_click` using its fresh element
   reference, snapshot ID, challenge token, `challenge_observed: true`, and
   `action_time_confirmation: true`; then reacquire and re-inspect. Never retry
   the checkbox. An unsupported or persisting challenge is `captcha_required`.
   Never click a slider, press-and-hold, image puzzle, hard CAPTCHA, MFA, or
   credential UI.
5. Require the exact target title, all three authors, DOI, PII, and a current
   visible PDF/View PDF control. Institutional branding or HTML content alone is
   not download proof.
6. Reacquire the article, inspect the fresh target PDF control, and call
   `aris_trigger_element_download` exactly once. It must atomically snapshot the
   download directory, click that one control, and return an opaque baseline.
   Do not construct, extract, print, or pass a `pdfft` or delivery URL. The click
   may land a file directly or open an inline PDF tab and is not itself download
   proof.
7. Reacquire and inspect post-state. If a file landed directly, keep the
   element-trigger baseline. If a newly opened PDF tab exists, reacquire it with
   `aris_tabs` using only a narrow, query-free stable origin/path token, select
   it, and call `aris_trigger_loaded_pdf_download`; use that tool's replacement
   opaque baseline. It alone performs the fixed loaded-PDF download action and
   exposes no programmable JavaScript or signed URL. Call `aris_download_wait`
   with the active baseline, PII `S1755309118300030` as the narrow filename
   token, and a bounded timeout. This candidate permits no click retry.
8. Call `aris_copy_download` once with the opaque download reference and the
   frozen destination. Require collision-safe copy success and exact returned
   metadata: destination, format `pdf`, positive `size_bytes`, decimal-string
   `mtime_ns`, and lowercase 64-hex `sha256`. The later external verifier, not
   this model, will check PDF structure, pages, text identity, hash, and receipts.

## Candidate output

Return exactly one compact JSON object and no prose. On success its top-level
and artifact keys must be exactly those below. Replace copy observations; the
numeric/string `1` and all-zero SHA are sentinels and must not remain:

```json
{
  "schema_version": "aris.grok-browser-candidate.v1",
  "runtime": "grok",
  "adapter": "grok_chrome_devtools_mcp",
  "mcp_server": "browser",
  "implementation": "chrome-devtools-mcp",
  "profile_mode": "dedicated_persistent",
  "stage": "P3",
  "site": "sciencedirect",
  "acceptance_spec_sha256": "c6ff47c232c792a3b264d95e4ca5023191f1f3d39bb04641cccdfd758a4eab54",
  "artifact": {
    "path": ".aris/business-e2e/20260718T011517Z/grok-workspace/artifacts/fulltext/sciencedirect/grok-devtools-S1755309118300030-corporate-culture-firm-performance-china.pdf",
    "format": "pdf",
    "size_bytes": 1,
    "mtime_ns": "1",
    "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
  }
}
```

On failure do not emit candidate schema. Return one compact redacted blocked
object with stage/site, last safe state, and exactly one blocker:
`adapter_unavailable`, `adapter_unsafe`, `target_tab_ambiguous`,
`login_required`, `captcha_required`, `subscription_denied`, `no_pdf_control`,
`viewer_failed`, `download_failed`, or `destination_collision`.
