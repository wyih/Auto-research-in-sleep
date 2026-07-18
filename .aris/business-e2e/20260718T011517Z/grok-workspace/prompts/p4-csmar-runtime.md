# Grok P4 CSMAR real-portal acceptance

Use `$cn-data-bridge` and `$browser-session-bridge`. Read their CSMAR recipe, shared browser-session contract, and Grok adapter before acting. This is a real independent Grok/chrome-mcp run through the user's existing Chrome state. A plan, description, copied Codex file, or prior receipt is not acceptance.

## Frozen target and paths

- Run ID: `20260718T011517Z`
- Spec: `/Users/wyih/Projects/Auto-research-in-sleep/.aris/business-e2e/20260718T011517Z/cn-data/downloads/DOWNLOAD_SPEC_csmar_fs_combas_grok_v1.md`
- Source: CSMAR, `财务报表 → 资产负债表`, table `FS_Combas`
- Direct entry: `https://data.csmar.com/csmar.html#/datacenter/singletable`
- Filters: only `Stkcd=000001`; start and end both `2020-12-31`; `Typrep=A`
- Fields, in order: `Stkcd,ShortName,Accper,Typrep,A001000000`
- Expected preview: exactly one real row; matching code/date/type; total assets non-empty
- New landing root: `/Users/wyih/Projects/Auto-research-in-sleep/.aris/business-e2e/20260718T011517Z/cn-data/raw/csmar/2026-07-18_grok_v1/`
- Receipt: `/Users/wyih/Projects/Auto-research-in-sleep/.aris/business-e2e/20260718T011517Z/cn-data/receipts/p4-csmar-grok.json`
- External semantic report: `/Users/wyih/Projects/Auto-research-in-sleep/.aris/business-e2e/20260718T011517Z/cn-data/receipts/semantic-extract-csmar.json`
- Manifest: `/Users/wyih/Projects/Auto-research-in-sleep/.aris/business-e2e/20260718T011517Z/cn-data/DATA_MANIFEST.md`

Never overwrite the landing root, receipt, external semantic report, or an existing Grok manifest row. If any exists before this run, stop with `destination_collision`; do not rename silently. Do not inspect, copy, or use the existing Codex CSMAR ZIP/CSV/receipt as evidence.

## Only permitted browser route

Run from the supplied Grok workspace. Resolve:

```bash
BRIDGE_SKILL_DIR="$PWD/.agents/skills/browser-session-bridge"
MCP_CLIENT="$BRIDGE_SKILL_DIR/scripts/chrome_mcp_client.mjs"
DOWNLOAD_VERIFIER="$BRIDGE_SKILL_DIR/scripts/verify_download.py"
```

Every browser operation must be a separate one-shot command through `node "$MCP_CLIENT"`. Do not use Grok `search_tool`/`use_tool`, the separate `browser` MCP, built-in web search/fetch, curl, wget, requests, Playwright, AppleScript, direct CDP, direct MCP HTTP, arbitrary JavaScript, or another Chrome profile. Do not change Chrome/MCP/user configuration.

Run `self-test`, then `list-tools` only if needed. A nonzero helper exit is not evidence. Never call `chrome_get_web_content` or `chrome_javascript`. Never use an element `ref`, `refId`, stale snapshot, XPath, or a saved coordinate. Never place raw helper output in a file or receipt.

The installed extension is legacy-compatible and foreground-only:

