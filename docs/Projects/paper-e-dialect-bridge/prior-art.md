# Paper E: Dialect Pronunciation Coverage — Prior Art

## Our Claim

Open-source dialect dictionaries can be unified into a comprehensive character-level
pronunciation database for Cantonese (Jyutping) and Hokkien (POJ), with computational
gap-filling (rule-based + LLM-assisted) achieving near-complete coverage for the top
3,000 most frequent characters. The methodology is reproducible for other Chinese dialects.

## Closest Related Work

### 1. WikiHan (COLING 2022) — Most Directly Comparable
Chang, Cui, Kim, Mortensen (CMU LLAB). 67,943 entries across 8 Sinitic varieties in IPA.
- **Similarity**: Multi-variety character pronunciation dataset
- **Our advantage**: 5+ sources vs. Wiktionary-only; coverage analysis against frequency tiers;
  computational gap-filling; 184K dialect forms (3x scale); practical product target (worksheets)
- **Our weakness**: WikiHan uses unified IPA; we use native romanizations (Jyutping, POJ)
- [ACL Anthology](https://aclanthology.org/2022.coling-1.314/)

### 2. Neural Pronunciation Prediction (EMNLP 2018)
Nguyen, Ngo, Chen. Multimodal LSTM predicts Cantonese from character radicals + cognate
pronunciations in related languages. 54.1% relative TER reduction.
- **Relevance**: Validates our approach of using existing readings to predict missing ones
- **Our difference**: We use LLMs with dictionary context, not radical decomposition
- [ACL Anthology](https://aclanthology.org/D18-1320/)

### 3. Ancient Chinese Pronunciation Reconstruction (EMNLP Findings 2024)
Huang, Jin, Wu, Zhu. ACP dataset: 70,943 entries, 17,001 characters. Transformer-based.
- **Relevance**: Reconstructs ancestral readings from modern dialects (inverse of our problem)
- **Our difference**: We predict modern dialect readings from Mandarin + context, not proto-forms
- [ACL Anthology](https://aclanthology.org/2024.findings-emnlp.325/)

### 4. Middle Chinese Reconstruction via MIP (TACL 2025)
Luo, Sun. Formal optimization using Guangyun + 20 modern dialects.
- **Relevance**: Shows computational methods can produce phonologically valid reconstructions
- **Our difference**: Practical coverage database vs. theoretical reconstruction
- [MIT Press](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00742/128937)

### 5. Reflex Prediction for Gap-Filling (LREC-COLING 2024)
Lu, Wang, Mortensen (CMU LLAB). Predicts missing daughter-language readings from proto-forms
+ sister-language data. GRU beam search + reranking.
- **Relevance**: Directly validates computational gap-filling in comparative datasets
- **Our difference**: We use LLMs, they use trained seq2seq models
- [ACL Anthology](https://aclanthology.org/2024.lrec-main.762/)

### 6. Cantonese NLP Survey (LREV 2024)
Xiang et al. Documents the resource gap: only 61 Cantonese papers in ACL Anthology.
- **Relevance**: Establishes motivation — Cantonese is under-resourced
- [Springer](https://link.springer.com/article/10.1007/s10579-024-09744-w)

### 7. Hokkien Writing System Standardization (arXiv 2024)
Lu, Lin, Lee, Tsai. Standardizes Hokkien's four writing systems for NMT.
- **Relevance**: Addresses the fundamental Hokkien writing fragmentation problem
- [arXiv](https://arxiv.org/abs/2403.12024)

## Novelty Assessment (Updated)

| Contribution | Novelty | Competition |
|-------------|---------|-------------|
| Multi-source merging (11 open dicts) | **High** | WikiHan uses Wiktionary only |
| Frequency-tier coverage analysis | **High** | No prior work measures against HSK/frequency tiers |
| LLM-assisted gap-filling for dialect readings | **Novel** | Prior work uses seq2seq; LLMs with dictionary context is new |
| 326K dialect forms unified database | **Good scale** | WikiHan 68K, but in IPA |
| Hokkien single-char derivation from compounds | **Novel** | Not attempted computationally |
| Reproducible methodology for other dialects | **Moderate** | WikiHan also claims this |

## Gap Rating: STRONG

The combination of multi-source merging + systematic coverage analysis + LLM gap-filling
is genuinely novel. WikiHan is the closest competitor but doesn't do gap-filling or
coverage analysis against practical frequency targets. The Hokkien single-character
derivation from compounds is a new contribution. The literary/colloquial reading
distinction in Hokkien adds depth that WikiHan doesn't address.

## Key Risk

The EMNLP ARR May 25 deadline is tight (~11 weeks). If Paper B (Dictionarium Sinicum) is
also targeting this cycle, prioritize. LREV journal (rolling) is a strong fallback with no
deadline pressure.
