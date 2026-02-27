"""MiniMax M2.5 translation via direct API (Anthropic-compatible endpoint)."""

import json
from pathlib import Path
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

# Config file path
CONFIG_PATH = Path.home() / ".claude" / "settings.minimax.json"


def _load_config() -> dict:
    """Load MiniMax API config from settings file."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"MiniMax config not found at {CONFIG_PATH}. "
            "Create it with env.ANTHROPIC_BASE_URL, env.ANTHROPIC_AUTH_TOKEN, env.ANTHROPIC_MODEL"
        )
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    env = config.get("env", {})
    return {
        "base_url": env.get("ANTHROPIC_BASE_URL", "https://api.minimax.io/anthropic"),
        "api_key": env.get("ANTHROPIC_AUTH_TOKEN", ""),
        "model": env.get("ANTHROPIC_MODEL", "MiniMax-M2.5"),
    }


def _get_client():
    """Create an Anthropic client configured for MiniMax."""
    from anthropic import Anthropic

    config = _load_config()
    return Anthropic(
        api_key=config["api_key"],
        base_url=config["base_url"],
    ), config["model"]


def _chat(system: str, user: str, max_tokens: int = 1024) -> str:
    """Send a chat request to MiniMax API and return the response text."""
    client, model = _get_client()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    # Skip ThinkingBlock / other non-text blocks, find first TextBlock
    for block in response.content:
        if hasattr(block, "text"):
            return block.text.strip()
    return ""


def translate_entry(
    traditional: str,
    simplified: str,
    pinyin: str,
    pos: Optional[str],
    target_lang: str,
    context_defs: dict[str, str],
) -> str:
    """Translate a single dictionary entry via MiniMax API.

    Returns slash-separated definition in target language.
    """
    prompt = build_translate_prompt(
        traditional, simplified, pinyin, pos or "", target_lang, context_defs
    )
    response = _chat(SYSTEM_PROMPT, prompt)
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
    """Verify and potentially improve an existing definition via MiniMax API.

    Returns the (possibly improved) slash-separated definition.
    """
    prompt = build_verify_prompt(
        traditional, simplified, pinyin, pos or "", target_lang,
        current_definition, context_defs,
    )
    response = _chat(SYSTEM_PROMPT, prompt)
    return _clean_response(response)


def translate_batch(
    entries: list[dict],
    target_lang: str,
) -> list[str]:
    """Translate a batch of entries via MiniMax API.

    Each entry dict has: traditional, simplified, pinyin, pos, context_defs
    Returns list of slash-separated definitions (same order as input).
    """
    prompt = build_batch_prompt(entries, target_lang)
    response = _chat(SYSTEM_PROMPT, prompt)

    lines = response.strip().split("\n")
    results = []
    for line in lines:
        cleaned = _clean_response(line)
        if cleaned:
            results.append(cleaned)

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
    response = _chat(UNIVERSAL_SYSTEM_PROMPT, prompt, max_tokens=2048)
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
    # 20 entries × 11 langs × ~40 chars/def ≈ 8800 chars ≈ 3K tokens
    response = _chat(UNIVERSAL_SYSTEM_PROMPT, prompt, max_tokens=8192)
    return parse_universal_batch_response(response, len(entries), target_langs)


def _clean_response(text: str) -> str:
    """Clean LLM response to extract just the slash-separated glosses."""
    text = text.strip()
    if text and text[0].isdigit():
        parts = text.split(".", 1)
        if len(parts) == 2 and parts[0].strip().isdigit():
            text = parts[1].strip()
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    if text.startswith("/"):
        text = text[1:]
    if text.endswith("/"):
        text = text[:-1]
    return text.strip()
