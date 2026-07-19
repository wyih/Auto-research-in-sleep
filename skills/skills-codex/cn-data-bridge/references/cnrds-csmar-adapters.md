# CNRDS And CSMAR Site Recipes

Companion to `cn-data-bridge`. Describes how to obtain **on-demand** extracts using the **user's network and login**. Execute browser steps through `browser-session-bridge`; this recipe must remain free of runtime-specific tool names. This is not a bulk crawler and not a CNKI fulltext guide.

## Shared Principles

1. **Gap-fill only** — export tables/fields/years named in `DOWNLOAD_SPEC`.
2. **User access** — browser session (CNRDS) or institutional IP path (CSMAR); no skill-bundled credentials.
3. **No secrets in repo** — no passwords, cookies, tokens, or session strings in markdown, scripts, logs, or passport.
4. **Immutable raw landing** — `Data/raw/<source>/<YYYY-MM-DD>/` (or project `data/` alias).
5. **Provenance** — every landed file gets a MANIFEST row with hash and filters.
6. **Platform-agnostic** — do not hard-code one university VPN product, lab host, or portal skin as required.
7. **Out of scope** — CNKI fulltext/PDF harvest; WRDS (use `wrds-query-bridge`).
8. **Runtime separation** — Codex uses native Chrome. Grok prefers the official DevTools safety facade with its dedicated persistent profile and may use the legacy real-Chrome bridge only as an explicitly frozen fallback, selected only by `browser-session-bridge`.
9. **Orchestration is neutral** — browser state and portal mutations still go through the selected bridge, but a checked-in helper may act as its MCP client and may wait, copy, hash, inspect archives, and verify rows. Acceptance depends on the fresh artifact and receipt, not on one-by-one interactive tool calls.

## Path And Naming

```text
Data/raw/csmar/<YYYY-MM-DD>/
Data/raw/cnrds/<YYYY-MM-DD>/
Data/downloads/DOWNLOAD_SPEC_<spec_id>.md
Data/DATA_MANIFEST.md
logs/cn-data/<spec_id_or_date>.log
```

Landing rules:

| Rule | Detail |
|---|---|
| Keep vendor filenames when sensible | Preserve official export names; avoid opaque renames |
| Sidecar when needed | `<file>.meta.md` with module, table, filters, export time |
| No overwrite | Same-day re-pull → `_v2` suffix or new subfolder |
| Formats | Prefer csv/txt for analysis; accept xlsx/dta/sas7bdat if that is what the portal emits |
| Large files | Do not git-commit; hash only |

Example sidecar:

```markdown
# meta: TRD_Dalyr_2010_2023.csv

- source: csmar
- module: stock market trading (verify local portal label)
- table_or_dataset: daily quote
- fields: [list or "portal default for query"]
- filters: years=2010-2023; A-share
- download_spec: Data/downloads/DOWNLOAD_SPEC_....md
- pulled_at: ISO-8601
- notes:
```

## CNRDS Adapter

### Access Pattern

- Typical: **personal login** on the CNRDS web portal
- Prefer **session reuse** in the user's browser (already logged in)
- When an authenticated module deep link is already verified for the current portal skin, prefer it over rediscovering the module from the home-page card or library search. Reacquire after navigation and independently verify the visible module/dataset identity; a deep link is routing convenience, not identity evidence.
- If not logged in and the user has authorized saved-login submission, click the ordinary login/continue control once only when Chrome has already populated the form; do not read, copy, log, or type any credential value
- If fields are empty, the saved submit fails, or MFA/account choice/hard CAPTCHA is required: ask the user to complete login once; continue after they confirm
- Do not script password entry into project files
- Optional project labels (non-secret): `CNRDS_ACCOUNT_LABEL=personal|lab` for passport notes only

### Operator Sequence

1. Confirm `DOWNLOAD_SPEC` items with `source = cnrds`.
2. Open the CNRDS portal in the user's environment (browser tools or user-driven navigation).
3. For each item:
   - navigate to a previously verified authenticated module deep link when available; otherwise locate the module / database from the portal
   - select dataset or indicator set matching the variable map
   - set year/date and universe filters from the spec
   - select only required fields when the UI allows field picking
   - export/download
   - move/copy the file into `Data/raw/cnrds/<YYYY-MM-DD>/`
   - write sidecar meta if the filename is generic (`export.xlsx`)
4. Verify columns against the variable map.
5. Hash and append MANIFEST rows.
6. Mark item status: `complete` | `partial` | `failed` | `blocked`.
7. Preserve the bridge receipt and verifier output with the item evidence.

### Observed Export Queue Details

