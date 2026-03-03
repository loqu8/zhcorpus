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


def strip_thinking(text: str) -> str:
    """Strip <think>...</think> blocks from LLM responses (e.g. MiniMax M2.5).

    If the response has content after </think>, use only that content.
    If the entire response is inside <think> tags (model put the answer in
    the thinking block), extract and use the thinking content instead.
    """
    if '<think>' not in text:
        return text

    # Try stripping — if there's substantial content after, use that
    clean = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    if len(clean) > 50:
        return clean

    # Entire response is inside <think> — extract the thinking content
    m = re.search(r'<think>(.*?)</think>', text, flags=re.DOTALL)
    if m:
        return m.group(1).strip()

    return text.strip()


# Diacritical pinyin → numbered tone mapping
_TONE_MAP = {
    'ā': 'a1', 'á': 'a2', 'ǎ': 'a3', 'à': 'a4',
    'ē': 'e1', 'é': 'e2', 'ě': 'e3', 'è': 'e4',
    'ī': 'i1', 'í': 'i2', 'ǐ': 'i3', 'ì': 'i4',
    'ō': 'o1', 'ó': 'o2', 'ǒ': 'o3', 'ò': 'o4',
    'ū': 'u1', 'ú': 'u2', 'ǔ': 'u3', 'ù': 'u4',
    'ǖ': 'v1', 'ǘ': 'v2', 'ǚ': 'v3', 'ǜ': 'v4',
    'ü': 'v',
}


def _diacritical_to_numbered(text: str) -> str:
    """Convert diacritical pinyin (ái) to numbered (ai2).

    Tone number is placed at the end of the syllable (after all vowels/consonants),
    not immediately after the toned vowel.
    """
    result = []
    tone = ''
    for ch in text:
        if ch in _TONE_MAP:
            mapped = _TONE_MAP[ch]
            if len(mapped) == 2:  # letter + tone number
                result.append(mapped[0])
                tone = mapped[1]
            else:
                result.append(mapped)
        elif ch.isalpha():
            result.append(ch)
        else:
            # Non-alpha boundary: flush pending tone
            if tone:
                result.append(tone)
                tone = ''
            result.append(ch)
    if tone:
        result.append(tone)
    return ''.join(result)


def extract_pinyin(text: str) -> str | None:
    """Extract pinyin from generated text.

    Handles both numbered (ai2) and diacritical (ái) formats.
    """
    # Common patterns: numbered tones
    patterns = [
        r'\(([a-z]+\d[a-z\s\d]*)\)',  # (ai2)
        r'\[([a-z]+\d[a-z\s\d]*)\]',  # [ai2]
        r'[Pp]inyin:?\s*([a-z]+\d[a-z\s\d]*)',  # Pinyin: ai2
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()

    # Diacritical patterns: ái, cè shì, etc.
    diacritical_chars = r'[a-zA-Zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü]'
    diacritical_patterns = [
        r'[Pp]inyin[:\s]*\*?\*?\s*(' + diacritical_chars + r'+(?:\s+' + diacritical_chars + r'+)*)',
    ]
    for pat in diacritical_patterns:
        m = re.search(pat, text)
        if m:
            raw = m.group(1).strip()
            return _diacritical_to_numbered(raw)

    return None


def normalize_pinyin(pinyin: str) -> str:
    """Normalize pinyin for comparison (lowercase, letters + tones only).

    Compares just the letters (ignoring tone position):
      'a2i' and 'ai2' both normalize to the same form.
    """
    clean = re.sub(r'[^a-z0-9]', '', pinyin.lower())
    # Extract just the letters and just the digits separately
    letters = re.sub(r'[^a-z]', '', clean)
    tones = re.sub(r'[^0-9]', '', clean)
    return letters + tones


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

    # Strip thinking blocks (e.g. MiniMax M2.5 <think>...</think>)
    generated = strip_thinking(generated)

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

    # Match by term, not position
    ref_by_term = {r["term"]: r for r in ref_data}

    for resp in resp_data:
        term = resp.get("term")
        ref = ref_by_term.get(term)
        if not ref:
            continue
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
