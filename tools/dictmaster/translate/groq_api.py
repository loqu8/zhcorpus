"""Groq API translation backend using Kimi K2 Instruct.

Uses Groq's free tier with rate limiting (30 req/min, 131K tokens/min).
"""

import json
import re
import threading
import time
from pathlib import Path
from typing import Optional

from tools.dictmaster.translate.prompts import (
    UNIVERSAL_SYSTEM_PROMPT,
    build_universal_batch_prompt,
    parse_universal_batch_response,
    parse_universal_response,
    build_universal_prompt,
)

# Rate limiter: Groq free tier = 10K tokens/min for Kimi K2.
# Each batch uses ~5,100 tokens, so max ~1.9 batches/min.
# We allow 1 batch every 35s to stay safely under the limit.
_rate_lock = threading.Lock()
_last_request_time: float = 0.0
_MIN_INTERVAL_SECONDS = 35.0  # ~1.7 req/min = ~8,700 tokens/min (under 10K)
_CJK_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]')


def _load_api_key() -> str:
    """Load Groq API key from model-radar config or environment."""
    import os

    # Try environment first
    key = os.environ.get("GROQ_API_KEY", "")
    if key:
        return key

    # Try model-radar config
    config_path = Path.home() / ".model-radar" / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        key = config.get("api_keys", {}).get("groq", "")
        if key:
            return key

    # Try groq settings file
    groq_settings = Path.home() / ".claude" / "settings.groq.json"
    if groq_settings.exists():
        with open(groq_settings) as f:
            config = json.load(f)
        key = config.get("env", {}).get("GROQ_API_KEY", "")
        if key:
            return key

    raise FileNotFoundError(
        "Groq API key not found. Set GROQ_API_KEY env var or configure in "
        "~/.model-radar/config.json"
    )


def _get_client():
    """Create a Groq client."""
    from groq import Groq

    return Groq(api_key=_load_api_key())


def _rate_limit():
    """Block until enough time has passed since last request. Thread-safe."""
    global _last_request_time
    with _rate_lock:
        now = time.time()
        elapsed = now - _last_request_time
        if elapsed < _MIN_INTERVAL_SECONDS:
            wait = _MIN_INTERVAL_SECONDS - elapsed
            time.sleep(wait)
        _last_request_time = time.time()


def _strip_cjk_from_context(context_defs: dict[str, str]) -> dict[str, str]:
    """Remove CJK characters from context definitions to prevent leaking.

    Turns "variant of 逼格[bi1 ge2]" into "variant of [bi1 ge2]".
    """
    cleaned = {}
    for lang, defn in context_defs.items():
        cleaned[lang] = _CJK_RE.sub("", defn).strip()
        # Clean up double spaces left by removal
        cleaned[lang] = re.sub(r"  +", " ", cleaned[lang])
    return cleaned


def _chat(system: str, user: str, max_tokens: int = 8192) -> str:
    """Send a chat request to Groq and return the response text.

    Retries up to 3 times on rate limit (429) errors with backoff.
    """
    max_retries = 3
    for attempt in range(max_retries + 1):
        _rate_limit()
        try:
            client = _get_client()
            response = client.chat.completions.create(
                model="moonshotai/kimi-k2-instruct",
                max_tokens=max_tokens,
                temperature=0,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if "429" in str(e) and attempt < max_retries:
                # Rate limited — wait and retry
                wait = 10 * (attempt + 1)
                time.sleep(wait)
                continue
            raise


def translate_universal(
    traditional: str,
    simplified: str,
    pinyin: str,
    pos: Optional[str],
    context_defs: dict[str, str],
    examples: list[str] | None = None,
    target_langs: list[str] | None = None,
) -> dict[str, str]:
    """Translate a single entry into all target languages in one call."""
    clean_ctx = _strip_cjk_from_context(context_defs)
    prompt = build_universal_prompt(
        traditional, simplified, pinyin, pos or "", clean_ctx,
        examples=examples, target_langs=target_langs,
    )
    response = _chat(UNIVERSAL_SYSTEM_PROMPT, prompt, max_tokens=2048)
    return parse_universal_response(response, target_langs)


def translate_universal_batch(
    entries: list[dict],
    target_langs: list[str] | None = None,
) -> list[dict[str, str]]:
    """Translate a batch of entries into all target languages in one call."""
    # Strip CJK from context defs to prevent cross-reference leaks
    cleaned_entries = []
    for e in entries:
        ce = dict(e)
        ce["context_defs"] = _strip_cjk_from_context(e.get("context_defs", {}))
        cleaned_entries.append(ce)

    prompt = build_universal_batch_prompt(cleaned_entries, target_langs)
    response = _chat(UNIVERSAL_SYSTEM_PROMPT, prompt, max_tokens=8192)
    return parse_universal_batch_response(response, len(entries), target_langs)
