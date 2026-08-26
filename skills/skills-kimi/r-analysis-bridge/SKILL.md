---
name: r-analysis-bridge
description: Execute empirical business, accounting, finance, management, and economics analyses in R. Use when a project has .R, .Rmd, .qmd, .rds, parquet/csv workflows, fixest/lfe/plm models, modelsummary tables, ggplot figures, event studies, DiD, panel regressions, or when the user asks for an R backend for the business research workflow.
---

# R Analysis Bridge

Analysis context: $ARGUMENTS

## Purpose

Turn an empirical design into reproducible R scripts, logs, tables, figures, and analysis summaries that feed paper writing, number audits, and claim calibration.

## When To Use

Use this skill when:

- the project already uses R, `.R`, `.Rmd`, `.qmd`, `.rds`, parquet, or tidyverse workflows
- `data-analysis-bridge` chooses R as the backend
- the user wants `fixest`, `modelsummary`, `broom`, `marginaleffects`, `did`, `did2s`, `rdrobust`, `MatchIt`, or `ggplot2`
- table and figure outputs must trace back to scripts and logs
- the project needs reproducible regression outputs for accounting, finance, management, or economics papers

## Inputs

Read available files in this order:

1. `empirical-design/RESEARCH_DESIGN.md`
2. `empirical-design/DATA_PLAN.md`
3. `empirical-design/TABLE_SHELLS.md`
4. `empirical-design/ROBUSTNESS_PLAN.md`
5. existing `data_wrangle.md`, `key_variables.md`, data dictionaries, or codebooks
6. existing `R/`, `scripts/`, `logs/`, `tables/`, and `figures/`
7. `BUSINESS_RUN_PASSPORT.md` when present

If R execution details matter, read `references/r-analysis-guide.md`. Read `../shared-references/business-helper-resolution.md` before invoking the submit helper outside the ARIS repository.

## Project Layout

Use or create:

```text
R/
  00_setup.R
  01_build_sample.R
  02_variables.R
  03_descriptives.R
  04_main_results.R
  05_event_study_or_identification.R
  06_robustness.R
  07_mechanism_heterogeneity.R
logs/
tables/
figures/
data/raw/
data/intermediate/
data/final/
analysis/output/
```

Keep raw source files under `data/raw/`. Put rebuildable staged files under `data/intermediate/`. Put analysis-ready `.rds`, `.parquet`, `.csv`, or `.dta` exports under `data/final/`.

## Workflow

### Step 1: Inventory Data And Existing Code

Map raw files, derived datasets, keys, unit of observation, panel identifiers, date variables, variable labels, existing R scripts, and output folders. Record package/version or data-access gaps in `analysis/ANALYSIS_LOG.md`.

### Step 2: Write Or Repair R Scripts

Create scripts around the table shells:

- sample construction with attrition counts after each filter
- variable construction with validation checks
- Table 1 descriptives
- main specification with stated fixed effects and clustering
- event-study or identification diagnostics
- robustness, placebo, mechanism, and heterogeneity analyses
- export of tables to `.tex`, `.csv`, and `.md` when practical

Keep each R script runnable from a clean session.

### Step 3: Run R Locally

Prefer the bundled launcher:

```bash
R_SUBMIT="$R_ANALYSIS_SKILL_DIR/scripts/r_submit.sh"
JOBID=$("$R_SUBMIT" R/04_main_results.R)
"$R_SUBMIT" --wait "$JOBID"
```

Inside Codex `exec_command` sessions, use foreground mode so the tool keeps the process alive and verifies the exit file:

```bash
"$R_SUBMIT" --foreground R/04_main_results.R
```

If R is outside the usual locations, set:

```bash
export R_BIN="/full/path/to/Rscript"
```

### Step 4: Inspect Logs And Outputs

For every run:

- read the log
- check errors, warnings, dropped rows, NA-induced sample changes, omitted coefficients, separation, convergence warnings, singleton drops, and unexpected missingness
- confirm fixed effects, clustering, sample filters, and table labels match `TABLE_SHELLS.md`
- preserve null, failed, and mixed results in logs and the summary

### Step 5: Write Analysis Artifacts

Write:

- `analysis/ANALYSIS_LOG.md`
- `analysis/output/TABLE_INDEX.md`
- `analysis/output/RESULTS_SUMMARY.md`
- update `BUSINESS_RUN_PASSPORT.md` through `business-run-passport` when writing is allowed

`RESULTS_SUMMARY.md` must list each table or figure, source R script, source log, sample, specification, fixed effects, clustering, key estimates, economic magnitude, and claim it can support.

### Step 6: Export Tidy Coefs And Route Results Docx

After main regressions (and other tables meant for paper-facing results packs):

1. Export broom-style tidy coefficient CSVs and descriptives CSVs per `results-to-docx/references/coef-table-contract.md` (required: `term`, `estimate`, `std.error`, `p.value`, `model_id` or `model`).
2. Prefer `analysis/output/coef/` and `analysis/output/descriptives/` (or documented `tables/*_coef.csv` paths).
3. Route to `results-to-docx` for a **standalone** academic results `.docx` (three-line tables; figures optional).
4. **Do not edit the manuscript** Word/TeX in this step—only write under a results directory such as `analysis/output/results_docx/`.

## Output Contract

End every substantial R run with:

```markdown
# Results Summary

## Data Build
## Tables And Figures
| Output | R Script | Log | Sample | Specification | Key Numbers | Claim Supported |

## Main Findings
## Robustness And Placebos
## Null Or Mixed Results
## Issues For Audit Ledger
## Next Analyses
```

## Rules

- For local tasks, complete only the requested stage and mark downstream gaps as next-stage inputs.
- Keep R outputs traceable from paper claim to table, log, and script.
- Use `set.seed()` for simulations, resampling, matching, or bootstrap inference.
- Prefer `renv` if the project already uses it; otherwise record package versions.
- Do not simplify fixed effects, clustering, sample restrictions, or event windows to save runtime.
- Use parallel execution only when scripts load their own data independently.
- Route manuscript number checking to `business-number-audit`.
- Route standalone results Word packaging to `results-to-docx` after tidy coef export; never overwrite manuscript files for that step.
- Record R version, key package versions, and output hashes in the `repro_lock` when the results feed writing.
