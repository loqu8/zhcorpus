# Paper E: Dialect Pronunciation Coverage — Research Notes

Research compiled 2026-03-09 for a paper on building comprehensive character-level
Cantonese/Hokkien pronunciation databases using open sources + computational gap-filling.

## Problem Statement

Copyworks worksheets need character-level Cantonese (Jyutping) and Hokkien (POJ) readings
for HSK 1-6 (~2,600 chars) plus common Traditional characters. zhcorpus/dictmaster has 184K
dialect_forms but single-character coverage has gaps — especially Hokkien.

### Current Coverage (dictmaster.db, 2026-03-09)

| Tier | Cantonese | Hokkien |
|------|-----------|---------|
| Top 500 | 99.6% | 89.2% |
| Top 1,000 | 98.7% | 86.9% |
| Top 2,600 (HSK) | 91.8% | 78.1% |
| Top 3,000 | 90.2% | 75.3% |
| All single chars (19,471) | 34.6% (6,728) | 42.0% (8,181) |

Sources currently imported:
- Cantonese: CC-CEDICT readings (96K), CC-Canto (30K)
- Hokkien: TaiHua (48K), iTaigi (11K)

### The Gap

- **Cantonese**: 295 chars missing from top 3,000. Mostly traditional-form variants
  (為, 國, 學, 動, 區) — readings exist under simplified forms but lookup fails.
  Solvable with two imports (rime-cantonese + Unihan kCantonese) -> **100% coverage**.

- **Hokkien**: 740 chars missing from top 3,000 (24.7% gap). Structural problem:
  iTaigi and TaiHua are word-level dictionaries, not character-level pronunciation tables.
  No Hokkien equivalent of Unihan kCantonese exists. Requires: mechanical derivation from
  compounds + AI-assisted prediction for the remainder.

## Available Open Data Sources

### Already Downloaded

| Source | Location | Records | License |
|--------|----------|---------|---------|
| Rime jyut6ping3 chars | `data/raw/dictmaster/hokkien/rime-cantonese/` | 27,006 single chars | CC BY 4.0 |
| Rime jyut6ping3 words | same | 101,808 words | CC BY 4.0 |
| Rime jyut6ping3 phrases | same | 330,777 phrases | CC BY 4.0 |
| ChhoeTaigi (9 CSVs) | `data/raw/dictmaster/hokkien/ChhoeTaigiDatabase/` | 353K total | Various open |

Note: rime-cantonese is mislocated under `hokkien/` directory.

### Not Yet Downloaded

