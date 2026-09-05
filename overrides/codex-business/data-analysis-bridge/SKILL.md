---
name: data-analysis-bridge
description: Convert an empirical design plan into analysis scripts and reproducible outputs for business, accounting, finance, management, and economics papers. Use when the user has data or a research design and needs R, Stata, or Python code, cleaning scripts, regression tables, event-study plots, robustness execution, or a business replacement for experiment-bridge.
---

# Data Analysis Bridge

Plan or data context: $ARGUMENTS

## Purpose

Bridge empirical design to executable analysis. Produce reproducible code, logs, and paper-ready tables.

Use the supplied design, data, and existing project layout. Implement the requested analyses and necessary diagnostics; the full layout and artifact names below are conventions for a complete analysis project, not prerequisites for a local task.

## Defaults

- Use `r-analysis-bridge` when the project already uses `.R`, `.Rmd`, `.qmd`, `.rds`, tidyverse, `fixest`, or the user asks for R. Prefer R when the project has no existing language.
- Use `stata-analysis-bridge` when the project already uses `.do` files, `.dta` files, Stata table shells, or the user asks for Stata.
- Use Python when the project is already Python-based or the analysis depends on Python-specific parsing.

## Inputs

Read available files or their project equivalents:

1. `empirical-design/RESEARCH_DESIGN.md`
2. `empirical-design/DATA_PLAN.md`
3. `empirical-design/TABLE_SHELLS.md`
4. existing scripts and data dictionaries
5. raw or derived data folders if available
6. `BUSINESS_RUN_PASSPORT.md` when present

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

Route R execution through `r-analysis-bridge` and Stata execution through `stata-analysis-bridge`. Reuse the project's layout and create only files needed for the requested work. A full Python analysis may use:

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
- robustness and placebo analyses required by the requested design
- table export to CSV, LaTeX, and Markdown when practical
- diagnostic plots for event studies or distributions

### Phase 4: Verify Outputs

Check:

- row counts match sample plan
- fixed effects and clustering match design
- signs and magnitudes are plausible
- table columns match shell labels
- every reported number traces to an output file

Check any reported numbers against the generated outputs. Run `business-number-audit` when a separate audit is requested or required by the project's workflow.

### Phase 5: Document

Record scripts, logs, outputs, sample, specification, and findings in the project's existing analysis notes. For a full analysis or a consumer requiring named artifacts, write:

- `analysis/ANALYSIS_LOG.md`
- `analysis/output/TABLE_INDEX.md`
- `analysis/output/RESULTS_SUMMARY.md`

Maintain `BUSINESS_RUN_PASSPORT.md` through `business-run-passport` when the project already uses it, the user requests it, or an actual downstream consumer requires it.

## Rules

- For local tasks, complete only the requested stage and mark downstream gaps as next-stage inputs.
- Never overwrite raw data.
- Keep all filters auditable.
- Report sample attrition explicitly.
- Preserve failed or null results in logs.
- Flag data access gaps instead of fabricating placeholder outputs.
- Record the analysis backend and source outputs. Include output hashes only when an adopted reproducibility contract requires them.
