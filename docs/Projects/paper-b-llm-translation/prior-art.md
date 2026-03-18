# Paper B: LLM Multilingual Dictionary Translation — Prior Art

## Our Claim
A single LLM (MiniMax M2.5) can translate 428K Chinese headwords into 18 languages for ~$150 at list rates, with prompt engineering solving CJK leaks, kanji echo, and Hangul purity.

## Closest Related Work

### LLM-Powered Lexicography
- **Pre-Qin Philosophy Lexicon via Qwen3-14B** (npj Heritage Science, Jan 2026): Uses LLM to generate bilingual (Chinese-English) dictionary entries for classical Chinese philosophical terms. Small-scale (~1K terms), single language pair. Shows LLMs can do lexicography but at tiny scale.
- **Chain-of-Dictionary Prompting** (EMNLP 2024): Uses existing bilingual dictionaries as chain-of-thought context to improve LLM translation of rare/low-resource words. Complementary approach — they use dictionaries to help LLMs translate; we use LLMs to BUILD dictionaries.
- **Legal Terminology Extraction**: Various papers on using LLMs to extract and translate domain-specific terminology. Smaller scale, single domain.

### Multilingual Translation with LLMs
- **Tower multilingual LLM** (Unbabel): Specialized multilingual translation model. Focuses on high-resource language pairs, not dictionary-style definitions.
- **Multi-agent Classical Chinese Translation**: Uses multiple LLM agents for classical Chinese → modern Chinese → English pipeline. Different task (document translation vs dictionary definitions).
- **NLLB (Meta)**: 200-language translation model. General purpose, not dictionary-style.

### Dictionary Construction
- **CC-CEDICT**: Community-maintained Chinese-English dictionary. Manual/crowdsourced, not LLM-generated.
- **HanDeDict, CFDICT**: Community Chinese-German and Chinese-French dictionaries. Same approach.
- **Wiktionary extraction**: Various projects extracting structured data from Wiktionary. Crowdsourced, not LLM.

### Prompt Engineering for Structured Output
- General literature on prompt engineering for structured output (JSON, tables). No published work on prompt engineering specifically for multilingual dictionary output with CJK contamination prevention.

## Novelty Assessment
- **Scale**: 428K headwords × 18 languages is unprecedented. Closest is Pre-Qin (~1K × 2 langs).
- **Cost**: ~$150 at list rates (~$20 actual via flat-rate subscription) for complete multilingual dictionary is a strong claim. No comparable cost analysis published.
- **Prompt engineering for CJK leaks**: Novel problem (Japanese kanji echo, Korean hanja mixing). No prior art on preventing script contamination in multilingual dictionary output.
- **Weakness**: LLM-generated dictionaries lack the authority of human-curated ones. Need strong quality evaluation to be convincing.

## Potential Venues
- ACL/EMNLP (NLP), LREC (language resources), EACL
- Machine Translation workshops
- Digital Humanities conferences

## Gap Rating: HIGH
No one has done LLM dictionary generation at this scale or across this many languages. Strong novelty on both scale and prompt engineering.
