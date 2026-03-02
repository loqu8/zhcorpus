# zhcorpus — Source Licensing & Attribution Guide

Complete licensing reference for all data sources in zhcorpus (corpus) and dictmaster (dictionary).
Last updated: 2026-02-27.

---

## Quick Reference

### Corpus Sources (zhcorpus.db)

| # | Source | License | Commercial? | Citation Required? |
|---|--------|---------|:-----------:|:------------------:|
| 1 | Chinese Wikipedia | CC BY-SA 4.0 + GFDL | Yes | Yes (ShareAlike) |
| 2 | Baidu Baike | Non-commercial research | **No** | Yes |
| 3 | ChID (idioms) | Apache 2.0 | Yes | Yes (paper) |
| 4 | news2016zh | MIT | Yes* | Yes (DOI) |
| 5 | THUCNews | MIT (toolkit) / unclear (data) | **Uncertain** | Yes (THUNLP) |
| 6 | webtext2019zh | MIT | Yes* | Yes (DOI) |
| 7 | LCCC-large | MIT | Yes* | Yes (paper) |
| 8 | CAIL2018 | MIT | Yes | Yes (paper) |
| 9 | translation2019zh | MIT | Yes* | Yes (DOI) |
| 10 | baike2018qa | MIT | Yes* | Yes (DOI) |
| 11 | CSL | Apache 2.0 | Yes | Yes (paper) |
| 12 | LawRefBook/Laws | Public domain (PRC law) | Yes | No |
| 13 | cMedQA2 | GPL-3.0 | Yes (copyleft) | Yes (paper) |
| 14 | Medical Dialogues | MIT | Yes | Yes (copyright) |
| 15 | OpenSubtitles zh | Unclear / no standard license | **No (risky)** | Yes (paper) |
| 16 | Classical-Modern | MIT | Yes | Yes (copyright) |
| 17 | chinese-poetry | MIT | Yes | Yes (copyright) |

**Yes*** = Dataset compilation is MIT-licensed, but underlying content was aggregated from
third-party sources (news publishers, social media users) who retain copyright on their
original contributions. Standard for research use; consult legal counsel for redistribution.

### Dictionary Sources (dictmaster.db)

| Source | License | Commercial? | Attribution |
|--------|---------|:-----------:|-------------|
| CC-CEDICT | CC BY-SA 4.0 | Yes | "CC-CEDICT" + https://cc-cedict.org/ |
| CFDICT | CC BY-SA 3.0 | Yes | https://chine.in |
| HanDeDict | CC BY-SA 3.0 | Yes | "HanDeDict" + https://handedict.zydeo.net/ |
| CC-CIDICT | CC BY-SA 4.0 | Yes | "CC-CIDICT" + https://cidict.org/ |
| Wiktextract | CC BY-SA 4.0 | Yes | "Wiktionary via Kaikki.org" |
| JMDict | CC BY-SA 4.0 | Yes | EDRDG attribution |
| ChEDICC | Open Source | Yes | ChEDICC project |
| MiniMax (LLM) | No restriction | Yes | "AI-generated via MiniMax M2.5" |

### Dialect Sources (in dictmaster.db)

| Source | License | Commercial? | Attribution |
|--------|---------|:-----------:|-------------|
| CC-Canto (cccedict-readings) | CC BY-SA | Yes | CC-Canto / Pleco |
| CC-Canto (cccanto) | CC BY-SA | Yes | CC-Canto / Pleco |
| iTaigi | CC BY-SA 4.0 | Yes | iTaigi project |
| TaiHua | Research use | Uncertain | TaiHua dictionary |

---

## Detailed Source Documentation

### 1. Chinese Wikipedia

- **License**: CC BY-SA 4.0 + GFDL (dual-licensed)
- **URL**: https://dumps.wikimedia.org/
- **Stats**: 1,259,000 articles, 21.3M chunks
- **Commercial use**: Yes
- **Requirements**: Attribution + ShareAlike — derivative works must use CC BY-SA 4.0 or compatible
- **Notes**: All original Wikipedia text is dual-licensed. Some text may be CC BY-SA only.

### 2. Baidu Baike

- **License**: Non-commercial research only (custom terms)
- **URL**: https://huggingface.co/datasets/lars1234/baidu-baike-dataset
- **Stats**: 1,622,624 articles, 6.7M chunks
- **Commercial use**: **No** — explicitly prohibited without Baidu's permission
- **Requirements**: Cite "Beijing Institute of Technology (BIT-ENGD)" as dataset creators
- **Notes**: Content owned by Baidu. HuggingFace card states "research purposes only."
  This is a mirror of scraped content; no standard open-source license.

### 3. ChID (Chinese Idiom Dataset)

- **License**: Apache License 2.0
- **URL**: https://github.com/chujiezheng/ChID-Dataset
- **Stats**: 38,643 articles, 165K chunks
- **Commercial use**: Yes
- **Citation**: Zheng et al. "ChID: A Large-scale Chinese IDiom Dataset for Cloze Test" (ACL 2019)
- **Notes**: Archived repo (May 2024). License is clear Apache 2.0 on both GitHub and HuggingFace.

