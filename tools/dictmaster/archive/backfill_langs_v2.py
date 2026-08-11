#!/usr/bin/env python3
"""Backfill missing language definitions — V2 with queue-based concurrency.

Producer-Consumer pattern:
- Workers: Parallel API calls, produce results to queue
- Queue: Thread-safe buffer between workers and writer
- Writer: Single thread consumes queue, batch writes to SQLite

Benefits over V1:
- True parallelism: workers don't wait for DB writes
- SQLite-safe: single writer thread, no lock contention
- Scalable: can run 50-100 workers without DB issues
- Batch inserts: more efficient via executemany()

Usage:
    python tools/dictmaster/backfill_langs_v2.py --workers 50 --batch-size 20
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
# Backfill prompt — same as V1
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

BACKFILL_BATCH_TEMPLATE = """\
Fill in the MISSING languages for these Chinese dictionary entries.
Existing translations are shown for context — only produce the MISSING ones.

CRITICAL FORMAT: For each numbered entry, output ONE LINE PER MISSING LANGUAGE.
Each line must be "xx: def1/def2" on its own line.
Separate entries with a blank line.

{entries}"""

# ---------------------------------------------------------------------------
# Prompt builders (same as V1)
# ---------------------------------------------------------------------------

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

    return BACKFILL_BATCH_TEMPLATE.format(entries="\n\n".join(blocks))


def parse_backfill_response(
    response: str,
    count: int,
    entries: list[dict],
) -> list[dict[str, str]]:
    """Parse a backfill response — same as V1."""
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
# Query helpers
# ---------------------------------------------------------------------------

def count_partial_entries(conn: sqlite3.Connection, include_zero: bool = False) -> tuple[int, Counter]:
    """Count headwords needing backfill."""
    target_count = len(ALL_TARGET_LANGS)
    join = "LEFT JOIN" if include_zero else "JOIN"
    rows = conn.execute(f"""
        SELECT GROUP_CONCAT(DISTINCT d.lang) as existing_langs
        FROM headwords h
        {join} definitions d ON d.headword_id = h.id AND d.source = 'minimax'
        GROUP BY h.id
        HAVING COUNT(DISTINCT d.lang) < ?
    """, (target_count,)).fetchall()

    missing_count: Counter = Counter()
    for row in rows:
        present = set(row["existing_langs"].split(",")) if row["existing_langs"] else set()
        present.discard("")
        for lang in ALL_LANGS_SET - present:
            missing_count[lang] += 1
    return len(rows), missing_count


def fetch_batch(
    conn: sqlite3.Connection,
    batch_size: int,
    include_zero: bool = False,
) -> list[dict]:
    """Fetch one batch of headwords needing backfill."""
    target_count = len(ALL_TARGET_LANGS)
    join = "LEFT JOIN" if include_zero else "JOIN"
    rows = conn.execute(f"""
        SELECT h.id, h.traditional, h.simplified, h.pinyin,
               GROUP_CONCAT(d.lang) as existing_langs
        FROM headwords h
        {join} definitions d ON d.headword_id = h.id AND d.source = 'minimax'
        GROUP BY h.id
        HAVING COUNT(DISTINCT d.lang) < ?
        ORDER BY h.id
        LIMIT ?
    """, (target_count, batch_size)).fetchall()

    if not rows:
        return []

    entries = []
    ids = []
    for row in rows:
        present = set(row["existing_langs"].split(",")) if row["existing_langs"] else set()
        present.discard("")
        missing = sorted(ALL_LANGS_SET - present)
        entries.append({
            "headword_id": row["id"],
            "traditional": row["traditional"],
            "simplified": row["simplified"],
            "pinyin": row["pinyin"] or "",
            "missing_langs": missing,
            "existing_lang_set": present,
        })
        ids.append(row["id"])

    # Bulk-load existing definitions for context
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
        e["existing_defs"] = defs_by_id[e["headword_id"]]

    return entries


# ---------------------------------------------------------------------------
# Queue-based writer (the key innovation)
# ---------------------------------------------------------------------------

class QueueWriter:
    """Single-threaded writer that consumes results from a queue.

    Creates its own DB connection to avoid SQLite thread-safety issues.
    """

    def __init__(self, db_path: Path, result_queue: queue.Queue, batch_size: int = 100):
        self.db_path = db_path
        self.queue = result_queue
        self.batch_size = batch_size
        self.running = True
        self.filled_defs = 0
        self.filled_entries = 0
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None

    def _get_connection(self) -> sqlite3.Connection:
        """Create a new connection for this thread."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def run(self):
        """Main loop: consume from queue and batch-insert to DB."""
        self._conn = self._get_connection()
        batch: list[tuple] = []
        while self.running or not self.queue.empty():
            try:
                item = self.queue.get(timeout=0.5)
                if item is None:  # Poison pill
                    break

                entry, lang_defs = item
                for lang, defn in lang_defs.items():
                    if defn and lang in entry["missing_langs"]:
                        batch.append((
                            entry["headword_id"], lang, defn, "minimax",
                            "medium", "v2-backfill"
                        ))

                if len(batch) >= self.batch_size:
                    self._flush(batch)
                    batch = []

            except queue.Empty:
                # Queue empty, flush any remaining
                if batch:
                    self._flush(batch)
                    batch = []

        # Final flush
        if batch:
            self._flush(batch)

        self._conn.close()

    def _flush(self, batch: list[tuple]):
        """Batch insert with executemany."""
        if not batch:
            return
        if not self._conn:
            return
        self._conn.executemany(
            "INSERT OR IGNORE INTO definitions "
            "(headword_id, lang, definition, source, confidence, prompt_version) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            batch
        )
        self._conn.commit()
        with self._lock:
            self.filled_entries += len(set(b[0] for b in batch))  # Unique headword_ids
            self.filled_defs += len(batch)

    def stop(self):
        """Signal writer to stop."""
        self.running = False


