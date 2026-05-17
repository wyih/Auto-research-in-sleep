---
name: business-novelty-check
description: Check novelty for business, accounting, finance, management, and economics research ideas against published papers, working papers, SSRN, NBER, RePEc, journal pages, and closely related constructs. Use before committing to a business research question or paper framing.
---

# Business Novelty Check

Idea or draft: $ARGUMENTS

## Purpose

Assess whether a business-school research idea has a credible contribution after accounting for journal articles, working papers, title variants, and overlapping constructs.

## Workflow

### Step 1: Parse the Idea

Extract:

- research question
- proposed mechanism
- setting and sample
- treatment or key independent variable
- outcome variables
- identification strategy
- target field and journal conversation

### Step 2: Search Close Substitutes

Search exact and near-exact combinations:

- treatment + outcome
- setting + construct
- data source + method
- mechanism + journal field
- author/title variants from SSRN and NBER

Use `business-lit-review` for broad discovery when the nearby literature is unclear.

### Step 3: Classify Overlap

For each close paper, classify:

- `same_question_same_design`
- `same_question_different_design`
- `same_setting_different_question`
- `same_construct_different_outcome`
- `same_mechanism_different_context`
- `adjacent_only`

### Step 4: Decide Novelty

Return one verdict:

- `clear`: a meaningful contribution remains
- `narrow`: contribution exists but must be framed tightly
- `crowded`: several close papers force a design or theory pivot
- `blocked`: a close paper already makes the central claim
- `uncertain`: metadata or access gaps require manual verification

## Output

Use:

```markdown
# Business Novelty Check

## Verdict

## Closest Papers
| Paper | Status | Overlap Type | What It Already Does | Remaining Delta |

## Safe Framing

## Risky Framing to Avoid

## Search Gaps

## Recommended Next Step
```

## Rules

- Include working papers in the novelty judgment.
- Treat same authors with changed titles as the same project until evidence says otherwise.
- Distinguish setting novelty from theoretical novelty.
- Preserve uncertainty when full PDFs or appendices are inaccessible.
- Recommend a pivot when the remaining delta is a footnote.
