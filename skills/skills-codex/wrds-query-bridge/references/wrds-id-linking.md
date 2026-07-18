# WRDS Identifier Linking (CCM / IBES / Universe + copy_inline)

Generic linking for business empirical projects. Patterns follow production usage in Option_listing (2026 `inline_keys` / `copy_inline`, and pre-2026 IBES via `wrdsapps.ibcrsphist`).

**Not** project-specific sample sizes. Prefer official WRDS link tables. Never invent ticker fuzzy matches as the default path.

---

## Core pattern: universe first, then remote filter (copy_inline)

This is the main efficiency pattern for “small sample later, large tables on WRDS.”

```text
1. Build local DATA UNIVERSE (keys only)
   e.g. gvkey–fyear–datadate, or gvkey–fyear–datadate–permno–fybeg–fyend
2. Push keys to WRDS with dbplyr::copy_inline() / inline_keys()
   (no temp-table privileges required)
3. inner_join / semi_join large remote tables ON those keys
4. collect() only the filtered result → parquet + DATA_MANIFEST
5. Further research merges across local caches
```

| Anti-pattern | Preferred |
|---|---|
| `SELECT *` full CRSP/OM then local filter | `copy_inline(universe)` then join remote |
| Huge `IN ('000001',…)` strings for large key sets | `copy_inline` (chunk if > ~50k rows) |
| Resolve links after downloading entire fact tables | Resolve CCM/IBES links → attach facts with key filter |

Helper shape (from Option_listing `source/2026/00_wrds_connection.R`):

```r
inline_keys <- function(con, data, ..., max_rows = 50000L) {
  # select key columns, distinct, collect locally if needed
  dbplyr::copy_inline(con, data)
}
```

Templates:

- `scripts/wrds_universe_inline_template.R` — universe → copy_inline → remote join demo
- `scripts/wrds_ccm_link_template.R` — CCM date-valid + coverage (+ optional CRSP month)
- `scripts/wrds_ibes_link_template.R` — `wrdsapps.ibcrsphist` date-valid ticker–permno

See also `business-wrds-policy.md` (R default, SAS escalation, missing ≠ 0).

---

## Compustat gvkey ↔ CRSP permno (CCM)

### Table

| Item | Value |
|---|---|
| Table | `crsp.ccmxpf_linktable` |
| Keys | `gvkey`, `lpermno` → `permno` |
| Window | `linkdt`, `linkenddt` |
| Quality | `linktype`, `linkprim`, `usedflag` |

### Default filters (production default)

```text
linktype  IN ('LU', 'LC')
linkprim  IN ('P', 'C')
usedflag  == 1
```

### Date-valid rule

For observation date `event_date` (often Compustat `datadate`):

```text
event_date >= coalesce(linkdt, 1900-01-01)
event_date <= coalesce(linkenddt, 2100-12-31)
```

When joining CRSP monthly on `date` (month-start or calendar date as in your CRSP file):

```text
date >= linkdt AND date <= coalesce(linkenddt, 2100-12-31)
```

### gvkey format

Zero-pad to **6 characters** before join.

### Duplicates

Multiple date-valid rows for one `(gvkey, event_date)`:

1. Write audit CSV.
2. Do **not** silent `first()`.
3. Optional pre-registered tie-break only if documented.

### Coverage metrics

| Metric | Meaning |
|---|---|
| `n_input_keys` / firm-dates | Universe size |
| `n_date_valid_unique` | Usable unique links |
| `n_ambiguous` | Multi-link firm-dates |
| `n_unlinked` | No date-valid link |
| `link_rate` | unique / input |

Missing link ≠ zero return.

### With universe + copy_inline

Preferred when the universe is already known (Option_listing 2026 style):

```r
# remote CCM (filtered)
ccm <- wrds_table(con, "crsp", "ccmxpf_linktable") |>
  filter(linktype %in% c("LU", "LC"), linkprim %in% c("P", "C"), usedflag == 1)

# restrict large CRSP pull to universe gvkeys
crsp_for_universe <- crsp_monthly_remote(con, ...) |>
  inner_join(ccm, by = "permno") |>
  filter(date >= linkdt, date <= linkenddt) |>
  inner_join(inline_keys(con, universe, gvkey), by = "gvkey")
```

