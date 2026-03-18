#!/usr/bin/env python3
"""Audit and repair language contamination in dictionary definitions.

This script finds definitions with incorrect script contamination (e.g., Cyrillic in non-Russian,
Greek letters mixed in, CJK characters in Latin scripts, etc.) and optionally repairs them.

Usage:
    # Dry run - show all contamination
    python tools/dictmaster/audit_and_repair.py

    # Show only Cyrillic contamination
    python tools/dictmaster/audit_and_repair.py --script cyrillic

    # Show statistics only
    python tools/dictmaster/audit_and_repair.py --stats

    # Repair mode - requires --lang and --script
    python tools/dictmaster/audit_and_repair.py --lang en --script cyrillic --repair
"""

import argparse
import sqlite3
from collections import defaultdict
from pathlib import Path


# Character ranges for each script/language family
SCRIPTS = {
    "latin": (0x0000, 0x024F),
    "cyrillic": (0x0400, 0x04FF),
    "arabic": (0x0600, 0x06FF),
    "persian": (0x0750, 0x077F, 0xFB50, 0xFDFF, 0xFE70, 0xFEFF),
    "devanagari": (0x0900, 0x097F),
    "thai": (0x0E00, 0x0E7F),
    "cjk": (0x4E00, 0x9FFF),
    "hangul": (0xAC00, 0xD7AF),
    "japanese": (0x3040, 0x309F, 0x30A0, 0x30FF),
    "hebrew": (0x0590, 0x05FF),
    "greek": (0x0370, 0x03FF),
}

# Which scripts are VALID for each language
LANGUAGE_VALID_SCRIPTS = {
    "en": ["latin"],
    "de": ["latin"],
    "fr": ["latin"],
    "es": ["latin"],
    "it": ["latin"],
    "pt": ["latin"],
    "sv": ["latin"],
    "ru": ["cyrillic", "latin"],
    "ar": ["arabic"],
    "fa": ["persian", "arabic"],
    "hi": ["devanagari"],
    "th": ["thai"],
    "ja": ["cjk", "japanese", "latin"],
    "ko": ["cjk", "hangul", "latin"],
    "vi": ["latin"],
    "id": ["latin"],
    "tl": ["latin"],
    "nl": ["latin"],
}


def detect_scripts(text: str) -> set[str]:
    """Detect which scripts are used in text."""
    if not text:
        return set()

    scripts = set()
    for char in text:
        code = ord(char)

        if 0x0000 <= code <= 0x024F:
            scripts.add("latin")
        elif 0x0400 <= code <= 0x04FF:
            scripts.add("cyrillic")
        elif 0x0600 <= code <= 0x06FF:
            scripts.add("arabic")
        elif 0x0750 <= code <= 0x077F:
            scripts.add("persian")
        elif 0xFB50 <= code <= 0xFDFF or 0xFE70 <= code <= 0xFEFF:
            scripts.add("persian")
        elif 0x0900 <= code <= 0x097F:
            scripts.add("devanagari")
        elif 0x0E00 <= code <= 0x0E7F:
            scripts.add("thai")
        elif 0x4E00 <= code <= 0x9FFF:
            scripts.add("cjk")
        elif 0xAC00 <= code <= 0xD7AF:
            scripts.add("hangul")
        elif 0x3040 <= code <= 0x309F or 0x30A0 <= code <= 0x30FF:
            scripts.add("japanese")
        elif 0x0590 <= code <= 0x05FF:
            scripts.add("hebrew")
        elif 0x0370 <= code <= 0x03FF:
            scripts.add("greek")

    return scripts


def check_contamination(db_path: Path, lang: str | None = None, script: str | None = None):
    """Check for language contamination."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    results = defaultdict(lambda: {"count": 0, "samples": []})

    # Get all languages if not specified
    if lang:
        languages = [lang]
    else:
        cur.execute("SELECT DISTINCT lang FROM definitions WHERE source = 'minimax'")
        languages = [r[0] for r in cur.fetchall()]

    for target_lang in languages:
        valid_scripts = set(LANGUAGE_VALID_SCRIPTS.get(target_lang, []))

        # Check definitions for this language
        cur.execute("""
            SELECT h.traditional, h.simplified, d.definition, d.headword_id, d.id
            FROM definitions d
            JOIN headwords h ON h.id = d.headword_id
            WHERE d.lang = ? AND d.source = 'minimax'
        """, (target_lang,))

        for row in cur.fetchall():
            trad, simp, defn, hw_id, def_id = row
            if not defn:
                continue

            detected = detect_scripts(defn)
            invalid = detected - valid_scripts

            if invalid:
                # Filter by specific script if requested
                if script and script not in invalid:
                    continue

                results[target_lang]["count"] += 1
                if len(results[target_lang]["samples"]) < 5:
                    results[target_lang]["samples"].append({
                        "trad": trad,
                        "simp": simp,
                        "defn": defn[:100],
                        "invalid": list(invalid),
                        "def_id": def_id
                    })

    conn.close()
    return dict(results)


def main():
    parser = argparse.ArgumentParser(description="Audit and repair language contamination")
    parser.add_argument("--db", type=Path, default=Path("data/artifacts/dictmaster.db"))
    parser.add_argument("--lang", type=str, default=None, help="Specific language to check")
    parser.add_argument("--script", type=str, default=None, help="Specific script to check (cyrillic, greek, etc)")
    parser.add_argument("--stats", action="store_true", help="Show statistics only")
    parser.add_argument("--repair", action="store_true", help="Repair mode (requires --lang and --script)")
    parser.add_argument("--limit", type=int, default=0, help="Limit results per language")
    args = parser.parse_args()

    print("=== Language Contamination Audit ===\n")

    results = check_contamination(args.db, args.lang, args.script)

    # Print results
    for lang in sorted(results.keys(), key=lambda x: results[x]["count"], reverse=True):
        data = results[lang]
        count = data["count"]

        if args.limit and count > args.limit:
            count = args.limit

        print(f"## {lang.upper()}: {count:,} contamination issues")

        if args.stats:
            continue

        # Show samples
        for sample in data["samples"][:5]:
            print(f"  - {sample['simp']}: [{', '.join(sample['invalid'])}]")
            print(f"    {sample['defn'][:70]}...")

        print()


if __name__ == "__main__":
    main()
