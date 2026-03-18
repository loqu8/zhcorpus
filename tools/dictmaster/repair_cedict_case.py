"""Repair CC-CEDICT definitions lost to case-folding in reconcile_headwords().

Root cause: reconcile_headwords() used LOWER() on pinyin, collapsing
case-distinguished entries (He2 = surname vs he2 = common word).
UPDATE OR IGNORE silently dropped ~1,102 common-word definitions.

This script:
1. Parses raw CC-CEDICT and compares against dictmaster.db
2. Re-inserts missing headwords + definitions
3. Removes bogus Wiktextract entries with CJK Extension G simplified forms (𰵝 etc.)

Usage:
    python -m tools.dictmaster.repair_cedict_case [--dry-run]
"""

import argparse
import shutil
import sqlite3
import sys
from pathlib import Path

from tools.dictmaster.parsers.cedict_format import iter_cedict, infer_pos
from tools.dictmaster.schema import DEFAULT_DB_PATH


def repair_cedict_case(db_path: Path, cedict_path: Path, *, dry_run: bool = False) -> dict:
    """Restore CC-CEDICT definitions lost to case-folding.

    Returns dict with repair statistics.
    """
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row

    stats = {
        "cedict_entries": 0,
        "already_present": 0,
        "headwords_created": 0,
        "definitions_restored": 0,
        "proper_nouns": 0,
        "common_words": 0,
    }

    # Build lookup of existing headwords: (trad, simp, pinyin) -> id
    existing = {}
    for row in conn.execute("SELECT id, traditional, simplified, pinyin FROM headwords"):
        existing[(row["traditional"], row["simplified"], row["pinyin"])] = row["id"]

    # Build set of existing cedict definitions: set of headword_ids
    has_cedict_def = set()
    for row in conn.execute(
        "SELECT headword_id FROM definitions WHERE lang = 'en' AND source = 'cedict'"
    ):
        has_cedict_def.add(row["headword_id"])

    # Parse raw CEDICT and categorize entries
    missing_headwords = []  # headword doesn't exist at all
    missing_defs = []       # headword exists but cedict definition is missing
    for entry in iter_cedict(cedict_path):
        stats["cedict_entries"] += 1
        key = (entry.traditional, entry.simplified, entry.pinyin)
        hw_id = existing.get(key)
        if hw_id is None:
            missing_headwords.append(entry)
        elif hw_id not in has_cedict_def:
            missing_defs.append((hw_id, entry))
            stats["already_present"] += 1
        else:
            stats["already_present"] += 1

    print(f"Raw CEDICT entries: {stats['cedict_entries']}")
    print(f"Already complete: {stats['already_present']}")
    print(f"Missing headwords: {len(missing_headwords)}")
    print(f"Missing cedict definitions (headword exists): {len(missing_defs)}")

    if not missing_headwords and not missing_defs:
        print("Nothing to repair.")
        conn.close()
        return stats

    # Show samples
    if missing_headwords:
        print("\nSample missing headwords:")
        for entry in missing_headwords[:10]:
            is_proper = entry.pinyin[0].isupper() if entry.pinyin else False
            tag = "[proper]" if is_proper else "[common]"
            print(f"  {tag} {entry.traditional} {entry.simplified} [{entry.pinyin}] "
                  f"/{entry.definition[:60]}/")
        if len(missing_headwords) > 10:
            print(f"  ... and {len(missing_headwords) - 10} more")

    if missing_defs:
        print("\nSample missing definitions (headword exists):")
        for hw_id, entry in missing_defs[:10]:
            print(f"  hw_id={hw_id} {entry.simplified} [{entry.pinyin}] "
                  f"/{entry.definition[:60]}/")
        if len(missing_defs) > 10:
            print(f"  ... and {len(missing_defs) - 10} more")

    if dry_run:
        print("\n--dry-run: no changes made")
        conn.close()
        return stats

    # Insert missing headwords + their definitions
    for entry in missing_headwords:
        is_proper = entry.pinyin[0].isupper() if entry.pinyin else False
        if is_proper:
            stats["proper_nouns"] += 1
        else:
            stats["common_words"] += 1

        pos = infer_pos(entry.definition)
        conn.execute(
            "INSERT OR IGNORE INTO headwords (traditional, simplified, pinyin, pos) "
            "VALUES (?, ?, ?, ?)",
            (entry.traditional, entry.simplified, entry.pinyin, pos),
        )
        row = conn.execute(
            "SELECT id FROM headwords WHERE traditional = ? AND simplified = ? AND pinyin = ?",
            (entry.traditional, entry.simplified, entry.pinyin),
        ).fetchone()
        if row:
            hw_id = row["id"]
            stats["headwords_created"] += 1
            conn.execute(
                "INSERT OR IGNORE INTO definitions (headword_id, lang, definition, source) "
                "VALUES (?, 'en', ?, 'cedict')",
                (hw_id, entry.definition),
            )
            stats["definitions_restored"] += 1

    # Insert missing definitions for existing headwords
    for hw_id, entry in missing_defs:
        conn.execute(
            "INSERT OR IGNORE INTO definitions (headword_id, lang, definition, source) "
            "VALUES (?, 'en', ?, 'cedict')",
            (hw_id, entry.definition),
        )
        stats["definitions_restored"] += 1

    conn.commit()
    print(f"\nRestored {stats['headwords_created']} headwords, "
          f"{stats['definitions_restored']} definitions")
    print(f"  Proper nouns: {stats['proper_nouns']}")
    print(f"  Common words: {stats['common_words']}")

    conn.close()
    return stats


