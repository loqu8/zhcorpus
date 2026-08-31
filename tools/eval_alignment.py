#!/usr/bin/env python3
"""Alignment evaluation: can local models produce iCE-style {t, a} JSON?

Issues the *exact* iCE production prompt (from loqu8/telemetry/src/index.js,
post-fix) to each candidate system and captures raw output. Scoring is done
separately by tools/score_alignment.py.

Phase 1: zh -> en, 10-sentence pilot, 6 systems.

Usage:
    .venv/bin/python tools/eval_alignment.py --test-set pilot --system all
    .venv/bin/python tools/eval_alignment.py --test-set pilot --system cerebras
    .venv/bin/python tools/eval_alignment.py --test-set pilot --system qwen2.5:3b-instruct
"""

import argparse
import asyncio
import json
import os
import time
from pathlib import Path

import httpx

PILOT = Path("data/alignment_eval/pilot.jsonl")
RESULTS_DIR = Path("data/alignment_eval/results")
OLLAMA_URL = "http://localhost:11434"
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"

# --- iCE production prompt (matches telemetry/src/index.js translateCerebras) -

def make_ice_prompt(text: str, target_lang: str = "en") -> tuple[str, str]:
    target_name = {
        "en": "English", "de": "German", "fr": "French", "es": "Spanish",
        "ja": "Japanese", "ko": "Korean",
    }.get(target_lang, target_lang)
    source_name = "Chinese"
    system = (
        f"Translate {source_name} to {target_name}. Return compact JSON:\n"
        f'{{"t":"translation","a":[["s:源词","t:{target_name}1"],'
        f'["s:源词2","t:{target_name}2"],...]}}\n'
        f'The "a" array maps each {source_name} word/phrase to its '
        f"{target_name} equivalent in reading order. Group compound words "
        f"naturally. Include function words like 之/的/了 with empty target "
        f"if no {target_name} equivalent."
    )
    user = (
        f"Translate to {target_name}: {text}\n"
        "Return ONLY this JSON format, no other text:\n"
        '{"t":"<translation>","a":[["s:源","t:target"],...]}'
    )
    return system, user


# --- Backends ----------------------------------------------------------------

async def call_ollama(
    client: httpx.AsyncClient, model: str, text: str, target_lang: str
) -> dict:
    system, user = make_ice_prompt(text, target_lang)
    t0 = time.time()
    try:
        r = await client.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
                # Disable "thinking" output so reasoning-models (Qwen3.5, gpt-oss)
                # emit JSON directly. num_predict bumped to 1024 to give room.
                "think": False,
                "options": {"temperature": 0.0, "num_predict": 1024},
            },
            timeout=300,
        )
        r.raise_for_status()
        data = r.json()
        msg = data.get("message", {}) or {}
        content = (msg.get("content") or "").strip()
        # Safety net: if a thinking model still emits to `thinking` despite
        # think=False, capture that so we don't unfairly mark it a parse fail.
        if not content:
            content = (msg.get("thinking") or "").strip()
        return {
            "raw": content,
            "elapsed_s": round(time.time() - t0, 3),
            "error": None,
        }
    except Exception as e:
        return {"raw": "", "elapsed_s": round(time.time() - t0, 3), "error": str(e)}


def _get_cerebras_key() -> str:
    key = os.environ.get("CEREBRAS_API_KEY", "")
    if key:
        return key
    cfg = Path.home() / ".model-radar" / "config.json"
    if cfg.exists():
        return json.loads(cfg.read_text()).get("api_keys", {}).get("cerebras", "")
    return ""


