#!/usr/bin/env python3
"""Audit and clean up script contamination in minimax definitions.

Phase 1 (--audit):  Scan all minimax definitions, report contamination counts.
Phase 2 (--delete): Delete contaminated definitions (creates gaps for backfill).
Phase 3 (--retranslate): Re-translate deleted slots using backfill_langs.py
                         with the script validator active as a hard gate.

The delete step is safe: it only removes minimax definitions, never community
dictionary entries.  The re-translation step feeds the rest of each row's
good definitions as context so replacements stay semantically consistent.

Usage:
    # Audit only — see what's contaminated
    python tools/dictmaster/cleanup_contamination.py --audit

    # Delete contaminated definitions (backup first!)
    python tools/dictmaster/cleanup_contamination.py --delete

    # Re-translate the gaps (calls minimax API)
    python tools/dictmaster/cleanup_contamination.py --retranslate --workers 20

    # All three phases in sequence
    python tools/dictmaster/cleanup_contamination.py --audit --delete --retranslate --workers 20
"""

import argparse
import sqlite3
import time
from collections import Counter, defaultdict
from pathlib import Path

from tools.dictmaster.schema import DEFAULT_DB_PATH, get_connection
from tools.dictmaster.script_validator import validate_definition
from tools.dictmaster.translate.prompts import ALL_TARGET_LANGS


# ---------------------------------------------------------------------------
# Phase 1: Audit
# ---------------------------------------------------------------------------

def audit_contamination(
    conn: sqlite3.Connection,
    verbose: bool = True,
) -> dict[str, list[dict]]:
    """Scan all minimax definitions for script contamination.

    Returns {lang: [{"def_id", "headword_id", "trad", "simp", "defn", "bad_scripts"}, ...]}
    """
    contaminated: dict[str, list[dict]] = defaultdict(list)
    lang_totals: Counter = Counter()
    lang_bad: Counter = Counter()

    for lang in ALL_TARGET_LANGS:
        rows = conn.execute("""
            SELECT d.id, d.headword_id, h.traditional, h.simplified, d.definition
            FROM definitions d
            JOIN headwords h ON h.id = d.headword_id
            WHERE d.lang = ? AND d.source = 'minimax'
        """, (lang,)).fetchall()

        lang_totals[lang] = len(rows)
        for row in rows:
            def_id, hw_id, trad, simp, defn = row
            if not defn:
                continue
            ok, bad_scripts = validate_definition(lang, defn)
            if not ok:
                lang_bad[lang] += 1
                contaminated[lang].append({
                    "def_id": def_id,
                    "headword_id": hw_id,
                    "trad": trad,
                    "simp": simp,
                    "defn": defn,
                    "bad_scripts": bad_scripts,
                })

    if verbose:
        total_bad = sum(lang_bad.values())
        total_defs = sum(lang_totals.values())
        print(f"\n=== Contamination Audit ===")
        print(f"Total definitions scanned: {total_defs:,}")
        print(f"Total contaminated:        {total_bad:,} ({total_bad/total_defs*100:.2f}%)")
        print()
        print(f"{'Lang':<6} {'Contaminated':>12} {'Total':>10} {'Rate':>8}")
        print("-" * 40)
        for lang in sorted(lang_bad, key=lambda x: lang_bad[x], reverse=True):
            bad = lang_bad[lang]
            tot = lang_totals[lang]
            print(f"{lang:<6} {bad:>12,} {tot:>10,} {bad/tot*100:>7.2f}%")

        # Break down by invalid script type
        print(f"\nContamination by script type:")
        script_counts: Counter = Counter()
        for lang, entries in contaminated.items():
            for e in entries:
                for s in e["bad_scripts"]:
                    script_counts[(lang, s)] += 1

        for (lang, script), count in script_counts.most_common(30):
            print(f"  {lang} ← {script}: {count:,}")

        # Show examples
        print(f"\nExamples (3 per worst language):")
        for lang in sorted(lang_bad, key=lambda x: lang_bad[x], reverse=True)[:5]:
            print(f"\n  {lang.upper()}:")
            for e in contaminated[lang][:3]:
                scripts = ",".join(e["bad_scripts"])
                print(f"    {e['simp']}: [{scripts}] {e['defn'][:80]}")

    return dict(contaminated)


