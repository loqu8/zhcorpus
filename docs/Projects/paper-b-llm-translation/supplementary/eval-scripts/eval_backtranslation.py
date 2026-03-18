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

import requests

from tools.eval_community_comparison import (
    BANDS,
    PER_BAND,
    split_glosses,
    gloss_overlap,
    get_frequency_bands,
    sample_headwords,
)

# Non-community languages to evaluate (all 13 without community dicts)
NON_COMMUNITY_LANGS = {
    "es": "Spanish",
    "ko": "Korean",
    "ru": "Russian",
    "vi": "Vietnamese",
    "tl": "Tagalog",
    "fa": "Persian",
    "sv": "Swedish",
    "nl": "Dutch",
    "pt": "Portuguese",
    "ar": "Arabic",
    "th": "Thai",
    "hi": "Hindi",
    "it": "Italian",
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
    for lang in list(NON_COMMUNITY_LANGS.keys()):
        if lang not in summary["by_language"]:
            continue
        d = summary["by_language"][lang]
        name = NON_COMMUNITY_LANGS[lang]
        print(f"| {name} ({lang}) | {d['n']} | {d['sense_coverage']:.1%} | {d['false_sense_rate']:.1%} |")
    print()

    # Show examples of failures
    print("**Notable back-translation failures:**\n")
    count = 0
    for lang in list(NON_COMMUNITY_LANGS.keys()):
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


# ---------------------------------------------------------------------------
# LLM-as-Judge evaluation
# ---------------------------------------------------------------------------

JUDGE_SYSTEM = """\
You are a dictionary quality evaluator. Rate the following dictionary definition
on three dimensions, each on a 1-5 scale:

1. **Accuracy**: Does the definition correctly convey the meaning of the Chinese word?
2. **Naturalness**: Does the definition read naturally in the target language?
3. **Completeness**: Does it cover the main senses of the word?

Output ONLY three numbers separated by commas. Example: 4,5,3
No explanations."""

JUDGE_USER = """\
Chinese word: {headword} ({pinyin})
English reference: {english_ref}
{lang_name} definition to evaluate: {definition}

Rate accuracy, naturalness, completeness (1-5 each):"""

# Judge models (free, via direct API)
JUDGE_MODELS = [
    ("moonshotai/kimi-k2-instruct", "groq", "Kimi K2"),
    ("openai/gpt-oss-120b", "groq", "GPT-OSS-120B"),
    ("DeepSeek-V3.1", "sambanova", "DeepSeek V3.1"),
    ("claude-sonnet-4-20250514", "anthropic", "Claude Sonnet 4"),
]


_model_radar_keys: dict | None = None


def _get_provider_key(provider: str) -> str:
    """Load API key from model-radar config (~/.model-radar/config.json)."""
    global _model_radar_keys
    if _model_radar_keys is None:
        import os
        config_path = Path.home() / ".model-radar" / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                _model_radar_keys = json.load(f).get("api_keys", {})
        else:
            _model_radar_keys = {}
    key = _model_radar_keys.get(provider, "")
    if not key:
        import os
        env_map = {"groq": "GROQ_API_KEY", "sambanova": "SAMBANOVA_API_KEY"}
        key = os.environ.get(env_map.get(provider, ""), "")
    if not key:
        raise ValueError(f"No API key for {provider}")
    return key


def _load_credentials() -> dict:
    """Load credentials from /mnt/a/loqu8/credentials.json."""
    cred_path = Path("/mnt/a/loqu8/credentials.json")
    if cred_path.exists():
        with open(cred_path) as f:
            return json.load(f)
    return {}


def _call_judge(system: str, user: str, model_id: str, provider: str) -> str:
    """Call a judge model via provider API."""
    if provider == "anthropic":
        creds = _load_credentials()
        api_key = creds.get("anthropic_api", {}).get("api_key", "")
        if not api_key:
            raise ValueError("No Anthropic API key in credentials.json")
        resp = requests.post("https://api.anthropic.com/v1/messages", headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }, json={
            "model": model_id,
            "max_tokens": 20,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }, timeout=30)
        resp.raise_for_status()
        return resp.json()["content"][0]["text"].strip()

    api_key = _get_provider_key(provider)

    if provider == "groq":
        url = "https://api.groq.com/openai/v1/chat/completions"
    elif provider == "sambanova":
        url = "https://api.sambanova.ai/v1/chat/completions"
    else:
        raise ValueError(f"Unknown provider: {provider}")

    resp = requests.post(url, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }, json={
        "model": model_id,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": 20,
        "temperature": 0.0,
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def parse_judge_scores(response: str) -> tuple[float, float, float] | None:
    """Parse '4,5,3' format from judge response."""
    import re
    numbers = re.findall(r"[1-5]", response)
    if len(numbers) >= 3:
        return float(numbers[0]), float(numbers[1]), float(numbers[2])
    return None


def run_judge_eval(
    db_path: str,
    target_langs: list[str] | None = None,
    limit: int = 100,
) -> dict:
    """Run LLM-as-judge evaluation on non-community language definitions."""
    import os
    import requests as req

    conn = sqlite3.connect(db_path)
    langs = target_langs or list(NON_COMMUNITY_LANGS.keys())

    print("Sampling headwords for judge evaluation...", file=sys.stderr)
    bands = get_frequency_bands(conn)
    samples = sample_headwords(bands, PER_BAND)

    # Collect pairs with MiniMax definitions
    eval_entries = []
    for band, hw_id in samples:
        hw = conn.execute(
            "SELECT simplified, pinyin FROM headwords WHERE id = ?", (hw_id,)
        ).fetchone()
        if not hw:
            continue

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
                eval_entries.append({
                    "hw_id": hw_id, "headword": hw[0], "pinyin": hw[1],
                    "lang": lang, "definition": minimax_def, "english_ref": english_ref,
                })

    if limit:
        random.seed(42)
        random.shuffle(eval_entries)
        eval_entries = eval_entries[:limit]

    print(f"Judging {len(eval_entries)} entries with {len(JUDGE_MODELS)} models...", file=sys.stderr)

    # Run judges
    scores_by_lang = defaultdict(lambda: {"accuracy": [], "naturalness": [], "completeness": []})
    judge_agreement = []  # per-entry: list of (judge_scores) tuples

    t_start = time.time()
    for i, entry in enumerate(eval_entries):
        lang_name = NON_COMMUNITY_LANGS.get(entry["lang"], entry["lang"])
        user_prompt = JUDGE_USER.format(
            headword=entry["headword"], pinyin=entry["pinyin"],
            english_ref=entry["english_ref"], lang_name=lang_name,
            definition=entry["definition"],
        )

        entry_scores = []
        for model_id, provider, label in JUDGE_MODELS:
            try:
                response = _call_judge(JUDGE_SYSTEM, user_prompt, model_id, provider)
                scores = parse_judge_scores(response)
                if scores:
                    entry_scores.append(scores)
            except Exception as e:
                if i == 0:
                    print(f"  Judge {label} error: {e}", file=sys.stderr)

        if entry_scores:
            # Average across judges for this entry
            avg_acc = sum(s[0] for s in entry_scores) / len(entry_scores)
            avg_nat = sum(s[1] for s in entry_scores) / len(entry_scores)
            avg_comp = sum(s[2] for s in entry_scores) / len(entry_scores)

            scores_by_lang[entry["lang"]]["accuracy"].append(avg_acc)
            scores_by_lang[entry["lang"]]["naturalness"].append(avg_nat)
            scores_by_lang[entry["lang"]]["completeness"].append(avg_comp)

            if len(entry_scores) >= 2:
                # Inter-judge agreement: max pairwise difference
                diffs = []
                for j in range(len(entry_scores)):
                    for k in range(j + 1, len(entry_scores)):
                        for dim in range(3):
                            diffs.append(abs(entry_scores[j][dim] - entry_scores[k][dim]))
                judge_agreement.append(sum(diffs) / len(diffs) if diffs else 0)

        if (i + 1) % 20 == 0:
            elapsed = time.time() - t_start
            print(f"  [{i + 1}/{len(eval_entries)}] {elapsed:.1f}s", file=sys.stderr)

    conn.close()
    elapsed = time.time() - t_start
    print(f"Judge eval done in {elapsed:.1f}s", file=sys.stderr)

    # Aggregate
    summary = {"by_language": {}, "overall": {}, "inter_judge_agreement": {}}

    all_acc, all_nat, all_comp = [], [], []
    for lang in langs:
        data = scores_by_lang[lang]
        if not data["accuracy"]:
            continue
        n = len(data["accuracy"])
        summary["by_language"][lang] = {
            "n": n,
            "accuracy": round(sum(data["accuracy"]) / n, 2),
            "naturalness": round(sum(data["naturalness"]) / n, 2),
            "completeness": round(sum(data["completeness"]) / n, 2),
        }
        all_acc.extend(data["accuracy"])
        all_nat.extend(data["naturalness"])
        all_comp.extend(data["completeness"])

    if all_acc:
        summary["overall"] = {
            "n": len(all_acc),
            "accuracy": round(sum(all_acc) / len(all_acc), 2),
            "naturalness": round(sum(all_nat) / len(all_nat), 2),
            "completeness": round(sum(all_comp) / len(all_comp), 2),
        }

    if judge_agreement:
        summary["inter_judge_agreement"] = {
            "mean_pairwise_diff": round(sum(judge_agreement) / len(judge_agreement), 2),
            "n_entries_with_multi_judge": len(judge_agreement),
        }

    summary["judges"] = [label for _, _, label in JUDGE_MODELS]

    return summary


def main():
    parser = argparse.ArgumentParser(description="Back-translation + judge evaluation for Paper B")
    parser.add_argument("--db", default="data/artifacts/dictmaster.db", help="Path to dictmaster.db")
    parser.add_argument("--langs", default=None, help="Comma-separated lang codes (default: all 13)")
    parser.add_argument("--limit", type=int, default=None, help="Max pairs to evaluate")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--judge", action="store_true", help="Run LLM-as-judge eval")
    parser.add_argument("--judge-limit", type=int, default=100, help="Max entries for judge eval")
    parser.add_argument("--both", action="store_true", help="Run both back-translation and judge")
    args = parser.parse_args()

    langs = args.langs.split(",") if args.langs else None
    results = {}

    if args.both or not args.judge:
        summary = run_backtranslation_eval(args.db, target_langs=langs, limit=args.limit)
        if args.json or args.both:
            for lang_data in summary.get("by_language", {}).values():
                lang_data.pop("examples", None)
            results["backtranslation"] = summary
        else:
            print_report(summary)
            return

    if args.both or args.judge:
        judge_summary = run_judge_eval(args.db, target_langs=langs, limit=args.judge_limit)
        results["judge"] = judge_summary

    if results:
        print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
