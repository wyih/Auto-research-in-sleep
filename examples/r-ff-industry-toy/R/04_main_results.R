options(stringsAsFactors = FALSE)

args <- commandArgs(FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script_path <- if (length(file_arg)) sub("^--file=", "", file_arg[[1]]) else "R/04_main_results.R"
root <- normalizePath(file.path(dirname(script_path), ".."), mustWork = FALSE)
if (!dir.exists(file.path(root, "empirical-design"))) {
  root <- normalizePath(getwd(), mustWork = TRUE)
}

paths <- list(
  raw = file.path(root, "data", "raw"),
  final = file.path(root, "data", "final"),
  logs = file.path(root, "logs"),
  tables = file.path(root, "tables"),
  figures = file.path(root, "figures"),
  analysis = file.path(root, "analysis"),
  output = file.path(root, "analysis", "output"),
  paper = file.path(root, "paper")
)
for (p in paths) dir.create(p, showWarnings = FALSE, recursive = TRUE)

log_lines <- character()
add_log <- function(...) {
  line <- paste0(format(Sys.time(), "%Y-%m-%d %H:%M:%S"), " | ", paste(..., collapse = " "))
  log_lines <<- c(log_lines, line)
  message(line)
}

download_if_needed <- function(url, dest) {
  if (!file.exists(dest)) {
    add_log("Downloading", url)
    download.file(url, dest, mode = "wb", quiet = TRUE)
  } else {
    add_log("Using cached", dest)
  }
}

extract_zip_csv <- function(zip_path) {
  info <- unzip(zip_path, list = TRUE)
  csv_name <- info$Name[grepl("\\.csv$", info$Name, ignore.case = TRUE)][1]
  out_dir <- tempfile("ff_csv_")
  dir.create(out_dir)
  unzip(zip_path, files = csv_name, exdir = out_dir)
  file.path(out_dir, csv_name)
}

parse_french_section <- function(zip_path, header_regex) {
  csv_path <- extract_zip_csv(zip_path)
  lines <- readLines(csv_path, warn = FALSE)
  start <- grep(header_regex, lines)[1]
  if (is.na(start)) stop("Could not find header in ", zip_path)
  after <- seq.int(start + 1, length(lines))
  blank <- after[trimws(lines[after]) == ""][1]
  if (is.na(blank)) blank <- length(lines) + 1
  text <- paste(lines[start:(blank - 1)], collapse = "\n")
  df <- read.csv(text = text, check.names = FALSE)
  names(df)[1] <- "yyyymm"
  df <- df[grepl("^\\d{6}$", df$yyyymm), , drop = FALSE]
  for (nm in setdiff(names(df), "yyyymm")) {
    df[[nm]] <- suppressWarnings(as.numeric(df[[nm]])) / 100
  }
  df$year <- as.integer(substr(df$yyyymm, 1, 4))
  df$month <- as.integer(substr(df$yyyymm, 5, 6))
  df$date <- as.Date(sprintf("%04d-%02d-01", df$year, df$month))
  df
}

write_csv <- function(x, path) {
  write.csv(x, path, row.names = FALSE)
  add_log("Wrote", path)
}

format_num <- function(x, digits = 3) {
  formatC(x, format = "f", digits = digits)
}

write_latex_table <- function(df, path, caption) {
  con <- file(path, open = "wt")
  on.exit(close(con), add = TRUE)
  writeLines("\\begin{table}[!htbp]\\centering", con)
  writeLines(paste0("\\caption{", caption, "}"), con)
  writeLines("\\begin{tabular}{lrrrrrr}", con)
  writeLines("\\hline", con)
  writeLines("Industry & Alpha & t(Alpha) & Beta & t(Beta) & $R^2$ & N \\\\", con)
  writeLines("\\hline", con)
  for (i in seq_len(nrow(df))) {
    row <- df[i, ]
    writeLines(sprintf(
      "%s & %.4f & %.2f & %.3f & %.2f & %.3f & %d \\\\",
      row$industry, row$alpha, row$alpha_t, row$beta, row$beta_t, row$r_squared, row$n
    ), con)
  }
  writeLines("\\hline", con)
  writeLines("\\end{tabular}", con)
  writeLines("\\end{table}", con)
  add_log("Wrote", path)
}

factors_zip <- file.path(paths$raw, "F-F_Research_Data_Factors_CSV.zip")
industry_zip <- file.path(paths$raw, "10_Industry_Portfolios_CSV.zip")
download_if_needed(
  "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_CSV.zip",
  factors_zip
)
download_if_needed(
  "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/10_Industry_Portfolios_CSV.zip",
  industry_zip
)

factors <- parse_french_section(factors_zip, "Mkt-RF.*SMB.*HML.*RF")
industry <- parse_french_section(industry_zip, "NoDur.*Durbl.*Manuf.*Enrgy.*HiTec")

sample_start <- as.Date("2010-01-01")
sample_end <- as.Date("2024-12-01")
factors <- factors[factors$date >= sample_start & factors$date <= sample_end, ]
industry <- industry[industry$date >= sample_start & industry$date <= sample_end, ]

merged <- merge(
  industry,
  factors[, c("yyyymm", "Mkt-RF", "SMB", "HML", "RF")],
  by = "yyyymm",
  all = FALSE,
  suffixes = c("_industry", "_factor")
)
merged <- merged[order(merged$yyyymm), ]

industry_names <- c("NoDur", "Durbl", "Manuf", "Enrgy", "HiTec", "Telcm", "Shops", "Hlth", "Utils", "Other")
panel <- do.call(rbind, lapply(industry_names, function(ind) {
  data.frame(
    yyyymm = merged$yyyymm,
    date = merged$date,
    industry = ind,
    industry_return = merged[[ind]],
    rf = merged$RF,
    mkt_rf = merged$`Mkt-RF`,
    smb = merged$SMB,
    hml = merged$HML,
    excess_return = merged[[ind]] - merged$RF
  )
}))
panel <- panel[is.finite(panel$excess_return) & is.finite(panel$mkt_rf), ]

write_csv(factors, file.path(paths$final, "factors_monthly.csv"))
write_csv(panel, file.path(paths$final, "industry_month_panel.csv"))

summary_stats <- do.call(rbind, lapply(split(panel, panel$industry), function(df) {
  data.frame(
    industry = df$industry[1],
    n = nrow(df),
    mean_excess_return = mean(df$excess_return),
    sd_excess_return = sd(df$excess_return),
    mean_market_excess_return = mean(df$mkt_rf)
  )
}))
summary_stats <- summary_stats[match(industry_names, summary_stats$industry), ]
write_csv(summary_stats, file.path(paths$tables, "table_summary_stats.csv"))

capm_rows <- lapply(split(panel, panel$industry), function(df) {
  fit <- lm(excess_return ~ mkt_rf, data = df)
  co <- summary(fit)$coefficients
  data.frame(
    industry = df$industry[1],
    alpha = unname(co["(Intercept)", "Estimate"]),
    alpha_t = unname(co["(Intercept)", "t value"]),
    beta = unname(co["mkt_rf", "Estimate"]),
    beta_t = unname(co["mkt_rf", "t value"]),
    r_squared = summary(fit)$r.squared,
    n = nobs(fit)
  )
})
capm <- do.call(rbind, capm_rows)
capm <- capm[match(industry_names, capm$industry), ]
write_csv(capm, file.path(paths$tables, "table_capm_by_industry.csv"))
write_latex_table(capm, file.path(paths$tables, "table_capm_by_industry.tex"), "CAPM regressions by industry portfolio")

pdf(file.path(paths$figures, "capm_beta_by_industry.pdf"), width = 7.5, height = 4.5)
barplot(
  capm$beta,
  names.arg = capm$industry,
  col = "#1A85FF",
  border = NA,
  ylab = "CAPM beta",
  main = "Market beta by industry portfolio"
)
abline(h = 1, col = "#A0A0A0", lty = 2)
dev.off()
add_log("Wrote", file.path(paths$figures, "capm_beta_by_industry.pdf"))

hitec <- panel[panel$industry == "HiTec", ]
pdf(file.path(paths$figures, "hitec_excess_returns.pdf"), width = 7.5, height = 4.5)
plot(
  hitec$date,
  hitec$excess_return,
  type = "l",
  col = "#1A85FF",
  xlab = "Month",
  ylab = "Monthly excess return",
  main = "HiTec portfolio excess returns"
)
abline(h = 0, col = "#A0A0A0", lty = 2)
dev.off()
add_log("Wrote", file.path(paths$figures, "hitec_excess_returns.pdf"))

top_beta <- capm[which.max(capm$beta), ]
low_beta <- capm[which.min(capm$beta), ]
hitec_row <- capm[capm$industry == "HiTec", ]

analysis_log <- c(
  "# Analysis Log",
  "",
  paste0("- Script: `R/04_main_results.R`"),
  paste0("- Sample: ", min(panel$yyyymm), " to ", max(panel$yyyymm)),
  paste0("- Industry-month observations: ", nrow(panel)),
  paste0("- Public data source: Ken French Data Library"),
  "",
  "## Run Log",
  log_lines,
  "",
  "## Package Versions",
  paste0("- R: ", R.version.string)
)
writeLines(analysis_log, file.path(paths$analysis, "ANALYSIS_LOG.md"))

table_index <- c(
  "# Table Index",
  "",
  "| Output | Source Script | Description |",
  "|--------|---------------|-------------|",
  "| `tables/table_summary_stats.csv` | `R/04_main_results.R` | Industry-level return summary statistics |",
  "| `tables/table_capm_by_industry.csv` | `R/04_main_results.R` | CAPM alpha and beta by industry |",
  "| `tables/table_capm_by_industry.tex` | `R/04_main_results.R` | LaTeX version of CAPM table |",
  "| `figures/capm_beta_by_industry.pdf` | `R/04_main_results.R` | CAPM beta bar chart |",
  "| `figures/hitec_excess_returns.pdf` | `R/04_main_results.R` | HiTec monthly excess return time series |"
)
writeLines(table_index, file.path(paths$output, "TABLE_INDEX.md"))

results_summary <- c(
  "# Results Summary",
  "",
  "## Data Build",
  paste0("The analysis uses monthly Ken French factors and 10 industry portfolio returns from ", min(panel$yyyymm), " to ", max(panel$yyyymm), "."),
  paste0("The final panel contains ", nrow(panel), " industry-month observations across ", length(unique(panel$industry)), " industries."),
  "",
  "## Tables And Figures",
  "| Output | R Script | Log | Sample | Specification | Key Numbers | Claim Supported |",
  "|--------|----------|-----|--------|---------------|-------------|-----------------|",
  paste0(
    "| `tables/table_capm_by_industry.csv` | `R/04_main_results.R` | `logs/04_main_results.log` | ",
    min(panel$yyyymm), "-", max(panel$yyyymm),
    " | `excess_return ~ mkt_rf` by industry | highest beta ",
    top_beta$industry, " = ", format_num(top_beta$beta, 3),
    "; HiTec beta = ", format_num(hitec_row$beta, 3),
    "; HiTec alpha = ", format_num(hitec_row$alpha, 4),
    " | Industry portfolios differ in market exposure. |"
  ),
  paste0(
    "| `figures/capm_beta_by_industry.pdf` | `R/04_main_results.R` | `logs/04_main_results.log` | ",
    min(panel$yyyymm), "-", max(panel$yyyymm),
    " | CAPM beta estimates | lowest beta ",
    low_beta$industry, " = ", format_num(low_beta$beta, 3),
    " | Market exposure varies across industries. |"
  ),
  "",
  "## Main Findings",
  paste0("The highest estimated CAPM beta is ", top_beta$industry, " at ", format_num(top_beta$beta, 3), "."),
  paste0("HiTec has an estimated beta of ", format_num(hitec_row$beta, 3), " and an alpha of ", format_num(hitec_row$alpha, 4), "."),
  "",
  "## Robustness And Placebos",
  "This toy run does not implement robustness checks. The robustness plan recommends adding Fama-French three-factor models and Newey-West standard errors.",
  "",
  "## Null Or Mixed Results",
  "Alpha estimates in this toy CAPM exercise should be treated descriptively and should not be framed as causal evidence.",
  "",
  "## Issues For Audit Ledger",
  "No blocking replication issues. Conceptual issue: CAPM alpha is descriptive benchmark evidence.",
  "",
  "## Next Analyses",
  "Add SMB and HML factors, Newey-West inference, and pre/post-2020 subsample checks."
)
writeLines(results_summary, file.path(paths$output, "RESULTS_SUMMARY.md"))

paper <- c(
  "# Toy Results Note",
  "",
  "This note uses public Ken French monthly data to estimate simple CAPM regressions for 10 industry portfolios from 2010 through 2024.",
  paste0("The final panel contains ", nrow(panel), " industry-month observations."),
  paste0("The highest market beta is ", top_beta$industry, " at ", format_num(top_beta$beta, 3), "."),
  paste0("The HiTec portfolio has a beta of ", format_num(hitec_row$beta, 3), " and a monthly alpha of ", format_num(hitec_row$alpha, 4), "."),
  "These numbers describe benchmark market exposure; they do not support causal claims."
)
writeLines(paper, file.path(paths$paper, "toy_results.md"))

ledger <- c(
  "| Issue ID | First Raised In | Category | Severity | Blocking Until | Status | Notes |",
  "|----------|-----------------|----------|----------|----------------|--------|-------|",
  "| TOY-001 | RESULTS_SUMMARY.md | claim calibration | MINOR | evidence-to-claim | OPEN | CAPM alpha is descriptive benchmark evidence. |"
)
writeLines(ledger, file.path(root, "audit_issue_ledger.md"))

add_log("Completed toy R analysis")
writeLines(analysis_log, file.path(paths$analysis, "ANALYSIS_LOG.md"))
