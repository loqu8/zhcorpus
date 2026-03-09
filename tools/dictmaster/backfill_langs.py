#!/usr/bin/env python3
"""Backfill missing language definitions for headwords with partial coverage.

Sends existing translations as context so new definitions stay consistent.

Usage:
    # Dry run — show what would be backfilled
    python tools/dictmaster/backfill_langs.py --dry-run

    # Test 10 entries
    python tools/dictmaster/backfill_langs.py --limit 10

    # Full backfill with 20 parallel workers
    python tools/dictmaster/backfill_langs.py --workers 20

    # Also retry the 840 headwords with zero definitions
    python tools/dictmaster/backfill_langs.py --workers 20 --include-zero
"""

import argparse
import sqlite3
import time
from collections import Counter
from pathlib import Path

from tools.dictmaster.schema import DEFAULT_DB_PATH, get_connection, ensure_source, upsert_definition
from tools.dictmaster.translate.prompts import ALL_TARGET_LANGS, UNIVERSAL_SYSTEM_PROMPT

ALL_LANGS_SET = set(ALL_TARGET_LANGS)

# ---------------------------------------------------------------------------
# Backfill prompt — sends existing defs as read-only context
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
(汉字). If you catch yourself writing 漢字/汉字 in any definition, replace \
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


def build_backfill_batch_prompt(entries: list[dict]) -> str:
    """Build a backfill prompt for a batch of entries.

    Each entry dict has: traditional, simplified, pinyin, existing_defs, missing_langs
    """
    blocks = []
    for i, e in enumerate(entries, 1):
        # Format existing defs as context
        existing_lines = []
        for lang in ALL_TARGET_LANGS:
            defn = e.get("existing_defs", {}).get(lang)
            if defn:
                existing_lines.append(f"   {lang}: {defn}")
        existing_block = "\n".join(existing_lines) if existing_lines else "   (none)"

        # Format missing lang placeholders
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
    """Parse a backfill response — only accept langs that were actually missing.

    Handles two formats:
    1. Numbered entries: "1. \\n  xx: def\\n\\n2. \\n  xx: def"
    2. Unnumbered (common when 1 lang missing per entry): "xx: def\\n\\nxx: def"
       In this case, blank lines separate entries.
    """
    from tools.dictmaster.translate.prompts import _normalize_response_lines

    lines = _normalize_response_lines(response, ALL_LANGS_SET)

    # Detect if response uses numbered entries
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
            # Numbered entry boundary
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
                            continue  # out of bounds — skip
                        missing = set(entries[current_entry_idx]["missing_langs"])
                        if prefix in missing:
                            cleaned = _clean_defn(defn)
                            if cleaned:
                                current[prefix] = cleaned
                    continue
        else:
            # Unnumbered: blank line = entry separator
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
            continue  # out of bounds — skip to avoid overwriting
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
    """Count headwords needing backfill and per-lang gaps without loading all rows."""
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
    """Fetch one batch of headwords needing backfill, with existing defs included.

    Uses the DB as a live queue — each call queries for headwords that still
    have fewer than ALL_TARGET_LANGS definitions, so completed entries are
    automatically skipped on the next call.
    """
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

    # Build entries with missing langs
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
# Main
# ---------------------------------------------------------------------------

