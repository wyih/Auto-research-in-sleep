---
name: data-analysis-bridge
description: Convert an empirical design plan into analysis scripts and reproducible outputs for business, accounting, finance, management, and economics papers. Use when the user has data or a research design and needs R, Stata, or Python code, cleaning scripts, regression tables, event-study plots, robustness execution, or a business replacement for experiment-bridge.
---

# Data Analysis Bridge

Plan or data context: $ARGUMENTS

## Purpose

Bridge empirical design to executable analysis. Produce reproducible code, logs, and paper-ready tables.

## Defaults

- Use `r-analysis-bridge` when the project already uses `.R`, `.Rmd`, `.qmd`, `.rds`, tidyverse, `fixest`, or the user asks for R. Prefer R when the project has no existing language.
- Use `stata-analysis-bridge` when the project already uses `.do` files, `.dta` files, Stata table shells, or the user asks for Stata.
- Use Python when the project is already Python-based or the analysis depends on Python-specific parsing.

## Inputs

Read:

1. `empirical-design/RESEARCH_DESIGN.md`
2. `empirical-design/DATA_PLAN.md`
3. `empirical-design/TABLE_SHELLS.md`
4. existing scripts and data dictionaries
5. raw or derived data folders if available

## Workflow

### Phase 1: Inventory

Map:

- raw data files
- derived data files
- code already present
- variable dictionaries
- merge keys
- sample filters
- missing data patterns

### Phase 2: Build Reproducible Structure

If R is selected, route execution through `r-analysis-bridge` and use its `R/`, `logs/`, `tables/`, `figures/`, and `data/` layout. If Stata is selected, route execution through `stata-analysis-bridge` and use its `do/`, `logs/`, `tables/`, `figures/`, and `data/` layout. For Python, use or create:

```text
analysis/
  00_setup.*
  01_build_sample.*
  02_variables.*
  03_descriptives.*
  04_main_results.*
  05_robustness.*
  06_mechanism_heterogeneity.*
  output/
    tables/
    figures/
    logs/
```

### Phase 3: Implement Analyses

Implement:

- sample construction with row counts after each filter
- variable construction with validation checks
- main specifications from `TABLE_SHELLS.md`
- standard errors and clustering as specified
- robustness and placebo analyses
- table export to CSV, LaTeX, and Markdown when practical
- diagnostic plots for event studies or distributions

### Phase 4: Verify Outputs

Check:

- row counts match sample plan
- fixed effects and clustering match design
- signs and magnitudes are plausible
- table columns match shell labels
- every reported number traces to an output file

When the backend is R or Stata, run `business-number-audit` after manuscript text or result prose exists.

### Phase 5: Document

Write:

- `analysis/ANALYSIS_LOG.md`
- `analysis/output/TABLE_INDEX.md`
- `analysis/output/RESULTS_SUMMARY.md`

## Rules

- Never overwrite raw data.
- Keep all filters auditable.
- Report sample attrition explicitly.
- Preserve failed or null results in logs.
- Flag data access gaps instead of fabricating placeholder outputs.