- After the official export request, wait for the queue row to show **压缩完成** and reconcile it with the requested dataset before the final download action.
- In the current CNRDS skin the final control can appear in accessibility state as a short private-use icon-font `StaticText`, not a button. Use the bridge's fixed queue-icon action only when there is exactly one visible **压缩完成 + 未下载** row and exactly one matching icon; ambiguity is a re-inspection condition, not permission to click several candidates.
- The portal can save ZIP bytes with a `.7z` filename. Treat detected structure as authoritative, retain the vendor filename when practical, and verify the archive plus its inner table. A filename token used for waiting should match the observed portal filename rather than forcing `.zip`.

### Session Hygiene

- Reuse one login session across items in the same work block.
- If the session expires mid-batch, pause, re-auth with user help, resume remaining items only.
- Never paste session cookies into chat or files.
- If the account lacks a module subscription, record `data_access_gap` with module name; do not scrape workarounds.

### Failure Handling (CNRDS)

| Symptom | Status | Action |
|---|---|---|
| Chrome-autofilled login form | continue once | Submit once without reading fields; verify fresh authenticated state |
| Empty/failed login, MFA, account choice, or hard captcha | `blocked` | User completes login; retry the intended data action once |
| Module not in subscription | `blocked` | `data_access_gap`; consider CSMAR equivalent if definition matches |
| Export empty | `failed` or `partial` | Loosen one filter carefully or re-check table choice |
| Portal timeout | retry once | Then stop; record log path |
| Wrong grain discovered post-download | `partial` | Keep file; fix mapping; do not delete without user OK |

## CSMAR Adapter

### Access Pattern

- Typical: institutional **IP-based** access from campus network or approved VPN path
- Some users also have personal CSMAR accounts; prefer whatever the project already uses
- Before large exports, confirm the current network can reach the download service (boolean check only)
- Optional non-secret env labels: `CN_DATA_NETWORK=campus|home|vpn_label`

### Operator Sequence

1. Confirm network path (campus IP / approved VPN). If home network without access, stop with `data_access_gap` rather than bulk retry.
2. Confirm `DOWNLOAD_SPEC` items with `source = csmar`.
3. For each item:
   - open CSMAR data browser / query UI available to the user
   - locate database → table matching the variable map
   - apply year and sample filters from the spec
   - select required fields when the builder supports selection
   - preview the exact filtered rows when preview is available
   - run query / export, then validate the separate download-summary page before the final local-save action
   - land under `Data/raw/csmar/<YYYY-MM-DD>/`
   - sidecar meta for opaque names
4. Verify fields and basic row counts when cheap.
5. Hash + MANIFEST.
6. Update item status.
7. Preserve the bridge receipt and verifier output with the item evidence.

### Observed Single-Table Flow (Current Portal Skin)

The following sequence was verified on 2026-07-18. Labels can move, so re-read the live page rather than depending on coordinates:

1. Enter **单表查询**, choose the database card, and select the exact table named by the variable map.
2. If a clean start is required, use the builder's global **重置** exactly once immediately after verifying the table identity and **before** applying dates, codes, conditions, or requested fields. Re-read the default state. On the observed balance-sheet builder this meant four mandatory identity fields (`已选：4/154`). Never use global reset after filters are frozen: it clears dates and code as well as field selection.
3. Set both time endpoints. A typed date may look changed and then silently revert; commit each date through the widget (for example, Enter or an explicit calendar-day choice), change focus, and re-read both values before preview.
4. Choose **代码选择**, search the requested code, execute the search, move the exact result into **已选代码**, confirm, and verify both the selected-code count and disabled summary field show the requested code.
5. Keep only the requested fields. Do not use **全选** as a repair action: it is a toggle and a second click can invert the intended selection. For the observed balance-sheet slice, retain the four mandatory identity fields and use field search to add only `A001000000` (`资产总计`), then verify the summary changes from `已选：4/154` to `已选：5/154`. The canonical order is `Stkcd`, `ShortName`, `Accper`, `Typrep`, and `A001000000`.
6. Use **常用条件 → 查询合并报表** when the specification requires consolidated statements; verify the condition table records `Typrep = A` rather than inferring report type from the filename.
7. Re-read the complete frozen state—both dates, selected code, field count/order, and condition—together immediately before preview. If one component is wrong, repair that component directly; do not use global reset or **全选**.
8. Run **预览数据** and verify row count, code, date, report type, and at least one requested domain value.
9. Select the requested output format and activate **下载数据**. This creates a separate `sdownload.html` result page; it is not yet proof that a local file exists.
10. On the result page, reconcile table, date range, code count, field IDs, condition expression, format, and record count with the `DOWNLOAD_SPEC`. CSMAR may retain several exact-URL `sdownload.html` sibling tabs. Claim the newest page by page identity only through the bridge's narrow CSMAR exception, then verify the complete visible summary; never infer that a same-URL tab is the intended result.
11. Arm download completion immediately before **本地保存数据**, activate it once, and verify the landed file. CSMAR may wrap a selected CSV output in a ZIP; verify both the ZIP and the inner CSV.

