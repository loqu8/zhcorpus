#!/usr/bin/env python3
"""Detect and delete definitions with CJK character leaks, then backfill.

Step 1: Find non-ja minimax definitions containing Chinese characters.
Step 2: Delete those specific (headword_id, lang) definitions.
Step 3: Run the existing backfill_langs.py to retranslate them with context.

Usage:
    # Dry run — show what would be deleted
    python tools/dictmaster/fix_cjk_leaks.py --dry-run

    # Delete leaks only (no retranslation)
    python tools/dictmaster/fix_cjk_leaks.py --delete-only

    # Delete + backfill 50 headwords as a test
    python tools/dictmaster/fix_cjk_leaks.py --limit 50

    # Full run: delete all leaks + backfill with 20 workers
    python tools/dictmaster/fix_cjk_leaks.py --workers 20
"""

import argparse
import re
import sqlite3
from collections import Counter
from pathlib import Path

from tools.dictmaster.schema import DEFAULT_DB_PATH, get_connection

# CJK Unified Ideographs + Extension A + Compatibility Ideographs
CJK_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]')


def find_leaked_def_ids(conn: sqlite3.Connection) -> tuple[list[int], Counter, int]:
    """Find definition IDs with CJK leaks. Returns (ids, lang_counts, hw_count).

    Streams rows with a cursor to avoid loading 4.7M rows at once.
    """
    cur = conn.execute("""
        SELECT id, lang, definition
        FROM definitions
        WHERE source = 'minimax' AND lang != 'ja'
    """)

    leaked_ids = []
    by_lang = Counter()
    hw_ids = set()
    batch_size = 50_000

    while True:
        rows = cur.fetchmany(batch_size)
        if not rows:
            break
        for r in rows:
            if CJK_RE.search(r["definition"]):
                leaked_ids.append(r["id"])
                by_lang[r["lang"]] += 1

    return leaked_ids, by_lang


def main():
    parser = argparse.ArgumentParser(description="Fix CJK character leaks in translations")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="Database path")
    parser.add_argument("--dry-run", action="store_true", help="Show stats without deleting")
    parser.add_argument("--delete-only", action="store_true", help="Delete leaks but don't backfill")
    parser.add_argument("--limit", type=int, default=None, help="Max headwords to backfill")
    parser.add_argument("--workers", type=int, default=1, help="Parallel workers for backfill")
    parser.add_argument("--batch-size", type=int, default=20, help="Entries per API call")
    args = parser.parse_args()

    conn = get_connection(args.db)

    # Step 1: Scan
    print("Step 1: Scanning for CJK leaks in non-ja definitions...")
    leaked_ids, by_lang = find_leaked_def_ids(conn)
    total_leaked = len(leaked_ids)

    print(f"  Found {total_leaked:,} leaked definitions")
    for lang in sorted(by_lang, key=by_lang.get, reverse=True):
        print(f"    {lang}: {by_lang[lang]:,}")

    if args.dry_run:
        print("\n  [DRY RUN] No changes made.")
        conn.close()
        return

    # Step 2: Bulk delete
    print(f"\nStep 2: Deleting {total_leaked:,} leaked definitions...")
    # Delete in batches of 500 using WHERE id IN (...)
    deleted = 0
    for i in range(0, total_leaked, 500):
        batch = leaked_ids[i:i + 500]
        placeholders = ",".join("?" * len(batch))
        conn.execute(f"DELETE FROM definitions WHERE id IN ({placeholders})", batch)
        deleted += len(batch)
    conn.commit()
    print(f"  Deleted {deleted:,} definitions")
    conn.close()

    if args.delete_only:
        print("\n  [DELETE ONLY] Skipping backfill. Run backfill_langs.py to retranslate.")
        return

    # Step 3: Backfill using existing infrastructure
    print(f"\nStep 3: Backfilling deleted entries (workers={args.workers})...")
    from tools.dictmaster.backfill_langs import run_backfill
    run_backfill(
        db_path=args.db,
        batch_size=args.batch_size,
        workers=args.workers,
        limit=args.limit,
        prompt_version="v2-cjk-fix",
    )


if __name__ == "__main__":
    main()
