#!/usr/bin/env python3
"""Backfill missing language definitions — V3 with two-phase architecture.

ARCHITECTURE:
1. Phase 1: Load ALL remaining work into memory (single DB read)
2. Phase 2: Workers process in parallel, push to queue (NO DB access)
3. Phase 3: Single-threaded writer consumes queue (single DB write)

This eliminates SQLite lock contention entirely because:
- Phase 1: Only reads (no concurrent writers)
- Phase 2: Zero DB access
- Phase 3: Only writes (no concurrent readers)

Benefits:
- True parallelism: workers don't wait for DB
- No lock errors: phases are sequential
- Scalable: can run 50-100 workers
- Memory efficient: ~100MB for 87K entries

Usage:
    python tools/dictmaster/backfill_langs_v3.py --workers 50
"""

import argparse
import queue
import sqlite3
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from tools.dictmaster.schema import DEFAULT_DB_PATH, get_connection, ensure_source
from tools.dictmaster.translate.prompts import ALL_TARGET_LANGS, UNIVERSAL_SYSTEM_PROMPT

ALL_LANGS_SET = set(ALL_TARGET_LANGS)

# ---------------------------------------------------------------------------
# Backfill prompt — same as V1/V2
# ---------------------------------------------------------------------------

BACKFILL_SYSTEM_PROMPT = """\
You are a professional multilingual Chinese lexicographer.
Fill in ONLY the missing language definitions listed below.
Existing translations are provided for consistency — match their style and \
specificity. Do NOT repeat or modify the existing translations.

Rules:
- Output EXACTLY one line per MISSING language in format "xx: def1/def2"
- Be concise: dictionary style, not full sentences
- Use the target language exclusively for each definition
- For verbs, start with the infinitive form appropriate to the target language
- For nouns, give the most common equivalent(s)
- Maximum 5 glosses per entry
- No explanatory notes, no parenthetical qualifiers unless essential

CRITICAL: Every non-Chinese definition must contain ZERO Chinese characters \
(漢字). If you catch yourself writing 漢字/汉字 in any definition, replace \
them with the target language equivalent. \
EXCEPTION: When a headword is a variant or component of another character, you \
may cite the reference character (e.g. "variant of 夂") — but the rest of the \
definition must be in the target language only.

Language-specific rules:
- ja (Japanese): Provide the MEANING in Japanese, not just kanji echo or kana \
reading. Write a Japanese definition/gloss that explains the word. Use native \
Japanese vocabulary.
- ko (Korean): Write in Hangul only. Do NOT mix in Chinese characters (漢字/한자).
- tl (Tagalog): Use natural Tagalog vocabulary. Do NOT produce literal \
word-for-word translations from English.
- fa (Persian): Write definitions in Persian script (فارسی). Use native Persian \
vocabulary. Do NOT mix in Latin script or other languages.
- vi (Vietnamese): Write in Vietnamese with proper diacritics. Do NOT include \
Chinese characters.
- ar (Arabic): Write in Arabic script only. Do NOT mix in Latin words from \
other languages (French, Spanish, English). Use proper Arabic equivalents.
- th (Thai): Write in Thai script with proper tone marks. Do NOT transliterate \
from English.
- hi (Hindi): Write in Devanagari script. Use native Hindi vocabulary, not \
English transliterations.
- nl (Dutch): Write in standard Dutch. Use natural Dutch compounds and phrasing.
- pt (Portuguese): Write in Brazilian Portuguese. Use proper diacritics.
- it (Italian): Write in standard Italian."""

BACKFALL_BATCH_TEMPLATE = """\
Fill in the MISSING languages for these Chinese dictionary entries.
Existing translations are shown for context — only produce the MISSING ones.

CRITICAL FORMAT: For each numbered entry, output ONE LINE PER MISSING LANGUAGE.
Each line must be "xx: def1/def2" on its own line.
Separate entries with a blank line.

{entries}"""


