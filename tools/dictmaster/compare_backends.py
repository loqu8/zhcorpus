#!/usr/bin/env python3
"""Compare translation backends: MiniMax M2.7, M2.5, Cerebras Qwen3-235B, Anthropic, OpenAI.

Runs the same 20 entries through each backend and compares quality + timing.
"""

import json
import os
import sqlite3
import time
from pathlib import Path

from tools.dictmaster.retranslate_single_chars import (
    SYSTEM_V2, TEMPLATE_V2, get_community_defs, get_sample_sentences,
)
from tools.dictmaster.translate.prompts import ALL_TARGET_LANGS, LANG_NAMES, parse_universal_response
from tools.dictmaster.schema import DEFAULT_DB_PATH
from tools.dictmaster.script_validator import validate_definition

# Load credentials
CREDS_PATH = Path("/mnt/a/loqu8/credentials.json")
with open(CREDS_PATH) as f:
    CREDS = json.load(f)


def _build_prompt(conn, headword_id, traditional, simplified, pinyin, pos):
    """Build the prompt for a single entry (same as translate_one but without calling API)."""
    community = get_community_defs(conn, headword_id)
    sentences = get_sample_sentences(simplified)

    ctx_lines = []
    for lang, defn in community.items():
        lang_name = LANG_NAMES.get(lang, lang)
        ctx_lines.append(f"  {lang_name}: {defn}")

    ex_lines = []
    for text, source in sentences:
        ex_lines.append(f"  [{source}] {text}")
    if not ex_lines:
        ex_lines.append("  (none available)")

    lang_lines = "\n".join(f"{lang}:" for lang in ALL_TARGET_LANGS)

    scope_warning = ""
    en_community = community.get("en", "")
    is_proper = pinyin and pinyin[0].isupper()
    is_narrow = any(kw in en_community.lower() for kw in [
        "surname", "only used in", "variant of", "abbr. for",
        "old variant", "used in place name",
    ])
    if is_proper and is_narrow:
        scope_warning = (
            f'\n\u26a0\ufe0f SCOPE WARNING: Capitalized pinyin "{pinyin}" = PROPER NOUN reading.\n'
            f'The reference says: "{en_community.split("(")[0].strip()}"\n'
            f'Output ONLY this narrow meaning. Do NOT add the general meaning of {simplified}.\n'
        )
    elif is_narrow:
        scope_warning = (
            f'\n\u26a0\ufe0f SCOPE WARNING: This is a NARROW entry.\n'
            f'The reference says: "{en_community.split("(")[0].strip()}"\n'
            f'Output ONLY this specific meaning. Do NOT substitute common meanings.\n'
        )
    elif is_proper:
        scope_warning = (
            f'\n\u26a0\ufe0f SCOPE WARNING: Capitalized pinyin "{pinyin}" = PROPER NOUN reading.\n'
            f'This entry is a surname, place name, or abbreviation. Translate ONLY as such.\n'
        )

    return TEMPLATE_V2.format(
        traditional=traditional,
        simplified=simplified,
        pinyin=pinyin or "",
        pos=pos or "unknown",
        scope_warning=scope_warning,
        context_definitions="\n".join(ctx_lines) if ctx_lines else "  (none)",
        examples="\n".join(ex_lines),
        lang_lines=lang_lines,
    ), community


def call_minimax(system, prompt, model="MiniMax-M2.7"):
    """Call MiniMax via Anthropic-compatible API."""
    from anthropic import Anthropic
    config_path = Path.home() / ".claude" / "settings.minimax.json"
    with open(config_path) as f:
        env = json.load(f).get("env", {})
    client = Anthropic(
        api_key=env["ANTHROPIC_AUTH_TOKEN"],
        base_url=env["ANTHROPIC_BASE_URL"],
    )
    parts = []
    with client.messages.stream(
        model=model, max_tokens=2048, system=system,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            parts.append(text)
    return "".join(parts).strip()


def call_cerebras(system, prompt):
    """Call Cerebras Qwen3-235B via OpenAI-compatible API."""
    from openai import OpenAI
    client = OpenAI(
        api_key=CREDS["cerebras_api"]["api_key"],
        base_url=CREDS["cerebras_api"]["base_url"],
    )
    resp = client.chat.completions.create(
        model="qwen-3-235b-a22b-instruct-2507",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        max_tokens=2048,
    )
    return resp.choices[0].message.content.strip()


def call_anthropic(system, prompt):
    """Call Anthropic Claude via API."""
    from anthropic import Anthropic
    client = Anthropic(api_key=CREDS["anthropic_api"]["api_key"])
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def call_openai(system, prompt):
    """Call OpenAI GPT-4o-mini via API."""
    from openai import OpenAI
    client = OpenAI(api_key=CREDS["openai_api"]["api_key"])
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        max_tokens=2048,
    )
    return resp.choices[0].message.content.strip()


BACKENDS = {
    "minimax-m27": lambda s, p: call_minimax(s, p, "MiniMax-M2.7"),
    "minimax-m25": lambda s, p: call_minimax(s, p, "MiniMax-M2.5"),
    "cerebras-qwen235b": call_cerebras,
    "anthropic-haiku45": call_anthropic,
    "openai-gpt4omini": call_openai,
}


