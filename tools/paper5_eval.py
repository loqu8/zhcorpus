"""Paper 5 Evaluation: MCP vs RAG vs Baseline for dictionary entry generation.

Three conditions:
  (A) Baseline — LLM generates from parametric knowledge only
  (B) RAG — LLM receives top-5 raw corpus passages
  (C) MCP — LLM receives structured word_report (definitions + examples + dialects)

For each headword, generates a dictionary entry under all 3 conditions,
then evaluates against reference definitions (CEDICT + dictmaster).

Usage:
    .venv/bin/python tools/paper5_eval.py --headwords data/paper5_eval_headwords.json
    .venv/bin/python tools/paper5_eval.py --headwords data/paper5_eval_headwords.json --limit 10
"""

import asyncio
import json
import sqlite3
import time
from pathlib import Path

import click

from zhcorpus.db import get_connection
from zhcorpus.search.fts import search_fts
from zhcorpus.mcp.server import configure_test_dbs, word_report


# ---------------------------------------------------------------------------
# Condition A: Baseline prompt (no evidence)
# ---------------------------------------------------------------------------

BASELINE_PROMPT = """\
Generate a complete dictionary entry for the Chinese word: {term}

Include:
1. Pinyin pronunciation
2. English definition (all senses)
3. Part of speech
4. One example sentence in Chinese with English translation
5. Related words (synonyms or compounds)

Respond in structured format."""


# ---------------------------------------------------------------------------
# Condition B: RAG prompt (raw corpus passages)
# ---------------------------------------------------------------------------

RAG_PROMPT = """\
Generate a complete dictionary entry for the Chinese word: {term}

Here are real corpus passages containing this word:

{passages}

Based on these passages and your knowledge, include:
1. Pinyin pronunciation
2. English definition (all senses)
3. Part of speech
4. One example sentence in Chinese with English translation
5. Related words (synonyms or compounds)

Respond in structured format."""


# ---------------------------------------------------------------------------
# Condition C: MCP prompt (structured evidence)
# ---------------------------------------------------------------------------

MCP_PROMPT = """\
Generate a complete dictionary entry for the Chinese word: {term}

Here is structured evidence from the zhcorpus knowledge base:

{evidence}

Based on this evidence, include:
1. Pinyin pronunciation
2. English definition (all senses)
3. Part of speech
4. One example sentence in Chinese with English translation
5. Related words (synonyms or compounds)

Respond in structured format."""


# ---------------------------------------------------------------------------
# Evidence builders
# ---------------------------------------------------------------------------

def build_rag_context(corpus_conn: sqlite3.Connection, term: str, top_k: int = 5) -> str:
    """Build RAG context: top-k raw corpus passages."""
    results = search_fts(corpus_conn, term, limit=top_k)
    if not results:
        return "(No corpus passages found)"
    passages = []
    for i, r in enumerate(results, 1):
        passages.append(f"[{i}] Source: {r.source} | {r.title}\n{r.text}")
    return "\n\n".join(passages)


async def build_mcp_context(term: str) -> str:
    """Build MCP context: structured word_report."""
    return await word_report(term, detail="standard")


# ---------------------------------------------------------------------------
# Reference data for evaluation
# ---------------------------------------------------------------------------

def get_reference_data(
    dict_conn: sqlite3.Connection,
    corpus_conn: sqlite3.Connection,
    term: str,
) -> dict:
    """Get ground truth data for evaluation."""
    # All definitions
    defs = dict_conn.execute(
        """
        SELECT d.lang, d.definition, d.source
        FROM definitions d
        JOIN headwords h ON h.id = d.headword_id
        WHERE (h.simplified = ? OR h.traditional = ?) AND d.lang = 'en'
        ORDER BY d.source
        """,
        (term, term),
    ).fetchall()

    # Pinyin
    hw = dict_conn.execute(
        "SELECT pinyin FROM headwords WHERE simplified = ? OR traditional = ?",
        (term, term),
    ).fetchone()

    # Dialect forms
    dialects = dict_conn.execute(
        """
        SELECT df.dialect, df.pronunciation, df.native_chars, df.source
        FROM dialect_forms df
        JOIN headwords h ON h.id = df.headword_id
        WHERE h.simplified = ? OR h.traditional = ?
        """,
        (term, term),
    ).fetchall()

    # Corpus hit count
    from zhcorpus.search.fts import count_hits
    hits = count_hits(corpus_conn, term)

    return {
        "term": term,
        "pinyin": hw["pinyin"] if hw else None,
        "definitions": [{"definition": d["definition"], "source": d["source"]} for d in defs],
        "dialect_forms": [dict(d) for d in dialects],
        "corpus_hits": hits,
    }


