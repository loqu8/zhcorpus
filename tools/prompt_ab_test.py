#!/usr/bin/env python3
"""A/B test prompt variants for MiniMax universal translation.

Runs batches of 20 headwords against two prompt variants and prints
side-by-side comparison focused on problem languages (ja, ko, tl, fa).

Usage:
    .venv/bin/python tools/prompt_ab_test.py --iterations 10
    .venv/bin/python tools/prompt_ab_test.py --iterations 3 --offset 100
"""

import argparse
import re
import sys
import time
from pathlib import Path

from tools.dictmaster.schema import DEFAULT_DB_PATH, get_connection
from tools.dictmaster.translate.minimax_api import _chat
from tools.dictmaster.translate.prompts import (
    ALL_TARGET_LANGS,
    LANG_NAMES,
    UNIVERSAL_SYSTEM_PROMPT,
    build_universal_batch_prompt,
    parse_universal_batch_response,
)

# ── Prompt variants ──────────────────────────────────────────────────

PROMPT_A = """\
You are a professional multilingual Chinese lexicographer producing \
dictionary-style definitions in 12 languages.

Rules:
- Output EXACTLY one line per language in format "xx: def1/def2"
- Be concise: dictionary style, not full sentences
- Use the target language exclusively for each definition
- For verbs, start with the infinitive form appropriate to the target language
- For nouns, give the most common equivalent(s)
- Maximum 5 glosses per entry
- If an existing definition is provided, you may rewrite it for consistency
- No explanatory notes, no parenthetical qualifiers unless essential

CRITICAL: Every non-Chinese definition must contain ZERO Chinese characters (汉字). \
If you catch yourself writing 漢字/汉字 in any definition, replace them with the \
target language equivalent.

Language-specific rules:
- ja (Japanese): Produce a JAPANESE MEANING — a definition a Japanese person would \
understand. NEVER echo the Chinese headword characters. NEVER output only a kana \
reading. Write explanatory glosses using native Japanese words. \
Example: 银行 → 金融機関/お金を預ける所 (NOT 銀行, NOT ぎんこう). \
For phone numbers or codes, describe their PURPOSE: 緊急通報番号/警察への通報用番号.
- ko (Korean): Write in Hangul ONLY. No Hanja (漢字), no romanization, no English. \
Every character must be Hangul (ㄱ-ㅎ, ㅏ-ㅣ, 가-힣) or slash/space. \
Example: 은행 → 금융 기관/돈을 맡기는 곳 (NOT 銀行).
- tl (Tagalog): Use natural Tagalog vocabulary and grammar. Do NOT calque from \
English word-by-word. Prefer established Filipino equivalents.
- fa (Persian): Write definitions in Persian script (فارسی). Use native Persian vocabulary.
- vi (Vietnamese): Write in Vietnamese with proper diacritics. No Chinese characters.
- ru (Russian): Use Cyrillic only. No Latin transliterations."""

PROMPT_B = """\
You are a senior lexicographer undergoing peer review for a major multilingual \
dictionary. Your reviewers will reject any entry containing characters from the \
wrong writing system. Your reputation depends on accuracy.

You produce dictionary-style definitions in 12 languages.

Format rules:
- Output EXACTLY one line per language: "xx: gloss1/gloss2/gloss3"
- Separate glosses with "/" only (never semicolons, commas, or other separators)
- 1-5 short glosses per entry, each gloss under 5 words
- Use only ASCII parentheses ( ) never fullwidth （）
- No explanatory notes, no pronunciation guides
- If the entry is a cross-reference ("see X"), translate the MEANING of X \
instead of writing "see" + Chinese characters

ABSOLUTE RULE — ZERO Chinese characters (汉字/漢字) in any non-ja definition. \
This includes 的, 是, 在, 了, 不, and ALL others. Your peer reviewers run \
automated script detection and will reject your submission on any violation.

Language-specific rules:
- ja (Japanese): Produce a JAPANESE MEANING using native Japanese vocabulary. \
NEVER echo the Chinese headword. NEVER output only a kana reading. \
Use Japanese kanji (新字体), NOT simplified Chinese (弾 not 弹, 機 not 机). \
Example: 银行 → 金融機関/預金する所 (NOT 銀行, NOT ぎんこう).
- ko (Korean): Hangul ONLY (가-힣) plus ASCII letters/numbers/spaces/slashes. \
ZERO Chinese characters, ZERO Japanese kana, ZERO fullwidth punctuation. \
Use ( ) not （）. Your reviewer runs: if any char is not [가-힣a-zA-Z0-9 /().-], reject.
- tl (Tagalog): Natural Tagalog, not English calques. Use Filipino equivalents.
- fa (Persian): Persian script only. Native Persian vocabulary.
- vi (Vietnamese): Vietnamese with diacritics. No Chinese characters.
- ru (Russian): Cyrillic only. No Latin transliterations."""

