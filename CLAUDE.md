# zhcorpus

Chinese corpus MCP search engine — multi-source evidence reports for AI-powered Chinese lexicography.

## Agent Operating Principles

- User authority: never push, deploy, or commit without explicit request
- Task-driven: one task at a time, verify before moving on
- Test-first: write tests before implementation, run tests after every change
- Scope discipline: do what was asked, nothing more

## Tech Stack

- Python 3.11+, SQLite FTS5 with [simple tokenizer](https://github.com/wangfenjin/simple), numpy
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
│   │   ├── fts.py         # FTS5 search with simple tokenizer
│   │   └── hybrid.py      # (Phase 3: embeddings + RRF)
│   └── mcp/
│       └── server.py      # (Phase 2) MCP stdio server
├── tools/
│   ├── import_corpus.py   # Import from cedict-backfill DB + CC-CEDICT
│   ├── download_news.py   # Download + import THUCNews/news2016zh
│   └── dictmaster/
│       ├── build_master.py       # Orchestrator: parse → merge → translate → export
│       ├── backfill_langs.py     # Context-aware backfill for missing languages
│       └── translate/            # Translation backends (minimax, groq, ollama)
├── docs/
│   ├── corpus-import-plan.md         # Data sources, sizes, download log
│   ├── translation-model-eval.md     # LLM model comparison for translation
│   └── translation-backfill-plan.md  # Backfill strategy and results
├── tests/
│   ├── fixtures/
│   │   └── sample_corpus.py     # Hand-picked Chinese text fixtures
│   ├── test_chunker.py          # 13 tests
│   ├── test_cedict_parser.py    # 11 tests
│   ├── test_corpus_extract.py   # 15 tests
│   ├── test_fts_chinese.py      # 46 tests
│   ├── test_news_import.py      # 10 tests
│   └── test_word_report.py      # 20 tests
└── data/
    ├── raw/               # Source files (gitignored)
    └── artifacts/         # Generated databases (gitignored)
```

## FTS5 Search Architecture

[simple tokenizer](https://github.com/wangfenjin/simple) — native C FTS5 extension for Chinese:
- Each CJK character becomes a separate FTS5 token (character-level tokenization in C)
- Raw Chinese text goes in, no preprocessing needed
- `simple_query()` builds the right MATCH expression at query time
- `simple_highlight()` / `simple_snippet()` for proper Chinese highlighting
- Optional jieba integration for word-level matching via `jieba_query()`
- Content table with triggers — standard FTS5 sync, `rebuild` command works
- BM25 ranking for all queries

Key tables: `chunks_fts` (FTS5 with `tokenize='simple'`), `chunks_fts_vocab` (fts5vocab), `chunks` (content table)

Extension: `lib/libsimple-linux-ubuntu-latest/libsimple.so` — loaded in `get_connection()`

**History**: Trigram (12x bloat, multi-minute queries) → plain unicode61 (CJK runs = single tokens, broken) → space-separation (works but transforms data) → simple tokenizer (native, clean, correct).

## Key Docs

- tests/fixtures/sample_corpus.py — canonical test data across sources and difficulty tiers
- src/zhcorpus/report.py — the Word Report, the single product we deliver

## Licensing

- SAFE to use: CC-CEDICT (CC BY-SA 4.0), jieba (MIT), CFDICT (CC BY-SA 3.0), HanDeDict (CC BY-SA 2.0), HSK (public)
- DO NOT use CJKI dictionaries (IT/Medical/Civil) from nomad-builder — commercially licensed, likely has canary entries

## MCP argument validation (vendored mcpkit)

Unknown tool arguments are **refused**, not silently dropped. The zhcorpus MCP server vendors the
shared `mcpkit` guard as one hash-verified file (`src/zhcorpus/mcp/_mcpkit.py`, mcpkit 0.2.1):
`StrictArgsMCP` rejects any argument a tool does not declare and stamps `additionalProperties:
false` on the advertised schema. Regenerate / verify:

```bash
python -m mcpkit.vendor --out src/zhcorpus/mcp/_mcpkit.py    # regenerate from upstream
python -m mcpkit.vendor --check src/zhcorpus/mcp/_mcpkit.py   # verify unmodified + current
```

**For AI agents:** a tool call that returns `unknown argument(s): … running older code than you
think … reconnect` does **not** mean your arguments are wrong in general — *this running server
process* does not implement them (a long-lived daemon serves the code it launched with). Nothing
ran. Check the server's reported revision and reconnect the MCP; do not retry against the same
process.

## Srclight Code Index (MCP)

Call `codebase_map()` at the START of every session before any other work.

## Conductor

This repo is monitored by the [Loqu8 Conductor](https://github.com/loqu8/conductor) for automated agent orchestration.

When you are spawned by the conductor to work on an issue:
1. Call `acknowledge()` — claims the issue and posts a comment
2. Call `my_assignment()` — returns the full issue body, comments, and labels
3. Work on the task. Post milestone updates with `update_progress(milestone)`
4. If blocked: call `report_blocked(reason)` — adds label, notifies dispatcher
5. When done: call `complete(summary)` — posts summary and closes the issue

These tools are available via the conductor MCP server. If you were spawned by conductor, `repo` and `issue_number` default from environment variables — no args needed.

## Do NOT

- Do NOT create duplicate scripts — modify existing ones
- Do NOT add features without tests
- Do NOT use trigram or plain unicode61 for Chinese FTS5 — use the simple tokenizer
- Do NOT embed full articles — chunk into sentences first
- Do NOT commit data/ files or .db files
- Do NOT use CJKI dictionaries for segmentation or indexing
- Do NOT add a segmenter dependency — simple tokenizer handles character-level tokenization natively
