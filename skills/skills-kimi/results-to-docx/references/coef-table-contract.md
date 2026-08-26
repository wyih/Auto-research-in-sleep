# Coefficient Table Contract (Tidy → Word)

Machine-readable regression exports for `results-to-docx`. One row = one coefficient (or GOF/spec meta-row) in one model. Wide journal tables are **derived** from this long form.

## File layout

Preferred:

```text
analysis/output/coef/<table_id>_coef.csv
analysis/output/descriptives/<table_id>_descriptives.csv
```

Also accept:

- `tables/*_coef.csv`
- `analysis/output/*_coef.csv`
- stacked multi-table file with a `table_id` column

Encoding: UTF-8. Delimiter: comma. Missing numeric cells: empty or `NA`.

## Required columns (coefficients)

| Column | Type | Meaning |
|---|---|---|
| `term` | string | Coefficient name as estimated (e.g. `treat`, `LNPVOL`) |
| `estimate` | number | Point estimate |
| `std.error` | number | Standard error used for inference in the paper |
| `p.value` | number | Two-sided p-value consistent with the SE |
| `model_id` | string | Stable model key within the table (e.g. `m1`, `col1`, `OLS_FE`) |

`model_id` may be named `model` in exports; consumers should accept either and normalize to `model_id`.

## Strongly recommended columns

| Column | Type | Meaning |
|---|---|---|
| `table_id` | string | Table shell id (`T3`, `main`, `table_event`) |
| `panel` | string | Panel label (`A`, `B`, `pos_volume`) |
| `term_label` | string | Reader-facing label if different from `term` |
| `statistic` | number | t/z statistic when available |
| `conf.low` | number | CI lower (optional) |
| `conf.high` | number | CI upper (optional) |
| `nobs` | integer | Estimation sample size for that model |
| `adj.r.squared` | number | Adjusted R² when defined |
| `r.squared` | number | R² when useful |
| `dependent_variable` | string | Outcome name or label |
| `fixed_effects` | string | Short FE summary (`firm + year`) |
| `cluster` | string | Clustering summary (`firm`, `exec_id`) |
| `controls` | string | `Yes` / `No` / control-set name |
| `model_label` | string | Column header for Word (`(1)`, `Cash t+1`) |
| `source_script` | string | Path to estimating script |
| `source_log` | string | Path to log |

## Optional audit columns

| Column | Meaning |
|---|---|
| `row_type` | `coef` (default), `gof`, `spec`, `note` |
| `stars` | Precomputed star string if upstream already applied a convention |
| `estimate_fmt` | Pre-rounded display string (use sparingly; prefer raw numbers) |
| `std_error_fmt` | Pre-rounded SE string |
| `weight` | Estimation weights description |
| `sample` | Sample restriction label |
| `run_id` | Passport / repro run id |

## Row types

Default rows are coefficients (`row_type` missing or `coef`).

Specification / GOF rows may appear as:

| `row_type` | `term` example | `estimate` usage |
|---|---|---|
| `spec` | `Controls`, `FE`, `Cluster` | often empty; put text in `model_label` cells via separate wide export **or** encode text in a `value_text` column |
| `gof` | `N`, `adj.R2` | numeric in `estimate` or `nobs` / `adj.r.squared` |

When GOF is constant per model, it is valid to store GOF only once per `model_id` (duplicate on each coef row, or a single `row_type=gof` block). `results-to-docx` should not invent GOF if absent.

### Optional `value_text`

For non-numeric footer cells (e.g. FE = `Year/Industry`):

| Column | Type | Meaning |
|---|---|---|
| `value_text` | string | Display text for this model cell when not numeric |

## Descriptives contract

File: `*_descriptives.csv` (or documented equivalent).

Recommended columns:

| Column | Meaning |
|---|---|
| `variable` | Variable name |
| `variable_label` | Reader-facing label |
| `n` | Non-missing count |
| `mean` | Mean |
| `sd` | Standard deviation |
| `p25` / `p50` / `p75` | Quartiles when used |
| `min` / `max` | Range when used |
| `sample` / `panel` | Sample slice |

