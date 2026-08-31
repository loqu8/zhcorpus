#!/usr/bin/env python3
"""Score MT eval translations against references.

For FLORES: BLEU + chrF++ against gold references.
For iCE-realism: BLEU + chrF++ against Cerebras Qwen3-235B as silver reference,
                 plus relative agreement statistics.

Output: data/mt_eval/scores.json + Markdown table to stdout.

Usage:
    .venv/bin/python tools/score_mt.py
    .venv/bin/python tools/score_mt.py --test-set flores --langs en,de
"""

import argparse
import json
from pathlib import Path

import sacrebleu

from tools.eval_mt import (
    FLORES_LANG_CODES, FLORES_DIR, ICE_REALISM, LANG_NAMES, RESULTS_DIR,
)

# Tokenizer per target language for sacrebleu.
# For zh→en/de/fr/es: intl tokenizer; ja: ja-mecab; ko: ko-mecab fallback to char; etc.
# Falling back to "13a" (default) where mecab isn't installed.
BLEU_TOKENIZE = {
    "en": "intl",
    "de": "intl",
    "fr": "intl",
    "es": "intl",
    "ja": "ja-mecab",  # falls back if mecab not installed
    "ko": "ko-mecab",
}


def load_results(test_set: str, system: str, lang: str) -> dict[str, str]:
    """Return {id: translation} from result JSONL, skipping errors/empties."""
    path = RESULTS_DIR / f"{test_set}_{system}_{lang}.jsonl"
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("error"):
            continue
        if not r.get("translation", "").strip():
            continue
        out[r["id"]] = r["translation"].strip()
    return out


def load_flores_refs(target_lang: str, limit: int | None = None) -> dict[str, str]:
    """Return {flores-N: reference} for target lang."""
    code = FLORES_LANG_CODES[target_lang]
    refs = (FLORES_DIR / f"{code}.dev").read_text(encoding="utf-8").splitlines()
    rows = {f"flores-{i}": r for i, r in enumerate(refs)}
    if limit:
        rows = {k: v for k, v in rows.items() if int(k.split("-")[1]) < limit}
    return rows


def compute_bleu_chrf(hyps: list[str], refs: list[str], lang: str) -> dict:
    """Corpus BLEU + chrF++ for one system/lang slice."""
    if not hyps or not refs:
        return {"bleu": None, "chrf": None, "n": 0}
    tok = BLEU_TOKENIZE.get(lang, "13a")
    try:
        bleu = sacrebleu.corpus_bleu(hyps, [refs], tokenize=tok).score
    except Exception:
        # mecab missing - fall back to char tokenizer for CJK
        tok_fallback = "char" if lang in ("ja", "ko") else "13a"
        bleu = sacrebleu.corpus_bleu(hyps, [refs], tokenize=tok_fallback).score
    chrf = sacrebleu.corpus_chrf(hyps, [refs], word_order=2).score  # chrF++
    return {"bleu": round(bleu, 2), "chrf": round(chrf, 2), "n": len(hyps),
            "bleu_tokenizer": tok}


def score_one(test_set: str, system: str, lang: str, refs: dict[str, str]) -> dict:
    """Score one (test_set, system, lang) combination against given refs."""
    hyps_map = load_results(test_set, system, lang)
    if not hyps_map:
        return {"n": 0, "skipped": "no results"}
    # Align by id
    aligned_ids = sorted(set(hyps_map) & set(refs))
    hyps = [hyps_map[i] for i in aligned_ids]
    rs = [refs[i] for i in aligned_ids]
    res = compute_bleu_chrf(hyps, rs, lang)
    res["coverage"] = round(len(aligned_ids) / len(refs), 3) if refs else 0
    res["errors"] = len(refs) - len(aligned_ids)
    return res


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--test-sets", default="flores,ice")
    p.add_argument("--systems", default="cerebras,hy-mt-1.8b,hy-mt-7b,opus-mt")
    p.add_argument("--langs", default="en,de,ja,ko")
    p.add_argument("--limit", type=int, default=200,
                   help="Limit FLORES refs to first N (match what was translated)")
    p.add_argument("--out", default="data/mt_eval/scores.json")
    args = p.parse_args()

    test_sets = args.test_sets.split(",")
    systems = args.systems.split(",")
    langs = args.langs.split(",")

    all_scores: dict = {}

    for test_set in test_sets:
        all_scores[test_set] = {}
        for lang in langs:
            # Determine reference for this test set
            if test_set == "flores":
                refs = load_flores_refs(lang, args.limit)
                ref_source = "FLORES-200 gold"
            else:  # ice - use Cerebras as silver
                cerebras_results = load_results("ice", "cerebras", lang)
                refs = cerebras_results
                ref_source = "Cerebras Qwen3-235B (silver)"

            all_scores[test_set][lang] = {
                "reference_source": ref_source,
                "n_refs": len(refs),
                "systems": {},
            }

            for system in systems:
                # For iCE, skip scoring Cerebras against itself
                if test_set == "ice" and system == "cerebras":
                    all_scores[test_set][lang]["systems"][system] = {
                        "note": "self-reference (silver baseline)",
                        "n": len(refs),
                    }
                    continue
                res = score_one(test_set, system, lang, refs)
                all_scores[test_set][lang]["systems"][system] = res

    # Save
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(all_scores, indent=2, ensure_ascii=False))
    print(f"\nWrote scores to {out_path}\n")

    # Markdown summary
    for test_set, by_lang in all_scores.items():
        print(f"## {test_set.upper()} results")
        for lang, info in by_lang.items():
            print(f"\n### zh → {LANG_NAMES.get(lang, lang)} ({info['reference_source']}, n={info['n_refs']})")
            print("\n| System | n | BLEU | chrF++ | Coverage |")
            print("|---|---:|---:|---:|---:|")
            for system, s in info["systems"].items():
                if "note" in s:
                    print(f"| {system} | — | — | — | (self) |")
                    continue
                if s.get("n", 0) == 0:
                    print(f"| {system} | 0 | — | — | — |")
                    continue
                cov = s.get("coverage", 0)
                print(f"| {system} | {s['n']} | {s['bleu']} | {s['chrf']} | {cov:.1%} |")
        print()


if __name__ == "__main__":
    main()
