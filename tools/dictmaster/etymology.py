"""Cross-dialect etymology lookup for the dictmaster dictionary.

Given a Chinese word, shows the full chain: Mandarin → Cantonese → Hokkien,
plus definitions in SE Asian languages (Vietnamese, Indonesian, Tagalog) that
reveal Hokkien loanword connections.

Usage:
    PYTHONPATH=. python tools/dictmaster/etymology.py 豆腐
    PYTHONPATH=. python tools/dictmaster/etymology.py 謝謝 媽媽 漂亮
    PYTHONPATH=. python tools/dictmaster/etymology.py --all-langs 銀行
"""

import sqlite3
from pathlib import Path
from typing import Optional

from tools.dictmaster.schema import DEFAULT_DB_PATH, get_connection

# Languages to highlight in SE Asian context section
SE_ASIAN_LANGS = ["vi", "id", "tl"]
# All other foreign languages
OTHER_LANGS = ["en", "de", "fr", "es", "sv", "ja", "ko", "ru"]

LANG_DISPLAY = {
    "en": "English",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "sv": "Swedish",
    "ja": "Japanese",
    "ko": "Korean",
    "ru": "Russian",
    "id": "Indonesian",
    "vi": "Vietnamese",
    "tl": "Tagalog",
}


def lookup_etymology(
    conn: sqlite3.Connection,
    word: str,
) -> list[dict]:
    """Look up a word and return full etymology data.

    Searches both traditional and simplified forms.
    Returns list of dicts (multiple if word has multiple headword entries).
    """
    rows = conn.execute(
        "SELECT id, traditional, simplified, pinyin, pos FROM headwords "
        "WHERE traditional = ? OR simplified = ?",
        (word, word),
    ).fetchall()

    if not rows:
        return []

    results = []
    for hw in rows:
        hw_id = hw["id"]

        # Gather definitions by language (pick best source per lang)
        defs = {}
        for d in conn.execute(
            "SELECT lang, definition, source FROM definitions "
            "WHERE headword_id = ? ORDER BY lang",
            (hw_id,),
        ).fetchall():
            lang = d["lang"]
            if lang not in defs:
                defs[lang] = {"text": d["definition"], "source": d["source"]}

        # Gather dialect forms (pick best source per dialect)
        dialects = {}
        for df in conn.execute(
            "SELECT dialect, pronunciation, native_chars, gloss, source "
            "FROM dialect_forms WHERE headword_id = ? ORDER BY dialect",
            (hw_id,),
        ).fetchall():
            dialect = df["dialect"]
            if dialect not in dialects:
                dialects[dialect] = {
                    "pronunciation": df["pronunciation"],
                    "native_chars": df["native_chars"],
                    "gloss": df["gloss"],
                    "source": df["source"],
                }

        results.append({
            "traditional": hw["traditional"],
            "simplified": hw["simplified"],
            "pinyin": hw["pinyin"],
            "pos": hw["pos"],
            "definitions": defs,
            "dialects": dialects,
        })

    return results


def format_etymology(entry: dict, all_langs: bool = False) -> str:
    """Format an etymology entry as human-readable text.

    Default: shows Mandarin → dialects → SE Asian languages.
    With all_langs=True: shows all available languages.
    """
    lines = []
    trad = entry["traditional"]
    simp = entry["simplified"]
    pinyin = entry["pinyin"]
    pos = entry["pos"] or ""

    # Header
    if trad != simp:
        header = f"{trad} / {simp}  [{pinyin}]"
    else:
        header = f"{trad}  [{pinyin}]"
    if pos:
        header += f"  ({pos})"
    lines.append(header)

    # English definition (always show)
    en_def = entry["definitions"].get("en")
    if en_def:
        lines.append(f"  {_clean_cedict_def(en_def['text'])}")
    lines.append("")

    # Dialect section
    yue = entry["dialects"].get("yue")
    nan = entry["dialects"].get("nan")

    if yue or nan:
        lines.append("  Dialects")
        if yue:
            yue_line = f"    Cantonese:  {yue['pronunciation']}"
            if yue["native_chars"]:
                yue_line += f"  ({yue['native_chars']})"
            lines.append(yue_line)

        if nan:
            nan_line = f"    Hokkien:    {nan['pronunciation']}"
            if nan["native_chars"]:
                nan_line += f"  ({nan['native_chars']})"
            lines.append(nan_line)
        lines.append("")

    # SE Asian languages (the loanword connection)
    se_asian_defs = {
        lang: entry["definitions"][lang]
        for lang in SE_ASIAN_LANGS
        if lang in entry["definitions"]
    }
    if se_asian_defs:
        lines.append("  Southeast Asian")
        for lang in SE_ASIAN_LANGS:
            if lang in se_asian_defs:
                d = se_asian_defs[lang]
                text = _clean_cedict_def(d["text"])
                lines.append(f"    {LANG_DISPLAY[lang]:12s}  {text}")
        lines.append("")

    # Other languages (if requested)
    if all_langs:
        other_defs = {
            lang: entry["definitions"][lang]
            for lang in OTHER_LANGS
            if lang in entry["definitions"] and lang != "en"
        }
        if other_defs:
            lines.append("  Other Languages")
            for lang in OTHER_LANGS:
                if lang in other_defs and lang != "en":
                    d = other_defs[lang]
                    text = _clean_cedict_def(d["text"])
                    lines.append(f"    {LANG_DISPLAY[lang]:12s}  {text}")
            lines.append("")

    return "\n".join(lines)


def _clean_cedict_def(text: str) -> str:
    """Clean up CEDICT-style definitions for display.

    Removes classifier annotations like CL:家[jia1],個|个[ge4]
    and KP: (Indonesian equivalent).
    """
    import re
    # Remove /CL:.../ or /KP:.../ classifier annotations
    text = re.sub(r'/CL:[^/]*', '', text)
    text = re.sub(r'/KP:[^/]*', '', text)
    # Clean up double slashes
    text = re.sub(r'/{2,}', '/', text)
    text = text.strip('/')
    return text


def etymology_report(
    conn: sqlite3.Connection,
    words: list[str],
    all_langs: bool = False,
) -> str:
    """Generate etymology report for multiple words."""
    blocks = []
    for word in words:
        results = lookup_etymology(conn, word)
        if not results:
            blocks.append(f"{word}  (not found)\n")
            continue
        for entry in results:
            blocks.append(format_etymology(entry, all_langs=all_langs))
    return "\n".join(blocks)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Cross-dialect Chinese etymology lookup"
    )
    parser.add_argument("words", nargs="+", help="Chinese words to look up")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--all-langs", action="store_true",
                        help="Show all available languages, not just SE Asian")
    args = parser.parse_args()

    conn = get_connection(args.db)
    print(etymology_report(conn, args.words, all_langs=args.all_langs))
    conn.close()


if __name__ == "__main__":
    main()
