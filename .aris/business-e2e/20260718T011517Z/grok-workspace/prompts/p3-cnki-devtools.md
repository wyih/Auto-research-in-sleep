# Grok P3 CNKI official-DevTools browser candidate

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
  after every navigation, fill, wait, click, timeout, new page, or challenge
  change.

## Frozen target

- Chinese title: `质量文化对企业绩效的影响研究——组织承诺的中介作用`
- Author: `段菁菁`
- Institution/year: `西北大学`, 2018
- CNKI source identity: `1018120457.nh`, CMFD
- Stable search entry: `https://kns.cnki.net/kns8s/search`
- Destination:
  `.aris/business-e2e/20260718T011517Z/grok-workspace/artifacts/fulltext/cnki/grok-devtools-duan-2018-quality-culture-performance.pdf`
- Independent identity reference for later external reconciliation: PDF, 67
  pages, 2086277 bytes, SHA-256
  `79b6a8b9f2c6f075343f1322c38ff4c6c79abedba8ed963cee5f8a6094a28117`.
- Frozen external acceptance-spec SHA-256:
  `4408fc8b8a652f25c5a03162678faf3c64d97f8540ceb0b3daa1c9f62eee86d5`.

The English title and romanized author embedded in the PDF are frozen by the
external acceptance spec. Never read or copy a prior Codex/legacy artifact.

## Browser flow

1. Acquire one selectable `kns.cnki.net` search page through `aris_tabs`;
   otherwise use one unique `about:blank` page. Zero/multiple pages is
   `target_tab_ambiguous`. Select it and navigate only to the stable search
   entry.
2. Reacquire and call `aris_challenge_state`. On CNKI require the facade's fixed
   rendered-geometry classification. Hidden, zero-size, offscreen, or
   non-obstructing Tencent markup is not a challenge. If a rendered slider,
   image puzzle, press-and-hold, hard CAPTCHA, MFA, or credential UI blocks the
   search/detail/PDF action, stop with `captcha_required`; never click, drag, or
   solve it.
3. Reacquire and inspect the current search input, then call `aris_fill` once
   with the exact Chinese title. Reacquire, inspect the visible search action,
   and call `aris_click` once. Do not encode the title into a navigation URL.
4. After a bounded wait, reacquire the results page and inspect only a narrow
   title query. Require an exact title match plus author `段菁菁`, institution
   `西北大学`, and year 2018 before clicking that one fresh result. Do not use a
   list-page download control or a CAJ action.
5. Reacquire the resulting detail page by a query-free stable CNKI origin/path
   token. Call `aris_challenge_state` again, then inspect and require the exact
   title plus at least the author and source identity. Require a current visible
   named PDF action; a detail page, filename, or CAJ control is not proof.
6. Reacquire and inspect the fresh detail-page PDF link/button, then call
   `aris_trigger_element_download` once. It must atomically inventory
   `~/Downloads`, click only that fresh PDF control, and return an opaque
   baseline. Do not construct, extract, print, or replay a session-bearing
   download URL.
7. Call `aris_download_wait` with that baseline, `质量文化` as the narrow filename
   token, and a bounded timeout. Require a new stable non-partial file. This
   candidate permits no click retry.
8. Call `aris_copy_download` once to the frozen destination. Require
   collision-safe success and exact returned destination, format `pdf`, positive
   `size_bytes`, decimal-string `mtime_ns`, and lowercase 64-hex `sha256`.
   External verification will check PDF structure, page count, and embedded
   title/author identity.

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
  "site": "cnki",
  "acceptance_spec_sha256": "4408fc8b8a652f25c5a03162678faf3c64d97f8540ceb0b3daa1c9f62eee86d5",
  "artifact": {
    "path": ".aris/business-e2e/20260718T011517Z/grok-workspace/artifacts/fulltext/cnki/grok-devtools-duan-2018-quality-culture-performance.pdf",
    "format": "pdf",
    "size_bytes": 1,
    "mtime_ns": "1",
    "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
  }
}
```

The sentinels must be replaced with returned copy metadata. On failure do not
emit candidate schema; return one compact redacted blocked object with exactly
one blocker: `adapter_unavailable`, `adapter_unsafe`,
`target_tab_ambiguous`, `login_required`, `captcha_required`,
`subscription_denied`, `no_result`, `no_pdf_control`, `download_failed`, or
`destination_collision`.
