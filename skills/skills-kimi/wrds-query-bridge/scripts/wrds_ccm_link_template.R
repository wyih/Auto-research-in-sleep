#!/usr/bin/env Rscript
# Date-valid Compustat–CRSP CCM link + optional one-month CRSP pull.
# Credentials: WRDS_USER, WRDS_PASSWORD (never hard-code / never print password).
#
# Default link filters (override only with explicit project rule):
#   linktype IN ('LU','LC'), linkprim IN ('P','C'), usedflag == 1

args <- commandArgs(trailingOnly = TRUE)

usage <- function() {
  cat(
    "Usage:\n",
    "  wrds_ccm_link_template.R [options]\n",
    "\n",
    "Options:\n",
    "  --gvkeys-file PATH   Text file: one gvkey per line (optional)\n",
    "  --event-date YYYY-MM-DD   Date for date-valid window (default: 2020-12-31)\n",
    "  --out-dir PATH       Output directory (default: ./wrds_link_out)\n",
    "  --crsp-month YYYY-MM Optional; if set, pull CRSP monthly for that month\n",
    "  --seed-n N           If no gvkeys file, take N funda gvkeys at event fyear (default: 30)\n",
    "  --help\n",
    "\n",
    "Env: WRDS_USER, WRDS_PASSWORD required.\n",
    "Optional: WRDS_HOST, WRDS_PORT, WRDS_DBNAME, WRDS_RENVIRON (path to .Renviron to load first)\n",
    sep = ""
  )
}

if (any(args %in% c("-h", "--help"))) {
  usage()
  quit(status = 0)
}

get_opt <- function(flag, default = NA_character_) {
  i <- match(flag, args)
  if (is.na(i) || i == length(args)) {
    return(default)
  }
  args[[i + 1]]
}

# Optional: load project Renviron without printing values
renviron <- Sys.getenv("WRDS_RENVIRON", "")
if (!nzchar(renviron)) {
  renviron <- get_opt("--renviron", "")
}
if (nzchar(renviron) && file.exists(renviron)) {
  readRenviron(renviron)
  message("loaded_renviron=", renviron)
}

gvkeys_file <- get_opt("--gvkeys-file", "")
event_date_chr <- get_opt("--event-date", "2020-12-31")
out_dir <- get_opt("--out-dir", "wrds_link_out")
crsp_month <- get_opt("--crsp-month", "")
seed_n <- as.integer(get_opt("--seed-n", "30"))
if (is.na(seed_n) || seed_n < 1L) seed_n <- 30L

user <- Sys.getenv("WRDS_USER", "")
pass <- Sys.getenv("WRDS_PASSWORD", "")
if (!nzchar(user) || !nzchar(pass)) {
  stop("Set WRDS_USER and WRDS_PASSWORD (or WRDS_RENVIRON pointing to a .Renviron that sets them).")
}

host <- Sys.getenv("WRDS_HOST", "wrds-pgdata.wharton.upenn.edu")
port <- as.integer(Sys.getenv("WRDS_PORT", "9737"))
dbname <- Sys.getenv("WRDS_DBNAME", "wrds")

need <- c("DBI", "RPostgres", "dplyr", "arrow")
missing_pkgs <- need[!vapply(need, requireNamespace, quietly = TRUE, FUN.VALUE = logical(1))]
if (length(missing_pkgs)) {
  stop("Missing R packages: ", paste(missing_pkgs, collapse = ", "))
}

suppressPackageStartupMessages({
  library(DBI)
  library(dplyr)
})

as_gvkey_chr <- function(x) {
  x <- gsub("\\s", "", as.character(x))
  ifelse(
    is.na(x) | !nzchar(x),
    NA_character_,
    vapply(x, function(z) {
      if (is.na(z) || !nzchar(z)) return(NA_character_)
      paste0(strrep("0", max(0L, 6L - nchar(z))), z)
    }, character(1))
  )
}

event_date <- as.Date(event_date_chr)
if (is.na(event_date)) stop("Invalid --event-date: ", event_date_chr)
event_fyear <- as.integer(format(event_date, "%Y"))

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

message("host=", host, " port=", port, " dbname=", dbname, " user=set")
message("event_date=", as.character(event_date), " out_dir=", out_dir)

con <- dbConnect(
  RPostgres::Postgres(),
  host = host,
  port = port,
  dbname = dbname,
  user = user,
  password = pass,
  sslmode = "require"
)
on.exit(try(dbDisconnect(con), silent = TRUE), add = TRUE)

