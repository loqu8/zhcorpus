"""Paper 5 LLM-as-Judge: Blind evaluation of dictionary entries by Claude.

Presents 3 dictionary entries (Baseline/RAG/MCP) in randomized order,
labeled Entry A/B/C, to Claude for rubric-based scoring.

Rubric dimensions (1-5 each):
  1. Accuracy — pinyin, definitions, part of speech correct?
  2. Completeness — all major senses covered?
  3. Example quality — natural, illustrative, appropriate?
  4. Organization — well-structured, easy to use?
  5. Overall — holistic quality judgment

Usage:
    .venv/bin/python tools/paper5_judge.py \
        --responses data/paper5_eval_responses.json \
        --output data/paper5_eval_judgments.json \
        --limit 5

    # Resume after interruption
    .venv/bin/python tools/paper5_judge.py \
        --responses data/paper5_eval_responses.json \
        --output data/paper5_eval_judgments.json
"""

import asyncio
import json
import os
import random
import re
import time
from pathlib import Path

import click
from anthropic import AsyncAnthropic


# ---------------------------------------------------------------------------
# Rubric prompt
# ---------------------------------------------------------------------------

JUDGE_SYSTEM = """\
You are an expert lexicographer evaluating Chinese-English dictionary entries.
You will be shown a Chinese headword and three candidate dictionary entries
labeled Entry A, Entry B, and Entry C (in random order).

Rate EACH entry independently on these dimensions using a 1-5 scale:

1. **Accuracy** (1-5): Are the pinyin, definitions, and part of speech correct?
   - 5: All facts correct
   - 3: Minor errors (e.g. tone number off, missing a sense)
   - 1: Major errors (wrong pinyin, wrong meaning)

2. **Completeness** (1-5): Are all major senses/uses of the word covered?
   - 5: Comprehensive — covers all common and important senses
   - 3: Covers the primary sense but misses secondary ones
   - 1: Only covers one sense or is very superficial

3. **Example Quality** (1-5): Is the example sentence natural, illustrative, and useful?
   - 5: Natural Chinese, clearly demonstrates the word's usage, with accurate translation
   - 3: Acceptable but generic or not very illustrative
   - 1: Unnatural, incorrect, or no example provided

4. **Organization** (1-5): Is the entry well-structured and easy to use?
   - 5: Clear headings, logical flow, easy to scan
   - 3: Readable but could be better organized
   - 1: Disorganized, hard to find information

5. **Overall** (1-5): Holistic quality — would this be useful in a real dictionary?
   - 5: Publication-ready, comprehensive and accurate
   - 3: Acceptable but needs improvement
   - 1: Not suitable for use

Respond in EXACTLY this JSON format (no other text):
{
  "entry_a": {"accuracy": N, "completeness": N, "example_quality": N, "organization": N, "overall": N},
  "entry_b": {"accuracy": N, "completeness": N, "example_quality": N, "organization": N, "overall": N},
  "entry_c": {"accuracy": N, "completeness": N, "example_quality": N, "organization": N, "overall": N}
}"""


def _build_judge_prompt(term: str, entries: list[tuple[str, str]]) -> str:
    """Build the judge prompt with 3 blind entries.

    Args:
        term: Chinese headword
        entries: list of (label, text) tuples, e.g. [("Entry A", "..."), ...]
    """
    parts = [f"## Headword: {term}\n"]
    for label, text in entries:
        # Strip thinking blocks before showing to judge
        clean = _strip_thinking(text)
        parts.append(f"### {label}\n{clean}\n")
    parts.append("Rate each entry on the rubric. Respond with JSON only.")
    return "\n".join(parts)


def _strip_thinking(text: str) -> str:
    """Strip <think> blocks, falling back to thinking content if response is empty."""
    if '<think>' not in text:
        return text
    clean = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    if len(clean) > 50:
        return clean
    m = re.search(r'<think>(.*?)</think>', text, flags=re.DOTALL)
    return m.group(1).strip() if m else text.strip()


# ---------------------------------------------------------------------------
# Blind randomization
# ---------------------------------------------------------------------------

CONDITIONS = ["baseline", "rag", "mcp"]
LABELS = ["Entry A", "Entry B", "Entry C"]


def randomize_entries(response: dict, seed: int) -> tuple[list[tuple[str, str]], dict]:
    """Randomize condition order for blind evaluation.

    Returns:
        (entries, mapping) where entries is [(label, text), ...] and
        mapping is {"Entry A": "mcp", "Entry B": "baseline", ...}
    """
    rng = random.Random(seed)
    order = list(CONDITIONS)
    rng.shuffle(order)

    entries = []
    mapping = {}
    for label, cond in zip(LABELS, order):
        text = response.get(f"response_{cond}", "")
        entries.append((label, text))
        mapping[label] = cond

    return entries, mapping


# ---------------------------------------------------------------------------
# Judge API call
# ---------------------------------------------------------------------------

def _get_client() -> AsyncAnthropic:
    """Create Anthropic client from environment."""
    return AsyncAnthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
    )


