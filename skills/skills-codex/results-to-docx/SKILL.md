---
name: results-to-docx
description: Build a standalone academic-style Word document of empirical results (regression tables, descriptives, figures) from tidy coefficient CSVs and analysis outputs. Use after R/Stata/Python regressions when the user wants results in .docx without editing the manuscript.
---

# Results To Docx

Results context: $ARGUMENTS

## Purpose

Produce a **standalone** academic results Word document from tidy coefficient tables, descriptive statistics, and figure paths. The document is a paper-facing results pack for review, coauthors, or audit—not a manuscript rewrite.

## Hard Rules

- **Never edit the manuscript** (do not open or overwrite `paper/*.docx`, `paper/*.tex`, Overleaf source, or any existing submission Word file unless the user explicitly names a different target).
- Write only under a dedicated results path such as `analysis/output/results_docx/`, `output/results_docx/`, or a path the user names.
- Prefer regenerating a new `*.docx` over patching an old results doc.
- Keep numbers traceable: every table cell should come from a CSV, log, or model tidy export on disk.
- Platform-agnostic: use shell, Rscript, or Python interchangeably; do not require a specific agent harness.

## When To Use

Use this skill when:

- main regressions, robustness, mechanism, or event-study outputs exist
- the user wants a Word results pack with academic three-line tables
- `r-analysis-bridge` (or another analysis bridge) has exported tidy coef / descriptives CSVs
- metadata on generated docx must be normalized to author `Yihong Wang`

Do **not** use this skill to draft Introduction/literature or to rewrite the full paper—route that to `business-paper-writing`.

## Inputs

Read what exists, in order:

1. `analysis/output/RESULTS_SUMMARY.md`
2. `analysis/output/TABLE_INDEX.md`
3. tidy coefficient CSVs (see `references/coef-table-contract.md`)
4. descriptive-statistics CSVs
5. figure files under `figures/` or `analysis/output/figures/`
6. optional Word template only if the user provides one for layout cues
7. `empirical-design/TABLE_SHELLS.md` when table titles/order matter
8. `BUSINESS_RUN_PASSPORT.md` when present

Read `references/coef-table-contract.md` before inventing column names. Read `../shared-references/business-helper-resolution.md` before invoking the metadata helper outside the ARIS repository.
Read `references/build-spec-contract.md` before assembling the production JSON spec.

## Output Paths

Default layout:

```text
analysis/output/
  coef/
    <table_id>_coef.csv
  descriptives/
    <table_id>_descriptives.csv
  results_docx/
    results_<run_id_or_date>.docx
    RESULTS_DOCX_MANIFEST.md
```

If the project already uses `tables/` and `figures/` at the root, keep reading those, but still write the Word file under a **non-manuscript** results directory.

## Workflow

### Step 1: Collect Machine-Readable Inputs

Confirm tidy coef and descriptives exports exist. If regressions already ran in R but only modelsummary `.tex`/`.md` exist, ask the analysis stage (or run a small export script) to write broom-style tidy CSVs per `references/coef-table-contract.md`.

Minimum useful set:

- one long tidy coef CSV per table or one stacked multi-model file with `model_id`
- optional GOF / sample rows (`nobs`, `adj.r.squared`, FE, cluster labels)
- optional figure paths listed in the manifest

### Step 2: Plan Document Structure

Order tables to match `TABLE_SHELLS.md` when available:

1. sample / descriptives
2. main results
3. identification / event study
4. robustness
5. mechanism / heterogeneity

For each table, plan:

- title (Table N …)
- short note (sample, FE, clustering, DV timing)
- panel labels if multi-panel
- which `term` rows and which `model_id` columns appear

### Step 3: Build Academic Three-Line Tables

Style defaults for business/accounting/finance journals:

- Times New Roman (or project default serif)
- three-line table: top rule, header rule, bottom rule; no vertical rules
- estimate on one row; standard error or p-value in parentheses on the next row
- significance stars: `***` p<0.01, `**` p<0.05, `*` p<0.10 (state convention in table notes)
- column headers = model labels / dependent variables
- specification footer rows: Controls, FE, Cluster, N, adj. R² when available

**Production assembly path (portable Python CLI):**

Create one build spec following `references/build-spec-contract.md`, then run:

```bash
python3 "$RESULTS_DOCX_SKILL_DIR/scripts/build_results_docx.py" \
  --spec analysis/output/results_docx/build_spec.json \
  --out analysis/output/results_docx/results_main.docx
```

The CLI is the reusable acceptance path. It validates tidy input types and
within-model metadata, rejects duplicate coefficients and unsafe manuscript
targets, derives significance stars from raw p-values, applies explicit 9360
DXA table geometry, embeds figure alt text, writes row-level narrative
provenance, normalizes Office identity, and emits both:

- `RESULTS_DOCX_MANIFEST.md`
- `RESULTS_DOCX_RECEIPT.json`

For engineering acceptance or pipeline smoke tests, set
`"narrative_mode": "transport-only"` in the build spec. This mode keeps the
coefficient, standard-error, p-value, table, and provenance transport checks,
but emits only fixed wrapper text, validated raw ASCII identifiers, and recorded
numeric values. Caller-supplied titles, subtitles, labels, outcome/model/spec
descriptions, table/figure notes, alt text, and non-numeric `value_text` are
ignored in the DOCX, manifest, and receipt. It does not generate direction,
statistical-threshold, economic, causal, or substantive interpretations.
`"engineering-smoke"` is an accepted alias and is normalized to
`"transport-only"` in the receipt. Omit the field for the backward-compatible
`"standard"` behavior.

