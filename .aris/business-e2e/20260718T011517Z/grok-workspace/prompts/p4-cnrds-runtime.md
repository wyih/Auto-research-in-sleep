# Grok P4 CNRDS real-portal acceptance

Use `$cn-data-bridge` and `$browser-session-bridge`. Read their CNRDS recipe, shared browser-session contract, and Grok adapter before acting. This is a real independent Grok/chrome-mcp run through the user's existing Chrome state. A plan, copied Codex artifact, prior receipt, or simulated CSV is not acceptance.

## Frozen target and paths

- Run ID: `20260718T011517Z`
- Spec: `/Users/wyih/Projects/Auto-research-in-sleep/.aris/business-e2e/20260718T011517Z/cn-data/downloads/DOWNLOAD_SPEC_cnrds_cird_grok_v1.md`
- Source path: CNRDS → 创新专利研究 (CIRD) → 上市公司专利申请与获得 → 上市公司专利申请情况
- Dates: `2020-01-01` through `2020-12-31`
- Code: only `000001`
- Fields, in order: `Scode,Year,Ftyp,Aplctm,Invia,Umia,Desia,Invja,Umja,Desja`
- Expected preview: exactly 2 real data rows, both year 2020, with `Ftyp` values `上市公司本身` and `集团公司合计`
- New landing root: `/Users/wyih/Projects/Auto-research-in-sleep/.aris/business-e2e/20260718T011517Z/cn-data/raw/cnrds/2026-07-18_grok_v1/`
- Receipt: `/Users/wyih/Projects/Auto-research-in-sleep/.aris/business-e2e/20260718T011517Z/cn-data/receipts/p4-cnrds-grok.json`
- External semantic report: `/Users/wyih/Projects/Auto-research-in-sleep/.aris/business-e2e/20260718T011517Z/cn-data/receipts/semantic-extract-cnrds.json`
- Manifest: `/Users/wyih/Projects/Auto-research-in-sleep/.aris/business-e2e/20260718T011517Z/cn-data/DATA_MANIFEST.md`

Never overwrite the landing root, receipt, external semantic report, or an existing Grok manifest row. If any exists before this run, stop with `destination_collision`; do not silently switch paths. Do not inspect, copy, or use the existing Codex CNRDS ZIP/CSV/receipt as evidence.

## Only permitted browser route

Run from the supplied Grok workspace. Resolve:

```bash
BRIDGE_SKILL_DIR="$PWD/.agents/skills/browser-session-bridge"
MCP_CLIENT="$BRIDGE_SKILL_DIR/scripts/chrome_mcp_client.mjs"
DOWNLOAD_VERIFIER="$BRIDGE_SKILL_DIR/scripts/verify_download.py"
```

Every browser operation must be a separate one-shot command through `node "$MCP_CLIENT"`. Do not use Grok `search_tool`/`use_tool`, the separate `browser` MCP, built-in web search/fetch, curl, wget, requests, Playwright, AppleScript, direct CDP, direct MCP HTTP, arbitrary JavaScript, or another Chrome profile. Do not change Chrome/MCP/user configuration.

Run `self-test`, then `list-tools` only if needed. A nonzero helper exit is not evidence. Never call `chrome_get_web_content` or `chrome_javascript`. Never use an element `ref`, `refId`, stale snapshot, XPath, or saved coordinate. Never place raw helper output in a file or receipt.

The installed extension is legacy-compatible and foreground-only:

1. `tabs --url-contains "cnrds.com"` must return exactly one intended CNRDS tab and it must be `active:true`. Otherwise stop with `target_tab_not_foreground`; do not try to mutate another tab.
2. Before every browser action, reacquire the current tab with that same narrow `tabs` call. Never reuse a tab ID across state transitions.
3. Use compact `chrome_read_page` calls with a narrow CSS `selector`, `textQuery`, and/or `types`; keep each output small.
4. If an exact visible label is outside the viewport, use `exact-text --scope-selector <narrow CSS> --text <exact label> --tab-id <current id>` only to validate and scroll. It never clicks and is not acceptance evidence. Reacquire, re-read, obtain a current CSS selector, perform one native `chrome_click_element`, then verify the new state. If that native click fails or times out, treat the effect as unknown and independently re-read. Only when the expected transition did not occur may you change methods once to `exact-selector-click` with that immediately preceding fresh CSS, the same exact text, one narrow scope, and the current reacquired tab ID. Its `effect_state:attempted` is not acceptance evidence; immediately reacquire and prove the expected post-click state. Never retry either click path blindly.
5. Actions must use a fresh CSS selector from the immediately preceding page read. Do not use coordinate clicks in this run. If no unambiguous current selector exists, stop rather than guessing.
6. After any mutating-call error or timeout, the effect is unknown. Reacquire and inspect state before deciding anything; never repeat the action blindly.
7. Legacy `chrome_handle_download` is a post-click `~/Downloads` fallback, not an event arm. Call it only after the final click with a narrow non-empty `filenameContains`, bounded `lookbackMs`, and `waitForComplete:true`.

