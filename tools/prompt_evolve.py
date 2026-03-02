#!/usr/bin/env python3
"""Self-evolving prompt optimization for MiniMax dictionary translation.

Each round:
  1. Translate 20 headwords with the current prompt
  2. Ask MiniMax to critique the output and suggest prompt improvements
  3. Ask MiniMax to rewrite the prompt incorporating its own suggestions
  4. Translate the SAME 20 headwords with the new prompt
  5. Compare and report

Usage:
    .venv/bin/python -m tools.prompt_evolve --rounds 5
    .venv/bin/python -m tools.prompt_evolve --rounds 3 --offset 200
"""

import argparse
import re
import time
from pathlib import Path

from tools.dictmaster.schema import DEFAULT_DB_PATH, get_connection
from tools.dictmaster.translate.minimax_api import _chat
from tools.dictmaster.translate.prompts import (
    ALL_TARGET_LANGS,
    LANG_NAMES,
    build_universal_batch_prompt,
    parse_universal_batch_response,
)

# ── Starting prompt (best so far = Prompt B from A/B testing) ────────

STARTING_PROMPT = """\
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

# ── Critique prompt ──────────────────────────────────────────────────

CRITIQUE_SYSTEM = """\
You are a multilingual dictionary quality reviewer. You are an expert in \
Chinese, Japanese, Korean, and Southeast Asian languages. You review \
AI-generated dictionary translations for errors."""

CRITIQUE_TEMPLATE = """\
Below is the system prompt used to generate multilingual dictionary translations, \
followed by 20 Chinese headwords and the translations produced.

SYSTEM PROMPT USED:
---
{system_prompt}
---

HEADWORDS AND TRANSLATIONS:
{translations}

Please review the translations and:

1. LIST every specific error you find. For each error give:
   - The headword
   - The language
   - What's wrong (e.g. "Chinese character 的 leaked into Korean", "Japanese definition \
just echoes the headword kanji", "Korean uses fullwidth parentheses （）")
   - What it should be instead

2. IDENTIFY patterns — what kinds of errors keep recurring?

3. SUGGEST specific additions or changes to the system prompt that would \
prevent these errors. Be concrete — give exact wording to add/change.

Focus especially on:
- Chinese characters (汉字) leaking into non-Chinese definitions
- Japanese definitions that just echo the Chinese headword or give only kana readings
- Korean definitions with non-Hangul characters (Chinese, Japanese, fullwidth punctuation)
- Definitions that are too verbose or explanatory instead of dictionary-style glosses
- Wrong script in any language"""

REWRITE_SYSTEM = """\
You are a prompt engineer specializing in multilingual NLP tasks. \
You rewrite system prompts to be more effective."""

REWRITE_TEMPLATE = """\
Here is the current system prompt for a multilingual Chinese dictionary translator:

CURRENT PROMPT:
---
{current_prompt}
---

Here is a quality review identifying errors in the output:

REVIEW:
---
{critique}
---

