"""FTS5 search for Chinese text using the 'simple' tokenizer.

The simple tokenizer (github.com/wangfenjin/simple) handles Chinese
character-level tokenization natively in C — each CJK character becomes
a separate FTS5 token. No data transformation needed: raw Chinese text
goes in, simple_query() builds the right MATCH expression.
"""

import sqlite3
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class SearchResult:
    """A single search result from the corpus."""
    chunk_id: int
    text: str
    source: str
    title: str
    rank: float
    snippet: str
    article_id: int = 0
    chunk_index: int = 0


def _get_source_ranges(conn: sqlite3.Connection) -> List[Tuple[str, int, int]]:
    """Get (source_name, min_chunk_id, max_chunk_id) per source.

    Chunk IDs are monotonically assigned during import, so each source
    occupies a contiguous rowid range. This allows per-source FTS5
    queries using `AND rowid BETWEEN ? AND ?` which FTS5 handles
    efficiently via posting-list intersection.

    Reads from the `source_chunk_ranges` table if available (instant).
    Falls back to computing from articles/chunks (slow on large DBs).
    Results are cached on the connection object either way.
    """
    cache = getattr(conn, "_source_ranges", None)
    if cache is not None:
        return cache

    # Try materialized ranges first (instant)
    ranges = _read_source_ranges(conn)
    if not ranges:
        # Compute from articles/chunks (slow first time, ~2s on 34M articles)
        ranges = _compute_source_ranges(conn)

    try:
        conn._source_ranges = ranges  # type: ignore[attr-defined]
    except AttributeError:
        pass  # read-only connection objects
    return ranges


def _read_source_ranges(conn: sqlite3.Connection) -> List[Tuple[str, int, int]]:
    """Read pre-computed source ranges from the database."""
    try:
        rows = conn.execute(
            "SELECT name, min_chunk_id, max_chunk_id "
            "FROM source_chunk_ranges ORDER BY min_chunk_id"
        ).fetchall()
        return [(r["name"], r["min_chunk_id"], r["max_chunk_id"]) for r in rows]
    except sqlite3.OperationalError:
        return []  # table doesn't exist


def _compute_source_ranges(conn: sqlite3.Connection) -> List[Tuple[str, int, int]]:
    """Compute source ranges from articles/chunks tables."""
    sources = conn.execute(
        "SELECT id, name FROM sources ORDER BY id"
    ).fetchall()

    if not sources:
        return []

    ranges = []
    for src in sources:
        sid = src["id"]
        bounds = conn.execute(
            "SELECT MIN(id) AS lo, MAX(id) AS hi FROM articles WHERE source_id = ?",
            (sid,),
        ).fetchone()
        if not bounds or bounds["lo"] is None:
            continue
        lo_row = conn.execute(
            "SELECT MIN(id) AS lo FROM chunks WHERE article_id = ?",
            (bounds["lo"],),
        ).fetchone()
        hi_row = conn.execute(
            "SELECT MAX(id) AS hi FROM chunks WHERE article_id = ?",
            (bounds["hi"],),
        ).fetchone()
        if lo_row and hi_row and lo_row["lo"] is not None:
            ranges.append((src["name"], lo_row["lo"], hi_row["hi"]))

    return ranges


def materialize_source_ranges(conn: sqlite3.Connection) -> int:
    """Pre-compute and persist source chunk ranges for fast startup.

    Call this after importing new data. Creates/replaces the
    `source_chunk_ranges` table with one row per source.
    Returns the number of sources materialized.
    """
    ranges = _compute_source_ranges(conn)
    conn.execute("DROP TABLE IF EXISTS source_chunk_ranges")
    conn.execute("""
        CREATE TABLE source_chunk_ranges (
            name TEXT PRIMARY KEY,
            min_chunk_id INTEGER NOT NULL,
            max_chunk_id INTEGER NOT NULL
        )
    """)
    conn.executemany(
        "INSERT INTO source_chunk_ranges (name, min_chunk_id, max_chunk_id) VALUES (?, ?, ?)",
        ranges,
    )
    conn.commit()
    # Invalidate cache
    try:
        del conn._source_ranges  # type: ignore[attr-defined]
    except AttributeError:
        pass
    return len(ranges)


