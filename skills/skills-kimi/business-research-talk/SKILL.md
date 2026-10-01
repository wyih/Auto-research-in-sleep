---
name: business-research-talk
description: Turn an accounting, finance, economics, or management paper into an author presentation, discussant deck, or timed speaker script. Use for seminars, conferences, thesis defenses, and adapting an existing research deck.
---

# Business Research Talk

Build the requested presentation around the paper's question, main finding, and evidence. Preserve an existing deck's style and authorial voice unless the user requests a redesign.

## Scope the presentation

Infer author presentation, neutral summary, or discussant role from the request. Use the supplied audience, format, and speaking allocation. Distinguish speaking time from a session that includes questions; make a modest explicit timing assumption when it is unspecified. Derive the slide count from the argument and timing, with detailed analyses in backup slides.

Use the available presentation/artifact skill for PPTX engineering and rendering when it is installed. For Beamer, retain the existing engine and macros; in Codex, use the native LaTeX editor/compiler for a supported standalone `.tex` document. Use an existing project compiler for a multi-file Beamer project. Verify compilation and rendered layout with available tools.

## Build the argument

1. Read the manuscript and key exhibits. Identify the research question, economic contribution, main result, data and design/model objects needed to understand it, and the supported scope of the conclusion.
2. Select the evidence that carries the argument. Record source page/table/column or output file for each displayed number, sample, definition, and consequential assumption in slide notes or source comments.
3. Give the answer early once its meaning is intelligible. Introduce the sample, outcome, treatment/exposure, and identification before detailed empirical results; introduce agents, timing, constraints, and assumptions before theoretical propositions.
4. Read [exhibits and discussion](references/exhibits-and-discussion.md) when reducing paper tables, adapting figures, or preparing a discussant deck. Give each slide one main job and preserve uncertainty, units, and sample context.
5. Inspect the rendered slides at presentation scale. Fix unreadable labels, dense tables, clipped content, and titles that no longer match their exhibits. Verify all displayed numbers and derived magnitudes against their sources.
6. If a speaker script is requested, align it with slide IDs and the actual speaking allocation. Scripts preserve the evidence strength and scope of the slide claims. Separate prepared speech from backup/Q&A material.

## Completion

Deliver the requested editable source/deck and a rendered preview or PDF when supported, plus any requested script. Report unresolved source conflicts, missing exhibits, or unverified rendering only when they affect usability. For `.pptx`, set document and comment/revision identity to the user's configured Office author and verify after final export.

Adaptation credits: [Barrios and Lu Han sources](../shared-references/business-source-attribution.md).
