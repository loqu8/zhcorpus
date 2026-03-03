"""Paper 5 Experiment Runner: Send prompts to LLM, collect responses.

Reads pre-generated prompts from paper5_eval.py, sends each condition's
prompt to an LLM via OpenAI-compatible API, and saves responses in the
format expected by paper5_metrics.py.

Supports:
  - Preconfigured provider profiles (minimax, groq, ollama)
  - Any OpenAI-compatible API via --base-url / --api-key
  - Async concurrency for throughput
  - Checkpointing / resume (skips completed entries)
  - Configurable model, temperature, max_tokens

Usage:
    # MiniMax M2.5 (recommended — proven, cheap, fast)
    .venv/bin/python tools/paper5_runner.py \
        --prompts data/paper5_eval_prompts.json \
        --provider minimax

    # Test run (5 headwords)
    .venv/bin/python tools/paper5_runner.py \
        --prompts data/paper5_eval_prompts.json \
        --output data/paper5_eval_responses_test.json \
        --provider minimax --limit 5

    # Custom provider
    .venv/bin/python tools/paper5_runner.py \
        --prompts data/paper5_eval_prompts.json \
        --base-url https://api.fireworks.ai/inference/v1 \
        --api-key $FIREWORKS_API_KEY \
        --model accounts/fireworks/models/llama-v3p3-70b-instruct

    # Resume after interruption (automatic — checks output file)
    .venv/bin/python tools/paper5_runner.py \
        --prompts data/paper5_eval_prompts.json \
        --provider minimax
"""

import asyncio
import json
import os
import time
from pathlib import Path

import click
from openai import AsyncOpenAI


# ---------------------------------------------------------------------------
# Provider profiles
# ---------------------------------------------------------------------------

PROVIDERS = {
    "minimax": {
        "base_url": "https://api.minimax.io/v1",
        "model": "MiniMax-M2.5",
        "api_key_source": "minimax_config",  # loaded from ~/.claude/settings.minimax.json
        "concurrency": 20,  # no rate limiting observed
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "api_key_source": "env:GROQ_API_KEY",
        "concurrency": 5,  # free tier is limited
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "model": "qwen3-coder:30b",
        "api_key_source": "literal:ollama",
        "concurrency": 1,
    },
}


def _load_minimax_key() -> str:
    """Load MiniMax API key from ~/.claude/settings.minimax.json."""
    config_path = Path.home() / ".claude" / "settings.minimax.json"
    if not config_path.exists():
        raise FileNotFoundError(f"MiniMax config not found at {config_path}")
    with open(config_path) as f:
        config = json.load(f)
    return config.get("env", {}).get("ANTHROPIC_AUTH_TOKEN", "")


def _resolve_api_key(source: str, cli_key: str | None) -> str:
    """Resolve API key from CLI arg, provider profile, or environment."""
    if cli_key:
        return cli_key
    if source == "minimax_config":
        return _load_minimax_key()
    if source.startswith("env:"):
        return os.environ.get(source[4:], "")
    if source.startswith("literal:"):
        return source[8:]
    return os.environ.get("OPENAI_API_KEY", "")


# ---------------------------------------------------------------------------
# LLM client
# ---------------------------------------------------------------------------

def _make_client(base_url: str | None, api_key: str | None) -> AsyncOpenAI:
    """Create an AsyncOpenAI client with the given config."""
    return AsyncOpenAI(
        base_url=base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        api_key=api_key or os.environ.get("OPENAI_API_KEY", ""),
    )


