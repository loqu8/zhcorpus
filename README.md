# zhcorpus

Chinese corpus MCP search engine — multi-source evidence reports for AI-powered Chinese lexicography.

Delivers structured, per-source evidence briefs to AI agents via MCP, enabling grounded dictionary entry generation from a 113M-chunk Chinese text corpus spanning encyclopedic, literary, classical, and news registers.

## What It Does

- **Corpus search**: 113M chunks from 34M articles across 8 sources (Wikipedia zh, Baidu Baike, ChID idioms, THUCNews, news2016zh, NiuTrans classical Chinese, chinese-poetry, LCCC)
- **Multilingual dictionary**: 428K headwords with 5.9M definitions in 18 languages (en, de, fr, es, sv, ja, ko, ru, id, vi, tl, fa, nl, pt, ar, th, hi, it)
- **Dialect forms**: 184K Cantonese (Jyutping) + Hokkien (POJ) pronunciation entries
- **Word reports**: Structured per-source evidence briefs combining corpus hits, dictionary definitions, and dialect forms

## Architecture

```
AI Agent (Claude, Cursor, etc.)
  | MCP (SSE on port 8744)
  v
zhcorpus MCP Server (FastMCP + uvicorn)
  | word_report / search_corpus / lookup_word / get_dialect_forms
  v
Search Engine (FTS5 + simple tokenizer)
  |
  v
SQLite
  +-- corpus.db (119 GB) -- chunks, articles, sources, chunks_fts
  +-- dictmaster.db (753 MB) -- headwords, definitions, dialect_forms
```

### FTS5 with simple tokenizer

[simple](https://github.com/wangfenjin/simple) — a native C FTS5 extension for Chinese:
- Each CJK character becomes a separate FTS5 token (character-level tokenization)
- Raw Chinese text goes in, no preprocessing or segmenter needed
- `simple_query()` builds MATCH expressions, `simple_highlight()` for highlighting
- Per-source rowid range sampling for instant BM25 results on any term

### Dictionary languages

All definitions produced by **MiniMax M2.5** via Anthropic-compatible API. Community dictionaries (CC-CEDICT, CFDICT, HanDeDict, CC-CIDICT, JMdict/Wiktextract) used as seed context.

- **12 complete**: en, de, fr, es, sv, ja, ko, ru, id, vi, tl, fa
- **6 planned**: nl, pt, ar, th, hi, it

### Dialect sources

| Dialect | Source | Forms |
|---------|--------|-------|
| Cantonese | CC-Canto (Jyutping) | 126K |
| Hokkien | iTaigi + TaiHua (POJ) | 59K |

## MCP Tools

| Tool | Description |
|------|-------------|
| `word_report(term)` | Full evidence report: definitions + dialects + corpus examples |
| `search_corpus(query)` | Example sentences across all sources |
| `lookup_word(headword)` | Dictionary definitions in 18 languages |
| `get_dialect_forms(headword)` | Cantonese + Hokkien pronunciation |
| `corpus_stats()` | Corpus overview |
| `dictionary_stats()` | Dictionary overview |

## Quick Start

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest tests/ -v
```

### Import corpus

```bash
# Full import (Wikipedia + Baike + ChID + CC-CEDICT)
.venv/bin/python tools/import_corpus.py

# THUCNews from HuggingFace
.venv/bin/python tools/download_news.py --thucnews
```

### Run MCP server

The server runs as a systemd service (`zhcorpus-mcp.service`) on port 8744.

```bash
# Manual start
.venv/bin/python -m zhcorpus.mcp.server
```

## License

MIT