def build_backfill_batch_prompt(entries: list[dict]) -> str:
    """Build a backfill prompt for a batch of entries."""
    blocks = []
    for i, e in enumerate(entries, 1):
        existing_lines = []
        for lang in ALL_TARGET_LANGS:
            defn = e.get("existing_defs", {}).get(lang)
            if defn:
                existing_lines.append(f"   {lang}: {defn}")
        existing_block = "\n".join(existing_lines) if existing_lines else "   (none)"

        missing_lines = "\n".join(f"   {lang}:" for lang in e["missing_langs"])

        block = (
            f"{i}. {e['traditional']} / {e['simplified']}\n"
            f"   Pinyin: {e['pinyin']}\n"
            f"   Existing translations:\n{existing_block}\n"
            f"   MISSING — fill these:\n{missing_lines}"
        )
        blocks.append(block)

    return BACKFALL_BATCH_TEMPLATE.format(entries="\n\n".join(blocks))


def parse_backfill_response(
    response: str,
    count: int,
    entries: list[dict],
) -> list[dict[str, str]]:
    """Parse a backfill response."""
    from tools.dictmaster.translate.prompts import _normalize_response_lines

    lines = _normalize_response_lines(response, ALL_LANGS_SET)

    has_numbers = any(
        line.strip() and line.strip()[0].isdigit() and "." in line.strip().split(" ")[0]
        for line in lines if line.strip()
    )

    results: list[dict[str, str]] = []
    current: dict[str, str] = {}
    current_entry_idx = 0

    def _clean_defn(text: str) -> str:
        text = text.strip()
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        if text.startswith("/"):
            text = text[1:]
        if text.endswith("/"):
            text = text[:-1]
        return text.strip()

    for line in lines:
        line = line.strip()

        if has_numbers:
            if line and line[0].isdigit():
                parts = line.split(".", 1)
                if len(parts) == 2 and parts[0].strip().isdigit():
                    if current:
                        results.append(current)
                        current = {}
                        current_entry_idx = len(results)
                    remainder = parts[1].strip()
                    if remainder and ":" in remainder:
                        prefix, _, defn = remainder.partition(":")
                        prefix = prefix.strip().lower()
                        if current_entry_idx >= len(entries):
                            continue
                        missing = set(entries[current_entry_idx]["missing_langs"])
                        if prefix in missing:
                            cleaned = _clean_defn(defn)
                            if cleaned:
                                current[prefix] = cleaned
                    continue
        else:
            if not line:
                if current:
                    results.append(current)
                    current = {}
                    current_entry_idx = len(results)
                continue

        if not line or ":" not in line:
            continue
        prefix, _, defn = line.partition(":")
        prefix = prefix.strip().lower()
        if current_entry_idx >= len(entries):
            continue
        missing = set(entries[current_entry_idx]["missing_langs"])
        if prefix in missing:
            cleaned = _clean_defn(defn)
            if cleaned:
                current[prefix] = cleaned

    if current:
        results.append(current)

    while len(results) < count:
        results.append({})

    return results[:count]


# ---------------------------------------------------------------------------
# Phase 1: Load ALL work into memory (single-threaded)
# ---------------------------------------------------------------------------