def run_backfill(
    db_path: Path,
    batch_size: int = 20,
    workers: int = 1,
    limit: int | None = None,
    dry_run: bool = False,
    include_zero: bool = False,
    prompt_version: str = "v2-backfill",
) -> None:
    """Run the backfill pass.

    Uses the DB as a live queue: each iteration fetches the next batch of
    headwords that still need translations, so memory stays constant regardless
    of corpus size. Safe to interrupt and resume — completed work persists.
    """
    from tools.dictmaster.translate.minimax_api import _chat

    conn = get_connection(db_path)
    ensure_source(conn, "minimax")

    total, missing_count = count_partial_entries(conn, include_zero=include_zero)
    if limit:
        total = min(total, limit)

    print(f"Backfill: {total:,} headwords with partial coverage", flush=True)
    print(f"  Total missing definition slots: {sum(missing_count.values()):,}", flush=True)
    print(f"  Per-lang gaps:", flush=True)
    for lang in ALL_TARGET_LANGS:
        if missing_count[lang] > 0:
            print(f"    {lang}: {missing_count[lang]:,}", flush=True)

    if dry_run:
        print("\n  [DRY RUN] Would backfill the above. Exiting.")
        conn.close()
        return

    print(f"\n  Starting backfill ({workers} workers, batch size {batch_size})...", flush=True)
    t_start = time.time()
    filled_defs = 0
    filled_entries = 0
    processed = 0

    def _translate_one_batch(batch: list[dict]) -> list[dict[str, str]]:
        """Send a single backfill batch to the API. Thread-safe."""
        prompt = build_backfill_batch_prompt(batch)
        avg_missing = sum(len(e["missing_langs"]) for e in batch) / len(batch)
        max_tokens = max(2048, int(len(batch) * avg_missing * 80))
        response = _chat(BACKFILL_SYSTEM_PROMPT, prompt, max_tokens=min(max_tokens, 8192))
        return parse_backfill_response(response, len(batch), batch)

    def _save_results(batch: list[dict], results: list[dict[str, str]]):
        nonlocal filled_defs, filled_entries
        for entry, lang_defs in zip(batch, results):
            if not lang_defs:
                continue
            saved_any = False
            for lang, defn in lang_defs.items():
                if defn and lang in entry["missing_langs"]:
                    existing = conn.execute(
                        "SELECT 1 FROM definitions WHERE headword_id = ? AND lang = ? AND source = 'minimax'",
                        (entry["headword_id"], lang),
                    ).fetchone()
                    if existing:
                        continue
                    upsert_definition(
                        conn, entry["headword_id"], lang, defn, "minimax",
                        confidence="medium", prompt_version=prompt_version,
                    )
                    filled_defs += 1
                    saved_any = True
            if saved_any:
                filled_entries += 1

    def _log_progress():
        elapsed = time.time() - t_start
        rate = processed / elapsed if elapsed > 0 else 0
        remaining = total - processed
        eta = remaining / rate if rate > 0 else 0
        print(
            f"    [{processed:,}/{total:,}] "
            f"{filled_entries:,} entries, {filled_defs:,} defs filled "
            f"({rate:.1f} entries/s, ETA {eta / 60:.1f}m)",
            flush=True,
        )

    if workers <= 1:
        while processed < total:
            batch = fetch_batch(conn, batch_size, include_zero=include_zero)
            if not batch:
                break
            try:
                results = _translate_one_batch(batch)
            except Exception as e:
                print(f"    ERROR: {e}", flush=True)
                continue
            _save_results(batch, results)
            conn.commit()
            processed += len(batch)
            _log_progress()
    else:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Fetch a working set from DB — enough to keep workers busy
        fetch_size = min(workers * batch_size * 2, total - processed)
        working_set = fetch_batch(conn, fetch_size, include_zero=include_zero)

        executor = ThreadPoolExecutor(max_workers=workers)
        pending: dict = {}       # future -> batch
        ws_idx = 0

        def _submit_from_working_set():
            nonlocal ws_idx
            while len(pending) < workers * 2 and ws_idx < len(working_set):
                batch = working_set[ws_idx:ws_idx + batch_size]
                if not batch:
                    break
                fut = executor.submit(_translate_one_batch, batch)
                pending[fut] = batch
                ws_idx += batch_size

        _submit_from_working_set()

        while pending:
            for fut in as_completed(pending):
                batch = pending.pop(fut)
                try:
                    results = fut.result()
                    _save_results(batch, results)
                except Exception as e:
                    print(f"    ERROR: {e}", flush=True)

                processed += len(batch)

                # Refill working set from DB when all submitted
                if ws_idx >= len(working_set) and not pending and processed < total:
                    conn.commit()
                    remaining = total - processed
                    working_set = fetch_batch(conn, min(fetch_size, remaining), include_zero=include_zero)
                    ws_idx = 0

                _submit_from_working_set()

                if processed % (batch_size * 10) < batch_size:
                    conn.commit()
                    _log_progress()
                break  # process one future at a time

        conn.commit()
        executor.shutdown(wait=False)

    conn.close()
    elapsed = time.time() - t_start
    print(
        f"\n  Done: {filled_entries:,} entries, {filled_defs:,} definitions filled "
        f"in {elapsed / 60:.1f}m"
    )


def main():
    parser = argparse.ArgumentParser(description="Backfill missing language definitions")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="Database path")
    parser.add_argument("--batch-size", type=int, default=20, help="Entries per API call")
    parser.add_argument("--workers", type=int, default=1, help="Parallel workers")
    parser.add_argument("--limit", type=int, default=None, help="Max entries to process")
    parser.add_argument("--dry-run", action="store_true", help="Show stats without translating")
    parser.add_argument("--include-zero", action="store_true",
                        help="Also retry headwords with zero definitions")
    args = parser.parse_args()

    print("Step: Backfill missing languages")
    run_backfill(
        db_path=args.db,
        batch_size=args.batch_size,
        workers=args.workers,
        limit=args.limit,
        dry_run=args.dry_run,
        include_zero=args.include_zero,
    )


if __name__ == "__main__":
    main()
