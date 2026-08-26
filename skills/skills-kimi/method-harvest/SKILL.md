---
name: method-harvest
description: Extract evidence-grounded METHOD_CARD artifacts from verified local research-paper fulltext. Use when empirical design or fulltext literature synthesis needs a paper's question, theory, construct depth, observation/respondent/unique-entity units, identification, exact factor/index or questionnaire construction, numeric consistency audit, mediation evidence, fixed effects, clustering, data lineage, main/null results, limitations, or claim ceiling; invoke fulltext-acquire first when no verified PDF exists. Not for browser downloads or CSMAR/CNRDS microdata export.
---

# Method Harvest

Turn one or more verified local papers into reusable method cards without inventing details.

## Inputs

- target papers and why each matters
- verified local PDF paths or `literature/FULLTEXT_MANIFEST.md`
- existing literature/design notes when they define the desired method fields
- synthesis questions when the cards will feed `business-lit-review` (for example, construct measurement, result conflicts, or reusable variable formulas)

Read `references/pdf-processing.md` and `references/method-card-template.md` before extraction. Read `../shared-references/business-helper-resolution.md` before invoking the verifier bundled with `/browser-session-bridge` outside the ARIS repository.

## Acquisition Gate

If a target lacks a verified local PDF, invoke `fulltext-acquire` and stop extraction until it returns either:

- a PDF that passes deterministic integrity and identity checks, or
- a documented gap

Do not perform browser navigation inside this skill. Do not treat metadata, an abstract, CAJ, HTML, or a visible browser PDF viewer as verified fulltext.

## Workflow

### 1. Freeze targets

For each work, record a stable METHOD_CARD/synthesis `work_id`. For each acquired PDF, separately record its `FULLTEXT_MANIFEST` `artifact_id`, `parent_artifact_id`, role, specific version identity, DOI/source ID, local path, content hash, and the design/measure/data question to answer. Do not substitute an acquisition-specific artifact ID for the stable work ID.

### 2. Verify source depth

Run the shared verifier when the PDF is not already represented by a current accepted manifest row:

```bash
python3 "$BRIDGE_SKILL_DIR/scripts/verify_download.py" PAPER.pdf --expect pdf --min-bytes 10240
```

Confirm that the document title or DOI matches the target. Identity must be checked on the title pages rather than by a token found anywhere in the PDF; add author or DOI corroboration when available. Set `source_depth=fulltext`. If the only authorized material is an abstract, explicitly set `source_depth=abstract_only` and leave unsupported method fields unknown.

### 3. Preflight and extract the PDF

Follow `references/pdf-processing.md`. Run `scripts/inspect_pdf.py` with the work/artifact/version identity tuple to record the source hash, page count, text-layer coverage, likely OCR pages, extraction-tool version, and title-token identity result. Keep the source PDF immutable.

Use the runtime's local PDF reader. If unavailable and the PDF contains text, use a local command such as `pdftotext -layout`; do not upload licensed papers to an unrelated third-party service. For image-only scans, use authorized local OCR, retain source/derivative hashes and page mapping, and stop extraction while the receipt says `ocr_required`. Use the inspector's `--render-required-pages` and repository-contained `--render-output-dir` for every page in `visual_review_pending_pages`; after reviewing those PNGs, rerun the same render command with explicit cleared page numbers before treating the receipt as ready. Use repeatable `--render-page` for focal definitions, formulas, tables, and appendices. Accept only the inspector's native, hash-bound `render_evidence`; never inject page-image facts into the JSON afterward.

Build a page-range structure map first, then extract evidence. Capture page/section/equation/table/figure/appendix locations for every material method statement. Render and visually check focal definitions, sample flow, the main specification, material result tables, and questionnaire/index appendices; text extraction alone is not sufficient for formulas or tables.

### 4. Build the method card

Extract only what the source supports:

| Block | Required content |
|---|---|
| Bibliographic | title, authors, year, venue, DOI/source ID |
| PDF processing | source/derivative hashes, page count, text/OCR route, identity status, page-map status, and visual-check evidence |
| Question and theory | research question, theoretical mechanism, hypotheses/predictions, construct definitions |
| Construct map | each focal construct's role and depth: espoused value, promotion artifact, perceived norm, enacted norm, domain-specific practice, effectiveness/outcome, other, or unknown |
| Sample and dependence | observation/respondent/estimand unit, response N, unique-entity N, responses per entity, period, geography, filters, final N, dependence, and cluster-unit alignment |
| Identification | design family, variation, treatment/timing, comparison, assumptions, threats |
| Variables | outcomes, key X/treatment, mediators/moderators, controls, exact construction/coding/transforms, source location |
| Measurement provenance | factor/index inputs and scoring; questionnaire version, item text, translation, reverse scoring, weights, zero/missing handling, and reproducibility |
| Inference | fixed effects, clustering, other standard-error choices |
| Data | vendor/source, years, grain, keys or merge hints |
| Findings | main, null/mixed, and mechanism/heterogeneity results with model/table locations and economic magnitude when stated |
| Numeric audit | estimate/SE versus reported statistic, sign, p-value/stars/CI, prose versus table, sample-N reconciliation, and indirect-effect arithmetic |
| Mediation | temporal order; paths a, b, c, and c-prime; indirect effect; estimator; test/CI; and common-method assessment |
| Boundaries | robustness, limitations, external-validity boundary, and supported claim ceiling |
| Reuse | codebook candidates and cautions for the current project |

Write `method-harvest/cards/<short_id>_METHOD_CARD.md`. For multiple papers, update `method-harvest/METHOD_CARD_INDEX.md`.

### 5. Audit the card

