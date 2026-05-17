---
name: business-lit-review
description: Literature review for business, accounting, finance, management, economics, and empirical social-science papers. Use when the task is finding related work, building a literature map, checking journal positioning, surveying accounting or finance research, comparing working papers, or deciding where a business research idea fits.
---

# Business Lit Review

Research topic: $ARGUMENTS

## Purpose

Use this skill for business-school research where the unit of evaluation is a journal-style empirical or theory paper rather than an ML benchmark paper.

This skill is knowledge-base-first and journal-aware. Search the user's own library first, then working-paper sources, then journal and publisher sources, then broad web.

## References

Load only the reference needed for the current task:

- `references/source-policy.md` for source order and search rules.
- `references/venue-tiering.md` for accounting, finance, management, and economics venue tiers.
- `references/domain-taxonomy.md` for topic grouping and trigger boundaries.
- `references/output-template.md` for the default literature table and synthesis structure.

## Source Selection

Parse `$ARGUMENTS` for `— sources:`.

If omitted, search in this order:

1. Zotero, Obsidian, and local `papers/` or `literature/`
2. SSRN and NBER
3. RePEc, Google Scholar, Crossref, OpenAlex, Semantic Scholar
4. Publisher and journal pages
5. Broader web only for tracing papers already identified

Valid source values:

- `zotero`
- `obsidian`
- `local`
- `ssrn`
- `nber`
- `repec`
- `scholar`
- `openalex`
- `crossref`
- `publisher`
- `web`
- `all`

Interpret `all` as the full default source set.

## Workflow

### Step 0: Load Local Knowledge

Search local sources before web search.

Extract:

- title, authors, year, venue or working-paper source
- user annotations, notes, tags, and collections
- key question, setting, data, method, result, and limitation
- why the paper matters for this project

Treat user-owned notes and annotations as high-priority context.

### Step 1: Search Working Papers

Search SSRN and NBER early. Many accounting and finance ideas circulate as working papers for years before journal publication.

For each hit, capture:

- current version date
- earlier title variants when visible
- author institution
- abstract-level method and data
- journal publication status if known

Label source status as `published`, `forthcoming`, `working_paper`, or `preprint`.

### Step 2: Search Formal Literature

Use venue tiering from `references/venue-tiering.md`.

Prefer formal versions when a working paper and a journal article refer to the same work. Keep the working-paper link when it has newer appendices, data details, or an accessible PDF.

### Step 3: Build the Landscape

Group papers by research design and mechanism rather than search order.

Common grouping axes:

- theory channel
- institutional setting
- data source
- identification strategy
- construct or measure
- outcome family
- journal conversation

### Step 4: Diagnose the Gap

For each potential gap, state:

- what the closest paper already does
- what the user's project changes
- whether the gap is theoretical, empirical, data-driven, setting-driven, identification-driven, or measurement-driven
- what evidence would make the gap credible to a referee

## Output

Use the table and synthesis shape in `references/output-template.md`.

Always include:

1. top 8-15 closest papers
2. closest-paper delta table
3. venue-positioning note
4. unresolved search gaps
5. recommended next search or design action

## Rules

- Prefer journal and working-paper primary sources over tertiary summaries.
- Preserve working-paper status instead of smoothing it into publication status.
- Separate accounting, finance, management, and economics conversations when they use different constructs or referee standards.
- Flag duplicate title variants and author-version drift.
- Mark papers as `needs_verification` when metadata or claims are uncertain.
