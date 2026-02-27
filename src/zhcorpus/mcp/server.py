"""zhcorpus MCP server — Chinese corpus search + dictionary for AI agents.

Exposes 104M-chunk Chinese corpus, 428K-headword dictionary, and 184K
dialect forms via MCP tools. Follows the srclight/model-radar pattern:
module-level FastMCP instance, lazy DB connections, configure() + run_server().
"""

import os
import sqlite3
import time
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Lazy imports — these touch zhcorpus internals only when actually called
# ---------------------------------------------------------------------------

_INSTRUCTIONS = """\
# zhcorpus — Chinese corpus search engine

Multi-source evidence reports for AI-powered Chinese lexicography.

## Quick Start
1. Call `corpus_stats()` or `dictionary_stats()` to see what's available
2. Use `search_corpus(query)` to find example sentences
3. Use `word_report(term)` for a full evidence report on any Chinese word
4. Use `lookup_word(headword)` for dictionary definitions across 11 languages
5. Use `get_dialect_forms(headword)` for Cantonese + Hokkien pronunciation

## Tool Selection Guide
| Need | Tool |
|------|------|
| Full evidence report | `word_report(term)` |
| Corpus examples | `search_corpus(query, limit)` |
| Dictionary lookup | `lookup_word(headword)` |
| Cantonese/Hokkien | `get_dialect_forms(headword)` |
| Corpus overview | `corpus_stats()` |
| Dictionary overview | `dictionary_stats()` |
| Server health | `server_stats()` |

## Data Sources
- **Corpus**: Wikipedia, Baidu Baike, ChID idioms, THUCNews, news2016zh, NiuTrans classical, chinese-poetry
- **Dictionary**: CC-CEDICT, CFDICT, HanDeDict, CC-CIDICT, Wiktextract, JMdict, MiniMax translations
- **Dialects**: CC-Canto (Cantonese/Jyutping), iTaigi + TaiHua (Hokkien/POJ)
"""

mcp = FastMCP("zhcorpus", instructions=_INSTRUCTIONS)

# ---------------------------------------------------------------------------
# Global state — configured lazily
# ---------------------------------------------------------------------------

_corpus_db_path: Optional[Path] = None
_dict_db_path: Optional[Path] = None
_corpus_conn: Optional[sqlite3.Connection] = None
_dict_conn: Optional[sqlite3.Connection] = None
_server_start_time: Optional[float] = None

_VERSION = "0.2.0"


def _default_corpus_path() -> Path:
    """Default corpus DB path, relative to project root or via env."""
    env = os.environ.get("ZHCORPUS_CORPUS_DB")
    if env:
        return Path(env)
    return Path("data/artifacts/zhcorpus.db")


def _default_dict_path() -> Path:
    """Default dictionary DB path, relative to project root or via env."""
    env = os.environ.get("ZHCORPUS_DICT_DB")
    if env:
        return Path(env)
    return Path("data/artifacts/dictmaster.db")


def _get_corpus_conn() -> sqlite3.Connection:
    """Lazy-init corpus connection (needs libsimple.so)."""
    global _corpus_conn
    if _corpus_conn is None:
        from zhcorpus.db import get_connection
        path = _corpus_db_path or _default_corpus_path()
        _corpus_conn = get_connection(path)
    return _corpus_conn


