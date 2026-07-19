---
name: cn-data-bridge
description: Resolve and export minimal Chinese firm or market datasets from CNRDS and CSMAR through the user's authorized network and persistent Chrome session. Use for table/field resolution, DOWNLOAD_SPEC execution, verified raw extracts, browser-session receipts, and DATA_MANIFEST provenance; Codex uses native Chrome and Grok uses the official DevTools safety facade or an explicitly selected legacy real-Chrome fallback through browser-session-bridge. Not for CNKI fulltext.
---

# CN Data Bridge

Pull context: $ARGUMENTS

## Purpose

Turn a research **data gap** into a minimal, documented extract from **CNRDS** and/or **CSMAR**. This skill is **on-demand gap fill**, not bulk crawl or full-database dump.

The agent operates on the **user's network and login** (browser session for CNRDS; often campus/IP access for CSMAR downloads). Produce:

1. a resolved variable map (table/field identity)
2. a `DOWNLOAD_SPEC` when confidence is high
3. raw files under `Data/raw/csmar/<date>/` or `Data/raw/cnrds/<date>/`
4. a verified browser receipt and `MANIFEST` (plus passport update when present)

Downstream sample build and regressions belong to `data-analysis-bridge` / `r-analysis-bridge` / `stata-analysis-bridge`.

## When To Use

Use this skill when:

- `empirical-design/DATA_PLAN.md` lists CNRDS or CSMAR sources
- local files miss required Chinese firm/market variables
- the user asks to resolve, download, or document CNRDS/CSMAR fields
- analysis is blocked on a **named gap** (variables, years, universe), not a desire to “download everything”

Do **not** use this skill for:

- **CNKI** fulltext, PDF, or bibliographic harvest (method literature belongs to lit-review / method-harvest paths)
- inventing offline fake panels when access is missing
- bulk crawling whole product modules without a gap list
- WRDS pulls (use `wrds-query-bridge`)

## Inputs

Read available files in this order:

1. `empirical-design/DATA_PLAN.md`
2. `empirical-design/RESEARCH_DESIGN.md`
3. `empirical-design/TABLE_SHELLS.md` when sample filters depend on tables
4. existing variable dictionaries, codebooks, or prior download notes
5. existing `Data/DATA_MANIFEST.md`, `Data/raw/*/MANIFEST.md`, or `data/**/DATA_MANIFEST.md`
6. local raw/intermediate panels already on disk
7. `BUSINESS_RUN_PASSPORT.md` when present

Read:

- `references/variable-resolution.md` for gap inventory, multi-definition policy, and confidence gates
- `references/cnrds-csmar-adapters.md` for access modes, download steps, and landing rules
- `browser-session-bridge` plus `../shared-references/browser-session-contract.md` before any portal interaction

## Project Layout

Prefer project-local layout (create only what the pull needs):

```text
Data/
  raw/
    csmar/
      <YYYY-MM-DD>/          # immutable vendor dumps for this pull day
        ...
      MANIFEST.md            # optional source-local manifest
    cnrds/
      <YYYY-MM-DD>/
        ...
      MANIFEST.md
  intermediate/              # rebuildable cleaned extracts (later stages)
  final/                     # analysis-ready panels (later stages)
  DATA_MANIFEST.md           # project-level extract index (preferred)
  downloads/
    DOWNLOAD_SPEC_<id>.md    # approved pull specs
logs/
  cn-data/
empirical-design/
  DATA_PLAN.md
```

Path aliases:

- If the project already uses lowercase `data/`, use `data/raw/csmar|cnrds/<date>/` and keep that convention for the whole project.
- Never mix `Data/` and `data/` inside one project without recording the choice in the manifest policy block.

Date folder: use the pull calendar date in `YYYY-MM-DD` (local project timezone, default Asia/Shanghai when the project is CN-market work). Re-pulls the same day append a suffix (`_v2`, `_retry1`) rather than overwriting completed files.

## Access Model

| Source | Typical access | Agent posture |
|---|---|---|
| **CNRDS** | Personal account login; browser session reuse | Use the user's browser/session; do not store passwords or cookies in the repo |
| **CSMAR** | Often institutional **IP-based** download access | Confirm network path first; no fake “API key” inventing |
| **CNKI** | Out of scope | Refuse fulltext harvest; point to lit/method skills |

Rules:

- Credentials, cookies, session tokens, and portal passwords stay in the browser or OS secret store the user already uses. **Never** write them into markdown, scripts, YAML, logs, or passport.
- Access is **platform-agnostic**: no single university VPN name, VPN client, or lab machine is required by the skill. Site-specific steps belong in project notes or env labels (`CN_DATA_NETWORK=campus|home|vpn_label`).
- If fresh state proves login or IP access is missing, stop with `data_access_gap`. A dismissible inactivity/auto-logout overlay alone is not fresh proof: run the site recipe's close → single refresh → re-inspect recovery first. Do not fabricate extracts.

