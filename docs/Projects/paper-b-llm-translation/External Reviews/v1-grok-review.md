# Review: Dictionarium Sinicum v1 — Grok

## Overall verdict
- Soundness: 4/5
- Excitement: 4/5
- Reproducibility: 4/5
- Software: 4/5 (based on paper's description; reviewer would see anon-mirror)
- Datasets: 5/5 (based on paper's description; reviewer would see Zenodo DOI)
- Meaningful comparison: 4/5

## Summary
The paper presents Dictionarium Sinicum, a large-scale open multilingual Chinese dictionary covering 428,073 headwords across 18 target languages (plus Cantonese/Hokkien dialect forms). It is constructed by unifying seven existing community dictionaries and generating the remaining glosses with a single open-weight LLM (MiniMax M2.5) via a carefully engineered three-phase pipeline (batched multi-language generation, retry, and context-aware backfill), at a total inference cost of ~$150. The authors emphasize prompt design to suppress script contamination, a deterministic post-hoc validator, and a suite of automated evaluations including sense-coverage against community references, model-based MT metrics (BERTScore, COMET-DA, CometKiwi), an English-pivot ablation, per-language error signals, and second-model verification. The resource and pipeline are to be released under permissive licenses.

## Strengths
- Impressive scale and cost-efficiency: producing ~7.7M gloss slots (100% multi-character coverage) from a single open-weight model for under $150 is a concrete engineering contribution that lowers the barrier for similar resources in other source languages.
- Thorough treatment of a practical failure mode (script contamination / CJK leakage, kanji echo, hanja mixing). The combination of language-specific prompt rules + deterministic Unicode-script validator + cleanup/re-translation is well-described and quantified (0.83% contamination rate, Table 6).
- Multi-faceted automated evaluation that goes beyond simple lexical overlap: community sense coverage + false-sense rate (Tables 7–8), semantic MT metrics (Tables 7, 10), reference-free CometKiwi across all 18 languages (Table 11), English-pivot ablation on Vietnamese/Thai, full-corpus mono-gloss / CJK / echo rates (Appendix Table 13), and independent second-model rating (Gemma-4-31B).
- Clear open-science posture: open-weight model framing, planned public code + data releases with compatible CC licenses, explicit prioritization of community sources over LLM output, and honest Limitations/Future Work sections.
- Useful downstream framing (language-pack generation for learning apps) and dialect augmentation that leverages existing open Hokkien/Cantonese sources.

## Weaknesses (ranked)
1. **Circularity in the strongest quantitative claims for the four community-reference languages.** Section 5.2 and the associated tables repeatedly note that the production prompt supplies the existing community glosses as context. Consequently the reported 87.3% sense coverage, low false-sense rate, high BERTScore/COMET, and "outperformance" of MT baselines largely measure faithful context utilization / reproduction rather than independent generation quality. The paper acknowledges this but still frames the numbers as primary evidence of dictionary quality; this weakens the central comparative claim. A cleaner split (e.g., held-out headwords never shown the reference, or an ablation that removes community context) would have been more convincing.

2. **Absence of native-speaker human evaluation remains the largest gap for a lexicographic resource.** Automated proxies (lexical overlap, CometKiwi, LLM-as-judge, second-model ratings) are useful but inherit encoder biases, calibration problems on lower-resource scripts, and possible shared biases with the generator. The paper correctly defers full human eval to future work, yet for a resource whose primary claim is "dictionary-quality glosses," even a modest stratified sample (e.g., 50–100 entries × 4–6 languages rated by 2 native speakers each on accuracy/naturalness/completeness) would substantially raise confidence. The current completeness scores already flag sense compression as a systematic issue; human data would quantify how often that compression is harmful versus acceptable.

3. **English-pivot mediation and sample-size limitations for the 12 non-community languages.** The pipeline is explicitly pivot-based for these languages (§4.2, §5.3). The ablation (Llama-3.3-70B, n≈33 after CC-CEDICT filter) shows a mixed, language-dependent effect (+0.067 CometKiwi for Vietnamese, essentially neutral for Thai). While the authors are transparent about the small n and the language dependence, the result undercuts any strong claim that pivot bias is negligible. Combined with the near-flat but still lower non-community CometKiwi macro (0.542 vs 0.562), residual English sense-boundary effects remain under-characterized.

4. **Sense compression and lack of sense discrimination are systemic.** Median gloss count is lower than community references; many entries are mono-gloss (Table 13 shows 55–75% mono rates). The resource therefore functions more as a large translation-equivalent glossary than a true multi-sense dictionary. This is acknowledged in Limitations but still affects utility claims for language learning and NLP downstream tasks that need sense distinctions.

5. **Single-generator homogeneity.** All 7.7M LLM glosses come from MiniMax M2.5. The open-weight framing and the Llama pivot ablation mitigate some concern, but model-specific stylistic and semantic biases are uniformly propagated. The second-model verification (Gemma) is a good check on semantic preservation, yet does not address whether a different generator family would have produced systematically different coverage or error patterns.

6. **Minor statistical and reporting issues.** Confidence intervals are supplied for the main sense-coverage figure but not for most other metrics or the small ablation. Residual single-character gaps are concentrated in Arabic/Thai/German/Persian and attributed to metalinguistic CJK references that the validator correctly rejects; a short qualitative analysis of a few such radicals would help readers judge whether the gaps are inevitable or addressable.

## Questions for the authors
- For the community-language evaluation, what is the sense-coverage / semantic-metric performance on a true held-out subset of headwords whose community glosses were never supplied in the prompt?
- Can you release (or at least quantify) the exact fraction of "false senses" that manual inspection judged to be legitimate synonyms versus genuine errors? The 3% genuine-error claim in the <50% coverage slice is useful; the same analysis on the full sample would be stronger.
- In the English-pivot ablation, how sensitive are the CometKiwi deltas to the particular 50-headword samples and to the CC-CEDICT filter? Would a larger or stratified sample change the language-dependence conclusion?
- The parser robustness section mentions several failure modes and three layers of overwrite protection. Were any residual data-integrity issues discovered after the three backfill passes, and how were they quantified?
- Why was MiniMax M2.5 preferred over other open-weight models that also passed the 5-headword smoke test (e.g., the Kimi or Nemotron entries in Table 4) beyond the reported latency/cost numbers? Any qualitative differences in multi-sense or low-resource behavior?

## Missing prior art
The paper correctly positions itself relative to PanLex, BabelNet, the small Pre-Qin philosophy lexicon (Wu & Wang, 2025/2026, npj Heritage Science), and Chain-of-Dictionary prompting (Lu et al., EMNLP 2024). The scale and multilingual breadth claims appear accurate; no published peer-reviewed work of comparable headword × language coverage using LLMs was identified. Two related strands that could be briefly acknowledged for completeness:
- Small-scale synthetic Chinese–English dictionary generation pipelines that combine LLMs with CEDICT-style validation (e.g., public GitHub efforts producing ~75k enriched entries). These are not archival publications but illustrate concurrent interest in LLM lexicography for Chinese.
- Recent experimental work on LLM-assisted learner-oriented Chinese dictionary micro-structure (definition and example generation) appearing in Chinese-language venues; these remain far smaller and monolingual/bilingual.

None of the above undermines the novelty claim at the reported scale.

## Suggestions for the next revision
- Strengthen the independent-generation claim by reporting at least one non-circular evaluation slice for the four community languages (held-out headwords or context-ablated runs) and by expanding the pivot ablation (larger n, additional languages, confidence intervals).
- Even a modest native-speaker pilot (a few hundred ratings) on the languages that currently score lowest on CometKiwi / second-model verification (Tagalog, Thai, Arabic) would move both soundness and excitement upward; the paper already has the stratified sampling machinery.
- Consider releasing a "sense-compressed vs. community" parallel sample so users can judge the practical impact of the mono-gloss tendency.
- If compute budget allows, a small end-to-end open-weight alternative (e.g., a Qwen or Llama variant on a few thousand headwords) would further support the claim that the pipeline generalizes beyond MiniMax.
- Minor polish: ensure all tables that report percentages also give absolute counts or CIs where space permits; the residual single-character gap discussion could benefit from 2–3 concrete examples of rejected metalinguistic definitions.

Overall this is a solid, practically useful resource paper whose engineering and evaluation effort already address many of the concerns raised in the prior ARR round. Addressing the circularity and human-evaluation gaps more directly would make the contribution even stronger for NAACL/COLING Findings.
