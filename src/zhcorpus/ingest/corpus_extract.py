"""Extract corpus data from cedict-backfill's jieba_candidates.db.

The cedict-backfill database has a `corpus_texts` table with columns:
    id, source, source_id, title, text, metadata, created_at

Sources: wikipedia, baidu_baike, chid_train, chid_test, chid_validation

This module extracts articles and imports them into zhcorpus,
chunking them into sentences along the way.
"""

import re
import sqlite3
from pathlib import Path
from typing import Iterator, Tuple

from zhcorpus.db import (
    content_hash,
    ensure_source,
    insert_article,
    insert_chunk,
)
from zhcorpus.ingest.chunker import chunk_text

# Map cedict-backfill source names to zhcorpus source names
SOURCE_MAP = {
    "wikipedia": "wikipedia",
    "baidu_baike": "baidu_baike",
    "chid_train": "chid",
    "chid_test": "chid",
    "chid_validation": "chid",
}

# ChID has #idiom# markers that need stripping
_IDIOM_MARKER = re.compile(r"#idiom\d*#")


def _clean_chid_text(text: str) -> str:
    """Strip #idiom# fill-in-the-blank markers from ChID text."""
    return _IDIOM_MARKER.sub("", text)


def iter_source_articles(
    src_conn: sqlite3.Connection,
    source: str,
    limit: int = 0,
) -> Iterator[Tuple[str, str, str]]:
    """Iterate over articles from a source in the cedict-backfill DB.

    Yields (source_id, title, text) tuples.
    """
    query = "SELECT id, title, text FROM corpus_texts WHERE source = ?"
    params: list = [source]
    if limit > 0:
        query += " LIMIT ?"
        params.append(limit)

    cursor = src_conn.execute(query, params)
    while True:
        rows = cursor.fetchmany(1000)
        if not rows:
            break
        for row in rows:
            article_id = str(row[0])
            title = row[1] or ""
            text = row[2] or ""
            if source.startswith("chid"):
                text = _clean_chid_text(text)
            yield article_id, title, text


def import_source(
    dest_conn: sqlite3.Connection,
    src_conn: sqlite3.Connection,
    source_name: str,
    description: str = "",
    limit: int = 0,
    batch_size: int = 10000,
    progress_fn=None,
) -> Tuple[int, int]:
    """Import a source from cedict-backfill into zhcorpus.

    Args:
        dest_conn: zhcorpus database connection.
        src_conn: cedict-backfill database connection (read-only).
        source_name: Source name in cedict-backfill (e.g. "wikipedia").
        description: Description for the source record.
        limit: Max articles to import (0 = all).
        batch_size: Commit every N articles.
        progress_fn: Optional callback(articles_so_far, chunks_so_far).

    Returns:
        (articles_imported, chunks_imported)
    """
    zhcorpus_source = SOURCE_MAP.get(source_name, source_name)
    source_id = ensure_source(dest_conn, zhcorpus_source, description)

    articles = 0
    chunks = 0

    for article_id, title, text in iter_source_articles(src_conn, source_name, limit):
        if not text.strip():
            continue

        aid = insert_article(dest_conn, source_id, article_id, title, len(text))

        sentences = chunk_text(text)
        for idx, sentence in enumerate(sentences):
            insert_chunk(dest_conn, aid, idx, sentence)
            chunks += 1

        articles += 1

        if articles % batch_size == 0:
            dest_conn.commit()
            if progress_fn:
                progress_fn(articles, chunks)

    dest_conn.commit()

    # Update source counts
    dest_conn.execute(
        "UPDATE sources SET article_count = ?, chunk_count = ? WHERE id = ?",
        (articles, chunks, source_id),
    )
    dest_conn.commit()

    return articles, chunks
