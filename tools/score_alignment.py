#!/usr/bin/env python3
"""Score alignment eval outputs.

Metrics:
  - parse_rate:     fraction of outputs that parse to {t, a} with a as list
  - alignment_pairs_mean: mean number of (s,t) pairs in successful parses
  - coverage:       fraction of source chars covered by some 's' span
  - chrF++:         translation chrF++ vs Cerebras silver (excluding cerebras itself)
  - latency_p50:    median latency in seconds

Usage:
    .venv/bin/python tools/score_alignment.py --test-set pilot
"""

import argparse
import json
import re
import statistics
from pathlib import Path

import sacrebleu

RESULTS_DIR = Path("data/alignment_eval/results")


def try_parse(raw: str) -> dict | None:
    """Try to extract {t: str, a: list} from a model's raw output.

    Tolerates:
      - markdown code fences (```json ... ``` or ``` ... ```)
      - leading/trailing prose
      - duplicate JSON blobs (takes the first that parses)
    Returns dict with keys t, a, or None.
    """
    if not raw:
        return None
    # Strip ```json ... ``` or ``` ... ``` fences
    s = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    s = re.sub(r"\s*```$", "", s)
    # Try direct parse
    try:
        obj = json.loads(s)
        if isinstance(obj, dict) and "t" in obj and "a" in obj:
            return obj
    except Exception:
        pass
    # Fall back: find first {...} block that parses
    for m in re.finditer(r"\{[\s\S]*?\}", s):
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict) and "t" in obj and "a" in obj:
                return obj
        except Exception:
            continue
    # Greedy fallback: first { to last }
    if "{" in s and "}" in s:
        try:
            chunk = s[s.index("{"):s.rindex("}") + 1]
            obj = json.loads(chunk)
            if isinstance(obj, dict) and "t" in obj and "a" in obj:
                return obj
        except Exception:
            pass
    return None


def extract_s_term(pair) -> str:
    """An alignment pair can be ['s:X', 't:Y'] or {'s': 'X', 't': 'Y'} or
    ['X','Y']. Return the source side."""
    if isinstance(pair, list) and len(pair) >= 2:
        a = pair[0]
        if isinstance(a, str):
            return a[2:] if a.startswith("s:") else a
    if isinstance(pair, dict):
        s = pair.get("s", "")
        return s[2:] if isinstance(s, str) and s.startswith("s:") else s
    return ""


def coverage(source: str, parsed: dict | None) -> float:
    """Fraction of source chars covered by at least one alignment's s span.
    Counts unique covered char positions (set union of substring matches).
    """
    if not parsed or not source:
        return 0.0
    a = parsed.get("a") or []
    if not isinstance(a, list):
        return 0.0
    covered = [False] * len(source)
    for pair in a:
        s_term = extract_s_term(pair)
        if not s_term or not isinstance(s_term, str):
            continue
        # Mark all occurrences of s_term in source as covered
        start = 0
        while True:
            i = source.find(s_term, start)
            if i < 0:
                break
            for j in range(i, i + len(s_term)):
                if 0 <= j < len(source):
                    covered[j] = True
            start = i + max(1, len(s_term))
    return sum(covered) / len(covered)


def score_system(rows: list[dict], silver_by_id: dict[str, str]) -> dict:
    n = len(rows)
    parsed_rows = []
    parse_ok = 0
    pair_counts = []
    coverages = []
    latencies = []
    translations = []
    refs = []
    for row in rows:
        latencies.append(row.get("elapsed_s", 0.0))
        raw = row.get("raw", "") or ""
        p = try_parse(raw)
        if p is not None:
            parse_ok += 1
            a = p.get("a") or []
            if isinstance(a, list):
                pair_counts.append(len(a))
            cov = coverage(row["text"], p)
            coverages.append(cov)
            t = p.get("t", "")
            if isinstance(t, str) and t.strip():
                translations.append(t.strip())
                refs.append(silver_by_id.get(row["id"], ""))
        parsed_rows.append((row, p))

    # chrF++ if we have refs
    chrf = None
    if translations and refs and all(refs):
        chrf = sacrebleu.corpus_chrf(translations, [refs], word_order=2).score

    return {
        "n": n,
        "parse_rate": parse_ok / n if n else 0.0,
        "parse_ok": parse_ok,
        "pairs_mean": statistics.mean(pair_counts) if pair_counts else 0.0,
        "coverage_mean": statistics.mean(coverages) if coverages else 0.0,
        "chrf_pp": chrf,
        "latency_p50": statistics.median(latencies) if latencies else 0.0,
        "latency_max": max(latencies) if latencies else 0.0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-set", default="pilot")
    ap.add_argument("--target-lang", default="en")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    pattern = f"{args.test_set}_*_{args.target_lang}.jsonl"
    files = sorted(RESULTS_DIR.glob(pattern))
    if not files:
        raise SystemExit(f"no results matching {pattern} in {RESULTS_DIR}")

    # First, find the cerebras file to build silver-translation index
    silver_by_id = {}
    for f in files:
        if "cerebras" in f.name:
            for line in f.open():
                row = json.loads(line)
                p = try_parse(row.get("raw", "") or "")
                if p and isinstance(p.get("t"), str):
                    silver_by_id[row["id"]] = p["t"].strip()
            break

    table = {}
    for f in files:
        rows = [json.loads(l) for l in f.open()]
        # Recover system tag from filename
        sys_tag = f.stem.replace(f"{args.test_set}_", "").replace(
            f"_{args.target_lang}", "")
        table[sys_tag] = score_system(rows, silver_by_id)

    # Print table
    header = (f"{'system':<25} {'parse':>6} {'pairs':>6} {'cov':>6} "
              f"{'chrF++':>7} {'p50_s':>7} {'max_s':>7}")
    print(header)
    print("-" * len(header))
    # Order: cerebras silver first, then locals by parse rate desc
    order = sorted(table.items(),
                   key=lambda kv: (0 if "cerebras" in kv[0] else 1,
                                   -kv[1]["parse_rate"]))
    for sys_tag, s in order:
        chrf = f"{s['chrf_pp']:>7.2f}" if s["chrf_pp"] is not None else "    n/a"
        print(f"{sys_tag:<25} {s['parse_rate']*100:>5.0f}% "
              f"{s['pairs_mean']:>6.1f} {s['coverage_mean']*100:>5.0f}% "
              f"{chrf} {s['latency_p50']:>7.2f} {s['latency_max']:>7.2f}")

    out = args.out or f"data/alignment_eval/{args.test_set}_scores.json"
    Path(out).write_text(json.dumps(table, ensure_ascii=False, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
