# Confident Prose, Honest Limits (Business Line)

The anti-defensive-writing contract for the business suite. It tracks the
`CONFIDENT PROSE, HONEST LIMITS` block in `skills/paper-write/SKILL.md`
(upstream ARIS #423/#424). `tests/test_confident_prose_sync.py` watches that
upstream block and fails when it changes — re-sync this file at that point
instead of letting the business line drift stale.

Tone edits under this contract never upgrade claims.

## The contract

1. Calibrate each claim to the evidence's actual scope and modality, then
   state that calibrated claim directly. Necessary assumptions, uncertainty,
   and scope are part of the claim; stacked hedges and defensive
   throat-clearing are not.
2. If the current claim is unsupported, narrow it to a version the evidence
   supports or cut it. Do not substitute a softer-sounding synonym for fixing
   scope, modality, comparison, or aggregation.
3. Put generic caveats and broader boundary discussion in one place — the
   limitations discussion (in business papers, the limits paragraph of the
   Conclusion). Outside it, remove generic disclaimers such as "further
   research is needed", "may not generalize", and "should be interpreted with
   caution". Claim-defining scope, assumptions, and statistical qualifications
   stay attached to the claims they make true.
4. State 2-4 material, specific limitations (sample window, data source,
   identification assumption). Real ones only — never invent one to meet a
   count, never apologize generically, never repeat the same limitation
   through the paper.
5. Writing instructions are not manuscript content. "Do not mention X" means
   omit X, not write "we do not address/claim/discuss X". Never expose
   drafting instructions, requested omissions, reviewer feedback, or revision
   history in manuscript prose.
6. Replace self-defence ("we do not claim", "our goal is merely") with a
   positive, evidence-matched statement of what the paper does establish. If
   the defensive sentence carries a real boundary, keep that boundary in the
   claim or in the limitations discussion; do not delete truth-conditional
   content.
7. Tone-only edits never alter facts, negation, modality, scope, assumptions,
   comparison direction, aggregation, numbers, formulas, or citations. Genuine
   overclaims must still be narrowed; supported claims wrapped in redundant
   caution must be stated directly. Calibrating tone must not hide null or
   mixed findings.
8. One argument spine: gap -> question -> design -> evidence -> implication.
   Every section advances it. Front-load the contribution; never narrate the
   drafting or revision process.

## Scan items for review passes

Flag these wherever they appear outside the limitations discussion:

- stacked hedges and defensive throat-clearing;
- per-paragraph generic caveats ("further research is needed" scattering);
- self-defence phrasing ("we do not claim", "our goal is merely");
- reviewer-facing prebuttals that apologize for the sample, setting, or design;
- contribution-by-relabeling — renaming a limitation as a contribution.
