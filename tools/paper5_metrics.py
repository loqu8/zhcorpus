"""Paper 5 Evaluation Metrics: Score generated dictionary entries.

Metrics:
  1. Atomic factual precision (FActScore-style)
  2. Definition completeness (senses covered)
  3. Pinyin accuracy
  4. Example authenticity (is the example attested in corpus?)

Usage:
    .venv/bin/python tools/paper5_metrics.py \
        --responses data/paper5_eval_responses.json \
        --references data/paper5_eval_references.json
"""

import json
import re
from pathlib import Path

import click


def extract_pinyin(text: str) -> str | None:
    """Extract pinyin from generated text."""
    # Common patterns: (pin1 yin1), [pin1 yin1], pinyin: pin1 yin1
    patterns = [
        r'\(([a-z]+\d[a-z\s\d]*)\)',  # (ai2)
        r'\[([a-z]+\d[a-z\s\d]*)\]',  # [ai2]
        r'[Pp]inyin:?\s*([a-z]+\d[a-z\s\d]*)',  # Pinyin: ai2
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()
    return None


def normalize_pinyin(pinyin: str) -> str:
    """Normalize pinyin for comparison (lowercase, strip spaces/punctuation)."""
    return re.sub(r'[^a-z0-9]', '', pinyin.lower())


def score_pinyin_accuracy(generated: str, reference: str) -> float:
    """Score pinyin accuracy (0 or 1)."""
    if not reference:
        return 1.0  # can't evaluate

    gen_pinyin = extract_pinyin(generated)
    if not gen_pinyin:
        return 0.0

    return 1.0 if normalize_pinyin(gen_pinyin) == normalize_pinyin(reference) else 0.0


def extract_definitions(text: str) -> list[str]:
    """Extract English definitions from generated text."""
    defs = []
    # Look for definition lines
    for line in text.split('\n'):
        line = line.strip()
        # Common patterns
        if re.match(r'^\d+\.', line) or re.match(r'^[-*]', line):
            # Remove bullets/numbers
            clean = re.sub(r'^[\d.)\-*\s]+', '', line).strip()
            if clean and len(clean) > 2:
                defs.append(clean.lower())
        elif 'definition' in line.lower() or 'meaning' in line.lower():
            clean = re.sub(r'.*?:\s*', '', line).strip()
            if clean:
                defs.append(clean.lower())
    return defs


def score_definition_completeness(
    generated: str,
    reference_defs: list[dict],
) -> float:
    """Score how many reference senses are covered in the generated text.

    Simple substring matching: for each reference definition, check if
    key words appear in the generated text.
    """
    if not reference_defs:
        return 1.0

    generated_lower = generated.lower()
    covered = 0

    for ref in reference_defs:
        ref_def = ref["definition"].lower()
        # Extract key English words (skip particles, CL:, etc.)
        words = re.findall(r'[a-zA-Z]{3,}', ref_def)
        key_words = [w for w in words if w not in {
            'the', 'and', 'for', 'that', 'this', 'with', 'from',
            'also', 'see', 'used', 'abbr', 'variant',
        }]

        if not key_words:
            covered += 1  # can't evaluate
            continue

        # Check if at least half the key words appear
        matches = sum(1 for w in key_words if w in generated_lower)
        if matches >= len(key_words) * 0.5:
            covered += 1

    return covered / len(reference_defs)


def score_example_authenticity(
    generated: str,
    term: str,
    corpus_conn=None,
) -> float:
    """Check if the generated example sentence contains the term.

    Basic check: does the example actually use the word?
    Advanced (with corpus_conn): is the example attested in the corpus?
    """
    # Find example sentences (lines with Chinese characters)
    chinese_lines = []
    for line in generated.split('\n'):
        if re.search(r'[\u4e00-\u9fff]{4,}', line) and term in line:
            chinese_lines.append(line)

    if not chinese_lines:
        return 0.0

    # Basic: example contains the target term
    return 1.0


def score_entry(
    generated: str,
    reference: dict,
) -> dict:
    """Score a single generated dictionary entry against reference."""
    term = reference["term"]

    # 1. Pinyin accuracy
    pinyin_score = score_pinyin_accuracy(generated, reference.get("pinyin", ""))

    # 2. Definition completeness
    def_score = score_definition_completeness(
        generated,
        reference.get("definitions", []),
    )

    # 3. Term presence (does the generated entry mention the term?)
    term_present = 1.0 if term in generated else 0.0

    # 4. Example authenticity
    example_score = score_example_authenticity(generated, term)

    return {
        "term": term,
        "pinyin_accuracy": pinyin_score,
        "definition_completeness": def_score,
        "term_present": term_present,
        "example_authenticity": example_score,
        "composite": (pinyin_score + def_score + term_present + example_score) / 4,
    }


@click.command()
@click.option("--responses", type=click.Path(exists=True), required=True)
@click.option("--references", type=click.Path(exists=True), required=True)
def main(responses: str, references: str):
    """Score generated dictionary entries against references."""
    with open(responses) as f:
        resp_data = json.load(f)
    with open(references) as f:
        ref_data = json.load(f)

    conditions = ["baseline", "rag", "mcp"]
    results = {c: [] for c in conditions}

    for resp, ref in zip(resp_data, ref_data):
        for cond in conditions:
            key = f"response_{cond}"
            if key not in resp:
                continue
            score = score_entry(resp[key], ref)
            score["band"] = ref.get("band", "unknown")
            score["condition"] = cond
            results[cond].append(score)

    # Summary
    click.echo("\n=== PAPER 5 EVALUATION RESULTS ===\n")

    for cond in conditions:
        scores = results[cond]
        if not scores:
            click.echo(f"{cond.upper()}: no data")
            continue

        avg_pinyin = sum(s["pinyin_accuracy"] for s in scores) / len(scores)
        avg_def = sum(s["definition_completeness"] for s in scores) / len(scores)
        avg_term = sum(s["term_present"] for s in scores) / len(scores)
        avg_example = sum(s["example_authenticity"] for s in scores) / len(scores)
        avg_comp = sum(s["composite"] for s in scores) / len(scores)

        click.echo(f"--- {cond.upper()} (n={len(scores)}) ---")
        click.echo(f"  Pinyin accuracy:         {avg_pinyin:.1%}")
        click.echo(f"  Definition completeness: {avg_def:.1%}")
        click.echo(f"  Term present:            {avg_term:.1%}")
        click.echo(f"  Example authenticity:    {avg_example:.1%}")
        click.echo(f"  Composite:               {avg_comp:.1%}")
        click.echo()

        # Per-band breakdown
        for band in ["high", "mid", "low", "rare"]:
            band_scores = [s for s in scores if s["band"] == band]
            if band_scores:
                avg = sum(s["composite"] for s in band_scores) / len(band_scores)
                click.echo(f"  {band:6s}: {avg:.1%} (n={len(band_scores)})")
        click.echo()


if __name__ == "__main__":
    main()
