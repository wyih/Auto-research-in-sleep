# Grok P3 verified-PDF synthesis v2 runtime acceptance

Use the installed project skills `$method-harvest` and `$business-lit-review` in `fulltext_synthesis` mode. Read both `SKILL.md` files, `method-harvest/references/method-card-template.md`, and `business-lit-review/references/fulltext-synthesis.md` before acting. This is a fresh Grok-runtime PDF-to-method-card-to-evidence-matrix-to-review execution, not a summary of the existing Codex synthesis.

## Scope and prohibited reuse

- This prompt must be launched from a workspace created by `scripts/prepare_p3_grok_blind_workspace.py`, with `PYTHONDONTWRITEBYTECODE=1`, Grok `--sandbox strict`, `--permission-mode bypassPermissions`, `--cwd <p3_root>`, web/MCP meta-tools disabled, memory disabled, and subagents disabled. Confirm `inputs/isolation-preparation.json` records those exact controls before acting; otherwise stop with a non-wrapper failure record.
- Work only inside the current isolated `<p3_root>`. The strict sandbox is the filesystem boundary: do not attempt to traverse to the parent repository or any absolute source path shown only for lineage.
- The outer repository root `<outer_repo_root>` is supplied only as a path-namespace argument to `inspect_pdf.py --repo-root`; do not list, read, or traverse it. The candidate's canonical repository-relative prefix is exactly `<repo_candidate_root>`.
- This stage is offline. Use local CLI/PDF capabilities only; do not browse, connect to Chrome MCP or another MCP, log in, download, or use network search.
- Do not open, copy, rename, paraphrase from, or use as content input any prior method card, matrix, review, acceptance report, or synthesis receipt under:
  - `.aris/business-e2e/20260718T011517Z/method-harvest/`
  - `.aris/business-e2e/20260718T011517Z/literature/`
  - `.aris/business-e2e/20260718T011517Z/literature-v2/`
  - `.aris/business-e2e/20260718T011517Z/literature-forward-test/`
  - `.aris/business-e2e/20260718T011517Z/receipts/p3-literature-synthesis.json`
- Only the two skill snapshots under `skills/`, `inputs/FULLTEXT_MANIFEST_MINIMAL.md`, `inputs/isolation-preparation.json`, `tools/verify_download.py`, this prompt, and the three snapshot PDFs below are allowed. Do not read repository tests, prior expected-output fixtures, root verifiers, or any prior P3 artifact before generating and freezing your candidate artifacts. Every substantive claim must be independently recovered from the PDF.
- Copying the three immutable verified PDFs into the isolated Grok test bundle is permitted only as an input snapshot with identical hashes. It is not a fresh browser acquisition and must never be represented as one. No prior synthesis output may be copied.

The preparation runner has already assigned a new UTC run tag and created the isolated root:

```text
.aris/business-e2e/20260718T011517Z/grok-workspace/p3-synthesis-v2/<grok_run_tag>/
```

Do not create another tag or overwrite any prepared input. Beneath this root use:

```text
artifacts/fulltext/open/
artifacts/fulltext/sciencedirect/
artifacts/fulltext/cnki/
extracted/
literature-v2/cards/
literature-v2/pdf-processing/rendered-native-v2/
literature-v2/pdf-processing/PDF_VISUAL_CHECKS.md
literature-v2/LITERATURE_EVIDENCE_MATRIX.md
literature-v2/BUSINESS_LIT_REVIEW.md
literature-v2/ACCEPTANCE_REPORT.md
receipts/
qa/
```

The `literature-v2` name and bundle topology are required by the current real-bundle integration test.
Do not create any other top-level directory. In particular, never create top-level `local-bin/`. If strict sandboxing hides host Poppler and a PyMuPDF compatibility shim is necessary, place the executables only under `qa/local-bin/`, prepend that directory to `PATH`, and inventory them at freeze. Run every Python process with `python3 -B`; the launch environment also sets `PYTHONDONTWRITEBYTECODE=1`. No `__pycache__` or `.pyc` may be created anywhere, especially under the protected `skills/` tree.

## Fixed three-paper corpus

The user-authorized acceptance corpus is exactly these three papers. It overrides the 8–15 discovery target. Do not add a paper merely to increase count; label unrequested discovery/venue positioning `HANDOFF_INCOMPLETE` rather than inventing it.

