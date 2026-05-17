# Business Run Passport

`BUSINESS_RUN_PASSPORT.md` is the project spine for business, accounting, finance, management, and economics papers. It records what materials exist, what stage is active, and which gates passed.

## Data Access Level

Use one value for each material:

- `raw`: raw data, source PDFs, downloaded archives, or private material
- `redacted`: data or text with sensitive fields removed
- `verified_only`: derived facts, tables, audit verdicts, and citation metadata safe for writing

Audit and reviewer-style skills should prefer `verified_only` when raw data is unnecessary.

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
| Design | RESEARCH_DESIGN.md | pending | |
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
- Update `Audit Status` only from actual audit artifacts.
- Keep unresolved issues visible until they are resolved, reframed, or dropped by the user.