# ── Helpers ──────────────────────────────────────────────────────────

FOCUS_LANGS = ["ja", "ko", "tl", "fa"]  # languages we're specifically watching

# Regex for detecting CJK characters (Chinese/Japanese kanji)
CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uF900-\uFAFF]")
# Regex for Hangul
HANGUL_RE = re.compile(r"[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]")


def has_cjk(text: str) -> bool:
    return bool(CJK_RE.search(text))


def flag_issues(lang: str, defn: str) -> list[str]:
    """Flag quality issues in a definition."""
    issues = []
    if lang != "ja" and lang not in ("zh",) and has_cjk(defn):
        issues.append("CJK_LEAK")
    if lang == "ko":
        # Check for non-Hangul, non-ASCII, non-space/slash characters
        cleaned = re.sub(r"[\s/(),.\-0-9a-zA-Z]", "", defn)
        cleaned = re.sub(r"[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]", "", cleaned)
        if cleaned:
            issues.append(f"NON_HANGUL:{cleaned[:10]}")
    if lang == "ja":
        # Check if definition is just the Chinese headword echoed
        if not any(c in defn for c in "ァ-ヶぁ-ゖー") and len(defn) < 5:
            issues.append("POSSIBLE_ECHO")
    return issues


def run_one_batch(
    entries: list[dict],
    system_prompt: str,
    target_langs: list[str],
) -> list[dict[str, str]]:
    """Run a batch through MiniMax with the given system prompt."""
    prompt = build_universal_batch_prompt(entries, target_langs)
    response = _chat(system_prompt, prompt, max_tokens=8192)
    return parse_universal_batch_response(response, len(entries), target_langs)


def load_headwords(conn, offset: int = 0, limit: int = 20) -> list[dict]:
    """Load headwords that don't have minimax defs yet."""
    rows = conn.execute("""
        SELECT h.id, h.traditional, h.simplified, h.pinyin, h.pos
        FROM headwords h
        WHERE NOT EXISTS (
            SELECT 1 FROM definitions d
            WHERE d.headword_id = h.id AND d.source = 'minimax'
        )
        ORDER BY h.id
        LIMIT ? OFFSET ?
    """, (limit, offset)).fetchall()

    entries = []
    for row in rows:
        context = conn.execute(
            "SELECT lang, definition FROM definitions WHERE headword_id = ?",
            (row["id"],),
        ).fetchall()
        context_defs = {r["lang"]: r["definition"] for r in context}
        entries.append({
            "id": row["id"],
            "traditional": row["traditional"],
            "simplified": row["simplified"],
            "pinyin": row["pinyin"],
            "pos": row["pos"] or "",
            "context_defs": context_defs,
        })
    return entries