Never request, inspect, print, or persist credentials, cookies, storage, passwords, auth headers, account/session identifiers, signed URLs, URL queries/fragments, or object-storage delivery URLs. The helper's redacted `tabs` response may expose a tab/window ID transiently because the very next one-shot operation requires it; never write that ID to disk, logs, receipts, or prose.

## Authentication rule

The user has authorized one saved-login submission. If the visible foreground page is the ordinary CNRDS personal-login form and Chrome has already populated it, click the normal login button once without reading, copying, printing, or typing either field. Immediately re-read authenticated state. Record only `saved_login_submitted:true`; never record values or account identity. If the form is empty, the click fails, MFA/account choice appears, or a genuinely viewport-blocking hard CAPTCHA is present, stop with `login_required` or `captcha_required`. Do not inspect password-manager UI and do not retry login.

## Portal sequence

1. Record an ISO-8601 start time. Read the frozen spec, require the item status to be `planned`, and record the SHA-256 of those exact bytes as `DOWNLOAD_SPEC.input_sha256`. Confirm the receipt, external semantic report, landing path, and a Grok manifest row do not already exist. Preserve the exact pre-run spec and manifest bytes in unique run-local temporary files for rollback; do not mutate either live file yet.
2. Run helper `self-test`, verify the one unique foreground CNRDS tab, and navigate within the active query-free CNRDS origin only if needed. Reacquire and re-read.
3. Apply the authentication rule if required, then independently verify the signed-in portal state.
4. Resolve the frozen module/dataset path exactly: `创新专利研究 (CIRD) → 上市公司专利申请与获得 → 上市公司专利申请情况`.
5. Set custom dates to `2020-01-01` and `2020-12-31`; explicitly commit each live control and re-read both values after focus changes.
6. Choose code-selection mode, search `000001`, select only the exact result, confirm it, and re-read the selected-code summary.
7. Select exactly the ten frozen fields and CSV output. Do not add conditions or extra fields.
8. Run the portal preview. Verify exactly two real rows for `Scode=000001`, `Year=2020`, with the two expected company types. Do not count a field-label/description row as data.
9. Start the official download flow, reconcile the summary, add it to the queue, and wait in bounded steps until the queue visibly says `压缩完成`. A preview or queue row alone is not a landed file.
10. Immediately before the final queue download, snapshot only `~/Downloads` names, sizes, and modification times and record the snapshot time. Reacquire, re-read `压缩完成`, click the final download control exactly once with a fresh CSS selector, and record click time.
11. Invoke the legacy download fallback after the click with a narrow filename substring. If unsupported or timed out, poll only `~/Downloads`. Accept only a new, stable, non-partial ZIP whose mtime is later than the baseline/click window.
12. If the normal browser action leads to `ERR_BLOCKED_BY_CLIENT` or another vendor-host failure, do not extract, replay, print, persist, or fetch the temporary signed URL. Stop with `download_failed`. There is no approved arbitrary-JavaScript or direct-network fallback in this run.

## Deterministic artifact gate

Only after a new landing file is proven:

