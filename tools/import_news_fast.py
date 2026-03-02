#!/usr/bin/env python3
"""Fast news2016zh import — drops FTS triggers during import, rebuilds after.

The FTS5 triggers cause O(log n) WAL growth per chunk insert on a 121M+ row
index, making a 2.4M article import take days.  This script:

  1. Drops FTS triggers
  2. Imports all articles (INSERT OR IGNORE — safe to re-run)
  3. Rebuilds FTS index from the content table
  4. Recreates triggers
  5. Rematerializes source_chunk_ranges

Usage:
    python tools/import_news_fast.py data/raw/news2016zh/news2016zh_train.json
    python tools/import_news_fast.py data/raw/news2016zh/news2016zh_train.json data/raw/news2016zh/news2016zh_valid.json
"""

import argparse
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from zhcorpus.db import get_connection, ensure_source, insert_article, insert_chunk
from zhcorpus.ingest.news import iter_news2016zh
from zhcorpus.search.fts import materialize_source_ranges

DEFAULT_DB = Path(__file__).parent.parent / "data" / "artifacts" / "zhcorpus.db"
BATCH_SIZE = 10_000


def main():
    parser = argparse.ArgumentParser(description="Fast news2016zh import (trigger-free)")
    parser.add_argument("files", type=Path, nargs="+", help="news2016zh JSONL files")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()

    for f in args.files:
        if not f.exists():
            print(f"ERROR: {f} not found")
            return 1

    conn = get_connection(args.db)
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA cache_size=-512000")

    # Step 1: Drop FTS triggers
    print("Step 1: Dropping FTS triggers...")
    conn.executescript("""
        DROP TRIGGER IF EXISTS chunks_ai;
        DROP TRIGGER IF EXISTS chunks_ad;
        DROP TRIGGER IF EXISTS chunks_au;
    """)
    print("  Done")

    # Step 2: Import articles
    print("Step 2: Importing articles...")
    source_id = ensure_source(conn, "news2016zh",
                              "brightmart news2016zh: 63K media sources, 2014-2016")

    total_articles = 0
    total_chunks = 0
    t0 = time.time()

    for filepath in args.files:
        print(f"\n  File: {filepath.name}")
        file_articles = 0
        file_chunks = 0

        for article_id, title, text in iter_news2016zh(filepath):
            if not text.strip():
                continue

            aid = insert_article(conn, source_id, article_id, title, len(text))

            from zhcorpus.ingest.chunker import chunk_text
            sentences = chunk_text(text)
            for idx, sentence in enumerate(sentences):
                insert_chunk(conn, aid, idx, sentence)
                file_chunks += 1

            file_articles += 1
            total_articles += 1

            if file_articles % BATCH_SIZE == 0:
                conn.commit()
                elapsed = time.time() - t0
                rate = total_articles / elapsed if elapsed > 0 else 0
                print(f"    [{total_articles:,} articles, {total_chunks + file_chunks:,} chunks] "
                      f"({rate:,.0f} art/s)")

        conn.commit()
        total_chunks += file_chunks
        elapsed = time.time() - t0
        print(f"  File done: {file_articles:,} articles, {file_chunks:,} chunks")

    elapsed = time.time() - t0
    print(f"\n  Total: {total_articles:,} articles, {total_chunks:,} chunks in {elapsed:.0f}s")

    # Update source counts
    actual = conn.execute("""
        SELECT COUNT(DISTINCT a.id) as articles,
               (SELECT COUNT(*) FROM chunks c JOIN articles a2
                ON c.article_id = a2.id WHERE a2.source_id = ?) as chunks
        FROM articles a WHERE a.source_id = ?
    """, (source_id, source_id)).fetchone()
    conn.execute("UPDATE sources SET article_count = ?, chunk_count = ? WHERE id = ?",
                 (actual[0], actual[1], source_id))
    conn.commit()
    print(f"  Source metadata updated: {actual[0]:,} articles, {actual[1]:,} chunks")

    # Step 3: Rebuild FTS index
    total_row = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    print(f"\nStep 3: Rebuilding FTS index ({total_row:,} chunks)...")
    print("  This will take a while...")
    t0 = time.time()
    conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES ('rebuild')")
    conn.commit()
    elapsed = time.time() - t0
    rate = total_row / elapsed if elapsed > 0 else 0
    print(f"  Done in {elapsed:.0f}s ({rate:,.0f} chunks/sec)")

    # Step 4: Recreate triggers
    print("\nStep 4: Recreating FTS triggers...")
    conn.executescript("""
        CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
            INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
        END;
        CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
        END;
        CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
            INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
        END;
    """)
    print("  Done")

    # Step 5: Rematerialize source ranges
    print("\nStep 5: Rematerializing source_chunk_ranges...")
    n = materialize_source_ranges(conn)
    print(f"  {n} sources materialized")

    # Step 6: Checkpoint WAL
    print("\nStep 6: WAL checkpoint...")
    conn.execute("PRAGMA synchronous=NORMAL")
    r = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
    print(f"  Checkpoint: busy={r[0]}, log={r[1]}, checkpointed={r[2]}")

    conn.close()
    db_size = args.db.stat().st_size / (1024**3)
    print(f"\nDatabase size: {db_size:.1f} GB")
    print("Done!")
    return 0


if __name__ == "__main__":
    exit(main())