1. For initial entry only, `tabs --url-contains "data.csmar.com"` must return exactly one intended active CSMAR tab. After navigating to the frozen builder route, every builder operation must instead use the legacy-stable filter `tabs --url-contains "csmar.html"`; the old chrome-mcp may omit the SPA fragment even when Chrome's address bar shows it. The immediately following compact page read must independently confirm the single-table builder state. After `下载数据` opens the result page, every result-page/local-save operation must use `tabs --url-contains "sdownload.html"`. Each stage must return exactly one `active:true` match; otherwise stop with `target_tab_not_foreground`.
2. Before every browser action, reacquire the current tab with the current stage's route-specific `tabs` call. Never reuse a tab ID across state transitions.
3. Use compact `chrome_read_page` calls with a narrow CSS `selector`, `textQuery`, and/or `types`; keep each output small.
4. If an exact visible label is outside the viewport, use `exact-text --scope-selector <narrow CSS> --text <exact label> --tab-id <current id>` only to validate and scroll. It never clicks and is not acceptance evidence. Reacquire, re-read, obtain a current CSS selector, perform one native `chrome_click_element`, then verify the new state. If that native click fails or times out, treat the effect as unknown and independently re-read. Only when the expected transition did not occur may you change methods once to `exact-selector-click` with that immediately preceding fresh CSS, the same exact text, one narrow scope, and the current reacquired tab ID. Its `effect_state:attempted` is not acceptance evidence; immediately reacquire and prove the expected post-click state. Never retry either click path blindly.
5. Actions must use a fresh CSS selector from the immediately preceding page read. Do not use coordinate clicks in this run. If no unambiguous current selector exists, stop rather than guessing.
6. After any mutating-call error or timeout, the effect is unknown. Reacquire and inspect state before deciding anything; never repeat the action blindly.
7. Legacy `chrome_handle_download` is a post-click `~/Downloads` fallback, not an event arm. Call it only after the final click with a narrow non-empty `filenameContains`, bounded `lookbackMs`, and `waitForComplete:true`.

Never request, inspect, print, or persist credentials, cookies, storage, passwords, auth headers, account/session identifiers, raw IP addresses, signed URLs, query-bearing delivery URLs, or object-storage URLs. The helper's redacted `tabs` response may expose a tab/window ID transiently because the very next one-shot operation requires it; never write that ID to disk, logs, receipts, or prose. The frozen credential-free hash route `csmar.html#/datacenter/singletable` may be used for navigation but must not be copied into the receipt. The receipt may record only `institutional_access_observed: true|false`.

## Portal sequence

1. Record an ISO-8601 start time. Read the frozen spec, require the item status to be `planned`, and record the SHA-256 of those exact bytes as `DOWNLOAD_SPEC.input_sha256`. Confirm the receipt, external semantic report, landing path, and a Grok manifest row do not already exist. Preserve the exact pre-run spec and manifest bytes in unique run-local temporary files for rollback; do not mutate either live file yet.
2. Run helper `self-test`, verify the one unique foreground CSMAR tab with the initial domain filter, and navigate that active tab to the frozen credential-free hash entry. Once loaded, reacquire only with the legacy-stable `csmar.html` filter and re-read enough bounded state to confirm the single-table builder before any action.
3. Confirm institutional access from visible portal state. Record only the boolean category. If denied, stop with `data_access_gap`.
4. Use the direct single-table query flow, not a home-page carousel. Resolve `财务报表 → 资产负债表` and independently confirm table ID `FS_Combas`.
5. Set the start date to `2020-12-31`, explicitly commit it through the live control, change focus, then re-read the value. Repeat independently for the end date. If either reverts, retry that date once from fresh state; a second failure is `filter_commit_failed`.
6. Choose code mode, search `000001`, select only that exact result, confirm it, and re-read the selected-code summary.
7. Select exactly the five frozen fields and no others. Under `常用条件`, set `查询合并报表` and verify the condition table visibly records `Typrep = A`.
8. Run `预览数据`. Verify exactly one row and visible values `Stkcd=000001`, `Accper=2020-12-31`, `Typrep=A`, with non-empty `A001000000`. Do not treat a page label or planned filter as preview evidence.
9. Choose CSV output when offered and click `下载数据` once. Discard the builder tab ID. Require the resulting `sdownload.html` tab to be the unique foreground route match, then reconcile all of: table `FS_Combas`, both dates, one selected code, exact five fields, condition `Typrep=A`, CSV format, and one record. If anything differs, stop with `result_summary_mismatch`; do not switch back to the builder.
10. Immediately before `本地保存数据`, snapshot only `~/Downloads` names, sizes, and modification times and record the snapshot time; do not search elsewhere. Reacquire only through the `sdownload.html` route filter, re-read, click `本地保存数据` exactly once with a fresh CSS selector, and record click time.
11. Invoke the legacy download fallback after the click with a narrow filename substring observed from the query-free result page. If unsupported or timed out, poll only `~/Downloads`. Accept only a new, stable, non-partial ZIP whose mtime is later than the baseline/click window. A same hash is allowed only with this independent freshness proof.

