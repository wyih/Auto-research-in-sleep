# Source attribution for business research adaptations

## Barrios skills

Reviewed source: [Barrios88/barrios-skills](https://github.com/Barrios88/barrios-skills/tree/d50afc62f4c67535a1949d029dfa0462feb906fd), commit `d50afc62f4c67535a1949d029dfa0462feb906fd`, reviewed 2026-09-30 and rechecked 2026-10-02.

Update review on 2026-11-02: [commit 680c983](https://github.com/Barrios88/barrios-skills/tree/680c98370381593141bf1d39da4353354958e2f0). Additional adaptations cover source-fidelity checks, comparable numerical quantities, independently fixable review findings, and table-cell reading rules from `econ-referee`/`paper-pdf`. The suite retains its existing local PDF inspector and presentation tools.

The suite selectively adapts research workflow guidance, with rewritten instructions for its existing contracts:

- `business-public-data`: `sec-edgar` and `api-data-fetcher`.
- `business-text-measures`: `financial-text-nlp`.
- `business-research-talk`: `econ-slides` and its exhibit/discussant references.
- Empirical diagnostics and Python/figure guidance: `r-econometrics`, `stata-data-cleaning`, `pyfixest`, `python-panel-data`, `econ-visualization`, and the identification guidance in `econ-write`/`econ-writing-plus`.
- Empirical prose guidance: `econ-write`, its identification reference, and `econ-writing-plus`.
- Optional manuscript-wide economics writing framework: `econ-write`, including the Cochrane, McCloskey, and Shapiro writing tradition collected by Lu Han. The adapted reference covers structure, sections, prose, exhibits, and revision; it does not reproduce the authors' books or attribute every rule to all three.
- Meaning-preserving academic prose editing: `econ-humanizer` and `econ-humanizer-plus`, with conflicting punctuation rules resolved through the user's style and manuscript voice.
- Field-specific prereview and contribution/evidence comparisons: `econ-referee` and the `econ-write` review checklist, integrated into the existing prereview skill.

Barrios's `econ-write` and `econ-slides` credit [Lu Han's econ-writing-skill](https://github.com/hanlulong/econ-writing-skill) and [econ-slides-skill](https://github.com/hanlulong/econ-slides-skill), respectively, under the MIT license. Other listed materials are credited to the Barrios collection and their named contributors in the source. No upstream MCP implementation, model weights, or general library manual is bundled by this adaptation.

Both original repositories were independently checked on 2026-11-02: writing at `f2bf7a22c5e3b37921a5e6c73bd1fb380a5e00e8`, slides at `4ac998bfa98bc0b59d4d1776b4ced565b34b802c`. Their latest commits remain dated July 2026. The updated Barrios referee guidance also credits [Ingar30/reviewer](https://github.com/Ingar30/reviewer), inspected at `e6ae89dbab1aa642392d813caebcce197844edff`; this adaptation uses rewritten evidence principles rather than its reviewer runtime.

## Reference matching

Reviewed source: [mimaowang/econ-reference-matcher](https://github.com/mimaowang/econ-reference-matcher/tree/84678b07922e09e96e26666aac33bba1c4a7b399), commit `84678b07922e09e96e26666aac33bba1c4a7b399`, reviewed 2026-10-03.

Rechecked on 2026-11-02 at `7fd344d7586a4ca6bebaa8bff8367f318d000935`. Changes from the absorbed version affect GitHub Actions only; the matching workflow is unchanged.

The suite adapts passage-level claim decomposition, citation roles, source-version verification, and journal-filter handling into `business-lit-review`'s `reference_match` mode and the shared claim-source audit rules. The instructions are rewritten around the suite's existing discovery, fulltext, method-harvest, and audit contracts. The upstream helper scripts and benchmark fixtures are not bundled.

## Empirical feedback and explorable presentations

Reviewed source: [claesbackman/AI-research-feedback](https://github.com/claesbackman/AI-research-feedback/tree/4c1aef514cf4aa520937131a54830b4af0e403db), checked 2026-11-02. The suite already adapts `audit-analysis` and `explain-diff`; those directories are unchanged relative to the source state preceding the suite's September 2026 integration.

The requested explorable-presentation branch adapts progressive explanation, source-traceable exhibits, shared data across reveals, editable PowerPoint elements, and readable static handouts from `explorable-deck`, `explorable-beamer`, and `explorable-pptx`. It uses the suite's existing presentation engineering tools and does not bundle the upstream templates or impose their visual theme.

## Referenced dependencies

The ARIS update references [HERO-Anti-OverDefense](https://github.com/wanshuiyin/HERO-Anti-OverDefense/tree/92686ca5c7dc9f4852cd323e2852219b7e86a8ea) for writing guidance and the optional Goal Pulse lifecycle. Goal Pulse starts only after an actual user-requested Goal exists, following the installed skill's host contract. It is not part of ordinary research routing.

[HonestDiD](https://github.com/asheshrambachan/HonestDiD/tree/6813f02ed38f0b63bdca6915604b2eac90491303) is a referenced analysis library, not bundled skill code. Its latest commit was checked on 2026-11-02 and remains dated April 2026. Analysis dependencies remain governed by each empirical project's environment.

## Retained MIT notice

MIT License

Copyright (c) 2026 John Barrios
Copyright (c) 2026 Lu Han
Copyright (c) 2026 econ-reference-matcher contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
