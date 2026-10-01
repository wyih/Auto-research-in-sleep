# Models and construct validation

| Construct/material | Candidate approach | Decision that matters |
|---|---|---|
| English financial polarity | [ProsusAI FinBERT](https://huggingface.co/ProsusAI/finbert) or an established finance dictionary | Positive/negative/neutral labels; section-specific validity |
| Financial uncertainty or other dictionary constructs | A source-grounded dictionary with a stated counting rule | Negation, denominator, language, and dictionary version |
| Central-bank hawkish/dovish stance | A validated stance model or task-specific coding rubric | Policy stance label definition and speaker/time context |
| Chinese annual reports or calls | A validated Chinese/domain scorer or documented human/LLM coding | Corpus language, financial context, and local validation |
| Novel disclosure content or specificity | A theory-grounded rubric and labeled examples | Unit, boundaries between labels, adjudication, and holdout performance |

FinBERT's model card identifies English financial sentiment and three polarity classes. Verify `model.config.id2label` before interpreting output columns; record the model and tokenizer revision. Put the model in evaluation mode and use inference/no-gradient execution. Batch within the installed runtime's capacity. Use the tokenizer's actual context limit and segment long text explicitly.

For LLM coding, save the rubric, exact prompt, model/version, decoding settings, and raw responses used to derive scores. Parse expected labels and flag malformed answers. A provider's response is a measurement output; its agreement with labeled examples establishes what the coding rule captures.

## Validation proportional to the claim

- Draw examples across document types, sections, language, firms, time, and ambiguous cases relevant to the intended use. Identify examples with source IDs and keep their labels separately from model predictions.
- Define the labeling rule first. Where disagreement affects the construct, use documented adjudication or inter-rater agreement and inspect the conflicting cases.
- Report a confusion matrix and per-class precision/recall or suitable continuous-score agreement. Include class prevalence; overall accuracy can hide errors in a rare label central to the study.
- Split at the firm/document/time level appropriate to the claim so duplicated passages and related documents do not leak across tuning and validation. Fit text transformations and tune thresholds on the training/development partition.
- Inspect whether measurement errors vary with treatment, time, industry, document length, or disclosure selection when that could drive the main result. Use a dictionary or alternative segmentation as a sensitivity check only when it tests a material measurement concern.

## Aggregation examples

For sentence probability scores, net tone may be `mean(p_positive - p_negative)` over the defined section. For dictionary counts, net tone may be `(positive_count - negative_count) / eligible_word_count`. These measure different objects. Specify which formula the study uses and retain the denominator, coverage, and number of eligible units.

Decide whether sentence, word, section, or document weights match the economic construct. Handle overlap once, retain an explicit missing value for no usable text, and keep original and amended versions distinguishable. Report the merge coverage and temporal rule that make the score available to the subsequent analysis.
