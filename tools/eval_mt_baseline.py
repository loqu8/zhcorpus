#!/usr/bin/env python3
"""
Paper B: MT baseline comparison.

Translates CC-CEDICT English definitions into German/French/Indonesian using
a generic MT prompt, then compares against community dictionaries (HanDeDict,
CFDICT, CC-CIDICT) using the same eval metrics as eval_community_comparison.py.

This establishes a baseline: "what if you just translated English glosses
with a generic LLM instead of using our structured dictionary pipeline?"

Usage:
    # Uses MiniMax API with a plain translation prompt (not dictionary prompt)
    .venv/bin/python tools/eval_mt_baseline.py

    # Use a different backend (requires model-radar or direct API)
    .venv/bin/python tools/eval_mt_baseline.py --backend groq
"""

import argparse
import json
import random
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path

# Reuse eval functions from the main comparison script
from tools.eval_community_comparison import (
    COMMUNITY_SOURCES,
    SAMPLE_SIZE,
    BANDS,
    PER_BAND,
    split_glosses,
    gloss_overlap,
    get_frequency_bands,
    sample_headwords,
)

# Target languages for MT baseline (those with community dictionaries, excluding English)
MT_TARGETS = {
    "de": {"name": "German", "community_source": "handedict"},
    "fr": {"name": "French", "community_source": "cfdict"},
    "id": {"name": "Indonesian", "community_source": "cidict"},
}

MT_SYSTEM_PROMPT = """\
You are a translator. Translate the following English text into {lang_name}.
Output ONLY the translation, nothing else. Keep the same format (slash-separated
alternatives if the input has them). Be concise — dictionary style."""

MT_USER_TEMPLATE = "Translate to {lang_name}: {text}"


def translate_gloss_minimax(english_def: str, target_lang: str) -> str:
    """Translate an English definition into target language via MiniMax API."""
    from tools.dictmaster.translate.minimax_api import _chat

    lang_name = MT_TARGETS[target_lang]["name"]
    system = MT_SYSTEM_PROMPT.format(lang_name=lang_name)
    user = MT_USER_TEMPLATE.format(lang_name=lang_name, text=english_def)

    try:
        response = _chat(system, user, max_tokens=256)
        return response.strip()
    except Exception as e:
        print(f"    MT error: {e}", file=sys.stderr)
        return ""


def run_mt_baseline(db_path: str, backend: str = "minimax") -> dict:
    """Run the MT baseline evaluation."""
    conn = sqlite3.connect(db_path)

    # Use same sampling as main eval (same seed = same headwords)
    print("Stratifying headwords by frequency band...", file=sys.stderr)
    bands = get_frequency_bands(conn)
    for b, ids in bands.items():
        print(f"  {b}: {len(ids):,} headwords", file=sys.stderr)

    samples = sample_headwords(bands, PER_BAND)
    print(f"\nSampled {len(samples)} headwords", file=sys.stderr)

    # Collect headwords that have both CC-CEDICT (English) and a community target
    eval_pairs = []  # (band, hw_id, target_lang, english_def, community_def)

    for band, hw_id in samples:
        defs = conn.execute(
            "SELECT lang, source, definition FROM definitions WHERE headword_id = ?",
            (hw_id,),
        ).fetchall()

        by_lang_source = defaultdict(dict)
        for lang, source, defn in defs:
            by_lang_source[lang][source] = defn

        # Need CC-CEDICT English definition as source
        english_def = by_lang_source.get("en", {}).get("cedict")
        if not english_def:
            continue

        # Check each target language for community reference
        for target_lang, info in MT_TARGETS.items():
            community_def = by_lang_source.get(target_lang, {}).get(info["community_source"])
            if community_def:
                eval_pairs.append((band, hw_id, target_lang, english_def, community_def))

    print(f"\nFound {len(eval_pairs)} evaluation pairs (headword × target lang)", file=sys.stderr)
    print(f"  de: {sum(1 for _, _, l, _, _ in eval_pairs if l == 'de')}", file=sys.stderr)
    print(f"  fr: {sum(1 for _, _, l, _, _ in eval_pairs if l == 'fr')}", file=sys.stderr)
    print(f"  id: {sum(1 for _, _, l, _, _ in eval_pairs if l == 'id')}", file=sys.stderr)

    # Translate and evaluate
    results_by_lang = defaultdict(lambda: {"sense_coverage": [], "false_sense_rate": []})
    results_by_band = defaultdict(lambda: {"sense_coverage": [], "false_sense_rate": []})

    t_start = time.time()
    for i, (band, hw_id, target_lang, english_def, community_def) in enumerate(eval_pairs):
        if backend == "minimax":
            mt_def = translate_gloss_minimax(english_def, target_lang)
        else:
            raise ValueError(f"Unknown backend: {backend}")

        if not mt_def:
            continue

        # Compare MT output against community dictionary
        mt_glosses = split_glosses(mt_def, target_lang)
        ref_glosses = split_glosses(community_def, target_lang)

        overlap = gloss_overlap(ref_glosses, mt_glosses, target_lang)

        results_by_lang[target_lang]["sense_coverage"].append(overlap["sense_coverage"])
        results_by_lang[target_lang]["false_sense_rate"].append(overlap["false_sense_rate"])
        results_by_band[band]["sense_coverage"].append(overlap["sense_coverage"])
        results_by_band[band]["false_sense_rate"].append(overlap["false_sense_rate"])

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

    for lang in ["de", "fr", "id"]:
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
    """Print the MT baseline evaluation report."""
    print("## MT Baseline: English→Target Translation Comparison\n")

    if not summary.get("overall"):
        print("No results.")
        return

    overall = summary["overall"]
    print(f"**Overall** (n={overall['n']} headword-language pairs):")
    print(f"- Sense coverage: {overall['sense_coverage']:.1%}")
    print(f"- False sense rate: {overall['false_sense_rate']:.1%}")
    print()

    print("**By Language**\n")
    print("| Language | Reference | n | Sense Coverage | False Sense Rate |")
    print("|----------|-----------|---|---------------|-----------------|")
    source_names = {"de": "HanDeDict", "fr": "CFDICT", "id": "CC-CIDICT"}
    for lang in ["de", "fr", "id"]:
        if lang not in summary["by_language"]:
            continue
        d = summary["by_language"][lang]
        print(f"| {lang} | {source_names[lang]} | {d['n']} | {d['sense_coverage']:.1%} | {d['false_sense_rate']:.1%} |")
    print()

    print("**By Frequency Band**\n")
    print("| Band | n | Sense Coverage | False Sense Rate |")
    print("|------|---|---------------|-----------------|")
    for band in BANDS:
        if band not in summary["by_band"]:
            continue
        d = summary["by_band"][band]
        print(f"| {band} | {d['n']} | {d['sense_coverage']:.1%} | {d['false_sense_rate']:.1%} |")

    print("\n---")
    print("**Comparison**: Our structured dictionary pipeline achieves 87.3% sense coverage /")
    print("12.5% false sense rate on the same headwords (Table 3 in paper).")


def main():
    parser = argparse.ArgumentParser(description="MT baseline evaluation for Paper B")
    parser.add_argument("--db", default="data/artifacts/dictmaster.db", help="Path to dictmaster.db")
    parser.add_argument("--backend", default="minimax", choices=["minimax"], help="MT backend")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    summary = run_mt_baseline(args.db, backend=args.backend)

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print_report(summary)


if __name__ == "__main__":
    main()