## Stars and rounding (display only)

Default display convention for Word tables (state in table notes):

- `***` if `p.value < 0.01`
- `**` if `p.value < 0.05`
- `*` if `p.value < 0.10`
- else no star

Default rounding unless the project already fixed a rule:

- coefficients and SEs: 3 decimal places
- R²: 3 decimal places
- N: integer with thousands separators optional

Do not re-round away from an existing project convention recorded in `RESULTS_SUMMARY.md`.

## R export pattern

Minimal broom-style export after `fixest` / `lm` / etc.:

```r
tidy_one <- function(model, model_id, table_id = "main", panel = NA_character_) {
  dv <- all.vars(stats::formula(model))[[1]]
  broom::tidy(model) |>
    dplyr::mutate(
      table_id = table_id,
      panel = panel,
      model_id = model_id,
      model = model_id,
      dependent_variable = dv,
      nobs = stats::nobs(model),
      adj.r.squared = tryCatch(
        as.numeric(broom::glance(model)$adj.r.squared[[1]]),
        error = function(...) NA_real_
      ),
      source_script = "R/04_main_results.R"
    )
}

coef_df <- dplyr::bind_rows(
  tidy_one(fit1, "m1"),
  tidy_one(fit2, "m2")
)
readr::write_csv(coef_df, "analysis/output/coef/main_coef.csv")
```

Accept either broom names (`std.error`, `p.value`) or equivalent aliases:

| Alias | Canonical |
|---|---|
| `std_error`, `se`, `Std. Error` | `std.error` |
| `pvalue`, `p`, `Pr(>|t|)` | `p.value` |
| `coef`, `estimate` | `estimate` |
| `model` | `model_id` |

## Stata / Python notes

- Stata: export estimation results to CSV with the same canonical names (e.g. via `estout` / `regsave` / custom postfile), then rename columns to match this contract.
- Python: `statsmodels` summary frames or custom tidy builders should write the same columns.

## Word assembly expectations

`results-to-docx` pivots long tidy data to wide columns by `model_id` / `model_label`:

1. filter to the table/panel
2. order terms as in `TABLE_SHELLS.md` or first-seen order
3. place `estimate` (+ stars) on odd display rows and `(std.error)` or `(p.value)` on even rows—pick one secondary row convention and keep it within a paper
4. append FE / Cluster / N / R² footer from recommended columns
5. apply three-line borders; no vertical rules

Secondary row convention default: **standard errors in parentheses**. If a project historically prints p-values under estimates, keep that project rule and document it in the table note.

### Transport-only projection

When `narrative_mode` is `transport-only`, the production builder applies a
stricter projection instead of the reader-facing standard projection:

- display validated raw `term`, `model_id`, and descriptive `variable` IDs
- ignore `term_label`, `model_label`, `dependent_variable`, `fixed_effects`,
  `cluster`, `controls`, `variable_label`, `sample`, and free-text `value_text`
- omit non-coefficient footer rows that would require free-text cells
- retain recorded numeric coefficient/SE/p-value displays, N, and adjusted R²
- reject raw IDs that are not conservative 1–128 character ASCII identifiers

This projection is for pipeline transport verification, not a journal-facing
results table.

## Validation checklist

Before building Word:

- [ ] every `model_id` used in the table has at least one coef row
- [ ] `term` values match code / table shells (no silent renames without `term_label`)
- [ ] `nobs` consistent with sample narrative
- [ ] FE and cluster strings match `RESEARCH_DESIGN.md` / logs
- [ ] null results for key terms remain present
- [ ] file is not written over manuscript paths

## Non-goals

- This contract does not define causal claim language.
- This contract does not replace `business-number-audit` for manuscript prose.
- Manuscript `.docx` / `.tex` are out of scope for writers of these CSVs.