def print_comparison(entries, results_a, results_b, iteration: int):
    """Print side-by-side comparison focused on problem languages."""
    print(f"\n{'#' * 78}")
    print(f"# ITERATION {iteration}: {len(entries)} headwords")
    print(f"{'#' * 78}")

    issues_a_total = 0
    issues_b_total = 0

    for i, entry in enumerate(entries):
        defs_a = results_a[i] if i < len(results_a) else {}
        defs_b = results_b[i] if i < len(results_b) else {}

        hw = f"{entry['traditional']} / {entry['simplified']}  [{entry['pinyin']}]"
        print(f"\n{'─' * 70}")
        print(f"  {hw}")

        # Show existing defs briefly
        ctx = entry.get("context_defs", {})
        if "en" in ctx:
            print(f"  en (orig): {ctx['en'][:80]}")

        # Compare focus languages
        for lang in FOCUS_LANGS:
            a = defs_a.get(lang, "(missing)")
            b = defs_b.get(lang, "(missing)")

            flags_a = flag_issues(lang, a) if a != "(missing)" else ["MISSING"]
            flags_b = flag_issues(lang, b) if b != "(missing)" else ["MISSING"]
            issues_a_total += len(flags_a)
            issues_b_total += len(flags_b)

            marker_a = f" ⚠ {','.join(flags_a)}" if flags_a else ""
            marker_b = f" ⚠ {','.join(flags_b)}" if flags_b else ""

            if a == b:
                print(f"  {lang} [SAME]: {a}{marker_a}")
            else:
                print(f"  {lang} [A]: {a}{marker_a}")
                print(f"  {lang} [B]: {b}{marker_b}")

        # Also check ALL langs for CJK leaks
        for lang in ALL_TARGET_LANGS:
            if lang in FOCUS_LANGS or lang == "ja":
                continue
            for label, defs in [("A", defs_a), ("B", defs_b)]:
                defn = defs.get(lang, "")
                if defn and has_cjk(defn):
                    print(f"  {lang} [{label}]: {defn} ⚠ CJK_LEAK")

    print(f"\n{'=' * 70}")
    print(f"  ISSUES: A={issues_a_total}  B={issues_b_total}")
    if issues_b_total < issues_a_total:
        print(f"  → Prompt B wins ({issues_a_total - issues_b_total} fewer issues)")
    elif issues_a_total < issues_b_total:
        print(f"  → Prompt A wins ({issues_b_total - issues_a_total} fewer issues)")
    else:
        print(f"  → Tie")
    return issues_a_total, issues_b_total


def main():
    parser = argparse.ArgumentParser(description="A/B test prompt variants")
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--offset", type=int, default=0,
                        help="Starting offset in headwords table")
    args = parser.parse_args()

    conn = get_connection(DEFAULT_DB_PATH)
    target_langs = ALL_TARGET_LANGS

    total_a = 0
    total_b = 0

    for it in range(args.iterations):
        offset = args.offset + it * args.batch_size
        entries = load_headwords(conn, offset=offset, limit=args.batch_size)
        if not entries:
            print(f"No more headwords at offset {offset}")
            break

        hw_sample = ", ".join(e["simplified"] for e in entries[:5])
        print(f"\nIteration {it + 1}/{args.iterations}: offset={offset}, "
              f"words=[{hw_sample}, ...]")

        # Run A
        print(f"  Running Prompt A...", end="", flush=True)
        t0 = time.time()
        results_a = run_one_batch(entries, PROMPT_A, target_langs)
        print(f" {time.time() - t0:.1f}s")

        # Run B
        print(f"  Running Prompt B...", end="", flush=True)
        t0 = time.time()
        results_b = run_one_batch(entries, PROMPT_B, target_langs)
        print(f" {time.time() - t0:.1f}s")

        issues_a, issues_b = print_comparison(entries, results_a, results_b, it + 1)
        total_a += issues_a
        total_b += issues_b

    print(f"\n{'=' * 78}")
    print(f"GRAND TOTAL over {args.iterations} iterations:")
    print(f"  Prompt A issues: {total_a}")
    print(f"  Prompt B issues: {total_b}")
    if total_b < total_a:
        print(f"  → Prompt B wins overall ({total_a - total_b} fewer issues)")
    elif total_a < total_b:
        print(f"  → Prompt A wins overall ({total_b - total_a} fewer issues)")
    else:
        print(f"  → Tie overall")

    conn.close()


if __name__ == "__main__":
    main()
