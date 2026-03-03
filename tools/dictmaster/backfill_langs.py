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
them with the target language equivalent.

Language-specific rules:
- ja (Japanese): Provide the MEANING in Japanese, not just kanji echo or kana \
reading. Write a Japanese definition/gloss that explains the word. Use native \
Japanese vocabulary.
- ko (Korean): Write in Hangul only. Do NOT mix in Chinese characters (漢字/한자).
- tl (Tagalog): Use natural Tagalog vocabulary. Do NOT produce literal \
word-for-word translations from English.
- fa (Persian): Write definitions in Persian script (فارسی). Use native Persian \
vocabulary.
- vi (Vietnamese): Write in Vietnamese with proper diacritics. Do NOT include \
Chinese characters."""

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

def get_partial_entries(conn: sqlite3.Connection, include_zero: bool = False) -> list[dict]:
    """Find headwords with < 12 minimax langs."""
    if include_zero:
        # Include headwords with 0 defs too
        rows = conn.execute("""
            SELECT h.id, h.traditional, h.simplified, h.pinyin,
                   COALESCE(GROUP_CONCAT(d.lang), '') as existing_langs
            FROM headwords h
            LEFT JOIN definitions d ON d.headword_id = h.id AND d.source = 'minimax'
            GROUP BY h.id
            HAVING COUNT(DISTINCT d.lang) < 12
            ORDER BY COUNT(DISTINCT d.lang) DESC, h.id
        """).fetchall()
    else:
        # Only headwords that have SOME defs but not all 12
        rows = conn.execute("""
            SELECT h.id, h.traditional, h.simplified, h.pinyin,
                   GROUP_CONCAT(d.lang) as existing_langs
            FROM headwords h
            JOIN definitions d ON d.headword_id = h.id AND d.source = 'minimax'
            GROUP BY h.id
            HAVING COUNT(DISTINCT d.lang) < 12
            ORDER BY COUNT(DISTINCT d.lang) DESC, h.id
        """).fetchall()

    entries = []
    for row in rows:
        present = set(row["existing_langs"].split(",")) if row["existing_langs"] else set()
        present.discard("")  # clean up empty strings
        missing = sorted(ALL_LANGS_SET - present)
        entries.append({
            "headword_id": row["id"],
            "traditional": row["traditional"],
            "simplified": row["simplified"],
            "pinyin": row["pinyin"] or "",
            "missing_langs": missing,
            "existing_lang_set": present,
        })
    return entries


def load_existing_defs(conn: sqlite3.Connection, headword_id: int) -> dict[str, str]:
    """Fetch existing minimax definitions for context."""
    rows = conn.execute(
        "SELECT lang, definition FROM definitions WHERE headword_id = ? AND source = 'minimax'",
        (headword_id,),
    ).fetchall()
    return {r["lang"]: r["definition"] for r in rows}


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
    """Run the backfill pass."""
    from tools.dictmaster.translate.minimax_api import _chat

    conn = get_connection(db_path)
    ensure_source(conn, "minimax")

    entries = get_partial_entries(conn, include_zero=include_zero)
    if limit:
        entries = entries[:limit]

    total = len(entries)
    missing_count = Counter()
    for e in entries:
        for lang in e["missing_langs"]:
            missing_count[lang] += 1

    print(f"Backfill: {total:,} headwords with partial coverage")
    print(f"  Total missing definition slots: {sum(missing_count.values()):,}")
    print(f"  Per-lang gaps:")
    for lang in ALL_TARGET_LANGS:
        if missing_count[lang] > 0:
            print(f"    {lang}: {missing_count[lang]:,}")

    if dry_run:
        print("\n  [DRY RUN] Would backfill the above. Exiting.")
        conn.close()
        return

    # Load existing defs for all entries (main thread)
    print(f"\n  Loading existing definitions...")
    for e in entries:
        e["existing_defs"] = load_existing_defs(conn, e["headword_id"])

    print(f"  Starting backfill ({workers} workers, batch size {batch_size})...")
    t_start = time.time()
    filled_defs = 0
    filled_entries = 0

    def _translate_one_batch(batch: list[dict]) -> list[dict[str, str]]:
        """Send a single backfill batch to the API. Thread-safe."""
        prompt = build_backfill_batch_prompt(batch)
        # Estimate tokens: existing defs ~150 tok/entry, missing ~30 tok/lang output
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
                    # Safety: verify this definition doesn't already exist in DB
                    existing = conn.execute(
                        "SELECT 1 FROM definitions WHERE headword_id = ? AND lang = ? AND source = 'minimax'",
                        (entry["headword_id"], lang),
                    ).fetchone()
                    if existing:
                        continue  # already has this lang — never overwrite
                    upsert_definition(
                        conn, entry["headword_id"], lang, defn, "minimax",
                        confidence="medium", prompt_version=prompt_version,
                    )
                    filled_defs += 1
                    saved_any = True
            if saved_any:
                filled_entries += 1

    if workers <= 1:
        for i in range(0, total, batch_size):
            batch = entries[i:i + batch_size]
            try:
                results = _translate_one_batch(batch)
            except Exception as e:
                print(f"    ERROR at batch {i}: {e}")
                continue

            _save_results(batch, results)
            conn.commit()

            done = min(i + batch_size, total)
            elapsed = time.time() - t_start
            rate = done / elapsed if elapsed > 0 else 0
            eta = (total - done) / rate if rate > 0 else 0
            print(
                f"    [{done:,}/{total:,}] "
                f"{filled_entries:,} entries, {filled_defs:,} defs filled "
                f"({rate:.1f} entries/s, ETA {eta / 60:.1f}m)"
            )
    else:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        executor = ThreadPoolExecutor(max_workers=workers)
        pending = {}
        batch_map = {}
        next_idx = 0
        completed_since_commit = 0
        progress_interval = batch_size * 10

        # Pre-submit initial batches
        for _ in range(min(workers * 2, (total + batch_size - 1) // batch_size)):
            if next_idx >= total:
                break
            batch = entries[next_idx:next_idx + batch_size]
            batch_map[next_idx] = batch
            fut = executor.submit(_translate_one_batch, batch)
            pending[fut] = next_idx
            next_idx += batch_size

        while pending:
            done_futures = set()
            for fut in as_completed(pending):
                done_futures.add(fut)
                break

            for fut in done_futures:
                bidx = pending.pop(fut)
                batch = batch_map.pop(bidx)
                try:
                    results = fut.result()
                    _save_results(batch, results)
                    completed_since_commit += 1
                except Exception as e:
                    print(f"    ERROR at batch {bidx}: {e}")

                if next_idx < total:
                    new_batch = entries[next_idx:next_idx + batch_size]
                    batch_map[next_idx] = new_batch
                    new_fut = executor.submit(_translate_one_batch, new_batch)
                    pending[new_fut] = next_idx
                    next_idx += batch_size

            if completed_since_commit >= workers * 2:
                conn.commit()
                completed_since_commit = 0

            done = filled_entries
            if done % progress_interval < batch_size or not pending:
                elapsed = time.time() - t_start
                rate = done / elapsed if elapsed > 0 else 0
                eta = (total - done) / rate if rate > 0 else 0
                print(
                    f"    [{done:,}/{total:,}] "
                    f"{filled_entries:,} entries, {filled_defs:,} defs filled "
                    f"({rate:.1f} entries/s, ETA {eta / 60:.1f}m)"
                )

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
