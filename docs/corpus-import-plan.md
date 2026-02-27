# Corpus Import Plan

## Disk Budget

- **Available**: 785 GB free on `/dev/sdd`
- **Raw data acquired**: 15 GB on disk (after zip cleanup)
- **Estimated total (FTS5 only)**: 115-175 GB (raw + chunked + FTS5 indexed)
- **Estimated total (FTS5 + embeddings)**: 150-230 GB (add ~50 GB for representative subset embeddings)
- **Verdict**: fits easily — under 30% of disk even with full embeddings

## Data Sources

### 1. CC-CEDICT (cross-reference table)
- **Status**: DOWNLOADED 2026-02-24
- **File**: `data/raw/cedict_1_0_ts_utf-8_mdbg.txt` (9.4 MB, 124,260 entries)
- **Source**: https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz
- **License**: CC BY-SA 4.0
- **Refresh**: Monthly releases; re-download when needed
- **Action**: Parse and load into `cedict` table

### 2. Chinese Wikipedia
- **Status**: AVAILABLE in cedict-backfill DB (imported ~2025-12)
- **Stats**: 1,259,000 articles, 2.2 GB text, avg 1,744 chars/article
- **Source**: Wikimedia dumps (zhwiki-*-pages-articles-multistream.xml.bz2)
- **License**: CC BY-SA 3.0
- **Refresh**: Wikimedia dumps update ~monthly; data is encyclopedic, slow to change
- **Action**: Extract from cedict-backfill DB → chunk → load
- **Chunking estimate**: ~3-4M sentence-level chunks

### 3. Baidu Baike
- **Status**: AVAILABLE in cedict-backfill DB (imported ~2025-12)
- **Stats**: 1,622,632 articles, 289 MB text, avg 178 chars/article
- **Source**: HuggingFace `lars1234/baidu-baike-dataset`
- **License**: Research use
- **Refresh**: HuggingFace dataset is a static snapshot
- **Action**: Extract from cedict-backfill DB → chunk → load
- **Chunking estimate**: ~800K-1M chunks (shorter articles)

### 4. ChID (Chinese Idiom Dataset)
- **Status**: AVAILABLE in cedict-backfill DB (imported ~2025-12)
- **Stats**: 1,119,414 passages, 194 MB text, avg 172 chars/passage
- **Source**: HuggingFace `thu-coai/chid`
- **License**: Research use
- **Refresh**: Static academic dataset, will not change
- **Note**: Contains `#idiom#` fill-in-the-blank markers — strip on import
- **Action**: Extract from cedict-backfill DB → strip markers → chunk → load
- **Chunking estimate**: ~1M chunks (already short passages)

### 5. News Corpus
- **Status**: TO DOWNLOAD (tools ready)

#### Option A: news2016zh (RECOMMENDED)
- **Source**: brightmart/nlp_chinese_corpus — https://github.com/brightmart/nlp_chinese_corpus
- **Stats**: 2,500,000 articles from 63,000 media sources (2014-2016)
- **Size**: 9 GB raw (3.6 GB compressed)
- **Format**: JSONL with fields: `news_id`, `title`, `content`, `source`, `time`, `keywords`, `desc`
- **License**: Research use, cite DOI 10.5281/zenodo.3402023
- **Download**: Google Drive direct link
- **Value**: Massive, diverse news register with metadata; complements encyclopedic Wikipedia/Baike

#### Option B: THUCNews (Tsinghua)
- **Source**: THUNLP — https://github.com/thunlp/THUCTC
- **Stats**: 740,000 articles from Sina News RSS (2005-2011), 14 categories
- **Size**: 2.19 GB
- **Format**: UTF-8 plain text, one file per article, organized by category
- **License**: Free for academic/research use
- **Download**: HuggingFace mirrors (no registration): `Tongjilibo/THUCNews` (Apache-2.0, 3.6 GB)
- **Value**: Clean category labels (Finance, Tech, Sports, Politics, etc.) — useful for register tagging

#### Option C: Both
- news2016zh for breadth (2.5M articles, diverse sources)
- THUCNews for category labels (740K articles, 14 clean categories)
- Total: ~3.2M news articles, ~11 GB raw — still fits easily