For small one-off audits, `wrds_ccm_link_template.R` may use a bounded key list; production pipelines should use **universe + copy_inline**.

---

## IBES ↔ CRSP (official link table)

**Do not** treat raw IBES ticker as a permanent firm id without the WRDS link product.

### Official table (Option_listing usage)

| Item | Value |
|---|---|
| Table | `wrdsapps.ibcrsphist` |
| Keys | IBES `ticker` ↔ CRSP `permno` |
| Window | `sdate`, `edate` |
| Quality | `score` (keep higher quality; production often `score <= 2`) |

References in Option_listing:

- `source/cs_analyst_coverage.R`
- `source/2025/1.wrds.R` (same table + date filter)

### Default filters

```text
score <= 2
select ticker, permno, sdate, edate
```

### Date-valid rule

For IBES statistical period `statpers` (or other event date `d`):

```text
sdate <= d AND d <= edate
```

Example flow:

```text
ibes.statsumu_epsus (filters: fpi, measure, usfirm, …)
  |> join ibcrsphist on ticker
  |> filter(sdate <= statpers, statpers <= edate)
  |> (optional) join CRSP/Compustat via permno / CCM to gvkey
```

### Coverage

Report:

- % IBES rows with date-valid `ibcrsphist` link
- % linked permnos that also map to sample `gvkey` (via CCM or CRSP panel)

### CUSIP

Prefer **ibcrsphist + CCM** over CUSIP string equality. Historical CUSIP length/header differences make CUSIP a last resort; if used, document normalization and match rate.

---

## CIK ↔ Compustat gvkey (SEC filings / 13F / governance)

When data are keyed by **SEC CIK** (Edgar, some ownership/governance extracts) and the sample is **gvkey**, use a **date-valid CIK–gvkey link table** — not free-text company names.

Option_listing uses **two methods**. Prefer WRDS when the subscription works; otherwise use the R package path (often denser in practice).

### Method A — WRDS `wrdssec.wciklink_gvkey`

| Item | Value |
|---|---|
| Table | `wrdssec.wciklink_gvkey` |
| Keys | `cik` ↔ `gvkey` |
| Window | `link_start_date`, `link_end_date` (often renamed `first_date` / `last_date`) |

References: `source/cs_board_size.R`, `source/2025/1.wrds.R` (comment: some accounts lack this library).

```text
filter !is.na(gvkey), !is.na(link_start_date)
if link_end_date is NA → coalesce to today() or 2100-12-31
date-valid: event_date between link_start_date and link_end_date
```

```r
left_join(
  filings_or_holders,   # cik, date
  wciklink,             # cik, gvkey, first_date, last_date
  join_by(cik, between(date, first_date, last_date))
)
```

**Access caveat:** some WRDS logins can see columns in `information_schema` but fail with
`permission denied for schema wrdssec_common`. Treat as `data_access_gap` → Method B or a local cached extract.

### Method B — R package `farr::gvkey_ciks` (local, no WRDS SEC schema)