Rewrite the system prompt to fix the identified issues. Rules:
- Keep the same overall structure and format instructions
- Incorporate the reviewer's specific suggestions
- Be concrete and explicit about constraints (especially script/character rules)
- Keep it under 2000 characters — concise prompts work better than long ones
- Output ONLY the new system prompt, nothing else"""


# ── Helpers ──────────────────────────────────────────────────────────

CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uF900-\uFAFF]")
FOCUS_LANGS = ["ja", "ko", "tl", "fa", "vi", "ru"]


def has_cjk(text: str) -> bool:
    return bool(CJK_RE.search(text))


def count_issues(entries, results) -> tuple[int, list[str]]:
    """Count automated issues and return descriptions."""
    issues = []
    for i, entry in enumerate(entries):
        defs = results[i] if i < len(results) else {}
        hw = entry["simplified"]
        for lang, defn in defs.items():
            if lang != "ja" and has_cjk(defn):
                issues.append(f"{hw}/{lang}: CJK leak — {defn[:50]}")
            if lang == "ko":
                cleaned = re.sub(r"[\s/(),.\-0-9a-zA-Z]", "", defn)
                cleaned = re.sub(r"[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]", "", cleaned)
                if cleaned:
                    issues.append(f"{hw}/ko: non-Hangul chars '{cleaned[:10]}' — {defn[:50]}")
    return len(issues), issues


def format_translations(entries, results) -> str:
    """Format entries + results for the critique prompt."""
    blocks = []
    for i, entry in enumerate(entries):
        defs = results[i] if i < len(results) else {}
        hw = f"{entry['traditional']} / {entry['simplified']}  [{entry['pinyin']}]"
        ctx = entry.get("context_defs", {})
        en_orig = ctx.get("en", "(none)")

        lines = [f"{i+1}. {hw}", f"   English (original): {en_orig[:80]}"]
        lines.append("   Translations:")
        for lang in ALL_TARGET_LANGS:
            defn = defs.get(lang, "(missing)")
            lines.append(f"     {lang}: {defn}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def run_batch(entries, system_prompt, target_langs):
    """Run a batch through MiniMax."""
    prompt = build_universal_batch_prompt(entries, target_langs)
    response = _chat(system_prompt, prompt, max_tokens=8192)
    return parse_universal_batch_response(response, len(entries), target_langs)


def load_headwords(conn, offset=0, limit=20):
    """Load headwords without minimax defs."""
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
        entries.append({
            "id": row["id"],
            "traditional": row["traditional"],
            "simplified": row["simplified"],
            "pinyin": row["pinyin"],
            "pos": row["pos"] or "",
            "context_defs": {r["lang"]: r["definition"] for r in context},
        })
    return entries


def main():
    parser = argparse.ArgumentParser(description="Self-evolving prompt optimization")
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--offset", type=int, default=0)
    args = parser.parse_args()

    conn = get_connection(DEFAULT_DB_PATH)
    target_langs = ALL_TARGET_LANGS
    current_prompt = STARTING_PROMPT

    for rnd in range(1, args.rounds + 1):
        offset = args.offset + (rnd - 1) * args.batch_size
        entries = load_headwords(conn, offset=offset, limit=args.batch_size)
        if not entries:
            print(f"No more headwords at offset {offset}")
            break

        hw_sample = ", ".join(e["simplified"] for e in entries[:5])
        print(f"\n{'#' * 78}")
        print(f"# ROUND {rnd}/{args.rounds}  (offset={offset}, words=[{hw_sample}, ...])")
        print(f"{'#' * 78}")

        # Step 1: Translate with current prompt
        print(f"\n  [1/4] Translating with current prompt...", end="", flush=True)
        t0 = time.time()
        results_before = run_batch(entries, current_prompt, target_langs)
        print(f" {time.time() - t0:.0f}s")

        n_issues_before, issue_list_before = count_issues(entries, results_before)
        print(f"        Automated issues: {n_issues_before}")
        for iss in issue_list_before[:5]:
            print(f"          - {iss}")
        if len(issue_list_before) > 5:
            print(f"          ... and {len(issue_list_before) - 5} more")

        # Step 2: Ask MiniMax to critique
        print(f"\n  [2/4] Getting self-critique...", end="", flush=True)
        t0 = time.time()
        formatted = format_translations(entries, results_before)
        critique_prompt = CRITIQUE_TEMPLATE.format(
            system_prompt=current_prompt,
            translations=formatted,
        )
        critique = _chat(CRITIQUE_SYSTEM, critique_prompt, max_tokens=4096)
        print(f" {time.time() - t0:.0f}s")
        print(f"\n  --- CRITIQUE ---")
        # Print first 40 lines
        for line in critique.split("\n")[:40]:
            print(f"  {line}")
        if len(critique.split("\n")) > 40:
            print(f"  ... ({len(critique.split(chr(10)))} lines total)")

        # Step 3: Ask MiniMax to rewrite the prompt
        print(f"\n  [3/4] Generating improved prompt...", end="", flush=True)
        t0 = time.time()
        rewrite_prompt = REWRITE_TEMPLATE.format(
            current_prompt=current_prompt,
            critique=critique,
        )
        new_prompt = _chat(REWRITE_SYSTEM, rewrite_prompt, max_tokens=2048)
        print(f" {time.time() - t0:.0f}s")

        # Clean up — sometimes model wraps in markdown code blocks
        new_prompt = new_prompt.strip()
        if new_prompt.startswith("```"):
            new_prompt = re.sub(r"^```\w*\n?", "", new_prompt)
            new_prompt = re.sub(r"\n?```$", "", new_prompt)
            new_prompt = new_prompt.strip()

        print(f"\n  --- NEW PROMPT ({len(new_prompt)} chars) ---")
        for line in new_prompt.split("\n"):
            print(f"  {line}")

        # Step 4: Re-translate SAME words with new prompt
        print(f"\n  [4/4] Re-translating with improved prompt...", end="", flush=True)
        t0 = time.time()
        results_after = run_batch(entries, new_prompt, target_langs)
        print(f" {time.time() - t0:.0f}s")

        n_issues_after, issue_list_after = count_issues(entries, results_after)
        print(f"        Automated issues: {n_issues_after}")
        for iss in issue_list_after[:5]:
            print(f"          - {iss}")
        if len(issue_list_after) > 5:
            print(f"          ... and {len(issue_list_after) - 5} more")

        # Show side-by-side for focus languages
        print(f"\n  --- COMPARISON (focus langs) ---")
        for i, entry in enumerate(entries):
            defs_before = results_before[i] if i < len(results_before) else {}
            defs_after = results_after[i] if i < len(results_after) else {}
            hw = f"{entry['simplified']}  [{entry['pinyin']}]"

            changed = False
            for lang in FOCUS_LANGS:
                a = defs_before.get(lang, "")
                b = defs_after.get(lang, "")
                if a != b:
                    changed = True
                    break

            if changed:
                print(f"\n    {hw}")
                for lang in FOCUS_LANGS:
                    a = defs_before.get(lang, "(missing)")
                    b = defs_after.get(lang, "(missing)")
                    if a == b:
                        continue
                    print(f"      {lang} BEFORE: {a}")
                    print(f"      {lang} AFTER:  {b}")

        # Verdict
        print(f"\n  {'=' * 60}")
        print(f"  BEFORE: {n_issues_before} issues → AFTER: {n_issues_after} issues")
        if n_issues_after < n_issues_before:
            print(f"  ✓ Improved! Adopting new prompt for next round.")
            current_prompt = new_prompt
        elif n_issues_after == n_issues_before:
            print(f"  = Tie. Adopting new prompt (may fix non-automated issues).")
            current_prompt = new_prompt
        else:
            print(f"  ✗ Worse. Keeping previous prompt.")

    # Final output
    print(f"\n{'#' * 78}")
    print(f"# FINAL PROMPT")
    print(f"{'#' * 78}")
    print(current_prompt)

    conn.close()


if __name__ == "__main__":
    main()
