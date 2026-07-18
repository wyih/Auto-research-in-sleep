# Grok P2 real-WRDS results DOCX runtime acceptance

Use the installed project skill `$results-to-docx`. Read its `SKILL.md`, `references/build-spec-contract.md`, and `references/coef-table-contract.md` before acting. This is a fresh Grok-runtime build from the integrated chain's real 10-row WRDS-derived inputs. It is not permission to reuse the existing synthetic Codex results pack.

## Hard input gate

The only authorized handoff receipt is:

```text
/Users/wyih/Projects/Auto-research-in-sleep/.aris/business-e2e/20260718T011517Z/integrated-chain/INTEGRATED_CHAIN_RECEIPT.json
```

Require all of the following before creating any DOCX:

- the file exists and is valid UTF-8 JSON;
- root `schema_version` is exactly `aris.business-e2e.integrated-chain-root.v2`, root status is accepted, and `generation.pure_from_current_facts` is true;
- independently hash the root receipt, then follow only its `lineage_receipt` descriptor. Require the descriptor's path, bytes, SHA-256, and accepted status to match the current file exactly;
- the linked lineage receipt has `schema_version` exactly `aris.business-e2e.integrated-chain-lineage.v2`, accepted status, `check_summary.failed == 0`, and every recorded check has `passed: true`;
- the lineage `wrds_lane.source`, `wrds_lane.processed`, `wrds_lane.model`, and `wrds_lane.source_receipt` jointly prove a real WRDS extract of exactly 10 source/model rows, including source query/run identity, project-relative paths, byte sizes, and SHA-256 values;
- `wrds_lane.artifacts` explicitly lists the tidy coefficient CSV, descriptives CSV, figure PNG, and source R script with hashes; `wrds_lane.processed` separately lists the figure's source-data CSV; `results_docx.build_spec` is a separately hash-bound descriptor that may be read only to recover the explicit figure→source-data/source-script mapping;
- every required coefficient/descriptives/figure/source-data/source-script path is represented by a lineage descriptor and its current byte size/hash matches. Do not infer a path by globbing;
- coefficient inputs are results of an actual recorded estimation over the 10-row WRDS-derived chain, not invented table values; model `nobs` values are positive and cannot exceed 10 without an explicit, valid repeated-observation lineage;
- the handoff does not label any accepted input `synthetic`, `mock`, `fixture`, `demonstration`, or `placeholder`.

Read paths only from the root receipt's linked lineage descriptor, the lineage receipt's explicit descriptors, and the hash-verified source receipt/build spec they name. Do not glob for substitute CSVs or figures. The lineage receipt's prior DOCX, builder receipt/manifest, rendered PDF/PNGs, QA, and extracted tables are verification history only and are forbidden as Grok build inputs. If either receipt is absent, either schema differs, a required descriptor is absent, a path/hash disagrees, or the 10-row lineage is not demonstrated, stop as `INCOMPLETE` and do not write a passed P2 wrapper.

## Independence and write boundary

- Work from `/Users/wyih/Projects/Auto-research-in-sleep`.
- Use a new UTC tag and write all Grok P2 files beneath:

  ```text
  .aris/business-e2e/20260718T011517Z/grok-workspace/integrated-chain/p2/<grok_run_tag>/
  ```

- Use `input/` only for the new Grok build spec and audit helpers, `output/results_docx/` for the DOCX/manifest/builder receipt, `rendered/` for the final PDF/PNGs, `qa/` for visual/accessibility/metadata reports, and `receipts/` for the Grok acceptance receipt.
- Never overwrite an existing tag. Never use `--force` to replace an existing accepted artifact.
- Do not open, copy, rename, repackage, or use as input anything under `.aris/business-e2e/20260718T011517Z/p2/`. In particular, never copy `aris_p2_results_pack.docx`, its synthetic CSVs/figure, its receipt, or its QA reports.
- Do not write under `paper/`, `papers/`, `manuscript/`, `submission/`, or `submissions/`, and do not modify any manuscript file.
- No browser or MCP is needed. Do not use network content or browser state for this stage.

## Build-spec gate

Validate every receipt-listed coefficient CSV against the current tidy contract before building:

