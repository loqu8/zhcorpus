#!/usr/bin/env python3
"""Benchmark: single-character retrieval strategies on the 104M-chunk corpus.

Compares:
  A) Current:    FTS5 MATCH + JOINs + snippet + ORDER BY rank LIMIT N
  B) IDs-first:  FTS5 MATCH LIMIT N (no rank, no JOINs) → fetch text by PK
  C) Per-source:  For each source, FTS5 MATCH + source filter LIMIT 3 → fetch text
  D) Pool+group: Grab 200 rowids (no rank), fetch text, pick best per source
  E) Adaptive:   vocab count → pick B or A based on threshold

Usage:
  .venv/bin/python tools/bench_single_char.py
  .venv/bin/python tools/bench_single_char.py --chars 的 人 中
"""

import argparse
import signal
import sqlite3
import sys
import time
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from zhcorpus.db import get_connection

DB_PATH = project_root / "data" / "artifacts" / "zhcorpus.db"

# Characters: ultra-common → medium → rare
DEFAULT_CHARS = ["的", "龙", "鬯"]


class TimeoutError(Exception):
    pass


def _timeout_handler(signum, frame):
    raise TimeoutError("timed out")


def setup_conn() -> sqlite3.Connection:
    conn = get_connection(DB_PATH)
    conn.execute("PRAGMA cache_size = -64000")
    conn.execute("PRAGMA temp_store = MEMORY")
    try:
        conn.execute("PRAGMA mmap_size = 268435456")
    except sqlite3.OperationalError:
        pass
    return conn


def vocab_doc_count(conn: sqlite3.Connection, char: str) -> int:
    """Fast doc count from fts5vocab (no FTS scan)."""
    row = conn.execute(
        "SELECT doc FROM chunks_fts_vocab WHERE term = ?", (char,)
    ).fetchone()
    return row["doc"] if row else 0


# ── Strategy A: current approach (full query) ──────────────────────────