#### Not recommended
- **People's Daily**: Not freely available as bulk full-text; only POS-tagged sentence corpus (1998)
- **CLUECorpus2020**: 100 GB, email-gated, mixed content — overkill for our needs

### 6. Classical Chinese Texts
- **Status**: DOWNLOADED 2026-02-24
- **Sources**:
  - NiuTrans/Classical-Modern: 327 books, bilingual (classical + modern), 1.3 GB, MIT
  - chinese-poetry: 55K Tang + 260K Song poems + 楚辞 + 四书五经 + 蒙学, 597 MB, MIT
- **Key texts**: 论语, 老子, 庄子, 孟子, 史记, 诗经, 左传, 红楼梦, 三国演义, 水浒传, 西游记, 唐诗三百首, 宋词三百首, 古文观止
- **License**: MIT (both repos), underlying texts public domain
- **Size**: 1.9 GB repos, ~100 MB raw text, 366K items
- **Refresh**: Static — these texts don't change
- **Value**: Rare/archaic character readings, literary register, classical idiom attestation, coverage for jieba's rare words
- **Action**: Import tool ready: `tools/import_classics.py`

### 7. Jieba Dictionary (reference only)
- **Status**: Stable, not a corpus source
- **Stats**: 349,045 entries in cedict-backfill DB, ~5 MB
- **Refresh**: Rare updates; pypi package version tracks it
- **Note**: Many rare words in jieba overlap with classical Chinese vocabulary — classical texts should provide attestation

### 8. Community Q&A — webtext2019zh
- **Status**: DOWNLOADED 2026-02-24
- **Source**: brightmart/nlp_chinese_corpus — https://github.com/brightmart/nlp_chinese_corpus
- **Stats**: 4,100,000 high-quality Q&A answers across 28,000 topics
- **Size**: 3.7 GB raw (1.7 GB compressed)
- **Format**: JSONL with fields: `qid`, `title`, `desc`, `topic`, `star`, `content`, `answer_id`, `answerer_tags`
- **License**: Research use, cite DOI 10.5281/zenodo.3402023
- **Download**: Google Drive direct link from repo README
- **Value**: Broadest vocabulary coverage of any single dataset — tech, health, cooking, law, finance, relationships, etc. across 28K topics. Fills social/colloquial register gap.
- **Chunking estimate**: ~6-8M chunks

### 9. Conversational Chinese — LCCC
- **Status**: DOWNLOADED 2026-02-24
- **Source**: Tsinghua COAI — https://github.com/thu-coai/CDial-GPT
- **Stats**: LCCC-large: 12,000,000 dialogues from Weibo conversations
- **Size**: ~3-5 GB uncompressed
- **Format**: JSON, each entry is a multi-turn dialogue (list of strings)
- **License**: MIT (research)
- **Download**: Google Drive links in repo README
- **Value**: Colloquial Mandarin — internet slang, discourse particles (吧/呢/啥), everyday vocabulary, emotional expressions. Registers that Wikipedia/news completely lack.
- **Chunking estimate**: ~15-20M chunks (short utterances)

### 10. Legal Cases — CAIL2018
- **Status**: DOWNLOADED 2026-02-24
- **Source**: https://github.com/china-ai-law-challenge/CAIL2018
- **Stats**: 2,680,000 criminal case descriptions with charges and sentencing
- **Size**: ~5-10 GB uncompressed
- **Format**: JSON with fact description, relevant articles, charges, prison term
- **License**: CC BY-NC-SA 4.0
- **Download**: Direct from GitHub / associated links
- **Value**: Legal register — 量刑, 缓刑, 取保候审, 侵权, 追诉. Vocabulary not found in any other source.
- **Chunking estimate**: ~5-8M chunks

### 11. Bilingual Parallel — translation2019zh
- **Status**: DOWNLOADED 2026-02-24
- **Source**: brightmart/nlp_chinese_corpus
- **Stats**: 5,200,000 zh-en sentence pairs
- **Size**: 1.1 GB raw (596 MB compressed)
- **Format**: JSONL with `english`, `chinese` fields
- **License**: Research use
- **Download**: Google Drive direct link
- **Value**: Directly useful for bilingual dictionary — example sentences with English translations. Diverse registers from translation sources.
- **Chunking estimate**: ~5-6M chunks

