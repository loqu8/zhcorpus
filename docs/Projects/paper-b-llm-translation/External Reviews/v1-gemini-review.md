# Review: Dictionarium Sinicum v1 — Gemini

## Overall verdict

* Soundness: 3/5
* Excitement: 4/5
* Reproducibility: 4/5
* Software: 4/5 (based on paper's description; reviewer would see anon-mirror)
* Datasets: 4/5 (based on paper's description; reviewer would see Zenodo DOI)
* Meaningful comparison: 3/5

## Summary

*Dictionarium Sinicum* presents an open multilingual Chinese dictionary comprising 428,073 headwords translated across 18 target languages (~7.7 million dictionary slots) and augmented with 511,514 Cantonese and Hokkien dialect forms. Using a single open-weight model (MiniMax M2.5) and a three-phase pipeline (batching, retry, and context-aware backfill), the resource was compiled for approximately $150 in API costs. The pipeline integrates tailored prompts to suppress script contamination (e.g., Japanese kanji echo and Korean hanja mixing) and employs a deterministic script validator that discards contaminated outputs (0.83% of total definitions). Evaluation relies on automated lexical overlap, model-based metrics (BERTScore, COMET-DA, CometKiwi), back-translation, and second-model verification (Gemma-4-31B).

## Strengths

* **Scale and cost efficiency**: Compiling 7.7 million target slots across 18 languages for under $150 with 99.3% overall coverage (100% for multi-character headwords) is a significant engineering achievement for open NLP resources.
* **Resource consolidation and dialect integration**: Unifying seven community dictionaries alongside 18 Cantonese and Hokkien dialect sources (Table 1, Table 2) under CC BY-SA 4.0 provides a consolidated, legally unencumbered lexicon for Chinese NLP.
* **Robust script contamination control**: The combination of prompt-level constraints (§4.2) and a deterministic post-translation validator (§5.1) effectively identifies and removes multi-lingual leakage (e.g., Cyrillic in Arabic, hanja in Korean) prior to database insertion.
* **Comprehensive multi-metric evaluation strategy**: The authors evaluate output quality across multiple dimensions, including reference-free quality estimation (CometKiwi) on all 18 languages (§5.3), error taxonomies (Appendix C), and second-model semantic preservation checks.

## Weaknesses (ranked)

1. **Confounded baseline comparison (§5.2, §5.3, Abstract lines 023–027, Table 9)**: The paper claims that the proposed pipeline outperforms ten MT baselines by 12–22 percentage points on sense coverage (Table 9). However, as acknowledged in §5.2 (lines 371–376), the production prompt provides existing community reference glosses as input context to MiniMax M2.5, whereas the baseline models in Table 9 received a generic prompt without reference context. Consequently, Table 9 measures context retention for the proposed pipeline against zero-context translation for the baselines. Abstracting this as a raw translation performance win (+12–22pp) is misleading; it reflects prompt context availability rather than superior intrinsic translation ability.
2. **Underpowered sample size for the pivot ablation claim (§5.3 lines 481–493)**: The claim that pivot bias is "language-dependent" (improving Vietnamese CometKiwi by +0.067 while remaining neutral for Thai) is based on a sample of $n = 50$ headwords per language, which drops to $n \approx 33$ after filtering. Drawing architectural conclusions about target-language distance from English on fewer than 40 data points per language is statistically underpowered.
3. **Over-reliance on LLM-as-judge for non-community languages (§5.3 lines 499–516, §6 lines 563–565)**: For the 12 languages lacking community reference dictionaries, quality assurance relies on Gemma-4-31B rating MiniMax outputs and back-translation with LLM judges. Because open-weight LLMs share common training corpora and pre-training objectives, LLM judges suffer from shared self-preference and alignment biases. While acknowledged in Limitations (§6), this leaves 66% of the target languages without independent ground-truth verification.
4. **API and provider instability impacting execution (§4.1 lines 209–222)**: Section 4.1 notes that running MiniMax M2.1 on NVIDIA NIM vs. Fireworks caused dramatic latency differences (167s vs. 5.4s per entry) due to silent thinking mode toggles. While informative, it highlights that relying on third-party inference providers introduces behavioral variance that complicates exact pipeline execution reproducibility across environments.
5. **Absence of grammatical and lexicographical structure (§6 lines 545–551)**: The generated resource consists of flat translation glosses rather than structured dictionary entries. It lacks sense discrimination (polysemous words output flat lists), part-of-speech tagging for target languages, noun genders (e.g., German), or aspectual pairs (e.g., Russian), limiting its utility for downstream lexicographical applications compared to traditional bilingual dictionaries.

## Questions for the authors

1. If the MT baselines (e.g., Claude Sonnet 4, GPT-4o-mini) in Table 9 were supplied with the exact same community reference glosses in their input context as MiniMax M2.5, how much of the 12–22 percentage point coverage gap would remain?
2. In §5.3 (lines 481–493), why was the pivot ablation conducted on only $n=50$ headwords ($n \approx 33$ post-filter)? Can this ablation be scaled to $n \ge 300$ per language with 95% confidence intervals to verify if the Vietnamese vs. Thai pivot delta is statistically significant?
3. For single-character headwords with persistent coverage gaps in Arabic, Thai, German, and Persian (§5.1 lines 351–355), could the script validator be adapted to permit metalinguistic references for obscure radicals without discarding the output?

## Missing prior art

* **Wang et al. (2023)**: *Document-level Machine Translation with Large Language Models*. (Relevant to §4.2 for context-augmented prompting strategies in LLM translation).
* **Haddow et al. (2022)**: *Survey on Low-Resource Machine Translation*. (Relevant to §1 and §7 regarding pivot-based translation risks in under-resourced languages).
* **Bond and Paik (2012)**: *A survey of open multilingual WordNets*. In Proceedings of the Global WordNet Conference (GWC). (Relevant to §2.1 for community-maintained open multilingual lexical networks).

## Suggestions for the next revision

1. **Re-align baseline evaluation framing**: Explicitly state in the Abstract (lines 023–027) and §5.3 that Table 9 evaluates context retention versus zero-context MT baselines, or run a control experiment providing baseline models with the same context to isolate the effect of prompt structure versus model capability.
2. **Expand pivot ablation sample size**: Increase the sample size for the English-pivot ablation in §5.3 to at least $n=300$ headwords per language and report 95% bootstrap confidence intervals.
3. **Incorporate small-scale human sanity checks**: Perform a targeted human evaluation on a small, stratified sample (e.g., 50–100 entries across 2–3 non-community languages like Tagalog, Vietnamese, or Arabic) to validate whether Gemma-4-31B quality scores correlate with native-speaker judgments.