def strategy_a_current(conn: sqlite3.Connection, char: str, limit: int = 20):
    """Current search_fts: JOINs + snippet + ORDER BY rank."""
    match_expr = conn.execute("SELECT simple_query(?)", (char,)).fetchone()[0]
    rows = conn.execute(
        """
        SELECT
            c.id AS chunk_id,
            c.text,
            s.name AS source,
            a.title,
            chunks_fts.rank AS rank,
            simple_snippet(chunks_fts, 0, '', '', '...', 64) AS snippet,
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
        (match_expr, limit),
    ).fetchall()
    return rows


# ── Strategy B: IDs-first (no ranking) ─────────────────────────────────

def strategy_b_ids_first(conn: sqlite3.Connection, char: str, limit: int = 20):
    """Phase 1: get rowids only (no rank). Phase 2: fetch text by PK."""
    match_expr = conn.execute("SELECT simple_query(?)", (char,)).fetchone()[0]

    # Phase 1: just rowids, no JOINs, no ranking
    id_rows = conn.execute(
        "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ? LIMIT ?",
        (match_expr, limit),
    ).fetchall()
    ids = [r["rowid"] for r in id_rows]
    if not ids:
        return []

    # Phase 2: fetch text by PK
    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(
        f"""
        SELECT c.id AS chunk_id, c.text, s.name AS source, a.title,
               c.article_id, c.chunk_index
        FROM chunks c
        JOIN articles a ON a.id = c.article_id
        JOIN sources s ON s.id = a.source_id
        WHERE c.id IN ({placeholders})
        """,
        ids,
    ).fetchall()
    return rows


# ── Strategy C: per-source sampling ─────────────────────────────────────

def strategy_c_per_source(conn: sqlite3.Connection, char: str, per_source: int = 3):
    """For each source, grab a few rowids via FTS + source filter, then fetch text."""
    match_expr = conn.execute("SELECT simple_query(?)", (char,)).fetchone()[0]
    sources = conn.execute("SELECT id, name FROM sources").fetchall()

    all_ids = []
    for src in sources:
        id_rows = conn.execute(
            """
            SELECT chunks_fts.rowid
            FROM chunks_fts
            JOIN chunks c ON c.id = chunks_fts.rowid
            JOIN articles a ON a.id = c.article_id
            WHERE chunks_fts MATCH ? AND a.source_id = ?
            LIMIT ?
            """,
            (match_expr, src["id"], per_source),
        ).fetchall()
        all_ids.extend(r["rowid"] for r in id_rows)

    if not all_ids:
        return []

    placeholders = ",".join("?" * len(all_ids))
    rows = conn.execute(
        f"""
        SELECT c.id AS chunk_id, c.text, s.name AS source, a.title,
               c.article_id, c.chunk_index
        FROM chunks c
        JOIN articles a ON a.id = c.article_id
        JOIN sources s ON s.id = a.source_id
        WHERE c.id IN ({placeholders})
        """,
        all_ids,
    ).fetchall()
    return rows


# ── Strategy D: pool + group by source ──────────────────────────────────

def strategy_d_pool_group(conn: sqlite3.Connection, char: str, pool: int = 200, per_source: int = 3):
    """Grab a pool of rowids (no rank), fetch text, pick best per source."""
    match_expr = conn.execute("SELECT simple_query(?)", (char,)).fetchone()[0]

    id_rows = conn.execute(
        "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ? LIMIT ?",
        (match_expr, pool),
    ).fetchall()
    ids = [r["rowid"] for r in id_rows]
    if not ids:
        return []

    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(
        f"""
        SELECT c.id AS chunk_id, c.text, s.name AS source, a.title,
               c.article_id, c.chunk_index, length(c.text) AS text_len
        FROM chunks c
        JOIN articles a ON a.id = c.article_id
        JOIN sources s ON s.id = a.source_id
        WHERE c.id IN ({placeholders})
        """,
        ids,
    ).fetchall()

    # Group by source, pick longest (richer context) per source
    by_source = {}
    for r in rows:
        by_source.setdefault(r["source"], []).append(r)

    result = []
    for source, items in by_source.items():
        items.sort(key=lambda r: r["text_len"], reverse=True)
        result.extend(items[:per_source])
    return result


# ── Strategy E: rowid-range per source (no JOINs) ───────────────────────

def _get_source_ranges(conn: sqlite3.Connection) -> list:
    """Get (source_name, min_id, max_id) per source. Cached per connection."""
    rows = conn.execute("""
        SELECT s.name, MIN(c.id) AS min_id, MAX(c.id) AS max_id
        FROM chunks c
        JOIN articles a ON a.id = c.article_id
        JOIN sources s ON s.id = a.source_id
        GROUP BY s.id
        ORDER BY MIN(c.id)
    """).fetchall()
    return [(r["name"], r["min_id"], r["max_id"]) for r in rows]


def strategy_e_rowid_range(conn: sqlite3.Connection, char: str, per_source: int = 3):
    """Use rowid ranges to target each source in FTS5 — no JOINs needed."""
    match_expr = conn.execute("SELECT simple_query(?)", (char,)).fetchone()[0]
    source_ranges = _get_source_ranges(conn)

    all_ids = []
    source_map = {}  # rowid → source_name
    for src_name, min_id, max_id in source_ranges:
        id_rows = conn.execute(
            """
            SELECT rowid FROM chunks_fts
            WHERE chunks_fts MATCH ? AND rowid BETWEEN ? AND ?
            LIMIT ?
            """,
            (match_expr, min_id, max_id, per_source),
        ).fetchall()
        for r in id_rows:
            all_ids.append(r["rowid"])
            source_map[r["rowid"]] = src_name

    if not all_ids:
        return []

    # Fetch text by PK (fast — small IN list)
    placeholders = ",".join("?" * len(all_ids))
    rows = conn.execute(
        f"""
        SELECT c.id AS chunk_id, c.text, c.article_id, c.chunk_index,
               a.title
        FROM chunks c
        JOIN articles a ON a.id = c.article_id
        WHERE c.id IN ({placeholders})
        """,
        all_ids,
    ).fetchall()

    # Attach source name from our map (avoids the sources JOIN)
    result = []
    for r in rows:
        result.append({
            "chunk_id": r["chunk_id"],
            "text": r["text"],
            "source": source_map[r["chunk_id"]],
            "title": r["title"],
            "article_id": r["article_id"],
            "chunk_index": r["chunk_index"],
        })
    return result


# ── Strategy F: rowid-range, IDs only (zero JOINs) ─────────────────────

def strategy_f_rowid_ids_only(conn: sqlite3.Connection, char: str, per_source: int = 3):
    """Absolute minimum: rowid ranges + text fetch by PK. No JOINs at all in phase 1."""
    match_expr = conn.execute("SELECT simple_query(?)", (char,)).fetchone()[0]
    source_ranges = _get_source_ranges(conn)

    all_ids = []
    source_map = {}
    for src_name, min_id, max_id in source_ranges:
        id_rows = conn.execute(
            "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ? AND rowid BETWEEN ? AND ? LIMIT ?",
            (match_expr, min_id, max_id, per_source),
        ).fetchall()
        for r in id_rows:
            all_ids.append(r["rowid"])
            source_map[r["rowid"]] = src_name

    if not all_ids:
        return []

    # Phase 2: just the text, minimal JOIN
    placeholders = ",".join("?" * len(all_ids))
    rows = conn.execute(
        f"SELECT id AS chunk_id, text FROM chunks WHERE id IN ({placeholders})",
        all_ids,
    ).fetchall()

    result = []
    for r in rows:
        result.append({
            "chunk_id": r["chunk_id"],
            "text": r["text"],
            "source": source_map[r["chunk_id"]],
            "title": "",
            "article_id": 0,
            "chunk_index": 0,
        })
    return result


# ── Run benchmark ───────────────────────────────────────────────────────

def timed_run(fn, *args, timeout_sec: float = 60.0):
    """Run fn with a SIGALRM timeout. Returns (result, elapsed) or (None, -1) on timeout."""
    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(int(timeout_sec))
    try:
        t0 = time.perf_counter()
        result = fn(*args)
        elapsed = time.perf_counter() - t0
        return result, elapsed
    except TimeoutError:
        return None, -1
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def main():
    parser = argparse.ArgumentParser(description="Benchmark single-char retrieval strategies")
    parser.add_argument("--chars", nargs="+", default=DEFAULT_CHARS, help="Characters to test")
    parser.add_argument("--timeout", type=float, default=30.0, help="Max seconds per strategy")
    args = parser.parse_args()

    conn = setup_conn()

    # Run fast strategies first, slow Strategy A last
    strategies = [
        ("B: IDs-first (no rank)",         strategy_b_ids_first),
        ("D: pool+group (pool=200)",       strategy_d_pool_group),
        ("E: rowid-range per source",      strategy_e_rowid_range),
        ("F: rowid-range IDs-only",        strategy_f_rowid_ids_only),
        ("C: per-source JOIN (3 each)",    strategy_c_per_source),
        ("A: current (rank+join+snip)",    strategy_a_current),
    ]

    print(f"Database: {DB_PATH}")
    print(f"Total chunks: {conn.execute('SELECT COUNT(*) FROM chunks').fetchone()[0]:,}")
    print(f"Timeout: {args.timeout}s per strategy")
    print("=" * 100)

    for char in args.chars:
        doc_count = vocab_doc_count(conn, char)
        print(f"\n{'─' * 100}")
        print(f"Character: {char}  |  fts5vocab doc count: {doc_count:,}")
        print(f"{'─' * 100}")
        print(f"  {'Strategy':<38s} {'Time':>10s} {'Rows':>6s}  {'Sources':>3s}  Sample sources")
        print(f"  {'─' * 38} {'─' * 10} {'─' * 6}  {'─' * 3}  {'─' * 30}")

        for name, fn in strategies:
            result, elapsed = timed_run(fn, conn, char, timeout_sec=args.timeout)
            if elapsed < 0:
                print(f"  {name:<38s} {'TIMEOUT':>10s}      -    -  (>{args.timeout:.0f}s)")
                # Interrupt the connection to cancel any in-flight query
                conn.interrupt()
                continue
            n_rows = len(result)
            sources = sorted(set(r["source"] for r in result)) if result else []
            src_str = ", ".join(sources[:5])
            if len(sources) > 5:
                src_str += f" +{len(sources) - 5}"
            print(f"  {name:<38s} {elapsed:>9.3f}s {n_rows:>6d}  {len(sources):>3d}  {src_str}")

    # Show sample output from Strategy E for each char
    print(f"\n{'=' * 100}")
    print("Sample sentences (Strategy E: rowid-range per source)")
    print(f"{'=' * 100}")
    for char in args.chars:
        result, elapsed = timed_run(strategy_e_rowid_range, conn, char)
        if not result:
            continue
        print(f"\n  {char} ({elapsed:.3f}s, {len(result)} rows from {len(set(r['source'] for r in result))} sources):")
        for r in result:
            text_preview = r["text"][:72].replace("\n", " ")
            print(f"    [{r['source']:18s}] {text_preview}")

    conn.close()


if __name__ == "__main__":
    main()
