---
name: business-idea-creator
description: Generate and rank business, accounting, finance, management, and economics research ideas. Use when the user wants research questions, paper ideas, hypotheses, data-driven empirical opportunities, journal positioning, or a business-school adaptation of idea discovery.
---

# Business Idea Creator

Research direction: $ARGUMENTS

## Purpose

Turn a broad business-school research direction into feasible paper ideas with theory channels, data paths, and identification risks.

## Inputs

Read available context in this order:

1. `BUSINESS_LIT_REVIEW.md`
2. `research-wiki/`
3. `RESEARCH_BRIEF.md`
4. local notes, paper summaries, or user-provided constraints

If no context exists, derive from `$ARGUMENTS` and state the assumptions.

## Workflow

### Phase 1: Define the Research Space

Extract:

- field: accounting, finance, management, economics, information systems, or adjacent
- phenomenon and institutional setting
- candidate constructs
- likely data sources
- target journal family
- user constraints on data access, timeline, and methods

### Phase 2: Generate Candidate Ideas

Generate 8-12 ideas. Each idea must include:

- research question
- theory or mechanism
- hypothesis sketch
- unit of analysis
- data source candidates
- empirical design candidate
- closest literature
- likely contribution type

Contribution types:

- new construct or measure
- new setting
- new shock or institutional change
- sharper identification
- mechanism clarification
- reconciliation of mixed findings
- replication or boundary-condition paper
- theory extension

### Phase 3: Filter

Score each idea on:

- literature gap
- data feasibility
- identification plausibility
- construct validity
- journal fit
- execution cost
- referee risk

Eliminate ideas with no plausible data path, no clear theoretical delta, or a design that can only support claims weaker than the proposed contribution.

### Phase 4: Rank and Recommend

For the top 3-5 ideas, create:

- one-paragraph pitch
- closest-paper delta
- minimum viable dataset
- main specification
- first robustness tests
- strongest likely referee objection
- recommended next step

## Output

Write `idea-stage/BUSINESS_IDEA_REPORT.md` when writing is allowed.

Use this structure:

```markdown
# Business Idea Report

## Executive Recommendation

## Candidate Ideas
| Rank | Idea | Field | Data Path | Identification | Journal Fit | Risk |

## Top Idea Deep Dive
- Research question:
- Theory channel:
- Hypotheses:
- Data:
- Empirical design:
- Closest papers:
- Contribution:
- Referee risk:
- Next step:

## Rejected Ideas and Why
```

## Rules

- Prefer one strong, feasible paper over a broad agenda.
- Keep claim strength aligned with achievable evidence.
- Treat data access as a first-class constraint.
- Surface identification and measurement threats early.
- Avoid ML-style pilot language unless the idea truly involves predictive modeling.
