#!/usr/bin/env python3
"""Test MiniMax direct API key (not Coding Plan) with M2.5 and M2.7."""

import json
import sqlite3
import time
from pathlib import Path

from tools.dictmaster.retranslate_single_chars import (
    SYSTEM_V2, get_community_defs, get_sample_sentences,
)
from tools.dictmaster.translate.prompts import ALL_TARGET_LANGS, LANG_NAMES, parse_universal_response
from tools.dictmaster.schema import DEFAULT_DB_PATH
from tools.dictmaster.script_validator import validate_definition
from tools.dictmaster.compare_backends import _build_prompt

CREDS_PATH = Path("/mnt/a/loqu8/credentials.json")
with open(CREDS_PATH) as f:
    CREDS = json.load(f)

MINIMAX_DIRECT_KEY = CREDS["minimax_api"]["api_key"]


def call_minimax_direct(system, prompt, model="MiniMax-M2.7"):
    """Call MiniMax via their direct API (Anthropic-compatible endpoint)."""
    from anthropic import Anthropic
    # Direct API key still uses the Anthropic-compatible endpoint
    client = Anthropic(
        api_key=MINIMAX_DIRECT_KEY,
        base_url="https://api.minimax.io/anthropic",
    )
    parts = []
    with client.messages.stream(
        model=model, max_tokens=2048, system=system,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            parts.append(text)
    return "".join(parts).strip()


def run_test(model_name, model_id):
    conn = sqlite3.connect(str(DEFAULT_DB_PATH))
    conn.row_factory = sqlite3.Row

    test_chars = ["猪", "事", "钱", "菜", "员", "错", "人", "大", "水", "好",
                  "张", "李", "曲", "了", "颇", "碎", "砖", "冻", "马", "书"]

    entries = []
    for char in test_chars:
        row = conn.execute(
            "SELECT id, traditional, simplified, pinyin, pos, sfreq "
            "FROM headwords WHERE simplified = ? AND pinyin NOT LIKE '%%)5' "
            "ORDER BY sfreq DESC NULLS LAST LIMIT 1",
            (char,),
        ).fetchone()
        if row:
            entries.append(dict(row))

    print(f"\n{'='*60}")
    print(f"MiniMax Direct API: {model_name} ({model_id})")
    print(f"{'='*60}")

    total_time = 0
    success = 0
    errors = 0
    total_valid = 0
    first_matches = 0
    first_total = 0

    for entry in entries:
        char = entry["simplified"]
        py = entry["pinyin"]
        prompt, community = _build_prompt(
            conn, entry["id"], entry["traditional"], entry["simplified"],
            entry["pinyin"], entry["pos"]
        )

        t0 = time.time()
        try:
            raw = call_minimax_direct(SYSTEM_V2, prompt, model_id)
            elapsed = time.time() - t0
            total_time += elapsed
            parsed = parse_universal_response(raw)

            valid = sum(1 for l, d in parsed.items() if d and validate_definition(l, d)[0])
            total_valid += valid

            en_def = parsed.get("en", "(none)")[:60]

            # First sense check
            en_community = community.get("en", "")
            if en_community:
                raw_c = en_community.split("(")[0].strip()
                cedict_first = raw_c.split("/")[0].split(";")[0].strip().lower()
                if cedict_first:
                    first_total += 1
                    if cedict_first in en_def.lower():
                        first_matches += 1

            success += 1
            print(f"  {char} ({py}): {elapsed:.1f}s, {len(parsed)}lang, {valid}valid, en=\"{en_def}\"")
        except Exception as e:
            elapsed = time.time() - t0
            total_time += elapsed
            errors += 1
            print(f"  {char} ({py}): ERROR {elapsed:.1f}s — {str(e)[:80]}")

    avg_time = total_time / success if success else 0
    avg_valid = total_valid / success if success else 0
    pct = f"{first_matches/first_total*100:.0f}%" if first_total else "n/a"

    print(f"\n  SUMMARY: {success}/20 ok, {errors} errors")
    print(f"  Avg time: {avg_time:.1f}s | Avg valid: {avg_valid:.0f}/26 | 1st sense: {pct}")
    print(f"  Total time: {total_time:.0f}s")

    return {"success": success, "errors": errors, "avg_time": avg_time,
            "avg_valid": avg_valid, "total_time": total_time,
            "first_match_pct": pct}


if __name__ == "__main__":
    r27 = run_test("M2.7", "MiniMax-M2.7")
    r25 = run_test("M2.5", "MiniMax-M2.5")

    print(f"\n{'='*60}")
    print("COMPARISON (Direct API Key)")
    print(f"{'='*60}")
    print(f"{'Model':<12} {'OK':>3} {'Err':>4} {'Avg s':>6} {'Valid':>5} {'1st%':>5} {'Total':>6}")
    print("-" * 45)
    for name, r in [("M2.7", r27), ("M2.5", r25)]:
        print(f"{name:<12} {r['success']:>3} {r['errors']:>4} {r['avg_time']:>5.1f}s "
              f"{r['avg_valid']:>5.0f} {r['first_match_pct']:>5} {r['total_time']:>5.0f}s")