### 12. Encyclopedic Q&A — baike2018qa
- **Status**: DOWNLOADED 2026-02-24
- **Source**: brightmart/nlp_chinese_corpus
- **Stats**: 1,500,000 Q&A pairs across 492 categories
- **Size**: ~1 GB raw (663 MB compressed)
- **Format**: JSONL with `category`, `title`, `desc`, `answer`
- **License**: Research use
- **Download**: Google Drive / Baidu Pan
- **Value**: Complements Baidu Baike with explanatory Q&A format — semi-colloquial language across 492 categories.
- **Chunking estimate**: ~2-3M chunks

### 13. Scientific Abstracts — CSL
- **Status**: DOWNLOADED 2026-02-24
- **Source**: ydli-ai/CSL (COLING 2022) via Google Drive
- **Stats**: 396,209 paper abstracts from Chinese academic journals, 13 categories, 67 disciplines
- **Size**: 264 MB
- **Format**: TSV (title, abstract, keywords, discipline, category)
- **License**: Research use
- **Download**: HuggingFace, no registration
- **Value**: Academic/scientific vocabulary — 算法, 催化剂, 光谱, 拓扑, 聚合物. Keywords field useful for identifying technical terms.
- **Chunking estimate**: ~800K-1M chunks

### 14. Chinese Laws — LawRefBook
- **Status**: DOWNLOADED 2026-02-24
- **Source**: https://github.com/LawRefBook/Laws
- **Stats**: Complete collection of PRC laws and regulations
- **Size**: ~50-100 MB text
- **Format**: Structured markdown/JSON
- **License**: Public domain (government documents)
- **Download**: GitHub clone
- **Value**: Authoritative statute/regulatory register. Compact but extremely vocabulary-dense.
- **Chunking estimate**: ~50-100K chunks

### 15. Medical Q&A — cMedQA2 + Medical Dialogues
- **Status**: DOWNLOADED 2026-02-24
- **Source**: https://github.com/zhangsheng93/cMedQA2 + https://github.com/Toyhom/Chinese-medical-dialogue-data
- **Stats**: cMedQA2: 108K questions, 203K answers; Medical dialogues: ~800K across 6 departments
- **Size**: ~500 MB - 1 GB combined
- **Format**: CSV/JSON
- **License**: Research use
- **Download**: Direct from GitHub
- **Value**: Medical vocabulary — 诊断, 处方, 挂号, 问诊, 化验. Patient-accessible register + doctor-patient dialogue.
- **Chunking estimate**: ~1-2M chunks

### 16. Film/TV Subtitles — OpenSubtitles zh
- **Status**: DOWNLOADED 2026-02-24
- **Source**: OPUS project — https://opus.nlpl.eu/OpenSubtitles-v2018.php
- **Stats**: 16,316,804 subtitle lines (zh_cn simplified)
- **Size**: 423 MB uncompressed (165 MB gzipped)
- **Format**: TMX or plain text
- **License**: Open
- **Download**: Direct from OPUS
- **Value**: Natural spoken dialogue from movies/TV — everyday vocabulary, sentence-final particles, exclamations, diverse domains (crime, romance, sci-fi, historical).
- **Chunking estimate**: ~3-5M chunks

## Import Strategy

