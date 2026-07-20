# Business Run Passport

`BUSINESS_RUN_PASSPORT.md` is the project spine for business, accounting, finance, management, and economics papers. It records what materials exist, what stage is active, and which gates passed.

## Data Access Level

Use one value for each material:

- `raw`: raw data, source PDFs, downloaded archives, or private material
- `redacted`: data or text with sensitive fields removed
- `verified_only`: derived facts, tables, audit verdicts, and citation metadata safe for writing

Audit and reviewer-style skills should prefer `verified_only` when raw data is unnecessary.

## Run State Contract

Use one project-level state:

- `active` — work can proceed.
- `waiting_external_gate` — a known next step awaits a temporary dependency; use `waiting_browser_turn` when the browser grant, lease, or serialized turn is pending. This is never terminal.
- `blocked_source` — an actually attempted source has an evidenced gap. This is non-terminal while a permitted material alternative remains untested.
- `design_killed` — a named design failed its kill test; do not automatically kill the broader research question.
- `terminal_stop` — decisive evidence defeats the core question, all indispensable permitted sources or defensible design paths have been exhausted, or the user explicitly stops.
- `complete` — the requested evidence chain is complete.

Never infer `terminal_stop` from a missing browser grant, queued profile, pending user checkpoint, unattempted source, sample preview, search result, or incomplete public proxy. If a STOP report says the project can resume merely by receiving a browser turn and running an unattempted source, record `waiting_external_gate` instead.

## Template

~~~markdown
# Business Run Passport

## Project Identity
| Field | Value |
|---|---|
| Project | |
| Research Area | |
| Target Journals | |
| Current Stage | |
| Overall State | active / waiting_external_gate / blocked_source / design_killed / terminal_stop / complete |
| Waiting On | |
| Owner Decision Needed | |

## Materials
| Material | Path Or Source | Data Access Level | Status | Notes |
|---|---|---|---|---|

## Data And Analysis
| Field | Value |
|---|---|
| Data Sources | |
| Sample Period | |
| Unit Of Analysis | |
| Analysis Backend | R / Stata / Python / mixed |
| Main Scripts | |
| Main Outputs | |

## Acquisition Status
| Source Or Target | Producer Skill | Runtime Adapter | Manifest Or Receipt | Status | Blocking Gap |
|---|---|---|---|---|---|

## Artifact Index
| Artifact | Path | Producer Skill | Last Verified | Status |
|---|---|---|---|---|

## Decision Log
| Date | Decision | Evidence | Owner |
|---|---|---|---|

## Audit Status
| Gate | Artifact | Verdict | Blocking Issues |
|---|---|---|---|
| Novelty | BUSINESS_NOVELTY_CHECK.md | pending | |
| Fulltext / Method | FULLTEXT_MANIFEST.md / METHOD_CARD_INDEX.md | pending | |
| Design | RESEARCH_DESIGN.md | pending | |
| Data Acquisition | DATA_MANIFEST.md | pending | |
| Results Word | RESULTS_DOCX_MANIFEST.md | pending | |
| Numbers | BUSINESS_NUMBER_AUDIT.md | pending | |
| Source Claims | SOURCE_CLAIM_AUDIT.md | pending | |

## Repro Lock
```yaml
repro_lock:
  schema_version: 1
  generated_at:
  skills:
  model:
  source_material_hash:
  data_outputs_hash:
  analysis_backend:
  run_id:
```
~~~

## Update Rules

- Create the passport at project intake when none exists.
- Update `Artifact Index` after each skill writes a deliverable.
- Update `Acquisition Status` from actual fulltext/data manifests and redacted browser receipts; never from portal reachability alone.
- Update `Audit Status` only from actual audit artifacts.
- Keep unresolved issues visible until they are resolved, reframed, or dropped by the user.
- Keep `waiting_external_gate` and `blocked_source` non-terminal. Do not mark the project complete merely because a precise gap or STOP file exists.
- Record `terminal_stop` only after applying the pipeline's terminal criteria and distinguishing attempted from unattempted sources and designs.