# --- seed firm-dates ---
if (nzchar(gvkeys_file) && file.exists(gvkeys_file)) {
  raw_keys <- readLines(gvkeys_file, warn = FALSE)
  raw_keys <- trimws(raw_keys)
  raw_keys <- raw_keys[nzchar(raw_keys) & !startsWith(raw_keys, "#")]
  firm_dates <- tibble(
    gvkey = as_gvkey_chr(raw_keys),
    event_date = event_date
  ) |>
    filter(!is.na(gvkey)) |>
    distinct()
  message("seed=gvkeys_file n=", nrow(firm_dates))
} else {
  sql_seed <- paste0(
    "SELECT gvkey, datadate, fyear, at, sale FROM comp.funda ",
    "WHERE indfmt = 'INDL' AND datafmt = 'STD' AND popsrc = 'D' AND consol = 'C' ",
    "AND fyear = ", event_fyear, " ",
    "ORDER BY gvkey LIMIT ", seed_n
  )
  seed <- dbGetQuery(con, sql_seed)
  firm_dates <- seed |>
    transmute(
      gvkey = as_gvkey_chr(gvkey),
      event_date = as.Date(datadate),
      fyear = as.integer(fyear),
      at = at,
      sale = sale
    ) |>
    filter(!is.na(gvkey), !is.na(event_date))
  message("seed=comp.funda fyear=", event_fyear, " n=", nrow(firm_dates))
}

if (nrow(firm_dates) == 0L) {
  stop("No firm-dates to link.")
}

gvkey_list <- unique(firm_dates$gvkey)
# SQL IN list — keys are zero-padded digits only after as_gvkey_chr
safe_keys <- gvkey_list[grepl("^[0-9]{6}$", gvkey_list)]
if (length(safe_keys) == 0L) stop("No valid 6-digit gvkeys after padding.")
in_clause <- paste0("'", paste(safe_keys, collapse = "','"), "'")

sql_ccm <- paste0(
  "SELECT gvkey, lpermno AS permno, linkdt, linkenddt, linktype, linkprim, usedflag ",
  "FROM crsp.ccmxpf_linktable ",
  "WHERE usedflag = 1 ",
  "AND linktype IN ('LU', 'LC') ",
  "AND linkprim IN ('P', 'C') ",
  "AND gvkey IN (", in_clause, ")"
)

t0 <- Sys.time()
ccm_raw <- dbGetQuery(con, sql_ccm)
message("ccm_raw_rows=", nrow(ccm_raw), " elapsed_sec=", round(as.numeric(difftime(Sys.time(), t0, "secs")), 3))

ccm <- ccm_raw |>
  transmute(
    gvkey = as_gvkey_chr(gvkey),
    permno = as.integer(permno),
    linkdt = as.Date(linkdt),
    linkenddt = as.Date(linkenddt),
    linktype = as.character(linktype),
    linkprim = as.character(linkprim),
    usedflag = as.integer(usedflag)
  ) |>
  mutate(
    linkdt = dplyr::coalesce(linkdt, as.Date("1900-01-01")),
    linkenddt = dplyr::coalesce(linkenddt, as.Date("2100-12-31"))
  )

# date-valid many-to-many then audit
linked <- firm_dates |>
  inner_join(ccm, by = "gvkey", relationship = "many-to-many") |>
  filter(event_date >= linkdt, event_date <= linkenddt)

dup_ids <- linked |>
  count(gvkey, event_date, name = "n_links") |>
  filter(n_links > 1L)

ambiguous <- linked |>
  semi_join(dup_ids, by = c("gvkey", "event_date"))

# unique date-valid: keep only non-ambiguous
unique_links <- linked |>
  anti_join(dup_ids, by = c("gvkey", "event_date")) |>
  select(gvkey, event_date, permno, linkdt, linkenddt, linktype, linkprim)

unlinked <- firm_dates |>
  anti_join(unique_links, by = c("gvkey", "event_date")) |>
  anti_join(ambiguous |> distinct(gvkey, event_date), by = c("gvkey", "event_date"))

n_input <- nrow(firm_dates)
n_any_ccm <- firm_dates |> semi_join(ccm, by = "gvkey") |> nrow()
n_date_valid_unique <- nrow(unique_links)
n_ambiguous <- nrow(dup_ids)
n_unlinked <- nrow(unlinked)
link_rate <- if (n_input > 0) n_date_valid_unique / n_input else NA_real_

# write outputs
path_firm <- file.path(out_dir, "firm_dates.parquet")
path_ccm <- file.path(out_dir, "ccm_raw.parquet")
path_unique <- file.path(out_dir, "ccm_date_valid_unique.parquet")
path_amb <- file.path(out_dir, "ccm_date_valid_ambiguous.csv")
path_unl <- file.path(out_dir, "ccm_unlinked.csv")
path_report <- file.path(out_dir, "CCM_COVERAGE_REPORT.md")

arrow::write_parquet(firm_dates, path_firm)
arrow::write_parquet(ccm, path_ccm)
arrow::write_parquet(unique_links, path_unique)
if (nrow(ambiguous) > 0) {
  write.csv(ambiguous, path_amb, row.names = FALSE)
} else {
  write.csv(ambiguous[FALSE, ], path_amb, row.names = FALSE)
}
write.csv(unlinked, path_unl, row.names = FALSE)

