# Variable Resolution (CNRDS / CSMAR)

Companion to `cn-data-bridge`. Use this document to map research concepts to platform tables and fields before any download.

## Goal

Close **named gaps** with the smallest correct extract. Resolution is complete when each gap has either:

- a high-confidence platform mapping ready for `DOWNLOAD_SPEC`, or
- a single user decision among competing definitions, or
- an explicit blocker (`access`, `not_in_source`, `needs_manual_code`)

## Inputs To Resolution

1. Research name and role (outcome, treatment, control, instrument, moderator, sample filter)
2. Unit of observation (firm-year, firm-day, stock-day, person-year, event, …)
3. Universe (A-share, ChiNext, STAR, financials include/exclude, ST handling, listed-only, …)
4. Time window and fiscal vs calendar convention
5. Preferred source hints in `DATA_PLAN.md` (CNRDS vs CSMAR vs either)
6. Local files already covering the gap

## Gap Inventory Template

Write or update a short inventory (in the pull summary, log, or `Data/downloads/GAP_INVENTORY.md` when useful):

```markdown
# Gap Inventory

| gap_id | research_name | role | unit | years | universe | preferred_source | local_path | status |
|---|---|---|---|---|---|---|---|---|
| g1 | | | | | | cnrds \| csmar \| either | | open \| satisfied \| partial \| blocked |
```

Status meanings:

| status | Meaning |
|---|---|
| `open` | Needs resolution and/or download |
| `satisfied` | Local extract already sufficient |
| `partial` | Some years/fields present; remainder open |
| `blocked` | Access or definition pending |

Only `open` and `partial` gaps enter the download queue.

## Resolution Procedure

### 1. Normalize The Research Concept

Rewrite the concept as an operational definition before searching portals:

- **What is measured?** (e.g. net income / average total assets)
- **At what grain?** (firm-year vs firm-quarter)
- **Which entities?** (listed A-share non-financials, …)
- **Which restatement policy?** (latest available, as-reported, …) when known

If the design already freezes a formula in `RESEARCH_DESIGN.md` or `DATA_PLAN.md`, that freeze wins over portal defaults.

### 2. Search Candidate Modules

On the **user's** CNRDS/CSMAR access (browser or IP session):

1. Search by Chinese and English labels used in the field (e.g. 总资产收益率 / ROA)
2. Prefer official firm fundamental, governance, market trading, and event modules over obscure mirrors
3. Record **module → table/dataset → field code → field label → unit → frequency**
4. Prefer fields that match grain and universe without heavy post-hoc aggregation when the design allows

Do not download whole modules while exploring. Catalog candidates in notes first.

### 3. Score Confidence

| confidence | Criteria | Next action |
|---|---|---|
| **high** | Single mainstream field/table matches grain, unit, and design formula; naming is unambiguous | Write `DOWNLOAD_SPEC` and execute |
| **medium** | Two+ fields could work; differences are documented and design-relevant | Ask user **once** (see below) |
| **low** | Label collision, wrong grain, or unclear construction | Pause; propose alternatives; no download |
| **none** | Not found on CNRDS/CSMAR | Mark `source_gap`; do not invent coverage |

High confidence examples (illustrative — always verify on the live portal for the account’s subscription):

- Stock code + trading date from a standard daily quote table when the design needs firm-day returns
- Balance-sheet total assets from a standard annual consolidated statement table when grain is firm-year

Medium confidence examples:

- ROA pre-computed by vendor vs self-constructed NI/AT
- Ownership concentration: largest shareholder % vs top-10 sum
- SOE indicator: different control-chain or ultimate-controller rules across tables

### 4. Multi-Definition Policy: Ask Once

When several definitions are plausible:

1. Collect **all** conflicts for the current gap batch
2. Ask the user **one** decision message covering the whole batch
3. Freeze answers into `DOWNLOAD_SPEC` → Variable Map and MANIFEST → Definition Decisions
4. Do not re-prompt field-by-field unless the user changes the research design

Decision table format:

