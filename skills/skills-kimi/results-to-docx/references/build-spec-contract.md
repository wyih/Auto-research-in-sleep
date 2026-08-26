# Results DOCX Build Spec Contract

The production builder accepts one UTF-8 JSON object. Paths are resolved
relative to the spec file, so a copied run directory remains portable.

## Minimal shape

```json
{
  "title": "Corporate Culture and Firm Performance",
  "subtitle": "Auditable empirical results pack",
  "run_id": "2026-07-18-main",
  "as_of_date": "2026-07-18",
  "narrative_mode": "standard",
  "coefficient_tables": [
    {
      "path": "../coef/main_coef.csv",
      "title": "Table 2. Main Regression Results",
      "primary_term": "culture_score",
      "primary_model": "m2",
      "note": "Firm and year fixed effects; standard errors clustered by firm."
    }
  ]
}
```

Required top-level fields in `standard` mode:

- `title`: document title
- `run_id`: stable analysis/passport run identifier
- `as_of_date`: explicit date string shown in the title block
- `coefficient_tables`: non-empty list

In `transport-only` mode, `title` and `subtitle` are optional and ignored. The
builder uses fixed document title text. `run_id` must be a 1–128 character ASCII
identifier and `as_of_date` must be a canonical `YYYY-MM-DD` date, because both
remain visible structured fields.

Optional top-level fields:

- `subtitle`: defaults to `Empirical results and audit pack`
- `descriptive_tables`: list, default empty
- `figures`: list, default empty
- `coefficient_decimals`: integer 0–8, default 3
- `descriptive_decimals`: integer 0–8, default 3
- `narrative_mode`: `standard` (default) or `transport-only`;
  `engineering-smoke` is accepted as an alias for `transport-only`

## Coefficient table entry

```json
{
  "path": "../coef/main_coef.csv",
  "title": "Table 2. Main Regression Results",
  "primary_term": "culture_score",
  "primary_model": "m2",
  "note": "Optional table-specific note."
}
```

- `path` and `title` are required in `standard` mode. In `transport-only`, the
  caller title/note are optional and ignored; captions are fixed (`Coefficient
  output C1`, and so on).
- The CSV must follow `coef-table-contract.md`.
- `primary_term` and `primary_model` select the row used for the generated
  overview sentence. If omitted, the builder uses the last model for the first
  non-intercept coefficient. A requested selector that is absent is a hard
  error.
- Repeated `nobs`, adjusted R-squared, dependent-variable, FE, cluster, control,
  and model labels must be internally consistent within each model.
- Duplicate `(panel, term, model_id)` coefficient rows are rejected.
- `gof`, `spec`, and `note` rows may use `value_text`; they are preserved as
  explicit table footer rows in `standard` mode. Transport-only omits these
  free-text rows and displays only recorded observations and adjusted R-squared
  metadata when present.
- Transport-only displays validated raw `term` and `model_id` values, not
  `term_label`, `model_label`, `dependent_variable`, `fixed_effects`, `cluster`,
  `controls`, or `value_text`. Raw IDs must be 1–128 character ASCII identifiers.

## Descriptive table entry

```json
{
  "path": "../descriptives/sample_descriptives.csv",
  "title": "Table 1. Descriptive Statistics",
  "note": "Main analysis sample."
}
```

The CSV follows the descriptives section of `coef-table-contract.md`. Empty
statistic columns are omitted from the Word table; observed values are never
imputed. In transport-only mode, the caller title/note and `variable_label` /
`sample` prose are ignored, and the validated raw `variable` ID is displayed.

## Figure entry

```json
{
  "path": "../figures/event_study.png",
  "title": "Figure 1. Dynamic Treatment Effects",
  "source_data": ["../figures/event_study_points.csv"],
  "source_script": "../../R/05_event_study.R",
  "alt_text": "Point estimates with 95% confidence intervals by event time.",
  "note": "The omitted period is t=-1."
}
```

- `path`, `title`, `source_data`, and `alt_text` are required.
- `source_data` must contain at least one file. The builder hashes the image,
  every source-data file, and the optional source script.
- `alt_text` is written to the drawing object's OOXML description.
- The manifest records provenance; it does not claim to re-run or visually
  reverse-engineer the plotting script.

In `transport-only` mode, `path` and non-empty `source_data` remain required,
while caller `title`, `note`, and `alt_text` are optional and ignored. Figures
are not embedded unless the entry sets `"transport_figure": true`. An opted-in
figure receives a fixed caption and alt description; its file/provenance hashes
are audited, but labels, annotations, and claims inside the image pixels are not
semantically audited.

## Generated prose provenance

The builder generates short overview statements only from selected coefficient
and descriptive rows. Each sentence is recorded in the JSON receipt with:

- source path and 1-based CSV row number (header is row 1)
- selectors (`term`, `model_id`, `panel`, or `variable`)
- raw values used in the sentence

In the default `standard` mode, the Word text says “estimated association,”
preserves null results, reports the raw p-value display, and explicitly states
that the result alone does not establish causality. This preserves the original
builder behavior.

In `transport-only` mode, generated prose uses only fixed wrapper text,
validated raw term/model/variable IDs, and recorded numeric fields. It omits
the outcome and all reader-facing labels. It emits no direction label,
statistical-threshold classification, economic interpretation, causal
interpretation, or substantive claim. Generated descriptive prose likewise
reproduces recorded values without interpreting the sample. The receipt stores
the normalized mode as `narrative_mode`; the `engineering-smoke` alias is
recorded as `transport-only`.

The guarantee covers the DOCX plus its generated manifest and receipt: ignored
free-text fields are not echoed into those outputs. Provenance paths and hashes
remain present as structured audit data.

## Output safety

- Output must end in `.docx` and include a `results_docx/` directory component.
- Targets under `paper/`, `manuscript/`, `submission/`, or `submissions/` are
  rejected.
- Existing DOCX, manifest, or receipt files are not replaced without `--force`.
- Final Office metadata is normalized after save and audited before output is
  accepted.