| Source | Description | Est. Coverage | License |
|--------|-------------|---------------|---------|
| Unihan kCantonese | Unicode Consortium, 29,936 chars with Jyutping | Near-total CJK | Unicode ToU |
| MoE Taiwan Minnan Dict | 教育部臺灣閩南語常用詞辭典 via [g0v/moedict-data-twblg](https://github.com/g0v/moedict-data-twblg) | ~16K headwords, POJ+Tai-lo | CC BY-SA-ND 3.0 |
| WikiHan (CMU LLAB) | 67,943 entries across 8 Sinitic varieties in IPA | Mandarin+Cantonese+Hokkien parallel | CC BY-SA 4.0 |
| 小学堂 (Xiaoxuetang) | Academia Sinica, **1.28M records across 14 dialect groups** | Most comprehensive | [GitHub CSV](https://github.com/lernanto/xiaoxuetang) |
| 漢字音典 HDQT | nk2028, **2,500+ language varieties** | Broadest coverage | GPL-3.0, [GitHub](https://github.com/nk2028/hdqt) |
| kfcd/yyzd | 開放粵語字典, Cantonese character readings | Comprehensive | Open, [GitHub](https://github.com/kfcd/yyzd) |
| words.hk | 粵典, 56K entries via [wordshk-tools](https://github.com/AlienKevin/wordshk-tools) | Comprehensive | CC BY-NC 4.0 |
| LSHK Jyutping Table | Official LSHK character-Jyutping table, TSV | Authoritative | CC BY 4.0, [GitHub](https://github.com/lshk-org/jyutping-table) |
| CanCLID/ToJyutping | Auto Jyutping labeling, 99% accuracy, g2p | Near-complete | [GitHub](https://github.com/CanCLID/ToJyutping) |
| Taibun | Python Hokkien transliterator, handles tone sandhi, POJ/Tai-lo | MIT | [GitHub](https://github.com/andreihar/taibun) |
| Glossika 10-Lang Dict | 5,000+ chars, 10 Chinese varieties incl. literary/colloquial | Free PDF | [glossika.com](https://ai.glossika.com/free-download/glossika-ten-language-dictionary-of-chinese-characters) |
| Wiktextract (kaikki.org) | Structured JSON from Wiktionary, weekly updates, multi-dialect | Broad | [kaikki.org](https://kaikki.org/dictionary/rawdata.html) |
| 漢語方音字匯 (2003) | PKU, ~2,800 chars × 20 dialect points | Top 3K chars | Academic |

### Major Chinese-Language Resources (中文学术资源)

**语保工程 (Language Resources Protection Project)**:
- 1,712 survey points, 123 languages, 10M+ entries (5M audio, 5M video), 100TB
- Per-point: 1,000 single characters + 1,200 vocabulary items
- Platform: [zhongguoyuyan.cn](https://zhongguoyuyan.cn/) — 1,284 dialect points publicly accessible
- This is the Chinese government's most comprehensive dialect documentation effort

**小学堂 (Xiaoxuetang) — Most Valuable for Our Project**:
- 1.28M phonological records, 200K+ character forms, 350K+ dictionary index entries
- Covers 14 dialect groups including 上古音, 中古音, 闽语, 粤语, 客语
- Machine-readable CSV at [lernanto/xiaoxuetang](https://github.com/lernanto/xiaoxuetang)
- Analysis tools: [lernanto/sinetym](https://github.com/lernanto/sinetym) (Python)

**侯精一《现代汉语方言音库》(Hou 1994-2004)**:
- 40 representative dialect points, all major groups
- Character pronunciation database with literary/colloquial distinction
- CD-ROM edition 2004; digital catalog at Cambridge Chinese Catalogue

### Projected Coverage After Imports

**Cantonese** (adding rime-cantonese + Unihan):

| Tier | Current | +Rime | +Rime+Unihan |
|------|---------|-------|-------------|
| Top 500 | 99.6% | 99.8% | **100%** |
| Top 1,000 | 98.7% | 99.8% | **100%** |
| Top 2,600 | 91.8% | 99.6% | **100%** |
| Top 3,000 | 90.2% | 99.5% | **100%** |

**Hokkien** — no single source closes the gap. Requires multi-source + computational:
- Additional ChhoeTaigi dicts (Maryknoll 55K, Embree 36K, KamJitian 24K)
- Mechanical single-char derivation from multi-char compound entries
- AI/ML prediction for remaining ~10-15%

## Scholarly Landscape

### Directly Comparable Work

1. **WikiHan** — Chang, Cui, Kim, Mortensen. COLING 2022.
   67,943 entries across 8 Sinitic varieties, normalized to IPA. Extracted from Wiktionary.
   Validated on protoform reconstruction (54.11% accuracy, 17.69% PER).
   [ACL Anthology](https://aclanthology.org/2022.coling-1.314/) |
   [GitHub](https://github.com/cmu-llab/wikihan)
   **Most directly comparable to our work.** Key difference: WikiHan only merges Wiktionary;
   we merge 5+ sources with coverage analysis and gap-filling.

2. **Automatic Reconstruction of Ancient Chinese Pronunciations** — Huang, Jin, Wu, Zhu.
   EMNLP Findings 2024. ACP dataset: 70,943 entries for 17,001 characters.
   Transformer-based reconstruction. Uses Hou (2004) phonological database.
   [ACL Anthology](https://aclanthology.org/2024.findings-emnlp.325/)

3. **Phonetic Reconstruction of Middle Chinese via Mixed Integer Optimization** — Luo, Sun.
   TACL 2025. Uses Guangyun + 20 modern dialects. Formal optimization approach.
   [MIT Press](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00742/128937) |
   [GitHub](https://github.com/Xiaoxi-Luo-CL/Reconstruction-of-Middle-Chinese-via-Mixed-Integer-Optimization)

### Cantonese NLP Resources

4. **Cantonese NLP in the Transformers Era: A Survey** — Xiang et al. LREV 2024.
   Key finding: only 61 Cantonese papers in ACL Anthology vs 9,756 for English.
   Establishes the resource gap.
   [Springer](https://link.springer.com/article/10.1007/s10579-024-09744-w)

5. **PyCantonese** — Lee, Chen, Lam, Lau, Tsui. LREC 2022.
   [ACL Anthology](https://aclanthology.org/2022.lrec-1.711)

6. **How Well Do LLMs Handle Cantonese?** — NAACL Findings 2025.
   [ACL Anthology](https://aclanthology.org/2025.findings-naacl.253)

### Hokkien NLP

7. **Enhancing Taiwanese Hokkien Dual Translation** — Lu, Lin, Lee, Tsai. arXiv 2024.
   Standardizes Hokkien's four writing systems for NMT.
   [arXiv](https://arxiv.org/abs/2403.12024)

8. **Hokkien-Mandarin Code-Mixing Corpora** — EMNLP Findings 2022.
   [GitHub](https://github.com/alznn/Taiwanese-Hokkien_Mandarin_CM_Dataset)

9. **Developing NLP Models for Taiwanese Hokkien** — J. Chinese Inst. Engineers, 2025.
   [Taylor & Francis](https://www.tandfonline.com/doi/full/10.1080/02533839.2025.2504703)

### Computational Dialect Prediction

10. **Multimodal Neural Pronunciation Modeling** — Nguyen, Ngo, Chen. EMNLP 2018.
    Predicts Cantonese from character radicals + Mandarin/Korean/Vietnamese cognates.
    LSTM with geometric decomposition. **54.1% relative reduction in Token Error Rate**.
    Key insight: radicals hint at nucleus/coda but NOT onset; cognate phonemes complement.
    [ACL Anthology](https://aclanthology.org/D18-1320/) |
    [GitHub](https://github.com/nguyen-binh-minh/logographic)

11. **Neural Proto-Language Reconstruction** — Cui et al. arXiv 2024.
    Transformer VAE predicts missing daughter-language readings from proto-forms + sister languages.
    Directly applicable to gap-filling.
    [arXiv](https://arxiv.org/abs/2404.15690)

12. **Improved Neural Protoform Reconstruction via Reflex Prediction** — Lu, Wang, Mortensen.
    LREC-COLING 2024. GRU beam search + reflex prediction reranking.
    [ACL Anthology](https://aclanthology.org/2024.lrec-main.762/) |
    [GitHub](https://github.com/cmu-llab/reranked-reconstruction)

### Chinese-Language AI/ASR Work on Dialects

13. **Dolphin** (Tsinghua, Zhang Weiqiang). Large-scale ASR supporting 40 East Asian
    languages including 22 Chinese dialect varieties, 212K hours training data.

14. **中国电信 "星辰" model**: First model supporting 30+ Chinese dialects in free
    mixing, processing ~2M calls/day. Won Interspeech 2024 ASR challenge.

15. **Cross-Dialect Semantic Embeddings** — arXiv 2601.07274 (2026). SOTA Chinese dialect
    ASR via cross-dialect semantic space learning.

16. **方音圖鑑** — Professional geolinguistics platform with phonological queries, ML for
    natural village classification. [dialects.yzup.top](https://dialects.yzup.top/)

## Key Challenges for Prediction

| Challenge | Severity | Notes |
|-----------|----------|-------|
| Literary vs. colloquial readings (wendu/baidu) | **Critical** for Hokkien | Same char has systematically different pronunciations. Hokkien 肉: literary jio̍k, colloquial bah |
| Ru tone (entering tone) loss | **Critical** | Preserved in Cantonese (3 checked tones), lost in Mandarin. Cannot recover from Mandarin alone |
| Many-to-many mappings | High | One Mandarin syllable -> multiple Cantonese/Hokkien syllables |
| Pre-Middle Chinese Min branching | Critical for Hokkien | Colloquial Hokkien readings branched off before Middle Chinese; correspondence rules don't apply |
| Tone sandhi | Moderate | Hokkien has complex tone sandhi; citation != surface form |
| Characters without standard Hokkien mapping | High | ~15% of Hokkien morphemes lack definitive character associations |

**Phonological regularity**: Less than 48% of characters have pronunciations matching their
phonetic radical (Zhou 1978). For Mandarin-Cantonese tone correspondence, regular cases
achieve 96.1% perception accuracy; irregular drops to 85.7% — suggesting ~10-15% irregularity.

## Publication Venues

### Primary Targets

| Venue | Deadline | Format | Fit |
|-------|----------|--------|-----|
| **EMNLP 2026** (Budapest) | ARR May 25, 2026 | Long/short paper | Strong — published WikiHan, ACP, Hokkien code-mixing |
| **LREV Journal** (Springer) | Rolling | Journal paper | Excellent — Cantonese NLP survey published here |
| **AACL-IJCNLP 2026** | TBA (~Aug 2026?) | Long/short via ARR | Good geographic fit for dialect work |

### Also Consider

| Venue | Deadline | Notes |
|-------|----------|-------|
| ISCSLP 2026 (Penang, Nov) | TBA (~Jun-Jul) | Needs speech angle |
| SIGHAN Workshop | TBA | Perfect topical fit, workshop-level |
| LREC 2028 | ~Oct 2027 | Ideal for resource paper, biennial |

**Note**: Paper B (Dictionarium Sinicum) already targets EMNLP ARR May cycle.
Submitting two papers to same cycle is allowed but doubles reviewing load.

## Licensing Compatibility

Our use case: data feeds into dictmaster.db which is used by Copyworks (commercial product).

| Source | License | Commercial OK? | Notes |
|--------|---------|----------------|-------|
| rime-cantonese | CC BY 4.0 | **YES** | Must attribute. Sources include LSHK, Words.hk, CC-Canto |
| LSHK Jyutping Table | CC BY 4.0 | **YES** | Must attribute LSHK |
| Unihan kCantonese | Unicode ToU | **YES** | Must acknowledge LSHK for Jyutping data |
| CC-Canto | CC BY-SA 4.0 | **YES** | Must share-alike if distributing raw data; derived works OK |
| CC-CEDICT | CC BY-SA 4.0 | **YES** | Same as CC-Canto |
| ChhoeTaigi | Various per dict | **CHECK** | Individual dict licenses vary; some may be restrictive |
| iTaigi | CC BY 4.0 | **YES** | Crowdsourced, attribution required |
| TaiHua | Open | **YES** | Community project |
| g0v/moedict-twblg | CC BY-SA-ND 3.0 TW | **CAUTION** | ND = No Derivatives. Can use data but cannot modify/transform? Unclear if importing into DB counts as derivative |
| words.hk | CC BY-NC 4.0 | **NO** | NC = Non-Commercial. Cannot use in Copyworks |
| kfcd/yyzd | Open | **LIKELY YES** | Need to verify specific license |
| Xiaoxuetang | Unknown | **CHECK** | Academic data from Academia Sinica; may have restrictions |
| WikiHan | CC BY-SA 4.0 | **YES** | Must share-alike |
| Glossika 10-Lang Dict | Free download, unclear terms | **CHECK** | Free != open; may have commercial restrictions |
| 漢語方音字匯 | Academic publication | **NO** | Copyrighted book, not open data |
| 语保工程 | Government | **CHECK** | Public browsing OK; bulk commercial use unclear |
| HDQT/漢字音典 | GPL-3.0 | **CAUTION** | GPL requires code sharing if distributed; data extraction may be OK |
| Taibun | MIT (code) | **YES** | Code is MIT; underlying data licenses separate |
| CanCLID/ToJyutping | MIT (code) | **YES** | Tool is MIT; data from rime-cantonese (CC BY 4.0) |
| Wiktextract/kaikki.org | CC BY-SA 3.0 | **YES** | From Wiktionary, share-alike |

### Safe to Use (Commercial)
rime-cantonese, LSHK, Unihan, CC-Canto, CC-CEDICT, iTaigi, TaiHua, WikiHan, Wiktextract,
Taibun (code), CanCLID/ToJyutping (code)

### Must Avoid for Copyworks
words.hk (NC), 漢語方音字匯 (copyrighted book)

### Needs Verification
g0v/moedict-twblg (ND clause), ChhoeTaigi (per-dict), Xiaoxuetang, Glossika, 语保工程, HDQT (GPL)

## Our Novel Contributions (vs. WikiHan)

1. **Multi-source merging**: 5+ open sources (CC-Canto, CC-CEDICT, rime-cantonese, Unihan,
   ChhoeTaigi, iTaigi, TaiHua) vs. WikiHan's Wiktionary-only approach
2. **Systematic coverage analysis**: Character-level coverage measured against HSK frequency
   tiers, not just raw counts
3. **Computational gap-filling**: LLM-assisted prediction for readings not in any open source,
   using existing multi-dialect data as context — no prior work does this
4. **Practical product target**: Coverage optimized for actual educational use (Copyworks
   worksheets), not just academic completeness
5. **Scale**: 184K dialect forms (growing), 428K headword base with 18-language definitions

## Next Steps

### Phase 1: Cantonese to 100% (data on disk, highest ROI)
1. Import rime-cantonese chars (27K single chars) -> ~99.5% for top 3K
2. Import Unihan kCantonese (29,936 chars) -> close remaining gaps -> **100%**

### Phase 2: Hokkien Source Expansion
3. Download [g0v/moedict-data-twblg](https://github.com/g0v/moedict-data-twblg) (MoE Hokkien dict in JSON/SQLite)
4. Import remaining ChhoeTaigi dicts (Maryknoll 55K, Embree 36K, KamJitian 24K)
5. Download [xiaoxuetang CSV](https://github.com/lernanto/xiaoxuetang) — 1.28M records, 14 dialect groups
6. Download [WikiHan](https://github.com/cmu-llab/wikihan) — parallel readings for validation

### Phase 3: Computational Gap-Filling
7. Mechanical Hokkien single-char derivation from multi-char compound entries
8. AI/LLM prediction for remaining Hokkien gaps using existing dialect context
9. Coverage re-analysis after each step (measure against HSK frequency tiers)

### Phase 4: Paper
10. Draft paper — target LREV journal (rolling, no deadline pressure)
11. Or EMNLP ARR May 25 if ready (tight, and Paper B also targets this cycle)
12. Or AACL-IJCNLP 2026 (~Aug deadline TBA)

### Key Downloads to Do Now
```bash
# Xiaoxuetang (1.28M dialect readings — most valuable single source)
git clone https://github.com/lernanto/xiaoxuetang.git data/raw/dictmaster/xiaoxuetang

# HDQT (2,500+ varieties)
git clone https://github.com/nk2028/hdqt.git data/raw/dictmaster/hdqt

# MoE Hokkien (g0v, JSON/SQLite)
git clone https://github.com/g0v/moedict-data-twblg.git data/raw/dictmaster/hokkien/moedict-twblg

# WikiHan (parallel readings)
git clone https://github.com/cmu-llab/wikihan.git data/raw/dictmaster/wikihan

# Cantonese open dict
git clone https://github.com/kfcd/yyzd.git data/raw/dictmaster/cantonese/yyzd

# Sinetym analysis tools
pip install sinetym  # or: git clone https://github.com/lernanto/sinetym.git
```