- required fields: `term`, `estimate`, `std.error`, `p.value`, and `model_id` (or the documented `model` alias normalized to `model_id`);
- one coefficient row per `(panel, term, model_id)`;
- parseable estimates/SEs/p-values, with p-values in range;
- internally consistent `nobs`, dependent-variable, fixed-effect, cluster, control, and model labels within model;
- main, null, and mixed results remain present; do not drop an insignificant row;
- no causal label is introduced merely because a coefficient is significant.

Validate the descriptives source and figure lineage against the current contracts. Missing values must remain missing; do not impute zero. The figure must be the explicitly listed integrated-chain figure. Recover its source-data and source-script relationship only from the hash-verified lineage-listed build spec, then require those resolved files to match `wrds_lane.processed`/`wrds_lane.artifacts`. Do not reuse any prior DOCX or render and do not redraw the figure.

Create a new JSON spec beneath the Grok P2 root. It must:

- use a Grok-specific `run_id` linked to the integrated-chain run ID and this run tag;
- include an explicit `as_of_date`;
- reference only the receipt-listed, hash-verified coefficient, descriptive, figure, source-data, and source-script files;
- include every listed coefficient table, the listed descriptives table, and every listed figure;
- choose `primary_term` and `primary_model` that actually exist and preserve a null result when the handoff's primary result is null;
- state the actual estimator/FE/cluster/sample notes from the handoff without embellishment;
- use non-causal association language and make the 10-row smoke scope conspicuous;
- supply meaningful figure alt text and source data.

Hash the new spec and record a machine-readable input audit before invoking the builder.

## Fresh production build

Invoke the current canonical CLI as a new Grok process:

```bash
python3 skills/results-to-docx/scripts/build_results_docx.py \
  --spec "<new_grok_p2_root>/input/build_spec.json" \
  --out "<new_grok_p2_root>/output/results_docx/grok-wrds-10row-results.docx" \
  --author "Yihong Wang"
```

Do not use `--force`. Require a zero exit, a newly created DOCX, `RESULTS_DOCX_MANIFEST.md`, and `RESULTS_DOCX_RECEIPT.json`. Verify from the builder receipt that:

- builder is `results-to-docx` and the run ID is the new Grok run;
- the DOCX path is under this Grok tag's `results_docx/` directory;
- every input path/hash matches the integrated receipt or the new Grok spec;
- all receipt-listed tables/figures are present;
- every generated narrative claim points to a real CSV row and raw values;
- null/mixed results are preserved and prose does not exceed an associational claim ceiling;
- `safety.manuscript_files_modified` is false.

Run the current production test file and record its command, file hash, and observed result:

```bash
python3 -m unittest tests.test_results_to_docx -v
```

No failed/error test is allowed.

## Final metadata gate

The builder normalizes metadata, but audit the final file again after the last save:

```bash
python3 skills/results-to-docx/scripts/normalize_docx_author.py \
  --check "<new_docx_path>"
```

Require:

- Creator/Author exactly `Yihong Wang`;
- Last Modified By exactly `Yihong Wang`;
- Company and Manager empty;
- no prior author/editor custom properties;
- no comment/people author parts or comment markers;
- no tracked changes;
- no `rsid*` revision-session attributes.

Store the JSON audit under the Grok P2 `qa/` directory. If normalization must be rerun for a discovered defect, render and inspect the post-normalization file again; a pre-normalization render is not evidence.

## Render and visual gate

Render the **final normalized DOCX** to a PDF and one PNG per page. Use the local LibreOffice/Poppler route available to the Grok CLI (for example `soffice` or the installed LibreOffice binary, followed by `pdftoppm`); do not use or copy the prior Codex PDF/PNGs. Record exact renderer binaries/versions and commands without environment secrets.

Open and visually inspect every newly rendered page at original size/100% using Grok's available local image-reading capability. Package/XML checks alone are not visual acceptance. Require:

- no clipped or overlapping text;
- no table or figure overflow beyond page margins;
- intact academic three-line rules and no unintended vertical/inside borders;
- readable labels, notes, legends, symbols, and glyphs;
- no missing image, blank page, accidental orphan heading/caption, or broken page furniture;
- the rendered title and narrative clearly identify the real 10-row WRDS smoke scope.

If Grok has no way to inspect the PNG pixels visually, mark `visual_inspection_unavailable` and do not pass. If a page defect is found, fix only the Grok build spec or builder-compatible input, rebuild to a new collision-free tag, normalize, rerender, and inspect all pages again.