The result page may expose a short-lived object-storage URL. Never persist or print that URL. If normal browser saving is blocked only after the authorized UI has generated the result, use the browser-session bridge's narrowly scoped download fallback and record the transport; do not replay or generalize the signed URL.

### IP And Network Notes

- CSMAR access is often **location-dependent**. Document `network` in the download summary (`campus_ip` / `vpn_label` / `unknown`), not the raw IP address if sensitive.
- Do not hard-code a single university gateway as the skill default.
- If IP auth fails, report `data_access_gap`; suggest user switch to an authorized network. Do not attempt credential stuffing or unauthorized proxies.

### Failure Handling (CSMAR)

| Symptom | Status | Action |
|---|---|---|
| IP denied / not on allowlist | `blocked` | `data_access_gap`; switch network with user |
| Query builder rejects filter | adjust or download minimal superset | Document analysis-side filters |
| Date appears changed but reverts | retry once with explicit widget commit | Re-read both endpoint values after focus changes and before preview |
| Global reset used after filters | state invalidated | Reapply the frozen slice from the clean table state; do not infer that dates/code survived |
| Field count unexpectedly expands | stop and inspect | Do not click **全选** again; repair only the named field selection or restart the clean sequence |
| `下载数据` opens a result page but no file lands | expected intermediate step | Reconcile the result summary, then arm completion before `本地保存数据` |
| Export size limit | split by year or code ranges | Multiple MANIFEST rows; same `gap_ids` |
| Truncated file | `partial` or `failed` | Re-download; do not mark complete without hash |
| Table renamed in portal UI | re-resolve variable | Update spec; keep audit trail |

## Mixed-Source Specs

A single `DOWNLOAD_SPEC` may list both CNRDS and CSMAR items when gaps split across portals.

Rules:

- Execute per-item with the correct adapter
- One MANIFEST, multiple `source` values
- Do not merge raw vendor files into one “combined raw” blob; keep source folders separate
- Analysis stage performs merges

## Verification Checklist

Before marking an extract `complete`:

- [ ] Path is under `Data/raw/csmar|cnrds/<date>/` (or project `data/` alias)
- [ ] File non-empty; format identifiable
- [ ] Required fields from variable map present (names or clearly documented renames)
- [ ] Year/date span plausible vs filters
- [ ] `sha256` recorded
- [ ] `DOWNLOAD_SPEC` item status updated
- [ ] No secrets in sidecar, log, or MANIFEST

Quick hash:

```bash
shasum -a 256 Data/raw/csmar/2026-07-17/example.csv
```

Optional row peek (example; use project language):

```bash
# csv header only
head -n 1 Data/raw/csmar/2026-07-17/example.csv
```

## MANIFEST Row Mapping

| DOWNLOAD_SPEC field | MANIFEST column |
|---|---|
| item_id | extract_id (or prefix with source) |
| source | source |
| module_or_db | module_or_db |
| table_or_dataset | table_or_dataset |
| fields | fields_or_query |
| filters + years | filters |
| local_relpath | local_path |
| format | format |
| gap_ids | gap_ids |
| status | status |

Always set `content_hash` and `pulled_at` on success.

## Logging

Write `logs/cn-data/<spec_id>.log` (or dated log) with:

- start/end timestamps
- network label (not raw IP unless user wants it)
- items attempted
- paths and hashes
- redacted errors
- definition decision references

Never log passwords, cookies, or full session headers.

## Passport Touchpoints

When `BUSINESS_RUN_PASSPORT.md` exists and writing is allowed, update via `business-run-passport`:

- **materials / data_access_level** — e.g. local CNRDS/CSMAR extracts present; access `verified_only` raw stays local
- **artifact_index** — MANIFEST path, raw folder paths, DOWNLOAD_SPEC paths
- **decision_log** — multi-definition choices frozen
- **repro_lock** — hashes of extracts that feed results (when analysis later depends on them)

Do not paste account identifiers that the project wants anonymized; extract_id + hash is enough.

## Explicit Non-Goals

| Non-goal | Why |
|---|---|
| Bulk crawl entire CNRDS/CSMAR libraries | Violates on-demand policy; wastes quota and obscures provenance |
| CNKI fulltext download | Different skill lane (method/lit harvest) |
| Headless credential stuffing | Security and ToS risk |
| Fabricating panels offline | Honesty / data integrity |
| Zero-filling missing vendor values | Missing is data |
| Requiring one branded VPN client | Breaks platform neutrality |

## Minimal End-To-End Sketch

1. Gaps: daily return + annual total assets, 2015–2022.
2. High confidence on both after portal check; no multi-definition ask.
3. Write `Data/downloads/DOWNLOAD_SPEC_ret_at_v1.md`.
4. CSMAR IP OK → export two tables only → `Data/raw/csmar/2026-07-17/`.
5. Hash files; update `Data/DATA_MANIFEST.md`.
6. Summary shows both gaps `satisfied`; next step `data-analysis-bridge` sample build.
