# Business Method Routing

Classify a business research project into exactly one first-level research method before any design planning. Method choice follows the research question, available evidence access, and the conclusion the paper wants to make; method sophistication is not a selection criterion.

## The Seven First-Level Methods

| Primary criterion | Method | Do not misclassify as |
|---|---|---|
| Uses existing financial data, filings, announcements, regulatory records, transactions, text, or policy changes; the researcher does not manipulate the treatment | Archival research | Experiment |
| The researcher manipulates the independent variable or situation and observes decision or behavior consequences | Experiment | A quasi-natural study merely because it has "treatment/control groups" |
| Core constructs are attitudes, perceptions, preferences, beliefs, or self-reported information unavailable from archives | Survey | An experiment that only uses a questionnaire as a post-task measure |
| Research quality depends on the researcher's sustained, close presence inside an organization, interacting with members to understand practice | Field research | A case study based on a few interviews or a single organization |
| Answers "how/why" in a real-life context, around one or more bounded cases, explaining phenomenon and context through multiple sources of evidence | Case study | Field research judged by case count |
| Goal is to build and evaluate an artifact that solves a practical business problem: construct, model, method, framework, algorithm, prototype, or system instance | Design science | Normative discussion with only a conceptual proposal or architecture vision |
| Core task is to compare standards, rules, principles, or systems under stated goals and value premises and to reach a prescriptive conclusion | Normative research | Any paper without regressions, a pure concept piece, or a literature review |

## Boundary Rules

1. Quasi-natural experiments are archival research. When a policy, rule, or event splits units into treated and comparison groups but the researcher did not manipulate the treatment, the design is causal identification on archival data. DID, DDD, RDD, and IV may be used, but the paper is not a behavioral experiment; write "treatment group", not "experimental group".
2. Field research is not case study. Field research is identified by sustained close interaction with organizational members; case study is identified by a bounded case in a real-life context, an unclear phenomenon-context boundary, and multiple evidence sources. A single-case study need not be field research; a multi-organization study can be field research.
3. Textual analysis is archival research. When annual reports, disclosures, call transcripts, media, or social text are converted into variables that enter statistical tests, textual analysis is a data-construction route inside archival research. Dictionaries, supervised models, topic models, readability, and similarity are feature-extraction choices, not a paradigm.
4. Design science requires build-and-evaluate. A design-science paper identifies an important problem, states evaluable objectives, builds an artifact, demonstrates use, and evaluates utility, quality, or efficacy with appropriate evidence. A paper that only proposes a framework or path without building or evaluating is conceptual or normative support material.
5. Normative research is not "non-empirical research". Normative research is identified by goals, value judgments, and ends-means argumentation; it may use qualitative, quantitative, archival, survey, experimental, case, field, or formal evidence. Pure concept sorting, historical review, or literature survey without prescriptive argumentation is not normative research.

## Techniques Are Not Paradigms

DID, IV, RDD, PSM, event studies, panel models, and textual analysis are designs or techniques inside archival research, selected by question, data, and identification conditions. They are not parallel first-level paradigms, and choosing a more advanced technique never substitutes for fit.

## Suite Coverage By Method

- Archival: full chain — empirical-design-plan, wrds-query-bridge, cn-data-bridge, data-analysis-bridge, evidence-to-claim, audits, writing.
- Experiment and survey: design planning, analysis bridges, claim discipline, audits, and writing apply; acquisition routes through project-managed instruments, not WRDS/CSMAR.
- Case study: design planning through the case-study branch of `empirical-design-plan`; claim ceilings through the case-study levels of `evidence-to-claim`; evidence-chain audit through `business-claim-source-audit`; factual-numeric consistency through `business-number-audit`; WRDS/CSMAR bridges apply only to supplementary archival evidence.
- Field research, design science, normative: upstream stages (literature, idea, novelty, claim calibration, writing) apply unchanged; this suite has no dedicated design, acquisition, or analysis path yet — record the gap explicitly in `RESEARCH_DESIGN.md` instead of forcing the archival template.

## Case-Study Design Contract

Use when the question is how/why about a contemporary phenomenon in a real-life context, the phenomenon-context boundary is unclear, the researcher cannot control behavioral events, and explanation must rest on multiple evidence sources.

Required design elements (record all in `RESEARCH_DESIGN.md`):

- research question: explicit how/why, exploration, description, or explanation — not "introduce company X's transformation"
- case boundary: organization, program, event, or process, with time span and analytic level
- unit of analysis: organization, team, project, decision, event chain, or process; holistic vs embedded units stated
- theory role: test, extend, build, or describe; explanatory cases need theoretical propositions, exploratory cases need sensitizing concepts and observation focus
- case type: single or multiple; exploratory, descriptive, explanatory, or evaluative — chosen by the research question
- selection logic: typical, critical, extreme, revelatory, or longitudinal; multi-case selection follows replication logic (literal vs theoretical replication), not statistical sampling; successful cases require a survivor-bias note and, where possible, failure or contrast cases
- data sources: documents, archival records, interviews, direct or participant observation, physical or technical artifacts; each source reports purpose, access process, credibility, and limits
- analysis strategy: proposition-driven or descriptive-framework; pattern matching, explanation building, or time-series/process analysis; within-case analysis before cross-case comparison
- quality plan: construct validity (triangulation, evidence chain, informant review), internal validity (explanatory cases only), external validity (analytic generalization, never statistical representation), reliability (case protocol and case database)

Claim ceilings:

- Causal language is limited to within-case explanatory inference; rival explanations must be addressed explicitly.
- Cross-case conclusions generalize to theory, not to populations; never claim statistical representativeness.
- If only management or public success narratives are accessible, record that as an evidence limitation, not a finding.

Common errors to reject:

- calling a study a case study only because the subject is one company
- selecting cases because they are famous, successful, or convenient, with no theoretical logic
- multi-case work that stacks stories without within-case and cross-case analysis
- imposing statistical-sampling representativeness on theoretical sampling or replication logic
- interview quotes substituting for an evidence chain, or relying solely on management publicity material
- stages and mechanisms drawn from a polished narrative without event anchors or negative evidence
- extrapolating within-case explanation into universal regularities