1. Create the frozen versioned landing root. Copy the newly landed ZIP there without changing the vendor filename.
2. Run `verify_download.py <zip> --expect zip --min-bytes 1024`; require `ok:true` and a clean ZIP CRC.
3. Safely extract without absolute paths, `..`, symlinks, or escaping the landing root. Require the data CSV, field-description file, and copyright/source documentation.
4. Verify the CSV independently. Detect UTF-8/UTF-8-BOM/GB18030. Require exact ordered header `Scode,Year,Ftyp,Aplctm,Invia,Umia,Desia,Invja,Umja,Desja` and require the next row to be exactly `股票代码,会计年度,公司类型,申请时间,当年独立申请的发明数量,当年独立申请的实用新型数量,当年独立申请的外观设计数量,当年联合申请的发明数量,当年联合申请的实用新型数量,当年联合申请的外观设计数量`. Classify that mandatory row as metadata and exclude it from data counts. Then require exactly two data rows, both `Scode=000001`, both `Year=2020`, and company types exactly `上市公司本身` and `集团公司合计`.
5. Preserve missing values unchanged. Record SHA-256 and bytes for outer ZIP and inner CSV, CSV encoding/rows/columns, CRC result, metadata-row classification, and mismatch counts. Rehash after all copies/extraction.
6. Re-read the still-`planned` live spec and require its hash to remain exactly `DOWNLOAD_SPEC.input_sha256`. Render the exact intended completed spec into a unique same-directory temporary file without replacing the live spec. The completed draft may change only this Grok item from `planned` to `complete` and add bounded observed completion evidence: completion time, adapter, receipt path, artifact paths/hashes, and `input_sha256`. It must not contain the receipt hash, semantic-report hash, or its own hash. Record the completed draft's SHA-256 as `DOWNLOAD_SPEC.completed_sha256`, require it to differ from `input_sha256`, and keep its bytes unchanged for the later atomic install.
7. Write the complete candidate receipt described below with `status: pending_external_verification`, both spec hashes, and only the external semantic-report path/schema—not a semantic result. Do not append the manifest or replace the live spec. Run:

   ```bash
   python3 "$PWD/.agents/skills/cn-data-bridge/scripts/verify_cn_extract.py" \
     --receipt /Users/wyih/Projects/Auto-research-in-sleep/.aris/business-e2e/20260718T011517Z/cn-data/receipts/p4-cnrds-grok.json \
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
  "subject": {"stage": "P4", "site": "cnrds", "runtime": "grok"},
  "receipt": {
    "path": ".aris/business-e2e/20260718T011517Z/cn-data/receipts/p4-cnrds-grok.json",
    "sha256": "observed_final_receipt_64_hex"
  },
  "DOWNLOAD_SPEC": {
    "path": ".aris/business-e2e/20260718T011517Z/cn-data/downloads/DOWNLOAD_SPEC_cnrds_cird_grok_v1.md",
    "input_sha256": "observed_planned_spec_64_hex",
    "completed_sha256": "observed_completed_spec_64_hex"
  },
  "verifier_report": {"replace_with_complete_parsed_second_pass_report": true}
}
```

## Receipt, manifest, and final gate

Build one redacted JSON candidate receipt with the following fields. It starts as `status: pending_external_verification` and becomes `status: passed` only through the two-pass semantic-verifier sequence above:

- `schema_version: 1`, `stage: P4`, `site: cnrds`, `source: cnrds`; candidate `status: pending_external_verification`, final `status: passed`
- `runtime: grok`, `adapter: grok_chrome_mcp`, `mcp_server: chrome-mcp`
- `started_at`, `download_started_at`, `completed_at`, and exact spec path plus distinct `input_sha256`/`completed_sha256` under `DOWNLOAD_SPEC`
- `session_reused`, `login_state`, `saved_login_submitted`, `human_handoff`
- complete frozen `query`
- `portal_evidence` containing exact dataset path, `preview_rows:2`, `preview_codes:["000001"]`, `preview_years:[2020]`, `company_types:["上市公司本身","集团公司合计"]`, and `queue_compression_complete:true`
- `download_transport` containing `ui_export_completed:true`, one final click, baseline/click/completion times, `download_event: unsupported`, `completion: fallback_directory_increment`, `temporary_url_persisted:false`, and freshness proof
- exactly one ZIP and one CSV artifact, each with project-relative `path`, `detected_format`, `size_bytes`, and `sha256`; the CSV also records rows/columns/encoding and mandatory description-row handling
- generic download-verifier result under `verifier`, plus the external hash-bound semantic-report path/schema under `semantic_verifier`; never embed the semantic result in this receipt
- all credential/cookie/session/signed-URL persistence flags explicitly false

