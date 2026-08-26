---
name: business-research-pipeline
description: Complete end-to-end business, accounting, finance, management, and economics research workflow for Codex or Kimi Code CLI. Use when the user wants one entry point that routes literature review, verified fulltext and method synthesis, idea and novelty, empirical design, WRDS, kimi-datasource, or CSMAR/CNRDS acquisition, analysis, evidence audits, paper planning, writing, rebuttal, or resubmission, regardless of which model is selected in the host CLI.
---

# Business Research Pipeline

Research direction: $ARGUMENTS

## Purpose

Orchestrate a business-school research lifecycle while reusing ARIS artifact discipline.

## Default Mode: Current Stage

When the request names a stage, artifact, or local problem, load only the current stage skill and the minimum existing artifacts needed for that stage. Stop at the next checkpoint with produced output, missing inputs, and the next recommended skill.

## Full Pipeline Mode

Run the whole chain only when the user explicitly asks for a full pipeline, end-to-end run, or all stages. In full-pipeline mode, advance stage by stage and keep later-stage references unloaded until their stage begins.

## Lightest-Sufficient Source Escalation

Use the cheapest sufficient channel and escalate only when the unresolved evidence requires it:

1. project-local verified artifacts, manifests, caches, and checked-in scripts
2. model-native web search/fetch, when available, for public discovery, official documentation, literature metadata, public filings, and openly downloadable data
3. a bounded public API or direct HTTP helper when it yields a reproducible public artifact. Under Kimi Code CLI the preferred bounded API is the `kimi-datasource` plugin (`mcp__plugin-kimi-datasource_data__get_data_source_desc` → `mcp__plugin-kimi-datasource_data__call_data_source_tool`): `wind`/`stock_finance_data` for A-share/HK quotes and financials, `sp_data`/`sec_edgar`/`yahoo_finance` for US fundamentals and filings, `china_nbs`/`china_nda`/`fred`/`imf`/`world_bank_open_data` for macro, `tianyancha` for Chinese corporate registry, `china_standards`/`yuandian_law` for standards and law, `arxiv`/`scholar` for literature metadata, `xhcj`/`caixin` for financial news. It does not cover WRDS, CSMAR/CNRDS research tables, CNKI or publisher fulltext
4. an authenticated browser only for a remaining login/session-bound page, protected portal schema, interactive query/export, challenge, or entitled download

Do not acquire a browser turn for public discovery that model-native web search/fetch can complete. Before queuing protected work, record the exact unresolved item and a `browser_required_reason` accepted by `browser-session-bridge`. Public search can identify candidates and open alternatives; it cannot prove the user's current subscription, the live authenticated table state, or a protected export.

## Shared Contracts

Read these references when the stage touches them:

- `../shared-references/business-run-passport.md` for the Business Run Passport
- `../shared-references/business-handoff-schemas.md` for stage artifact schemas
- `../shared-references/business-repro-lock.md` for final artifact reproducibility records
- `../shared-references/business-feasibility-gates.md` before any frozen gate, high-cost acquisition, or STOP decision

## Pipeline

```text
business-run-passport
  -> business-lit-review
     -> fulltext-acquire when a required PDF is missing
     -> method-harvest for design-relevant papers
     -> business-lit-review fulltext_synthesis from verified method cards
  -> business-idea-creator
  -> business-novelty-check
  -> empirical-design-plan
     -> feasibility-and-gate calibration before frozen gates or expensive acquisition
     -> wrds-query-bridge for WRDS (R/Postgres default)
        -> wrds-sas-cloud only after a recorded escalation or explicit SAS request
     -> cn-data-bridge for CSMAR/CNRDS gaps
  -> data-analysis-bridge
     -> r-analysis-bridge when R is the backend
     -> stata-analysis-bridge when Stata or .dta is the backend
     -> results-to-docx for a standalone academic results document
  -> evidence-to-claim
     -> business-number-audit before submission-ready writing
     -> business-claim-source-audit before submission-ready writing
  -> business-paper-plan
     -> business-author-style-profile when writing samples or target-journal style are available
  -> business-paper-writing
```

Use `business-rebuttal` after reviews arrive. Use `resubmit-pipeline` for text-only cross-venue resubmission of an already polished paper.

## Stages

### Stage 0: Business Run Passport

Run `business-run-passport`.

Output:

- `BUSINESS_RUN_PASSPORT.md`
- data access level map
- artifact index
- audit gate dashboard

