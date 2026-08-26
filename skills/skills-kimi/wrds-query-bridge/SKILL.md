---
name: wrds-query-bridge
description: Pull and cache WRDS data through R and WRDS Postgres for business, accounting, finance, management, and economics projects. Use when the user needs WRDS SQL pulls, parquet caches, DATA_MANIFEST provenance, CRSP/Compustat/IBES/TAQ-style extracts, or a platform-agnostic alternative to ad-hoc WRDS downloads.
---

# WRDS Query Bridge

Query context: $ARGUMENTS

## Purpose

Turn a data plan into reproducible WRDS Postgres pulls via R, local parquet caches, and a `DATA_MANIFEST` that analysis skills can trust.

Default backend is **R + WRDS Postgres**. SAS cloud is an escalation path only; see `../shared-references/business-wrds-policy.md` and `wrds-sas-cloud`.

## When To Use

Use this skill when:

- the project needs WRDS libraries or tables (for example Compustat, CRSP, IBES, Thomson, BoardEx, TAQ subsets)
- `empirical-design/DATA_PLAN.md` lists WRDS sources
- the user asks to pull, refresh, or document WRDS extracts
- analysis needs parquet/csv caches with query provenance
- credentials are available as `WRDS_USER` / `WRDS_PASSWORD` (never paste secrets into chat)

Do not use this skill to invent offline fake WRDS panels when access is missing.

## Inputs

Read available files in this order:

1. `empirical-design/DATA_PLAN.md`
2. `empirical-design/RESEARCH_DESIGN.md`
3. `empirical-design/TABLE_SHELLS.md` when sample filters depend on tables
4. existing `data/wrds/DATA_MANIFEST.md` or `data/DATA_MANIFEST.md`
5. existing R pull scripts under `R/`, `scripts/`, or `data/wrds/`
6. `BUSINESS_RUN_PASSPORT.md` when present

Read:

- `../shared-references/business-wrds-policy.md` for default path, escalation, missing-value, and secret rules
- `references/wrds-r-postgres.md` for connection, SQL, and cache conventions
- `references/wrds-id-linking.md` for CCM / IBES / CUSIP identity resolution, date-valid rules, and coverage audits
- `../shared-references/business-helper-resolution.md` before invoking bundled R helpers outside the ARIS repository

## Project Layout

Use or create:

```text
data/
  raw/wrds/                 # optional immutable source dumps
  intermediate/wrds/        # rebuildable parquet caches (preferred)
  final/                    # analysis-ready panels (built later)
  wrds/
    DATA_MANIFEST.md
    sql/                    # saved .sql snippets when useful
    R/                      # pull scripts dedicated to WRDS
R/
  00_setup.R
  01_wrds_pull_*.R
logs/
  wrds/
analysis/output/
```

Prefer `data/intermediate/wrds/*.parquet` for rebuildable caches. Keep raw vendor dumps under `data/raw/wrds/` only when the project needs an immutable snapshot.

## Credentials

```bash
export WRDS_USER="your_wrds_username"
export WRDS_PASSWORD="your_wrds_password"
```

Optional:

```bash
export WRDS_HOST="wrds-pgdata.wharton.upenn.edu"
export WRDS_PORT="9737"
export WRDS_DBNAME="wrds"
```

Rules:

- never write password into scripts, YAML, markdown, or git-tracked env files
- never print `WRDS_PASSWORD` in logs
- preflight with `scripts/check_wrds_env.sh` when helpful

## Workflow

### Step 1: Inventory Need And Access

Map:

- required WRDS libs/tables and key columns
- unit of observation and merge keys
- date/range filters and universe filters
- existing local caches and their hashes
- whether `WRDS_USER` and `WRDS_PASSWORD` are set (boolean only)

If credentials are missing, stop with a `data_access_gap` note. Do not fabricate data.

### Step 2: Design Pulls

For each extract:

- write explicit SQL (prefer column lists over `SELECT *` on wide tables)
- filter early by date, share codes, industry, or id lists when the design allows
- plan chunking by year or id block for heavy tables
- assign a stable `query_id` (for example `comp_funda_ann_1990_2024_v1`)

Save SQL under `data/wrds/sql/` when the query is non-trivial.

### Step 2b: Universe Keys + Identifier Linking

**Primary production pattern (Option_listing 2026):** build a local **data universe** of keys, push with `dbplyr::copy_inline` / `inline_keys`, then join large WRDS tables remotely and `collect` only the filtered result.

```text
local universe (gvkey/fyear/datadate[/permno/windows])
  → copy_inline(keys)
  → remote join CCM / CRSP / IBES facts
  → parquet + DATA_MANIFEST
```

Read `references/wrds-id-linking.md` for CCM, **official IBES–CRSP** (`wrdsapps.ibcrsphist`), and copy_inline rules.

