#!/usr/bin/env python3
"""
Paper B: Back-translation evaluation for non-community languages.

For languages without community dictionaries (es, ko, ru, vi, tl, fa, sv),
we back-translate the MiniMax definitions into English, then compare against
CC-CEDICT English definitions using the same gloss_overlap metrics.

This provides an indirect quality signal: if Spanish "banco/institución
financiera" back-translates to "bank/financial institution" and CC-CEDICT
says "bank/financial institution", we know the Spanish definition is reasonable.

Usage:
    .venv/bin/python tools/eval_backtranslation.py
    .venv/bin/python tools/eval_backtranslation.py --langs es,ko,ru
    .venv/bin/python tools/eval_backtranslation.py --limit 50
"""

import argparse
import json
import random
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path

from tools.eval_community_comparison import (
    BANDS,
    PER_BAND,
    split_glosses,
    gloss_overlap,
    get_frequency_bands,
    sample_headwords,
)

# Non-community languages to evaluate
NON_COMMUNITY_LANGS = {
    "es": "Spanish",
    "ko": "Korean",
    "ru": "Russian",
    "vi": "Vietnamese",
    "tl": "Tagalog",
    "fa": "Persian",
    "sv": "Swedish",
}

BACKTRANSLATE_SYSTEM = """\
You are a translator. Translate the following {lang_name} text into English.
Output ONLY the English translation, nothing else. Keep the same format
(slash-separated alternatives if the input has them). Be concise."""

BACKTRANSLATE_USER = "Translate to English: {text}"


def backtranslate_minimax(definition: str, source_lang: str) -> str:
    """Back-translate a non-English definition into English via MiniMax API."""
    from tools.dictmaster.translate.minimax_api import _chat

    lang_name = NON_COMMUNITY_LANGS.get(source_lang, source_lang)
    system = BACKTRANSLATE_SYSTEM.format(lang_name=lang_name)
    user = BACKTRANSLATE_USER.format(text=definition)

    try:
        response = _chat(system, user, max_tokens=256)
        return response.strip()
    except Exception as e:
        print(f"    Backtranslation error: {e}", file=sys.stderr)
        return ""


def run_backtranslation_eval(
    db_path: str,
    target_langs: list[str] | None = None,
    limit: int | None = None,
) -> dict:
    """Run back-translation evaluation."""
    conn = sqlite3.connect(db_path)
    langs = target_langs or list(NON_COMMUNITY_LANGS.keys())

    print("Stratifying headwords by frequency band...", file=sys.stderr)
    bands = get_frequency_bands(conn)
    samples = sample_headwords(bands, PER_BAND)
    print(f"Sampled {len(samples)} headwords", file=sys.stderr)

    # Collect pairs: headwords with both CC-CEDICT English and MiniMax target-lang def
    eval_pairs = []

    for band, hw_id in samples:
        defs = conn.execute(
            "SELECT lang, source, definition FROM definitions WHERE headword_id = ?",
            (hw_id,),
        ).fetchall()

        by_lang_source = defaultdict(dict)
        for lang, source, defn in defs:
            by_lang_source[lang][source] = defn

        english_ref = by_lang_source.get("en", {}).get("cedict")
        if not english_ref:
            continue

        for lang in langs:
            minimax_def = by_lang_source.get(lang, {}).get("minimax")
            if minimax_def:
                eval_pairs.append((band, hw_id, lang, minimax_def, english_ref))

    if limit:
        eval_pairs = eval_pairs[:limit]

    print(f"\nFound {len(eval_pairs)} evaluation pairs", file=sys.stderr)
    for lang in langs:
        n = sum(1 for _, _, l, _, _ in eval_pairs if l == lang)
        print(f"  {lang}: {n}", file=sys.stderr)

    # Back-translate and evaluate
    results_by_lang = defaultdict(lambda: {
        "sense_coverage": [], "false_sense_rate": [], "examples": []
    })
    results_by_band = defaultdict(lambda: {"sense_coverage": [], "false_sense_rate": []})

    t_start = time.time()
    for i, (band, hw_id, lang, minimax_def, english_ref) in enumerate(eval_pairs):
        backtranslated = backtranslate_minimax(minimax_def, lang)
        if not backtranslated:
            continue

        bt_glosses = split_glosses(backtranslated, "en")
        ref_glosses = split_glosses(english_ref, "en")

        overlap = gloss_overlap(ref_glosses, bt_glosses, "en")

        results_by_lang[lang]["sense_coverage"].append(overlap["sense_coverage"])
        results_by_lang[lang]["false_sense_rate"].append(overlap["false_sense_rate"])
        results_by_band[band]["sense_coverage"].append(overlap["sense_coverage"])
        results_by_band[band]["false_sense_rate"].append(overlap["false_sense_rate"])

        # Save interesting examples
        if overlap["sense_coverage"] < 0.5 or overlap["false_sense_rate"] > 0.5:
            hw = conn.execute(
                "SELECT simplified, pinyin FROM headwords WHERE id = ?", (hw_id,)
            ).fetchone()
            results_by_lang[lang]["examples"].append({
                "headword": hw[0] if hw else "?",
                "pinyin": hw[1] if hw else "?",
                "lang": lang,
                "original": minimax_def[:150],
                "backtranslated": backtranslated[:150],
                "reference": english_ref[:150],
                "sense_coverage": overlap["sense_coverage"],
                "false_sense_rate": overlap["false_sense_rate"],
            })

        if (i + 1) % 50 == 0:
            elapsed = time.time() - t_start
            print(f"  [{i + 1}/{len(eval_pairs)}] {elapsed:.1f}s", file=sys.stderr)

    conn.close()
    elapsed = time.time() - t_start
    print(f"\nDone in {elapsed:.1f}s", file=sys.stderr)

    # Aggregate
    summary = {"by_language": {}, "by_band": {}, "overall": {}}
    all_coverage = []
    all_false = []

    for lang in langs:
        data = results_by_lang[lang]
        if not data["sense_coverage"]:
            continue
        n = len(data["sense_coverage"])
        avg_cov = sum(data["sense_coverage"]) / n
        avg_false = sum(data["false_sense_rate"]) / n
        summary["by_language"][lang] = {
            "n": n,
            "sense_coverage": round(avg_cov, 3),
            "false_sense_rate": round(avg_false, 3),
            "examples": data["examples"][:3],
        }
        all_coverage.extend(data["sense_coverage"])
        all_false.extend(data["false_sense_rate"])

    for band in BANDS:
        data = results_by_band[band]
        if not data["sense_coverage"]:
            continue
        n = len(data["sense_coverage"])
        summary["by_band"][band] = {
            "n": n,
            "sense_coverage": round(sum(data["sense_coverage"]) / n, 3),
            "false_sense_rate": round(sum(data["false_sense_rate"]) / n, 3),
        }

    if all_coverage:
        summary["overall"] = {
            "n": len(all_coverage),
            "sense_coverage": round(sum(all_coverage) / len(all_coverage), 3),
            "false_sense_rate": round(sum(all_false) / len(all_false), 3),
        }

    return summary