### Stage 1: Literature and Positioning

Run `business-lit-review`.

Output:

- `BUSINESS_LIT_REVIEW.md`
- closest-paper delta
- journal conversation map

### Stage 2: Fulltext and Method Evidence

For papers whose methods, measures, data, or identification affect the design, run `fulltext-acquire` until each target has either an identity-matched verified PDF or a precise access gap. Then run `method-harvest` only on verified local PDFs.

Output:

- `literature/fulltext/FULLTEXT_MANIFEST.md`
- protected-session browser receipts when applicable
- `method-harvest/cards/*_METHOD_CARD.md`
- `method-harvest/METHOD_CARD_INDEX.md` for multiple papers
- `LITERATURE_EVIDENCE_MATRIX.md`
- updated source-grounded `BUSINESS_LIT_REVIEW.md`

This stage cannot pass from abstracts, metadata, a visible PDF viewer, or an unverified download click.
After cards exist, re-enter `business-lit-review` in `fulltext_synthesis` mode. Stage 2 is incomplete when the pipeline has only per-paper cards but no cross-paper comparison of constructs, variable calculations, designs, findings, boundaries, and claim ceilings.

### Stage 3: Idea Generation

Run `business-idea-creator`.

Output:

- `idea-stage/BUSINESS_IDEA_REPORT.md`
- top research question and data path

### Stage 4: Novelty Check

Run `business-novelty-check` on the top idea.

Output:

- novelty verdict
- risky framing to avoid
- closest working papers

### Stage 5: Empirical Design

Run `empirical-design-plan`. Its Phase 0 routes the first-level method via `business-method-routing.md`; archival designs (including quasi-natural experiments and textual analysis) continue through the standard stages, and case-study ideas use its case-study branch. Methods without a dedicated suite path (field research, design science, normative) are recorded as explicit gaps, not forced into the archival template.

Output:

- `empirical-design/RESEARCH_DESIGN.md`
- `empirical-design/DATA_PLAN.md`
- `empirical-design/TABLE_SHELLS.md`
- `empirical-design/ROBUSTNESS_PLAN.md`
- `empirical-design/FEASIBILITY_AND_GATE_CALIBRATION.md`
- `empirical-design/CASE_PROTOCOL.md` when Phase 0 routes to case study

### Stage 5.5: Feasibility And Gate Calibration

Before bulk collection, protected/high-cost exports, or a frozen go/no-go contract:

1. benchmark sample size, treatment support, clusters/events, match coverage, attrition, and precision against verified closest studies;
2. freeze a claim ladder from flagship through scoped and descriptive contributions;
3. run a representative end-to-end pilot across easy, typical, and difficult cases;
4. classify gates as validity-hard, design-hard, quality targets, or aspirational;
5. compute passed, terminal-no-go, recoverable, external-waiting, and best-case attainable counts;
6. authorize only bounded QA and acquisition that can change the decision.

Do not proceed when the named branch is already mathematically unable to pass. Scope down or stop that branch before production. Do not treat failure of one branch as project `terminal_stop` while a defensible claim tier remains.

### Stage 6: Data Acquisition

Resolve every required source in `empirical-design/DATA_PLAN.md` before estimation:

- Run `wrds-query-bridge` for WRDS. Use its R/Postgres path by default.
- Run `wrds-sas-cloud` only when the R path has a recorded timeout, OOM, hard failure, authentication blocker after retries, or the user explicitly requires SAS.
- Under Kimi Code CLI, resolve covered data needs through the `kimi-datasource` plugin before escalating to an authenticated browser: Chinese macro and provincial series via `china_nbs`, global macro via `fred`/`imf`/`world_bank_open_data`, A-share/HK financials and intraday series via `wind`, US filings and fundamentals via `sec_edgar`/`sp_data`, Chinese corporate registry via `tianyancha`, financial news and announcements via `xhcj`/`caixin`. Parameter names come from the live `get_data_source_desc` documentation of each source — never infer them across sources (`china_nbs` takes `filepath`, `wind` takes `file_path`). Independent desc/call pairs for different data sources may be issued in parallel; do not re-fetch a desc already read in the same session, and keep a one-line list of descs already read in `DATA_PLAN.md` or `DATA_MANIFEST.md`. Record one datasource receipt per call (`data_source_name`, `api_name`, verbatim `params`, landed CSV path, hash, request id, and `field_mapping` for localized returned columns) per `DATASOURCE_RECEIPT.json` in `../shared-references/business-handoff-schemas.md`, and link it from `DATA_MANIFEST.md`. `kimi-datasource` does not replace WRDS, CSMAR/CNRDS portal exports, or paywalled fulltext; keep those on their existing routes.
- Run `cn-data-bridge` for minimal CSMAR/CNRDS exports. Route protected portal actions through `browser-session-bridge` and the host CLI's native browser control (Codex native Chrome plugin under Codex, Kimi WebBridge under Kimi Code CLI). Keep browser mutations serialized against the user's browser profile; parallelize public search and local analysis instead.
- Case-study primary evidence (interviews, field notes, internal documents) does not route through WRDS, `kimi-datasource`, or `cn-data-bridge`; it lands as project-managed files under the case protocol's evidence-chain rules. Use the bridges only for supplementary archival evidence the design names.

