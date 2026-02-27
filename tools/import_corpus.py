#!/usr/bin/env python3
"""Import corpus data into zhcorpus database.

Usage:
    # Import everything from cedict-backfill + CC-CEDICT:
    python tools/import_corpus.py

    # Import only specific sources:
    python tools/import_corpus.py --sources wikipedia baidu_baike

    # Import with a limit (for testing):
    python tools/import_corpus.py --limit 1000

    # Specify output database:
    python tools/import_corpus.py --db data/artifacts/zhcorpus.db
"""

import argparse
import sqlite3
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from zhcorpus.db import get_connection, init_db
from zhcorpus.ingest.cedict_parser import load_cedict
from zhcorpus.ingest.corpus_extract import import_source, SOURCE_MAP


BACKFILL_DB = Path("/home/tim/Projects/loqu8/cedict-backfill/data/artifacts/jieba_candidates.db")
CEDICT_FILE = Path(__file__).parent.parent / "data" / "raw" / "cedict_1_0_ts_utf-8_mdbg.txt"
DEFAULT_DB = Path(__file__).parent.parent / "data" / "artifacts" / "zhcorpus.db"

SOURCE_DESCRIPTIONS = {
    "wikipedia": "Chinese Wikipedia (zhwiki)",
    "baidu_baike": "Baidu Baike encyclopedia",
    "chid_train": "ChID Chinese Idiom Dataset (train split)",
    "chid_test": "ChID Chinese Idiom Dataset (test split)",
    "chid_validation": "ChID Chinese Idiom Dataset (validation split)",
}

ALL_SOURCES = ["wikipedia", "baidu_baike", "chid_train", "chid_test", "chid_validation"]


def progress(source: str, start_time: float):
    """Return a progress callback for a source."""
    def callback(articles, chunks):
        elapsed = time.time() - start_time
        rate = articles / elapsed if elapsed > 0 else 0
        print(f"  [{source}] {articles:,} articles, {chunks:,} chunks "
              f"({rate:,.0f} articles/sec)")
    return callback


def main():
    parser = argparse.ArgumentParser(description="Import corpus into zhcorpus database")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB,
                        help="Output database path")
    parser.add_argument("--backfill-db", type=Path, default=BACKFILL_DB,
                        help="cedict-backfill database path")
    parser.add_argument("--cedict", type=Path, default=CEDICT_FILE,
                        help="CC-CEDICT file path")
    parser.add_argument("--sources", nargs="+", choices=ALL_SOURCES,
                        default=ALL_SOURCES, help="Sources to import")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max articles per source (0 = all)")
    parser.add_argument("--batch-size", type=int, default=10000,
                        help="Commit every N articles")
    parser.add_argument("--skip-cedict", action="store_true",
                        help="Skip CC-CEDICT import")
    args = parser.parse_args()

    # Ensure output directory exists
    args.db.parent.mkdir(parents=True, exist_ok=True)

    print(f"Output database: {args.db}")
    print(f"Backfill database: {args.backfill_db}")
    print()

    # Connect to zhcorpus
    conn = get_connection(args.db)
    # Performance tuning for bulk import
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA cache_size=-512000")  # 512MB cache
    init_db(conn)

    # 1. Load CC-CEDICT
    if not args.skip_cedict:
        if args.cedict.exists():
            print(f"Loading CC-CEDICT from {args.cedict}...")
            t0 = time.time()
            count = load_cedict(conn, args.cedict)
            elapsed = time.time() - t0
            print(f"  Loaded {count:,} entries in {elapsed:.1f}s")
            print()
        else:
            print(f"WARNING: CC-CEDICT not found at {args.cedict}")
            print()

    # 2. Import corpus sources
    if not args.backfill_db.exists():
        print(f"ERROR: cedict-backfill database not found at {args.backfill_db}")
        sys.exit(1)

    src_conn = sqlite3.connect(str(args.backfill_db))
    src_conn.row_factory = sqlite3.Row

    total_articles = 0
    total_chunks = 0

    for source in args.sources:
        desc = SOURCE_DESCRIPTIONS.get(source, source)
        limit_str = f" (limit {args.limit:,})" if args.limit else ""
        print(f"Importing {source}{limit_str}...")

        t0 = time.time()
        articles, chunks = import_source(
            conn, src_conn, source, desc,
            limit=args.limit,
            batch_size=args.batch_size,
            progress_fn=progress(source, t0),
        )
        elapsed = time.time() - t0

        total_articles += articles
        total_chunks += chunks
        print(f"  Done: {articles:,} articles, {chunks:,} chunks in {elapsed:.1f}s")
        print()

    src_conn.close()

    # 3. Summary
    print("=" * 60)
    print(f"Import complete!")
    print(f"  Total articles: {total_articles:,}")
    print(f"  Total chunks:   {total_chunks:,}")
    print()

    # Database stats
    for row in conn.execute(
        "SELECT name, article_count, chunk_count FROM sources ORDER BY chunk_count DESC"
    ).fetchall():
        print(f"  {row['name']:20s}  {row['article_count']:>10,} articles  {row['chunk_count']:>10,} chunks")

    cedict_count = conn.execute("SELECT COUNT(*) FROM cedict").fetchone()[0]
    print(f"\n  CC-CEDICT entries: {cedict_count:,}")

    # Database file size
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.close()

    if args.db.exists():
        size_mb = args.db.stat().st_size / (1024 * 1024)
        print(f"\n  Database size: {size_mb:,.1f} MB")


if __name__ == "__main__":
    main()
