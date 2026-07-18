# Task Plan: Business Research End-to-End Acceptance

## Goal

Deliver a production-ready business empirical-research workflow on current `main` that passes real acceptance in both Codex (native Chrome control) and Grok (Chrome MCP), including fulltext acquisition, method extraction, WRDS R/SAS acquisition, CSMAR/CNRDS portal export, analysis output, and dual-platform installation/routing.

## Current Phase

Phase 7 — Grok acceptance and final release validation, paused at the user's request after a checkpoint commit. Shared outputs and the complete Codex P1–P5 path pass the root verifier; only the explicit Grok synthesis/P4 gates and final post-completion validation remain.

## Current Verifier Snapshot

`python3 scripts/verify_business_e2e.py --run-id 20260718T011517Z --json` currently reports:

- Shared: P1 `PASS`, P2 `PASS`, P3 `PASS`, P5 `PASS`.
- Codex: overall `PASS`; P1–P5 `PASS`; CNKI, SSRN, ScienceDirect, Wiley, CNRDS, and CSMAR browser gates all `PASS`.
- Grok: P1, P2, and P5 `PASS`; the official-DevTools CNKI, SSRN, ScienceDirect, and Wiley PDF/download gates all `PASS`. The canonical P3 synthesis receipt remains incomplete, and CNRDS/CSMAR P4 exports remain incomplete.
- No browser or runtime gate is running. The CNRDS run and blind P3 worker were explicitly stopped for this checkpoint.

## Phases

### Phase 1: Recover and Audit Existing Work

- [x] Confirm user intent and create a persistent Goal.
- [x] Start from current `main` on `codex/business-research-e2e`.
- [x] Inventory Grok worktree changes without modifying that worktree.
- [x] Separate reusable work from stale or platform-coupled work.
- [x] Define explicit acceptance matrix for Codex and Grok.
- **Status:** completed

### Phase 2: Shared Workflow and Platform Adapters

- [x] Define platform-neutral browser-session capability contract.
- [x] Implement Codex adapter guidance using `chrome:control-chrome`.
- [x] Implement Grok adapter guidance using `chrome-mcp`.
- [x] Define download, human-login/captcha handoff, and manifest contracts.
- [x] Add checks preventing hard-coded incompatible tool calls in canonical workflows.
- **Status:** completed

### Phase 3: P3 Fulltext and Method Pipeline

- [x] Port/refactor fulltext acquisition and site recipes.
- [x] Validate local/OA baseline.
- [x] Validate CNKI search → detail → PDF → local verification in Codex.
- [x] Validate the same CNKI case in Grok through `chrome-mcp`.
- [x] Validate SSRN passive challenge → paper → verified PDF in Codex.
- [x] Validate ScienceDirect challenge/institutional path → viewer download → verified PDF.
- [x] Validate Wiley article → PDF → local verification in Codex.
- [x] Verify Zotero linkage/attachment semantics and METHOD_CARD generation without mutating the Zotero library.
- [x] Validate verified PDFs → enriched METHOD_CARDs → cross-paper evidence matrix → source-grounded literature review.
- [x] Harden P3 v2 acceptance around PDF-inspection receipts, native/OCR routing, visual source-page checks, structured Markdown fields, hashes, and PDF lineage.
- **Status:** completed — shared pipeline and Codex acceptance; independent Grok P3 evidence is tracked only in Phase 7

### Phase 4: P1 and P4 Data Acquisition

- [x] Port and verify WRDS R/Postgres, inline universe, CCM, IBES, and CIK fallback.
- [x] Run a real WRDS SAS Cloud handoff end to end.
- [x] Implement CSMAR/CNRDS portal recipes on the shared browser-session contract.
- [x] Export and verify one minimal CSMAR and one minimal CNRDS dataset in Codex under the available subscription access.
- [x] Record immutable raw files, hashes, schemas, filters, and transport/access facts.
- **Status:** completed — P1 shared/Codex and P4 Codex; independent Grok CNRDS/CSMAR exports are tracked only in Phase 7

### Phase 5: P2 Analysis-to-Word

- [x] Port/refactor `results-to-docx` into an executable generator.
- [x] Verify tidy coefficients, statistics, figures, and academic table rendering.
- [x] Normalize and inspect OOXML identity metadata as `Yihong Wang`.
- [x] Render and visually inspect the Word output.
- [x] Carry a real WRDS extract through a separate engineering analysis smoke into a verified DOCX without claiming causal or economic inference.
- **Status:** completed — shared output and Codex invocation; independent Grok invocation is tracked only in Phase 7

### Phase 6: P5 Routing and Installation

