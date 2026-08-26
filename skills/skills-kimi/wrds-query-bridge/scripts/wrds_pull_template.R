#!/usr/bin/env Rscript
# Minimal WRDS Postgres -> parquet pull template.
# Credentials: WRDS_USER, WRDS_PASSWORD (never hard-code).

args <- commandArgs(trailingOnly = TRUE)

usage <- function() {
  cat(
    "Usage:\n",
    "  wrds_pull_template.R --sql PATH --out PATH --query-id ID\n",
    "  wrds_pull_template.R --help\n",
    "\n",
    "Env: WRDS_USER, WRDS_PASSWORD required.\n",
    "Optional: WRDS_HOST, WRDS_PORT, WRDS_DBNAME\n",
    sep = ""
  )
}

if (length(args) == 0 || any(args %in% c("-h", "--help"))) {
  usage()
  quit(status = if (length(args) == 0) 1 else 0)
}

get_opt <- function(flag) {
  i <- match(flag, args)
  if (is.na(i) || i == length(args)) {
    return(NA_character_)
  }
  args[[i + 1]]
}

sql_path <- get_opt("--sql")
out_path <- get_opt("--out")
query_id <- get_opt("--query-id")

if (anyNA(c(sql_path, out_path, query_id)) || !nzchar(sql_path) || !nzchar(out_path) || !nzchar(query_id)) {
  usage()
  quit(status = 1)
}

if (!file.exists(sql_path)) {
  stop("SQL file not found: ", sql_path)
}

user <- Sys.getenv("WRDS_USER", "")
pass <- Sys.getenv("WRDS_PASSWORD", "")
if (!nzchar(user) || !nzchar(pass)) {
  stop("Set WRDS_USER and WRDS_PASSWORD in the environment.")
}

host <- Sys.getenv("WRDS_HOST", "wrds-pgdata.wharton.upenn.edu")
port <- as.integer(Sys.getenv("WRDS_PORT", "9737"))
dbname <- Sys.getenv("WRDS_DBNAME", "wrds")

need <- c("DBI", "RPostgres", "arrow")
missing_pkgs <- need[!vapply(need, requireNamespace, quietly = TRUE, FUN.VALUE = logical(1))]
if (length(missing_pkgs)) {
  stop("Missing R packages: ", paste(missing_pkgs, collapse = ", "))
}

sql <- paste(readLines(sql_path, warn = FALSE), collapse = "\n")
if (!nzchar(trimws(sql))) {
  stop("SQL file is empty: ", sql_path)
}

message("query_id=", query_id)
message("sql=", sql_path)
message("host=", host, " port=", port, " dbname=", dbname, " user=set")

con <- DBI::dbConnect(
  RPostgres::Postgres(),
  host = host,
  port = port,
  dbname = dbname,
  user = user,
  password = pass,
  sslmode = "require"
)
on.exit(try(DBI::dbDisconnect(con), silent = TRUE), add = TRUE)

t0 <- Sys.time()
df <- DBI::dbGetQuery(con, sql)
elapsed <- as.numeric(difftime(Sys.time(), t0, units = "secs"))

dir.create(dirname(out_path), recursive = TRUE, showWarnings = FALSE)
arrow::write_parquet(df, out_path)

n_rows <- nrow(df)
n_cols <- ncol(df)
hash <- tryCatch(
  digest::digest(file = out_path, algo = "sha256"),
  error = function(e) {
    # digest optional; fall back to size stamp
    paste0("size:", file.info(out_path)$size)
  }
)

message("status=complete")
message("n_rows=", n_rows)
message("n_cols=", n_cols)
message("out=", out_path)
message("content_hash=", hash)
message("elapsed_sec=", round(elapsed, 3))
message("Append a DATA_MANIFEST row with query_id, path, n_rows, n_cols, hash, and filters.")
message("Do not recode missing values to zero at the pull layer.")
