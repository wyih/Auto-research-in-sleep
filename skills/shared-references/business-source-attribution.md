# Source attribution for the Barrios adaptation

Reviewed source: [Barrios88/barrios-skills](https://github.com/Barrios88/barrios-skills/tree/d50afc62f4c67535a1949d029dfa0462feb906fd), commit `d50afc62f4c67535a1949d029dfa0462feb906fd`, reviewed 2026-09-30 and rechecked 2026-10-02.

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

## Retained MIT notice

MIT License

Copyright (c) 2026 John Barrios
Copyright (c) 2026 Lu Han

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
