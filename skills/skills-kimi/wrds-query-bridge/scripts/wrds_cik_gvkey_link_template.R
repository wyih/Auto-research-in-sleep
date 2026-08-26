#!/usr/bin/env Rscript
# CIK ↔ gvkey linking — two methods from Option_listing:
#   A) WRDS wrdssec.wciklink_gvkey
#   B) farr::gvkey_ciks (local package data; often denser when WRDS SEC unavailable)
#
# Env for method wrds/auto: WRDS_USER, WRDS_PASSWORD; optional WRDS_RENVIRON

args <- commandArgs(trailingOnly = TRUE)

usage <- function() {
  cat(
    "Usage:\n",
    "  wrds_cik_gvkey_link_template.R [options]\n",
    "\n",
    "Options:\n",
    "  --method auto|wrds|farr   default auto (WRDS then farr fallback)\n",
    "  --out-dir PATH\n",
    "  --seed-n N                sample size for smoke (default: 40)\n",
    "  --event-date YYYY-MM-DD   date-valid check date (default: 2020-12-31)\n",
    "  --help\n",
    "\n",
    "Method B needs: install.packages(\"farr\"); object farr::gvkey_ciks\n",
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

method <- tolower(get_opt("--method", "auto"))
out_dir <- get_opt("--out-dir", "wrds_cik_out")
seed_n <- as.integer(get_opt("--seed-n", "40"))
event_date <- as.Date(get_opt("--event-date", "2020-12-31"))
if (is.na(seed_n) || seed_n < 1L) seed_n <- 40L
if (is.na(event_date)) stop("bad --event-date")
if (!method %in% c("auto", "wrds", "farr")) stop("--method must be auto|wrds|farr")

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

as_gvkey_chr <- function(x) {
  x <- gsub("\\s", "", as.character(x))
  ifelse(
    is.na(x) | !nzchar(x),
    NA_character_,
    vapply(x, function(z) paste0(strrep("0", max(0L, 6L - nchar(z))), z), character(1))
  )
}

write_report <- function(path, method_used, n_in, n_u, n_d, n_x, rate, extra_lines = character()) {
  body <- paste0(
    "# CIK–gvkey link report\n\n",
    "## Method\n",
    "- used: `", method_used, "`\n",
    "- event_date: ", as.character(event_date), "\n",
    "- date rule: event_date in [first_date, last_date]\n",
    "- pulled_at: ", format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"), "\n\n",
    "## Coverage (smoke)\n\n",
    "| Metric | Value |\n|---|---|\n",
    "| n_event_keys | ", n_in, " |\n",
    "| n_date_valid_unique | ", n_u, " |\n",
    "| n_ambiguous | ", n_d, " |\n",
    "| n_unlinked | ", n_x, " |\n",
    "| link_rate_unique | ", sprintf("%.4f", rate), " |\n\n",
    paste(extra_lines, collapse = "\n"),
    "\n"
  )
  writeLines(body, path)
}

run_coverage <- function(link, method_used, extra_lines = character()) {
  # link: cik, gvkey, first_date, last_date
  link <- link |>
    dplyr::mutate(
      cik = as.character(cik),
      gvkey = as_gvkey_chr(gvkey),
      first_date = as.Date(first_date),
      last_date = as.Date(last_date)
    ) |>
    dplyr::mutate(
      last_date = dplyr::coalesce(last_date, as.Date("2100-12-31"))
    ) |>
    dplyr::filter(!is.na(gvkey), !is.na(cik), nzchar(cik), !is.na(first_date)) |>
    dplyr::distinct()

  events <- link |>
    dplyr::distinct(cik, gvkey) |>
    dplyr::slice_head(n = seed_n) |>
    dplyr::mutate(event_date = event_date)

  valid <- events |>
    dplyr::inner_join(link, by = c("cik", "gvkey"), relationship = "many-to-many") |>
    dplyr::filter(event_date >= first_date, event_date <= last_date)

  dup <- valid |>
    dplyr::count(cik, event_date, name = "n") |>
    dplyr::filter(n > 1L)

  unique_v <- valid |>
    dplyr::anti_join(dup, by = c("cik", "event_date")) |>
    dplyr::select(cik, gvkey, event_date, first_date, last_date)

  unlinked <- events |>
    dplyr::anti_join(valid |> dplyr::distinct(cik, event_date), by = c("cik", "event_date"))

  arrow::write_parquet(link, file.path(out_dir, paste0("cik_gvkey_links_", method_used, ".parquet")))
  arrow::write_parquet(unique_v, file.path(out_dir, paste0("cik_gvkey_date_valid_unique_", method_used, ".parquet")))
  utils::write.csv(dup, file.path(out_dir, paste0("cik_gvkey_ambiguous_", method_used, ".csv")), row.names = FALSE)
  utils::write.csv(unlinked, file.path(out_dir, paste0("cik_gvkey_unlinked_", method_used, ".csv")), row.names = FALSE)

  n_in <- nrow(events)
  n_u <- nrow(unique_v)
  n_d <- nrow(dup)
  n_x <- nrow(unlinked)
  rate <- if (n_in) n_u / n_in else NA_real_

  write_report(
    file.path(out_dir, "CIK_GVKEY_COVERAGE_REPORT.md"),
    method_used, n_in, n_u, n_d, n_x, rate, extra_lines
  )
  message(
    "method=", method_used,
    " link_rate_unique=", sprintf("%.4f", rate),
    " unique=", n_u, " unlinked=", n_x
  )
  invisible(TRUE)
}

try_wrds <- function() {
  need <- c("DBI", "RPostgres", "dplyr", "arrow")
  miss <- need[!vapply(need, requireNamespace, quietly = TRUE, FUN.VALUE = logical(1))]
  if (length(miss)) stop("Missing packages for WRDS path: ", paste(miss, collapse = ", "))

  user <- Sys.getenv("WRDS_USER", "")
  pass <- Sys.getenv("WRDS_PASSWORD", "")
  if (!nzchar(user) || !nzchar(pass)) {
    stop("WRDS_USER/WRDS_PASSWORD not set (or set WRDS_RENVIRON)")
  }

  host <- Sys.getenv("WRDS_HOST", "wrds-pgdata.wharton.upenn.edu")
  port <- as.integer(Sys.getenv("WRDS_PORT", "9737"))
  dbname <- Sys.getenv("WRDS_DBNAME", "wrds")

  con <- DBI::dbConnect(
    RPostgres::Postgres(),
    host = host, port = port, dbname = dbname,
    user = user, password = pass, sslmode = "require"
  )
  on.exit(try(DBI::dbDisconnect(con), silent = TRUE), add = TRUE)

  sql <- paste0(
    "SELECT cik, gvkey, link_start_date, link_end_date ",
    "FROM wrdssec.wciklink_gvkey ",
    "WHERE gvkey IS NOT NULL ",
    "ORDER BY gvkey LIMIT ", seed_n * 5L
  )
  raw <- DBI::dbGetQuery(con, sql)
  link <- data.frame(
    cik = raw$cik,
    gvkey = raw$gvkey,
    first_date = as.Date(raw$link_start_date),
    last_date = as.Date(raw$link_end_date),
    stringsAsFactors = FALSE
  )
  run_coverage(
    link,
    "wrds_wciklink_gvkey",
    c(
      "## Source",
      "- table: `wrdssec.wciklink_gvkey`",
      "- refs: Option_listing cs_board_size.R / 2025/1.wrds.R"
    )
  )
}

try_farr <- function(reason = NULL) {
  if (!requireNamespace("farr", quietly = TRUE)) {
    stop(
      "Package farr not installed. install.packages(\"farr\") ",
      "then re-run with --method farr"
    )
  }
  if (!requireNamespace("dplyr", quietly = TRUE) || !requireNamespace("arrow", quietly = TRUE)) {
    stop("Need dplyr and arrow for farr path")
  }
  suppressPackageStartupMessages(library(dplyr))

  # farr exports gvkey_ciks as a data object
  links <- tryCatch(
    farr::gvkey_ciks,
    error = function(e) {
      # some versions attach on library(farr)
      if (!requireNamespace("farr", quietly = TRUE)) stop(e)
      suppressPackageStartupMessages(library(farr))
      if (exists("gvkey_ciks", inherits = TRUE)) get("gvkey_ciks") else stop(e)
    }
  )
  links <- as.data.frame(links)
  need_cols <- c("cik", "gvkey", "first_date", "last_date")
  if (!all(need_cols %in% names(links))) {
    stop("farr::gvkey_ciks missing columns: ", paste(setdiff(need_cols, names(links)), collapse = ", "))
  }

  # Optional package version
  ver <- tryCatch(as.character(utils::packageVersion("farr")), error = function(e) "unknown")
  extra <- c(
    "## Source",
    "- package: `farr::gvkey_ciks`",
    paste0("- farr_version: ", ver),
    "- refs: Option_listing cs_board_size.R (comment: 用这个匹配出来的多一些); 2025/1.wrds.R; 2025/3.merge.R",
    "- join shapes: by cik+date window, or by gvkey+date window to attach cik"
  )
  if (!is.null(reason) && nzchar(reason)) {
    extra <- c(extra, paste0("- fallback_reason: ", reason))
  }

  # Sample denser slice: take head after arrange for stable smoke
  link <- links[, need_cols]
  if (nrow(link) > seed_n * 20L) {
    # keep a stable prefix of distinct ciks
    ord <- order(as.character(link$cik), as.character(link$gvkey))
    link <- link[ord, , drop = FALSE]
    link <- link[!duplicated(paste(link$cik, link$gvkey)), , drop = FALSE]
    link <- utils::head(link, seed_n * 5L)
  }

  run_coverage(link, "farr_gvkey_ciks", extra)
}

# --- dispatch ---
ok <- FALSE
if (method %in% c("auto", "wrds")) {
  wrds_err <- NULL
  ok <- tryCatch(
    {
      try_wrds()
      TRUE
    },
    error = function(e) {
      wrds_err <<- conditionMessage(e)
      message("wrds_path_failed: ", wrds_err)
      FALSE
    }
  )
  if (ok) {
    message("status=complete")
    quit(status = 0)
  }
  if (method == "wrds") {
    writeLines(
      paste0(
        "# CIK–gvkey link report\n\n",
        "## Status: data_access_gap\n\n",
        "WRDS method failed:\n\n```\n", wrds_err, "\n```\n\n",
        "Retry with `--method farr` (package `farr::gvkey_ciks`).\n"
      ),
      file.path(out_dir, "CIK_GVKEY_COVERAGE_REPORT.md")
    )
    message("status=data_access_gap")
    quit(status = 2)
  }
  # auto → farr
  try_farr(reason = wrds_err)
  message("status=complete_fallback_farr")
  quit(status = 0)
}

# method == farr
try_farr()
message("status=complete")
