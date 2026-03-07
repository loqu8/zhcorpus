#!/usr/bin/env python3
"""
Paper B Section 6.2: Compare LLM-generated definitions against community dictionaries.

Samples 200 headwords stratified by frequency, compares MiniMax glosses against
community dictionary references (CC-CEDICT, HanDeDict, CFDICT, CC-CIDICT, JMdict)
for sense coverage and false sense rate.

Usage:
    .venv/bin/python tools/eval_community_comparison.py [--db data/artifacts/dictmaster.db]
"""

import argparse
import json
import random
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

# Community source → language mapping
# Note: JMdict excluded — it stores kana readings (しふん), not definitions/glosses,
# making gloss-level comparison meaningless.
COMMUNITY_SOURCES = {
    "cedict": "en",
    "handedict": "de",
    "cfdict": "fr",
    "cidict": "id",
}

# How many headwords to sample per frequency band
SAMPLE_SIZE = 200
BANDS = ["high", "mid", "low", "rare"]
PER_BAND = SAMPLE_SIZE // len(BANDS)  # 50 per band


def split_glosses(definition: str, lang: str) -> list[str]:
    """Split a definition string into individual glosses/senses.

    Handles multiple separator styles:
    - CEDICT-style: /gloss1/gloss2/ or gloss1/gloss2
    - Semicolon-separated: gloss1; gloss2
    - Mixed: gloss1/gloss2; gloss3
    """
    # Strip leading/trailing slashes
    definition = definition.strip().strip("/")

    # Split on / and ;
    parts = re.split(r"[;/]", definition)

    glosses = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # Skip classifier markers (CL:...) and cross-references
        if p.startswith("CL:") or p.startswith("CL："):
            continue
        # Skip pure parenthetical qualifiers like (Eig, Geo)
        if re.match(r"^\([A-Z][a-z]+(?:,\s*[A-Z][a-z]+)*\)$", p):
            continue
        glosses.append(p)

    return glosses


def normalize_gloss(gloss: str, lang: str) -> str:
    """Normalize a gloss for comparison."""
    g = gloss.lower().strip()
    # Remove leading articles for European languages
    if lang in ("en", "de", "fr", "es", "id"):
        g = re.sub(r"^(to |a |an |the |le |la |les |l'|un |une |der |die |das |ein |eine |)", "", g)
    # Remove parenthetical notes
    g = re.sub(r"\s*\([^)]*\)\s*", " ", g)
    # Remove classifier info
    g = re.sub(r"\s*CL:.*$", "", g)
    # Collapse whitespace
    g = re.sub(r"\s+", " ", g).strip()
    return g


def gloss_overlap(ref_glosses: list[str], llm_glosses: list[str], lang: str) -> dict:
    """Compare reference glosses against LLM glosses.

    Returns:
        sense_coverage: proportion of reference senses captured by LLM
        false_sense_rate: proportion of LLM senses not in reference
        matched_ref: number of reference senses matched
        total_ref: total reference senses
        matched_llm: number of LLM senses that match a reference
        total_llm: total LLM senses
    """
    ref_normalized = [normalize_gloss(g, lang) for g in ref_glosses]
    llm_normalized = [normalize_gloss(g, lang) for g in llm_glosses]

    # Filter out empty
    ref_normalized = [g for g in ref_normalized if g]
    llm_normalized = [g for g in llm_normalized if g]

    if not ref_normalized:
        return {"sense_coverage": 1.0, "false_sense_rate": 0.0,
                "matched_ref": 0, "total_ref": 0,
                "matched_llm": 0, "total_llm": len(llm_normalized)}

    # Check each ref sense: is it captured (even partially) by any LLM sense?
    matched_ref = 0
    for rg in ref_normalized:
        r_words = set(rg.split())
        for lg in llm_normalized:
            l_words = set(lg.split())
            # Match if: exact match, substring, or >50% word overlap
            if rg == lg:
                matched_ref += 1
                break
            elif rg in lg or lg in rg:
                matched_ref += 1
                break
            elif r_words and l_words:
                overlap = len(r_words & l_words) / min(len(r_words), len(l_words))
                if overlap >= 0.5:
                    matched_ref += 1
                    break

    # Check each LLM sense: is it supported by any ref sense?
    matched_llm = 0
    for lg in llm_normalized:
        l_words = set(lg.split())
        for rg in ref_normalized:
            r_words = set(rg.split())
            if rg == lg or rg in lg or lg in rg:
                matched_llm += 1
                break
            elif r_words and l_words:
                overlap = len(r_words & l_words) / min(len(r_words), len(l_words))
                if overlap >= 0.5:
                    matched_llm += 1
                    break

    sense_coverage = matched_ref / len(ref_normalized)
    false_sense_rate = 1.0 - (matched_llm / len(llm_normalized)) if llm_normalized else 0.0

    return {
        "sense_coverage": sense_coverage,
        "false_sense_rate": false_sense_rate,
        "matched_ref": matched_ref,
        "total_ref": len(ref_normalized),
        "matched_llm": matched_llm,
        "total_llm": len(llm_normalized),
    }