### 4. news2016zh

- **License**: MIT License
- **URL**: https://github.com/brightmart/nlp_chinese_corpus
- **DOI**: 10.5281/zenodo.3402023
- **Stats**: ~2,500,000 articles from 63,000 media sources (2014-2016)
- **Commercial use**: Yes under MIT*
- **Citation**: Bright Xu, "NLP Chinese Corpus", DOI 10.5281/zenodo.3402023, 2019
- **Notes**: MIT covers the dataset curation. Underlying news articles are from third-party
  publishers who retain copyright. Standard for research use.

### 5. THUCNews

- **License**: MIT (toolkit at github.com/thunlp/THUCTC); data provenance unclear
- **URL**: https://huggingface.co/datasets/Tongjilibo/THUCNews (mirror)
- **Stats**: ~740,000 articles from Sina News (2005-2011), 14 categories
- **Commercial use**: **Uncertain** — THUCTC toolkit is MIT, but news text was scraped from
  Sina News which holds copyright
- **Citation**: THUCTC by Tsinghua NLP Lab (THUNLP)
- **Notes**: HuggingFace mirror by Tongjilibo; no explicit license on dataset card.
  Original intended for academic/research use. Treat as research-only.

### 6. webtext2019zh

- **License**: MIT License (same as #4)
- **URL**: https://github.com/brightmart/nlp_chinese_corpus
- **Stats**: 4,247,516 Q&A answers, 18.2M chunks
- **Commercial use**: Yes under MIT*
- **Notes**: User-generated Q&A content. Part of brightmart collection.

### 7. LCCC-large

- **License**: MIT License
- **URL**: https://github.com/thu-coai/CDial-GPT
- **Stats**: 12,007,759 dialogues, 19.5M chunks
- **Commercial use**: Yes under MIT*
- **Citation**: Wang et al. "A Large-Scale Chinese Short-Text Conversation Dataset" (NLPCC 2020)
- **Notes**: Weibo conversations. Copyright (c) 2020 lemon234071.
  Underlying Weibo posts have their own copyright.

### 8. CAIL2018

- **License**: MIT License
- **URL**: https://github.com/china-ai-law-challenge/CAIL2018
- **Stats**: 2,916,228 legal cases, 17.4M chunks
- **Commercial use**: Yes
- **Citation**: Xiao et al. "CAIL2018: A Large-Scale Legal Dataset for Judgment Prediction" (2018)
- **Notes**: Criminal case descriptions from China Judgments Online (public government resource).
  **Correction**: Previously listed as CC BY-NC-SA 4.0 in corpus-import-plan.md — actual
  LICENSE file is MIT.

### 9. translation2019zh

- **License**: MIT License (same as #4)
- **URL**: https://github.com/brightmart/nlp_chinese_corpus
- **Stats**: 5,200,757 zh-en sentence pairs, 5.6M chunks
- **Commercial use**: Yes under MIT*
- **Notes**: Translation pairs from various sources. Part of brightmart collection.

### 10. baike2018qa

- **License**: MIT License (same as #4)
- **URL**: https://github.com/brightmart/nlp_chinese_corpus
- **Stats**: 1,467,584 Q&A pairs, 8.3M chunks
- **Commercial use**: Yes under MIT*
- **Notes**: Encyclopedic Q&A across 492 categories. Part of brightmart collection.

### 11. CSL (Chinese Scientific Literature)

- **License**: Apache License 2.0
- **URL**: https://github.com/ydli-ai/CSL
- **Stats**: 396,209 abstracts, 563K chunks
- **Commercial use**: Yes
- **Citation**: Li et al. "CSL: A Large-scale Chinese Scientific Literature Dataset" (COLING 2022)
- **Notes**: Scientific abstracts from Chinese journals. Abstracts may have publisher restrictions,
  but dataset release is explicitly Apache 2.0.

### 12. LawRefBook/Laws

- **License**: Public domain (PRC Copyright Law, Article 5)
- **URL**: https://github.com/LawRefBook/Laws
- **Stats**: 3,529 law documents, 401K chunks
- **Commercial use**: Yes — PRC laws are explicitly excluded from copyright protection
- **Requirements**: None legally required
- **Notes**: Article 5 of PRC Copyright Law excludes "laws, regulations, decisions of state
  agencies" from copyright. No LICENSE file in repo but content is public domain by statute.

### 13. cMedQA2

- **License**: GPL-3.0 (GNU General Public License v3.0)
- **URL**: https://github.com/zhangsheng93/cMedQA2
- **Stats**: 346,266 articles, 841K chunks
- **Commercial use**: Yes, but with **copyleft obligations** — derivative works must be GPL-3.0
- **Citation**: Zhang et al. "Multi-Scale Attentive Interaction Networks for Chinese Medical
  Question Answer Selection" (BMC Medical Informatics, 2018)
- **Notes**: GPL-3.0 copyleft may require source distribution for commercial derivatives.
  Significant constraint vs. MIT/Apache sources.

### 14. Chinese Medical Dialogues

- **License**: MIT License
- **URL**: https://github.com/Toyhom/Chinese-medical-dialogue-data
- **Stats**: 792,099 dialogues, 3.5M chunks
- **Commercial use**: Yes
- **Copyright**: Copyright (c) 2019 Toyhom
- **Notes**: ~800K dialogues across 6 medical departments (内科/外科/妇产科/儿科/肿瘤科/男科).

### 15. OpenSubtitles zh_cn

- **License**: Unclear / no standard license
- **URL**: https://opus.nlpl.eu/OpenSubtitles-v2018.php
- **Stats**: 3,263,361 subtitle groups, 5.1M chunks
- **Commercial use**: **No (risky)** — subtitles are transcriptions of copyrighted dialogue
- **Citation**: Lison & Tiedemann, "OpenSubtitles2016" (LREC 2016)
- **Notes**: OPUS describes data as "freely available to the research community."
  User-contributed subtitles on opensubtitles.org. Copyright status is disputed in the
  NLP community. Treat as **research use only**.

### 16. NiuTrans/Classical-Modern

- **License**: MIT License
- **URL**: https://github.com/NiuTrans/Classical-Modern
- **Stats**: 21,343 articles, 3.4M chunks
- **Commercial use**: Yes
- **Copyright**: Copyright (c) 2022 NiuTrans Open Source
- **Notes**: 327 classical Chinese texts with modern translations. Underlying classical texts
  are public domain (ancient works). Modern translations from various web sources may have
  their own copyright; dataset release is MIT.

### 17. chinese-poetry

- **License**: MIT License
- **URL**: https://github.com/chinese-poetry/chinese-poetry
- **Stats**: 344,899 poems, 1.6M chunks
- **Commercial use**: Yes
- **Copyright**: Copyright (c) 2016 JackeyGao
- **Notes**: 55K Tang poems + 260K Song poems + classics. Ancient poems are public domain
  (authors died 500+ years ago). Database compilation is MIT.

---

## License Compatibility

### For research use (non-commercial, internal)
All 17 sources are compatible. No restrictions prevent combined use for research.

### For commercial use / redistribution
Must exclude or segregate:
- **Baidu Baike** (#2) — non-commercial only
- **OpenSubtitles** (#15) — unclear license, copyright risk
- **THUCNews** (#5) — unclear data license (Sina copyright)
- **cMedQA2** (#13) — GPL-3.0 copyleft (may require source distribution)

The remaining 13 sources are commercially usable under MIT, Apache 2.0, CC BY-SA, or
public domain, with appropriate attribution.

### Dictionary license compatibility
All dictmaster sources use CC BY-SA (3.0 and 4.0), which are compatible.
Combined output distributable under **CC BY-SA 4.0** with attribution.
AI-generated definitions (MiniMax) have no upstream license restrictions.

---

## Required Citations

### Primary corpus citation
```
Bright Xu. NLP Chinese Corpus: Large Scale Chinese Corpus for NLP.
DOI: 10.5281/zenodo.3402023, 2019.
```
(Covers: news2016zh, webtext2019zh, translation2019zh, baike2018qa)

### Per-source citations
```
ChID:           Zheng et al. (ACL 2019)
LCCC:           Wang et al. (NLPCC 2020)
CAIL2018:       Xiao et al. (2018)
CSL:            Li et al. (COLING 2022)
cMedQA2:        Zhang et al. (BMC Medical Informatics 2018)
OpenSubtitles:  Lison & Tiedemann (LREC 2016)
THUCNews:       THUNLP / Tsinghua NLP Lab
Wikipedia:      Wikimedia Foundation
```

### Dictionary citations
```
CC-CEDICT:      Paul Andrew Denisowski, community-maintained (CC BY-SA 4.0)
CFDICT:         David Houstin / Chine Informations (CC BY-SA 3.0)
HanDeDict:      Gábor L Ugray, Dr. Michael Klaus Engel, Jan Hefti (CC BY-SA 3.0)
CC-CIDICT:      Harmony Mandarin (CC BY-SA 4.0)
Wiktextract:    Tatu Ylonen / Kaikki.org (CC BY-SA 4.0)
JMDict:         James William Breen / EDRDG (CC BY-SA 4.0)
```

---

## Corrections from Previous Documentation

1. **CAIL2018**: Previously listed as "CC BY-NC-SA 4.0" in `docs/corpus-import-plan.md`.
   Actual LICENSE file in repo is **MIT**. Corrected here.
2. **ChID**: Previously listed as "Research use" in import plan.
   Actual license is **Apache 2.0**. Corrected here.

---

## CJKI Dictionaries (PROPRIETARY — DO NOT USE)

Located at: `C:\Users\timuy\Dropbox\loqu8\ext\data\in\CE`

These are **commercially licensed** dictionaries from the CJK Institute.
They must **NEVER** be imported into zhcorpus or dictmaster.

- **License**: Proprietary / Commercial
- **Usage**: Loqu8 Intuition products only
- **May contain canary entries** (fake entries to detect unauthorized copying)
