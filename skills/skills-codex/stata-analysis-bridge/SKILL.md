---
name: stata-analysis-bridge
description: Execute empirical business, accounting, finance, management, and economics analyses in Stata. Use when a project has .do files, .dta files, Stata-style table shells, event studies, DiD, panel regressions, esttab outputs, or when the user asks to migrate the paper_factory Stata analysis lane.
---

# Stata Analysis Bridge

Analysis context: $ARGUMENTS

## Purpose

Turn an empirical design into reproducible Stata do files, logs, tables, figures, and analysis summaries that can feed paper writing and number audits.

## When To Use

Use this skill when:

- the project already uses Stata or `.dta` files
- `data-analysis-bridge` chooses Stata as the backend
- the design requires panel FE, DiD, event study, IV, RD, matched samples, heterogeneity, robustness, or validation tables
- the user needs long-running Stata jobs monitored locally
- table and figure outputs must trace back to do files and logs

## Inputs

Read available files in this order:

1. `empirical-design/RESEARCH_DESIGN.md`
2. `empirical-design/DATA_PLAN.md`
3. `empirical-design/TABLE_SHELLS.md`
4. `empirical-design/ROBUSTNESS_PLAN.md`
5. existing `data_wrangle.md`, `key_variables.md`, or data dictionaries
6. existing `do/`, `logs/`, `tables/`, and `figures/`

If Stata execution details matter, read `references/stata-analysis-guide.md`.

## Project Layout

Use or create:

```text
do/
  00_setup.do
  01_build_sample.do
  02_variables.do
  03_descriptives.do
  04_main_results.do
  05_event_study_or_identification.do
  06_robustness.do
  07_mechanism_heterogeneity.do
logs/
tables/
figures/
data/raw/
data/intermediate/
data/final/
analysis/output/
```

Keep raw source files under `data/raw/`. Put rebuildable staged files under `data/intermediate/`. Put analysis-ready Stata datasets under `data/final/`.

## Workflow

### Step 1: Inventory Data And Existing Code

Map raw files, `.dta` files, merge keys, panel identifiers, time variables, variable labels, existing do files, and output folders. Record data-access gaps instead of creating placeholder analysis outputs.

### Step 2: Write Or Repair Do Files

Create do files around the table shells:

- sample construction with attrition counts after each filter
- variable construction with labels and validation checks
- Table 1 descriptive statistics
- main specification with stated fixed effects and clustering
- identification diagnostics, event-study plots, or design-specific checks
- robustness, placebo, mechanism, and heterogeneity analyses

Use readable file prefixes and keep each do file independently runnable.

### Step 3: Run Stata Locally

Prefer the bundled launcher:

```bash
STATA_SUBMIT="skills/stata-analysis-bridge/scripts/stata_submit.sh"
JOBID=$("$STATA_SUBMIT" do/04_main_results.do)
"$STATA_SUBMIT" --wait "$JOBID"
```

Inside Codex `exec_command` sessions, use foreground mode so the tool keeps the process alive until Stata writes its log:

```bash
"$STATA_SUBMIT" --foreground do/04_main_results.do
```

If the project is running from a Codex mirror install, use the corresponding installed skill path. If Stata is outside the usual locations, set:

```bash
export STATA_BIN="/full/path/to/stata-mp"
```

### Step 4: Inspect Logs And Outputs

For every run:

- read the Stata log
- check for `r(...)` errors, dropped variables, empty samples, omitted coefficients, singleton issues, and unexpected missingness
- confirm fixed effects, clustering, sample filters, and table labels match `TABLE_SHELLS.md`
- preserve null, failed, and mixed results in logs and the summary

### Step 5: Write Analysis Artifacts

Write:

- `analysis/ANALYSIS_LOG.md`
- `analysis/output/TABLE_INDEX.md`
- `analysis/output/RESULTS_SUMMARY.md`

`RESULTS_SUMMARY.md` must list each table or figure, source do file, source log, sample, specification, fixed effects, clustering, key estimates, economic magnitude, and claim it can support.

## Output Contract

End every substantial Stata run with:

```markdown
# Results Summary

## Data Build
## Tables And Figures
| Output | Do File | Log | Sample | Specification | Key Numbers | Claim Supported |

## Main Findings
## Robustness And Placebos
## Null Or Mixed Results
## Issues For Audit Ledger
## Next Analyses
```

## Rules

- Keep Stata outputs traceable from paper claim to table, log, and do file.
- Treat sample construction and variable construction as empirical evidence, not clerical setup.
- Do not shrink samples, drop fixed effects, or simplify clustering to save runtime unless the design requires it.
- Use parallel do files only when each loads its own dataset independently.
- Route manuscript number checking to `business-number-audit`.