## Deterministic artifact gate

Only after a new landing file is proven:

1. Create the frozen versioned landing root. Copy the newly landed ZIP there without changing the vendor filename.
2. Run `verify_download.py <zip> --expect zip --min-bytes 1024`; require `ok:true` and a clean ZIP CRC.
3. Safely extract without absolute paths, `..`, symlinks, or escaping the landing root. Require `FS_Combas.csv`; preserve any vendor field-description/copyright files.
4. Verify the CSV independently: detected encoding; exact ordered header `Stkcd,ShortName,Accper,Typrep,A001000000`; exactly one data row after excluding a genuine vendor label row; `Stkcd=000001`; `Accper=2020-12-31`; `Typrep=A`; non-empty parseable `A001000000`. Preserve missing values and amounts exactly.
5. Record SHA-256 and bytes for the outer ZIP and inner CSV, plus CSV rows, columns, encoding, CRC result, and mismatch counts. Rehash after all copies/extraction.
6. Re-read the still-`planned` live spec and require its hash to remain exactly `DOWNLOAD_SPEC.input_sha256`. Render the exact intended completed spec into a unique same-directory temporary file without replacing the live spec. The completed draft may change only this Grok item from `planned` to `complete` and add bounded observed completion evidence: completion time, adapter, receipt path, artifact paths/hashes, and `input_sha256`. It must not contain the receipt hash, semantic-report hash, or its own hash. Record the completed draft's SHA-256 as `DOWNLOAD_SPEC.completed_sha256`, require it to differ from `input_sha256`, and keep its bytes unchanged for the later atomic install.
7. Write the complete candidate receipt described below with `status: pending_external_verification`, both spec hashes, and only the external semantic-report path/schema—not a semantic result. Do not append the manifest or replace the live spec. Run:

   ```bash
   python3 "$PWD/.agents/skills/cn-data-bridge/scripts/verify_cn_extract.py" \
     --receipt /Users/wyih/Projects/Auto-research-in-sleep/.aris/business-e2e/20260718T011517Z/cn-data/receipts/p4-csmar-grok.json \
     --repo-root /Users/wyih/Projects/Auto-research-in-sleep \
     --run-dir /Users/wyih/Projects/Auto-research-in-sleep/.aris/business-e2e/20260718T011517Z \
     --runtime grok
   ```

   Require exit 0, schema `aris.cn-data-bridge.extract-verification.v1`, matching site/runtime, and `ok:true`; do not replace it with receipt assertions and do not write this output into the candidate receipt.
8. Only after that first pass, atomically change only the candidate receipt's `status` to `passed`. Keep both spec hashes and the external-report pointer unchanged; do not embed any semantic-verifier output or `semantic_verifier.ok`. Compute the SHA-256 of this final receipt, then treat it as byte-immutable on the success path.
9. Run the same semantic-verifier command once more against that final receipt. Capture its bounded JSON in a unique temporary file, require the same schema/site/runtime/`ok:true` checks, and confirm the final receipt's SHA-256 is unchanged. Do not create the external semantic report yet. If this second pass fails, atomically rewrite the receipt as blocked/failed, leave the live spec `planned`, and stop.
10. Only after both semantic passes and the receipt-hash check succeed, atomically replace the live spec with the unchanged completed draft and require its installed hash to equal `DOWNLOAD_SPEC.completed_sha256`; then atomically append the manifest row described below. Finally, atomically create the external semantic report with the exact shape below, embedding the captured second-pass report and binding it to the final receipt hash. Rehash the receipt once more and require the same value; never put the external report's hash back into the receipt. Remove only this run's temporary files. If a finalization write fails before the external report is committed, restore the saved pre-run spec/manifest bytes, rewrite the receipt as blocked/failed, and do not create a passed external semantic report.