| paper_id | identity | authorized verified source | expected pages | expected SHA-256 | isolated snapshot path |
|---|---|---|---:|---|---|
| `graham_harvey_popadak_rajgopal_2017` | *Corporate Culture: Evidence from the Field*, NBER w23255 / SSRN 2937525 | `.aris/business-e2e/20260718T011517Z/artifacts/fulltext/open/corporate-culture-field-w23255.pdf` | 79 | `f69be9aa4373ff67db8a98b9bcb27ff3576067ae82a1337a88e1aaed998847a2` | `<p3_root>/artifacts/fulltext/open/corporate-culture-field-w23255.pdf` |
| `zhao_teng_wu_2018` | *The effect of corporate culture on firm performance: Evidence from China*, DOI 10.1016/j.cjar.2018.01.003 | `.aris/business-e2e/20260718T011517Z/artifacts/fulltext/sciencedirect/S1755309118300030-corporate-culture-firm-performance-china.pdf` | 19 | `459e22da3a37ad6bd4823271ddfc4d6c8d027e054a43057b89c6cd0090d9770b` | `<p3_root>/artifacts/fulltext/sciencedirect/S1755309118300030-corporate-culture-firm-performance-china.pdf` |
| `duan_2018` | 《质量文化对企业绩效的影响研究——组织承诺的中介作用》, CNKI CMFD201901 / 1018120457.nh | `.aris/business-e2e/20260718T011517Z/artifacts/fulltext/cnki/duan-2018-quality-culture-performance.pdf` | 67 | `79b6a8b9f2c6f075343f1322c38ff4c6c79abedba8ed963cee5f8a6094a28117` | `<p3_root>/artifacts/fulltext/cnki/duan-2018-quality-culture-performance.pdf` |

For each source:

