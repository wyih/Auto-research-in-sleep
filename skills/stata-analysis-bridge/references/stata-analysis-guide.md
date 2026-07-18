# Stata Analysis Guide

## Local Stata Execution

Use the bundled launcher for long-running do files:

```bash
STATA_SUBMIT="$STATA_ANALYSIS_SKILL_DIR/scripts/stata_submit.sh"
JOBID=$("$STATA_SUBMIT" do/04_main_results.do)
"$STATA_SUBMIT" --status "$JOBID"
"$STATA_SUBMIT" --wait "$JOBID"
```

Set `STATA_BIN` when Stata is installed outside common locations:

```bash
export STATA_BIN="/Applications/Stata/StataMP.app/Contents/MacOS/stata-mp"
```

The launcher writes Stata stderr to `logs/<do-file>_stderr.log` and moves finished Stata batch logs to `logs/<do-file>.log` when possible.

## Data Layout

Use:

- `data/raw/`: original or downloaded source artifacts
- `data/intermediate/`: rebuildable staged products
- `data/final/`: analysis-ready datasets
- `tmp/`: scratch files

Keep source artifacts separate from rebuildable analysis files. Do not save rebuildable datasets in the project root.

## Do File Conventions

Use globals like:

```stata
global project "/path/to/project"
global data "$project/data"
global raw "$data/raw"
global intermediate "$data/intermediate"
global final "$data/final"
global figures "$project/figures"
global tables "$project/tables"
global logs "$project/logs"
```

Recommended active do files:

- `00_setup.do`
- `01_build_sample.do`
- `02_variables.do`
- `03_descriptives.do`
- `04_main_results.do`
- `05_event_study_or_identification.do`
- `06_robustness.do`
- `07_mechanism_heterogeneity.do`

Each do file should set paths, load its own dataset, and write its own log-compatible outputs. Sibling do files must not depend on shared Stata memory.

## Table Conventions

Prefer `esttab` fragments:

```stata
esttab m1 m2 m3 using "$tables/table_main.tex", replace ///
    booktabs fragment nomtitles label ///
    b(%9.3f) se(%9.3f) ///
    star(* 0.10 ** 0.05 *** 0.01) ///
    stats(N r2, labels("Observations" "R-squared") fmt(%9,0gc %9.3f)) ///
    compress nonotes
```

Use `coeflabel()` for reader-facing labels. Keep captions and notes in LaTeX or the manuscript, not buried in Stata table output.

## Figure Conventions

Use a restrained journal palette:

- primary: blue `26 133 255`
- secondary: magenta `212 17 89`
- grid: light gray
- zero line: medium gray
- event marker: red

Export vector PDF when practical. Keep explanatory notes in manuscript figure notes.

## Log Review Checklist

After each run, inspect the log for:

- `r(...)` errors
- zero-observation regressions
- omitted coefficients
- singleton drops
- unexpected missingness
- fixed effects or clusters absent from the command
- sample filters that differ from the design plan
- package-install failures

Record important warnings in `analysis/ANALYSIS_LOG.md` and `audit_issue_ledger.md`.
