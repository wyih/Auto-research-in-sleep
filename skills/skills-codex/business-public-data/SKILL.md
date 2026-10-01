---
name: business-public-data
description: Acquire and verify SEC EDGAR filings, XBRL facts, insider transactions, or official macroeconomic series for accounting and finance research. Use for public-source extracts, series definitions, release vintages, and reproducible data collection.
---

# Business Public Data

Turn the requested firms, indicators, and time window into locally saved extracts with documented definitions and coverage. Reuse the project's language, data plan, caches, and available connectors. Official APIs are sufficient when no connector is configured.

## Choose the source

- SEC filings, XBRL, 8-K events, and Forms 3/4/5: read [SEC EDGAR](references/sec-edgar.md).
- FRED/ALFRED, World Bank, or another official statistical provider: read [macro series](references/macro-series.md).
- Compustat/CRSP research panels and their established links: use `wrds-query-bridge`.
- CSMAR/CNRDS research tables: use `cn-data-bridge`.

Under Kimi Code, use `kimi-datasource` when its live schema covers the source; record its receipt using the project's existing contract. Otherwise use an available connector or the provider's documented API. Read current endpoint documentation before coding unfamiliar calls. Retrieve parameter names from that source's documentation.

## Acquire and verify

1. Establish observation unit, required fields, identifiers, date window, and information availability at the research date. Infer these from supplied materials; ask only for a missing choice that changes the extract.
2. Inspect a representative response before bulk acquisition. Check entity identity, units, dates, source coverage, and whether the result contains the intended data.
3. Save raw responses or filing artifacts and a runnable query script. Keep normalization and panel construction separate from the source files. Fetch all required pages/history and record any incomplete coverage.
4. Inspect saved files for expected type, schema, time coverage, duplicates, and missingness. Report `partial` when a requested entity, period, page, or field is still missing.
5. Record source URLs, query parameters excluding credentials, retrieval time, local paths, row counts, identifiers, and consequential transformations in the existing data manifest or analysis notes. Include release/vintage information when it changes the study's information set.

Completion means the requested extract is saved and checked, with its definitions and material coverage gaps documented. Route text-variable construction to `business-text-measures` and estimation to `data-analysis-bridge` when requested. When combining sources, reconcile their measurement definitions, periods, and accounting scope.

Adaptation credits: [Barrios sources](../shared-references/business-source-attribution.md).
