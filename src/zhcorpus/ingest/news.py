"""Import news corpus data into zhcorpus.

Supports:
- THUCNews (Tsinghua): HuggingFace `Tongjilibo/THUCNews`
- news2016zh (brightmart): JSONL with news_id, title, content, source, time, keywords

Both are chunked into sentences and loaded with source attribution.
"""

import json
import sqlite3
from pathlib import Path
from typing import Iterator, Tuple

from zhcorpus.db import ensure_source, insert_article, insert_chunk
from zhcorpus.ingest.chunker import chunk_text


# THUCNews category mapping (Chinese -> English label)
THUCNEWS_CATEGORIES = {
    "财经": "finance",
    "彩票": "lottery",
    "房产": "realestate",
    "股票": "stocks",
    "家居": "home",
    "教育": "education",
    "科技": "tech",
    "社会": "society",
    "时尚": "fashion",
    "时政": "politics",
    "体育": "sports",
    "星座": "horoscope",
    "游戏": "gaming",
    "娱乐": "entertainment",
}


def iter_thucnews_hf(dataset) -> Iterator[Tuple[str, str, str]]:
    """Iterate THUCNews from a HuggingFace dataset object.

    Yields (article_id, title, text) tuples.
    The dataset should have 'title' and 'content' columns, plus 'label'.
    """
    for i, row in enumerate(dataset):
        title = row.get("title", "") or ""
        content = row.get("content", "") or ""
        if content.strip():
            yield str(i), title, content


def iter_news2016zh(jsonl_path: Path) -> Iterator[Tuple[str, str, str]]:
    """Iterate news2016zh from a JSONL file.

    Format: {"news_id": "...", "title": "...", "content": "...", "source": "...", ...}
    Yields (article_id, title, text) tuples.
    """
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            news_id = obj.get("news_id", "") or ""
            title = obj.get("title", "") or ""
            content = obj.get("content", "") or ""
            if content.strip():
                yield news_id, title, content


def import_news_iter(
    conn: sqlite3.Connection,
    source_name: str,
    description: str,
    articles_iter: Iterator[Tuple[str, str, str]],
    limit: int = 0,
    batch_size: int = 10000,
    progress_fn=None,
) -> Tuple[int, int]:
    """Import news articles from an iterator into zhcorpus.

    Args:
        conn: zhcorpus database connection.
        source_name: Source name (e.g. "thucnews", "news2016zh").
        description: Description for the source record.
        articles_iter: Iterator yielding (article_id, title, text) tuples.
        limit: Max articles to import (0 = all).
        batch_size: Commit every N articles.
        progress_fn: Optional callback(articles_so_far, chunks_so_far).

    Returns:
        (articles_imported, chunks_imported)
    """
    source_id = ensure_source(conn, source_name, description)

    articles = 0
    chunks = 0

    for article_id, title, text in articles_iter:
        if limit > 0 and articles >= limit:
            break

        if not text.strip():
            continue

        aid = insert_article(conn, source_id, article_id, title, len(text))

        sentences = chunk_text(text)
        for idx, sentence in enumerate(sentences):
            insert_chunk(conn, aid, idx, sentence)
            chunks += 1

        articles += 1

        if articles % batch_size == 0:
            conn.commit()
            if progress_fn:
                progress_fn(articles, chunks)

    conn.commit()

    # Update source counts
    conn.execute(
        "UPDATE sources SET article_count = ?, chunk_count = ? WHERE id = ?",
        (articles, chunks, source_id),
    )
    conn.commit()

    return articles, chunks
