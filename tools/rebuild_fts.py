#!/usr/bin/env python3
"""Rebuild FTS5 index with the simple tokenizer.

Drops the old FTS5 table (trigram or whatever) and recreates it with
tokenize='simple', then rebuilds from the chunks content table.

Usage:
    python tools/rebuild_fts.py
    python tools/rebuild_fts.py --db path/to/zhcorpus.db
"""

import argparse
import sqlite3
import time
from pathlib import Path

# Default database path
DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "artifacts" / "zhcorpus.db"

# Simple tokenizer extension
LIB_DIR = Path(__file__).resolve().parent.parent / "lib" / "libsimple-linux-ubuntu-latest"
SIMPLE_EXT = str(LIB_DIR / "libsimple")


def rebuild_fts(db_path: Path) -> None:
    print(f"Database: {db_path}")
    print(f"Extension: {SIMPLE_EXT}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.enable_load_extension(True)
    conn.load_extension(SIMPLE_EXT)
    conn.enable_load_extension(False)
    print("simple tokenizer loaded")

    # Check chunk count
    row = conn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()
    chunk_count = row["n"]
    print(f"Chunks to index: {chunk_count:,}")

    # Check current FTS schema
    row = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'chunks_fts'").fetchone()
    if row:
        print(f"Current FTS: {row[0][:80]}...")
    else:
        print("No existing FTS table")

    # Drop old FTS tables and triggers
    print("\nDropping old FTS tables and triggers...")
    t0 = time.time()
    conn.executescript("""
        DROP TRIGGER IF EXISTS chunks_ai;
        DROP TRIGGER IF EXISTS chunks_ad;
        DROP TRIGGER IF EXISTS chunks_au;
        DROP TABLE IF EXISTS chunks_fts_vocab;
        DROP TABLE IF EXISTS chunks_fts;
    """)
    print(f"  Done in {time.time() - t0:.1f}s")

    # Create new FTS5 with simple tokenizer
    print("Creating FTS5 with simple tokenizer...")
    t0 = time.time()
    conn.executescript("""
        CREATE VIRTUAL TABLE chunks_fts USING fts5(
            text,
            content='chunks',
            content_rowid='id',
            tokenize='simple'
        );

        CREATE VIRTUAL TABLE chunks_fts_vocab
            USING fts5vocab(chunks_fts, row);

        CREATE TRIGGER chunks_ai AFTER INSERT ON chunks BEGIN
            INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
        END;
        CREATE TRIGGER chunks_ad AFTER DELETE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
        END;
        CREATE TRIGGER chunks_au AFTER UPDATE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
            INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
        END;
    """)
    print(f"  Done in {time.time() - t0:.1f}s")

    # Rebuild: reads all rows from chunks content table into FTS index
    print(f"Rebuilding FTS index from {chunk_count:,} chunks...")
    print("  (this may take a while)")
    t0 = time.time()
    conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES ('rebuild')")
    conn.commit()
    elapsed = time.time() - t0
    rate = chunk_count / elapsed if elapsed > 0 else 0
    print(f"  Done in {elapsed:.0f}s ({rate:,.0f} chunks/sec)")

    # Verify with a test search
    print("\nVerifying search...")
    t0 = time.time()
    rows = conn.execute("""
        SELECT c.id, c.text, chunks_fts.rank
        FROM chunks_fts
        JOIN chunks c ON c.id = chunks_fts.rowid
        WHERE chunks_fts MATCH simple_query('量刑')
        ORDER BY chunks_fts.rank
        LIMIT 5
    """).fetchall()
    elapsed = time.time() - t0
    print(f"  '量刑': {len(rows)} results in {elapsed:.3f}s")
    for r in rows:
        print(f"    rank={r['rank']:.4f}  {r['text'][:60]}")

    # Check DB size
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    db_size = db_path.stat().st_size
    print(f"\nDatabase size: {db_size / (1024**3):.1f} GB")
    print("Done!")
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Rebuild FTS5 index with simple tokenizer")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Database path")
    args = parser.parse_args()

    if not args.db.exists():
        print(f"Error: database not found at {args.db}")
        return 1

    rebuild_fts(args.db)
    return 0


if __name__ == "__main__":
    exit(main())
