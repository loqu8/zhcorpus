#!/usr/bin/env python3
"""Import classical Chinese texts into zhcorpus.

Usage:
    # Import from both repos:
    python tools/import_classics.py

    # Import with a limit:
    python tools/import_classics.py --limit 1000

    # Specify paths:
    python tools/import_classics.py --niutrans data/raw/Classical-Modern --poetry data/raw/chinese-poetry
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from zhcorpus.db import get_connection, init_db
from zhcorpus.ingest.classics import import_classics

DEFAULT_DB = Path(__file__).parent.parent / "data" / "artifacts" / "zhcorpus.db"
DEFAULT_NIUTRANS = Path(__file__).parent.parent / "data" / "raw" / "Classical-Modern"
DEFAULT_POETRY = Path(__file__).parent.parent / "data" / "raw" / "chinese-poetry"


def progress(start_time: float):
    def callback(articles, chunks):
        elapsed = time.time() - start_time
        rate = articles / elapsed if elapsed > 0 else 0
        print(f"  {articles:,} articles, {chunks:,} chunks ({rate:,.0f} articles/sec)")
    return callback


def main():
    parser = argparse.ArgumentParser(description="Import classical Chinese texts")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--niutrans", type=Path, default=DEFAULT_NIUTRANS)
    parser.add_argument("--poetry", type=Path, default=DEFAULT_POETRY)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    args.db.parent.mkdir(parents=True, exist_ok=True)

    conn = get_connection(args.db)
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA cache_size=-512000")
    init_db(conn)

    niutrans = args.niutrans if args.niutrans.exists() else None
    poetry = args.poetry if args.poetry.exists() else None

    if not niutrans and not poetry:
        print("ERROR: Neither NiuTrans nor chinese-poetry repos found.")
        print(f"  Expected: {args.niutrans}")
        print(f"  Expected: {args.poetry}")
        print("\nClone them with:")
        print("  git clone https://github.com/NiuTrans/Classical-Modern.git data/raw/Classical-Modern")
        print("  git clone https://github.com/chinese-poetry/chinese-poetry.git data/raw/chinese-poetry")
        sys.exit(1)

    print(f"Output: {args.db}")
    if niutrans:
        print(f"NiuTrans: {niutrans}")
    if poetry:
        print(f"Poetry: {poetry}")
    print()

    t0 = time.time()
    articles, chunks = import_classics(
        conn,
        niutrans_dir=niutrans,
        poetry_dir=poetry,
        limit=args.limit,
        progress_fn=progress(t0),
    )
    elapsed = time.time() - t0

    print(f"\nDone: {articles:,} articles, {chunks:,} chunks in {elapsed:.0f}s")

    # Summary
    print("\n" + "=" * 60)
    for row in conn.execute(
        "SELECT name, article_count, chunk_count FROM sources ORDER BY chunk_count DESC"
    ).fetchall():
        print(f"  {row['name']:20s}  {row['article_count']:>10,} articles  {row['chunk_count']:>10,} chunks")

    conn.execute("PRAGMA synchronous=NORMAL")
    conn.close()

    db_size = args.db.stat().st_size / (1024 * 1024)
    print(f"\n  Database size: {db_size:,.1f} MB")


if __name__ == "__main__":
    main()