- [x] Update canonical business-suite routing.
- [x] Provide project installation for Codex and Grok without manually maintained divergent skill bodies.
- [x] Confirm `grok inspect` discovers the intended 24 portable business skills in the isolated acceptance workspace.
- [x] Confirm Codex discovers the intended 24 portable business skills.
- [x] Verify the 24-skill/9-shared-reference portable mirror, inventory, validators, installer, and isolated discovery receipts.
- **Status:** completed — current acceptance receipt for both runtimes; the final post-change mirror/full-suite run is tracked only in Phase 7

### Phase 7: End-to-End Acceptance and Delivery

- [x] Run and root-verify the representative P1–P5 slice through Codex.
- [x] Verify Grok P5 discovery and the independent Grok CNKI browser gate.
- [x] Produce an independent Grok canonical-skill invocation receipt for P1, including a new real R/Postgres run and new SAS Cloud job.
- [x] Produce an independent Grok canonical-skill invocation receipt for P2.
- [x] Establish and restart-test a visible dedicated persistent Chrome profile for the official Grok DevTools MCP.
- [x] Verify one ScienceDirect checkbox bootstrap persists across full Chrome restart and a second article.
- [x] Install and validate the restricted official DevTools MCP facade; Grok doctor, live transport, fill/commit continuity, and download checks pass with exactly 15 safe tools.
- [ ] Produce an independent Grok canonical-skill invocation receipt for P3.
- [x] Produce independent Grok browser/download receipts for CNKI, SSRN, ScienceDirect, and Wiley.
- [ ] Produce independent Grok browser/export receipts for CNRDS and CSMAR.
- [x] Synchronize and check the canonical→Codex mirror for the pause checkpoint.
- [ ] Re-run the final mirror check, full relevant suite, and root verifier after all remaining Grok receipts land.
- [ ] Complete final-release diff review and evidence-backed handoff after Grok acceptance. (A non-final checkpoint commit/push is being made now.)
- **Status:** paused by user; no Grok gate is claimed as currently running

## Remaining Questions

1. Can the restricted official DevTools facade complete CNRDS/CSMAR without exposing raw URLs/values or weakening download proof?
2. Can the next blind Grok P3 synthesis rerun close the remaining Duan method-card fields and pass the post-generation external verifier?
3. After those receipts land, do the final mirror check, full relevant suite, root verifier, and diff review all pass cleanly enough for final release?

## Decisions Made

| Decision | Rationale |
|---|---|
| Develop on a new branch from current `main` | The Grok worktree is 296 main commits behind and contains uncommitted work; preserving it avoids destructive reconciliation. |
| Keep one canonical business workflow plus thin Codex/Grok adapters | Site and research logic should not drift merely because browser tool names differ. |
| Treat real artifacts as acceptance evidence | Homepage reachability, prose protocols, and clicks without verified downloads do not prove the workflow. |
| Split development installation from release packaging | Both runtimes must discover in-development skills early enough for real testing. |
| Use a visible dedicated persistent profile as Grok's primary protected-site path and ordinary Chrome only as explicit fallback | The official profile now preserves ScienceDirect clearance across restart while offering a maintained automation surface; adapter identity and evidence must remain separate. |
| Keep shared artifacts separate from runtime proof | A verified shared PDF/DOCX/review may be consumed by both runtimes, but only a runtime's own invocation or browser receipt proves that runtime passed. |
| Treat P3 `unknown`/`fail` audit values as valid evidence states | Literature processing acceptance requires faithful extraction and claim ceilings, not silently repairing incomplete or inconsistent papers. |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| GitNexus index unavailable in both worktrees | 1 | Use source inspection and direct tests; do not create an index unless later justified. |
| Computer Use cannot inspect iTerm2 | 1 | Read Grok's persisted session records and project state instead. |
| System Python has no pytest module | 1 | Use `uv run --with pytest pytest ...` for pytest-based acceptance suites; stdlib unittest suites continue under `python3`. |
| Raw `browser` MCP could not launch visible Chrome from Grok's workspace sandbox | 1 | Run a separately managed dedicated-profile Chrome on a loopback CDP port and direct-connect through the restricted facade while keeping Grok sandboxed. |
| Official browser prompt/acceptor artifact schema drift | 1 | Freeze one candidate schema and add `sha256`/`mtime_ns` to the facade copy result before any real candidate is accepted. |

## Notes

- Never expose credentials, cookies, proxy authentication, or API keys in logs or Markdown.
- Existing worktree `/Users/wyih/Projects/ARIS-business-skills` remains read-only continuity evidence unless the user explicitly redirects implementation there.
- Existing-session ordinary login buttons and site challenges may be operated under the user's explicit authorization. New credential entry, MFA/QR/SMS, purchases, or irreversible actions require a focused handoff.
- The only remaining work is the Phase 7 checklist above; do not reopen completed Codex gates unless a later change invalidates their hashes or tests.
