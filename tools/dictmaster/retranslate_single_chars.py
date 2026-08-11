#!/usr/bin/env python3
"""Re-translate single-char headwords using community-anchored one-at-a-time prompts.

Fixes ~382 known-bad entries where MiniMax hallucinated wrong definitions due to
batch cross-talk with compound words (e.g. 猪→"pig offal" from 猪杂 in same batch).

Usage:
    # Fix the ~382 known-bad entries (from bad_single_char_ids.json)
    python tools/dictmaster/retranslate_single_chars.py --bad-only

    # Re-translate all single-chars by frequency tier
    python tools/dictmaster/retranslate_single_chars.py --min-freq 1000000

    # Dry run
    python tools/dictmaster/retranslate_single_chars.py --bad-only --dry-run
"""

import argparse
import json
import os
import sqlite3
import time
from pathlib import Path

from tools.dictmaster.schema import DEFAULT_DB_PATH, get_connection, ensure_source, upsert_definition
from tools.dictmaster.script_validator import validate_definition
from tools.dictmaster.translate.prompts import ALL_TARGET_LANGS, LANG_NAMES, parse_universal_response

# ---------------------------------------------------------------------------
# Prompt v2 — community-anchored, one-at-a-time, cedict format enforced
# ---------------------------------------------------------------------------