def load_all_work(db_path: Path, include_zero: bool = False) -> list[dict]:
    """Load all headwords needing backfill into memory.

    This is a SINGLE-threaded DB read. After this, no more DB access
    until the write phase.
    """
    conn = get_connection(db_path)

    # Get all headwords with partial coverage
    target_count = len(ALL_TARGET_LANGS)
    join = "LEFT JOIN" if include_zero else "JOIN"

    # First get all headword IDs that need work
    headword_rows = conn.execute(f"""
        SELECT h.id, h.traditional, h.simplified, h.pinyin,
               GROUP_CONCAT(d.lang) as existing_langs
        FROM headwords h
        {join} definitions d ON d.headword_id = h.id AND d.source = 'minimax'
        GROUP BY h.id
        HAVING COUNT(DISTINCT d.lang) < ?
        ORDER BY h.id
    """, (target_count,)).fetchall()

    if not headword_rows:
        conn.close()
        return []

    # Build entries with missing langs
    entries = []
    ids = []
    for row in headword_rows:
        present = set(row["existing_langs"].split(",")) if row["existing_langs"] else set()
        present.discard("")
        missing = sorted(ALL_LANGS_SET - present)
        if not missing:
            continue  # Skip if somehow complete
        entries.append({
            "headword_id": row["id"],
            "traditional": row["traditional"],
            "simplified": row["simplified"],
            "pinyin": row["pinyin"] or "",
            "missing_langs": missing,
            "existing_lang_set": present,
        })
        ids.append(row["id"])

    # Bulk-load all existing definitions for context
    if not ids:
        conn.close()
        return []

    placeholders = ",".join("?" * len(ids))
    def_rows = conn.execute(
        f"SELECT headword_id, lang, definition FROM definitions "
        f"WHERE headword_id IN ({placeholders}) AND source = 'minimax'",
        ids,
    ).fetchall()

    defs_by_id: dict[int, dict[str, str]] = {hid: {} for hid in ids}
    for r in def_rows:
        defs_by_id[r["headword_id"]][r["lang"]] = r["definition"]

    for e in entries:
        e["existing_defs"] = defs_by_id.get(e["headword_id"], {})

    conn.close()
    return entries


# ---------------------------------------------------------------------------
# Worker function (no DB access)
# ---------------------------------------------------------------------------

def translate_batch(batch: list[dict]) -> list[dict[str, str]]:
    """Translate a batch - NO DB ACCESS."""
    from tools.dictmaster.translate.minimax_api import _chat

    prompt = build_backfill_batch_prompt(batch)
    avg_missing = sum(len(e["missing_langs"]) for e in batch) / len(batch)
    max_tokens = max(2048, int(len(batch) * avg_missing * 80))
    response = _chat(BACKFILL_SYSTEM_PROMPT, prompt, max_tokens=min(max_tokens, 8192))
    return parse_backfill_response(response, len(batch), batch)


# ---------------------------------------------------------------------------
# Phase 3: Single-threaded writer
# ---------------------------------------------------------------------------