# ---------------------------------------------------------------------------
# Main V2
# ---------------------------------------------------------------------------

def run_backfill_v2(
    db_path: Path,
    batch_size: int = 20,
    workers: int = 1,
    limit: int | None = None,
    dry_run: bool = False,
    include_zero: bool = False,
    queue_size: int = 500,
) -> None:
    """Run backfill with queue-based concurrency.

    Architecture:
    1. Main thread fetches batches from DB
    2. Workers (ThreadPoolExecutor) call API, put results in queue
    3. QueueWriter thread consumes queue, batch-inserts to SQLite
    4. This allows parallel API calls with serialized DB writes
    """
    from tools.dictmaster.translate.minimax_api import _chat

    conn = get_connection(db_path)
    ensure_source(conn, "minimax")

    total, missing_count = count_partial_entries(conn, include_zero=include_zero)
    if limit:
        total = min(total, limit)

    print(f"Backfill V2: {total:,} headwords with partial coverage", flush=True)
    print(f"  Total missing definition slots: {sum(missing_count.values()):,}", flush=True)
    print(f"  Per-lang gaps:", flush=True)
    for lang in ALL_TARGET_LANGS:
        if missing_count[lang] > 0:
            print(f"    {lang}: {missing_count[lang]:,}", flush=True)

    if dry_run:
        print("\n  [DRY RUN] Would backfill the above. Exiting.")
        conn.close()
        return

    # Create queue and writer (writer creates its own connection)
    result_queue: queue.Queue = queue.Queue(maxsize=queue_size)
    writer = QueueWriter(db_path, result_queue, batch_size=200)
    writer_thread = threading.Thread(target=writer.run, daemon=True)
    writer_thread.start()

    print(f"\n  Starting backfill V2 ({workers} workers, queue size {queue_size})...", flush=True)
    t_start = time.time()
    processed = 0

    def _translate_one_batch(batch: list[dict]) -> list[dict[str, str]]:
        """Send a single backfill batch to the API."""
        prompt = build_backfill_batch_prompt(batch)
        avg_missing = sum(len(e["missing_langs"]) for e in batch) / len(batch)
        max_tokens = max(2048, int(len(batch) * avg_missing * 80))
        response = _chat(BACKFILL_SYSTEM_PROMPT, prompt, max_tokens=min(max_tokens, 8192))
        return parse_backfill_response(response, len(batch), batch)

    # Fetch initial working set
    fetch_size = min(workers * batch_size * 4, total)
    working_set = fetch_batch(conn, fetch_size, include_zero=include_zero)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        pending = {}
        ws_idx = 0

        def _submit_more():
            nonlocal ws_idx
            while len(pending) < workers * 2 and ws_idx < len(working_set):
                batch = working_set[ws_idx:ws_idx + batch_size]
                if not batch:
                    break
                fut = executor.submit(_translate_one_batch, batch)
                pending[fut] = batch
                ws_idx += len(batch)

        _submit_more()

        while pending:
            # Wait for any future to complete
            done = set()
            for fut in as_completed(pending):
                done.add(fut)
                batch = pending.pop(fut)

                try:
                    results = fut.result()
                    # Put results in queue for writer thread
                    for entry, lang_defs in zip(batch, results):
                        if lang_defs:
                            result_queue.put((entry, lang_defs))
                except Exception as e:
                    print(f"    ERROR: {e}", flush=True)

                processed += len(batch)

                # Refill working set when running low
                if ws_idx >= len(working_set) and len(pending) < workers and processed < total:
                    remaining = total - processed
                    working_set = fetch_batch(conn, min(fetch_size, remaining), include_zero=include_zero)
                    ws_idx = 0
                    _submit_more()

                # Log progress periodically
                if processed % (batch_size * 10) < batch_size:
                    elapsed = time.time() - t_start
                    rate = processed / elapsed if elapsed > 0 else 0
                    remaining = total - processed
                    eta = remaining / rate if rate > 0 else 0
                    print(
                        f"    [{processed:,}/{total:,}] "
                        f"{writer.filled_entries:,} entries, {writer.filled_defs:,} defs filled "
                        f"({rate:.1f} entries/s, ETA {eta / 60:.1f}m)",
                        flush=True,
                    )

                _submit_more()
                break  # Process one at a time to keep queue from growing too fast

    # Signal writer to stop
    result_queue.put(None)  # Poison pill
    writer_thread.join(timeout=10)

    conn.close()
    elapsed = time.time() - t_start
    print(
        f"\n  Done: {writer.filled_entries:,} entries, {writer.filled_defs:,} definitions filled "
        f"in {elapsed / 60:.1f}m"
    )


def main():
    parser = argparse.ArgumentParser(description="Backfill missing language definitions (V2)")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="Database path")
    parser.add_argument("--batch-size", type=int, default=20, help="Entries per API call")
    parser.add_argument("--workers", type=int, default=1, help="Parallel workers")
    parser.add_argument("--limit", type=int, default=None, help="Max entries to process")
    parser.add_argument("--dry-run", action="store_true", help="Show stats without translating")
    parser.add_argument("--include-zero", action="store_true",
                        help="Also retry headwords with zero definitions")
    parser.add_argument("--queue-size", type=int, default=500,
                        help="Max results in queue before blocking")
    args = parser.parse_args()

    print("Step: Backfill missing languages (V2 - queue-based)")
    run_backfill_v2(
        db_path=args.db,
        batch_size=args.batch_size,
        workers=args.workers,
        limit=args.limit,
        dry_run=args.dry_run,
        include_zero=args.include_zero,
        queue_size=args.queue_size,
    )


if __name__ == "__main__":
    main()