def _get_dict_conn() -> sqlite3.Connection:
    """Lazy-init dictionary connection (plain SQLite, no FTS5 extension)."""
    global _dict_conn
    if _dict_conn is None:
        path = _dict_db_path or _default_dict_path()
        conn = sqlite3.connect(str(path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        _dict_conn = conn
    return _dict_conn


def configure(
    corpus_db: Optional[Path] = None,
    dict_db: Optional[Path] = None,
) -> None:
    """Configure DB paths. Call before run_server()."""
    global _corpus_db_path, _dict_db_path, _corpus_conn, _dict_conn
    if _corpus_conn is not None:
        _corpus_conn.close()
        _corpus_conn = None
    if _dict_conn is not None:
        _dict_conn.close()
        _dict_conn = None
    _corpus_db_path = corpus_db
    _dict_db_path = dict_db


def configure_test_dbs(
    corpus_conn: sqlite3.Connection,
    dict_conn: Optional[sqlite3.Connection] = None,
) -> None:
    """Inject pre-built connections for testing (in-memory DBs)."""
    global _corpus_conn, _dict_conn
    _corpus_conn = corpus_conn
    if dict_conn is not None:
        _dict_conn = dict_conn


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def word_report(term: str, detail: str = "standard") -> str:
    """Build a multi-source evidence report for a Chinese word.

    Aggregates corpus examples, dictionary definitions, and dialect forms
    into a structured report. This is the flagship tool — use it when you
    need comprehensive evidence about a word's meaning, usage, and variants.

    Args:
        term: Chinese word or phrase to report on.
        detail: Level of detail — "brief" (counts only), "standard"
            (counts + best snippets), or "full" (everything + context).
    """
    from zhcorpus.report import build_word_report

    conn = _get_corpus_conn()
    snippets_per = 2 if detail == "brief" else 3
    context = 0 if detail == "brief" else 2
    limit = 10 if detail == "brief" else 30

    report = build_word_report(
        conn, term, limit=limit,
        snippets_per_source=snippets_per, context_chunks=context,
    )

    # Build structured markdown response
    lines = [f"# Word Report: {term}\n"]

    # Dictionary entries from corpus DB (CEDICT)
    if report.cedict_entries:
        lines.append("## CC-CEDICT Definitions")
        for e in report.cedict_entries:
            lines.append(f"- **{e.traditional}** ({e.pinyin}): {e.definition}")
        lines.append("")

    # Dictionary lookup from dictmaster DB
    try:
        dict_conn = _get_dict_conn()
        defs = _query_definitions(dict_conn, term)
        if defs:
            lines.append("## Dictionary Definitions")
            for d in defs:
                lines.append(f"- [{d['lang']}] {d['definition']} *(source: {d['source']})*")
            lines.append("")

        # Dialect forms
        dialects = _query_dialect_forms(dict_conn, term)
        if dialects:
            lines.append("## Dialect Forms")
            for df in dialects:
                dialect_name = "Cantonese" if df["dialect"] == "yue" else "Hokkien"
                chars = f" ({df['native_chars']})" if df.get("native_chars") else ""
                gloss = f" — {df['gloss']}" if df.get("gloss") else ""
                lines.append(f"- **{dialect_name}**: {df['pronunciation']}{chars}{gloss} *(source: {df['source']})*")
            lines.append("")
    except Exception:
        pass  # dictmaster DB not available — skip silently

    # Corpus evidence
    lines.append(f"## Corpus Evidence ({report.total_hits:,} hits)")
    if report.sources:
        lines.append("| Source | Hits |")
        lines.append("|--------|------|")
        for s in report.sources:
            lines.append(f"| {s.name} | {s.hit_count:,} |")
        lines.append("")

    if detail != "brief" and report.best_snippets:
        lines.append("## Best Examples")
        for i, snip in enumerate(report.best_snippets, 1):
            lines.append(f"**{i}. [{snip['source']}] {snip['title']}**")
            lines.append(f"> {snip['text']}")
            if detail == "full" and snip.get("context"):
                lines.append(f"\n*Context:*\n> {snip['context']}")
            lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def search_corpus(query: str, limit: int = 20) -> str:
    """Search the Chinese corpus for example sentences matching a query.

    Returns BM25-ranked results with source provenance and text snippets.
    Use this to find real-world usage examples of Chinese words and phrases.

    Args:
        query: Chinese word or phrase to search for.
        limit: Maximum number of results (1-100, default 20).
    """
    from zhcorpus.search.fts import search_fts

    conn = _get_corpus_conn()
    limit = max(1, min(100, limit))
    results = search_fts(conn, query, limit=limit)

    if not results:
        return f"No corpus results for '{query}'."

    lines = [f"# Corpus Search: {query} ({len(results)} results)\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"**{i}. [{r.source}] {r.title}** (rank: {r.rank:.2f})")
        lines.append(f"> {r.snippet}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def lookup_word(headword: str) -> str:
    """Look up a Chinese word in the multilingual dictionary.

    Returns definitions from all sources (CC-CEDICT, CFDICT, HanDeDict,
    Wiktextract, JMdict, MiniMax) across up to 11 languages.

    Args:
        headword: Chinese word (simplified or traditional) to look up.
    """
    dict_conn = _get_dict_conn()

    # Find matching headwords
    rows = dict_conn.execute(
        "SELECT id, traditional, simplified, pinyin, pos "
        "FROM headwords WHERE simplified = ? OR traditional = ?",
        (headword, headword),
    ).fetchall()

    if not rows:
        return f"No dictionary entries for '{headword}'."

    lines = [f"# Dictionary: {headword}\n"]
    for hw in rows:
        pos = f" [{hw['pos']}]" if hw["pos"] else ""
        lines.append(f"## {hw['traditional']} / {hw['simplified']} ({hw['pinyin']}){pos}\n")

        defs = dict_conn.execute(
            "SELECT lang, definition, source, confidence "
            "FROM definitions WHERE headword_id = ? ORDER BY lang, source",
            (hw["id"],),
        ).fetchall()

        if defs:
            current_lang = None
            for d in defs:
                if d["lang"] != current_lang:
                    current_lang = d["lang"]
                    lines.append(f"### {current_lang}")
                conf = f" [{d['confidence']}]" if d["confidence"] else ""
                lines.append(f"- {d['definition']} *(source: {d['source']})*{conf}")
            lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def get_dialect_forms(headword: str) -> str:
    """Get Cantonese and Hokkien forms for a Chinese word.

    Returns dialect-specific pronunciation (Jyutping for Cantonese,
    POJ/Tai-lo for Hokkien), alternate characters if different from
    Mandarin, and English glosses where available.

    Args:
        headword: Chinese word (simplified or traditional) to look up.
    """
    dict_conn = _get_dict_conn()
    dialects = _query_dialect_forms(dict_conn, headword)

    if not dialects:
        return f"No dialect forms for '{headword}'."

    lines = [f"# Dialect Forms: {headword}\n"]

    for dialect_code in ["yue", "nan"]:
        dialect_name = "Cantonese" if dialect_code == "yue" else "Hokkien"
        forms = [d for d in dialects if d["dialect"] == dialect_code]
        if forms:
            lines.append(f"## {dialect_name}")
            for f in forms:
                chars = f" — characters: {f['native_chars']}" if f.get("native_chars") else ""
                gloss = f" — {f['gloss']}" if f.get("gloss") else ""
                lines.append(f"- **{f['pronunciation']}**{chars}{gloss} *(source: {f['source']})*")
            lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def corpus_stats() -> str:
    """Get an overview of the Chinese corpus: sources, article/chunk counts, DB size.

    Call this first to understand what data is available.
    """
    conn = _get_corpus_conn()

    sources = conn.execute(
        "SELECT name, article_count, chunk_count FROM sources ORDER BY chunk_count DESC"
    ).fetchall()

    total_articles = sum(s["article_count"] or 0 for s in sources)
    total_chunks = sum(s["chunk_count"] or 0 for s in sources)

    # DB file size
    db_path = _corpus_db_path or _default_corpus_path()
    try:
        size_bytes = Path(db_path).stat().st_size
        if size_bytes > 1_000_000_000:
            size_str = f"{size_bytes / 1_000_000_000:.1f} GB"
        else:
            size_str = f"{size_bytes / 1_000_000:.1f} MB"
    except OSError:
        size_str = "unknown (in-memory)"

    lines = [
        "# Corpus Statistics\n",
        f"- **Articles**: {total_articles:,}",
        f"- **Chunks**: {total_chunks:,}",
        f"- **DB size**: {size_str}",
        "",
        "## Sources",
        "| Source | Articles | Chunks |",
        "|--------|----------|--------|",
    ]
    for s in sources:
        ac = s["article_count"] or 0
        cc = s["chunk_count"] or 0
        lines.append(f"| {s['name']} | {ac:,} | {cc:,} |")

    return "\n".join(lines)


@mcp.tool()
async def dictionary_stats() -> str:
    """Get an overview of the multilingual dictionary: headwords, languages, sources.

    Call this first to understand what dictionary data is available.
    """
    dict_conn = _get_dict_conn()

    headwords = dict_conn.execute("SELECT COUNT(*) FROM headwords").fetchone()[0]
    definitions = dict_conn.execute("SELECT COUNT(*) FROM definitions").fetchone()[0]
    dialect_count = dict_conn.execute("SELECT COUNT(*) FROM dialect_forms").fetchone()[0]

    langs = dict_conn.execute(
        "SELECT lang, COUNT(*) as n FROM definitions GROUP BY lang ORDER BY n DESC"
    ).fetchall()

    sources = dict_conn.execute(
        "SELECT name, entry_count, license FROM sources ORDER BY entry_count DESC"
    ).fetchall()

    lines = [
        "# Dictionary Statistics\n",
        f"- **Headwords**: {headwords:,}",
        f"- **Definitions**: {definitions:,}",
        f"- **Dialect forms**: {dialect_count:,}",
        f"- **Languages**: {len(langs)}",
        "",
        "## Languages",
        "| Language | Definitions |",
        "|----------|-------------|",
    ]
    for l in langs:
        lines.append(f"| {l['lang']} | {l['n']:,} |")

    lines.extend([
        "",
        "## Sources",
        "| Source | Entries | License |",
        "|--------|---------|---------|",
    ])
    for s in sources:
        ec = s["entry_count"] or 0
        lines.append(f"| {s['name']} | {ec:,} | {s['license'] or 'N/A'} |")

    return "\n".join(lines)


@mcp.tool()
async def server_stats() -> str:
    """Return server version, uptime, and configuration.

    Use to check if the server is running and what databases are connected.
    """
    global _server_start_time
    if _server_start_time is None:
        _server_start_time = time.time()

    uptime_s = time.time() - _server_start_time
    if uptime_s < 3600:
        uptime_str = f"{uptime_s / 60:.1f} minutes"
    elif uptime_s < 86400:
        uptime_str = f"{uptime_s / 3600:.1f} hours"
    else:
        uptime_str = f"{uptime_s / 86400:.1f} days"

    corpus_path = str(_corpus_db_path or _default_corpus_path())
    dict_path = str(_dict_db_path or _default_dict_path())

    corpus_ok = _corpus_conn is not None or Path(corpus_path).exists()
    dict_ok = _dict_conn is not None or Path(dict_path).exists()

    lines = [
        "# zhcorpus Server\n",
        f"- **Version**: {_VERSION}",
        f"- **Uptime**: {uptime_str}",
        f"- **Corpus DB**: {corpus_path} ({'connected' if corpus_ok else 'not found'})",
        f"- **Dictionary DB**: {dict_path} ({'connected' if dict_ok else 'not found'})",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal query helpers (reused by tools and web API)
# ---------------------------------------------------------------------------

def _query_definitions(dict_conn: sqlite3.Connection, term: str) -> list[dict]:
    """Look up definitions for a term across all headword matches."""
    rows = dict_conn.execute(
        """
        SELECT d.lang, d.definition, d.source, d.confidence
        FROM definitions d
        JOIN headwords h ON h.id = d.headword_id
        WHERE h.simplified = ? OR h.traditional = ?
        ORDER BY d.lang, d.source
        """,
        (term, term),
    ).fetchall()
    return [dict(r) for r in rows]


def _query_dialect_forms(dict_conn: sqlite3.Connection, term: str) -> list[dict]:
    """Look up dialect forms for a term across all headword matches."""
    rows = dict_conn.execute(
        """
        SELECT df.dialect, df.native_chars, df.pronunciation, df.gloss, df.source
        FROM dialect_forms df
        JOIN headwords h ON h.id = df.headword_id
        WHERE h.simplified = ? OR h.traditional = ?
        ORDER BY df.dialect, df.source
        """,
        (term, term),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------

def create_server() -> FastMCP:
    """Return the MCP server instance."""
    global _server_start_time
    if _server_start_time is None:
        _server_start_time = time.time()
    return mcp


def make_sse_and_streamable_http_app(mount_path: str | None = "/"):
    """Return a Starlette app serving both SSE and Streamable HTTP.

    Cursor tries Streamable HTTP first, then falls back to SSE.
    Serving both on the same port avoids connection failures.
    """
    streamable_app = mcp.streamable_http_app()
    sse_app = mcp.sse_app(mount_path=mount_path)
    sse_routes = [
        r for r in sse_app.routes
        if getattr(r, "path", None) in ("/sse", "/messages")
    ]
    streamable_app.router.routes.extend(sse_routes)
    return streamable_app


def run_server(transport: str = "stdio", port: int = 8743) -> None:
    """Start the MCP server."""
    global _server_start_time
    if _server_start_time is None:
        _server_start_time = time.time()
    if transport in ("sse", "streamable-http"):
        mcp.settings.host = "127.0.0.1"
        mcp.settings.port = port
    mcp.run(transport=transport)


def main() -> None:
    """Entry point for basic stdio mode (no click dependency)."""
    global _server_start_time
    _server_start_time = time.time()
    mcp.run(transport="stdio")
