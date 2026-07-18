# Grok P4 CNRDS official-DevTools browser candidate

Execute one real CNRDS portal export through MCP server `browser`. The browser
run may only land one artifact and return a frozen candidate for a separate
external verifier. Do not write a success receipt, manifest, or root-verifier
result.

## Hard runtime boundary

- Use only these 15 safe-facade tools: `aris_health`, `aris_tabs`, `aris_select`,
  `aris_navigate`, `aris_inspect`, `aris_click`, `aris_fill`, `aris_key`,
  `aris_wait`, `aris_challenge_state`, `aris_trigger_element_download`,
  `aris_trigger_loaded_pdf_download`, `aris_download_baseline`,
  `aris_download_wait`, and `aris_copy_download`.
- Call `aris_health` first. Require `safe_facade: true`, implementation
  `chrome-devtools-mcp`, and profile mode `dedicated_persistent`.
- Raw official tools are unsafe. Stop with `adapter_unsafe` if the safe facade
  or its dedicated persistent profile is unavailable.
- Do not use a legacy adapter, arbitrary browser JavaScript, shell commands,
  filesystem tools, web search/fetch, curl, direct network requests, direct CDP,
  Playwright, AppleScript, another browser, or another profile.
- Never request, inspect, print, or return credentials, cookies, storage,
  account/session identifiers, auth headers, raw tool output, URL queries or
  fragments, signed/delivery URLs, or opaque page, lease, snapshot, element, or
  challenge identifiers.
- Every opaque browser reference is one-action-only. After every navigation,
  fill, key, click, wait, timeout, new page, or state transition, reacquire with
  `aris_tabs` and `aris_select`, then obtain fresh bounded state with
  `aris_inspect`.
- Every new `aris_inspect` immediately invalidates every earlier snapshot and
  element reference even if no mutation occurred. Use only the snapshot and
  element reference returned by the immediately preceding inspection for the
  next action; never mix references from two inspections.
- Before every `aris_click`, `aris_fill`, or
  `aris_trigger_element_download`, make one final targeted `aris_inspect` the
  last tool call, then make the intended action the very next tool call using
  both identifiers from that single response. If any intervening inspect,
  tabs, select, wait, or other tool call occurs, discard both identifiers and
  repeat the final targeted-inspect/action pair from a new page lease.
- A mutating-call error or timeout leaves its effect unknown. Inspect the new
  state before deciding what happened and never retry a mutation blindly.

The launch envelope supplies the lowercase SHA-256 of the already-frozen
external acceptance spec. It is data for the candidate only: do not read,
change, or write that spec in this browser run. The spec binds stage `P4`, site
`cnrds`, the exact artifact path below, ZIP format, minimum size, archive member,
ordered headers, and row assertions.
The frozen digest for this launch is
`e35830fced652d41c2949166389c28c33a5d9762b091980d0dab8c200e9f8d3d`.

## Frozen portal target

- Stable entry: `https://www.cnrds.com/Home/Index#/FeaturedDatabase/DB/CIRD/`
- Source path: `创新专利研究 (CIRD) → 上市公司专利申请与获得 → 上市公司专利申请情况`
- Dates: `2020-01-01` through `2020-12-31`
- Code: only `000001`
- Fields in exact order: `Scode`, `Year`, `Ftyp`, `Aplctm`, `Invia`, `Umia`,
  `Desia`, `Invja`, `Umja`, `Desja`
- Preview requirement: exactly two real rows; both `Scode=000001`, both
  `Year=2020`, and company types exactly `上市公司本身` and `集团公司合计`
- Completion requirement: the official queue visibly reaches `压缩完成`
- Export format: CSV packaged by the portal as ZIP
- Candidate destination:
  `.aris/business-e2e/20260718T011517Z/cn-data/raw/cnrds/2026-07-18_grok_v1/cnrds-cird-000001-2020.zip`

Never inspect, copy, or reuse a prior Codex or legacy artifact as evidence.

## Saved-login rule

The user authorizes one ordinary saved-login submission. The facade deliberately
does not expose autofilled credential values, so do not attempt to inspect or
prove either field's content. If the visible CNRDS login form and its normal
enabled login button are present, click that button once, relying only on the
dedicated profile's saved-login state. Do not read, copy, print, or type either
field. Reacquire immediately and independently verify authenticated portal
state. If the page remains at login, account selection or MFA appears, or a hard
CAPTCHA blocks the page, stop with `login_required` or `captcha_required`.
Do not inspect password-manager UI; do not retry login.

## Portal sequence