Write `qa/visual_report.json` containing page count, every PNG's project-relative path/bytes/SHA-256, `inspected_at_100_percent: true`, per-page findings, renderer details, and aggregate pass/fail. Hash the final PDF and every PNG.

## Accessibility and structure gate

Audit the final DOCX package and write `qa/a11y_report.json`. At minimum require:

- `counts.high`, `counts.medium`, and `counts.low` all equal zero and `findings` is empty;
- real heading styles form a sensible hierarchy;
- every table header row is marked with `w:tblHeader` for repetition;
- each figure has nonempty, meaningful alt text on both `wp:docPr` and `pic:cNvPr`;
- no blank alt text, duplicate placeholder alt text, or image-only result without a textual caption/note;
- table grid/width geometry fits the usable page width;
- top/header/bottom rules are present, with active vertical and inside borders absent;
- generated prose and table notes remain readable in document order.

Also write `qa/P2_GROK_ACCEPTANCE.md` summarizing the fixed integrated-chain receipt/hash, 10-row lineage, new builder invocation, DOCX/PDF/page hashes, metadata result, page-by-page visual result, accessibility result, test result, narrative provenance, and manuscript safety. Do not use the words PASS unless every gate above passed.

## Grok P2 receipt and runtime wrapper

After all gates pass, write `<new_grok_p2_root>/receipts/p2-results-docx-grok.json` using a non-wrapper schema such as `aris.business-e2e.results-docx-acceptance.v1`. Include:

- `runtime: grok`, `stage: P2`, `status: pass`, invoked skill, timestamps, and Grok tag;
- integrated-chain receipt path/hash and its real 10-row WRDS lineage;
- explicit input descriptors and verified hashes;
- canonical builder path/hash, command without secrets, builder receipt path/hash, DOCX bytes/hash, manifest hash, tables/figures/narrative counts;
- metadata audit, visual page audit, accessibility audit, and unit-test observations with hashes;
- `codex_pack_or_synthetic_input_reused: false` and `manuscript_files_modified: false`.

Only then create a uniquely named wrapper beneath `.aris/business-e2e/20260718T011517Z/grok-workspace/receipts/`:

```json
{
  "schema_version": "aris.business-e2e.runtime-invocation.v1",
  "runtime": "grok",
  "stage": "P2",
  "status": "passed",
  "recorded_at": "observed_ISO_8601",
  "skill": "results-to-docx",
  "invocation": {
    "grok_run_tag": "observed_unique_tag",
    "integrated_chain_root_schema": "aris.business-e2e.integrated-chain-root.v2",
    "integrated_chain_lineage_schema": "aris.business-e2e.integrated-chain-lineage.v2",
    "real_wrds_source_rows": 10,
    "fresh_docx_build": true,
    "codex_pack_reused": false,
    "visual_pages_inspected": 0,
    "accessibility_findings": 0
  },
  "evidence": [
    {
      "path": ".aris/business-e2e/20260718T011517Z/grok-workspace/integrated-chain/p2/<tag>/receipts/p2-results-docx-grok.json",
      "size_bytes": 0,
      "sha256": "observed_64_hex"
    }
  ]
}
```

Replace every placeholder and zero. Evidence must include only new files from this Grok build: the Grok acceptance receipt, final DOCX, builder receipt/manifest, metadata report, visual report, accessibility report, acceptance Markdown, final PDF, and page PNGs. Each entry needs an actual project-relative path, byte size, and SHA-256. Do not list the integrated-chain source receipt itself as Grok runtime output; its hash belongs inside the new Grok acceptance receipt as input lineage.

Run:

```bash
python3 /Users/wyih/Projects/Auto-research-in-sleep/scripts/verify_business_e2e.py \
  --run-id 20260718T011517Z --json
```

Require `runtimes.grok.stages.P2.status` to be `PASS`. Overall acceptance may remain incomplete for unrelated stages.

## Failure rule

On any missing handoff, schema/hash mismatch, synthetic-input detection, builder error, metadata defect, uninspectable or defective page, accessibility finding, test failure, or verifier failure, do not create a passed `aris.business-e2e.runtime-invocation.v1` wrapper and do not copy the Codex pack as a fallback. Preserve a redacted non-wrapper failure receipt with the exact last verified state, blocker, and safe retry point.
