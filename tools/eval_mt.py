#!/usr/bin/env python3
"""Scientific MT evaluation: HY-MT vs Cerebras vs Opus-MT vs cloud baselines.

Decision support for iCE Pro Forever bundling:
  - Bundle HY-MT1.5-1.8B (~1.1 GB) as default offline translator?
  - Sell HY-MT1.5-7B (~4.6 GB) as $49 addon?

Test sets:
  - FLORES-200 dev (997 zh sentences with high-quality references in 6 langs)
  - iCE-realism (100 zh sentences sampled from zhcorpus across news/baike/
    subtitles/classical/idioms; silver reference from Cerebras Qwen3-235B)

Systems:
  - hy-mt-1.8b   Ollama, hf.co/tencent/HY-MT1.5-1.8B-GGUF, local
  - hy-mt-7b     Ollama, hf.co/tencent/HY-MT1.5-7B-GGUF, local
  - cerebras     Cerebras qwen-3-235b-a22b-instruct-2507, cloud
  - opus-mt      HuggingFace Helsinki-NLP/opus-mt-zh-{lang}, local CPU

Output: data/mt_eval/results/<test_set>_<system>_<lang>.jsonl

Usage:
    # Small smoke test (5 sentences, one model, one target lang)
    .venv/bin/python tools/eval_mt.py --test-set flores --system hy-mt-1.8b \
        --target-langs en --limit 5

    # Full FLORES sweep (all systems x all langs)
    .venv/bin/python tools/eval_mt.py --test-set flores --all-systems
"""

import argparse
import asyncio
import json
import os
import time
from pathlib import Path

import httpx

# -----------------------------------------------------------------------------
# Test sets
# -----------------------------------------------------------------------------

FLORES_DIR = Path("data/mt_eval/flores200_dataset/dev")
ICE_REALISM = Path("data/mt_eval/ice_realism.jsonl")
RESULTS_DIR = Path("data/mt_eval/results")

# Target lang codes used by FLORES vs Opus-MT vs prompt
LANG_NAMES = {
    "en": "English",
    "de": "German",
    "fr": "French",
    "ja": "Japanese",
    "ko": "Korean",
    "es": "Spanish",
}
FLORES_LANG_CODES = {
    "en": "eng_Latn",
    "de": "deu_Latn",
    "fr": "fra_Latn",
    "ja": "jpn_Jpan",
    "ko": "kor_Hang",
    "es": "spa_Latn",
}


def load_flores(limit: int | None = None) -> list[dict]:
    """Load FLORES-200 dev: 997 zho_Hans sentences with refs in target langs."""
    src = (FLORES_DIR / "zho_Hans.dev").read_text(encoding="utf-8").splitlines()
    rows = [{"id": f"flores-{i}", "text": t} for i, t in enumerate(src)]
    if limit:
        rows = rows[:limit]
    return rows


def load_flores_refs(target_lang: str) -> list[str]:
    code = FLORES_LANG_CODES[target_lang]
    return (FLORES_DIR / f"{code}.dev").read_text(encoding="utf-8").splitlines()


def load_ice_realism(limit: int | None = None) -> list[dict]:
    rows = [json.loads(line) for line in ICE_REALISM.read_text(encoding="utf-8").splitlines()]
    if limit:
        rows = rows[:limit]
    return rows


# -----------------------------------------------------------------------------
# Prompts
# -----------------------------------------------------------------------------

