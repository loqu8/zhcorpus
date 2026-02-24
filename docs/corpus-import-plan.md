# Corpus Import Plan

## Disk Budget

- **Available**: 785 GB free on `/dev/sdd`
- **Estimated total**: 20-30 GB (raw + chunked + FTS5 indexed)
- **Verdict**: fits easily

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

### 5. News Corpus (NEW)
- **Status**: TO DOWNLOAD

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

### 6. Classical Chinese Texts (NEW)
- **Status**: TO DOWNLOAD
- **Sources**:
  - Chinese Text Project (ctext.org) — pre-Qin to Qing dynasty, API available
  - Chinese Wikisource (zh.wikisource.org) — public domain classical texts
  - HuggingFace classical Chinese datasets
- **Key texts**: 论语, 道德经, 庄子, 孟子, 史记, 诗经, 左传, 尚书, 易经, 礼记, 资治通鉴, 红楼梦, 三国演义, 水浒传, 西游记, 唐诗三百首, 宋词三百首, 古文观止
- **License**: Public domain (all pre-1900)
- **Size estimate**: 50-200 MB raw text
- **Refresh**: Static — these texts don't change
- **Value**: Rare/archaic character readings, literary register, classical idiom attestation, coverage for jieba's rare words
- **Action**: Download and chunk

### 7. Jieba Dictionary (reference only)
- **Status**: Stable, not a corpus source
- **Stats**: 349,045 entries in cedict-backfill DB, ~5 MB
- **Refresh**: Rare updates; pypi package version tracks it
- **Note**: Many rare words in jieba overlap with classical Chinese vocabulary — classical texts should provide attestation

## Import Strategy

### Phase A: Quick bootstrap from cedict-backfill DB
1. Parse CC-CEDICT → `cedict` table
2. Export Wikipedia articles from `jieba_candidates.db` → chunk → load
3. Export Baidu Baike → chunk → load
4. Export ChID (strip #idiom# markers) → chunk → load
5. Build FTS5 trigram index + fts5vocab
6. Validate with 68 existing tests + new import tests

### Phase B: News corpus
1. Download news2016zh via Google Drive (3.6 GB compressed)
2. Optionally download THUCNews via HuggingFace
3. Parse JSONL → chunk → load with source tags
4. Rebuild FTS5 index

### Phase C: Classical Chinese collection
1. Download from ctext.org API or Wikisource dumps
2. Source-tag each text (e.g., "classics/论语", "classics/史记")
3. Chunk (classical Chinese uses 。but also shorter clauses with ，)
4. Load and index

### Phase D: Fresh downloads (optional, for reproducibility)
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
| **Total (all)** | **~14 GB** | **~15-18M** | **~28-38 GB** | **~42-52 GB** |

All fits within 785 GB available. Even with both news corpora, under 7% of disk.

## Download Log

| Source | Date | Version/Notes |
|--------|------|---------------|
| CC-CEDICT | 2026-02-24 | 124,260 entries, fresh from mdbg.net |
| Wikipedia | ~2025-12 | Via cedict-backfill import, 1.26M articles |
| Baidu Baike | ~2025-12 | Via cedict-backfill import, 1.62M articles |
| ChID | ~2025-12 | Via cedict-backfill import, 1.12M passages |
| news2016zh | — | Pending download |
| THUCNews | — | Pending download |
| NiuTrans/Classical-Modern | 2026-02-24 | git clone, 327 books + 97 bilingual, 1.3 GB repo, MIT |
| chinese-poetry | 2026-02-24 | git clone, 55K Tang + 260K Song poems + classics, 597 MB repo, MIT |
