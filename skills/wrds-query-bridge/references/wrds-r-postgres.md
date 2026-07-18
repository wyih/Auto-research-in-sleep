# WRDS R Postgres Guide

Companion to `wrds-query-bridge`. Policy: `../../shared-references/business-wrds-policy.md`.

## Connection

Default WRDS Postgres endpoint:

| Setting | Default | Env override |
|---|---|---|
| host | `wrds-pgdata.wharton.upenn.edu` | `WRDS_HOST` |
| port | `9737` | `WRDS_PORT` |
| dbname | `wrds` | `WRDS_DBNAME` |
| user | — | `WRDS_USER` (required) |
| password | — | `WRDS_PASSWORD` (required) |
| sslmode | `require` | — |

Example:

```r
user <- Sys.getenv("WRDS_USER")
pass <- Sys.getenv("WRDS_PASSWORD")
if (!nzchar(user) || !nzchar(pass)) {
  stop("Set WRDS_USER and WRDS_PASSWORD in the environment.")
}

con <- DBI::dbConnect(
  RPostgres::Postgres(),
  host = Sys.getenv("WRDS_HOST", "wrds-pgdata.wharton.upenn.edu"),
  port = as.integer(Sys.getenv("WRDS_PORT", "9737")),
  dbname = Sys.getenv("WRDS_DBNAME", "wrds"),
  user = user,
  password = pass,
  sslmode = "require"
)
```

Disconnect when finished: `DBI::dbDisconnect(con)`.

Do not log `pass` or embed it in scripts.

## Packages

Typical stack:

- connection: `DBI`, `RPostgres`
- tables: `data.table` or `dplyr`
- parquet: `arrow`
- optional: `bit64` for large integer IDs

Record package versions in pull logs or passport `repro_lock` when extracts feed paper results.

## Schema Discovery

List schemas/libs the account can see:

```r
DBI::dbGetQuery(con, "SELECT DISTINCT table_schema FROM information_schema.tables ORDER BY 1")
```

Inspect columns:

```r
DBI::dbGetQuery(
  con,
  "SELECT column_name, data_type
   FROM information_schema.columns
   WHERE table_schema = $1 AND table_name = $2
   ORDER BY ordinal_position",
  params = list("comp", "funda")
)
```

WRDS library names map to Postgres schemas (for example `comp`, `crsp`, `ibes`). Exact table names depend on the subscription; verify before large pulls.

## SQL Practices

1. Project only needed columns.
2. Filter dates and share/universe codes in SQL when possible.
3. Prefer keys already documented in `DATA_PLAN.md` (for example `gvkey`, `permno`, `tic`).
4. For heavy panels, pull year-by-year or id-chunked queries and row-bind locally.
5. Save the final SQL text next to the extract or under `data/wrds/sql/`.

Minimal pattern:

```r
sql <- "
  SELECT gvkey, datadate, fyear, at, sale, ni
  FROM comp.funda
  WHERE indfmt = 'INDL'
    AND datafmt = 'STD'
    AND popsrc = 'D'
    AND consol = 'C'
    AND fyear BETWEEN 2000 AND 2024
"
df <- DBI::dbGetQuery(con, sql)
```

## Parquet Cache

```r
out <- "data/intermediate/wrds/comp_funda_2000_2024_v1.parquet"
dir.create(dirname(out), recursive = TRUE, showWarnings = FALSE)
arrow::write_parquet(df, out)
```

Hash for manifest (shell):

```bash
shasum -a 256 data/intermediate/wrds/comp_funda_2000_2024_v1.parquet
```

Or in R:

```r
digest::digest(file = out, algo = "sha256")
```

## Chunked Pulls

When a single query times out:

1. split by year or by id ranges
2. write one parquet per chunk or bind then write
3. mark each chunk or the combined extract in `DATA_MANIFEST`
4. if chunks still fail, escalate to `wrds-sas-cloud` with recorded reason — not because of a fixed row threshold

## Missing Values

After pull, summarize missingness for key fields:

```r
vapply(df, function(x) mean(is.na(x)), numeric(1))
```

Do not `replace(NA, 0)` at the pull layer. Zero-coding belongs only in analysis construction when the research design states it.

## Logging

Write a short log under `logs/wrds/<query_id>.log` with:

- start/end timestamps
- query_id
- row and column counts
- output path and hash
- warnings (truncated, retries)
- redacted error text on failure

Never include password or full connection URI with credentials.

## Bundled Helpers

```bash
skills/wrds-query-bridge/scripts/check_wrds_env.sh
skills/wrds-query-bridge/scripts/wrds_pull_template.R --help
```

`check_wrds_env.sh` only reports whether required env vars are set; it never prints secret values.
