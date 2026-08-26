#!/usr/bin/env Rscript
# Universe → copy_inline → remote join (Option_listing 2026 pattern).
# Build a small local key universe, push with dbplyr::copy_inline, pull only matching WRDS rows.
#
# Env: WRDS_USER, WRDS_PASSWORD
# Optional: WRDS_RENVIRON path to .Renviron; WRDS_HOST, WRDS_PORT, WRDS_DBNAME

args <- commandArgs(trailingOnly = TRUE)

usage <- function() {
  cat(
    "Usage:\n",
    "  wrds_universe_inline_template.R [options]\n",
    "\n",
    "Options:\n",
    "  --out-dir PATH     Output directory (default: ./wrds_universe_out)\n",
    "  --fyear Y          Compustat fyear for seed universe (default: 2020)\n",
    "  --seed-n N         Seed universe size from funda (default: 40)\n",
    "  --crsp-month YYYY-MM  Optional CRSP msf month after CCM resolve\n",
    "  --help\n",
    "\n",
    "Flow:\n",
    "  1) local universe keys (gvkey, datadate, fyear)\n",
    "  2) copy_inline(universe) on WRDS\n",
    "  3) join crsp.ccmxpf_linktable (date-valid) on remote\n",
    "  4) optional: CRSP msf for resolved permnos in one month\n",
    sep = ""
  )
}

if (any(args %in% c("-h", "--help"))) {
  usage()
  quit(status = 0)
}

get_opt <- function(flag, default = NA_character_) {
  i <- match(flag, args)
  if (is.na(i) || i == length(args)) return(default)
  args[[i + 1]]
}

renviron <- Sys.getenv("WRDS_RENVIRON", "")
if (!nzchar(renviron)) renviron <- get_opt("--renviron", "")
if (nzchar(renviron) && file.exists(renviron)) {
  readRenviron(renviron)
  message("loaded_renviron=", renviron)
}

out_dir <- get_opt("--out-dir", "wrds_universe_out")
fyear <- as.integer(get_opt("--fyear", "2020"))
seed_n <- as.integer(get_opt("--seed-n", "40"))
crsp_month <- get_opt("--crsp-month", "")
if (is.na(seed_n) || seed_n < 1L) seed_n <- 40L
if (is.na(fyear)) stop("bad --fyear")

user <- Sys.getenv("WRDS_USER", "")
pass <- Sys.getenv("WRDS_PASSWORD", "")
if (!nzchar(user) || !nzchar(pass)) {
  stop("Set WRDS_USER and WRDS_PASSWORD (or WRDS_RENVIRON).")
}

host <- Sys.getenv("WRDS_HOST", "wrds-pgdata.wharton.upenn.edu")
port <- as.integer(Sys.getenv("WRDS_PORT", "9737"))
dbname <- Sys.getenv("WRDS_DBNAME", "wrds")

need <- c("DBI", "RPostgres", "dplyr", "dbplyr", "arrow")
miss <- need[!vapply(need, requireNamespace, quietly = TRUE, FUN.VALUE = logical(1))]
if (length(miss)) stop("Missing R packages: ", paste(miss, collapse = ", "))

suppressPackageStartupMessages({
  library(DBI)
  library(dplyr)
  library(dbplyr)
})

as_gvkey_chr <- function(x) {
  x <- gsub("\\s", "", as.character(x))
  ifelse(
    is.na(x) | !nzchar(x),
    NA_character_,
    vapply(x, function(z) paste0(strrep("0", max(0L, 6L - nchar(z))), z), character(1))
  )
}

inline_keys <- function(con, data, ..., max_rows = 50000L) {
  dots <- enquos(...)
  if (length(dots) > 0L) data <- select(data, !!!dots)
  data <- data |> distinct()
  if (inherits(data, "tbl_lazy")) data <- collect(data)
  if (nrow(data) == 0L) stop("inline_keys: zero rows")
  if (nrow(data) > max_rows) {
    warning("Inlining ", nrow(data), " rows; consider chunking.", call. = FALSE)
  }
  copy_inline(con, data)
}

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
message("host=", host, " user=set out_dir=", out_dir)

con <- dbConnect(
  RPostgres::Postgres(),
  host = host, port = port, dbname = dbname,
  user = user, password = pass, sslmode = "require"
)
on.exit(try(dbDisconnect(con), silent = TRUE), add = TRUE)

# --- 1) local universe (keys only) ---
sql_seed <- paste0(
  "SELECT gvkey, datadate, fyear, at, sale FROM comp.funda ",
  "WHERE indfmt = 'INDL' AND datafmt = 'STD' AND popsrc = 'D' AND consol = 'C' ",
  "AND fyear = ", fyear, " ORDER BY gvkey LIMIT ", seed_n
)
seed <- dbGetQuery(con, sql_seed)
universe <- seed |>
  transmute(
    gvkey = as_gvkey_chr(gvkey),
    datadate = as.Date(datadate),
    fyear = as.integer(fyear),
    at = at,
    sale = sale
  ) |>
  filter(!is.na(gvkey), !is.na(datadate))

message("universe_n=", nrow(universe))
arrow::write_parquet(universe, file.path(out_dir, "universe_local.parquet"))

# --- 2) copy_inline keys only ---
t0 <- Sys.time()
u_remote <- inline_keys(con, universe, gvkey, datadate, fyear)
message("copy_inline_sec=", round(as.numeric(difftime(Sys.time(), t0, "secs")), 3))