def _run_fts_query(
    conn: sqlite3.Connection,
    match_expr: str,
    limit: int,
    snippet_tokens: int,
) -> List[SearchResult]:
    """Execute an FTS5 MATCH query and return source-diverse results.

    Uses a three-phase strategy for performance on large corpora
    (112M+ chunks). FTS5 BM25 ranking is O(n) on matching docs —
    a single-char query like 的 matches 100M+ chunks and times out.

    Strategy:
    1. Per-source sampling: for each source, grab a few rowids from
       FTS5 using `MATCH ? AND rowid BETWEEN lo AND hi` (instant —
       FTS5 intersects posting list with rowid range)
    2. JOIN metadata from chunks/articles/sources (instant via PK)
    3. Skip BM25 — results are in posting-list order per source

    This gives source-diverse results in ~2ms total, even for 的.
    """
    source_ranges = _get_source_ranges(conn)

    if not source_ranges:
        # Fallback for empty corpus or in-memory test DBs without ranges
        return _run_fts_query_simple(conn, match_expr, limit, snippet_tokens)

    # Phase 1: per-source rowid sampling (instant per source)
    per_source = max(2, (limit + len(source_ranges) - 1) // len(source_ranges))
    all_rowids = []
    for _name, lo, hi in source_ranges:
        rows = conn.execute(
            "SELECT rowid FROM chunks_fts "
            "WHERE chunks_fts MATCH ? AND rowid BETWEEN ? AND ? LIMIT ?",
            (match_expr, lo, hi, per_source),
        ).fetchall()
        all_rowids.extend(r[0] for r in rows)

    if not all_rowids:
        return []

    placeholders = ",".join("?" * len(all_rowids))

    # Phase 2: plain JOIN on chunk PKs (no FTS5 re-MATCH, instant)
    rows = conn.execute(
        f"""
        SELECT
            c.id AS chunk_id,
            c.text,
            s.name AS source,
            a.title,
            0.0 AS rank,
            substr(c.text, 1, ?) AS snippet,
            c.article_id,
            c.chunk_index
        FROM chunks c
        JOIN articles a ON a.id = c.article_id
        JOIN sources s ON s.id = a.source_id
        WHERE c.id IN ({placeholders})
        LIMIT ?
        """,
        [snippet_tokens * 4] + all_rowids + [limit],
    ).fetchall()

    return [
        SearchResult(
            chunk_id=row["chunk_id"],
            text=row["text"],
            source=row["source"],
            title=row["title"],
            rank=row["rank"],
            snippet=row["snippet"],
            article_id=row["article_id"],
            chunk_index=row["chunk_index"],
        )
        for row in rows
    ]


def _run_fts_query_simple(
    conn: sqlite3.Connection,
    match_expr: str,
    limit: int,
    snippet_tokens: int,
) -> List[SearchResult]:
    """Fallback FTS query for small/test databases without source ranges.

    Used when _get_source_ranges returns empty (in-memory test DBs).
    Same two-phase strategy but without per-source sampling.
    """
    rowid_rows = conn.execute(
        "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ? LIMIT ?",
        (match_expr, limit),
    ).fetchall()

    if not rowid_rows:
        return []

    rowids = [r[0] for r in rowid_rows]
    placeholders = ",".join("?" * len(rowids))

    rows = conn.execute(
        f"""
        SELECT
            c.id AS chunk_id,
            c.text,
            s.name AS source,
            a.title,
            0.0 AS rank,
            substr(c.text, 1, ?) AS snippet,
            c.article_id,
            c.chunk_index
        FROM chunks c
        JOIN articles a ON a.id = c.article_id
        JOIN sources s ON s.id = a.source_id
        WHERE c.id IN ({placeholders})
        LIMIT ?
        """,
        [snippet_tokens * 4] + rowids + [limit],
    ).fetchall()

    return [
        SearchResult(
            chunk_id=row["chunk_id"],
            text=row["text"],
            source=row["source"],
            title=row["title"],
            rank=row["rank"],
            snippet=row["snippet"],
            article_id=row["article_id"],
            chunk_index=row["chunk_index"],
        )
        for row in rows
    ]


def search_fts(
    conn: sqlite3.Connection,
    term: str,
    limit: int = 20,
    snippet_tokens: int = 64,
) -> List[SearchResult]:
    """Search the corpus for a Chinese term.

    Uses simple_query() to build the FTS5 MATCH expression.
    The simple tokenizer handles Chinese character-level tokenization
    natively — no preprocessing needed.

    Args:
        conn: Database connection.
        term: Chinese term to search for.
        limit: Maximum results.
        snippet_tokens: Context window for snippet extraction.

    Returns:
        List of SearchResult in posting-list order (BM25 skipped for perf).
    """
    match_expr = conn.execute(
        "SELECT simple_query(?)", (term,)
    ).fetchone()[0]
    return _run_fts_query(conn, match_expr, limit, snippet_tokens)


@dataclass
class ContextPassage:
    """A chunk with surrounding context from the same article."""
    source: str
    title: str
    hit_text: str
    context: str  # surrounding chunks joined
    hit_index: int  # which chunk in the context contains the hit
    chunk_count: int  # total chunks in the context window


def get_context(
    conn: sqlite3.Connection,
    result: SearchResult,
    before: int = 2,
    after: int = 2,
) -> ContextPassage:
    """Expand a search result to include neighboring chunks.

    Like grep -C: returns the hit chunk plus `before` chunks above
    and `after` chunks below from the same article.

    Args:
        conn: Database connection.
        result: A SearchResult from search_fts.
        before: Number of chunks before the hit to include.
        after: Number of chunks after the hit to include.

    Returns:
        ContextPassage with the hit embedded in surrounding text.
    """
    lo = max(0, result.chunk_index - before)
    hi = result.chunk_index + after

    rows = conn.execute(
        """
        SELECT chunk_index, text
        FROM chunks
        WHERE article_id = ? AND chunk_index BETWEEN ? AND ?
        ORDER BY chunk_index
        """,
        (result.article_id, lo, hi),
    ).fetchall()

    texts = [row["text"] for row in rows]
    indices = [row["chunk_index"] for row in rows]

    # Find where the hit chunk is in the window
    try:
        hit_pos = indices.index(result.chunk_index)
    except ValueError:
        hit_pos = 0

    return ContextPassage(
        source=result.source,
        title=result.title,
        hit_text=result.text,
        context="\n".join(texts),
        hit_index=hit_pos,
        chunk_count=len(texts),
    )


def get_full_article(
    conn: sqlite3.Connection,
    article_id: int,
) -> str:
    """Return all chunks for an article, joined as full text."""
    rows = conn.execute(
        "SELECT text FROM chunks WHERE article_id = ? ORDER BY chunk_index",
        (article_id,),
    ).fetchall()
    return "\n".join(row["text"] for row in rows)


def count_hits(
    conn: sqlite3.Connection, term: str, cap: int = 10_000,
) -> int:
    """Count how many chunks contain the term, capped for performance.

    FTS5 COUNT(*) is O(n) on matching documents. For high-frequency
    terms (的, 学) this means scanning millions of rows. The cap
    ensures consistent sub-second response times. Returns the cap
    value when the actual count exceeds it.
    """
    match_expr = conn.execute("SELECT simple_query(?)", (term,)).fetchone()[0]
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM "
        "(SELECT 1 FROM chunks_fts WHERE chunks_fts MATCH ? LIMIT ?)",
        (match_expr, cap),
    ).fetchone()
    return row["n"] if row else 0