async def call_llm(
    client: AsyncOpenAI,
    model: str,
    prompt: str,
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> dict:
    """Send a single prompt to the LLM. Returns response dict with text and metadata."""
    t0 = time.time()
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        elapsed = time.time() - t0
        text = response.choices[0].message.content or ""
        return {
            "text": text,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            },
            "elapsed_s": round(elapsed, 2),
            "error": None,
        }
    except Exception as e:
        elapsed = time.time() - t0
        return {
            "text": "",
            "model": model,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
            "elapsed_s": round(elapsed, 2),
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# Experiment runner
# ---------------------------------------------------------------------------

CONDITION_KEYS = [
    ("condition_a_baseline", "response_baseline"),
    ("condition_b_rag", "response_rag"),
    ("condition_c_mcp", "response_mcp"),
]


async def run_single_headword(
    client: AsyncOpenAI,
    model: str,
    prompt_entry: dict,
    temperature: float,
    max_tokens: int,
) -> dict:
    """Run all 3 conditions for one headword. Returns response dict."""
    result = {
        "term": prompt_entry["term"],
        "band": prompt_entry.get("band"),
        "pinyin": prompt_entry.get("pinyin"),
    }

    for prompt_key, response_key in CONDITION_KEYS:
        prompt_text = prompt_entry[prompt_key]
        resp = await call_llm(client, model, prompt_text, temperature, max_tokens)
        result[response_key] = resp["text"]
        result[f"{response_key}_meta"] = {
            "model": resp["model"],
            "usage": resp["usage"],
            "elapsed_s": resp["elapsed_s"],
            "error": resp["error"],
        }

    return result


async def run_experiment(
    prompts: list[dict],
    existing_responses: list[dict],
    client: AsyncOpenAI,
    model: str,
    temperature: float,
    max_tokens: int,
    concurrency: int,
    output_path: Path,
) -> list[dict]:
    """Run the full experiment with concurrency and checkpointing."""
    # Build set of already-completed terms
    done_terms = {r["term"] for r in existing_responses if r.get("response_mcp")}
    responses = list(existing_responses)

    # Filter to remaining prompts
    remaining = [p for p in prompts if p["term"] not in done_terms]

    if not remaining:
        click.echo("All headwords already completed. Nothing to do.")
        return responses

    click.echo(
        f"Running {len(remaining)} headwords "
        f"({len(done_terms)} already done, {len(remaining) * 3} LLM calls)"
    )

    sem = asyncio.Semaphore(concurrency)
    completed = 0
    total = len(remaining)
    t_start = time.time()

    async def process_one(prompt_entry: dict) -> dict:
        nonlocal completed
        async with sem:
            result = await run_single_headword(
                client, model, prompt_entry, temperature, max_tokens
            )
            completed += 1
            elapsed = time.time() - t_start
            rate = completed / elapsed if elapsed > 0 else 0
            eta = (total - completed) / rate if rate > 0 else 0

            # Count errors
            errors = sum(
                1 for _, rk in CONDITION_KEYS
                if result.get(f"{rk}_meta", {}).get("error")
            )
            err_str = f" ({errors} errors)" if errors else ""

            click.echo(
                f"  [{completed}/{total}] {result['term']} "
                f"({result['band']}){err_str} "
                f"[{rate:.1f}/s, ETA {eta:.0f}s]"
            )
            return result

    # Run with concurrency
    tasks = [process_one(p) for p in remaining]
    new_results = await asyncio.gather(*tasks)
    responses.extend(new_results)

    # Save checkpoint
    _save_responses(responses, output_path)

    elapsed_total = time.time() - t_start
    total_calls = len(new_results) * 3
    total_tokens = sum(
        r.get(f"{rk}_meta", {}).get("usage", {}).get("prompt_tokens", 0)
        + r.get(f"{rk}_meta", {}).get("usage", {}).get("completion_tokens", 0)
        for r in new_results
        for _, rk in CONDITION_KEYS
    )

    click.echo(f"\nDone: {len(new_results)} headwords, {total_calls} LLM calls")
    click.echo(f"Time: {elapsed_total:.1f}s ({total_calls / elapsed_total:.1f} calls/s)")
    click.echo(f"Tokens: {total_tokens:,}")

    return responses


def _save_responses(responses: list[dict], path: Path) -> None:
    """Save responses to JSON with atomic write."""
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(responses, f, ensure_ascii=False, indent=2)
    tmp.rename(path)


def load_responses(path: Path) -> list[dict]:
    """Load existing responses for resume."""
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.command()
@click.option("--prompts", type=click.Path(exists=True), required=True,
              help="Path to paper5_eval_prompts.json")
@click.option("--output", default="data/paper5_eval_responses.json",
              help="Path to save responses")
@click.option("--provider", type=click.Choice(list(PROVIDERS.keys())),
              default=None, help="Use a preconfigured provider profile")
@click.option("--base-url", default=None,
              help="OpenAI-compatible API base URL (or OPENAI_BASE_URL env)")
@click.option("--api-key", default=None,
              help="API key (or OPENAI_API_KEY env)")
@click.option("--model", default=None,
              help="Model name (overrides provider default)")
@click.option("--temperature", default=0.0, type=float,
              help="Sampling temperature (0.0 for deterministic)")
@click.option("--max-tokens", default=1024, type=int,
              help="Max response tokens per call")
@click.option("--concurrency", default=None, type=int,
              help="Max concurrent API calls (overrides provider default)")
@click.option("--limit", default=0, type=int,
              help="Limit headwords (0=all, for testing)")
@click.option("--resume/--no-resume", default=True,
              help="Resume from existing output file")
def main(
    prompts: str,
    output: str,
    provider: str | None,
    base_url: str | None,
    api_key: str | None,
    model: str | None,
    temperature: float,
    max_tokens: int,
    concurrency: int | None,
    limit: int,
    resume: bool,
):
    """Run Paper 5 experiment: send prompts to LLM, collect responses."""
    # Resolve provider profile
    if provider:
        profile = PROVIDERS[provider]
        base_url = base_url or profile["base_url"]
        model = model or profile["model"]
        api_key = _resolve_api_key(profile["api_key_source"], api_key)
        concurrency = concurrency or profile["concurrency"]
    else:
        model = model or "gpt-4o-mini"
        concurrency = concurrency or 10

    # Load prompts
    with open(prompts) as f:
        prompt_data = json.load(f)

    if limit > 0:
        prompt_data = prompt_data[:limit]

    click.echo(f"Loaded {len(prompt_data)} prompt sets from {prompts}")
    click.echo(f"Provider: {provider or 'custom'} | Model: {model}")
    click.echo(f"Concurrency: {concurrency} | Temperature: {temperature}")

    # Load existing responses for resume
    output_path = Path(output)
    existing = load_responses(output_path) if resume else []
    if existing:
        click.echo(f"Resuming: {len(existing)} existing responses in {output}")

    # Create client
    client = _make_client(base_url, api_key)

    # Run
    responses = asyncio.run(
        run_experiment(
            prompt_data, existing, client, model,
            temperature, max_tokens, concurrency, output_path,
        )
    )

    click.echo(f"\nSaved {len(responses)} responses to {output}")


if __name__ == "__main__":
    main()