# ---------------------------------------------------------------------------
# Phase 2: Delete contaminated definitions
# ---------------------------------------------------------------------------

def delete_contaminated(
    conn: sqlite3.Connection,
    contaminated: dict[str, list[dict]],
    dry_run: bool = False,
) -> int:
    """Delete contaminated minimax definitions from the database.

    Returns count of deleted rows.
    """
    total = sum(len(v) for v in contaminated.values())
    if total == 0:
        print("No contaminated definitions to delete.")
        return 0

    print(f"\n=== Delete Phase ===")
    print(f"Definitions to delete: {total:,}")

    if dry_run:
        print("[DRY RUN] Would delete the above. Exiting.")
        return 0

    deleted = 0
    for lang, entries in contaminated.items():
        def_ids = [e["def_id"] for e in entries]
        for i in range(0, len(def_ids), 500):
            batch = def_ids[i:i + 500]
            placeholders = ",".join("?" * len(batch))
            conn.execute(
                f"DELETE FROM definitions WHERE id IN ({placeholders})",
                batch,
            )
            deleted += len(batch)

    conn.commit()
    print(f"Deleted {deleted:,} contaminated definitions.")

    # Verify gaps
    gap_count = 0
    target_count = len(ALL_TARGET_LANGS)
    rows = conn.execute("""
        SELECT COUNT(*) FROM (
            SELECT h.id
            FROM headwords h
            JOIN definitions d ON d.headword_id = h.id AND d.source = 'minimax'
            GROUP BY h.id
            HAVING COUNT(DISTINCT d.lang) < ?
        )
    """, (target_count,)).fetchone()
    gap_count = rows[0] if rows else 0
    print(f"Headwords now needing backfill: {gap_count:,}")

    return deleted


# ---------------------------------------------------------------------------
# Phase 3: Re-translate using backfill with validator
# ---------------------------------------------------------------------------

def retranslate_gaps(
    db_path: Path,
    workers: int = 1,
    batch_size: int = 20,
) -> None:
    """Re-translate gaps left by deletion using the backfill pipeline.

    The backfill script already:
    - Finds headwords with < 18 languages
    - Sends existing good definitions as context
    - And now has the script validator integrated as a hard gate
    """
    from tools.dictmaster.backfill_langs import run_backfill

    print(f"\n=== Re-translate Phase ===")
    print(f"Running backfill with validator active ({workers} workers)...")
    run_backfill(
        db_path=db_path,
        batch_size=batch_size,
        workers=workers,
        prompt_version="v5-decontam",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Audit and clean up script contamination in dictionary definitions"
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--audit", action="store_true", help="Phase 1: scan and report")
    parser.add_argument("--delete", action="store_true", help="Phase 2: delete contaminated defs")
    parser.add_argument("--retranslate", action="store_true", help="Phase 3: re-translate gaps")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--workers", type=int, default=1, help="Workers for re-translation")
    parser.add_argument("--batch-size", type=int, default=20, help="Batch size for re-translation")
    args = parser.parse_args()

    if not (args.audit or args.delete or args.retranslate):
        args.audit = True

    conn = get_connection(args.db)

    contaminated = {}
    if args.audit or args.delete:
        contaminated = audit_contamination(conn, verbose=True)

    if args.delete:
        if not contaminated:
            contaminated = audit_contamination(conn, verbose=False)
        delete_contaminated(conn, contaminated, dry_run=args.dry_run)

    conn.close()

    if args.retranslate and not args.dry_run:
        retranslate_gaps(
            db_path=args.db,
            workers=args.workers,
            batch_size=args.batch_size,
        )


if __name__ == "__main__":
    main()
