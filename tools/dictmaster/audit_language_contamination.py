#!/usr/bin/env python3
"""Detect language contamination in dictionary definitions.

Finds definitions that contain scripts/characters that don't belong to the target language.
This helps identify translation errors where the model mixed languages.

Usage:
    python tools/dictmaster/audit_language_contamination.py

    # Specific language
    python tools/dictmaster/audit_language_contamination.py --lang fa

    # With threshold (show only with >N issues)
    python tools/dictmaster/audit_language_contamination.py --min 10
"""

import argparse
import sqlite3
from collections import defaultdict
from pathlib import Path

# Character ranges for each script/language family
SCRIPTS = {
    # Latin scripts
    "latin": (0x0000, 0x024F),  # Basic Latin + Extended

    # Cyrillic (Russian, etc.)
    "cyrillic": (0x0400, 0x04FF),

    # Arabic
    "arabic": (0x0600, 0x06FF),

    # Persian (extended Arabic)
    "persian": (0x0750, 0x077F, 0xFB50, 0xFDFF, 0xFE70, 0xFEFF),

    # Devanagari (Hindi)
    "devanagari": (0x0900, 0x097F),

    # Thai
    "thai": (0x0E00, 0x0E7F),

    # Japanese/Chinese characters
    "cjk": (0x4E00, 0x9FFF),  # CJK Unified Ideographs

    # Hangul (Korean)
    "hangul": (0xAC00, 0xD7AF),

    # Hiragana/Katakana
    "japanese": (0x3040, 0x309F, 0x30A0, 0x30FF),

    # Hebrew
    "hebrew": (0x0590, 0x05FF),

    # Greek
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

    "ru": ["cyrillic", "latin"],  # Latin for abbreviations

    "ar": ["arabic"],
    "fa": ["persian", "arabic"],

    "hi": ["devanagari"],

    "th": ["thai"],

    "ja": ["cjk", "japanese", "latin"],  # Latin for loanwords
    "ko": ["cjk", "hangul", "latin"],

    "vi": ["latin"],  # Vietnamese uses Latin with diacritics

    "id": ["latin"],

    "tl": ["latin"],  # Tagalog

    "nl": ["latin"],
}


def detect_scripts(text: str) -> set[str]:
    """Detect which scripts are used in text."""
    if not text:
        return set()

    scripts = set()
    for char in text:
        code = ord(char)

        # Check each script range
        if 0x0000 <= code <= 0x024F:
            scripts.add("latin")
        elif 0x0400 <= code <= 0x04FF:
            scripts.add("cyrillic")
        elif 0x0600 <= code <= 0x06FF:
            scripts.add("arabic")
        elif 0x0750 <= code <= 0x077F:
            scripts.add("persian")
        elif 0xFB50 <= code <= 0xFDFF or 0xFE70 <= code <= 0xFEFF:
            scripts.add("persian")  # Extended Persian
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


def check_contamination(db_path: Path, lang: str | None = None, min_count: int = 0) -> dict:
    """Check for language contamination."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    results = defaultdict(lambda: defaultdict(list))

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
            SELECT h.traditional, h.simplified, d.definition, d.headword_id
            FROM definitions d
            JOIN headwords h ON h.id = d.headword_id
            WHERE d.lang = ? AND d.source = 'minimax'
        """, (target_lang,))

        issues = 0
        for row in cur.fetchall():
            trad, simp, defn, hw_id = row
            if not defn:
                continue

            detected = detect_scripts(defn)

            # Find invalid scripts
            invalid = detected - valid_scripts

            if invalid:
                issues += 1
                results[target_lang]["_invalid_scripts"].append({
                    "invalid": list(invalid),
                    "found": list(detected),
                    "trad": trad,
                    "defn": defn[:100],
                    "hw_id": hw_id
                })

                # Track each invalid script
                for script in invalid:
                    results[target_lang][f"script_{script}"].append({
                        "trad": trad,
                        "defn": defn[:100],
                        "hw_id": hw_id
                    })

        results[target_lang]["_total_issues"] = issues

    conn.close()
    return dict(results)


def main():
    parser = argparse.ArgumentParser(description="Audit language contamination")
    parser.add_argument("--db", type=Path, default=Path("data/artifacts/dictmaster.db"))
    parser.add_argument("--lang", type=str, default=None, help="Specific language to check")
    parser.add_argument("--min", type=int, default=0, help="Minimum issues to show")
    parser.add_argument("--show-examples", type=int, default=5, help="Examples to show per issue")
    args = parser.parse_args()

    print("=== Language Contamination Audit ===\n")

    results = check_contamination(args.db, args.lang, args.min)

    # Sort by total issues
    for lang in sorted(results.keys(), key=lambda x: results[x]["_total_issues"], reverse=True):
        data = results[lang]
        total = data["_total_issues"]

        if total < args.min:
            continue

        print(f"## {lang.upper()} ({total:,} issues)")

        # Group by invalid script type
        script_counts = {}
        for key, val in data.items():
            if key.startswith("script_"):
                script = key.replace("script_", "")
                script_counts[script] = len(val)

        for script, count in sorted(script_counts.items(), reverse=True):
            print(f"  {script}: {count:,}")

        # Show examples
        if args.show_examples > 0:
            examples = data.get("_invalid_scripts", [])[:args.show_examples]
            print(f"  Examples:")
            for ex in examples:
                print(f"    - {ex['trad']}: {ex['invalid']} in {ex['defn'][:60]}...")

        print()


if __name__ == "__main__":
    main()