def print_report(summary: dict):
    """Print the back-translation evaluation report."""
    print("## Back-Translation Evaluation: Non-Community Languages\n")

    if not summary.get("overall"):
        print("No results.")
        return

    overall = summary["overall"]
    print(f"**Overall** (n={overall['n']} headword-language pairs):")
    print(f"- Sense coverage (via back-translation): {overall['sense_coverage']:.1%}")
    print(f"- False sense rate (via back-translation): {overall['false_sense_rate']:.1%}")
    print()

    print("**By Language** (back-translated to English, compared against CC-CEDICT)\n")
    print("| Language | n | Sense Coverage | False Sense Rate |")
    print("|----------|---|---------------|-----------------|")
    for lang in ["es", "ko", "ru", "vi", "tl", "fa", "sv"]:
        if lang not in summary["by_language"]:
            continue
        d = summary["by_language"][lang]
        name = NON_COMMUNITY_LANGS[lang]
        print(f"| {name} ({lang}) | {d['n']} | {d['sense_coverage']:.1%} | {d['false_sense_rate']:.1%} |")
    print()

    # Show examples of failures
    print("**Notable back-translation failures:**\n")
    count = 0
    for lang in ["es", "ko", "ru", "vi", "tl", "fa", "sv"]:
        if lang not in summary["by_language"]:
            continue
        for ex in summary["by_language"][lang].get("examples", [])[:2]:
            print(f"- **{ex['headword']}** [{ex['pinyin']}] ({lang})")
            print(f"  - MiniMax {lang}: {ex['original']}")
            print(f"  - Back-translated: {ex['backtranslated']}")
            print(f"  - CC-CEDICT ref: {ex['reference']}")
            print(f"  - Coverage: {ex['sense_coverage']:.0%}")
            count += 1
        if count >= 8:
            break


def main():
    parser = argparse.ArgumentParser(description="Back-translation evaluation for Paper B")
    parser.add_argument("--db", default="data/artifacts/dictmaster.db", help="Path to dictmaster.db")
    parser.add_argument("--langs", default=None, help="Comma-separated lang codes (default: all 7)")
    parser.add_argument("--limit", type=int, default=None, help="Max pairs to evaluate")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    langs = args.langs.split(",") if args.langs else None
    summary = run_backtranslation_eval(args.db, target_langs=langs, limit=args.limit)

    if args.json:
        for lang_data in summary.get("by_language", {}).values():
            lang_data.pop("examples", None)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print_report(summary)


if __name__ == "__main__":
    main()
