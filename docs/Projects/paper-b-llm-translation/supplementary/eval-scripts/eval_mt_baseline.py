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
import re
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests

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

# Language codes for commercial MT APIs
AZURE_LANG_CODES = {"de": "de", "fr": "fr", "id": "id"}
GOOGLE_LANG_CODES = {"de": "de", "fr": "fr", "id": "id"}
DEEPL_LANG_CODES = {"de": "DE", "fr": "FR", "id": "ID"}

MT_SYSTEM_PROMPT = """\
You are a translator. Translate the following English text into {lang_name}.
Output ONLY the translation, nothing else. Keep the same format (slash-separated
alternatives if the input has them). Be concise — dictionary style."""

MT_USER_TEMPLATE = "Translate to {lang_name}: {text}"

# Config path for commercial MT keys (nomad-builder build artifacts)
_APPSETTINGS_PATHS = [
    Path.home() / "Projects/loqu8/nomad-builder/guix-build-0.8.0/"
    "distsrc-0.8.0-x86_64-w64-mingw32/servers/broker/src/Loqu8.Broker/"
    "bin/Debug/net9.0/appsettings.Development.json",
]

_mt_config_cache: dict | None = None


def _load_mt_config() -> dict:
    """Load commercial MT API keys from nomad-builder config."""
    global _mt_config_cache
    if _mt_config_cache is not None:
        return _mt_config_cache
    for p in _APPSETTINGS_PATHS:
        if p.exists():
            with open(p) as f:
                cfg = json.load(f)
            _mt_config_cache = cfg.get("Translation", {})
            return _mt_config_cache
    raise FileNotFoundError("No appsettings.Development.json found with MT keys")


# ---------------------------------------------------------------------------
# Format compliance metric
# ---------------------------------------------------------------------------

def is_gloss_format(text: str) -> bool:
    """Check if text is in CEDICT-style gloss format (short segments, slash-separated).

    Returns True if output matches gloss1/gloss2 pattern:
    - Each segment ≤ 5 words
    - No sentence-ending punctuation (. ! ?)
    - Output has ≤ 5 segments
    """
    if not text or not text.strip():
        return False
    text = text.strip()
    # Split on / and ;
    segments = re.split(r"[;/]", text)
    segments = [s.strip() for s in segments if s.strip()]
    if not segments or len(segments) > 5:
        return False
    for seg in segments:
        # No sentence-ending punctuation
        if re.search(r"[.!?。！？]$", seg):
            return False
        # Count words (for non-CJK languages)
        words = seg.split()
        if len(words) > 5:
            return False
    return True


# ---------------------------------------------------------------------------
# Translation backends
# ---------------------------------------------------------------------------

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