async def judge_one(
    client: AsyncAnthropic,
    model: str,
    term: str,
    entries: list[tuple[str, str]],
    max_retries: int = 2,
) -> dict | None:
    """Call Claude to judge 3 entries for one headword."""
    prompt = _build_judge_prompt(term, entries)

    for attempt in range(max_retries + 1):
        try:
            response = await client.messages.create(
                model=model,
                max_tokens=512,
                system=JUDGE_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()

            # Extract JSON (Claude sometimes wraps in markdown code blocks)
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

        except Exception as e:
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
                continue
            return {"error": str(e)}

    return None


# ---------------------------------------------------------------------------
# Experiment runner
# ---------------------------------------------------------------------------

async def run_judgments(
    responses: list[dict],
    existing: list[dict],
    client: AsyncAnthropic,
    model: str,
    concurrency: int,
    output_path: Path,
) -> list[dict]:
    """Run blind judgments for all headwords."""
    done_terms = {j["term"] for j in existing if j.get("scores")}
    judgments = list(existing)
    remaining = [r for r in responses if r["term"] not in done_terms]

    if not remaining:
        click.echo("All headwords already judged.")
        return judgments

    click.echo(f"Judging {len(remaining)} headwords ({len(done_terms)} already done)")

    sem = asyncio.Semaphore(concurrency)
    completed = 0
    total = len(remaining)
    t_start = time.time()

    async def process_one(resp: dict, idx: int) -> dict:
        nonlocal completed
        async with sem:
            term = resp["term"]
            # Use term hash + index as seed for reproducible randomization
            seed = hash(term) + idx
            entries, mapping = randomize_entries(resp, seed)

            scores = await judge_one(client, model, term, entries)

            completed += 1
            elapsed = time.time() - t_start
            rate = completed / elapsed if elapsed > 0 else 0
            click.echo(f"  [{completed}/{total}] {term} [{rate:.1f}/s]")

            # Unblind: map Entry A/B/C back to conditions
            unblinded = {}
            if scores and "error" not in scores:
                for label in LABELS:
                    cond = mapping[label]
                    label_key = label.lower().replace(" ", "_")
                    unblinded[cond] = scores.get(label_key, {})

            return {
                "term": term,
                "band": resp.get("band"),
                "mapping": mapping,
                "raw_scores": scores,
                "scores": unblinded,
            }

    tasks = [process_one(r, i) for i, r in enumerate(remaining)]
    new_judgments = await asyncio.gather(*tasks)
    judgments.extend(new_judgments)

    # Save
    _save(judgments, output_path)

    elapsed_total = time.time() - t_start
    click.echo(f"\nDone: {len(new_judgments)} judgments in {elapsed_total:.1f}s")

    return judgments


def _save(data: list[dict], path: Path) -> None:
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.rename(path)


def load_judgments(path: Path) -> list[dict]:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


# ---------------------------------------------------------------------------
# Results summary
# ---------------------------------------------------------------------------

DIMENSIONS = ["accuracy", "completeness", "example_quality", "organization", "overall"]


def summarize_judgments(judgments: list[dict]) -> str:
    """Generate summary tables from judgments."""
    lines = ["# LLM-as-Judge Results\n"]

    # Collect scores by condition
    by_cond = {c: {d: [] for d in DIMENSIONS} for c in CONDITIONS}
    by_band = {}

    for j in judgments:
        scores = j.get("scores", {})
        band = j.get("band", "unknown")

        for cond in CONDITIONS:
            cond_scores = scores.get(cond, {})
            for dim in DIMENSIONS:
                val = cond_scores.get(dim)
                if val is not None:
                    by_cond[cond][dim].append(val)

                    by_band.setdefault(band, {}).setdefault(cond, {}).setdefault(dim, []).append(val)

    # Main table
    lines.append("## Overall Scores (1-5 scale)\n")
    lines.append("| Dimension | Baseline | RAG | MCP |")
    lines.append("|-----------|----------|-----|-----|")
    for dim in DIMENSIONS:
        row = f"| {dim.replace('_', ' ').title()} |"
        for cond in CONDITIONS:
            vals = by_cond[cond][dim]
            avg = sum(vals) / len(vals) if vals else 0
            row += f" {avg:.2f} |"
        lines.append(row)

    # Per-band breakdown (overall only)
    lines.append("\n## Per-Band Overall Scores\n")
    lines.append("| Band | n | Baseline | RAG | MCP |")
    lines.append("|------|---|----------|-----|-----|")
    for band in ["high", "mid", "low", "rare"]:
        if band not in by_band:
            continue
        n = len(by_band[band].get("baseline", {}).get("overall", []))
        row = f"| {band} | {n} |"
        for cond in CONDITIONS:
            vals = by_band[band].get(cond, {}).get("overall", [])
            avg = sum(vals) / len(vals) if vals else 0
            row += f" {avg:.2f} |"
        lines.append(row)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.command()
@click.option("--responses", type=click.Path(exists=True), required=True)
@click.option("--output", default="data/paper5_eval_judgments.json")
@click.option("--model", default="claude-sonnet-4-20250514",
              help="Claude model for judging")
@click.option("--concurrency", default=5, type=int)
@click.option("--limit", default=0, type=int, help="Limit headwords (0=all)")
@click.option("--resume/--no-resume", default=True)
def main(responses: str, output: str, model: str, concurrency: int, limit: int, resume: bool):
    """Run blind LLM-as-judge evaluation of dictionary entries."""
    with open(responses) as f:
        resp_data = json.load(f)

    if limit > 0:
        resp_data = resp_data[:limit]

    click.echo(f"Loaded {len(resp_data)} responses")
    click.echo(f"Judge model: {model}")

    output_path = Path(output)
    existing = load_judgments(output_path) if resume else []

    client = _get_client()

    judgments = asyncio.run(
        run_judgments(resp_data, existing, client, model, concurrency, output_path)
    )

    # Summary
    summary = summarize_judgments(judgments)
    click.echo("\n" + summary)

    # Save summary
    summary_path = output_path.with_suffix(".summary.md")
    with open(summary_path, "w") as f:
        f.write(summary)
    click.echo(f"\nSaved summary to {summary_path}")


if __name__ == "__main__":
    main()