1. Confirm that the matching row in `inputs/FULLTEXT_MANIFEST_MINIMAL.md` is `verified` and that `inputs/isolation-preparation.json` records source/snapshot byte identity, hash, and page count matching the table above.
2. Run `tools/verify_download.py SNAPSHOT --expect pdf --min-bytes 10240`, `pdfinfo`, SHA-256, and PDF-text identity checks on the already-prepared snapshot. Do not invoke an MCP helper.
3. Do not copy again or modify the snapshot PDF. Extract text locally with layout preservation (or use Grok's local PDF reader) into `extracted/`. Do not upload licensed PDFs or extracted text to a third party.
4. Record preparation-receipt lineage plus snapshot path, bytes, pages, hash, verifier result, and identity tokens in `receipts/input-lineage.json`. Do not add or modify anything under the protected `artifacts/`, `inputs/`, `skills/`, or `tools/` trees. If any identity/hash/page gate fails, stop; do not fall back to an abstract or an old card.

## Phase A — regenerate v2 method cards

Invoke `$method-harvest` over the isolated snapshots. Read the full methods/data/results/table notes and relevant appendices; do not merely search for acceptance strings. Write exactly:

```text
literature-v2/cards/graham_harvey_popadak_rajgopal_2017_METHOD_CARD.md
literature-v2/cards/zhao_teng_wu_2018_METHOD_CARD.md
literature-v2/cards/duan_2018_METHOD_CARD.md
literature-v2/cards/METHOD_CARD_INDEX.md
```

Each card must use the current full template and include the snapshot's project-relative `local_path`, `size_bytes`, page count, `content_hash: sha256:<hash>`, `source_depth: fulltext`, and unambiguous `PDF p.<viewer-page>` pointers. Add printed/article pagination only when it differs; never use an unlabeled page number.

For each snapshot, run `python3 -B skills/method-harvest/scripts/inspect_pdf.py` with the exact `work_id`, `artifact_id`, `parent_artifact_id`, `artifact_role`, `version_identity`, and `doi_or_source_id` from its isolated 21-column manifest row. Always pass `--repo-root <outer_repo_root>` so the receipt's `source_pdf` and every `render_evidence.pages[].png_path` are canonical repository-relative paths beginning `<repo_candidate_root>/`; do not invoke the inspector through an imported wrapper. Render all pages required by the inspector plus the material evidence pages you rely on, and write the three `aris.method-harvest.pdf-inspection.v2` receipts and their `aris.method-harvest.render-evidence.v1` PNG evidence under `literature-v2/pdf-processing/`. Write `PDF_VISUAL_CHECKS.md` only after those rendered pages are visually checked. The same six-field artifact-identity tuple must appear unchanged in the synthesis input, PDF-processing `artifact_identity`, method card, and exactly one isolated manifest row.

For every required field, supply a PDF-supported value, `unknown`, `needs_verification`, or `not_applicable: <reason>`. Blank required cells fail. Do not fill a missing formula, index weight, zero rule, questionnaire item/direction, unique-entity count, cluster, fixed effect, mediation path, or causal assumption by domain convention.

At minimum, independently audit each paper's:

- research question, constructs, theory/mechanism, hypotheses, and construct depth;
- observation, respondent, response N, unique-entity type/N, respondents per entity, estimand, dependence, cluster unit, and cluster/dependence alignment;
- sample period/geography/filters/final N and what that N counts;
- outcomes, key X, mediator/moderator, controls, exact numerator/denominator/coding/transform/lag/window/unit, winsorization/standardization, sign, zero and missing rules;
- factor/index inputs, transformations, extraction/aggregation, weights/loadings, retention/rotation, scoring, explained variance, missing rule, and reproducibility;
- questionnaire version/citation/language/translation/anchors/items/direction/reverse coding/composite/missing rule and table reconciliation;
- data source, years, grain, identifiers/merge hints;
- design family, identifying variation, comparison, assumptions/threats, estimator, fixed effects, clustering and other inference choices;
- main, null, mixed, mechanism and boundary results with exact model/table/page locations and economic magnitude when supported;
- numeric consistency for every material result: estimate/SE versus statistic, sign, p/stars/CI, prose versus table, sample N, distribution/rounding tolerance, and mediation `a*b` arithmetic when compatible;
- complete mediation fields `a`, `b`, `c`, `c-prime`, indirect effect, SE, estimator/scale, test, resamples, CI, temporal order, covariates/FE and common-method assessment;
- robustness, limitations, external-validity boundary, safe claim, unsafe claim, and `ready_for_design` impact.

Preserve source conflicts instead of repairing them. In particular, a failed or unresolved numeric check must remain `fail`/`needs_verification`, lower design readiness, and constrain later prose. Preserve null and mixed results; do not vote-count significance.

Before drafting a card, complete two exhaustive fulltext passes that are independent of any acceptance fixture:

1. **Main/robustness-table transcription pass.** Enumerate every main or robustness table/panel that links the focal construct, mediator/moderator, or measurement factor to an outcome. For every material row, carry all reported dependent-variable cells—not only the headline cell—into the card with exact sign, coefficient, stars, SE or parenthesized statistic, model/column, and N/range. Preserve null cells beside significant cells. If a panel reports multiple culture aggregates, outcome families, or steps of a mediation regression, transcribe each material row/cell needed to audit the paper's own conclusion. Put printed numeric literals in Markdown code spans and record the exact table/panel plus 1-based PDF viewer page.
2. **Variable-definition and appendix pass.** Search the complete PDF, including appendices and table notes, for every outcome/key-X/mediator name and close synonym. If an exact numerator/denominator, accounting-code formula, log transform, zero rule, lag/window, factor input, questionnaire coding rule, or sample-N definition appears anywhere, record it verbatim enough to reproduce it; do not leave that field `unknown`. Only use `unknown` after documenting that the complete-text and appendix search found no rule. Propagate every recovered formula and unresolved zero/missing rule into the evidence matrix and review.

The numeric audit covers sample identity and denominator consistency as well as coefficient arithmetic. Therefore, even when coefficient/SE/statistic checks pass, an unresolved conflict between reported responses/observations and unique entities/firms makes the paper-level numeric audit at least `needs_verification`, not `pass`. Explain the exact conflict and keep coefficient-cell subchecks separately marked pass where appropriate.

For machine-readable handoff fields, preserve these exact Markdown forms: `local_path: \`<canonical repo-relative path>\``, `content_hash: \`sha256:<64 hex>\``, `pdf_processing_receipt: \`<canonical repo-relative path>\``, and `source_pdf_sha256: \`<64 hex>\``. Do not omit code spans around paths/hashes. Each card must include both a standalone `pages: <integer>` handoff field and `source_pdf_pages: <same integer>` in its PDF Processing section; these are distinct required keys and neither substitutes for the other. Also include `identity_check: pass` and `source_pdf_preserved: yes`.

The index must enumerate all three cards, their fulltext channels, numeric-audit status, factor/index reproducibility, design readiness, and unresolved gaps.

## Phase B — regenerate evidence matrix and review

Invoke `$business-lit-review` in `fulltext_synthesis` mode using only the three new cards and isolated snapshots. Spot-check every material card claim against the PDFs before using it.

Build `literature-v2/LITERATURE_EVIDENCE_MATRIX.md` first. It must contain all three paper IDs/hashes and the current main matrix plus these linked per-paper audit subsections:

- Observation And Dependence Audit;
- Factor / Index Reproducibility Audit;
- Questionnaire / Scale Provenance Audit;
- Numeric Consistency Audit;
- Mediation Evidence Audit.

Every required cell must be explicit; blanks fail. Preserve exact variable calculations or explicit unknowns, main/null/mixed results, source conflicts, and source locations. Before comparing results, classify apparent disagreement as `substantive_conflict`, `measurement_difference`, `sample_or_setting_difference`, `design_or_estimand_difference`, `timing_difference`, `not_comparable`, or `needs_verification`.

Then write `literature-v2/BUSINESS_LIT_REVIEW.md`. Organize it by research questions, constructs, mechanisms, measurement families, units/settings, designs, findings/conflicts, boundaries, and implications—not as three sequential paper summaries. Every material source-derived sentence must carry a stable paper ID plus page/section/table/appendix pointer. Include a Source Grounding section with each PDF hash and new card path. Label cross-paper inference as synthesis, preserve the fixed-corpus scope, and keep the common claim ceiling no stronger than the designs support.

Use causal language only when the paper's design and identifying assumptions support it. Any unresolved or internally inconsistent numeric evidence must remain unresolved and must constrain the review. State what is genuinely comparable, what is not, and which variable definitions remain unreproducible.

The following machine-contract tokens and heading levels are mandatory. They specify structure only; recover all substantive values independently from the PDFs.

- `METHOD_CARD_INDEX.md`: `# METHOD_CARD_INDEX`, `## Corpus Gate`, and the literal fields `numeric_audit_status`, `index_reproducibility`, `ready_for_design`.
- `LITERATURE_EVIDENCE_MATRIX.md`: `# LITERATURE_EVIDENCE_MATRIX`, `## Corpus And Source Gate`, `## Exact Variable Construction`, then for each paper the exact level-four headings `#### Observation And Dependence Audit`, `#### Factor / Index Reproducibility Audit`, `#### Questionnaire / Scale Provenance Audit`, `#### Numeric Consistency Audit`, `#### Mediation Evidence Audit`; also `## Agreement And Conflict Classification`, `## Unresolved Fulltext Fields`, and `## Evidence-Matrix Bottom Line`. Include the literal `numeric_audit_status=<card value>` for each paper.
- `BUSINESS_LIT_REVIEW.md`: `# BUSINESS_LIT_REVIEW`, `## Conclusion`, `## Required Handoff Fields`, `## 2. How Variable Calculation Changes The Question`, `## 3. Observation Units, Dependence, And Identification`, `## 4. Findings, Nulls, And Apparent Contradictions`, `## 5. Does The Corpus Establish A Mediation Mechanism?`, `## 6. Claim Ceilings And Safe Language`, and `## Source Grounding`.
- `ACCEPTANCE_REPORT.md`: `# P3 V2 OFFLINE ACCEPTANCE REPORT`, `## Source Gate`, `## Artifact Inventory`, `## Contract Gates`, `## Material Paper-Level Status`, `## Real Source-Evidence Spot Checks`, and `## Remaining Evidence Gaps`.
- `PDF_VISUAL_CHECKS.md`: `# P3 PDF Visual Checks` plus the literal phrases `visually checked source pages`, `rendered source pages`, and `OCR was not used`.

Each method card must start with `# METHOD_CARD: <paper_id>` and preserve every heading and nonblank handoff field in `method-card-template.md`, including all six artifact-identity fields.

## Blind forward-test boundary

Freeze the complete candidate bundle before any repository test or verifier is opened. Do not run, hash, summarize, or inspect files under `tests/` or `scripts/verify_business_e2e.py`; do not ask another agent to do so during this invocation. Write `qa/grok-generation-record.json` with the exact field `"schema_version": "aris.business-e2e.p3-generation-record.v1"` (never use a field named `schema` for this record). Use the fields `generation_started_at`, `frozen_at`, `grok_run_tag`, runtime/stage, the four false provenance flags specified below, `frozen_artifacts`, and `bundle_digest`. `frozen_artifacts` must be the exact, sorted, repository-relative path/byte/SHA-256 inventory of every file under the candidate root except the generation record itself and the later candidate receipt. Every inventory `path` must begin with the literal prefix `<repo_candidate_root>/`; a candidate-relative value such as `PROMPT.md` is invalid. Compute `bundle_digest` as SHA-256 of compact, key-sorted UTF-8 JSON for the sorted projection of each artifact's `path`, `sha256`, and `size_bytes`. After writing this record, the only permitted addition is the candidate receipt described below; do not otherwise modify, add, or remove any candidate-bundle file. The root Codex acceptance runner will execute all deterministic tests externally after Grok returns. If the external runner later reports a failure, a new Grok tag may repair it from the PDFs and skill contract, but the original blind candidate must remain immutable and must never be overwritten.

## Acceptance report and synthesis receipt

Write `literature-v2/ACCEPTANCE_REPORT.md` only after the artifacts exist. It must state:

- the exact truthful phrase `offline; no browser, login, cookie, credential, or network acquisition operation`, plus the fact that no MCP operation occurred;
- all three source/snapshot identities and hashes;
- all new card/matrix/review paths and hashes;
- per-paper numeric-audit and mediation status derived independently from each PDF, including any unresolved or failing source conflicts;
- method-card completeness, unit/dependence, measurement, numeric-consistency, mediation, result, and claim-ceiling gates;
- the following exact truthful sentence, verbatim: `Repository tests and root verifiers were not read or run during blind generation and remain pending external acceptance.`;
- fixed three-paper acceptance scope and any `HANDOFF_INCOMPLETE` discovery/positioning item.

Write `<new_grok_p3_root>/receipts/p3-synthesis-grok-v2-candidate.json` using the exact non-wrapper field `"schema_version": "aris.business-e2e.p3-synthesis-candidate.v2"`; never use `schema` in place of `schema_version`. Include:

- `runtime: grok`, `stage: P3`, `status: candidate_pending_external_acceptance`, mode `fulltext_synthesis`, exact `skills: [method-harvest, business-lit-review]`, `generation_started_at`, `frozen_at`, `candidate_receipt_created_at`, and Grok tag;
- a top-level JSON key named `fixed_corpus` whose value is an object containing `closed: true`, `paper_count: 3`, and ordered `paper_ids` matching the table; do not flatten these three fields into the candidate-receipt root and do not rename the `fixed_corpus` object;
- each original verified input and isolated snapshot path, bytes, pages, hash, identity/verifier result, and copy lineage;
- canonical repository-relative `candidate_root: <repo_candidate_root>`, the generation-record path/bytes/hash, the generation record's exact `frozen_artifacts` inventory, and identical `bundle_digest`;
- the `inputs/isolation-preparation.json` path/bytes/hash as `isolation_preparation`;
- an embedded `synthesis` object using the exact field `"schema_version": "aris.business-e2e.literature-synthesis.v2"`, the exact current v2 input/output contract, `fulltext_manifest` path/bytes/hash, all three isolated PDF/processing/card inputs (each with the exact six-field `artifact_identity`), all five output roles, and its required checks including `artifact_identity_chain_joined: true`. This object remains candidate evidence and must not claim external acceptance;
- explicit completeness booleans for source identity, no blank required fields, variable construction/unknowns, unit/dependence, factor/index, questionnaire, numeric, mediation, null/mixed findings, disagreement diagnosis, source locations, and claim ceiling;
- `repository_tests_read_or_run: false`, `external_acceptance_pending: true`, `prior_codex_synthesis_reused: false`, `browser_or_mcp_used: false`, and `network_acquisition_performed: false`.

Every artifact-reference `path` in the candidate receipt and embedded synthesis must be canonical repository-relative and start with `<repo_candidate_root>/`. This includes `generation_record`, `isolation_preparation`, `fulltext_manifest`, every `pdf`, `pdf_processing`, `method_card`, and every output. Bare candidate-relative paths such as `inputs/...`, `qa/...`, `literature-v2/...`, or `artifacts/...` are invalid. An artifact reference always contains exact `path`, lowercase 64-hex `sha256`, and integer `size_bytes`; each `pdf` reference additionally contains integer `pages` and `detected_format: pdf`.

The embedded `synthesis` object must use this machine shape (values and hashes come from the new bundle, not from any old output):

```text
schema_version: aris.business-e2e.literature-synthesis.v2
status: candidate
contract:
  name: p3-fulltext-to-literature-review
  version: 2
  paper_count: 3
  required_nonempty_method_card_fields: [fulltext_status, local_path, content_hash, size_bytes, pages, source_depth, pdf_processing_receipt, work_id, artifact_id, parent_artifact_id, artifact_role, version_identity, doi_or_source_id, unit_of_observation, response_n, unique_entity_n, estimand_unit, cluster_unit, scale_provenance_status, numeric_audit_status, safe_claim, unsafe_claim]
  required_output_roles: [method_card_index, evidence_matrix, literature_review, acceptance_report, pdf_visual_checks]
fulltext_manifest: <canonical artifact reference>
inputs: exactly three objects, in fixed-corpus order, each with:
  paper_id
  artifact_identity: {work_id, artifact_id, parent_artifact_id, artifact_role, version_identity, doi_or_source_id}
  expected_render_pages: <sorted exact viewer_page list in that PDF-processing receipt>
  pdf: <canonical artifact reference plus pages and detected_format>
  pdf_processing: <canonical artifact reference>
  method_card: <canonical artifact reference>
  expected_fields: {source_depth: fulltext, numeric_audit_status: <exact nonblank card value>}
outputs: an object, never a list, with exactly these role keys:
  method_card_index: <artifact reference to METHOD_CARD_INDEX.md>
  evidence_matrix: <artifact reference to LITERATURE_EVIDENCE_MATRIX.md>
  literature_review: <artifact reference to BUSINESS_LIT_REVIEW.md>
  acceptance_report: <artifact reference to ACCEPTANCE_REPORT.md>
  pdf_visual_checks: <artifact reference to PDF_VISUAL_CHECKS.md>
checks:
  identity_matched_fulltext_only: true
  artifact_identity_chain_joined: true
  all_paper_hashes_recorded: true
  pdf_processing_ready: true
  pdf_source_preserved: true
  exact_variable_construction_or_unknown: true
  main_null_and_mixed_results_preserved: true
  source_locations_present: true
  agreement_conflict_diagnosed: true
  claim_ceiling_preserved: true
  abstract_only_method_claims: false
```

Before writing the generation record, perform a local structural self-check without opening repository tests or the root verifier: reject any `schema` key where `schema_version` is required; reject any artifact path not beginning `<repo_candidate_root>/`; reject a non-object `synthesis.outputs`; reject output-role keys other than the exact five above; reject a PDF reference without `pages`; reject top-level directories outside the declared topology; and reject any `.pyc` or `__pycache__`. This self-check is generation hygiene, not external acceptance, and must not claim the candidate passed repository tests.

## External acceptance handoff

Do not create a passed runtime-invocation wrapper and do not run the root verifier. Return the frozen candidate root and candidate-receipt path to the root Codex runner. The root runner will run `scripts/accept_p3_grok_candidate.py --candidate <candidate-receipt>` outside this invocation. That runner independently re-hashes the complete frozen inventory, runs the candidate mode of the general verifier and the real bundle test with JUnit evidence, re-hashes after testing, and creates an independent external-acceptance receipt. Only if every gate passes may it create a passed `aris.business-e2e.runtime-invocation.v1` wrapper bound to the candidate, generation record, verifier report, bundle-test report, and external acceptance receipt. The root verifier re-runs the candidate contract from those bindings; an ordinary list of hashed files is not Grok P3 runtime proof. The aggregate Grok P3 stage also remains incomplete until its separate SSRN, ScienceDirect, and Wiley browser gates pass.

## Failure rule

If a PDF identity/hash fails, a required field is blank, a source conflict is hidden, or a narrative claim lacks a pointer, write only a redacted non-wrapper failure record with the exact last verified state and blocker. Do not create a passed `aris.business-e2e.runtime-invocation.v1` wrapper, do not claim P3 synthesis pass, and do not fill the gap from an old Codex synthesis artifact.