def remove_bogus_simplified(db_path: Path, *, dry_run: bool = False) -> dict:
    """Remove Wiktextract entries with bogus CJK Extension G/H simplified forms.

    Characters like 𰵝 (U+30D5D, CJK Extension G) are not real simplified forms.
    They break HSK joins and pollute the dictionary.

    Returns dict with removal statistics.
    """
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row

    # Find headwords where simplified contains characters outside BMP + Extension A/B
    # CJK Extension G starts at U+30000, Extension H at U+31350
    # Real simplified characters are all in BMP (U+0000-U+FFFF) or Extension A (U+3400-U+4DBF)
    bogus = conn.execute("""
        SELECT h.id, h.traditional, h.simplified, h.pinyin,
               (SELECT COUNT(*) FROM definitions d WHERE d.headword_id = h.id) as def_count
        FROM headwords h
        WHERE h.simplified != h.traditional
          AND h.simplified LIKE '%' || CHAR(0xF0, 0xB0) || '%' ESCAPE '\\'
    """).fetchall()

    # The above SQL won't work for multi-byte detection. Use Python instead.
    bogus_ids = []
    bogus_entries = []
    for row in conn.execute(
        "SELECT id, traditional, simplified, pinyin FROM headwords"
    ):
        simp = row["simplified"]
        for ch in simp:
            cp = ord(ch)
            # CJK Extension G (U+30000–U+3134F), H (U+31350–U+323AF)
            # Also catch IDS sequences (⿰⿱ etc., U+2FF0–U+2FFF)
            if cp >= 0x30000 or (0x2FF0 <= cp <= 0x2FFF):
                bogus_ids.append(row["id"])
                bogus_entries.append(
                    (row["id"], row["traditional"], row["simplified"], row["pinyin"])
                )
                break

    stats = {
        "bogus_headwords": len(bogus_ids),
        "definitions_deleted": 0,
        "dialect_forms_deleted": 0,
    }

    if not bogus_ids:
        print("No bogus simplified forms found.")
        conn.close()
        return stats

    print(f"Found {len(bogus_ids)} headwords with bogus simplified forms:")
    for hw_id, trad, simp, pinyin in bogus_entries[:20]:
        print(f"  id={hw_id} trad={trad} simp={simp} [{pinyin}]")
    if len(bogus_entries) > 20:
        print(f"  ... and {len(bogus_entries) - 20} more")

    if dry_run:
        print("\n--dry-run: no changes made")
        conn.close()
        return stats

    # Delete definitions and dialect forms first (foreign key refs)
    for hw_id in bogus_ids:
        dc = conn.execute(
            "DELETE FROM definitions WHERE headword_id = ?", (hw_id,)
        ).rowcount
        stats["definitions_deleted"] += dc

        dfc = conn.execute(
            "DELETE FROM dialect_forms WHERE headword_id = ?", (hw_id,)
        ).rowcount
        stats["dialect_forms_deleted"] += dfc

    # Delete headwords
    placeholders = ",".join("?" * len(bogus_ids))
    conn.execute(f"DELETE FROM headwords WHERE id IN ({placeholders})", bogus_ids)
    conn.commit()

    print(f"\nDeleted {stats['bogus_headwords']} bogus headwords, "
          f"{stats['definitions_deleted']} definitions, "
          f"{stats['dialect_forms_deleted']} dialect forms")

    conn.close()
    return stats


