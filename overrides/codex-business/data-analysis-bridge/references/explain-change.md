# Explain An Empirical Analysis Change

Use for a revision whose effect on samples, estimates, or paper claims needs explanation. Work from the code and outputs; verify earlier descriptions against those artifacts.

## Establish The Comparison

- Honor the supplied commits, range, files, or saved runs. Record the endpoints and whether either is an uncommitted working tree. A request about the latest commit means its parent versus that commit.
- With no specified comparison, use `git diff HEAD --` for the net tracked change, including staged and unstaged edits. Inspect `git status --short --untracked-files=all`; relevant untracked scripts and outputs are additions to read explicitly. An empty tracked diff alone does not mean there is no change.
- With a supplied base ref, compare it to the working tree, including relevant untracked files. For an explicit commit-to-commit range, use those endpoints and exclude unrelated working-tree edits. Do not silently assume a `main` branch.
- Without Git, compare the supplied before/after files or runs. If there is only one version, explain the current implementation and identify the missing baseline; do not invent a change history.
- Read changed blocks in their enclosing scripts and follow affected upstream variable construction and downstream output consumers. Use `git show` or a separate scratch checkout for older files, preserving the active checkout and existing results.

## Trace The Empirical Consequences

Follow code change -> sample/variable construction -> estimation -> table/figure -> manuscript claim. Explain the research meaning of the changed filters, merges, transformations, timing, fixed effects, clustering, and weights that are actually involved.

Compare corresponding outputs from both runs:

- observation unit, period, and sample restrictions; sample sizes after affected filters and merges; entity/cluster counts and, where available, estimation-sample IDs
- changed variable definitions, units, missingness, and treatment/event-time coding
- the same model and coefficient: estimate, standard error or interval, estimation N, and relevant economic magnitude
- affected tables, figures, and claims, separating an added analysis from a changed existing result

Equal N can hide different observations. Equal displayed coefficients can hide rounding or changes in uncertainty. Match models and measurement definitions before comparing, use unrounded outputs when available, and limit a finding of agreement to what was actually compared. A changed estimand must be identified before interpreting a coefficient difference.

Read the output or log supplying each quoted number and check that it belongs to the stated run. A code diff alone supports an expected effect, not a measured result change. Distinguish numerical changes from timestamps, formatting, and figure re-rendering. When previous outputs are missing or stale, mark that comparison unverified; use a bounded rerun when it is within the requested scope and can preserve existing results.

## Deliver And Finish

Lead with which results changed, which checked results agreed, and what remains unverified. Give the reason in empirical terms, then a compact before/after comparison with source paths and the affected code locations. Attribute a change to a particular edit only when the evidence isolates it; otherwise identify the remaining candidate causes.

Use a direct answer or existing analysis notes by default. An offline HTML explanation and comprehension questions are optional when requested or useful for a requested handoff; neither is required to complete the explanation. Finish when the selected change and its decision-relevant consequences are accounted for.

Adapted from the ideas in Claes Bäckman's [explain-diff](https://github.com/claesbackman/AI-research-feedback/tree/main/Skills/explain-diff), with project-native outputs and optional presentation formats.