## Workflow

### Step 1: Inventory Gaps (On-Demand Only)

Build a **gap list**, not a module shopping list:

| gap_id | research_name | role | unit | years | universe | preferred_source | already_local | notes |
|---|---|---|---|---|---|---|---|---|
| g1 | ROA | outcome | firm-year | 2010–2023 | A-share non-financial | CSMAR or CNRDS | no | |

Sources for gaps:

- `DATA_PLAN.md` variable dictionary
- table shells that name measures not yet on disk
- user message listing missing fields
- merge failures documented in analysis logs

Skip variables already present with acceptable coverage (record “satisfied by local path” in the inventory).

### Step 2: Variable Resolution

For each open gap, map research concept → platform module → table → field(s). Follow `references/variable-resolution.md`.

Resolution outcomes:

| Outcome | Action |
|---|---|
| **High confidence** single definition | Write `DOWNLOAD_SPEC` and execute (Step 3–4) |
| **Multiple plausible definitions** | Ask the user **once** with a short comparison table; do not re-ask every field |
| **Ambiguous / low confidence** | Pause with options; no download |
| **Not on CNRDS/CSMAR** | Mark `source_gap`; suggest alternative source if known (do not invent coverage) |

When asking once on multi-definition conflicts, group all conflicts into a single decision block:

```markdown
# Variable Definition Decisions Needed

| gap_id | research_name | option_A | option_B | recommendation | why |
|---|---|---|---|---|---|
```

After the user answers, freeze choices into the `DOWNLOAD_SPEC` and do not reopen unless the design changes.

### Step 3: Write DOWNLOAD_SPEC

For high-confidence (or user-resolved) gaps, write:

`Data/downloads/DOWNLOAD_SPEC_<spec_id>.md`

```markdown
# DOWNLOAD_SPEC

## Identity
- spec_id:
- created_at:
- source: cnrds | csmar | mixed
- gap_ids: []

## Access Preconditions
- network: campus_ip | home | vpn_label | unknown
- login_required: yes/no
- session_reuse: yes/no (CNRDS)

## Items
| item_id | source | module_or_db | table_or_dataset | fields | filters | years | expected_format | local_relpath | status |
|---|---|---|---|---|---|---|---|---|---|
| | csmar | | | | | | csv/xlsx/zip/dta | Data/raw/csmar/<date>/... | planned |

## Variable Map
| gap_id | research_name | platform_field | definition_note | confidence |
|---|---|---|---|---|

## Execution Notes
- browser steps or portal path (no secrets)
- expected row grain
- expected identity fields and at least one domain field
- post-download checks
```

Do not execute a download without a written spec when the pull will land project files. For tiny ad-hoc probes (schema peek only), a log note is enough; still do not bulk-dump.

### Step 4: Execute Download (User Network)

Follow `references/cnrds-csmar-adapters.md` as the site recipe and invoke `browser-session-bridge` for the current runtime. The site recipe owns portal/module/filter intent; the bridge owns Codex-native versus Grok-MCP execution, authenticated-session reuse, download completion, and its redacted receipt.

Principles:

1. Download **only** rows/columns needed for open gaps (fields, years, universe filters).
2. Prefer official export formats the portal supports (csv/xlsx/dta/txt).
3. Land files under `Data/raw/<source>/<YYYY-MM-DD>/` without renaming away vendor identity; add a short sidecar `.meta.md` if the portal filename is opaque.
4. Never overwrite a completed prior extract; use a new date folder or version suffix.
5. On a recipe-identified inactivity/auto-logout overlay, invoke the bridge's one-shot soft-timeout recovery before any login or access-gap classification. Do not click an embedded re-login action during the probe.
6. Only when fresh post-recovery state still proves auth failure, captcha block, or IP deny, record `data_access_gap` and stop. Do not brute-force or bypass paywalls.
7. Arm download completion before the final export click; a portal toast or browser notification is not a landed file.

CNRDS:

- Prefer reusing an existing logged-in browser session.
- When the user has authorized it and Chrome has already filled the login form, the bridge may click the ordinary login button once without inspecting or typing the credential fields; verify the post-login state immediately.
- Navigate module → indicator/table → filter → export.
- If the fields are empty, the saved submit fails, or MFA/account choice/hard CAPTCHA is required, ask the user to complete login once, then continue.

CSMAR:

- Confirm IP/institutional access before large exports.
- If an inactivity 信息 dialog claims automatic logout and offers `重新登录`, do not press it first. Close the dialog with its top-right `×`, refresh the same CSMAR page once, wait, and re-inspect for the institutional/IP-authenticated state. Enter a login/access-gap branch only if the refreshed page still proves it. Reapply the frozen table/filter state if refresh reset the builder.
- Use the minimal query builder filters matching the gap list.
- Prefer batch export of the specified tables/fields only.

### Step 5: Verify, Manifest, Passport