def verify_key_entries(db_path: Path) -> bool:
    """Verify key entries are correct after repair."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    checks = [
        ("和", "he2", "and", "common word 'and/harmonious'"),
        ("和", "He2", "surname", "surname He"),
        ("三", "san1", "three", "common word 'three'"),
        ("中", "zhong1", "middle", "common word 'middle/center'"),
    ]

    all_ok = True
    print("\nVerification:")
    for simp, pinyin, must_contain, label in checks:
        # Check all definitions for this headword+pinyin, looking for a match
        rows = conn.execute(
            "SELECT h.traditional, d.definition FROM headwords h "
            "JOIN definitions d ON d.headword_id = h.id "
            "WHERE h.simplified = ? AND h.pinyin = ? AND d.lang = 'en' AND d.source = 'cedict'",
            (simp, pinyin),
        ).fetchall()

        found = any(must_contain.lower() in r["definition"].lower() for r in rows)
        if found:
            print(f"  OK  {simp} [{pinyin}]: {label}")
        elif rows:
            defs = "; ".join(r["definition"][:40] for r in rows)
            print(f"  !!  {simp} [{pinyin}]: found but missing '{must_contain}': {defs}")
            all_ok = False
        else:
            print(f"  FAIL {simp} [{pinyin}]: {label} — NOT FOUND")
            all_ok = False

    # Check 𰵝 is gone
    bogus = conn.execute(
        "SELECT COUNT(*) FROM headwords WHERE simplified = '𰵝'"
    ).fetchone()[0]
    if bogus == 0:
        print("  OK  No 𰵝 bogus entries")
    else:
        print(f"  FAIL {bogus} bogus 𰵝 entries remain")
        all_ok = False

    conn.close()
    return all_ok


def main():
    parser = argparse.ArgumentParser(description="Repair CC-CEDICT case-folding data loss")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH,
                        help="Path to dictmaster.db")
    parser.add_argument("--cedict", type=Path,
                        default=Path("data/raw/cedict_1_0_ts_utf-8_mdbg.txt"),
                        help="Path to raw CC-CEDICT file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without making changes")
    parser.add_argument("--skip-backup", action="store_true",
                        help="Skip creating a backup of dictmaster.db")
    args = parser.parse_args()

    if not args.db.exists():
        print(f"Error: database not found: {args.db}", file=sys.stderr)
        sys.exit(1)
    if not args.cedict.exists():
        print(f"Error: CEDICT file not found: {args.cedict}", file=sys.stderr)
        sys.exit(1)

    # Backup
    if not args.dry_run and not args.skip_backup:
        backup = args.db.with_suffix(".db.bak")
        print(f"Backing up {args.db} → {backup}")
        shutil.copy2(args.db, backup)

    # Phase 2: Restore missing CEDICT entries
    print("\n=== Phase 2: Restore case-collapsed CEDICT entries ===")
    repair_cedict_case(args.db, args.cedict, dry_run=args.dry_run)

    # Phase 3: Remove bogus Wiktextract simplified forms
    print("\n=== Phase 3: Remove bogus CJK Extension simplified forms ===")
    remove_bogus_simplified(args.db, dry_run=args.dry_run)

    # Verify
    if not args.dry_run:
        ok = verify_key_entries(args.db)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
