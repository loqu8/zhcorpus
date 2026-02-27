"""MiniMax M2.5 translation via Ollama (minimax-m2.5:cloud)."""

import sqlite3
from typing import Optional

from tools.dictmaster.translate.prompts import (
    SYSTEM_PROMPT,
    UNIVERSAL_SYSTEM_PROMPT,
    build_batch_prompt,
    build_translate_prompt,
    build_universal_batch_prompt,
    build_universal_prompt,
    build_verify_prompt,
    parse_universal_batch_response,
    parse_universal_response,
)

# Model name for Ollama
MODEL = "minimax-m2.5:cloud"


def _chat(messages: list[dict], model: str = MODEL) -> str:
    """Send a chat request to Ollama and return the response text."""
    import ollama

    response = ollama.chat(model=model, messages=messages)
    return response["message"]["content"].strip()


def translate_entry(
    traditional: str,
    simplified: str,
    pinyin: str,
    pos: Optional[str],
    target_lang: str,
    context_defs: dict[str, str],
) -> str:
    """Translate a single dictionary entry via Ollama.

    Returns slash-separated definition in target language.
    """
    prompt = build_translate_prompt(
        traditional, simplified, pinyin, pos or "", target_lang, context_defs
    )
    response = _chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ])
    return _clean_response(response)


def verify_entry(
    traditional: str,
    simplified: str,
    pinyin: str,
    pos: Optional[str],
    target_lang: str,
    current_definition: str,
    context_defs: dict[str, str],
) -> str:
    """Verify and potentially improve an existing definition via Ollama.

    Returns the (possibly improved) slash-separated definition.
    """
    prompt = build_verify_prompt(
        traditional, simplified, pinyin, pos or "", target_lang,
        current_definition, context_defs,
    )
    response = _chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ])
    return _clean_response(response)


def translate_batch(
    entries: list[dict],
    target_lang: str,
) -> list[str]:
    """Translate a batch of entries via Ollama.

    Each entry dict has: traditional, simplified, pinyin, pos, context_defs
    Returns list of slash-separated definitions (same order as input).
    """
    prompt = build_batch_prompt(entries, target_lang)
    response = _chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ])

    # Parse numbered lines from response
    lines = response.strip().split("\n")
    results = []
    for line in lines:
        cleaned = _clean_response(line)
        if cleaned:
            results.append(cleaned)

    # Pad with empty strings if response is shorter than input
    while len(results) < len(entries):
        results.append("")

    return results[:len(entries)]


def translate_universal(
    traditional: str,
    simplified: str,
    pinyin: str,
    pos: Optional[str],
    context_defs: dict[str, str],
    examples: list[str] | None = None,
    target_langs: list[str] | None = None,
) -> dict[str, str]:
    """Translate a single entry into all target languages in one call.

    Returns dict of {lang_code: definition}.
    """
    prompt = build_universal_prompt(
        traditional, simplified, pinyin, pos or "", context_defs,
        examples=examples, target_langs=target_langs,
    )
    response = _chat([
        {"role": "system", "content": UNIVERSAL_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ])
    return parse_universal_response(response, target_langs)


def translate_universal_batch(
    entries: list[dict],
    target_langs: list[str] | None = None,
) -> list[dict[str, str]]:
    """Translate a batch of entries into all target languages in one call.

    Each entry dict has: traditional, simplified, pinyin, pos, context_defs,
    and optionally 'examples' (list of strings).
    Returns list of {lang_code: definition} dicts (same order as input).
    """
    prompt = build_universal_batch_prompt(entries, target_langs)
    response = _chat([
        {"role": "system", "content": UNIVERSAL_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ])
    return parse_universal_batch_response(response, len(entries), target_langs)


def _clean_response(text: str) -> str:
    """Clean LLM response to extract just the slash-separated glosses."""
    text = text.strip()
    # Remove leading number + period (from batch responses)
    if text and text[0].isdigit():
        parts = text.split(".", 1)
        if len(parts) == 2 and parts[0].strip().isdigit():
            text = parts[1].strip()
    # Remove surrounding quotes
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    # Remove leading/trailing slashes
    if text.startswith("/"):
        text = text[1:]
    if text.endswith("/"):
        text = text[:-1]
    return text.strip()
