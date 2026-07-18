# Business WRDS Policy

Shared policy for WRDS pulls in business, accounting, finance, management, and economics projects. Both `wrds-query-bridge` and `wrds-sas-cloud` follow this document.

## Default Path: R + Postgres

Default to local R connected to WRDS Postgres:

- host: `wrds-pgdata.wharton.upenn.edu`
- port: `9737`
- dbname: `wrds`
- SSL required
- credentials only from environment: `WRDS_USER`, `WRDS_PASSWORD`

Use `wrds-query-bridge` for inventory, SQL design, pulls, parquet cache, and `DATA_MANIFEST` updates.

Do not put passwords, tokens, cookies, or connection strings with secrets into project files, logs committed to git, passport entries, or skill outputs.

## Escalation Path: SAS Cloud

Escalate to `wrds-sas-cloud` only when the R path has a concrete failure or blocker:

| Trigger | Escalate? | Record |
|---|---|---|
| Query timeout on WRDS Postgres | Yes | timeout duration, query id, last successful filter |
| Local or remote OOM / memory kill | Yes | peak memory if known, row/column attempt, machine class |
| Connection or auth failure after retries with correct env | Yes if SAS account path is available | error class, retry count |
| Hard failure (driver crash, repeated disconnect mid-pull) | Yes | error text (redacted), stage |
| Query merely large or “looks heavy” | No | stay on R; tighten filters, pull by year/chunk, or cache partials |
| Preference or habit for SAS | No | stay on R unless user explicitly requires SAS |

**No fixed row threshold.** Do not use rules such as “more than N million rows ⇒ SAS.” Size alone is not an escalation reason. Chunking, column projection, date filters, and parquet intermediate caches are preferred on the R path.

When escalating, record a short reason in:

- `data/wrds/DATA_MANIFEST.md` (or project-local equivalent)
- `analysis/ANALYSIS_LOG.md` when analysis has started
- `BUSINESS_RUN_PASSPORT.md` Decision Log when writing is allowed

Reason template:

```text
escalate_to_sas:
  reason: timeout | oom | hard_fail | auth_blocker | user_required
  query_id:
  attempted_at:
  evidence: <redacted error or log path>
  r_path_status: failed | partial
  sas_job_id_or_path:
```

## Missing Values Are Not Zero

WRDS missingness is data, not a fill strategy.

- Never recode missing numeric fields to `0` by default (returns, amounts, counts, flags, prices, spreads).
- Never treat a failed merge as a zero outcome or zero treatment without an explicit research-design rule.
- Record missing rates for key fields in the pull note or sample-build log.
- If the design requires a zero-fill (for example, non-event firm-years coded as zero for an indicator), state that rule in `empirical-design/DATA_PLAN.md` or `RESEARCH_DESIGN.md` and implement it only in analysis construction scripts, not silently at the WRDS pull layer.
- Distinguish: missing because not in universe, missing because not reported, and missing because pull filter excluded the row.

## Cache And Provenance

Every successful pull should leave:

1. local cache under `data/raw/wrds/` or `data/intermediate/wrds/` as parquet when practical
2. a `DATA_MANIFEST` row with query identity, source lib/table, filters, row/column counts, file path, content hash, pull timestamp, and backend (`r_postgres` or `sas_cloud`)
3. rebuildable SQL or SAS program path referenced from the manifest

Prefer parquet for R-facing caches. Prefer not to commit large WRDS extracts; keep them local or in agreed storage and track hashes in the manifest.

## Platform Neutrality

WRDS skills are platform-agnostic:

- do not hard-code a single university VPN, cluster queue, or Option/vendor product name as required
- SAS cloud handoff uses generic steps: submit job (`qsas` or site equivalent), transfer files (`rsync`/`scp`), verify hashes
- site-specific commands belong in project notes or env vars, not as skill defaults

## Handoff To Analysis

After pulls:

- analysis-ready panels go to `data/final/` via project build scripts
- regression execution routes to `r-analysis-bridge` or `stata-analysis-bridge`
- do not invent placeholder WRDS tables when credentials or access are missing; flag `data_access_gap`

## Security Rules

- Read credentials only from environment or an OS secret store already wired by the user.
- Never echo `WRDS_PASSWORD` in shell history helpers, skill logs, or markdown.
- Redact usernames in shared write-ups if the project requires anonymized repro notes; hashes and query ids are enough for provenance.
- Prefer project `.env` (gitignored) or shell profile over hard-coded values.