1. First call `aris_tabs` with the query-free filter `/ViewName/` to claim an
   already-open final-dataset page without including a CNRDS home/module tab in
   the candidate set. If and only if that returns zero matches, try
   `/FeaturedDatabase/DB/CIRD/`; if that also returns zero, try the exact
   `about:blank` bootstrap exception. Do not begin with a broad `cnrds.com`
   filter. For each stage, require exactly one selectable result. When duplicate
   matches exist, accept only the facade's sole currently selected match with
   `unique=true` and `selection_basis=only_selected_match`; otherwise the
   current stage is `target_tab_ambiguous` and must not be widened. Never put
   the URL's `#` fragment into `aris_tabs`. Select the page. If it already visibly identifies
   the exact frozen final dataset `上市公司专利申请情况`, keep that deeper route and
   do not navigate backward. Otherwise navigate to the frozen authenticated
   CIRD deep link and reacquire. Do not rediscover CIRD through the home page
   card or library search: this run freezes the user-verified direct route.
2. Apply the saved-login rule only when necessary, then independently verify the
   signed-in CIRD portal state. Resolve only the two remaining dataset levels,
   `上市公司专利申请与获得 → 上市公司专利申请情况`, and verify the full frozen
   module and dataset identity before applying filters.
3. Set and commit the two dates separately, change focus, reacquire, and verify
   both displayed values. Each date `aris_fill` must return
   `value_confirmation_available=true` and `value_matches_supplied=true`.
   Reacquire the same page, take a fresh inspection, commit with `aris_key`
   `Enter`, and require `value_confirmation_available_before_key`,
   `value_matches_last_fill_before_key`,
   `value_confirmation_available_after_key`, and
   `value_matches_last_fill_after_key` all to be true. These booleans are the
   permitted value proof when the accessibility
   snapshot omits the textbox value; never request or print the raw observed
   value. Select only code `000001`; select exactly the ten frozen fields in
   order and CSV output; add no extra condition or field.
4. Run the official preview. Require exactly two real rows matching the frozen
   code, year, and company types. Do not count a field-description row as data.
5. Start the official export, reconcile its summary, add it to the official
   queue, and use bounded `aris_wait` calls with fresh inspections until the
   relevant queue entry visibly says `压缩完成`.
6. Reacquire and re-inspect `压缩完成`, then call
   `aris_trigger_element_download` exactly once on the fresh queue-download
   control. It must atomically snapshot the download directory, click once, and
   return the opaque baseline used below. This candidate permits no click retry.
7. Reacquire and inspect post-state. Call `aris_download_wait` with the opaque
   baseline, filename token `.zip`, and a bounded timeout. CNRDS may assign an
   opaque server-generated outer filename, so do not guess a table-name token;
   the atomic pre-click baseline and the facade's exactly-one new-file rule are
   the identity boundary. Accept only a new stable non-partial download. If the
   browser shows a vendor-host failure, do not expose, replay, or directly fetch
   a temporary delivery URL; stop with `download_failed`.
8. Call `aris_copy_download` exactly once with the opaque download reference and
   the frozen destination. Require collision-safe success and returned artifact
   metadata containing that exact path, format `zip`, positive `size_bytes`,
   decimal-string `mtime_ns`, and a lowercase 64-hex `sha256`. If the facade omits any
   field, stop with `artifact_metadata_unavailable`; do not fabricate it.

## Candidate output

Only after all portal assertions and the copy succeed, return exactly one
compact JSON object and no prose. Its top-level and artifact keys must remain
exactly as shown. Replace the launch/spec digest and copied-file observations.
The all-zero artifact hash, numeric `1`, and string `"1"` below are sentinels; if any sentinel
would remain, return a compact blocked result instead of this candidate.

```json
{
  "schema_version": "aris.grok-browser-candidate.v1",
  "runtime": "grok",
  "adapter": "grok_chrome_devtools_mcp",
  "mcp_server": "browser",
  "implementation": "chrome-devtools-mcp",
  "profile_mode": "dedicated_persistent",
  "stage": "P4",
  "site": "cnrds",
  "acceptance_spec_sha256": "e35830fced652d41c2949166389c28c33a5d9762b091980d0dab8c200e9f8d3d",
  "artifact": {
    "path": ".aris/business-e2e/20260718T011517Z/cn-data/raw/cnrds/2026-07-18_grok_v1/cnrds-cird-000001-2020.zip",
    "format": "zip",
    "size_bytes": 1,
    "mtime_ns": "1",
    "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
  }
}
```

Do not write a success receipt, manifest, or root-verifier result. Do not claim
P4 acceptance: the external acceptor reopens the frozen spec and artifact,
checks their hashes and semantic table content, and alone writes the candidate
acceptance record.