def write_results(db_path: Path, result_queue: queue.Queue, total_expected: int,
                 batch_size: int = 500, progress_interval: int = 1000):
    """Consume queue and write to DB - single-threaded."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")  # 60 second timeout
    conn.execute("PRAGMA synchronous=NORMAL")

    filled_defs = 0
    filled_entries = 0
    processed = 0
    batch: list[tuple] = []

    while True:
        try:
            item = result_queue.get(timeout=2)
            if item is None:  # Poison pill
                break

            entry, lang_defs = item
            for lang, defn in lang_defs.items():
                if defn and lang in entry["missing_langs"]:
                    batch.append((
                        entry["headword_id"], lang, defn, "minimax",
                        "medium", "v3-backfill"
                    ))

            processed += 1

            if len(batch) >= batch_size:
                _flush_batch(conn, batch)
                filled_defs += len(batch)
                filled_entries += len(set(b[0] for b in batch))
                batch = []

                if processed % progress_interval < progress_interval:
                    print(f"    Writer: {processed:,}/{total_expected:,} batches, "
                          f"{filled_defs:,} defs written", flush=True)

        except queue.Empty:
            if batch:
                _flush_batch(conn, batch)
                filled_defs += len(batch)
                filled_entries += len(set(b[0] for b in batch))
                batch = []

    # Final flush
    if batch:
        _flush_batch(conn, batch)
        filled_defs += len(batch)
        filled_entries += len(set(b[0] for b in batch))

    conn.commit()
    conn.close()

    return filled_entries, filled_defs


def _flush_batch(conn: sqlite3.Connection, batch: list[tuple]):
    """Batch insert."""
    if not batch:
        return
    conn.executemany(
        "INSERT OR IGNORE INTO definitions "
        "(headword_id, lang, definition, source, confidence, prompt_version) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        batch
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Main V3
# ---------------------------------------------------------------------------

def run_backfill_v3(
    db_path: Path,
    batch_size: int = 20,
    workers: int = 1,
    limit: int | None = None,
    dry_run: bool = False,
    include_zero: bool = False,
) -> None:
    """Run backfill with two-phase architecture."""

    print("\n" + "="*60)
    print("PHASE 1: Loading all work into memory...")
    print("="*60 + "\n")

    all_entries = load_all_work(db_path, include_zero=include_zero)

    if limit:
        all_entries = all_entries[:limit]

    total = len(all_entries)
    total_missing = sum(len(e["missing_langs"]) for e in all_entries)

    print(f"Loaded {total:,} headwords needing backfill")
    print(f"Total missing definition slots: {total_missing:,}")
    print(f"Per-lang gaps:", flush=True)

    # Count per language
    lang_counts = Counter()
    for e in all_entries:
        for lang in e["missing_langs"]:
            lang_counts[lang] += 1

    for lang in ALL_TARGET_LANGS:
        if lang_counts[lang] > 0:
            print(f"  {lang}: {lang_counts[lang]:,}", flush=True)

    if dry_run:
        print("\n[DRY RUN] Would backfill the above. Exiting.")
        return

    if total == 0:
        print("\nNo work to do!")
        return

    print(f"\n{'='*60}")
    print(f"PHASE 2: Parallel translation ({workers} workers, {total} entries)")
    print(f"{'='*60}\n")

    # Create queue for results
    result_queue: queue.Queue = queue.Queue(maxsize=workers * 10)

    # Start writer thread
    writer_done = threading.Event()
    writer_result = {}

    def writer_thread():
        writer_result['entries'], writer_result['defs'] = write_results(
            db_path, result_queue, (total + batch_size - 1) // batch_size
        )
        writer_done.set()

    t_start = time.time()

    # Start writer
    writer_thread_handle = threading.Thread(target=writer_thread, daemon=True)
    writer_thread_handle.start()

    # Split into batches
    batches = []
    for i in range(0, len(all_entries), batch_size):
        batches.append(all_entries[i:i + batch_size])

    print(f"Processing {len(batches)} batches with {workers} workers...")

    # Process in parallel
    processed_batches = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(translate_batch, batch): batch for batch in batches}

        for future in as_completed(futures):
            batch = futures[future]
            try:
                results = future.result()
                # Push to queue for writer
                for entry, lang_defs in zip(batch, results):
                    if lang_defs:
                        result_queue.put((entry, lang_defs))
            except Exception as e:
                print(f"  ERROR: {e}", flush=True)

            processed_batches += 1
            if processed_batches % 50 == 0:
                elapsed = time.time() - t_start
                rate = processed_batches / elapsed if elapsed > 0 else 0
                print(f"  [{processed_batches}/{len(batches)}] {rate:.1f} batches/s", flush=True)

    # Signal writer done
    result_queue.put(None)
    writer_thread_handle.join(timeout=60)

    elapsed = time.time() - t_start
    rate = total / elapsed if elapsed > 0 else 0

    print(f"\n{'='*60}")
    print("COMPLETE")
    print(f"{'='*60}")
    print(f"  Entries processed: {total:,}")
    print(f"  Definitions written: {writer_result.get('defs', 0):,}")
    print(f"  Time: {elapsed:.1f}s ({rate:.1f} entries/sec)")
    print(f"  ETA equivalent at V1 rate (4/s): {total/4/60:.1f} minutes")


def main():
    parser = argparse.ArgumentParser(description="Backfill missing language definitions (V3)")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="Database path")
    parser.add_argument("--batch-size", type=int, default=20, help="Entries per API call")
    parser.add_argument("--workers", type=int, default=1, help="Parallel workers")
    parser.add_argument("--limit", type=int, default=None, help="Max entries to process")
    parser.add_argument("--dry-run", action="store_true", help="Show stats without translating")
    parser.add_argument("--include-zero", action="store_true",
                        help="Also retry headwords with zero definitions")
    args = parser.parse_args()

    print("Step: Backfill missing languages (V3 - two-phase architecture)")

    run_backfill_v3(
        db_path=args.db,
        batch_size=args.batch_size,
        workers=args.workers,
        limit=args.limit,
        dry_run=args.dry_run,
        include_zero=args.include_zero,
    )


if __name__ == "__main__":
    main()