| Item | Value |
|---|---|
| Package | [`farr`](https://cran.r-project.org/package=farr) (Financial Accounting Research Resources) |
| Object | `farr::gvkey_ciks` (data frame shipped with the package) |
| Columns | `gvkey`, `iid`, `cik`, `first_date`, `last_date` |
| Network | **None** once `farr` is installed |

Option_listing usage:

- `source/cs_board_size.R` — `left_join(gvkey_ciks, join_by(cik, between(date, first_date, last_date)))`
  Comment in code: **用这个匹配出来的多一些** (often more matches than WRDS for that project).
- `source/2025/1.wrds.R` — same idea; compares WRDS pull vs `farr`.
- `source/2025/3.merge.R` — also joins **from gvkey panels** to attach CIK:
  `join_by(gvkey, between(datadate, first_date, last_date))`.

```r
# install.packages("farr")  # once
library(farr)   # exports gvkey_ciks
# or: links <- farr::gvkey_ciks

# CIK-dated events → gvkey
events |>
  mutate(cik = as.integer(cik)) |>
  left_join(
    gvkey_ciks,
    join_by(cik, between(date, first_date, last_date))
  )

# gvkey-dated panel → cik (also supported)
panel |>
  left_join(
    gvkey_ciks,
    join_by(gvkey, between(datadate, first_date, last_date))
  )
```

**Rules for Method B:**

1. Zero-pad `gvkey` to 6 chars after join if downstream expects Compustat format.
2. Coerce `cik` type consistently (`integer` vs `character` / leading zeros) before join.
3. Still audit one-to-many `(cik, date)` or `(gvkey, date)` links.
4. Record in `DATA_MANIFEST`: `backend=farr_gvkey_ciks`, package version if available.
5. Package data can lag the latest SEC filings — fine for historical samples; re-check coverage for very recent years.

### Which method to use

| Situation | Choice |
|---|---|
| WRDS SEC link works | Method A (or both for reconciliation) |
| `wrdssec_common` permission denied / no subscription | **Method B (`farr::gvkey_ciks`)** |
| Need maximum historical coverage in offline R | Method B (often denser in Option_listing experience) |
| Institutional requirement “WRDS-only links” | Method A only; fail closed if denied |

### Coverage / audit (both methods)

| Metric | Meaning |
|---|---|
| `n_input` | CIK–date or gvkey–date events |
| `n_date_valid_unique` | unique usable links |
| `n_ambiguous` | multi-match after date filter |
| `n_unlinked` | no date-valid link |
| `link_rate` | unique / input |

### Template

```bash
# auto: try WRDS, fall back to farr
Rscript "$WRDS_SKILL_DIR/scripts/wrds_cik_gvkey_link_template.R" \
  --method auto --out-dir data/intermediate/wrds/links_cik --seed-n 40

# force farr only (no WRDS SEC)
Rscript "$WRDS_SKILL_DIR/scripts/wrds_cik_gvkey_link_template.R" \
  --method farr --out-dir data/intermediate/wrds/links_cik --seed-n 40

# force WRDS only
Rscript "$WRDS_SKILL_DIR/scripts/wrds_cik_gvkey_link_template.R" \
  --method wrds --out-dir data/intermediate/wrds/links_cik --seed-n 40
```

---

## Other common keys (pointers)

| Pair | Typical WRDS path | Notes |
|---|---|---|
| gvkey ↔ permno | `crsp.ccmxpf_linktable` | CCM section above |
| IBES ticker ↔ permno | `wrdsapps.ibcrsphist` | IBES section above |
| cik ↔ gvkey | `wrdssec.wciklink_gvkey` | this section |
| permno ↔ OptionMetrics secid | OM / CRSP–OM link products (project-specific) | Often date-valid; use universe + copy_inline |

---

## Remote vs local (summary)

| Step | Remote (Postgres + copy_inline) | Local caches |
|---|---|---|
| Build universe keys | | Yes (design / prior pulls) |
| CCM / ibcrsphist filter | Yes | or cache link table |
| Restrict large fact tables | Yes (`inline_keys` + join) | |
| Duplicate-link audit files | | Yes |
| Lags, multi-source sample, winsor | | Yes |

---

## Manifest

| query_id example | content |
|---|---|
| `universe_gvkey_fyear_v1` | key universe |
| `ccm_date_valid_v1` | CCM map + audit |
| `ibcrsphist_valid_v1` | IBES–CRSP map + audit |
| `crsp_m_for_universe_v1` | CRSP filtered via inline keys |

Record link filters (`score`, `linktype`, …) and whether `copy_inline` was used.

---

## Handoff

- Linking feeds `r-analysis-bridge` sample build.
- Missing links / missing returns stay missing.
- Escalate to `wrds-sas-cloud` only per `business-wrds-policy.md` when R/Postgres cannot finish filtered pulls.