SYSTEM_V2 = """\
You are a professional multilingual Chinese lexicographer producing \
dictionary-style definitions in 26 languages.

OUTPUT FORMAT (strictly enforced):
- Output EXACTLY one line per language in format "xx: def1/def2/def3"
- Separate DISTINCT SENSES with slash /
- Within one sense, use comma for near-synonyms (e.g. "pig, hog")
- Do NOT use semicolons as sense separators — use slash only
- Put the SHORTEST, most common equivalent FIRST
- Maximum 5 senses per entry
- Be concise: dictionary style, not full sentences
- Use the target language exclusively for each definition
- For verbs: infinitive form appropriate to the target language
- For nouns: most common equivalent(s)
- No explanatory notes, no parenthetical qualifiers unless essential
- NEVER fall back to English (or any other language) if you don't know the word — \
paraphrase in the target language instead
- NEVER output incomplete or truncated words — every word must be complete

MEANING ACCURACY (strictly enforced):
- The "Authoritative reference definitions" below are from community-curated \
dictionaries (CC-CEDICT, CFDICT, HanDeDict, etc.) and are CORRECT.
- Your definitions MUST be consistent with these reference meanings.
- Do NOT introduce meanings from compound words containing this character/word.
- Translate the PRIMARY meaning of this headword only.
- If the reference says "surname X" or "abbr. for Y", that IS the definition — \
do NOT expand it to the general meaning of the character. A surname entry means \
ONLY the surname.
- If the reference says "only used in XYZ" or "variant of X", preserve that \
narrow meaning exactly. Do NOT substitute the common meaning of the character.
- Capitalized Pinyin (e.g. "Guan1") indicates a proper noun reading — treat it \
as a proper noun (surname, place name, abbreviation), not the general meaning.

SELF-CHECK (do this before outputting):
- Compare each definition against the authoritative references. If your \
definition contradicts the reference, FIX IT.
- Compare against the example sentences. If your definition doesn't match how \
the word is used in the examples, reconsider.
- If the reference is very specific or narrow, your definition should be equally \
specific — do NOT generalize.

SCRIPT PURITY (strictly enforced — output that violates these rules will be \
rejected and discarded):

1. Each definition must use ONLY the script of its target language.
2. Do NOT copy Latin-script words (English, French, pinyin) into Arabic (ar), \
Persian (fa), Hindi (hi), or Thai (th) definitions. Translate everything into \
the target script. If the existing English definition contains "(Taiwanese, \
pr. [king])" — write the Arabic equivalent in Arabic script, or omit the \
parenthetical entirely.
3. Do NOT copy Cyrillic (Russian) words into non-Russian definitions.
4. Do NOT copy Hangul into Japanese or kana into Korean definitions.
5. EXCEPTION: When a headword is a variant or component of another character, \
you may cite the reference character (e.g. "variant of 夂") — but the rest \
of the definition must be in the target language script only.
6. For ar/fa: pinyin readings like "pou3" must be omitted or transliterated \
into Arabic script. Do NOT leave them in Latin.
7. For ar/fa: the letters X, T, U used as shape descriptors (e.g. "T-shaped") \
are acceptable as single letters only.

Language-specific rules:
- ja (Japanese): Provide the MEANING in Japanese, not just kanji echo or kana \
reading. Write a Japanese definition/gloss that explains the word. Use native \
Japanese vocabulary.
- ko (Korean): Write in Hangul ONLY. Every word must be in Hangul. Do NOT \
include ANY Chinese characters (漢字/한자) — not even for proper nouns, place \
names, or references to other characters. Write 복건성 not 福建省, 보모 not \
保姆, 백분 not 百分. If citing a variant character, describe it in Hangul \
(e.g. "옛 글자" not the character itself).
- tl (Tagalog): Use natural Tagalog vocabulary. Do NOT produce literal \
word-for-word translations from English.
- fa (Persian): Write definitions in Persian script (فارسی) ONLY. Every word \
must be in Persian script. Do NOT include any Latin letters, English words, or \
pinyin. If the existing definition mentions a pronunciation in brackets, \
translate or omit it.
- vi (Vietnamese): Write in Vietnamese with proper diacritics. Do NOT include \
Chinese characters.
- ar (Arabic): Write in Arabic script ONLY. Every word must be in Arabic \
script. Do NOT include any Latin letters, English words, French words, or \
pinyin. Translate all parenthetical notes into Arabic.
- th (Thai): Write in Thai script ONLY. Translate all parenthetical notes into \
Thai. Do NOT leave English or Latin words.
- hi (Hindi): Write in Devanagari script ONLY. Do NOT include English \
transliterations or Arabic script.
- ru (Russian): Write in Cyrillic script. Do NOT include Chinese characters \
(漢字) in the definition — describe the referenced character instead.
- nl (Dutch): Write in standard Dutch. Use natural Dutch compounds and phrasing.
- pt (Portuguese): Write in Brazilian Portuguese. Use proper diacritics.
- it (Italian): Write in standard Italian.
- tr (Turkish): Use proper Turkish characters (ğ, ş, ç, ı, ö, ü). Do NOT \
substitute ASCII equivalents. For idioms and set phrases, use the most natural \
Turkish equivalent — prefer zirve/doruk over literal translations.
- ms (Malay): Write in standard Malay (Bahasa Melayu). This is NOT Indonesian — \
use Malaysian vocabulary and conventions (e.g. "kereta" not "mobil" for car).
- pl (Polish): Use proper Polish diacritics (ą, ć, ę, ł, ń, ó, ś, ź, ż).
- hu (Hungarian): Use proper Hungarian accents (á, é, í, ó, ö, ő, ú, ü, ű).
- cs (Czech): Use proper Czech diacritics (á, č, ď, é, ě, í, ň, ó, ř, š, ť, \
ú, ů, ý, ž).
- el (Greek): Write in Greek script with proper diacritics (tonos). Do NOT \
transliterate from English. Write ONLY in Greek script.
- ro (Romanian): Use proper Romanian diacritics with comma-below (ș, ț), NOT \
cedilla (ş, ţ). NEVER use English words — always use Romanian equivalents.
- et (Estonian): Write in standard Estonian. Use proper characters (ä, ö, ü, õ, \
š, ž)."""

TEMPLATE_V2 = """\
Chinese: {traditional} / {simplified}
Pinyin: {pinyin}
POS: {pos}
{scope_warning}
Authoritative reference definitions:
{context_definitions}

Example sentences from corpus:
{examples}

Produce definitions for each language below. SHORTEST common equivalent FIRST. \
Senses separated by slash /. One line per language.

{lang_lines}"""

CONFIDENCE_TAG = "v2"
PROMPT_VERSION = "v2-single-char-anchored"

# ---------------------------------------------------------------------------
# Corpus example lookup
# ---------------------------------------------------------------------------

_corpus_conn = None

