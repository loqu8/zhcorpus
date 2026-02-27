# zhcorpus

Chinese corpus MCP search engine — multi-source evidence reports for AI-powered Chinese lexicography.

Delivers structured, per-source evidence briefs to AI agents via MCP, enabling grounded dictionary entry generation from a multi-million article Chinese text corpus spanning encyclopedic, literary, classical, and news registers.

## The Problem

When an AI writes a dictionary entry for a Chinese word, it needs corpus evidence: real usage in context, source attribution, register diversity, and disambiguation for polyphonic characters. Existing search (FTS5 with `unicode61`) can't segment Chinese text. A new approach is needed.

## The Solution

**Trigram FTS5 + fts5vocab expansion** — no segmenter dependency.

- Chunks Chinese text into sentences (。！？； boundaries)
- Indexes with FTS5 trigram tokenizer (3-character substring matching)
- For 2-character words (the majority in Chinese), expands via `fts5vocab` to find all trigrams containing the term, then searches with BM25 ranking
- Delivers a structured **Word Report** per term: hit counts per source, best snippets per source, CEDICT cross-reference, register analysis

## Architecture

```
AI Agent (Claude, Cursor, etc.)
  │ MCP (stdio)
  ▼
zhcorpus MCP Server
  │ word_report / search_corpus / corpus_status
  ▼
Search Engine
  ├── FTS5 trigram (3+ char terms) ──┐
  ├── fts5vocab expansion (2 char) ──┤── BM25 ranking
  └── Post-filter (exact match) ─────┘
  │
  ▼
SQLite DB
  ├── chunks (sentence-level)
  ├── chunks_fts (trigram index)
  ├── chunks_fts_vocab (fts5vocab)
  ├── articles / sources
  └── cedict (cross-reference)
```

## Status

**Phase 1 complete**: 68 tests passing across chunking, FTS5 search, and word report generation.

## Quick Start

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest tests/ -v
```

## License

MIT
