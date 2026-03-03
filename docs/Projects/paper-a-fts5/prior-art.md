# Paper A: FTS5 Chinese Search — Prior Art

## Our Claim
Per-source rowid sampling eliminates BM25 timeout on 100M+ chunk Chinese corpora while preserving source diversity.

## Closest Related Work

### Chinese FTS5 Tokenization
- **Signal's FTS5 extension** (signal-tokenizer): Rust-based CJK tokenizer for FTS5, developed for Signal Messenger's desktop app. Character-level tokenization for CJK, similar approach to wangfenjin/simple but different implementation. Not published academically.
- **wangfenjin/simple tokenizer**: C-based FTS5 extension, character-level tokenization. Well-documented on GitHub (700+ stars) but NOT in academic literature. Our primary tokenizer.
- **APSW UnicodeWordsTokenizer**: Python-based alternative using Unicode segmentation. Academic-adjacent (part of SQLite wrapper library).
- **GRDB Chinese FTS issue**: iOS/macOS Swift library documenting FTS5 Chinese tokenization challenges. Confirms the problem space is real.

### Full-Text Search for Chinese
- **Elasticsearch with ICU/IK analyzers**: Standard industry approach for Chinese FTS. Word-level tokenization (jieba, HanLP). Well-documented but no academic papers on performance at 100M+ Chinese document scale.
- **Meilisearch**: Built-in CJK tokenization. No published benchmarks at our scale.
- **Apache Lucene/Solr**: SmartChineseAnalyzer. Mature but heavy infrastructure.

### Performance Optimization for Large FTS Indexes
- No published work on **per-source rowid sampling** as a technique for avoiding BM25 O(n) scanning.
- General FTS5 optimization: SQLite documentation covers `ORDER BY rank` cost, but no solutions for 100M+ match terms.
- WAND/Block-Max WAND algorithms (Lucene) solve top-k efficiently but are not available in FTS5.

## Novelty Assessment
- **Per-source rowid sampling**: Novel technique. No prior art found.
- **Character-level tokenization for Chinese FTS5**: Implementations exist (Signal, wangfenjin) but no academic treatment.
- **Scale (113M chunks)**: No published FTS5 benchmarks at this scale for Chinese.
- **Weakness**: Niche topic. Hard to place in top NLP venues — better fit for systems/DB conferences or practitioner venues.

## Potential Venues
- VLDB (systems focus), SIGIR (IR focus), practitioner blogs/tech reports
- SQLite community / FTS5 documentation contributions

## Gap Rating: MODERATE
Technique is novel but topic is niche. Limited audience.
