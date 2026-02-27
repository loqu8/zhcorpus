"""FTS5 search for Chinese text using the 'simple' tokenizer.

The simple tokenizer (github.com/wangfenjin/simple) handles Chinese
character-level tokenization natively in C — each CJK character becomes
a separate FTS5 token. No data transformation needed: raw Chinese text
goes in, simple_query() builds the right MATCH expression.
"""

import sqlite3
from dataclasses import dataclass
from typing import List


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
            simple_snippet(chunks_fts, 0, '', '', '...', ?) AS snippet,
            c.article_id,
            c.chunk_index
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
        List of SearchResult ordered by BM25 relevance.
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


def count_hits(conn: sqlite3.Connection, term: str) -> int:
    """Count how many chunks contain the term."""
    match_expr = conn.execute("SELECT simple_query(?)", (term,)).fetchone()[0]
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM chunks_fts WHERE chunks_fts MATCH ?",
        (match_expr,),
    ).fetchone()
    return row["n"] if row else 0


def count_hits_by_source(conn: sqlite3.Connection, term: str) -> dict:
    """Count hits per source for a term."""
    match_expr = conn.execute("SELECT simple_query(?)", (term,)).fetchone()[0]
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