```bash
export WRDS_RENVIRON="/path/to/project/.Renviron"   # optional; never print password

# Preferred: universe → copy_inline → CCM (+ optional CRSP month)
Rscript "$WRDS_SKILL_DIR/scripts/wrds_universe_inline_template.R" \
  --fyear 2020 --seed-n 40 --crsp-month 2020-12 \
  --out-dir data/intermediate/wrds/links

# CCM-only smoke / audit helper
Rscript "$WRDS_SKILL_DIR/scripts/wrds_ccm_link_template.R" \
  --event-date 2020-12-31 --crsp-month 2020-12 --seed-n 30 \
  --out-dir data/intermediate/wrds/links_ccm

# IBES ↔ CRSP official link (wrdsapps.ibcrsphist, score<=2, sdate/edate)
Rscript "$WRDS_SKILL_DIR/scripts/wrds_ibes_link_template.R" \
  --statpers-start 2020-01-01 --statpers-end 2020-03-31 --seed-n 50 \
  --out-dir data/intermediate/wrds/links_ibes

# CIK ↔ gvkey: WRDS wciklink_gvkey and/or farr::gvkey_ciks
Rscript "$WRDS_SKILL_DIR/scripts/wrds_cik_gvkey_link_template.R" \
  --method auto --event-date 2020-12-31 --seed-n 40 \
  --out-dir data/intermediate/wrds/links_cik
# --method farr   # local package only (Option_listing often uses this when WRDS SEC missing)
# --method wrds   # force WRDS wrdssec.wciklink_gvkey
```

Official link tables / package objects to prefer:

| Pair | Source |
|---|---|
| gvkey ↔ permno | `crsp.ccmxpf_linktable` |
| IBES ticker ↔ permno | `wrdsapps.ibcrsphist` |
| cik ↔ gvkey | `wrdssec.wciklink_gvkey` **or** `farr::gvkey_ciks` (local; often denser offline) |

Rules:

1. Do **not** download full CRSP/IBES then invent links; use **universe + copy_inline**.
2. IBES uses **`wrdsapps.ibcrsphist`**, not fuzzy ticker matching.
3. CIK samples use **`wrdssec.wciklink_gvkey`** with date-valid windows (subscription-dependent).
4. Record coverage reports + ambiguous/unlinked audits in `DATA_MANIFEST`.
5. Never recode missing links or missing returns to zero at the link layer.
6. Large key sets: chunk `copy_inline` (see linking doc).

### Step 3: Pull With R Postgres And Cache Parquet

Use R + `RPostgres` (or project standard) against WRDS Postgres. Prefer the template:

```bash
# after env is set
Rscript "$WRDS_SKILL_DIR/scripts/wrds_pull_template.R" \
  --sql data/wrds/sql/example.sql \
  --out data/intermediate/wrds/example.parquet \
  --query-id example_v1
```

Or project scripts under `R/01_wrds_pull_*.R` following `references/wrds-r-postgres.md`.

On success:

- write parquet (preferred) or csv/rds if the project already standardizes on those
- compute a content hash
- append/update `DATA_MANIFEST`

### Step 4: Handle Failure And Escalation

On timeout, OOM, or hard failure:

1. retry once with tighter filters or year chunks if safe
2. if still failing, **do not invent a row-count threshold rule**
3. record the failure reason and route to `wrds-sas-cloud` per `business-wrds-policy.md`
4. leave partial caches marked `partial` in the manifest; never silently promote them to final

### Step 5: Write Manifest And Handoff

Update `data/wrds/DATA_MANIFEST.md` (create if missing). Update passport through `business-run-passport` when writing is allowed.

Hand analysis-ready construction to `r-analysis-bridge` / `data-analysis-bridge`. This skill stops at documented WRDS extracts unless the user also asked for sample build.

## DATA_MANIFEST Contract

Use this shape (extend columns if needed; do not drop required ones):

```markdown
# DATA_MANIFEST

## Policy
- backend_default: r_postgres
- escalation: see business-wrds-policy.md
- missing_value_rule: missing_is_not_zero

## Extracts
| query_id | backend | wrds_lib | wrds_table | sql_or_program | local_path | format | n_rows | n_cols | content_hash | pulled_at | filters | status | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| | r_postgres | | | | | parquet | | | sha256:... | | | complete \| partial \| failed | |
```

Also record escalation reasons under `## Escalations` when SAS is used later.

## Output Contract

End substantial pull work with:

```markdown
# WRDS Pull Summary

## Access
- WRDS_USER set: yes/no
- WRDS_PASSWORD set: yes/no (never print value)

## Extracts
| query_id | local_path | n_rows | hash | status |

## Missingness Notes
## Failures Or Escalations
## Next Steps
- sample build / analysis skill to run next
```

## Rules

- For local tasks, complete only the requested stage and mark downstream gaps as next-stage inputs.
- Default backend is R + WRDS Postgres; platform-agnostic (no site-specific VPN or cluster required by the skill).
- Cache parquet; document every extract in `DATA_MANIFEST`.
- Secrets stay in environment variables only.
- Missing WRDS values are not zeros; see policy.
- No fixed row-count trigger for SAS; escalate only on timeout, OOM, hard fail, auth blocker, or explicit user requirement, and record the reason.
- Never overwrite raw dumps without a new `query_id` or version suffix.
- Prefer column projection and date filters over full-table dumps.
- Do not commit large extracts; track hashes instead.
- Route regression execution to `r-analysis-bridge` or `stata-analysis-bridge`.