def score_result(result: dict[str, str], community: dict[str, str]) -> dict:
    """Score a result: lang count, validation pass rate, cedict first-sense match."""
    total_langs = len(result)
    valid = 0
    for lang, defn in result.items():
        if defn:
            ok, _ = validate_definition(lang, defn)
            if ok:
                valid += 1

    # Check EN first sense against cedict
    en_community = community.get("en", "")
    en_result = result.get("en", "")
    cedict_first = ""
    if en_community:
        # Extract first sense from cedict
        raw = en_community.split("(")[0].strip()  # strip source tag
        cedict_first = raw.split("/")[0].split(";")[0].strip().lower()

    first_match = cedict_first in en_result.lower() if cedict_first and en_result else None

    return {
        "langs": total_langs,
        "valid": valid,
        "first_sense_match": first_match,
    }


def main():
    conn = sqlite3.connect(str(DEFAULT_DB_PATH))
    conn.row_factory = sqlite3.Row

    # Pick 20 test entries: mix of known-bad + common chars
    test_chars = [
        # Known bad from original pipeline
        "猪", "事", "钱", "菜", "员", "错",
        # Common chars (should be stable)
        "人", "大", "水", "马", "书", "好",
        # Surnames (scope test)
        "张", "李",
        # Tricky tonal readings
        "曲", "了",
        # Less common
        "颇", "碎", "砖", "冻",
    ]

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

    print(f"Testing {len(entries)} entries across {len(BACKENDS)} backends\n")

    # Pre-build all prompts
    prompts = []
    for e in entries:
        prompt, community = _build_prompt(
            conn, e["id"], e["traditional"], e["simplified"], e["pinyin"], e["pos"]
        )
        prompts.append((e, prompt, community))

    results = {}
    for backend_name, backend_fn in BACKENDS.items():
        print(f"\n{'='*60}")
        print(f"Backend: {backend_name}")
        print(f"{'='*60}")

        backend_results = []
        total_time = 0
        errors = 0

        for entry, prompt, community in prompts:
            char = entry["simplified"]
            py = entry["pinyin"]

            t0 = time.time()
            try:
                raw = backend_fn(SYSTEM_V2, prompt)
                elapsed = time.time() - t0
                total_time += elapsed
                parsed = parse_universal_response(raw)
                scores = score_result(parsed, community)
                en_def = parsed.get("en", "(none)")[:60]
                print(f"  {char} ({py}): {elapsed:.1f}s, {scores['langs']}lang, "
                      f"{scores['valid']}valid, en=\"{en_def}\"")
                backend_results.append({
                    "char": char, "pinyin": py, "elapsed": elapsed,
                    "result": parsed, "scores": scores, "error": None,
                })
            except Exception as e:
                elapsed = time.time() - t0
                total_time += elapsed
                errors += 1
                err_msg = str(e)[:80]
                print(f"  {char} ({py}): ERROR {elapsed:.1f}s — {err_msg}")
                backend_results.append({
                    "char": char, "pinyin": py, "elapsed": elapsed,
                    "result": {}, "scores": {}, "error": err_msg,
                })

        # Summary
        successful = [r for r in backend_results if not r["error"]]
        avg_time = sum(r["elapsed"] for r in successful) / len(successful) if successful else 0
        avg_langs = sum(r["scores"]["langs"] for r in successful) / len(successful) if successful else 0
        avg_valid = sum(r["scores"]["valid"] for r in successful) / len(successful) if successful else 0
        first_matches = sum(1 for r in successful if r["scores"].get("first_sense_match"))
        first_total = sum(1 for r in successful if r["scores"].get("first_sense_match") is not None)

        print(f"\n  SUMMARY: {len(successful)}/{len(entries)} ok, {errors} errors")
        print(f"  Avg time: {avg_time:.1f}s | Avg langs: {avg_langs:.0f} | Avg valid: {avg_valid:.0f}")
        print(f"  First-sense match: {first_matches}/{first_total}")
        print(f"  Total time: {total_time:.0f}s")

        results[backend_name] = {
            "entries": backend_results,
            "summary": {
                "success": len(successful), "errors": errors,
                "avg_time": avg_time, "avg_langs": avg_langs,
                "avg_valid": avg_valid, "first_match": first_matches,
                "first_total": first_total, "total_time": total_time,
            },
        }

    # Final comparison table
    print(f"\n{'='*60}")
    print("COMPARISON TABLE")
    print(f"{'='*60}")
    print(f"{'Backend':<22} {'OK':>3} {'Err':>4} {'Avg s':>6} {'Langs':>5} {'Valid':>5} {'1st%':>5} {'Total':>6}")
    print("-" * 60)
    for name, data in results.items():
        s = data["summary"]
        pct = f"{s['first_match']/s['first_total']*100:.0f}%" if s["first_total"] else "n/a"
        print(f"{name:<22} {s['success']:>3} {s['errors']:>4} {s['avg_time']:>5.1f}s "
              f"{s['avg_langs']:>5.0f} {s['avg_valid']:>5.0f} {pct:>5} {s['total_time']:>5.0f}s")

    # Save full results
    out_path = Path("logs/backend-comparison.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nFull results saved to {out_path}")


if __name__ == "__main__":
    main()
