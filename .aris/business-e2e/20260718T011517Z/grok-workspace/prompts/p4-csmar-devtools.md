# Grok P4 CSMAR official-DevTools browser candidate

Execute one real CSMAR portal export through MCP server `browser`. The browser
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
`csmar`, the exact artifact path below, ZIP format, minimum size, archive member,
ordered headers, and row assertions.
The frozen digest for this launch is
`09b498389f378b78d3f6ca9ba9a731c7f4b23c183f6dba2ef631dfc047e5f767`.

## Frozen portal target

- Stable entry: `https://data.csmar.com/csmar.html#/datacenter/singletable`
- Dataset: `财务报表 → 资产负债表`; table ID `FS_Combas`
- Filters: only code `000001`; start date `2020-12-31`; end date
  `2020-12-31`; condition `Typrep=A`
- Fields in exact order: `Stkcd`, `ShortName`, `Accper`, `Typrep`,
  `A001000000`
- Preview requirement: exactly one real row with `Stkcd=000001`,
  `Accper=2020-12-31`, `Typrep=A`, and non-empty `A001000000`
- Export format: CSV packaged by the portal as ZIP
- Candidate destination:
  `.aris/business-e2e/20260718T011517Z/cn-data/raw/csmar/2026-07-18_grok_v1/csmar-fs-combas-000001-2020.zip`

Never inspect, copy, or reuse a prior Codex or legacy artifact as evidence.

## Portal sequence

1. Find exactly one selectable `data.csmar.com` page, or exactly one selectable
   `about:blank` page when no CSMAR page exists. When duplicate CSMAR matches
   exist, accept only the facade's sole currently selected match with
   `unique=true` and `selection_basis=only_selected_match`; otherwise multiple
   or zero candidates is `target_tab_ambiguous`. Select it, navigate only to the stable entry, then
   reacquire and inspect once for any visible modal, tooltip, history panel, or
   other overlay obstructing the single-table builder. If one is visible,
   identify it only from sanitized visible state and dismiss its ordinary close
   control exactly once using the final targeted-inspect/action rule. Reacquire
   and verify both that the builder is usable and that the same overlay has not
   returned. If it returns after that one dismissal, stop with
   `portal_overlay_recurred`; never click it a second time. If no overlay is
   visible, record that observation in reasoning and continue without a click.
2. Require visible authenticated or institutional-access portal state. Do not
   operate credential UI. Resolve the frozen dataset path and independently
   verify table ID `FS_Combas`. Immediately after that identity check and before
   setting any date, code, condition, or requested field, click the builder's
   global `重置` exactly once. Reacquire and verify the default field summary is
   `已选：4/154` (the four mandatory identity fields) and that no frozen filter
   has yet been applied. This is the only permitted global reset in the run.
   From this point onward, `重置` is forbidden because it also clears dates and
   the selected code; never use it to repair field selection.
3. Set and commit each date separately, move focus, reacquire, and verify the
   displayed value. Each date `aris_fill` must return
   `value_confirmation_available=true` and `value_matches_supplied=true`.
   Reacquire the same page, take a fresh inspection, commit with `aris_key`
   `Enter`, and require `value_confirmation_available_before_key`,
   `value_matches_last_fill_before_key`,
   `value_confirmation_available_after_key`, and
   `value_matches_last_fill_after_key` all to be true. These booleans are the
   permitted value proof when the accessibility
   snapshot omits the textbox value; never request or print the raw observed
   value. Select only code `000001`: use `代码选择`, locate the exact
   `000001（平安银行）` result, add it once, require `已选代码 [1] 个`, confirm,
   and verify the builder summary still names `000001`. Keep the four mandatory
   fields selected. Do not click `全选`. Use the field search control
   `请输入关键字进行字段搜索` to search for `资产总计`, select the exact
   `A001000000` result once, and verify `已选：5/154`; if the count is not five,
   stop rather than toggling `全选` or using global reset. The resulting exact
   order must be `Stkcd`, `ShortName`, `Accper`, `Typrep`, `A001000000`.
   Set `Typrep=A`, then re-inspect and verify both frozen dates, code `000001`,
   the five-field summary, and the condition together before preview.
4. Run the official preview and require exactly one real row matching every
   frozen preview assertion. Labels, requested filters, and estimated counts are
   not preview evidence.
5. Choose CSV and click `下载数据` once. The builder may remain open while a new
   result page appears. Reacquire exactly one selectable `sdownload.html` page;
   multiple or zero matches is `target_tab_ambiguous`. Select that result page
   and reconcile table ID, both dates, one code, exact ordered fields,
   `Typrep=A`, CSV, and one record. Any mismatch is
   `result_summary_mismatch`.
6. Reacquire and re-inspect the reconciled result, then call
   `aris_trigger_element_download` exactly once on the fresh `本地保存数据`
   control. It must atomically snapshot the download directory, click once, and
   return the opaque baseline used below. This candidate permits no click retry.
7. Reacquire and inspect post-state. Call `aris_download_wait` with the opaque
   baseline, filename token `资产负债表`, and a bounded timeout. The current portal
   names the outer ZIP from the Chinese table label rather than `FS_Combas`.
   Accept only a new stable non-partial download; do not retry with a guessed
   token after a timeout.
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
  "site": "csmar",
  "acceptance_spec_sha256": "09b498389f378b78d3f6ca9ba9a731c7f4b23c183f6dba2ef631dfc047e5f767",
  "artifact": {
    "path": ".aris/business-e2e/20260718T011517Z/cn-data/raw/csmar/2026-07-18_grok_v1/csmar-fs-combas-000001-2020.zip",
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
