"""FTS5 search for Chinese text.

Uses trigram tokenizer for 3+ character terms (substring matching),
with LIKE fallback for 1-2 character terms. Trigram requires queries
of at least 3 characters, but Chinese words are frequently 2 characters
(e.g. 银行, 选任, 长城), so the LIKE fallback is essential.
"""

import sqlite3
from dataclasses import dataclass
from typing import List


# Trigram FTS5 requires at least 3 characters
_MIN_TRIGRAM_CHARS = 3


@dataclass
class SearchResult:
    """A single search result from the corpus."""
    chunk_id: int
    text: str
    source: str
    title: str
    rank: float
    snippet: str


def _fts5_quote(term: str) -> str:
    """Escape a term for safe use in FTS5 trigram MATCH queries."""
    return '"' + term.replace('"', '""') + '"'


def _search_trigram(
    conn: sqlite3.Connection,
    term: str,
    limit: int,
    snippet_tokens: int,
) -> List[SearchResult]:
    """Search using FTS5 trigram (3+ character terms only)."""
    safe_term = _fts5_quote(term)
    rows = conn.execute(
        """
        SELECT
            c.id AS chunk_id,
            c.text,
            s.name AS source,
            a.title,
            chunks_fts.rank AS rank,
            snippet(chunks_fts, 0, '', '', '...', ?) AS snippet
        FROM chunks_fts
        JOIN chunks c ON c.id = chunks_fts.rowid
        JOIN articles a ON a.id = c.article_id
        JOIN sources s ON s.id = a.source_id
        WHERE chunks_fts MATCH ?
        ORDER BY chunks_fts.rank
        LIMIT ?
        """,
        (snippet_tokens, safe_term, limit),
    ).fetchall()
    return [
        SearchResult(
            chunk_id=row["chunk_id"],
            text=row["text"],
            source=row["source"],
            title=row["title"],
            rank=row["rank"],
            snippet=row["snippet"],
        )
        for row in rows
    ]


def _search_like(
    conn: sqlite3.Connection,
    term: str,
    limit: int,
) -> List[SearchResult]:
    """Fallback search using LIKE for short terms (< 3 chars).

    Less efficient than FTS5 but necessary for 1-2 character Chinese words.
    """
    pattern = f"%{term}%"
    rows = conn.execute(
        """
        SELECT
            c.id AS chunk_id,
            c.text,
            s.name AS source,
            a.title,
            0.0 AS rank,
            c.text AS snippet
        FROM chunks c
        JOIN articles a ON a.id = c.article_id
        JOIN sources s ON s.id = a.source_id
        WHERE c.text LIKE ?
        ORDER BY c.char_count ASC
        LIMIT ?
        """,
        (pattern, limit),
    ).fetchall()
    return [
        SearchResult(
            chunk_id=row["chunk_id"],
            text=row["text"],
            source=row["source"],
            title=row["title"],
            rank=row["rank"],
            snippet=row["snippet"],
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

    Uses FTS5 trigram for terms >= 3 characters, LIKE fallback for
    shorter terms. Most Chinese words are 2-4 characters, so both
    paths are exercised regularly.

    Args:
        conn: Database connection.
        term: Chinese term to search for.
        limit: Maximum results.
        snippet_tokens: Context window size for FTS5 snippet extraction.

    Returns:
        List of SearchResult ordered by relevance.
    """
    if len(term) >= _MIN_TRIGRAM_CHARS:
        results = _search_trigram(conn, term, limit, snippet_tokens)
        if results:
            return results
        # Trigram miss — fall through to LIKE
    return _search_like(conn, term, limit)


def count_hits(conn: sqlite3.Connection, term: str) -> int:
    """Count how many chunks contain the term."""
    if len(term) >= _MIN_TRIGRAM_CHARS:
        safe_term = _fts5_quote(term)
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM chunks_fts WHERE chunks_fts MATCH ?",
            (safe_term,),
        ).fetchone()
        n = row["n"] if row else 0
        if n > 0:
            return n
    # Fallback for short terms or trigram miss
    pattern = f"%{term}%"
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM chunks WHERE text LIKE ?",
        (pattern,),
    ).fetchone()
    return row["n"] if row else 0


def count_hits_by_source(conn: sqlite3.Connection, term: str) -> dict:
    """Count hits per source for a term."""
    if len(term) >= _MIN_TRIGRAM_CHARS:
        safe_term = _fts5_quote(term)
        rows = conn.execute(
            """
            SELECT s.name AS source, COUNT(*) AS n
            FROM chunks_fts
            JOIN chunks c ON c.id = chunks_fts.rowid
            JOIN articles a ON a.id = c.article_id
            JOIN sources s ON s.id = a.source_id
            WHERE chunks_fts MATCH ?
            GROUP BY s.name
            ORDER BY n DESC
            """,
            (safe_term,),
        ).fetchall()
        result = {row["source"]: row["n"] for row in rows}
        if result:
            return result
    # Fallback for short terms or trigram miss
    pattern = f"%{term}%"
    rows = conn.execute(
        """
        SELECT s.name AS source, COUNT(*) AS n
        FROM chunks c
        JOIN articles a ON a.id = c.article_id
        JOIN sources s ON s.id = a.source_id
        WHERE c.text LIKE ?
        GROUP BY s.name
        ORDER BY n DESC
        """,
        (pattern,),
    ).fetchall()
    return {row["source"]: row["n"] for row in rows}