Output:

- immutable or rebuildable landed extracts
- query/program/filter records
- file hashes and schema/row checks
- `data/**/DATA_MANIFEST.md` or the project's established `Data/**` equivalent
- separate browser receipts for each protected runtime acceptance run

A login page, portal preview, successful query submission, or download toast is not a landed-data pass.

### Stage 7: Data Analysis and Results Packaging

Run `data-analysis-bridge` when data or a working dataset exists.

Output:

- analysis scripts
- regression tables
- `analysis/output/RESULTS_SUMMARY.md`

When the project uses R, `.R`, `.Rmd`, `.qmd`, `.rds`, tidyverse, or `fixest`, route execution through `r-analysis-bridge`. When the project uses Stata, `.dta` files, or `.do` files, route execution through `stata-analysis-bridge`.

When a standalone academic Word artifact is requested or required by the acceptance run, export tidy coefficient/descriptive inputs and run `results-to-docx`. Keep the Word output separate from the manuscript, normalize OOXML identity metadata to the current user's explicitly configured Office author, render it, and inspect the rendered pages. Never inherit a maintainer identity from the distributed Skill.

### Stage 8: Evidence Gate

Run `evidence-to-claim`. Run `business-number-audit` once manuscript prose or numeric result text exists. Run `business-claim-source-audit` once the draft contains literature claims, institutional claims, or citation-supported prose.

Output:

- `CLAIMS_FROM_EVIDENCE.md`
- `BUSINESS_NUMBER_AUDIT.md` when paper text exists
- `SOURCE_CLAIM_AUDIT.md` when citation or source-supported claims exist
- safe claim language
- missing evidence list

### Stage 9: Paper Plan and Writing

Run `business-paper-plan`. Run `business-author-style-profile` when the user provides prior writing samples, advisor examples, or target journal exemplars. Then run `business-paper-writing`.

Output:

- `BUSINESS_PAPER_PLAN.md`
- `AUTHOR_STYLE_PROFILE.md` when style calibration is used
- manuscript sections or full `paper/` directory

## Checkpoints

Pause for user decision after:

- top idea selection
- novelty verdict
- empirical design before coding
- feasibility and gate calibration before a frozen contract or high-cost acquisition
- data acquisition plan before protected or high-cost exports
- evidence-to-claim verdict
- source-claim audit verdict when the draft is source-heavy
- paper plan before full manuscript drafting

## Run-State And STOP Discipline

Use these project-level states; do not collapse them into a generic `blocked` or `STOP`:

| State | Terminal | Use |
|---|---|---|
| `active` | no | Work can proceed now. |
| `waiting_external_gate` | no | A known next action awaits a serialized browser turn, user checkpoint, one-time login/challenge, network switch, or another temporary dependency. Use subtype `waiting_browser_turn` for a missing browser grant or lease. Keep the Goal active. |
| `blocked_source` | no by default | An exact source was actually attempted and produced an evidenced access, coverage, or field gap. Continue permitted alternative-source discovery before considering project termination. |
| `design_killed` | only for that design | Evidence rejects a named design such as sharp RDD. Preserve the research question and test a pre-specified or defensible pivot unless the rejected design is indispensable to the core question. |
| `terminal_stop` | yes | The core research objective is infeasible under the terminal criteria below. |
| `complete` | yes | All required stages and acceptance evidence are complete. |

Apply these terminal criteria strictly:

1. Never use absence of `BROWSER_TURN_GRANTED.md`, a busy browser/profile, an unserved queue turn, or a pending user checkpoint as evidence for `terminal_stop`; record `waiting_external_gate` and keep the Goal active.
2. Never treat `source_not_attempted` as `source_failed`. Before a data-based STOP, actually test the recipe-approved source after the required gate is available and preserve its receipt or schema evidence.
3. A public proxy, sample preview, search suggestion, wrong-grain table, or incomplete field set may reject that proxy; it cannot prove that an untested protected source lacks the required data.
4. A failed kill test terminates only the design or claim it directly tests. Continue with a viable pivot unless the evidence also defeats the core research objective.
5. Use `terminal_stop` only when at least one of these is true: decisive appropriate-grain evidence defeats the core question; every permitted required source and material alternative has been attempted and cannot supply indispensable data; every defensible identification path fails its stated kill test; or the user explicitly chooses to stop.
6. A terminal report must distinguish attempted paths from unattempted paths, cite evidence for each decisive failure, state why remaining pivots cannot answer the core question, and contain no resume condition that is merely “obtain browser grant and run the unattempted source.” Such a resume condition proves the state is non-terminal.
7. Obey a project `GOAL_BRIEF.md` instruction to remain active at a serialized gate even when another completion clause permits an evidence-backed STOP.
8. Treat `not_evaluable`, `branch_stop`, `design_killed`, `scope_down`, and `terminal_stop` as different conclusions. A null p-value, source gap, quality target, or aspirational threshold cannot by itself trigger `terminal_stop`.

## Rules

- Keep ML/GPU workflows out of the path unless the project truly needs predictive modeling.
- Keep the Business Run Passport updated at stage boundaries.
- Route empirical execution through `data-analysis-bridge`.
- Route missing fulltext through `fulltext-acquire` and method extraction through `method-harvest`; never infer method fields from abstracts.
- Route WRDS through `wrds-query-bridge` first and record any `wrds-sas-cloud` escalation reason.
- Under Kimi Code CLI, route data needs covered by the `kimi-datasource` plugin through `mcp__plugin-kimi-datasource_data__*` before escalating to an authenticated browser; it does not cover WRDS, CSMAR/CNRDS portal exports, or paywalled fulltext.
- Route CSMAR/CNRDS through `cn-data-bridge`; its browser transport must come from `browser-session-bridge`.
- Browser UI is required for authenticated navigation, login-state reuse, and portal mutations that depend on the visible session. Checked-in helper scripts may orchestrate the selected bridge, wait for and copy downloads, hash files, inspect archives, and run deterministic semantic checks. Do not fail an otherwise valid stage merely because the same approved bridge calls were issued by a helper script instead of one-by-one model tool calls.
- Treat `results-to-docx` as a reproducible results package, not permission to overwrite a manuscript.
- Route claim interpretation through `evidence-to-claim`.
- Preserve ARIS audit discipline: source claims, table claims, citation claims, and reproducibility locks stay traceable.
- For local tasks, complete only the requested stage and mark downstream gaps as next-stage inputs.
- Treat a valid STOP as an evidence verdict, never as a convenient way to complete a Goal while a required next action is merely queued or unattempted.
- Require closest-study benchmark calibration and a representative feasibility preflight before freezing numerical gates. Freezing prevents ex-post manipulation; it does not validate an arbitrary threshold.
- Apply the QA relevance test from `business-feasibility-gates.md`; repeat artifact-integrity checks only after material mutation, at handoff, or at finalization.
- Lead checkpoint reports with the research decision in plain language and keep implementation jargon in linked evidence.

## Full-Pipeline Acceptance

The complete entry point passes only when a fresh session can discover this skill, route every requested stage through its named child skill, and leave independently checkable artifacts. Record each stage as `passed`, a precise non-terminal state, or a valid `terminal_stop`; a precise blocker makes reporting honest but does not by itself complete the full Goal. A project with frozen numerical gates must include `FEASIBILITY_AND_GATE_CALIBRATION.md`; a gate without external or analytical calibration is incomplete. Keep the Goal active when the next required action is waiting on a temporary gate. Never report `PASS with STOP`, `PASS (gap-documented)`, or another hybrid that marks an unmet required artifact as passed. Inherited logs, old files, browser toasts, and unverified clicks are not fresh acceptance evidence. For protected sources, verify the landed PDF or data slice by identity, structure or required columns, size, and hash before allowing downstream synthesis or analysis.
