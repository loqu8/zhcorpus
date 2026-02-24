"""FTS5 trigram search for Chinese text.

Uses the trigram tokenizer for all queries. For terms >= 3 characters,
direct FTS5 MATCH. For shorter terms (1-2 chars, common in Chinese),
we expand via fts5vocab: find all indexed trigrams containing the term,
then OR them together. This gives proper BM25 ranking for every query
length — no LIKE table scans needed.
"""

import sqlite3
from dataclasses import dataclass
from typing import List

# Trigram FTS5 requires at least 3 characters for direct MATCH
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


def _expand_short_term(conn: sqlite3.Connection, term: str) -> str:
    """Expand a short term (< 3 chars) into an OR query via fts5vocab.

    Finds all trigrams in the index that contain the short term,
    then builds an OR query so FTS5 can search with BM25 ranking.

    Returns an FTS5 MATCH expression, or empty string if no trigrams found.
    """
    pattern = f"%{term}%"
    rows = conn.execute(
        "SELECT DISTINCT term FROM chunks_fts_vocab WHERE term LIKE ?",
        (pattern,),
    ).fetchall()

    if not rows:
        return ""

    # Build OR query from matching trigrams
    parts = [_fts5_quote(row["term"]) for row in rows]
    return " OR ".join(parts)


def _run_fts_query(
    conn: sqlite3.Connection,
    match_expr: str,
    limit: int,
    snippet_tokens: int,
) -> List[SearchResult]:
    """Execute an FTS5 MATCH query and return results."""
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
        (snippet_tokens, match_expr, limit),
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

    For terms >= 3 characters: direct FTS5 trigram MATCH.
    For shorter terms: expand via fts5vocab into an OR query
    of all trigrams containing the term, preserving BM25 ranking.

    Args:
        conn: Database connection.
        term: Chinese term to search for.
        limit: Maximum results.
        snippet_tokens: Context window size for FTS5 snippet extraction.

    Returns:
        List of SearchResult ordered by BM25 relevance.
    """
    if len(term) >= _MIN_TRIGRAM_CHARS:
        match_expr = _fts5_quote(term)
    else:
        match_expr = _expand_short_term(conn, term)
        if not match_expr:
            return []

    results = _run_fts_query(conn, match_expr, limit, snippet_tokens)

    # Post-filter: ensure the actual term appears in the text.
    # The trigram OR expansion can match chunks where the trigram exists
    # but the 2-char term is split across a different boundary.
    if len(term) < _MIN_TRIGRAM_CHARS:
        results = [r for r in results if term in r.text]

    return results


def count_hits(conn: sqlite3.Connection, term: str) -> int:
    """Count how many chunks contain the term."""
    if len(term) >= _MIN_TRIGRAM_CHARS:
        match_expr = _fts5_quote(term)
    else:
        match_expr = _expand_short_term(conn, term)
        if not match_expr:
            return 0

    row = conn.execute(
        "SELECT COUNT(*) AS n FROM chunks_fts WHERE chunks_fts MATCH ?",
        (match_expr,),
    ).fetchone()
    n = row["n"] if row else 0

    # For short terms, the count may include false positives from
    # trigram expansion. For accuracy, fall back to exact count.
    if len(term) < _MIN_TRIGRAM_CHARS and n > 0:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM chunks WHERE text LIKE ?",
            (f"%{term}%",),
        ).fetchone()
        return row["n"] if row else 0

    return n


def count_hits_by_source(conn: sqlite3.Connection, term: str) -> dict:
    """Count hits per source for a term."""
    if len(term) >= _MIN_TRIGRAM_CHARS:
        match_expr = _fts5_quote(term)
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
            (match_expr,),
        ).fetchall()
        return {row["source"]: row["n"] for row in rows}

    # For short terms, use the fts5vocab expansion for search
    # but verify with exact text match for accurate counts
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