def get_frequency_bands(conn: sqlite3.Connection) -> dict[str, list[int]]:
    """Stratify headwords by how many community sources define them.

    Uses number of community sources as a proxy for frequency:
    - high: defined in 4+ community sources (well-known words)
    - mid: defined in 3 community sources
    - low: defined in 2 community sources
    - rare: defined in 1 community source only
    """
    # Count community sources per headword
    rows = conn.execute("""
        SELECT headword_id, COUNT(DISTINCT source) as src_count
        FROM definitions
        WHERE source IN ('cedict', 'handedict', 'cfdict', 'cidict', 'jmdict')
        GROUP BY headword_id
    """).fetchall()

    bands = {"high": [], "mid": [], "low": [], "rare": []}
    for hw_id, src_count in rows:
        if src_count >= 4:
            bands["high"].append(hw_id)
        elif src_count == 3:
            bands["mid"].append(hw_id)
        elif src_count == 2:
            bands["low"].append(hw_id)
        else:
            bands["rare"].append(hw_id)

    return bands


def sample_headwords(bands: dict[str, list[int]], per_band: int, seed: int = 42) -> list[tuple[str, int]]:
    """Sample headwords from each frequency band."""
    random.seed(seed)
    samples = []
    for band_name in BANDS:
        pool = bands[band_name]
        n = min(per_band, len(pool))
        chosen = random.sample(pool, n)
        for hw_id in chosen:
            samples.append((band_name, hw_id))
    return samples