def _get_corpus_conn():
    global _corpus_conn
    if _corpus_conn is None:
        corpus_path = Path("data/artifacts/zhcorpus.db")
        if not corpus_path.exists():
            return None
        _corpus_conn = sqlite3.connect(str(corpus_path))
        _corpus_conn.row_factory = sqlite3.Row
        try:
            _corpus_conn.enable_load_extension(True)
            _corpus_conn.load_extension("lib/libsimple-linux-ubuntu-latest/libsimple")
        except Exception:
            _corpus_conn = None
            return None
    return _corpus_conn


_source_ranges_cache: list[tuple[str, int, int]] | None = None


def _get_source_ranges(cconn: sqlite3.Connection) -> list[tuple[str, int, int]]:
    """Get cached per-source rowid ranges from zhcorpus.db."""
    global _source_ranges_cache
    if _source_ranges_cache is not None:
        return _source_ranges_cache
    try:
        rows = cconn.execute(
            "SELECT name, min_chunk_id, max_chunk_id "
            "FROM source_chunk_ranges ORDER BY min_chunk_id"
        ).fetchall()
        _source_ranges_cache = [(r[0], r[1], r[2]) for r in rows]
    except Exception:
        _source_ranges_cache = []
    return _source_ranges_cache


def get_sample_sentences(term: str, limit: int = 3) -> list[tuple[str, str]]:
    """Pull short, diverse sample sentences using per-source rowid ranges."""
    cconn = _get_corpus_conn()
    if cconn is None:
        return []
    source_ranges = _get_source_ranges(cconn)
    if not source_ranges:
        return []

    results = []
    for name, lo, hi in source_ranges:
        if len(results) >= limit:
            break
        try:
            row = cconn.execute("""
                SELECT c.text
                FROM chunks_fts fts
                JOIN chunks c ON c.rowid = fts.rowid
                WHERE chunks_fts MATCH simple_query(?)
                AND fts.rowid BETWEEN ? AND ?
                AND c.char_count BETWEEN 8 AND 30
                LIMIT 1
            """, (term, lo, hi)).fetchone()
        except Exception:
            continue
        if row and term in row[0]:
            results.append((row[0], name))
    return results


# ---------------------------------------------------------------------------
# Core translation
# ---------------------------------------------------------------------------

def get_community_defs(conn: sqlite3.Connection, headword_id: int) -> dict[str, str]:
    """Get all non-minimax definitions grouped by lang."""
    rows = conn.execute(
        "SELECT lang, source, definition FROM definitions "
        "WHERE headword_id = ? AND source != 'minimax'",
        (headword_id,),
    ).fetchall()
    defs: dict[str, str] = {}
    for r in rows:
        lang = r["lang"]
        if lang not in defs:
            defs[lang] = f"{r['definition']} ({r['source']})"
    return defs


