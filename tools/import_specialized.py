#!/usr/bin/env python3
"""Import all specialized domain corpora into zhcorpus.

Usage:
    # Import everything:
    python tools/import_specialized.py

    # Import specific sources:
    python tools/import_specialized.py --sources webtext2019zh,cail2018,csl

    # Import with a limit per source:
    python tools/import_specialized.py --limit 1000

    # List available sources:
    python tools/import_specialized.py --list
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from zhcorpus.db import get_connection, init_db
from zhcorpus.ingest.specialized import (
    import_baike2018qa,
    import_cail2018,
    import_cmedqa2,
    import_csl,
    import_lccc,
    import_laws,
    import_medical_dialogues,
    import_subtitles,
    import_translation2019zh,
    import_webtext2019zh,
)

DEFAULT_DB = Path(__file__).parent.parent / "data" / "artifacts" / "zhcorpus.db"
RAW_DIR = Path(__file__).parent.parent / "data" / "raw"

# Source registry: name → (import_fn, path_resolver, description)
SOURCES = {
    "webtext2019zh": (
        import_webtext2019zh,
        lambda: RAW_DIR / "webtext2019zh",
        "4.1M community Q&A answers (28K topics)",
    ),
    "lccc": (
        import_lccc,
        lambda: RAW_DIR / "lccc_large.json",
        "12M Weibo dialogues (conversational)",
    ),
    "cail2018": (
        import_cail2018,
        lambda: RAW_DIR / "CAIL2018" / "final_all_data",
        "2.6M criminal case descriptions",
    ),
    "translation2019zh": (
        import_translation2019zh,
        lambda: RAW_DIR / "translation2019zh",
        "5.2M zh-en parallel sentence pairs",
    ),
    "baike2018qa": (
        import_baike2018qa,
        lambda: RAW_DIR / "baike2018qa",
        "1.5M encyclopedic Q&A (492 categories)",
    ),
    "csl": (
        import_csl,
        lambda: RAW_DIR / "csl_full.tsv",
        "396K scientific paper abstracts",
    ),
    "laws": (
        import_laws,
        lambda: RAW_DIR / "Laws",
        "PRC laws and regulations",
    ),
    "cmedqa2": (
        import_cmedqa2,
        lambda: RAW_DIR / "cMedQA2",
        "108K medical questions + 203K answers",
    ),
    "medical_dialogues": (
        import_medical_dialogues,
        lambda: RAW_DIR / "Chinese-medical-dialogue-data",
        "~800K medical dialogues (6 departments)",
    ),
    "subtitles": (
        import_subtitles,
        lambda: RAW_DIR / "zh_cn_subtitles.txt",
        "16.3M subtitle lines (film/TV)",
    ),
}

# Default import order: largest/most valuable first
DEFAULT_ORDER = [
    "webtext2019zh",
    "cail2018",
    "translation2019zh",
    "baike2018qa",
    "lccc",
    "csl",
    "laws",
    "cmedqa2",
    "medical_dialogues",
    "subtitles",
]


def progress(start_time: float):
    def callback(source_name, articles, chunks):
        elapsed = time.time() - start_time
        rate = articles / elapsed if elapsed > 0 else 0
        print(f"  [{source_name}] {articles:,} articles, {chunks:,} chunks ({rate:,.0f} articles/sec)")
    return callback


def main():
    parser = argparse.ArgumentParser(description="Import specialized corpora")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--sources", type=str, default=None,
                        help="Comma-separated list of sources to import")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max articles per source (0 = all)")
    parser.add_argument("--list", action="store_true",
                        help="List available sources and exit")
    args = parser.parse_args()

    if args.list:
        print("Available sources:")
        for name in DEFAULT_ORDER:
            _, path_fn, desc = SOURCES[name]
            path = path_fn()
            exists = "✓" if path.exists() else "✗"
            print(f"  {exists} {name:25s} {desc}")
        sys.exit(0)

    sources_to_import = DEFAULT_ORDER
    if args.sources:
        sources_to_import = [s.strip() for s in args.sources.split(",")]
        for s in sources_to_import:
            if s not in SOURCES:
                print(f"ERROR: Unknown source '{s}'. Use --list to see available sources.")
                sys.exit(1)

    args.db.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(args.db)
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA cache_size=-512000")
    init_db(conn)

    print(f"Output: {args.db}")
    if args.limit:
        print(f"Limit: {args.limit} articles per source")
    print()

    grand_total_articles = 0
    grand_total_chunks = 0
    t_grand = time.time()

    for source_name in sources_to_import:
        import_fn, path_fn, desc = SOURCES[source_name]
        path = path_fn()

        if not path.exists():
            print(f"Skipping {source_name}: {path} not found")
            print()
            continue

        print(f"Importing {source_name} ({desc})...")
        t0 = time.time()
        articles, chunks = import_fn(
            conn, path, limit=args.limit, progress_fn=progress(t0)
        )
        elapsed = time.time() - t0
        print(f"  Done: {articles:,} articles, {chunks:,} chunks in {elapsed:.0f}s")
        print()

        grand_total_articles += articles
        grand_total_chunks += chunks

    grand_elapsed = time.time() - t_grand
    print("=" * 60)
    print(f"Import complete!")
    print(f"  New articles: {grand_total_articles:,}")
    print(f"  New chunks:   {grand_total_chunks:,}")
    print(f"  Time:         {grand_elapsed:.0f}s ({grand_elapsed/60:.1f}min)")
    print()

    # Summary of all sources
    for row in conn.execute(
        "SELECT name, article_count, chunk_count FROM sources ORDER BY chunk_count DESC"
    ).fetchall():
        print(f"  {row['name']:25s}  {row['article_count']:>10,} articles  {row['chunk_count']:>10,} chunks")

    conn.execute("PRAGMA synchronous=NORMAL")

    import os
    db_size = os.path.getsize(str(args.db)) / (1024 * 1024)
    print(f"\n  Database size: {db_size:,.1f} MB ({db_size/1024:.1f} GB)")

    conn.close()


if __name__ == "__main__":
    main()
