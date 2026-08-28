# Journal Referee Rubric (Pre-Submission Review)

Scoring dimensions for journal-mode pre-review. Score each 1–5 with an
evidence pointer; weighting is a guide, not arithmetic — a fatally weak
dimension caps the verdict regardless of the average.

## Dimensions

1. **Contribution and incremental novelty** (weight: high)
   - What is the marginal contribution over the nearest neighbors?
   - Check against the suite's novelty artifacts (`business-novelty-check`
     output, literature map), not the author's own framing. No novelty run
     on record → mark `EVIDENCE_GAP` and cap confidence.
   - Red flags: contribution claimed only by assertion; nearest neighbor
     does the same thing on a different sample without a stated reason why
     that is a contribution.

2. **Theory and hypothesis development** (weight: high)
   - Mechanism stated before prediction; constructs defined at the depth
     the method cards require.
   - Red flags: hypotheses restate correlations as theory; alternative
     explanations not acknowledged.

3. **Research design and identification** (weight: high)
   - Match the design contract in `RESEARCH_DESIGN.md`; check the Phase 0
     method route is honestly carried through (a case study scored as
     archival, or a DiD scored as an experiment, is a design error).
   - Red flags: identification claims above the claim ceiling; sample
     selection unexplained; endogeneity handled by assertion.

4. **Execution and robustness** (weight: medium-high)
   - Number-audit consistency, robustness coverage vs. the design's
     promised tests, measurement validity of key constructs.
   - Red flags: promised robustness missing; winsorization/clustering
     choices unjustified; table numbers not reproducible from outputs.

5. **Exposition and structure** (weight: medium)
   - Introduction earns its claims; tables readable without the text;
     figures carry information.
   - Red flags: abstract overclaims; introduction lacks a clear "what we
     find" paragraph; notation drift.

6. **Journal fit** (weight: gate)
   - Does the paper join the target journal's current conversation
     (recent 3–5 years)? Is the method/setting mix within the journal's
     published envelope?
   - Output a fit note even when positive; if fit fails, name 1–2 better
     venues and what would need to change.

## Recommendation Scale

- **ready to submit** — no P0; fit note positive
- **minor revision before submission** — no P0 in design/contribution; exposition or robustness gaps remain
- **major revision before submission** — P0 in design, execution, or contribution framing
- **not ready for this journal** — fatal design/contribution issue, or fit fails; say which and why

## Comment Shape

Major comment = issue → why it threatens the conclusion → what evidence
or analysis would resolve it. Minor comment = one line, actionable.
No summary-of-the-paper padding beyond the opening paragraph; no
scorekeeping adjectives ("interesting", "important") without evidence.