def translate_gloss_google(english_def: str, target_lang: str) -> str:
    """Translate via Google Cloud Translation API v2."""
    cfg = _load_mt_config().get("Google", {})
    api_key = cfg.get("ApiKey", "")
    if not api_key:
        raise ValueError("Google Translation API key not configured")

    url = f"{cfg.get('Endpoint', 'https://translation.googleapis.com')}/language/translate/v2"
    resp = requests.post(url, params={"key": api_key}, json={
        "q": english_def,
        "source": "en",
        "target": GOOGLE_LANG_CODES[target_lang],
        "format": "text",
    }, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data["data"]["translations"][0]["translatedText"]


def translate_gloss_deepl(english_def: str, target_lang: str) -> str:
    """Translate via DeepL API Free."""
    cfg = _load_mt_config().get("DeepL", {})
    auth_key = cfg.get("AuthKey", "")
    if not auth_key:
        raise ValueError("DeepL API key not configured")

    endpoint = cfg.get("Endpoint", "https://api-free.deepl.com")
    resp = requests.post(f"{endpoint}/v2/translate", headers={
        "Authorization": f"DeepL-Auth-Key {auth_key}",
        "Content-Type": "application/json",
    }, json={
        "text": [english_def],
        "source_lang": "EN",
        "target_lang": DEEPL_LANG_CODES[target_lang],
    }, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data["translations"][0]["text"]


_claude_client = None


def _get_claude_client():
    """Get or create Anthropic client, loading key from credentials.json."""
    global _claude_client
    if _claude_client is not None:
        return _claude_client

    import os
    from anthropic import Anthropic

    # Try env var first, then credentials file
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        creds_path = Path("/mnt/a/loqu8/credentials.json")
        if creds_path.exists():
            with open(creds_path) as f:
                creds = json.load(f)
            api_key = creds.get("anthropic_api", {}).get("api_key", "")
    if not api_key:
        raise ValueError("No Anthropic API key found (set ANTHROPIC_API_KEY or add to credentials.json)")

    _claude_client = Anthropic(api_key=api_key)
    return _claude_client


def translate_gloss_claude(english_def: str, target_lang: str) -> str:
    """Translate via Claude API (Anthropic) with generic translation prompt."""
    lang_name = MT_TARGETS[target_lang]["name"]
    system = MT_SYSTEM_PROMPT.format(lang_name=lang_name)
    user = MT_USER_TEMPLATE.format(lang_name=lang_name, text=english_def)

    client = _get_claude_client()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=256,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    for block in response.content:
        if hasattr(block, "text"):
            return block.text.strip()
    return ""


_openai_client = None


def _get_openai_client():
    """Get or create OpenAI client, loading key from credentials.json."""
    global _openai_client
    if _openai_client is not None:
        return _openai_client

    import os

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        creds_path = Path("/mnt/a/loqu8/credentials.json")
        if creds_path.exists():
            with open(creds_path) as f:
                creds = json.load(f)
            api_key = creds.get("openai_api", {}).get("api_key", "")
    if not api_key:
        raise ValueError("No OpenAI API key found")

    # Use requests directly (no openai SDK dependency)
    _openai_client = api_key
    return _openai_client


def translate_gloss_gpt4o(english_def: str, target_lang: str) -> str:
    """Translate via OpenAI GPT-4o with generic translation prompt."""
    lang_name = MT_TARGETS[target_lang]["name"]
    system = MT_SYSTEM_PROMPT.format(lang_name=lang_name)
    user = MT_USER_TEMPLATE.format(lang_name=lang_name, text=english_def)

    api_key = _get_openai_client()
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": 256,
            "temperature": 0.0,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def translate_gloss_azure(english_def: str, target_lang: str) -> str:
    """Translate via Azure Cognitive Services Translator."""
    cfg = _load_mt_config().get("Azure", {})
    sub_key = cfg.get("SubscriptionKey", "")
    if not sub_key:
        raise ValueError("Azure Translator subscription key not configured")

    endpoint = cfg.get("Endpoint", "https://api.cognitive.microsofttranslator.com")
    region = cfg.get("Region", "westus3")
    resp = requests.post(
        f"{endpoint}/translate",
        params={"api-version": "3.0", "from": "en", "to": AZURE_LANG_CODES[target_lang]},
        headers={
            "Ocp-Apim-Subscription-Key": sub_key,
            "Ocp-Apim-Subscription-Region": region,
            "Content-Type": "application/json",
        },
        json=[{"text": english_def}],
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return data[0]["translations"][0]["text"]


TRANSLATE_FN = {
    "minimax": translate_gloss_minimax,
    "google": translate_gloss_google,
    "deepl": translate_gloss_deepl,
    "azure": translate_gloss_azure,
    "claude": translate_gloss_claude,
    "gpt4o": translate_gloss_gpt4o,
}


def run_mt_baseline(db_path: str, backend: str = "minimax") -> dict:
    """Run the MT baseline evaluation."""
    if backend not in TRANSLATE_FN:
        raise ValueError(f"Unknown backend: {backend}. Choose from: {list(TRANSLATE_FN)}")

    translate_fn = TRANSLATE_FN[backend]
    conn = sqlite3.connect(db_path)

    # Use same sampling as main eval (same seed = same headwords)
    print(f"Running MT baseline with backend: {backend}", file=sys.stderr)
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
    results_by_lang = defaultdict(lambda: {
        "sense_coverage": [], "false_sense_rate": [], "format_compliance": [],
    })
    results_by_band = defaultdict(lambda: {
        "sense_coverage": [], "false_sense_rate": [], "format_compliance": [],
    })
    errors = 0

    t_start = time.time()
    for i, (band, hw_id, target_lang, english_def, community_def) in enumerate(eval_pairs):
        try:
            mt_def = translate_fn(english_def, target_lang)
        except Exception as e:
            print(f"    {backend} error: {e}", file=sys.stderr)
            errors += 1
            continue

        if not mt_def:
            continue

        # Format compliance check
        fmt_ok = is_gloss_format(mt_def)

        # Compare MT output against community dictionary
        mt_glosses = split_glosses(mt_def, target_lang)
        ref_glosses = split_glosses(community_def, target_lang)

        overlap = gloss_overlap(ref_glosses, mt_glosses, target_lang)

        results_by_lang[target_lang]["sense_coverage"].append(overlap["sense_coverage"])
        results_by_lang[target_lang]["false_sense_rate"].append(overlap["false_sense_rate"])
        results_by_lang[target_lang]["format_compliance"].append(1.0 if fmt_ok else 0.0)
        results_by_band[band]["sense_coverage"].append(overlap["sense_coverage"])
        results_by_band[band]["false_sense_rate"].append(overlap["false_sense_rate"])
        results_by_band[band]["format_compliance"].append(1.0 if fmt_ok else 0.0)

        if (i + 1) % 50 == 0:
            elapsed = time.time() - t_start
            print(f"  [{i + 1}/{len(eval_pairs)}] {elapsed:.1f}s ({errors} errors)", file=sys.stderr)

    conn.close()
    elapsed = time.time() - t_start
    print(f"\nDone in {elapsed:.1f}s ({errors} errors)", file=sys.stderr)

    # Aggregate
    summary = {"backend": backend, "by_language": {}, "by_band": {}, "overall": {}}
    all_coverage = []
    all_false = []
    all_format = []

    for lang in ["de", "fr", "id"]:
        data = results_by_lang[lang]
        if not data["sense_coverage"]:
            continue
        n = len(data["sense_coverage"])
        avg_cov = sum(data["sense_coverage"]) / n
        avg_false = sum(data["false_sense_rate"]) / n
        avg_fmt = sum(data["format_compliance"]) / n
        summary["by_language"][lang] = {
            "n": n,
            "sense_coverage": round(avg_cov, 3),
            "false_sense_rate": round(avg_false, 3),
            "format_compliance": round(avg_fmt, 3),
        }
        all_coverage.extend(data["sense_coverage"])
        all_false.extend(data["false_sense_rate"])
        all_format.extend(data["format_compliance"])

    for band in BANDS:
        data = results_by_band[band]
        if not data["sense_coverage"]:
            continue
        n = len(data["sense_coverage"])
        summary["by_band"][band] = {
            "n": n,
            "sense_coverage": round(sum(data["sense_coverage"]) / n, 3),
            "false_sense_rate": round(sum(data["false_sense_rate"]) / n, 3),
            "format_compliance": round(sum(data["format_compliance"]) / n, 3),
        }

    if all_coverage:
        summary["overall"] = {
            "n": len(all_coverage),
            "sense_coverage": round(sum(all_coverage) / len(all_coverage), 3),
            "false_sense_rate": round(sum(all_false) / len(all_false), 3),
            "format_compliance": round(sum(all_format) / len(all_format), 3),
            "errors": errors,
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
    parser.add_argument("--backend", default="minimax",
                        choices=["minimax", "google", "deepl", "azure", "claude", "gpt4o"],
                        help="MT backend")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--all", action="store_true",
                        help="Run all backends and output combined JSON")
    args = parser.parse_args()

    if args.all:
        results = {}
        for backend in ["minimax", "google", "deepl", "azure"]:
            try:
                results[backend] = run_mt_baseline(args.db, backend=backend)
            except Exception as e:
                print(f"Backend {backend} failed: {e}", file=sys.stderr)
                results[backend] = {"error": str(e)}
        print(json.dumps(results, indent=2, ensure_ascii=False))
    elif args.json:
        summary = run_mt_baseline(args.db, backend=args.backend)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        summary = run_mt_baseline(args.db, backend=args.backend)
        print_report(summary)


if __name__ == "__main__":
    main()