Do not include raw helper output, tab/window IDs, account identifiers, browser history, query-bearing URLs, filenames containing query material, or any secret/session value.

The candidate must use this exact semantic shape, replacing every `observed_*` token with a real value before running the verifier:

```json
{
  "schema_version": 1,
  "stage": "P4",
  "site": "cnrds",
  "source": "cnrds",
  "status": "pending_external_verification",
  "runtime": "grok",
  "adapter": "grok_chrome_mcp",
  "mcp_server": "chrome-mcp",
  "started_at": "observed_ISO_8601",
  "download_started_at": "observed_ISO_8601",
  "completed_at": "observed_ISO_8601",
  "DOWNLOAD_SPEC": {
    "path": ".aris/business-e2e/20260718T011517Z/cn-data/downloads/DOWNLOAD_SPEC_cnrds_cird_grok_v1.md",
    "input_sha256": "observed_planned_spec_64_hex",
    "completed_sha256": "observed_completed_spec_64_hex"
  },
  "session_reused": true,
  "login_state": "already_authenticated_or_saved_login_submitted_and_verified",
  "saved_login_submitted": false,
  "human_handoff": false,
  "query": {
    "module": "创新专利研究 (CIRD) / 上市公司专利申请与获得",
    "table": "上市公司专利申请情况",
    "security_code": "000001",
    "date_start": "2020-01-01",
    "date_end": "2020-12-31",
    "selected_fields": ["Scode", "Year", "Ftyp", "Aplctm", "Invia", "Umia", "Desia", "Invja", "Umja", "Desja"]
  },
  "portal_evidence": {
    "preview_rows": 2,
    "preview_codes": ["000001"],
    "preview_years": [2020],
    "company_types": ["上市公司本身", "集团公司合计"],
    "queue_compression_complete": true
  },
  "download_transport": {
    "ui_export_completed": true,
    "final_download_clicked": true,
    "download_event": "unsupported",
    "completion": "fallback_directory_increment",
    "temporary_url_persisted": false,
    "baseline_at": "observed_ISO_8601",
    "clicked_at": "observed_ISO_8601",
    "landed_at": "observed_ISO_8601"
  },
  "artifacts": [
    {"path": ".aris/business-e2e/20260718T011517Z/cn-data/raw/cnrds/2026-07-18_grok_v1/observed_vendor.zip", "detected_format": "zip", "size_bytes": 0, "sha256": "observed_64_hex"},
    {"path": ".aris/business-e2e/20260718T011517Z/cn-data/raw/cnrds/2026-07-18_grok_v1/observed_data.csv", "detected_format": "csv", "size_bytes": 0, "sha256": "observed_64_hex", "data_rows": 2, "n_cols": 10, "encoding": "observed_encoding", "description_row_present": true}
  ],
  "verifier": {"ok": true},
  "semantic_verifier": {
    "mode": "external_hash_bound_report",
    "report_path": ".aris/business-e2e/20260718T011517Z/cn-data/receipts/semantic-extract-cnrds.json",
    "report_schema_version": "aris.cn-data-bridge.external-semantic-acceptance.v1"
  },
  "security": {"credentials_or_session_material_persisted": false, "temporary_url_persisted": false, "signed_url_persisted": false}
}
```

Append exactly one Grok extract row to `DATA_MANIFEST.md` only after both semantic passes, the external semantic report, and the exact completed-spec install succeed. It must link the exact CSV path/hash, receipt, spec, filters, `grok_chrome_mcp`, rows=2, cols=10, and `complete`. Preserve Codex rows. Do not edit the receipt, completed spec, or external semantic report after this point.

Finally run:

```bash
python3 /Users/wyih/Projects/Auto-research-in-sleep/scripts/verify_business_e2e.py --run-id 20260718T011517Z --json
```

Claim this gate only if `runtimes.grok.browser.P4_CNRDS.status` is `PASS`. Overall run incompleteness from other gates is allowed. On a failure before the finalization commit, restore/leave the pre-run manifest and `planned` spec, then write a redacted failed/blocked receipt with the exact last verified state and one concrete blocker. If the root verifier rejects after the immutable receipt/spec/report and manifest row were committed, preserve that evidence set unchanged, do not claim the gate, and report the exact failed check for external diagnosis.