```markdown
# Variable Definition Decisions Needed

| gap_id | research_name | option_A (source/table/field) | option_B | difference | recommendation | default_if_no_reply |
|---|---|---|---|---|---|---|
| g1 | ROA | CSMAR precomputed ROA | Construct NI/AT from FS tables | vendor formula vs design formula | B if design states formula | A (document vendor definition) |
```

If the user is unavailable and the task must progress only with high-confidence items, **download only high-confidence gaps** and leave medium/low as `blocked` with the decision table attached. Do not silently pick a contested definition.

### 5. Cross-Source Choice (CNRDS vs CSMAR)

When either source could supply the variable:

| Prefer | When |
|---|---|
| Source already used in the project | Continuity of codes, units, and prior extracts |
| Source named in `DATA_PLAN.md` | Design freeze |
| Higher definition match | Even if the other portal is more familiar |
| Easier access path | e.g. CSMAR IP works today but CNRDS login is expired — only for **equivalent** definitions |

Record the choice and reason in the download notes. Do not dual-download the same concept from both sources unless the design needs a validation comparison (then create two gap_ids).

### 6. Keys And Merge Hygiene

Resolution is incomplete until merge keys are named:

| Grain | Typical keys (verify labels on portal) |
|---|---|
| Firm-year | stock code / firm id + year (or report period) |
| Firm-quarter | stock code + year + quarter / report period |
| Firm-day / stock-day | stock code + trade date |
| Person-firm-year | person id + firm id + year |

Note exchange suffixes, leading zeros, and code changes (IPO, reverse merger) as **post-download** analysis concerns; raw extracts should keep vendor codes intact.

### 7. Filters Belong In The Spec

Push filters into the portal query when the UI allows:

- year or date range
- market board / list status if available
- statement type (consolidated vs parent) when the design requires it
- industry sample only if the portal filter matches the design industry scheme

If the portal cannot filter safely, download the minimal superset and document analysis-side filters in the spec notes — still avoid whole-module dumps.

## Mapping Record Shape

Every resolved gap should be representable as:

```text
gap_id:
research_name:
role:
unit:
source: cnrds | csmar
module_or_db:
table_or_dataset:
fields:
  - code:
    label:
    transform: as_is | rename_only | construct:<formula>
definition_note:
keys:
filters:
years:
confidence: high | medium | low
decision: n/a | pending | user:<choice>
download: yes | no | deferred
```

High confidence + `download: yes` → include in `DOWNLOAD_SPEC`.

## Construction Variables

When the research variable is a **construct** (e.g. abnormal accrual, custom leverage):

1. Resolve each **ingredient** field as its own gap or sub-item
2. Do not treat the construct name as a single portal field unless a validated vendor field matches the design
3. Land ingredients as raw extracts; build the construct in analysis scripts (`data-analysis-bridge` / R / Stata)
4. Record the formula in `DATA_PLAN.md` / `DOWNLOAD_SPEC` notes so the analysis stage does not re-guess

## Anti-Patterns

- Bulk-downloading an entire CSMAR/CNRDS product line “in case we need it”
- Picking the first search hit without checking grain or statement type
- Quietly switching from design formula to vendor precomputed field
- Asking the user separately for every ambiguous control variable
- Mapping CNKI paper PDFs as data extracts
- Zero-filling missing accounting items at download time
- Storing portal cookies or passwords next to the mapping table

## Minimal Worked Sketch

Design needs: firm-year ROA, 2010–2023, A-share non-financials; also board independence.

1. Inventory → `g_roa`, `g_indep`
2. Resolve ROA → two candidates (vendor ROA vs NI/AT) → **medium** → include in one-shot decision table
3. Resolve board independence → single governance field matches grain → **high**
4. User picks construct ROA from FS fields
5. `DOWNLOAD_SPEC` includes FS fields for NI and AT plus governance independence field; years 2010–2023
6. Execute minimal exports to `Data/raw/csmar/<date>/` (or CNRDS paths as chosen)
7. MANIFEST rows + passport materials update; ROA construction left to analysis