# --- 3) remote CCM date-valid join via inline universe ---
# Note: copy_inline table is only available for this connection's lazy queries.
ccm <- tbl(con, in_schema("crsp", "ccmxpf_linktable")) |>
  filter(
    usedflag == 1L,
    linktype %in% c("LU", "LC"),
    linkprim %in% c("P", "C")
  ) |>
  select(
    gvkey,
    permno = lpermno,
    linkdt,
    linkenddt,
    linktype,
    linkprim
  ) |>
  mutate(linkenddt = coalesce(linkenddt, as.Date("2100-12-31")))

linked_lazy <- u_remote |>
  inner_join(ccm, by = "gvkey") |>
  filter(datadate >= linkdt, datadate <= linkenddt)

t1 <- Sys.time()
linked <- collect(linked_lazy)
message(
  "ccm_join_collect_rows=", nrow(linked),
  " sec=", round(as.numeric(difftime(Sys.time(), t1, "secs")), 3)
)

# audit duplicates at gvkey-datadate
dup <- linked |>
  count(gvkey, datadate, name = "n") |>
  filter(n > 1L)
unique_links <- linked |>
  anti_join(dup, by = c("gvkey", "datadate")) |>
  select(gvkey, datadate, fyear, permno, linkdt, linkenddt, linktype, linkprim)

unlinked <- universe |>
  anti_join(unique_links, by = c("gvkey", "datadate")) |>
  anti_join(linked |> semi_join(dup, by = c("gvkey", "datadate")) |> distinct(gvkey, datadate),
            by = c("gvkey", "datadate"))

arrow::write_parquet(linked, file.path(out_dir, "ccm_date_valid_all.parquet"))
arrow::write_parquet(unique_links, file.path(out_dir, "ccm_date_valid_unique.parquet"))
write.csv(dup, file.path(out_dir, "ccm_duplicate_keys.csv"), row.names = FALSE)
write.csv(unlinked, file.path(out_dir, "ccm_unlinked.csv"), row.names = FALSE)

n_in <- nrow(universe)
n_u <- nrow(unique_links)
n_d <- nrow(dup)
n_x <- nrow(unlinked)
rate <- if (n_in) n_u / n_in else NA_real_

report <- paste0(
  "# Universe + copy_inline + CCM report\n\n",
  "## Pattern\n",
  "1. local universe keys\n",
  "2. dbplyr::copy_inline / inline_keys\n",
  "3. remote join crsp.ccmxpf_linktable (date-valid)\n",
  "4. collect filtered rows only\n\n",
  "## Coverage\n\n",
  "| Metric | Value |\n|---|---|\n",
  "| n_universe | ", n_in, " |\n",
  "| n_date_valid_rows | ", nrow(linked), " |\n",
  "| n_date_valid_unique | ", n_u, " |\n",
  "| n_ambiguous_keys | ", n_d, " |\n",
  "| n_unlinked | ", n_x, " |\n",
  "| link_rate_unique | ", sprintf("%.4f", rate), " |\n\n",
  "- fyear_seed: ", fyear, "\n",
  "- link_filters: usedflag=1; LU/LC; P/C\n",
  "- pulled_at: ", format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"), "\n"
)
writeLines(report, file.path(out_dir, "UNIVERSE_INLINE_REPORT.md"))
message("link_rate_unique=", sprintf("%.4f", rate), " unique=", n_u, " unlinked=", n_x)

# --- 4) optional CRSP month for resolved permnos (still key-filtered) ---
if (nzchar(crsp_month)) {
  if (!grepl("^[0-9]{4}-[0-9]{2}$", crsp_month)) stop("bad --crsp-month")
  y <- as.integer(substr(crsp_month, 1, 4))
  m <- as.integer(substr(crsp_month, 6, 7))
  month_start <- as.Date(sprintf("%04d-%02d-01", y, m))
  month_end <- seq(month_start, by = "month", length.out = 2L)[[2]] - 1L

  perm_df <- unique_links |>
    distinct(permno) |>
    filter(!is.na(permno)) |>
    mutate(permno = as.integer(permno))
  if (nrow(perm_df) == 0L) {
    message("crsp_skip=no_permno")
  } else {
    p_remote <- inline_keys(con, perm_df, permno)
    msf <- tbl(con, in_schema("crsp", "msf")) |>
      filter(date >= !!month_start, date <= !!month_end) |>
      select(permno, date, ret, prc, shrout, vol)
    t2 <- Sys.time()
    crsp <- p_remote |>
      inner_join(msf, by = "permno") |>
      collect()
    message(
      "crsp_rows=", nrow(crsp),
      " sec=", round(as.numeric(difftime(Sys.time(), t2, "secs")), 3)
    )
    arrow::write_parquet(crsp, file.path(out_dir, paste0("crsp_msf_", gsub("-", "", crsp_month), "_inline.parquet")))
    cat(
      "\n## CRSP via copy_inline permnos\n",
      "- month: ", crsp_month, "\n",
      "- n_permno: ", nrow(perm_df), "\n",
      "- n_rows: ", nrow(crsp), "\n",
      file = file.path(out_dir, "UNIVERSE_INLINE_REPORT.md"), append = TRUE, sep = ""
    )
  }
}

message("status=complete")
message("Pattern verified: universe → copy_inline → remote join → collect small result.")
