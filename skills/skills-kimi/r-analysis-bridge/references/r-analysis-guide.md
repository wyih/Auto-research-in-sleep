# R Analysis Guide

## Local R Execution

Use the bundled launcher for long-running scripts:

```bash
R_SUBMIT="$R_ANALYSIS_SKILL_DIR/scripts/r_submit.sh"
JOBID=$("$R_SUBMIT" R/04_main_results.R)
"$R_SUBMIT" --status "$JOBID"
"$R_SUBMIT" --wait "$JOBID"
```

Set `R_BIN` when `Rscript` is outside common locations:

```bash
export R_BIN="/usr/local/bin/Rscript"
```

The launcher writes logs to `logs/<script>.log` and records process metadata under `run_state/r_jobs/`.

## Recommended Packages

Use the project standard when one exists. Defaults for empirical business papers:

- data: `data.table`, `dplyr`, `readr`, `arrow`, `haven`
- fixed effects and panels: `fixest`, `lfe`, `plm`
- tables: `modelsummary`, `tinytable`, `gt`, `broom`
- figures: `ggplot2`, `patchwork`, `scales`
- event studies and DiD: `fixest::sunab`, `did`, `did2s`, `bacondecomp`
- RD: `rdrobust`
- matching: `MatchIt`, `cobalt`
- inference helpers: `clubSandwich`, `sandwich`, `lmtest`, `marginaleffects`

## Data Layout

Use:

- `data/raw/`: original source artifacts
- `data/intermediate/`: rebuildable staged products
- `data/final/`: analysis-ready `.rds`, `.parquet`, `.csv`, or `.dta`
- `tmp/`: scratch files

Do not save rebuildable datasets in the project root.

## Script Conventions

Each script should:

1. resolve the project root
2. load required packages
3. load its own input data
4. create missing output directories
5. write outputs deterministically
6. print `sessionInfo()` or key package versions when useful

Example setup:

```r
root <- normalizePath(getwd())
dir.create(file.path(root, "tables"), showWarnings = FALSE, recursive = TRUE)
dir.create(file.path(root, "figures"), showWarnings = FALSE, recursive = TRUE)
dir.create(file.path(root, "analysis", "output"), showWarnings = FALSE, recursive = TRUE)
```

For panel regressions, prefer explicit formulas:

```r
fit <- fixest::feols(
  y ~ treatment + controls | firm_id + year,
  cluster = ~ firm_id,
  data = df
)
```

## Table Conventions

Use `modelsummary` or `etable` with readable labels. Export at least one machine-readable version when practical:

```r
modelsummary::modelsummary(
  list("Main" = fit),
  output = "tables/table_main.tex",
  stars = TRUE,
  gof_omit = "IC|Log|Adj"
)
modelsummary::modelsummary(list("Main" = fit), output = "tables/table_main.csv")
```

Record model objects or tidy summaries under `analysis/output/` when useful.

## Figure Conventions

Use clean journal figures:

- white background
- readable axis labels
- point estimates with confidence intervals
- clear event-time zero line when relevant
- export PDF or PNG

Keep explanatory notes in manuscript figure notes or `RESULTS_SUMMARY.md`.

## Log Review Checklist

After each run, inspect the log for:

- errors and warnings
- package installation or version problems
- NA-induced row drops
- omitted coefficients
- separation or convergence warnings
- singleton or collinearity drops
- cluster counts too small for the intended claim
- output files missing or stale

Record important warnings in `analysis/ANALYSIS_LOG.md` and `audit_issue_ledger.md`.
