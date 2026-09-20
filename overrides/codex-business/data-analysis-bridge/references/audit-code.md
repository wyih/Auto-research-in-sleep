# Independent Empirical Code Audit

Use to find correctness errors in empirical analysis, with priority determined by consequences for the sample, estimates, or conclusions. Scope the work to the requested changes or named analysis and its dependencies.

## Set Scope And Preserve Independence

For changed-code requests, establish endpoints and include relevant untracked files using the comparison guidance in [explain-change](explain-change.md). For a named script or table audit, a Git diff is not required. Read complete affected stages and trace variables outside the changed lines.

Use a fresh reviewer context following [reviewer independence](../../shared-references/reviewer-independence.md). Supply the question, comparison endpoints, original file paths, available data/log paths, and the checks below. The reviewer reads primary artifacts directly; do not pass the executor's explanations, preferred diagnosis, or prior verdict. Use available subagent tools without prescribing a fixed number of reviewers. If independent execution is unavailable, perform the useful local audit and explicitly identify it as a local review, not an independent one.

The reviewer reports findings without editing the production analysis. Small read-only diagnostics or isolated reproductions can resolve a concrete uncertainty. Reading data and running diagnostics must stay within the project's existing access and execution permissions.

## Check The Affected Empirical Flow

| Area | Questions that can change the research conclusion |
|---|---|
| Sample | What is the observation unit? How do N and entity/cluster counts change at filters, joins, reshapes, and aggregation? Do estimation-sample exclusions agree with the stated rules? Use logs or diagnostics for counts; mark missing counts unverified. |
| Merges | Are keys unique on the required side? Does join cardinality duplicate observations? How are unmatched rows handled? Are id-period pairs and the time validity of links preserved? |
| Variables | Do formulas match the construct, units, denominator, deflation, and logs/levels? Are lags grouped by entity and aligned to actual calendar periods, including gaps? Are treatment and event time consistent with the design? |
| Silent failures | Are missing values treated as zero without justification, numeric strings silently coerced, or rows dropped unnoticed? In Stata, inspect missing values satisfying `if x > 0` and destructive `destring, force`; in R/Python, inspect missing-value matching in joins, NA filtering, row-based lags, aggregation, and fill/coercion behavior as applicable. |
| Estimation | Do fixed effects, controls, weights, clustering level/count, and estimation N implement the specification? Inspect absorbed regressors, singleton drops, convergence, and omitted coefficients where relevant. |
| Outputs | Does the executed path generate the cited table from that model and sample? Do comments and manuscript descriptions agree with what runs? Could a stale output or an unused code block account for the apparent result? |

These are investigation questions, not automatic defects. A zero fill, unmatched row, or omitted regressor is a finding only when its actual behavior violates the stated design or changes the analysis incorrectly. Report supported defects without inventing a quota or treating style preferences as errors.

## Verify Findings And Finish

Each finding identifies the file and line, a short exact excerpt, the erroneous behavior and affected result, and its evidentiary status:

- `CONFIRMED`: source logic or a diagnostic establishes the defect. State separately whether its numerical impact has been measured.
- `NEEDS_VERIFICATION`: there is a specific unresolved factual premise, such as duplicate keys in data not available to the reviewer. Name the smallest check that resolves it.

Before presenting material findings, verify the cited code and relevant upstream/downstream behavior. Run the smallest diagnostic or counterexample needed to distinguish an actual defect from a false positive. Correct or dismiss a reviewer finding only with evidence; retain unresolved findings with their status. Drop unsupported allegations rather than passing them through unchanged.

Report findings in order of empirical consequence, then briefly state scope and any material unverified area. If no supported issue is found, say so for the inspected scope. Use existing analysis notes or an audit ledger when the project maintains one; a separate report is optional. Finish once the requested scope and material findings are checked. Apply repairs only when the user's task includes them, and verify the affected results after repair.

Adapted from the empirical checks in Claes Bäckman's [audit-analysis](https://github.com/claesbackman/AI-research-feedback/tree/main/Skills/audit-analysis), using the suite's reviewer-independence contract and evidence-based finding verification.