def count_hits_by_source(
    conn: sqlite3.Connection, term: str, cap_per_source: int = 1_000,
) -> dict:
    """Count hits per source for a term, capped per source.

    Uses per-source FTS5 queries with rowid ranges (from materialized
    source_chunk_ranges table) to get representative counts from each
    source independently. This avoids the posting-list bias where a
    global LIMIT sample comes entirely from the first-imported source.

    For rare terms (< cap_per_source matches in a source), count is exact.
    For common terms, returns the cap value for that source.
    """
    match_expr = conn.execute("SELECT simple_query(?)", (term,)).fetchone()[0]
    source_ranges = _get_source_ranges(conn)

    if not source_ranges:
        # Fallback for DBs without materialized ranges
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM "
            "(SELECT 1 FROM chunks_fts WHERE chunks_fts MATCH ? LIMIT ?)",
            (match_expr, cap_per_source),
        ).fetchone()
        return {"unknown": row["n"]} if row and row["n"] > 0 else {}

    result = {}
    for name, lo, hi in source_ranges:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM "
            "(SELECT 1 FROM chunks_fts "
            " WHERE chunks_fts MATCH ? AND rowid BETWEEN ? AND ? LIMIT ?)",
            (match_expr, lo, hi, cap_per_source),
        ).fetchone()
        n = row["n"] if row else 0
        if n > 0:
            result[name] = n

    # Sort by count descending
    return dict(sorted(result.items(), key=lambda x: -x[1]))
