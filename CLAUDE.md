# zhcorpus

Chinese corpus MCP search engine — multi-source evidence reports for AI-powered Chinese lexicography.

## Agent Operating Principles

- User authority: never push, deploy, or commit without explicit request
- Task-driven: one task at a time, verify before moving on
- Test-first: write tests before implementation, run tests after every change
- Scope discipline: do what was asked, nothing more

## Tech Stack

- Python 3.11+, SQLite (FTS5 trigram), numpy
- MCP SDK (`mcp>=1.0.0`) for AI agent access
- Ollama + qwen3-embedding for semantic search (Phase 2)
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
│   │   ├── chunker.py     # Chinese sentence-level chunking
│   │   ├── wikipedia.py   # Wikipedia XML dump importer
│   │   └── baike.py       # Baidu Baike JSONL importer
│   ├── search/
│   │   ├── fts.py         # Trigram FTS5 search
│   │   └── hybrid.py      # (Phase 2: embeddings + RRF)
│   └── mcp/
│       └── server.py      # MCP stdio server
├── tests/
│   ├── fixtures/
│   │   └── sample_corpus.py  # Hand-picked Chinese text fixtures
│   ├── test_chunker.py
│   ├── test_fts_chinese.py
│   └── test_word_report.py
└── data/
    ├── raw/               # Source files (gitignored)
    └── artifacts/         # Generated databases (gitignored)
```

## Key Docs

- tests/fixtures/sample_corpus.py — canonical test data across sources and difficulty tiers
- src/zhcorpus/report.py — the Word Report, the single product we deliver

## Srclight Code Index (MCP)

Call `codebase_map()` at the START of every session before any other work.

## Do NOT

- Do NOT create duplicate scripts — modify existing ones
- Do NOT add features without tests
- Do NOT use unicode61 tokenizer for Chinese text — always trigram
- Do NOT embed full articles — chunk into sentences first
- Do NOT commit data/ files or .db files
