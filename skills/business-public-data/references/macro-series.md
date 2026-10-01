# Official macroeconomic series

Select indicators by their definition and role in the design. Keep country/region codes, series IDs, units, frequency, seasonal adjustment, price basis/base year, source, and coverage with the observations.

## FRED and ALFRED

Use [series observations](https://fred.stlouisfed.org/docs/api/fred/series_observations.html), [series metadata](https://fred.stlouisfed.org/docs/api/fred/series.html), and [real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html).

- Read the API key from the user's environment or configured connector. Omit keys from stored query URLs and logs.
- Save `series_id`, observation dates, values, and returned real-time fields. Preserve FRED's missing-value marker as missing during numeric conversion.
- Choose revised/latest data for studies of realized outcomes when appropriate; choose a documented historical vintage for studies of decisions or forecasts using information available then.
- Record observation bounds and requested real-time bounds/vintage dates. An observation date and its publication date serve different purposes.
- Frequency conversion requires an economic rule: stocks commonly use an end-of-period value; flows may require a sum; rates may require an average. Record the actual choice, seasonal adjustment, and annualization. Inspect missing subperiods before aggregating.

## World Bank and other providers

Use the [World Bank API call documentation](https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures) and indicator metadata. A documented V2 pattern is `https://api.worldbank.org/v2/country/{country}/indicator/{indicator}?format=json&date={start}:{end}`. Inspect response pagination and retrieve the requested pages; retain missing country-year cells.

Country aggregates and individual economies must remain identifiable. Check whether an indicator is nominal/real, current/constant currency, total/per capita, or an index before combining it with another series. For IMF/OECD/BLS or Chinese official series, read that provider's current endpoint and code list rather than transferring another API's parameters.

## Panel handoff

Define a unique geography-period key, the transformation formula, and the information-date rule. Inspect join coverage and frequency alignment before attaching a series to firms or events. Preserve missing observations and report breaks, revisions, and incomplete coverage that change the interpretation.