def _get_chat_fn(backend: str = "minimax"):
    """Return the appropriate chat function for the given backend."""
    if backend == "cerebras":
        import json
        from pathlib import Path
        from openai import OpenAI
        creds_path = Path("/mnt/a/loqu8/credentials.json")
        with open(creds_path) as f:
            creds = json.load(f)
        client = OpenAI(
            api_key=creds["cerebras_api"]["api_key"],
            base_url=creds["cerebras_api"]["base_url"],
        )
        def _cerebras_chat(system: str, user: str, max_tokens: int = 2048) -> str:
            resp = client.chat.completions.create(
                model="qwen-3-235b-a22b-instruct-2507",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content.strip()
        return _cerebras_chat
    elif backend == "anthropic":
        import json
        from pathlib import Path
        from anthropic import Anthropic
        creds_path = Path("/mnt/a/loqu8/credentials.json")
        with open(creds_path) as f:
            creds = json.load(f)
        client = Anthropic(api_key=creds["anthropic_api"]["api_key"])
        model = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
        def _anthropic_chat(system: str, user: str, max_tokens: int = 2048) -> str:
            msg = client.messages.create(
                model=model, max_tokens=max_tokens, system=system,
                messages=[{"role": "user", "content": user}],
            )
            return msg.content[0].text.strip()
        return _anthropic_chat
    elif backend == "minimax-direct":
        import json
        from pathlib import Path
        from anthropic import Anthropic
        creds_path = Path("/mnt/a/loqu8/credentials.json")
        with open(creds_path) as f:
            creds = json.load(f)
        client = Anthropic(
            api_key=creds["minimax_api"]["api_key"],
            base_url="https://api.minimax.io/anthropic",
        )
        model = os.environ.get("MINIMAX_MODEL", "MiniMax-M2.5")
        def _minimax_direct_chat(system: str, user: str, max_tokens: int = 2048) -> str:
            parts = []
            with client.messages.stream(
                model=model, max_tokens=max_tokens, system=system,
                messages=[{"role": "user", "content": user}],
            ) as stream:
                for text in stream.text_stream:
                    parts.append(text)
            return "".join(parts).strip()
        return _minimax_direct_chat
    else:
        from tools.dictmaster.translate.minimax_api import _chat
        return _chat


# Module-level chat function, set by main() based on --backend flag
_chat_fn = None


def translate_one(
    conn: sqlite3.Connection,
    headword_id: int,
    traditional: str,
    simplified: str,
    pinyin: str,
    pos: str | None,
) -> dict[str, str]:
    """Translate a single headword into all 26 languages. Returns {lang: def}."""
    global _chat_fn
    if _chat_fn is None:
        from tools.dictmaster.translate.minimax_api import _chat
        _chat_fn = _chat

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

    # Detect narrow-scope entries that need extra guardrails
    scope_warning = ""
    en_community = community.get("en", "")
    is_proper = pinyin and pinyin[0].isupper()
    is_narrow = any(kw in en_community.lower() for kw in [
        "surname", "only used in", "variant of", "abbr. for",
        "abbr. for", "old variant", "used in place name",
    ])
    if is_proper and is_narrow:
        scope_warning = (
            f"\n⚠️ SCOPE WARNING: Capitalized pinyin \"{pinyin}\" = PROPER NOUN reading.\n"
            f"The reference says: \"{en_community.split('(')[0].strip()}\"\n"
            f"Output ONLY this narrow meaning. Do NOT add the general meaning of {simplified}.\n"
        )
    elif is_narrow:
        scope_warning = (
            f"\n⚠️ SCOPE WARNING: This is a NARROW entry.\n"
            f"The reference says: \"{en_community.split('(')[0].strip()}\"\n"
            f"Output ONLY this specific meaning. Do NOT substitute common meanings.\n"
        )
    elif is_proper:
        scope_warning = (
            f"\n⚠️ SCOPE WARNING: Capitalized pinyin \"{pinyin}\" = PROPER NOUN reading.\n"
            f"This entry is a surname, place name, or abbreviation. Translate ONLY as such.\n"
        )

    prompt = TEMPLATE_V2.format(
        traditional=traditional,
        simplified=simplified,
        pinyin=pinyin or "",
        pos=pos or "unknown",
        scope_warning=scope_warning,
        context_definitions="\n".join(ctx_lines) if ctx_lines else "  (none)",
        examples="\n".join(ex_lines),
        lang_lines=lang_lines,
    )

    response = _chat_fn(SYSTEM_V2, prompt, max_tokens=2048)
    return parse_universal_response(response)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def _translate_worker(entry: dict) -> tuple[dict, dict[str, str] | None, str | None]:
    """Thread worker: calls API, returns (entry, result, error)."""
    try:
        # Each worker gets its own read-only DB connection for community defs
        conn = sqlite3.connect(str(DEFAULT_DB_PATH))
        conn.row_factory = sqlite3.Row
        result = translate_one(
            conn, entry["id"], entry["traditional"], entry["simplified"],
            entry["pinyin"], entry["pos"],
        )
        conn.close()
        return entry, result, None
    except Exception as e:
        return entry, None, str(e)


def run(
    db_path: Path,
    bad_only: bool = False,
    min_freq: int | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    workers: int = 1,
    include_multi: bool = False,
    reverse: bool = False,
    delay: float = 0.0,
    ids_file: str | None = None,
    force: bool = False,
) -> None:
    from tools.dictmaster.translate.minimax_api import _chat  # noqa: F401 — warm import

    conn = get_connection(db_path)
    ensure_source(conn, "minimax")

    # Build headword list
    if ids_file:
        with open(ids_file) as f:
            target_ids = json.load(f)
        placeholders = ",".join("?" * len(target_ids))
        rows = conn.execute(
            f"SELECT id, traditional, simplified, pinyin, pos, sfreq "
            f"FROM headwords WHERE id IN ({placeholders}) ORDER BY sfreq DESC NULLS LAST",
            target_ids,
        ).fetchall()
    elif bad_only:
        ids_path = Path("data/artifacts/bad_single_char_ids.json")
        if not ids_path.exists():
            print(f"ERROR: {ids_path} not found. Run the detection query first.")
            return
        with open(ids_path) as f:
            bad_ids = json.load(f)
        placeholders = ",".join("?" * len(bad_ids))
        rows = conn.execute(
            f"SELECT id, traditional, simplified, pinyin, pos, sfreq "
            f"FROM headwords WHERE id IN ({placeholders}) ORDER BY sfreq DESC NULLS LAST",
            bad_ids,
        ).fetchall()
    else:
        # Skip wiktextract variant entries with ")5" pinyin — they're excluded
        # from export (build_dbs.py) and have wrong simp/trad mappings.
        if include_multi:
            where = "pinyin NOT LIKE '%)5'"
        else:
            where = "length(simplified) = 1 AND pinyin NOT LIKE '%)5'"
        params: list = []
        if min_freq is not None:
            where += " AND sfreq >= ?"
            params.append(min_freq)
        order = "ASC NULLS FIRST" if reverse else "DESC NULLS LAST"
        rows = conn.execute(
            f"SELECT id, traditional, simplified, pinyin, pos, sfreq "
            f"FROM headwords WHERE {where} ORDER BY sfreq {order}",
            params,
        ).fetchall()

    if limit:
        rows = rows[:limit]

    # Skip entries already having v2 defs (unless --force)
    todo = []
    for r in rows:
        if force:
            todo.append(dict(r))
        else:
            has_v2 = conn.execute(
                "SELECT 1 FROM definitions WHERE headword_id = ? AND source = 'minimax' AND confidence = ?",
                (r["id"], CONFIDENCE_TAG),
            ).fetchone()
            if not has_v2:
                todo.append(dict(r))

    print(f"Retranslate: {len(todo)} entries to process ({len(rows) - len(todo)} already have v2)")
    if dry_run:
        for r in todo[:20]:
            freq = f"freq={r['sfreq']:,}" if r["sfreq"] else "no freq"
            print(f"  {r['simplified']} ({r['pinyin']}) [{freq}]")
        if len(todo) > 20:
            print(f"  ... and {len(todo) - 20} more")
        print("\n[DRY RUN] Exiting.")
        return

    print(f"  Workers: {workers}", flush=True)
    t_start = time.time()
    processed = 0
    saved = 0
    rejected = 0
    rate_limits = 0
    other_errors = 0

    def _save_result(entry: dict, result: dict[str, str]):
        nonlocal saved, rejected
        entry_saved = 0
        for lang, defn in result.items():
            if not defn:
                continue
            ok, bad_scripts = validate_definition(lang, defn)
            if not ok:
                rejected += 1
                continue
            upsert_definition(
                conn, entry["id"], lang, defn, "minimax",
                confidence=CONFIDENCE_TAG,
                prompt_version=PROMPT_VERSION,
            )
            entry_saved += 1
        if entry_saved > 0:
            saved += 1

    def _log_progress():
        elapsed = time.time() - t_start
        rate = processed / elapsed if elapsed > 0 else 0
        remaining = len(todo) - processed
        eta = remaining / rate if rate > 0 else 0
        rej_str = f", {rejected} rejected" if rejected else ""
        err_str = f", {rate_limits} rate-limited, {other_errors} errors" if (rate_limits or other_errors) else ""
        print(
            f"  [{processed}/{len(todo)}] {saved} saved{rej_str}{err_str} "
            f"({rate:.1f}/s, ETA {eta/60:.1f}m)",
            flush=True,
        )

    if workers <= 1:
        for entry in todo:
            if delay > 0:
                time.sleep(delay)
            try:
                result = translate_one(
                    conn, entry["id"], entry["traditional"], entry["simplified"],
                    entry["pinyin"], entry["pos"],
                )
            except Exception as e:
                if "429" in str(e) or "rate_limit" in str(e):
                    rate_limits += 1
                else:
                    other_errors += 1
                print(f"  ERROR {entry['simplified']} ({entry['pinyin']}): {e}")
                processed += 1
                continue
            _save_result(entry, result)
            conn.commit()
            processed += 1
            if processed % 10 == 0 or processed == len(todo):
                _log_progress()
    else:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit initial batch
            pending: dict = {}
            idx = 0

            def _submit_batch():
                nonlocal idx
                while len(pending) < workers * 2 and idx < len(todo):
                    fut = executor.submit(_translate_worker, todo[idx])
                    pending[fut] = todo[idx]
                    idx += 1

            _submit_batch()

            while pending:
                for fut in as_completed(pending):
                    entry = pending.pop(fut)
                    try:
                        _, result, error = fut.result()
                        if error:
                            if "429" in str(error) or "rate_limit" in str(error):
                                rate_limits += 1
                            else:
                                other_errors += 1
                            print(f"  ERROR {entry['simplified']} ({entry['pinyin']}): {error}", flush=True)
                        elif result:
                            _save_result(entry, result)
                    except Exception as e:
                        if "429" in str(e) or "rate_limit" in str(e):
                            rate_limits += 1
                        else:
                            other_errors += 1
                        print(f"  ERROR {entry['simplified']} ({entry['pinyin']}): {e}", flush=True)

                    processed += 1
                    if processed % 10 == 0:
                        conn.commit()
                        _log_progress()

                    _submit_batch()
                    break  # process one future at a time for ordered DB writes

        conn.commit()

    elapsed = time.time() - t_start
    _log_progress()
    print(f"\nDone: {processed} processed, {saved} saved, {rejected} rejected, "
          f"{rate_limits} rate-limited, {other_errors} other errors in {elapsed/60:.1f}m")


def main():
    parser = argparse.ArgumentParser(description="Re-translate single-char headwords")
    parser.add_argument("--bad-only", action="store_true",
                        help="Only fix the ~382 known-bad entries")
    parser.add_argument("--min-freq", type=int, default=None,
                        help="Only process entries with sfreq >= this value")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max entries to process")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without calling API")
    parser.add_argument("--workers", type=int, default=1,
                        help="Parallel API workers (default 1)")
    parser.add_argument("--backend", type=str, default="minimax",
                        choices=["minimax", "cerebras", "minimax-direct", "anthropic"],
                        help="Translation backend (default: minimax)")
    parser.add_argument("--include-multi", action="store_true",
                        help="Include multi-char entries (not just single-char)")
    parser.add_argument("--reverse", action="store_true",
                        help="Process low-frequency entries first (ascending order)")
    parser.add_argument("--force", action="store_true",
                        help="Re-process entries even if they already have v2 defs")
    parser.add_argument("--delay", type=float, default=0.0,
                        help="Delay between requests in seconds (e.g. 0.5)")
    parser.add_argument("--ids-file", type=str, default=None,
                        help="JSON file with list of headword IDs to process")
    parser.add_argument("--db", type=str, default=str(DEFAULT_DB_PATH),
                        help="Path to dictmaster.db")
    args = parser.parse_args()

    # Set up the chat backend
    global _chat_fn
    _chat_fn = _get_chat_fn(args.backend)
    print(f"Backend: {args.backend}", flush=True)

    run(
        db_path=Path(args.db),
        bad_only=args.bad_only,
        min_freq=args.min_freq,
        limit=args.limit,
        dry_run=args.dry_run,
        workers=args.workers,
        include_multi=args.include_multi,
        reverse=args.reverse,
        delay=args.delay,
        ids_file=args.ids_file,
        force=args.force,
    )


if __name__ == "__main__":
    main()