For each landed file:

1. Run `skills/browser-session-bridge/scripts/verify_download.py` for csv/xlsx/zip (or `any` for a vendor format not yet supported); reject HTML, empty, corrupt, or partial files.
2. Record path, size, detected format, SHA-256, and approximate n_rows/n_cols when cheap to inspect.
3. Spot-check identity fields, requested variable fields, row grain, and date span against the `DOWNLOAD_SPEC`.
4. Save the redacted browser receipt; it must say `codex_native_chrome`, `grok_chrome_devtools_mcp`, or the explicitly selected legacy `grok_chrome_mcp` for protected-session acceptance.
5. Update `Data/DATA_MANIFEST.md` (create if missing); optionally mirror a short entry under `Data/raw/<source>/MANIFEST.md`.
6. Update `BUSINESS_RUN_PASSPORT.md` through `business-run-passport` when writing is allowed (materials, data access level, artifact index, decision log for definition choices).

Missing values remain missing at the raw layer. Do not zero-fill.

### Step 6: Handoff

Hand off to analysis skills for sample construction. This skill stops at documented raw extracts unless the user also asked for cleaning/merge.

Mark remaining gaps explicitly:

- `satisfied` — local extract covers the need
- `partial` — years/fields incomplete
- `blocked` — access or definition pending
- `out_of_scope` — not CNRDS/CSMAR (e.g. CNKI)

## MANIFEST Contract

Use this shape in `Data/DATA_MANIFEST.md` (extend columns if needed; keep required ones):

```markdown
# DATA_MANIFEST

## Policy
- skill: cn-data-bridge
- mode: on_demand_gap_fill
- sources: cnrds, csmar
- missing_value_rule: missing_is_not_zero
- path_root: Data/   # or data/
- not_in_scope: cnki_fulltext

## Extracts
| extract_id | source | module_or_db | table_or_dataset | fields_or_query | local_path | format | n_rows | n_cols | content_hash | pulled_at | filters | gap_ids | adapter | receipt_path | status | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| | cnrds \| csmar | | | | Data/raw/... | | | | sha256:... | | | | codex_native_chrome \| grok_chrome_devtools_mcp \| grok_chrome_mcp | | complete \| partial \| failed \| blocked | |

## Definition Decisions
| gap_id | research_name | chosen_definition | decided_by | decided_at |
|---|---|---|---|---|

## Access Gaps
| gap_id | blocker | evidence | next_action |
|---|---|---|---|
```

Also append project root `MANIFEST.md` rows when the project uses the shared output-manifest protocol (`skill = cn-data-bridge`, stage = implementation / data).

## P4 Acceptance

| Gate | Required evidence |
|---|---|
| Variable resolution | Frozen platform module/table/field mapping and confidence decision |
| Portal execution | Current runtime receipt from `browser-session-bridge` |
| File integrity | Deterministic verifier pass, non-empty file, size, format, SHA-256 |
| Semantic integrity | Requested identity/domain fields, row grain, filters, and date span verified |
| Provenance | DOWNLOAD_SPEC item and DATA_MANIFEST row link to the same landed artifact |

Codex and Grok require separate portal receipts. A CSMAR pass does not prove CNRDS, and a CNRDS pass does not prove CSMAR.

## Output Contract

End substantial work with:

```markdown
# CN Data Bridge Summary

## Mode
- on_demand_gap_fill: yes
- bulk_crawl: no

## Access
- CNRDS session usable: yes/no/not_attempted
- CSMAR IP/network usable: yes/no/not_attempted
- secrets written to repo: no

## Gaps
| gap_id | research_name | status | extract_id_or_blocker |

## Downloads
| extract_id | local_path | hash | status |

## Definition Decisions
## Remaining Blockers
## Next Steps
- sample build / analysis skill to run next
```

## Rules

- For local tasks, complete only the requested stage and mark downstream gaps as next-stage inputs.
- **On-demand only**: download what closes named gaps; never bulk-crawl modules “for later.”
- **User network/login**: agent does not invent credentials; CNRDS reuses personal browser session; CSMAR often needs institutional IP.
- **Variable resolution first**: multi-definition → ask once; high confidence → `DOWNLOAD_SPEC` then execute.
- Land raw files under `Data/raw/csmar|cnrds/<date>/` (or project `data/` alias) and update `MANIFEST`.
- Update passport when present and writing is allowed.
- **Not CNKI**: fulltext/method PDFs are out of scope for this skill.
- Platform-agnostic: no required VPN brand, cluster, or single-university path.
- Never overwrite completed raw dumps; version or new date folder.
- Missing is not zero at the raw layer.
- Do not commit large extracts; track hashes in the manifest.
- No secrets in files, logs, or chat beyond access boolean status.
- Route regression execution to `r-analysis-bridge` or `stata-analysis-bridge`; route WRDS work to `wrds-query-bridge`.