async def call_cerebras(
    client: httpx.AsyncClient, text: str, target_lang: str,
    model: str = "qwen-3-235b-a22b-instruct-2507",
) -> dict:
    system, user = make_ice_prompt(text, target_lang)
    key = _get_cerebras_key()
    if not key:
        return {"raw": "", "elapsed_s": 0.0, "error": "no CEREBRAS_API_KEY"}
    t0 = time.time()
    backoff = 1.0
    last_err = ""
    for attempt in range(5):
        try:
            r = await client.post(
                CEREBRAS_URL,
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.0,
                    "max_completion_tokens": 512,
                },
                timeout=60,
            )
            if r.status_code == 429:
                retry_after = float(r.headers.get("retry-after", backoff))
                await asyncio.sleep(min(retry_after, 30.0))
                backoff = min(backoff * 2, 30.0)
                last_err = f"429 (attempt {attempt + 1})"
                continue
            r.raise_for_status()
            data = r.json()
            return {
                "raw": data["choices"][0]["message"]["content"].strip(),
                "elapsed_s": round(time.time() - t0, 3),
                "error": None,
            }
        except Exception as e:
            last_err = str(e)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30.0)
    return {"raw": "", "elapsed_s": round(time.time() - t0, 3),
            "error": f"{last_err} (gave up)"}


# --- System registry ---------------------------------------------------------

SYSTEMS = {
    # tag                  backend     model
    "hy-mt-1.8b":          ("ollama",   "hy-mt-1.8b:latest"),
    "hy-mt-7b":            ("ollama",   "hy-mt-7b:latest"),
    "qwen2.5:3b-instruct": ("ollama",   "qwen2.5:3b-instruct"),
    "qwen3.5:9b":          ("ollama",   "qwen3.5:9b"),
    "gpt-oss:20b":         ("ollama",   "gpt-oss:20b"),
    "cerebras":            ("cerebras", "qwen-3-235b-a22b-instruct-2507"),
}

# Concurrency: ollama runs one model at a time on the GPU, so keep =1.
CONCURRENCY = {
    "ollama":   1,
    "cerebras": 4,   # dev-tier 1K RPM, no throttle needed at this scale
}


async def run_system(system_tag: str, items: list[dict], target_lang: str) -> Path:
    backend, model = SYSTEMS[system_tag]
    safe_tag = system_tag.replace(":", "_").replace("/", "_")
    out_path = RESULTS_DIR / f"pilot_{safe_tag}_{target_lang}.jsonl"
    sem = asyncio.Semaphore(CONCURRENCY[backend])
    results: list[dict] = []

    async with httpx.AsyncClient() as client:
        async def one(it: dict):
            async with sem:
                if backend == "ollama":
                    res = await call_ollama(client, model, it["text"], target_lang)
                else:
                    res = await call_cerebras(client, it["text"], target_lang, model)
                row = {
                    "id": it["id"],
                    "source": it.get("source", ""),
                    "text": it["text"],
                    "char_count": it.get("char_count", len(it["text"])),
                    "system": system_tag,
                    "target_lang": target_lang,
                    **res,
                }
                print(f"  [{system_tag}/{target_lang}] {it['id']:<25} "
                      f"{res['elapsed_s']:>6.2f}s  "
                      f"err={res['error'] or '-'}  "
                      f"raw={res['raw'][:60].replace(chr(10), ' ')!r}")
                return row

        results = await asyncio.gather(*(one(it) for it in items))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for row in results:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {out_path} ({len(results)} rows)")
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-set", default="pilot",
                    help="pilot (default, 10-sentence) or full (100)")
    ap.add_argument("--system", default="all",
                    help="comma-separated system tags, or 'all'")
    ap.add_argument("--target-lang", default="en")
    args = ap.parse_args()

    test_path = PILOT if args.test_set == "pilot" else Path(
        f"data/alignment_eval/{args.test_set}.jsonl")
    items = [json.loads(l) for l in test_path.open()]

    if args.system == "all":
        systems = list(SYSTEMS.keys())
    else:
        systems = [s.strip() for s in args.system.split(",")]
    for s in systems:
        if s not in SYSTEMS:
            raise SystemExit(f"unknown system {s}; available: {list(SYSTEMS)}")

    print(f"Test set: {test_path.name} ({len(items)} items)")
    print(f"Systems:  {systems}")
    print(f"Target:   {args.target_lang}")
    print()

    for tag in systems:
        print(f"\n=== {tag} ===")
        asyncio.run(run_system(tag, items, args.target_lang))


if __name__ == "__main__":
    main()
