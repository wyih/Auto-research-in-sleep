# Business Run Passport

## Project Identity
| Field | Value |
|---|---|
| Project | R Fama-French Industry Toy Project |
| Research Area | Finance; asset pricing; industry portfolio benchmark regressions |
| Target Journals | Teaching toy project, not a submission target |
| Current Stage | Completed toy pipeline |
| Owner Decision Needed | None |

## Materials
| Material | Path Or Source | Data Access Level | Status | Notes |
|---|---|---|---|---|
| Ken French factors | `F-F_Research_Data_Factors_CSV.zip` | raw | downloaded by script | Public Ken French Data Library |
| Ken French 10 industries | `10_Industry_Portfolios_CSV.zip` | raw | downloaded by script | Public Ken French Data Library |
| Research design | `empirical-design/RESEARCH_DESIGN.md` | verified_only | complete | CAPM benchmark design |
| R results | `analysis/output/RESULTS_SUMMARY.md` | verified_only | complete | Produced by `R/04_main_results.R` |
| Manuscript note | `paper/toy_results.md` | verified_only | complete | Short result narrative |

## Data And Analysis
| Field | Value |
|---|---|
| Data Sources | Ken French Data Library |
| Sample Period | 2010-01 to 2024-12 |
| Unit Of Analysis | industry-month |
| Analysis Backend | R |
| Main Scripts | `R/04_main_results.R` |
| Main Outputs | `tables/table_capm_by_industry.csv`, `analysis/output/RESULTS_SUMMARY.md`, `paper/toy_results.md` |

## Artifact Index
| Artifact | Path | Producer Skill | Last Verified | Status |
|---|---|---|---|---|
| Literature review | `BUSINESS_LIT_REVIEW.md` | business-lit-review | 2026-05-17 | complete |
| Idea report | `idea-stage/BUSINESS_IDEA_REPORT.md` | business-idea-creator | 2026-05-17 | complete |
| Novelty check | `BUSINESS_NOVELTY_CHECK.md` | business-novelty-check | 2026-05-17 | complete |
| Design | `empirical-design/RESEARCH_DESIGN.md` | empirical-design-plan | 2026-05-17 | complete |
| Results summary | `analysis/output/RESULTS_SUMMARY.md` | r-analysis-bridge | 2026-05-17 | complete |
| Evidence claims | `CLAIMS_FROM_EVIDENCE.md` | evidence-to-claim | 2026-05-17 | complete |
| Number audit | `BUSINESS_NUMBER_AUDIT.md` | business-number-audit | 2026-05-17 | PASS |
| Source claim audit | `SOURCE_CLAIM_AUDIT.md` | business-claim-source-audit | 2026-05-17 | PASS |
| Style profile | `AUTHOR_STYLE_PROFILE.md` | business-author-style-profile | 2026-05-17 | complete |
| Final report | `FINAL_ANALYSIS_RESULTS.md` | business-paper-writing | 2026-05-17 | complete |

## Decision Log
| Date | Decision | Evidence | Owner |
|---|---|---|---|
| 2026-05-17 | Use public Ken French data for a reproducible toy project | public source, R run, number audit | Codex |
| 2026-05-17 | Keep claims descriptive | `CLAIMS_FROM_EVIDENCE.md`, CAPM design | Codex |

## Audit Status
| Gate | Artifact | Verdict | Blocking Issues |
|---|---|---|---|
| Novelty | `BUSINESS_NOVELTY_CHECK.md` | teaching toy | none |
| Design | `empirical-design/RESEARCH_DESIGN.md` | PASS | none |
| Numbers | `BUSINESS_NUMBER_AUDIT.md` | PASS | none |
| Source Claims | `SOURCE_CLAIM_AUDIT.md` | PASS | none |

## Repro Lock
```yaml
repro_lock:
  schema_version: 1
  generated_at: "2026-05-17"
  artifact: "FINAL_ANALYSIS_RESULTS.md"
  producing_skill: "r-analysis-bridge + business-paper-writing"
  source_material_hash:
    analysis/output/RESULTS_SUMMARY.md: "sha256:17d4cbabffa7e6ca4f65a71355241983b9179e63d1676433bf90f8998a7aa233"
    paper/toy_results.md: "sha256:2f5ef8d726758910dcbb8d257aea8ed646b250e52ef5479ea181f0a5b2d6ae32"
  data_outputs_hash:
    tables/table_capm_by_industry.csv: "sha256:ff093b7d5c33b99f53128328e75bf09f0fa4a95427a5e42588fe7f10f056d09a"
  analysis_backend:
    name: "R"
    script: "R/04_main_results.R"
  limitations:
    - "Toy project uses public benchmark data and descriptive CAPM regressions."
```