report <- paste0(
  "# CCM Coverage Report\n\n",
  "## Parameters\n",
  "- event_date_default: ", as.character(event_date), "\n",
  "- link_filters: usedflag=1; linktype in (LU,LC); linkprim in (P,C)\n",
  "- date_rule: event_date in [coalesce(linkdt,1900-01-01), coalesce(linkenddt,2100-12-31)]\n",
  "- backend: r_postgres\n",
  "- pulled_at: ", format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"), "\n\n",
  "## Coverage\n\n",
  "| Metric | Value |\n|---|---|\n",
  "| n_input_firm_dates | ", n_input, " |\n",
  "| n_distinct_gvkey | ", dplyr::n_distinct(firm_dates$gvkey), " |\n",
  "| n_with_any_ccm_row | ", n_any_ccm, " |\n",
  "| n_date_valid_unique | ", n_date_valid_unique, " |\n",
  "| n_ambiguous_firm_dates | ", n_ambiguous, " |\n",
  "| n_unlinked_firm_dates | ", n_unlinked, " |\n",
  "| link_rate_unique | ", sprintf("%.4f", link_rate), " |\n\n",
  "## Outputs\n",
  "- firm_dates: `", path_firm, "`\n",
  "- ccm_raw: `", path_ccm, "`\n",
  "- date_valid_unique: `", path_unique, "`\n",
  "- ambiguous: `", path_amb, "`\n",
  "- unlinked: `", path_unl, "`\n\n",
  "## Notes\n",
  "- Missing link is not a zero return.\n",
  "- Ambiguous links are excluded from unique map; review CSV before forcing a pick.\n"
)
writeLines(report, path_report)
message("coverage_report=", path_report)
message(
  "link_rate_unique=", sprintf("%.4f", link_rate),
  " unique=", n_date_valid_unique,
  " ambiguous=", n_ambiguous,
  " unlinked=", n_unlinked
)

# --- optional CRSP monthly for resolved permnos ---
if (nzchar(crsp_month)) {
  # parse YYYY-MM
  if (!grepl("^[0-9]{4}-[0-9]{2}$", crsp_month)) {
    stop("--crsp-month must be YYYY-MM, got: ", crsp_month)
  }
  y <- as.integer(substr(crsp_month, 1, 4))
  m <- as.integer(substr(crsp_month, 6, 7))
  month_start <- as.Date(sprintf("%04d-%02d-01", y, m))
  month_end <- seq(month_start, by = "month", length.out = 2L)[[2]] - 1L

  permnos <- unique(unique_links$permno)
  permnos <- permnos[!is.na(permnos)]
  if (length(permnos) == 0L) {
    message("crsp_skip=no_permnos")
  } else {
    perm_clause <- paste(permnos, collapse = ",")
    # Prefer msflist / monthly stock file; try common names
    sql_crsp <- paste0(
      "SELECT permno, date, ret, prc, shrout, vol ",
      "FROM crsp.msf ",
      "WHERE permno IN (", perm_clause, ") ",
      "AND date >= DATE '", month_start, "' ",
      "AND date <= DATE '", month_end, "'"
    )
    message("crsp_month=", crsp_month, " n_permno=", length(permnos))
    t1 <- Sys.time()
    crsp <- tryCatch(
      dbGetQuery(con, sql_crsp),
      error = function(e) {
        message("crsp.msf failed: ", conditionMessage(e), " — trying crsp.msf_v2 if present is out of scope; abort CRSP leg")
        NULL
      }
    )
    if (!is.null(crsp)) {
      message(
        "crsp_rows=", nrow(crsp),
        " elapsed_sec=", round(as.numeric(difftime(Sys.time(), t1, "secs")), 3)
      )
      path_crsp <- file.path(out_dir, paste0("crsp_msf_", gsub("-", "", crsp_month), ".parquet"))
      arrow::write_parquet(crsp, path_crsp)
      # attach to unique links
      crsp2 <- crsp |>
        mutate(permno = as.integer(permno), date = as.Date(date))
      attached <- unique_links |>
        left_join(crsp2, by = "permno", relationship = "many-to-many")
      path_att <- file.path(out_dir, paste0("linked_crsp_", gsub("-", "", crsp_month), ".parquet"))
      arrow::write_parquet(attached, path_att)
      n_with_ret <- attached |> filter(!is.na(ret)) |> distinct(permno) |> nrow()
      cat(
        "\n## CRSP monthly attach\n",
        "- month: ", crsp_month, "\n",
        "- n_permno: ", length(permnos), "\n",
        "- n_crsp_rows: ", nrow(crsp), "\n",
        "- n_permno_with_ret: ", n_with_ret, "\n",
        "- crsp_path: `", path_crsp, "`\n",
        "- linked_path: `", path_att, "`\n",
        file = path_report, append = TRUE, sep = ""
      )
      message("crsp_out=", path_crsp)
      message("linked_out=", path_att)
      message("n_permno_with_ret=", n_with_ret)
    }
  }
}

message("status=complete")
message("Do not recode missing links or missing returns to zero at the link layer.")