def run_evaluation(db_path: str) -> dict:
    """Run the full evaluation and return results."""
    conn = sqlite3.connect(db_path)

    # Get frequency bands
    print("Stratifying headwords by frequency band...", file=sys.stderr)
    bands = get_frequency_bands(conn)
    for b, ids in bands.items():
        print(f"  {b}: {len(ids):,} headwords", file=sys.stderr)

    # Sample
    samples = sample_headwords(bands, PER_BAND)
    print(f"\nSampled {len(samples)} headwords", file=sys.stderr)

    # For each sampled headword, compare community vs MiniMax in each available language
    results_by_lang = defaultdict(lambda: {"sense_coverage": [], "false_sense_rate": [], "examples": []})
    results_by_band = defaultdict(lambda: {"sense_coverage": [], "false_sense_rate": []})

    for band, hw_id in samples:
        # Get headword info
        hw = conn.execute(
            "SELECT simplified, traditional, pinyin FROM headwords WHERE id = ?", (hw_id,)
        ).fetchone()
        if not hw:
            continue

        # Get all definitions for this headword
        defs = conn.execute(
            "SELECT lang, source, definition FROM definitions WHERE headword_id = ?", (hw_id,)
        ).fetchall()

        # Organize by (lang, source)
        by_lang_source = defaultdict(dict)
        for lang, source, defn in defs:
            by_lang_source[lang][source] = defn

        # Compare each community source against minimax
        for source, lang in COMMUNITY_SOURCES.items():
            if source not in by_lang_source[lang]:
                continue
            if "minimax" not in by_lang_source[lang]:
                continue

            ref_def = by_lang_source[lang][source]
            llm_def = by_lang_source[lang]["minimax"]

            ref_glosses = split_glosses(ref_def, lang)
            llm_glosses = split_glosses(llm_def, lang)

            overlap = gloss_overlap(ref_glosses, llm_glosses, lang)

            results_by_lang[lang]["sense_coverage"].append(overlap["sense_coverage"])
            results_by_lang[lang]["false_sense_rate"].append(overlap["false_sense_rate"])
            results_by_band[band]["sense_coverage"].append(overlap["sense_coverage"])
            results_by_band[band]["false_sense_rate"].append(overlap["false_sense_rate"])

            # Save interesting examples (low coverage or high false sense)
            if overlap["sense_coverage"] < 0.5 or overlap["false_sense_rate"] > 0.5:
                results_by_lang[lang]["examples"].append({
                    "headword": hw[0],
                    "pinyin": hw[2],
                    "band": band,
                    "ref": ref_def[:200],
                    "llm": llm_def[:200],
                    "sense_coverage": overlap["sense_coverage"],
                    "false_sense_rate": overlap["false_sense_rate"],
                    "ref_senses": overlap["total_ref"],
                    "llm_senses": overlap["total_llm"],
                })

    conn.close()

    # Aggregate results
    summary = {"by_language": {}, "by_band": {}, "overall": {}}

    all_coverage = []
    all_false = []

    for lang in ["en", "de", "fr", "id", "ja"]:
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
            "examples": data["examples"][:5],
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
    """Print the evaluation report in markdown format."""
    print("## Section 6.2: Comparison with Community Dictionaries\n")

    overall = summary["overall"]
    print(f"**Overall** (n={overall['n']} headword-language pairs):")
    print(f"- Sense coverage: {overall['sense_coverage']:.1%}")
    print(f"- False sense rate: {overall['false_sense_rate']:.1%}")
    print()

    # Table by language
    print("**Table 5: LLM vs Community Dictionary Comparison by Language**\n")
    print("| Language | Source | n | Sense Coverage | False Sense Rate |")
    print("|----------|--------|---|---------------|-----------------|")

    source_names = {"en": "CC-CEDICT", "de": "HanDeDict", "fr": "CFDICT", "id": "CC-CIDICT"}
    for lang in ["en", "de", "fr", "id"]:
        if lang not in summary["by_language"]:
            continue
        d = summary["by_language"][lang]
        print(f"| {lang} | {source_names[lang]} | {d['n']} | {d['sense_coverage']:.1%} | {d['false_sense_rate']:.1%} |")
    print()

    # Table by frequency band
    print("**Table 6: LLM vs Community Dictionary Comparison by Frequency Band**\n")
    print("| Band | n | Sense Coverage | False Sense Rate |")
    print("|------|---|---------------|-----------------|")
    for band in BANDS:
        if band not in summary["by_band"]:
            continue
        d = summary["by_band"][band]
        print(f"| {band} | {d['n']} | {d['sense_coverage']:.1%} | {d['false_sense_rate']:.1%} |")
    print()

    # Error examples
    print("**Notable disagreements** (sense coverage < 50% or false sense rate > 50%):\n")
    example_count = 0
    for lang in ["en", "de", "fr", "id", "ja"]:
        if lang not in summary["by_language"]:
            continue
        for ex in summary["by_language"][lang]["examples"][:3]:
            print(f"- **{ex['headword']}** [{ex['pinyin']}] ({lang}, {ex['band']})")
            print(f"  - Reference ({ex['ref_senses']} senses): {ex['ref']}")
            print(f"  - MiniMax ({ex['llm_senses']} senses): {ex['llm']}")
            print(f"  - Coverage: {ex['sense_coverage']:.0%}, False: {ex['false_sense_rate']:.0%}")
            example_count += 1
        if example_count >= 10:
            break

    if example_count == 0:
        print("(No major disagreements found)")


def main():
    parser = argparse.ArgumentParser(description="Evaluate LLM vs community dictionary quality")
    parser.add_argument("--db", default="data/artifacts/dictmaster.db", help="Path to dictmaster.db")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of markdown")
    args = parser.parse_args()

    summary = run_evaluation(args.db)

    if args.json:
        # Strip examples for cleaner JSON output
        for lang_data in summary["by_language"].values():
            del lang_data["examples"]
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print_report(summary)


if __name__ == "__main__":
    main()
