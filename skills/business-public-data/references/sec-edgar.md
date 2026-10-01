# SEC EDGAR extracts

Use the [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) and [developer resources](https://www.sec.gov/about/developer-resources). Read the current access rules when implementing a pull. Send an identifying User-Agent with the user's actual research contact; obtain that contact if it is missing. Credentials and private contact details stay out of shared logs.

## Identity and history

- Resolve ticker/name to CIK and retain CIK as the issuer key. Keep the mapping source and its applicable dates when joining historical panels.
- The submissions endpoint is `https://data.sec.gov/submissions/CIK{10-digit-CIK}.json`. Recent filings are only part of the history; inspect the `files` entries and retrieve the historical submissions needed for the requested window.
- Retain form, accession number, filing date, report period, primary document, and acceptance timestamp when available. Use SEC-provided accession/document fields to form archive URLs.
- Distinguish fiscal period, filing/acceptance date, and the underlying event date. Choose the relevant timestamp and trading-day alignment from the research design.
- Keep amendments and original filings distinguishable. Define whether the study uses originally available information or subsequently amended information.

## XBRL facts

The company-facts endpoint is `https://data.sec.gov/api/xbrl/companyfacts/CIK{10-digit-CIK}.json`.

For each selected fact retain taxonomy, tag, unit, value, start/end, fiscal year/period, form, filing date, and accession where returned. A tag may contain overlapping annual and quarterly durations and repeated observations from later filings. Select by the intended duration and information date; verify consequential values against the corresponding filing.

Before computing ratios, align the accounting period, currency, scale, and consolidation scope of the inputs. Specify the numerator and denominator tags and formula. Inspect custom tags and coverage when the requested construct is not consistently represented by standard tags. Company-facts coverage and vendor-normalized Compustat definitions require reconciliation when combined.

## Forms 3/4/5

Keep issuer and reporting-owner identifiers, transaction date, filing date, security type, transaction code, acquired/disposed indicator, shares, price, direct/indirect ownership, derivative/non-derivative status, and amendment status as relevant. Separate open-market purchases/sales from grants, exercises, gifts, and other transaction types using the form's documented codes.

For a research panel, specify which transaction classes and owner roles count, how amendments are reconciled, and whether missing prices prevent constructing trade value. Use the established WRDS panel when that is the design's data source.

## Pull discipline

At review on 2026-09-30, the SEC's published ceiling is 10 requests per second per user across machines; use a lower shared rate and recheck the current policy for a new implementation. Respect server backoff instructions, reuse downloaded artifacts, and stop repeated requests when the provider denies access. Record an attempted source failure with its actual response.

Inspect a saved filing's company, form, accession, period, section heading, and a relevant fact before declaring it usable. A successful HTTP response may still contain an error page or the wrong document.