def make_prompt(text: str, target_lang: str, style: str = "generic") -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for a translation request."""
    lang = LANG_NAMES[target_lang]
    if style == "hy-mt":
        # HY-MT models need a non-empty system prompt for stable termination
        # (7B in particular hallucinates extra turns without one).
        system = f"You are a professional Chinese-to-{lang} translator. Respond ONLY with the translation."
        user = f"Translate the following segment into {lang}, without additional explanation.\n\n{text}"
    else:
        system = (
            f"You are a professional Chinese-to-{lang} translator. "
            f"Translate the input into {lang}. Respond ONLY with the translation, "
            "no commentary, no quotes."
        )
        user = text
    return system, user


# -----------------------------------------------------------------------------
# Backends
# -----------------------------------------------------------------------------

OLLAMA_URL = "http://localhost:11434"
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"


async def translate_ollama(
    client: httpx.AsyncClient, text: str, target_lang: str, model: str,
) -> dict:
    system, user = make_prompt(text, target_lang, style="hy-mt")
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    t0 = time.time()
    try:
        r = await client.post(
            f"{OLLAMA_URL}/api/chat",
            json={"model": model, "messages": messages, "stream": False,
                  "options": {"temperature": 0.0, "num_predict": 256}},
            timeout=180,
        )
        r.raise_for_status()
        data = r.json()
        return {
            "translation": data["message"]["content"].strip(),
            "elapsed_s": round(time.time() - t0, 2),
            "error": None,
        }
    except Exception as e:
        return {"translation": "", "elapsed_s": round(time.time() - t0, 2), "error": str(e)}


def _get_cerebras_key() -> str:
    key = os.environ.get("CEREBRAS_API_KEY", "")
    if key:
        return key
    cfg = Path.home() / ".model-radar" / "config.json"
    if cfg.exists():
        return json.loads(cfg.read_text()).get("api_keys", {}).get("cerebras", "")
    return ""


async def translate_cerebras(
    client: httpx.AsyncClient, text: str, target_lang: str,
    model: str = "qwen-3-235b-a22b-instruct-2507",
    max_retries: int = 5,
) -> dict:
    """Cerebras with exponential backoff on 429."""
    system, user = make_prompt(text, target_lang, style="generic")
    key = _get_cerebras_key()
    if not key:
        return {"translation": "", "elapsed_s": 0.0, "error": "no CEREBRAS_API_KEY"}
    t0 = time.time()
    backoff = 1.0
    last_err = ""
    for attempt in range(max_retries):
        try:
            r = await client.post(
                CEREBRAS_URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.0,
                    "max_tokens": 256,
                },
                timeout=60,
            )
            if r.status_code == 429:
                # Honour Retry-After header if present
                retry_after = float(r.headers.get("retry-after", backoff))
                await asyncio.sleep(min(retry_after, 30.0))
                backoff = min(backoff * 2, 30.0)
                last_err = f"429 (attempt {attempt + 1})"
                continue
            r.raise_for_status()
            data = r.json()
            return {
                "translation": data["choices"][0]["message"]["content"].strip(),
                "elapsed_s": round(time.time() - t0, 2),
                "error": None,
            }
        except Exception as e:
            last_err = str(e)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30.0)
    return {"translation": "", "elapsed_s": round(time.time() - t0, 2),
            "error": f"{last_err} (gave up after {max_retries} retries)"}


# Lazy-loaded Opus-MT models (only loaded when --system opus-mt is selected)
_opus_models: dict = {}


def translate_opus_mt(text: str, target_lang: str) -> dict:
    """Synchronous CPU inference via transformers. Loads model on first call."""
    try:
        from transformers import MarianMTModel, MarianTokenizer
    except ImportError:
        return {"translation": "", "elapsed_s": 0.0,
                "error": "transformers not installed"}
    name = f"Helsinki-NLP/opus-mt-zh-{target_lang}"
    if name not in _opus_models:
        try:
            tok = MarianTokenizer.from_pretrained(name)
            model = MarianMTModel.from_pretrained(name)
            _opus_models[name] = (tok, model)
        except Exception as e:
            return {"translation": "", "elapsed_s": 0.0,
                    "error": f"load {name}: {e}"}
    tok, model = _opus_models[name]
    t0 = time.time()
    try:
        inputs = tok([text], return_tensors="pt", truncation=True, max_length=512)
        out = model.generate(**inputs, max_new_tokens=256, num_beams=4)
        translation = tok.decode(out[0], skip_special_tokens=True)
        return {"translation": translation.strip(),
                "elapsed_s": round(time.time() - t0, 2), "error": None}
    except Exception as e:
        return {"translation": "", "elapsed_s": round(time.time() - t0, 2),
                "error": str(e)}


# -----------------------------------------------------------------------------
# Runner
# -----------------------------------------------------------------------------

SYSTEMS = {
    "hy-mt-1.8b": {"backend": "ollama", "model": "hy-mt-1.8b:latest",
                    "concurrency": 2, "supports": ["en", "de", "fr", "ja", "ko", "es"]},
    "hy-mt-7b":   {"backend": "ollama", "model": "hy-mt-7b:latest",
                    "concurrency": 1, "supports": ["en", "de", "fr", "ja", "ko", "es"]},
    # concurrency=4 + no interval = ~10 RPS, safe under dev-tier 1K RPM / 1M TPM
    "cerebras":   {"backend": "cerebras", "model": "qwen-3-235b-a22b-instruct-2507",
                    "concurrency": 4, "min_interval_s": 0.0,
                    "supports": ["en", "de", "fr", "ja", "ko", "es"]},
    "opus-mt":    {"backend": "opus-mt", "model": "Helsinki-NLP/opus-mt-zh-*",
                    "concurrency": 1, "supports": ["en", "de", "fr"]},  # zh-ja/ko/es not all available
}


async def run_system(
    system: str, target_lang: str, rows: list[dict], output: Path,
) -> None:
    """Translate all rows with one system into one target lang, stream to JSONL."""
    cfg = SYSTEMS[system]
    if target_lang not in cfg["supports"]:
        print(f"[skip] {system} doesn't support zh->{target_lang}")
        return

    # Resume: skip already-done ids
    done_ids: set[str] = set()
    if output.exists():
        for line in output.read_text(encoding="utf-8").splitlines():
            try:
                done_ids.add(json.loads(line)["id"])
            except Exception:
                pass

    remaining = [r for r in rows if r["id"] not in done_ids]
    if not remaining:
        print(f"  [{system} zh->{target_lang}] all {len(rows)} already done")
        return

    print(f"  [{system} zh->{target_lang}] {len(remaining)} to translate "
          f"({len(done_ids)} resumed)")

    sem = asyncio.Semaphore(cfg["concurrency"])
    min_interval = cfg.get("min_interval_s", 0.0)
    last_call_t = [0.0]  # mutable cell shared across closures
    t_start = time.time()
    completed = 0

    if cfg["backend"] == "opus-mt":
        # Synchronous — no event loop benefit on CPU
        with open(output, "a", encoding="utf-8") as f:
            for row in remaining:
                res = translate_opus_mt(row["text"], target_lang)
                f.write(json.dumps({
                    "id": row["id"], "source": row.get("source"),
                    "src_text": row["text"], "target_lang": target_lang,
                    "system": system, **res,
                }, ensure_ascii=False) + "\n")
                f.flush()
                completed += 1
                if completed % 20 == 0:
                    elapsed = time.time() - t_start
                    print(f"    [{completed}/{len(remaining)}] {elapsed:.1f}s")
        elapsed = time.time() - t_start
        print(f"  done in {elapsed:.1f}s ({completed/elapsed:.2f}/s)")
        return

    async with httpx.AsyncClient() as client:
        async def one(row: dict) -> dict:
            nonlocal completed
            async with sem:
                # Throttle: ensure min_interval seconds since last call started
                if min_interval > 0:
                    delta = time.time() - last_call_t[0]
                    if delta < min_interval:
                        await asyncio.sleep(min_interval - delta)
                    last_call_t[0] = time.time()
                if cfg["backend"] == "ollama":
                    res = await translate_ollama(client, row["text"], target_lang, cfg["model"])
                elif cfg["backend"] == "cerebras":
                    res = await translate_cerebras(client, row["text"], target_lang, cfg["model"])
                else:
                    res = {"translation": "", "elapsed_s": 0.0, "error": "unknown backend"}
                completed += 1
                if completed % 20 == 0 or completed == 1:
                    elapsed = time.time() - t_start
                    rate = completed / elapsed if elapsed > 0 else 0
                    eta = (len(remaining) - completed) / rate if rate > 0 else 0
                    print(f"    [{completed}/{len(remaining)}] {elapsed:.1f}s "
                          f"({rate:.2f}/s, eta {eta:.0f}s)")
                return {
                    "id": row["id"], "source": row.get("source"),
                    "src_text": row["text"], "target_lang": target_lang,
                    "system": system, **res,
                }

        # Run all concurrently, write results as they finish
        with open(output, "a", encoding="utf-8") as f:
            for coro in asyncio.as_completed([one(r) for r in remaining]):
                result = await coro
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
                f.flush()

    elapsed = time.time() - t_start
    print(f"  done in {elapsed:.1f}s")


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--test-set", choices=["flores", "ice"], required=True)
    p.add_argument("--system", choices=list(SYSTEMS.keys()), default=None)
    p.add_argument("--all-systems", action="store_true")
    p.add_argument("--target-langs", default="en,de,fr,ja,ko,es")
    p.add_argument("--limit", type=int, default=0)
    args = p.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.test_set == "flores":
        rows = load_flores(args.limit or None)
    else:
        rows = load_ice_realism(args.limit or None)

    systems = list(SYSTEMS.keys()) if args.all_systems else [args.system]
    if not systems[0]:
        p.error("--system or --all-systems required")

    target_langs = [s.strip() for s in args.target_langs.split(",") if s.strip()]

    for sys_name in systems:
        for lang in target_langs:
            output = RESULTS_DIR / f"{args.test_set}_{sys_name}_{lang}.jsonl"
            asyncio.run(run_system(sys_name, lang, rows, output))


if __name__ == "__main__":
    main()
