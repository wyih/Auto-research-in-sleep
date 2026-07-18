#!/usr/bin/env Rscript
# IBES ↔ CRSP via official WRDS link table wrdsapps.ibcrsphist
# (Option_listing source/cs_analyst_coverage.R and source/2025/1.wrds.R)
#
# Default: score <= 2; date-valid on sdate/edate.
# Env: WRDS_USER, WRDS_PASSWORD; optional WRDS_RENVIRON

args <- commandArgs(trailingOnly = TRUE)

usage <- function() {
  cat(
    "Usage:\n",
    "  wrds_ibes_link_template.R [options]\n",
    "\n",
    "Options:\n",
    "  --out-dir PATH\n",
    "  --statpers-start YYYY-MM-DD  IBES statsumu window start (default: 2020-01-01)\n",
    "  --statpers-end YYYY-MM-DD    window end (default: 2020-03-31)\n",
    "  --seed-n N                   limit IBES tickers after filter (default: 50)\n",
    "  --max-score N                keep score <= N (default: 2)\n",
    "  --help\n",
    "\n",
    "Uses wrdsapps.ibcrsphist (not fuzzy ticker matching).\n",
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

out_dir <- get_opt("--out-dir", "wrds_ibes_out")
d0 <- as.Date(get_opt("--statpers-start", "2020-01-01"))
d1 <- as.Date(get_opt("--statpers-end", "2020-03-31"))
seed_n <- as.integer(get_opt("--seed-n", "50"))
max_score <- as.integer(get_opt("--max-score", "2"))
if (is.na(seed_n) || seed_n < 1L) seed_n <- 50L
if (is.na(max_score)) max_score <- 2L

user <- Sys.getenv("WRDS_USER", "")
pass <- Sys.getenv("WRDS_PASSWORD", "")
if (!nzchar(user) || !nzchar(pass)) stop("Set WRDS_USER/WRDS_PASSWORD or WRDS_RENVIRON")

host <- Sys.getenv("WRDS_HOST", "wrds-pgdata.wharton.upenn.edu")
port <- as.integer(Sys.getenv("WRDS_PORT", "9737"))
dbname <- Sys.getenv("WRDS_DBNAME", "wrds")

need <- c("DBI", "RPostgres", "dplyr", "dbplyr", "arrow")
miss <- need[!vapply(need, requireNamespace, quietly = TRUE, FUN.VALUE = logical(1))]
if (length(miss)) stop("Missing packages: ", paste(miss, collapse = ", "))

suppressPackageStartupMessages({
  library(DBI)
  library(dplyr)
  library(dbplyr)
})

inline_keys <- function(con, data, ..., max_rows = 50000L) {
  dots <- enquos(...)
  if (length(dots) > 0L) data <- select(data, !!!dots)
  data <- data |> distinct()
  if (inherits(data, "tbl_lazy")) data <- collect(data)
  if (nrow(data) == 0L) stop("inline_keys: zero rows")
  if (nrow(data) > max_rows) warning("Inlining ", nrow(data), " rows", call. = FALSE)
  copy_inline(con, data)
}

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
message("ibcrsphist max_score=", max_score, " window=", d0, "..", d1)

con <- dbConnect(
  RPostgres::Postgres(),
  host = host, port = port, dbname = dbname,
  user = user, password = pass, sslmode = "require"
)
on.exit(try(dbDisconnect(con), silent = TRUE), add = TRUE)

# Seed: small IBES statsumu slice (EPS, US, monthly summary style filters from Option_listing)
ibes_seed_sql <- paste0(
  "SELECT ticker, statpers, numest, meanest, stdev, fpedats ",
  "FROM ibes.statsumu_epsus ",
  "WHERE fpi = '1' AND measure = 'EPS' AND usfirm = 1 AND curcode = 'USD' ",
  "AND statpers >= DATE '", d0, "' AND statpers <= DATE '", d1, "' ",
  "ORDER BY ticker, statpers LIMIT ", max(seed_n * 20L, 200L)
)
t0 <- Sys.time()
ibes_raw <- dbGetQuery(con, ibes_seed_sql)
message("ibes_raw_rows=", nrow(ibes_raw), " sec=", round(as.numeric(difftime(Sys.time(), t0, "secs")), 3))

ibes_u <- ibes_raw |>
  mutate(
    ticker = trimws(as.character(ticker)),
    statpers = as.Date(statpers)
  ) |>
  filter(!is.na(ticker), nzchar(ticker), !is.na(statpers)) |>
  distinct(ticker, statpers, .keep_all = TRUE)

# Prefer limited distinct tickers for smoke
tickers <- ibes_u |>
  distinct(ticker) |>
  arrange(ticker) |>
  slice_head(n = seed_n)

ibes_u <- ibes_u |> semi_join(tickers, by = "ticker")
message("ibes_universe_rows=", nrow(ibes_u), " n_ticker=", nrow(tickers))
arrow::write_parquet(ibes_u, file.path(out_dir, "ibes_seed_local.parquet"))

# Official link table
# Option_listing: wrdsapps.ibcrsphist, score <= 2, ticker/permno/sdate/edate
t1 <- Sys.time()
link <- tbl(con, in_schema("wrdsapps", "ibcrsphist")) |>
  filter(score <= !!max_score) |>
  select(ticker, permno, sdate, edate, score) |>
  collect()
message("ibcrsphist_rows=", nrow(link), " sec=", round(as.numeric(difftime(Sys.time(), t1, "secs")), 3))

link <- link |>
  mutate(
    ticker = trimws(as.character(ticker)),
    permno = as.integer(permno),
    sdate = as.Date(sdate),
    edate = as.Date(edate),
    score = as.integer(score)
  )

# Restrict link to seed tickers (local semi-join is fine for small smoke;
# production can copy_inline tickers then join remote ibcrsphist)
link_u <- link |> semi_join(tickers, by = "ticker")

joined <- ibes_u |>
  inner_join(link_u, by = "ticker", relationship = "many-to-many") |>
  filter(sdate <= statpers, statpers <= edate)

dup <- joined |>
  count(ticker, statpers, name = "n") |>
  filter(n > 1L)

unique_j <- joined |>
  anti_join(dup, by = c("ticker", "statpers"))

unlinked <- ibes_u |>
  anti_join(joined |> distinct(ticker, statpers), by = c("ticker", "statpers"))

arrow::write_parquet(link_u, file.path(out_dir, "ibcrsphist_for_tickers.parquet"))
arrow::write_parquet(unique_j, file.path(out_dir, "ibes_crsp_date_valid_unique.parquet"))
write.csv(dup, file.path(out_dir, "ibes_link_ambiguous.csv"), row.names = FALSE)
write.csv(unlinked, file.path(out_dir, "ibes_unlinked.csv"), row.names = FALSE)

n_in <- nrow(ibes_u)
n_u <- nrow(unique_j)
n_d <- nrow(dup)
n_x <- nrow(unlinked)
rate <- if (n_in) n_u / n_in else NA_real_

# Optional: copy_inline permnos to show pattern for next CRSP attach
perm_df <- unique_j |>
  distinct(permno) |>
  filter(!is.na(permno))
if (nrow(perm_df) > 0L) {
  # smoke: push permnos (no large fact pull required for accept of link table)
  p_remote <- inline_keys(con, perm_df, permno)
  n_check <- p_remote |> summarise(n = n()) |> collect()
  message("copy_inline_permno_n=", n_check$n[[1]])
}

report <- paste0(
  "# IBES–CRSP link report (wrdsapps.ibcrsphist)\n\n",
  "## Table\n",
  "- `wrdsapps.ibcrsphist`\n",
  "- filters: score <= ", max_score, "\n",
  "- date rule: sdate <= statpers <= edate\n\n",
  "## Coverage\n\n",
  "| Metric | Value |\n|---|---|\n",
  "| n_ibes_rows | ", n_in, " |\n",
  "| n_date_valid_unique | ", n_u, " |\n",
  "| n_ambiguous | ", n_d, " |\n",
  "| n_unlinked | ", n_x, " |\n",
  "| link_rate_unique | ", sprintf("%.4f", rate), " |\n\n",
  "- statpers window: ", d0, " .. ", d1, "\n",
  "- pulled_at: ", format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"), "\n",
  "- source pattern: Option_listing cs_analyst_coverage.R / 2025/1.wrds.R\n"
)
writeLines(report, file.path(out_dir, "IBES_LINK_COVERAGE_REPORT.md"))
message("link_rate_unique=", sprintf("%.4f", rate), " unique=", n_u, " unlinked=", n_x)
message("status=complete")