Transport-only figures are excluded by default. A figure is embedded only when
its entry explicitly sets `"transport_figure": true`; the builder then uses a
fixed caption and alt description and records that image pixels were not
semantically audited. The hash/provenance boundary does not validate claims,
labels, or annotations drawn inside an opted-in image.

It refuses to overwrite any output unless `--force` is explicit and refuses a
DOCX target under `paper/`, `manuscript/`, or `submission/`. The output path
must contain a dedicated `results_docx/` directory.

When Codex's `documents` skill is available, resolve its managed Python and
renderer through the workspace dependency loader rather than using system
Python. Other runtimes may use a compatible Python 3 environment with
`python-docx` and `lxml`.

**Upstream R path (preferred for estimation when R already runs the analysis):**

- `broom::tidy` / `modelsummary` → CSV (already done upstream)
- `officer` + `flextable` for body text and three-line tables
- `body_add_flextable` / `body_add_img` for tables and figures
- `print(doc, target = "<standalone>.docx")` only under the results directory

**Python path (when assembling from CSVs without R):**

- use the bundled production CLI above rather than drafting a one-off builder
- keep analysis/estimation code upstream; this stage only validates, derives
  presentation views, and packages Word output

Conceptual R sketch (adapt; do not require these package versions):

```r
# After tidy CSVs exist:
library(officer)
library(flextable)
doc <- read_docx()  # or a blank academic template path if user-provided
# paper_three_line(ft) pattern: border_remove + hline_top/bottom on header/body
# print(doc, target = "analysis/output/results_docx/results_main.docx")
```

### Step 4: Add Narrative Notes Sparingly

Include short table notes that state sample, fixed effects, clustering, and star legend. Optional 1–2 sentence result blurbs are allowed when they restate numbers already in the tables. Do not invent causal claims beyond `RESULTS_SUMMARY.md` / `CLAIMS_FROM_EVIDENCE.md`.

For a transport-only or engineering-smoke run, do not rely on custom titles,
labels, notes, or alt text: the builder deliberately replaces or omits them.
Use stable raw `term`, `model_id`, `panel`, and `variable` identifiers and
record interpretation elsewhere, outside the transport acceptance artifact.

### Step 5: Normalize Author Metadata

The production CLI runs the bundled normalizer after final save. It sets Author
/ Last Modified By to `Yihong Wang`; clears Company / Manager; removes custom,
comment, people, and revision-session identity residue; and fails if tracked
changes or author-bearing parts remain.

For a DOCX produced by another assembler, run the helper manually:

```bash
python3 "$RESULTS_DOCX_SKILL_DIR/scripts/normalize_docx_author.py" \
  analysis/output/results_docx/results_main.docx
```

Check-only:

```bash
python3 "$RESULTS_DOCX_SKILL_DIR/scripts/normalize_docx_author.py" \
  --check analysis/output/results_docx/results_main.docx
```

Default author is `Yihong Wang`. Override only if the user explicitly requests another author string.

### Step 6: Write Manifest

The production CLI writes `RESULTS_DOCX_MANIFEST.md` and a machine-readable
`RESULTS_DOCX_RECEIPT.json`. If assembling manually, create or update the
manifest with at least:

```markdown
# Results Docx Manifest

## Document
- path:
- created_from_run:

## Inputs
| Artifact | Path | Role |

## Tables In Document
| Table | Source Coef CSV | Source Descriptives | Notes |

## Figures In Document
| Figure | Path |

## Metadata
- author:
- last_modified_by:
- normalize_script_exit:

## Non-Goals
- manuscript files not modified: yes
```

## Output Contract

Deliver:

1. standalone `.docx` under a results directory (never the manuscript path)
2. `RESULTS_DOCX_MANIFEST.md`
3. `RESULTS_DOCX_RECEIPT.json` with hashes and row-level narrative provenance
4. rendered page images inspected page-by-page when a DOCX renderer is available
5. confirmation that manuscript paths were not written
6. optional pointer for `business-number-audit` if prose numbers appear in the results doc notes

## Render And Visual Acceptance Gate

DOCX package checks are necessary but not sufficient. After the final metadata
normalization, render the final DOCX (not a pre-normalization draft) to one PNG
per page and inspect every page at 100% zoom. With Codex's `documents` skill:

```bash
env TMPDIR=/private/tmp "$PYTHON" "$DOCUMENTS_SKILL_DIR/render_docx.py" \
  analysis/output/results_docx/results_main.docx \
  --output_dir analysis/output/results_docx/rendered \
  --emit_pdf
```

Fail acceptance for clipped text, overlap, broken three-line rules, table
overflow, unreadable figure labels, missing glyphs, or incorrect page
furniture. Rebuild, normalize again, and re-render after any fix. Run the
documents accessibility audit where available; figures must have meaningful
alt text and table header rows must be marked for repetition.

## Upstream Handoff (from analysis)

`r-analysis-bridge` should export tidy coef / descriptives CSVs per `references/coef-table-contract.md` after main regressions, then route here. This skill does not re-estimate models unless the user asks and analysis scripts are available.

## Rules

- For local tasks, complete only the requested document; mark missing CSVs as gaps instead of fabricating coefficients.
- Preserve null and mixed results; do not drop insignificant key terms to “clean” tables.
- Prefer long tidy coef tables as source of truth; wide presentation tables are derived views.
- Keep R/Stata/Python analysis code as the estimation authority; this skill is presentation + packaging.
- Do not silently change star thresholds, rounding, or sample labels relative to the CSV sources.
- Record output path and hash in `BUSINESS_RUN_PASSPORT.md` only when passport updates are in scope for the session.