### Phase A: Quick bootstrap from cedict-backfill DB ✅ IN PROGRESS
1. Parse CC-CEDICT → `cedict` table ✅
2. Export Wikipedia articles from `jieba_candidates.db` → chunk → load (importing...)
3. Export Baidu Baike → chunk → load
4. Export ChID (strip #idiom# markers) → chunk → load
5. Build FTS5 trigram index + fts5vocab
6. Validate with 121 tests

### Phase B: News corpus
1. Download THUCNews via HuggingFace
2. Optionally download news2016zh via Google Drive (3.6 GB compressed)
3. Parse JSONL → chunk → load with source tags

### Phase C: Classical Chinese collection ✅ READY
1. NiuTrans/Classical-Modern cloned (327 books) ✅
2. chinese-poetry cloned (55K Tang + 260K Song + classics) ✅
3. Import tool ready: `tools/import_classics.py`

### Phase D: Specialized domains — ALL DOWNLOADED ✅
1. webtext2019zh (4.12M Q&A, 3.8 GB) ✅
2. LCCC-large (12M dialogues, 1.5 GB) ✅
3. CAIL2018 (2.61M legal cases, 3.5 GB) ✅
4. translation2019zh (5.16M bilingual pairs, 1.3 GB) ✅
5. baike2018qa (1.43M Q&A, 1.5 GB) ✅
6. Build importers for Q&A, dialogue, legal, and parallel text formats
7. Import all → chunk → load

### Phase E: Academic, legal statutes, medical, subtitles — ALL DOWNLOADED ✅
1. CSL scientific abstracts (396K, 264 MB TSV) ✅
2. LawRefBook/Laws (PRC statutes, 144 MB repo) ✅
3. cMedQA2 (108K Q + 203K A) + Medical Dialogues (~800K, 6 depts, GBK CSVs) ✅
4. OpenSubtitles zh_cn (16.3M lines, 423 MB) ✅
5. Build importers → chunk → load

### Phase F: Semantic search (embedding layer)
1. Use `qwen3-embedding` via Ollama (7.6B Q4_K_M, 4096 dims — same as srclight)
2. Embed representative subset: ~2-3M chunks (1 per article, best quality per source)
3. Store in `sqlite-vec` or `faiss` for ANN search
4. Build hybrid search: FTS5 + embeddings via RRF (Reciprocal Rank Fusion)
5. See **Semantic Search Plan** section below

### Phase G: Fresh downloads (optional, for reproducibility)
1. Download fresh Wikipedia zh dump
2. Download fresh Baike from HuggingFace
3. Download fresh ChID from HuggingFace
4. Full re-import pipeline

## Size Estimates

| Source | Raw Text | Est. Chunks | FTS5 Index | Total |
|--------|----------|-------------|------------|-------|
| CC-CEDICT | 9 MB | (reference) | — | 9 MB |
| Wikipedia | 2.2 GB | ~3-4M | ~6-10 GB | ~8-12 GB |
| Baidu Baike | 289 MB | ~800K-1M | ~800 MB | ~1.1 GB |
| ChID | 194 MB | ~1M | ~500 MB | ~700 MB |
| news2016zh | 9 GB | ~8-10M | ~15-20 GB | ~24-29 GB |
| THUCNews | 2.2 GB | ~2-3M | ~5-7 GB | ~7-9 GB |
| Classical | ~100 MB | ~200K | ~300 MB | ~400 MB |
| webtext2019zh | 3.7 GB | ~6-8M | ~10-14 GB | ~14-18 GB |
| LCCC | ~3-5 GB | ~15-20M | ~20-30 GB | ~23-35 GB |
| CAIL2018 | ~5-10 GB | ~5-8M | ~10-15 GB | ~15-25 GB |
| translation2019zh | 1.1 GB | ~5-6M | ~8-10 GB | ~9-11 GB |
| baike2018qa | ~1 GB | ~2-3M | ~3-5 GB | ~4-6 GB |
| CSL | ~500 MB | ~800K-1M | ~1-2 GB | ~1.5-3 GB |
| Chinese Laws | ~100 MB | ~50-100K | ~200 MB | ~300 MB |
| Medical Q&A | ~500 MB | ~1-2M | ~2-3 GB | ~2.5-3.5 GB |
| OpenSubtitles | ~1-2 GB | ~3-5M | ~5-8 GB | ~6-10 GB |
| **Total (all)** | **~30-42 GB** | **~55-75M** | **~87-140 GB** | **~115-175 GB** |

All fits within 785 GB available. With everything, under 23% of disk.

## Download Log

| Source | Date | Version/Notes |
|--------|------|---------------|
| CC-CEDICT | 2026-02-24 | 124,260 entries, fresh from mdbg.net |
| Wikipedia | ~2025-12 | Via cedict-backfill import, 1.26M articles |
| Baidu Baike | ~2025-12 | Via cedict-backfill import, 1.62M articles |
| ChID | ~2025-12 | Via cedict-backfill import, 1.12M passages |
| news2016zh | — | Pending download (Google Drive) |
| THUCNews | — | Pending download (HuggingFace) |
| NiuTrans/Classical-Modern | 2026-02-24 | git clone, 327 books + 97 bilingual, 1.3 GB repo, MIT |
| chinese-poetry | 2026-02-24 | git clone, 55K Tang + 260K Song poems + classics, 597 MB repo, MIT |
| webtext2019zh | 2026-02-24 | Google Drive, 4.12M Q&A answers, 3.8 GB uncompressed |
| LCCC-large | 2026-02-24 | Google Drive via gdown, 12M dialogues (7.3M single + 4.7M multi), 32.9M utterances, 1.5 GB JSON |
| CAIL2018 | 2026-02-24 | Aliyun OSS, 2.61M legal cases (1.71M first_stage + 748K rest + 155K exercise), 3.5 GB uncompressed |
| translation2019zh | 2026-02-24 | Google Drive, 5.16M zh-en sentence pairs, 1.3 GB uncompressed |
| baike2018qa | 2026-02-24 | Google Drive, 1.43M encyclopedic Q&A pairs with 492 categories, 1.5 GB uncompressed |
| CSL | 2026-02-24 | Google Drive via gdown, 396K scientific abstracts (TSV: title/abstract/keywords/discipline/category), 264 MB |
| LawRefBook/Laws | 2026-02-24 | git clone, PRC laws organized by category (刑法/民法典/宪法/etc), includes SQLite DB, ~50 MB text |
| cMedQA2 | 2026-02-24 | git clone, 108K questions + 203K answers, medical Q&A |
| Medical Dialogues | 2026-02-24 | git clone, ~800K dialogues across 6 departments (内科/外科/妇产科/儿科/肿瘤科/男科), GBK CSVs |
| OpenSubtitles zh_cn | 2026-02-24 | OPUS v2018, 16.3M subtitle lines, 165 MB gz / ~500 MB text |

## Semantic Search Plan

### Current search: FTS5 trigram (exact string matching)
- 3+ char terms: direct FTS5 MATCH with BM25 ranking
- 1-2 char terms: fts5vocab expansion → OR query → post-filter
- Fast, precise, handles all word lengths
- **Limitation**: only finds exact character sequences — no synonym/meaning-based retrieval

### Planned: Hybrid search (FTS5 + embeddings via RRF)

#### Embedding model
- **Model**: `qwen3-embedding` via Ollama (same as srclight code index)
- **Size**: 7.6B params, Q4_K_M quantized, 4.7 GB on disk
- **Dimensions**: 4096
- **Hardware**: RTX 3090 (local GPU)
- **Throughput**: ~30 embeddings/sec with real corpus chunks (avg 83 chars)

#### Why semantic search matters for lexicography
1. **Synonym expansion**: Search `高兴` → also surfaces `开心`, `愉快`, `欢喜`
2. **English-to-Chinese example finding**: "prosecuting someone" → finds `起诉`, `追诉`, `公诉`
3. **Sense disambiguation**: `打电话` vs `打人` vs `打折` cluster by meaning
4. **Register-aware retrieval**: "formal thank you" → ranks `不胜感激` above `谢谢啦`
5. **Definition writing**: AI agent searches by concept to find best illustrative sentences

#### Embedding strategy: representative subset
Full corpus (55-75M chunks) at 30 emb/sec = 26-29 days — impractical.

**Plan**: Embed a representative subset of ~2-3M chunks:
- 1 best chunk per article (longest or most content-dense)
- Ensures every source and register is covered
- ~2-3M chunks at 30 emb/sec = **19-28 hours** (overnight on 3090)

#### Storage estimate
- 2.5M chunks × 4096 dims × 4 bytes (float32) = **~38 GB**
- With int8 quantization: **~10 GB**
- Vector index overhead (HNSW): ~20% → total **~12-46 GB**

#### Hybrid search (RRF fusion)
```
score(doc) = 1/(k + rank_fts5) + 1/(k + rank_embedding)
```
- FTS5 provides **precision** — exact matches ranked by BM25
- Embeddings provide **recall** — semantically similar passages
- RRF merges both ranked lists (k=60 is standard)
- Result: exact `量刑` matches at top, plus related `判处`, `定罪`, `宣判` passages

#### Implementation plan
1. Add `chunk_embeddings` table: `chunk_id INTEGER, embedding BLOB`
2. Build embedding pipeline: read chunks → batch API → store
3. At query time: embed query → ANN search → RRF merge with FTS5
4. Library: `sqlite-vec` (SQLite extension) or `faiss` (Facebook)
5. Add to `search/hybrid.py` (currently stub in CLAUDE.md)
