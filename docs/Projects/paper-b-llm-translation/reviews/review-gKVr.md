# Official Review — Reviewer gKVr
**Posted:** 23 Apr 2026 (modified 03 May 2026)
**Overall Assessment:** 3.5 = Borderline Conference
**Confidence:** 3 · **Soundness:** 4 · **Excitement:** 3 · **Reproducibility:** 4 · **Datasets:** 4 · **Software:** 1

## Paper Summary

The paper introduces Dictionarium Sinicum, an open resource that merges seven community‑maintained Chinese dictionaries (CC‑CEDICT, HanDeDict, CFDICT, CC‑CIDICT, CHEDICC, Wiktextract, JMdict) into a unified table of 428,073 headwords. Each headword is represented by a triple (traditional form, simplified form, pinyin). Using the MiniMax M2.5 large‑language model (LLM), the authors translate all headwords into 18 target languages, generating 7.7 million dictionary entries. Prompt engineering encourages dictionary‑style, multi‑sense glosses and mitigates script contamination by banning kanji echo in Japanese, hanja in Korean and any Chinese characters in non‑Chinese definitions. A three‑phase pipeline, main batch translation, retry, and context‑aware backfill, is run with about $146 in API costs and completes in under 27 hours, achieving 99.3% coverage overall and 100% coverage of multi‑character headwords. A deterministic script validator detects contaminated output (0.83% of definitions) and triggers re‑translation. Sense coverage and format compliance are evaluated against four existing dictionaries (English, German, French and Indonesian), yielding 87.3% coverage and 12.5% false‑sense rate. The resource outperforms multiple machine‑translation baselines by 12–22 percentage points on sense coverage. The dictionary is released with 511,514 Cantonese and Hokkien dialect forms from 18 open sources.

## Summary of Strengths

- **Large‑scale open lexicon:** first open multilingual Chinese dictionary covering 428,073 headwords and 18 languages. Cantonese/Hokkien forms add valuable dialect support.
- **Cost‑effective and reproducible pipeline:** $146, 27 hours, single mid‑size LLM.
- **Innovative prompt engineering:** rules to avoid script contamination (kanji echo, hanja) and enforce a lexicographer persona; deterministic validator identifies and cleans 0.83% of contaminated outputs.
- **Detailed evaluation:** 87.3% sense coverage; outperforms MT systems; script contamination analyzed across languages (e.g., Latin‑in‑Arabic, CJK‑in‑non‑CJK).

## Summary of Weaknesses

- **Glosses vs. full definitions:** Output provides translation equivalents, not full definitions or sense‑discriminated entries; polysemous words yield flat gloss lists; grammatical information (gender, aspect) is absent.
- **Limited evaluation scope:** Sense coverage uses lexical overlap with existing community definitions; for languages lacking such resources, pivot‑translation evaluation is limited. Human evaluation is restricted to LLM judges over 100 entries, raising bias/reliability concerns.
- **Reliance on a single proprietary model:** All 7.7M glosses come from MiniMax M2.5. Centralizes model‑specific biases; reproducibility risk if API/pricing changes.
- **Pivot translation and English bias:** For 12 target languages lacking community glosses, the model pivots through English definitions, inheriting English sense boundaries. Anglocentric meanings; may miss culturally specific senses.
- **Incomplete sense coverage:** LLM compresses senses (median 2 vs. community 3) and omits specialized or archaic senses. Korean shows weaker back‑translation accuracy.
- **Lack of error analysis per language:** Paper identifies contamination rates and failures but does not break down sense‑coverage errors by target language or headword class.

## Comments, Suggestions, and Typos

- **Broaden human evaluation:** Native‑speaker evaluations across all 18 languages, including low‑resource. Multiple annotators; mitigate LLM‑judge bias.
- **Experiment with open models:** Evaluate open‑weight LLMs or domain‑specific MT models; reduce proprietary API dependency, improve reproducibility.
- **Document pivot biases:** Analyze impact of English pivoting; compare direct vs. pivot translation for a sample of headwords in each language.
