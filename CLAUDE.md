# zhcorpus

Chinese corpus MCP search engine — multi-source evidence reports for AI-powered Chinese lexicography.

## Agent Operating Principles

- User authority: never push, deploy, or commit without explicit request
- Task-driven: one task at a time, verify before moving on
- Test-first: write tests before implementation, run tests after every change
- Scope discipline: do what was asked, nothing more

## Tech Stack

- Python 3.11+, SQLite (FTS5 trigram + fts5vocab), numpy
- MCP SDK (`mcp>=1.0.0`) for AI agent access
- pytest for testing

## Commands

```bash
# Run all tests
.venv/bin/pytest tests/ -v

# Run specific test file
.venv/bin/pytest tests/test_fts_chinese.py -v

# Run with coverage
.venv/bin/pytest tests/ --cov=zhcorpus --cov-report=term-missing
```

## Import Commands

```bash
# Full corpus import (Wikipedia + Baike + ChID + CC-CEDICT)
.venv/bin/python tools/import_corpus.py

# Import with a limit (for testing)
.venv/bin/python tools/import_corpus.py --limit 1000

# Download + import THUCNews from HuggingFace
.venv/bin/python tools/download_news.py --thucnews
```

## Verify Your Work

- All tests pass: `.venv/bin/pytest tests/ -v`
- No regressions in existing tests when adding features
- New functionality has corresponding tests

## Project Structure

```
zhcorpus/
├── CLAUDE.md
├── pyproject.toml
├── src/zhcorpus/
│   ├── db.py              # Schema, connection, CRUD
│   ├── report.py          # Word Report builder (core deliverable)
│   ├── ingest/
│   │   ├── chunker.py     # Chinese sentence-level chunking (。！？；)
│   │   ├── cedict_parser.py  # CC-CEDICT file parser
│   │   ├── corpus_extract.py # Extract from cedict-backfill DB
│   │   └── news.py        # THUCNews + news2016zh importers
│   ├── search/
│   │   ├── fts.py         # Trigram FTS5 + fts5vocab expansion
│   │   └── hybrid.py      # (Phase 3: embeddings + RRF)
│   └── mcp/
│       └── server.py      # (Phase 2) MCP stdio server
├── tools/
│   ├── import_corpus.py   # Import from cedict-backfill DB + CC-CEDICT
│   └── download_news.py   # Download + import THUCNews/news2016zh
├── docs/
│   └── corpus-import-plan.md  # Data sources, sizes, download log
├── tests/
│   ├── fixtures/
│   │   └── sample_corpus.py     # Hand-picked Chinese text fixtures
│   ├── test_chunker.py          # 13 tests
│   ├── test_cedict_parser.py    # 11 tests
│   ├── test_corpus_extract.py   # 15 tests
│   ├── test_fts_chinese.py      # 35 tests
│   ├── test_news_import.py      # 10 tests
│   └── test_word_report.py      # 20 tests
└── data/
    ├── raw/               # Source files (gitignored)
    └── artifacts/         # Generated databases (gitignored)
```

## FTS5 Search Architecture

Two-tier approach, no segmenter dependency:
- **3+ char terms**: Direct FTS5 trigram MATCH with BM25 ranking
- **1-2 char terms**: fts5vocab expansion — find all indexed trigrams containing the short term, OR them into one MATCH query, post-filter for exact matches

Key tables: `chunks_fts` (trigram), `chunks_fts_vocab` (fts5vocab exposing the trigram index)

## Key Docs

- tests/fixtures/sample_corpus.py — canonical test data across sources and difficulty tiers
- src/zhcorpus/report.py — the Word Report, the single product we deliver

## Licensing

- SAFE to use: CC-CEDICT (CC BY-SA 4.0), jieba (MIT), CFDICT (CC BY-SA 3.0), HanDeDict (CC BY-SA 2.0), HSK (public)
- DO NOT use CJKI dictionaries (IT/Medical/Civil) from nomad-builder — commercially licensed, likely has canary entries

## Srclight Code Index (MCP)

Call `codebase_map()` at the START of every session before any other work.

## Do NOT

- Do NOT create duplicate scripts — modify existing ones
- Do NOT add features without tests
- Do NOT use unicode61 tokenizer for Chinese text — always trigram
- Do NOT embed full articles — chunk into sentences first
- Do NOT commit data/ files or .db files
- Do NOT use CJKI dictionaries for segmentation or indexing
- Do NOT add a segmenter dependency — trigram + fts5vocab handles all word lengths
