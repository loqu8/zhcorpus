#!/usr/bin/env python3
"""Download and import news corpora into zhcorpus.

Usage:
    # Download THUCNews from HuggingFace and import:
    python tools/download_news.py --thucnews

    # Import news2016zh from a local JSONL file:
    python tools/download_news.py --news2016zh data/raw/news2016zh.json

    # Both with a limit:
    python tools/download_news.py --thucnews --limit 10000
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from zhcorpus.db import get_connection, init_db
from zhcorpus.ingest.news import (
    import_news_iter,
    iter_news2016zh,
    iter_thucnews_hf,
)

DEFAULT_DB = Path(__file__).parent.parent / "data" / "artifacts" / "zhcorpus.db"


def progress(source: str, start_time: float):
    def callback(articles, chunks):
        elapsed = time.time() - start_time
        rate = articles / elapsed if elapsed > 0 else 0
        print(f"  [{source}] {articles:,} articles, {chunks:,} chunks "
              f"({rate:,.0f} articles/sec)")
    return callback


def main():
    parser = argparse.ArgumentParser(description="Download and import news corpora")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--thucnews", action="store_true",
                        help="Download THUCNews from HuggingFace")
    parser.add_argument("--news2016zh", type=Path, default=None,
                        help="Path to news2016zh JSONL file")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max articles per source (0 = all)")
    parser.add_argument("--batch-size", type=int, default=10000)
    args = parser.parse_args()

    if not args.thucnews and not args.news2016zh:
        parser.error("Specify at least one of --thucnews or --news2016zh")

    conn = get_connection(args.db)
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA cache_size=-512000")
    init_db(conn)

    if args.thucnews:
        print("Downloading THUCNews from HuggingFace...")
        print("  Dataset: Tongjilibo/THUCNews (~3.6 GB)")
        t0 = time.time()

        from datasets import load_dataset
        dataset = load_dataset("Tongjilibo/THUCNews", split="train")

        dl_time = time.time() - t0
        print(f"  Downloaded in {dl_time:.0f}s ({len(dataset):,} articles)")

        print("Importing THUCNews...")
        t0 = time.time()
        articles, chunks = import_news_iter(
            conn, "thucnews",
            "THUCNews (Tsinghua): Sina News 2005-2011, 14 categories",
            iter_thucnews_hf(dataset),
            limit=args.limit,
            batch_size=args.batch_size,
            progress_fn=progress("thucnews", t0),
        )
        elapsed = time.time() - t0
        print(f"  Done: {articles:,} articles, {chunks:,} chunks in {elapsed:.0f}s")

    if args.news2016zh:
        if not args.news2016zh.exists():
            print(f"ERROR: File not found: {args.news2016zh}")
            sys.exit(1)

        print(f"Importing news2016zh from {args.news2016zh}...")
        t0 = time.time()
        articles, chunks = import_news_iter(
            conn, "news2016zh",
            "brightmart news2016zh: 63K media sources, 2014-2016",
            iter_news2016zh(args.news2016zh),
            limit=args.limit,
            batch_size=args.batch_size,
            progress_fn=progress("news2016zh", t0),
        )
        elapsed = time.time() - t0
        print(f"  Done: {articles:,} articles, {chunks:,} chunks in {elapsed:.0f}s")

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