The external semantic report must be independently re-verifiable and must not be discovered as another P4 browser receipt. Its top level therefore has no `stage`, `site`, `source`, `runtime`, `adapter`, `gate`, or `acceptance_id`; those values live only under `subject`:

```json
{
  "schema_version": "aris.cn-data-bridge.external-semantic-acceptance.v1",
  "status": "passed",
  "verified_at": "observed_ISO_8601",
  "subject": {"stage": "P4", "site": "csmar", "runtime": "grok"},
  "receipt": {
    "path": ".aris/business-e2e/20260718T011517Z/cn-data/receipts/p4-csmar-grok.json",
    "sha256": "observed_final_receipt_64_hex"
  },
  "DOWNLOAD_SPEC": {
    "path": ".aris/business-e2e/20260718T011517Z/cn-data/downloads/DOWNLOAD_SPEC_csmar_fs_combas_grok_v1.md",
    "input_sha256": "observed_planned_spec_64_hex",
    "completed_sha256": "observed_completed_spec_64_hex"
  },
  "verifier_report": {"replace_with_complete_parsed_second_pass_report": true}
}
```

## Receipt, manifest, and final gate

Build one redacted JSON candidate receipt with the following fields. It starts as `status: pending_external_verification` and becomes `status: passed` only through the two-pass semantic-verifier sequence above:

- `schema_version: 1`, `stage: P4`, `site: csmar`, `source: csmar`; candidate `status: pending_external_verification`, final `status: passed`
- `runtime: grok`, `adapter: grok_chrome_mcp`, `mcp_server: chrome-mcp`
- `started_at`, `download_started_at`, `completed_at`, and exact spec path plus distinct `input_sha256`/`completed_sha256` under `DOWNLOAD_SPEC`
- `session_reused`, `login_state`, `human_handoff`, and `institutional_access_observed`
- complete frozen `query`
- `portal_evidence` containing exact `preview_rows`, `preview_code`, `preview_date`, `preview_report_type`, `preview_total_assets_nonempty`, plus a complete nested `result_page`
- nested `result_page` with `reconciled:true`, table ID, both dates, code count/list, exact selected fields, condition, format, and record count
- `download_transport` containing `ui_export_completed:true`, `ui_local_save_clicked:true`, one final click, baseline/click/completion times, `download_event: unsupported`, `completion: fallback_directory_increment`, `temporary_url_persisted:false`, and freshness proof
- exactly one ZIP and one CSV artifact, each with project-relative `path`, `detected_format`, `size_bytes`, and `sha256`; the CSV also records rows/columns/encoding
- generic download-verifier result under `verifier`, plus the external hash-bound semantic-report path/schema under `semantic_verifier`; never embed the semantic result in this receipt
- all credential/cookie/session/signed-URL/raw-IP persistence flags explicitly false

Do not include raw helper output, tab/window IDs, account identifiers, browser history, query-bearing URLs, filenames containing query material, or any secret/session value.

The candidate must use this exact semantic shape, replacing every `observed_*` token and both zero byte sizes with real values before running the verifier:

```json
{
  "schema_version": 1,
  "stage": "P4",
  "site": "csmar",
  "source": "csmar",
  "status": "pending_external_verification",
  "runtime": "grok",
  "adapter": "grok_chrome_mcp",
  "mcp_server": "chrome-mcp",
  "started_at": "observed_ISO_8601",
  "download_started_at": "observed_ISO_8601",
  "completed_at": "observed_ISO_8601",
  "DOWNLOAD_SPEC": {
    "path": ".aris/business-e2e/20260718T011517Z/cn-data/downloads/DOWNLOAD_SPEC_csmar_fs_combas_grok_v1.md",
    "input_sha256": "observed_planned_spec_64_hex",
    "completed_sha256": "observed_completed_spec_64_hex"
  },
  "session_reused": true,
  "login_state": "already_authenticated_or_not_required",
  "human_handoff": false,
  "institutional_access_observed": true,
  "query": {
    "module": "财务报表",
    "table": "资产负债表",
    "table_id": "FS_Combas",
    "security_code": "000001",
    "date_start": "2020-12-31",
    "date_end": "2020-12-31",
    "condition": "Typrep=A",
    "selected_fields": ["Stkcd", "ShortName", "Accper", "Typrep", "A001000000"]
  },
  "portal_evidence": {
    "preview_rows": 1,
    "preview_code": "000001",
    "preview_date": "2020-12-31",
    "preview_report_type": "A",
    "preview_total_assets_nonempty": true,
    "result_page": {
      "reconciled": true,
      "table_id": "FS_Combas",
      "date_start": "2020-12-31",
      "date_end": "2020-12-31",
      "code_count": 1,
      "security_codes": ["000001"],
      "selected_fields": ["Stkcd", "ShortName", "Accper", "Typrep", "A001000000"],
      "condition": "Typrep=A",
      "export_summary_rows": 1,
      "export_summary_format": "csv"
    }
  },
  "download_transport": {
    "ui_export_completed": true,
    "ui_local_save_clicked": true,
    "browser_download_event_observed": false,
    "download_event": "unsupported",
    "completion": "fallback_directory_increment",
    "temporary_url_persisted": false,
    "baseline_at": "observed_ISO_8601",
    "clicked_at": "observed_ISO_8601",
    "landed_at": "observed_ISO_8601"
  },
  "artifacts": [
    {"path": ".aris/business-e2e/20260718T011517Z/cn-data/raw/csmar/2026-07-18_grok_v1/observed_vendor.zip", "detected_format": "zip", "size_bytes": 0, "sha256": "observed_64_hex"},
    {"path": ".aris/business-e2e/20260718T011517Z/cn-data/raw/csmar/2026-07-18_grok_v1/FS_Combas.csv", "detected_format": "csv", "size_bytes": 0, "sha256": "observed_64_hex", "data_rows": 1, "n_cols": 5, "encoding": "observed_encoding"}
  ],
  "verifier": {"ok": true},
  "semantic_verifier": {
    "mode": "external_hash_bound_report",
    "report_path": ".aris/business-e2e/20260718T011517Z/cn-data/receipts/semantic-extract-csmar.json",
    "report_schema_version": "aris.cn-data-bridge.external-semantic-acceptance.v1"
  },
  "security": {"credentials_or_session_material_persisted": false, "temporary_url_persisted": false, "signed_url_persisted": false, "raw_ip_persisted": false}
}
```

Append exactly one Grok extract row to `DATA_MANIFEST.md` only after both semantic passes, the external semantic report, and the exact completed-spec install succeed. It must link the exact CSV path/hash, receipt, spec, filters, `grok_chrome_mcp`, rows=1, cols=5, and `complete`. Preserve Codex rows. Do not edit the receipt, completed spec, or external semantic report after this point.

Finally run:

```bash
python3 /Users/wyih/Projects/Auto-research-in-sleep/scripts/verify_business_e2e.py --run-id 20260718T011517Z --json
```

Claim this gate only if `runtimes.grok.browser.P4_CSMAR.status` is `PASS`. Overall run incompleteness from other gates is allowed. On a failure before the finalization commit, restore/leave the pre-run manifest and `planned` spec, then write a redacted failed/blocked receipt with the exact last verified state and one concrete blocker. If the root verifier rejects after the immutable receipt/spec/report and manifest row were committed, preserve that evidence set unchanged, do not claim the gate, and report the exact failed check for external diagnosis.