- Compare the card against the paper's methods/data sections, main specification, table notes, and relevant appendix.
- Confirm the card's PDF-processing receipt still matches the source hash and page count; require artifact identity `pass`, fulltext identity `pass`, no pending sparse-page review, and preserve any OCR derivative hash and original-viewer-page mapping. Confirm `work_id` matches the METHOD_CARD, `artifact_id` matches the exact manifest row, and companion `parent_artifact_id` points to the main artifact rather than to itself.
- Recompute PNG hashes, byte counts, and IHDR dimensions from every inspector-generated visual evidence path before relying on the associated page. Confirm the path is repository-relative, the filename `-pN` token matches its 1-based viewer page, and the evidence's source PDF hash/page count matches the current PDF.
- Check every variable formula for numerator, denominator, transform, lag/window, aggregation, coding orientation, standardization/winsorization, unit, and missing-value rule when stated.
- For every factor, index, or composite, fill the factor/index sub-schema: inputs, input transforms and zero handling, extraction or aggregation method, standardization, weights/loadings, factor count/retention, rotation, score method, sign, explained variance, and missing rule. Set `index_reproducibility` to `complete`, `partial`, `not_reproducible`, or `not_applicable`.
- For every administered scale, record the administered version, original citation, item text/codes, language/translation, response anchors, reverse-coded items and direction, composite rule/weights, missing-item rule, and questionnaire-versus-table reconciliation.
- Reconcile response count with unique-entity count. Record observation, respondent, estimand, and cluster units separately; never substitute answer count for unique-firm N.
- Check every main or null result against the exact outcome, specification, sample, coefficient/effect, uncertainty, and table or figure location. Distinguish statistical from economic magnitude.
- Run the numeric consistency audit for every material reported estimate: compare estimate/SE with the reported t, z, or CR when on the same scale; check sign, p-value/stars/CI, prose-versus-table wording, and sample N. For mediation, also check the reported indirect effect against `a * b` when the paths share a compatible scale. Record the rounding tolerance and distribution. Use `not_applicable` only with a reason.
- Treat a numeric conflict as source evidence, not a typo to repair. Set `numeric_audit_status=fail` or `needs_verification`, preserve the competing values and locations, and set `ready_for_design=no` or `conditional` until resolved.
- For every mediation claim, record temporal order, a, b, c, c-prime, a-times-b, estimator/scale, indirect-effect SE, Sobel/bootstrap/delta/posterior method, resamples, CI, covariates/FE, and common-method assessment. Label a three-step significance argument `significance_steps_only` rather than a verified indirect effect.
- Mark unstated or ambiguous details `unknown` or `needs_verification`.
- Use `PDF p.<viewer-page>` for the 1-based PDF viewer page. Add `printed p.<page>` or `article p.<page>` when printed pagination differs; never write an unlabeled bare page number.
- Distinguish the paper's choices from recommendations for the current project.
- Preserve vendor names as printed; do not silently map them to a different database.
- Ensure every extracted definition has a page, section, table, or appendix pointer.

### 6. Handoff

Route cross-paper synthesis inputs to `business-lit-review` in `fulltext_synthesis` mode, design implications to `empirical-design-plan`, WRDS variables/keys to `wrds-query-bridge`, and Chinese microdata gaps to `cn-data-bridge`.

## Acceptance

| Gate | Evidence |
|---|---|
| Source | Verified identity-matched local PDF and SHA-256; stable work ID is distinct from the exact manifest artifact/version identity |
| PDF processing | Current native inspection receipt, usable text/OCR route, immutable original, page mapping, and inspector-generated hash/page/IHDR-bound PNG checks for material formulas/tables |
| Grounding | Material fields include source locations |
| Completeness | Question/theory, sample, identification, variables, inference, data, findings, limitations, and claim ceiling completed or explicitly unknown |
| Unit fidelity | Response/observation/estimand/unique-entity units and cluster alignment are explicit; unknown counts are not equated |
| Measurement fidelity | Index/factor and questionnaire sub-schemas preserve weights, standardization, zero/missing rules, item direction, and provenance or explicit unknowns |
| Calculation fidelity | Variable formulas preserve stated transforms, windows, units, and coding rules without inference |
| Numeric consistency | Every material result has an explicit audit status; failed or unverifiable arithmetic/prose conflicts lower design readiness |
| Mediation fidelity | a, b, c, c-prime, indirect effect, test/CI, temporal order, and common-method assessment are present or explicitly unknown/not applicable |
| Result fidelity | Main and null/mixed findings point to the exact model/table/PDF page and retain the paper's claim ceiling |
| Separation | No browser/tool-specific acquisition logic in this skill |
| Handoff | Concrete design/data implications and unresolved gaps |

## Output

```markdown
# Method Harvest Summary

| work_id | artifact_id | local_pdf | sha256 | source_depth | card_path | design_ready | unresolved_gap |
|---|---|---|---|---|---|---|---|

## Cross-Paper Method Patterns
## Construct, Measure, And Result Comparability
## Data And Identifier Handoffs
## Gaps Requiring Fulltext Or Clarification
```

## Rules

- Never invent a sample rule, variable definition, estimator, fixed effect, cluster, data source, index weight, zero-value rule, reverse-coded item, unique-entity count, or mediation path.
- Do not use domain convention to fill a required field. Write `unknown` when the source is silent and `needs_verification` when its own locations conflict.
- Do not copy an abstract-level claim into a full method field.
- Do not perform CNKI/ScienceDirect browsing here; use `fulltext-acquire`.
- Do not export CSMAR/CNRDS data here; use `cn-data-bridge`.
- Do not treat a significance count as a literature conclusion; hand cards to `business-lit-review` for cross-paper comparison.