# ---------------------------------------------------------------------------
# Prompt generation (for offline evaluation with any LLM)
# ---------------------------------------------------------------------------

def generate_prompts(
    corpus_conn: sqlite3.Connection,
    headword: dict,
) -> dict:
    """Generate all 3 condition prompts for a headword."""
    term = headword["simplified"]

    # Condition A: baseline
    baseline = BASELINE_PROMPT.format(term=term)

    # Condition B: RAG
    rag_context = build_rag_context(corpus_conn, term, top_k=5)
    rag = RAG_PROMPT.format(term=term, passages=rag_context)

    # Condition C: MCP
    mcp_context = asyncio.run(build_mcp_context(term))
    mcp = MCP_PROMPT.format(term=term, evidence=mcp_context)

    return {
        "term": term,
        "pinyin": headword.get("pinyin"),
        "band": headword.get("band"),
        "corpus_hits": headword.get("corpus_hits"),
        "condition_a_baseline": baseline,
        "condition_b_rag": rag,
        "condition_c_mcp": mcp,
        "rag_context_chars": len(rag_context),
        "mcp_context_chars": len(mcp_context),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

@click.command()
@click.option("--headwords", type=click.Path(exists=True), required=True)
@click.option("--limit", default=0, help="Limit headwords per band (0=all)")
@click.option("--output", default="data/paper5_eval_prompts.json")
@click.option("--corpus-db", default="data/artifacts/zhcorpus.db")
@click.option("--dict-db", default="data/artifacts/dictmaster.db")
def main(headwords: str, limit: int, output: str, corpus_db: str, dict_db: str):
    """Generate evaluation prompts for Paper 5 experiment."""
    with open(headwords) as f:
        data = json.load(f)

    corpus_conn = get_connection(corpus_db)
    dict_conn = sqlite3.connect(dict_db)
    dict_conn.row_factory = sqlite3.Row

    # Configure MCP server to use these connections
    configure_test_dbs(corpus_conn, dict_conn)

    all_prompts = []
    all_references = []

    for band_name in ["high", "mid", "low", "rare"]:
        band = data["bands"][band_name]
        if limit > 0:
            band = band[:limit]

        click.echo(f"\n=== {band_name.upper()} band ({len(band)} headwords) ===")

        for i, hw in enumerate(band):
            hw["band"] = band_name
            term = hw["simplified"]

            t0 = time.time()
            prompts = generate_prompts(corpus_conn, hw)
            ref = get_reference_data(dict_conn, corpus_conn, term)
            ref["band"] = band_name
            elapsed = time.time() - t0

            all_prompts.append(prompts)
            all_references.append(ref)

            click.echo(
                f"  [{i+1}/{len(band)}] {term} "
                f"(RAG: {prompts['rag_context_chars']:,} chars, "
                f"MCP: {prompts['mcp_context_chars']:,} chars) "
                f"{elapsed:.1f}s"
            )

    # Save prompts
    with open(output, "w") as f:
        json.dump(all_prompts, f, ensure_ascii=False, indent=2)
    click.echo(f"\nSaved {len(all_prompts)} prompt sets to {output}")

    # Save references
    ref_path = output.replace("prompts", "references")
    with open(ref_path, "w") as f:
        json.dump(all_references, f, ensure_ascii=False, indent=2)
    click.echo(f"Saved {len(all_references)} reference sets to {ref_path}")

    # Summary stats
    avg_rag = sum(p["rag_context_chars"] for p in all_prompts) / len(all_prompts)
    avg_mcp = sum(p["mcp_context_chars"] for p in all_prompts) / len(all_prompts)
    click.echo(f"\nAverage context size: RAG={avg_rag:.0f} chars, MCP={avg_mcp:.0f} chars")


if __name__ == "__main__":
    main()
