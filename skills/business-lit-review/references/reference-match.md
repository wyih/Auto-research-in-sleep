# Passage-Specific Reference Matching

Use for a request to find supporting references for a manuscript sentence, paragraph, theory argument, or contribution passage. Read [shared claim matching](../../shared-references/business-claim-source-audit.md#literature-claim-matching) for claim decomposition, citation roles, evidence checks, and verdicts. For checking an existing citation without a search request, use `business-claim-source-audit`.

## Context And Scope

Preserve the exact target text and its manuscript location. Read available surrounding paragraphs or relevant manuscript sections to establish the research question, constructs, population, setting, and intended citation use. Ask only for missing context that would change the match; otherwise use the supplied material.

Create a compact claim map with stable claim IDs, the assertion needing support, claim type, intended citation role, and material terms or scope that must be preserved. Reuse manuscript/audit claim IDs when available. A user-specified candidate set or library-only task bounds the search; inspect those sources without adding papers solely to fill a count.

## Search From The Claims

Follow [source policy](source-policy.md), starting with the user's library and existing project evidence. Reuse verified method cards or source notes when they cover the exact claim and version. Choose external routes by field: SSRN is useful for accounting/finance, NBER and RePEc for relevant economics claims, and broad indexes plus field journals/publishers for management and other business fields.

Search each relationship, mechanism, definition, or contribution claim separately. Translate concepts into the literature's terminology and use mechanism synonyms, foundational theory, or adjacent fields when they address the unresolved assertion. Include queries without a directional verb to find null or opposite results, and search competing explanations when the passage needs literature dialogue.

Expand promising seeds through references and later citations using available discovery providers. Read the relevant citing text before assigning a support or contrast role. Supplement broad discovery with targeted searches of strong relevant journals and recent publisher results. Keep compact notes linking queries/seeds to claim IDs and remaining gaps; distinguish retrieved records, distinct studies screened, and source sections actually read when reporting recorded counts.

## Verify The Citation Use

Apply the shared matching rules to each claim-paper pair. Resolve promising working papers against author/publisher records and verify the exact version to be cited under the source policy. Evidence may be a traceable official abstract when it explicitly supports the assertion; samples, variable construction, identification, detailed results, and mechanism tests require the relevant fulltext sections or tables.

When those sections are missing, use `fulltext-acquire`. Use `method-harvest` for a focused extraction only when the match needs method/result detail. Full method cards, synthesis matrices, manifests, and project passports are required only by an actual downstream contract, not by a standalone reference match.

Record citation role, verification verdict, and source depth separately. Evidence notes must identify the version read and its page, section, table, or abstract URL. Keep access-pending candidates separate from usable references. An inaccessible candidate is an access gap; a failed semantic match is a reason to change the citation use or reject that pairing.

## Select And Finish

Apply the user's hard journal conditions to final recommendations. Compare evidence fit and traceability first, then quality preferences among eligible matches. Follow the source policy for ranking sources, editions, and alternative versus joint conditions.

If an important claim remains unsupported, change the query family and follow promising leads. Finish when the requested claims have adequate verified support and plausible alternatives have been compared. If useful accessible routes for an unresolved claim are exhausted, or required evidence remains blocked after checking available alternatives, report the supported claims and that specific gap. Track completion per claim so one blocked source does not end useful work on other claims. Reference matching has no minimum candidate or recommendation count.

Return the [reference-match output](output-template.md#reference-match-output). Preserve original bibliographic titles and explain matches in the user's language. For an English manuscript or a request for citation wording, give concise usable sentences whose scope and causal/mechanism language match the evidence. Identify any proposed narrowing of the user's sentence; do not silently change its meaning or rewrite surrounding prose.

Workflow concepts adapted from [econ-reference-matcher](https://github.com/mimaowang/econ-reference-matcher), with shared audit verdicts and existing acquisition/extraction routes.
