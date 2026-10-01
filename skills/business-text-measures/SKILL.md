---
name: business-text-measures
description: Construct and validate research measures from annual reports, disclosure sections, earnings calls, or policy text. Use for financial tone, uncertainty, disclosure content, stance, dictionary measures, FinBERT, or LLM-assisted coding in accounting and finance studies.
---

# Business Text Measures

Produce a documented text measure at the study's observation unit, preserving the link from each score to source text. Reuse the requested measure definition and existing implementation when supported.

## Define the construct

Establish the economic construct, the role of the measure as X/Y/control/mechanism, document language, source section, scoring unit, information date, and aggregation rule. Financial polarity, uncertainty, disclosure specificity, and policy stance require different labels and validation evidence.

Acquire missing filings through `business-public-data`; use existing authorized transcript or annual-report sources for other text. `empirical-design-plan` owns the research design and causal interpretation.

## Build the measure

1. Preserve document ID, issuer ID, period, filing/publication date, section, and source path. Separate prepared remarks from Q&A and document sections when the construct depends on that distinction.
2. Inspect extraction quality. Remove navigation, repeated headers, and tables only according to the intended measure; retain negation, numerals, speaker attribution, and economically meaningful wording. Document treatment of amendments, duplicated text, and boilerplate.
3. Select a dictionary, domain classifier, or a coding model based on the construct and language. Read [model and validation choices](references/models-and-validation.md) when choosing or changing a scorer.
4. Keep sentence/chunk scores with source IDs. Use explicit segmentation and coverage rules for long documents; record excluded or truncated text. Define overlap handling before aggregating chunks.
5. Validate on representative labeled material before relying on the score as the intended construct. Separate threshold/model tuning from final validation; record the observed error patterns and consequences for the research claim.
6. Aggregate using a stated denominator and weights. Distinguish an absent/missing section from an observed section with a zero score. Validate firm-period merge keys and information dates before joining to financial data.

## Output and completion

Keep runnable extraction/scoring code, a score dataset, and concise measure notes in the existing analysis layout. Notes should identify model/dictionary version, prompt and label definitions when applicable, cleaning/segmentation rules, aggregation formula, validation evidence, and material coverage gaps.

Completion means the requested measure is constructed and its validation status is reported. A scored dataset with weak construct validation supports only the narrower interpretation established by the labels and checks. Route regression execution through `data-analysis-bridge` when requested.

Adaptation credits: [Barrios sources](../shared-references/business-source-attribution.md).
