"""Paper 5 Analysis: Statistical analysis and paper-ready tables.

Extends paper5_metrics.py with:
  - Per-band breakdowns with confidence intervals
  - Statistical significance tests (paired bootstrap + Wilcoxon)
  - Markdown and LaTeX table generation
  - Context size analysis (RAG vs MCP token counts)

Usage:
    .venv/bin/python tools/paper5_analysis.py \
        --responses data/paper5_eval_responses.json \
        --references data/paper5_eval_references.json \
        --prompts data/paper5_eval_prompts.json \
        --output-dir docs/Projects/paper-c-mcp-vs-rag/tables
"""

import json
import math
import random
from collections import defaultdict
from pathlib import Path

import click
import numpy as np

from tools.paper5_metrics import score_entry


# ---------------------------------------------------------------------------
# Score all entries
# ---------------------------------------------------------------------------

METRICS = ["pinyin_accuracy", "definition_completeness", "term_present", "example_authenticity", "composite"]
CONDITIONS = ["baseline", "rag", "mcp"]
BANDS = ["high", "mid", "low", "rare"]


def score_all(responses: list[dict], references: list[dict]) -> dict:
    """Score all entries, return structured results.

    Returns:
        {
            "scores": [{"term": ..., "band": ..., "baseline": {...}, "rag": {...}, "mcp": {...}}, ...],
            "by_condition": {"baseline": [...], "rag": [...], "mcp": [...]},
            "by_band": {"high": [...], ...},
        }
    """
    scores = []
    by_condition = defaultdict(list)
    by_band = defaultdict(list)

    # Match by term, not position
    ref_by_term = {r["term"]: r for r in references}

    for resp in responses:
        term = resp.get("term")
        ref = ref_by_term.get(term)
        if not ref:
            continue
        entry = {
            "term": ref["term"],
            "band": ref.get("band", "unknown"),
        }

        for cond in CONDITIONS:
            resp_key = f"response_{cond}"
            if resp_key not in resp or not resp[resp_key]:
                entry[cond] = {m: 0.0 for m in METRICS}
                continue
            s = score_entry(resp[resp_key], ref)
            entry[cond] = s
            by_condition[cond].append(s)

        scores.append(entry)
        by_band[entry["band"]].append(entry)

    return {
        "scores": scores,
        "by_condition": dict(by_condition),
        "by_band": dict(by_band),
    }


# ---------------------------------------------------------------------------
# Statistical tests
# ---------------------------------------------------------------------------

def paired_bootstrap_test(
    scores_a: list[float],
    scores_b: list[float],
    n_bootstrap: int = 10000,
    seed: int = 42,
) -> dict:
    """Paired bootstrap test for difference in means.

    Returns p-value, mean difference, and 95% confidence interval.
    """
    rng = random.Random(seed)
    n = len(scores_a)
    assert n == len(scores_b), "Score lists must be same length"

    diffs = [b - a for a, b in zip(scores_a, scores_b)]
    observed_diff = sum(diffs) / n

    # Bootstrap
    boot_diffs = []
    for _ in range(n_bootstrap):
        sample = [rng.choice(diffs) for _ in range(n)]
        boot_diffs.append(sum(sample) / n)

    boot_diffs.sort()

    # Two-sided p-value: fraction of bootstrap samples on opposite side of 0
    if observed_diff >= 0:
        p_value = sum(1 for d in boot_diffs if d <= 0) / n_bootstrap
    else:
        p_value = sum(1 for d in boot_diffs if d >= 0) / n_bootstrap
    p_value = min(p_value * 2, 1.0)  # two-sided

    # 95% CI
    ci_lo = boot_diffs[int(0.025 * n_bootstrap)]
    ci_hi = boot_diffs[int(0.975 * n_bootstrap)]

    return {
        "observed_diff": observed_diff,
        "p_value": p_value,
        "ci_95_lo": ci_lo,
        "ci_95_hi": ci_hi,
        "n": n,
        "n_bootstrap": n_bootstrap,
    }


def wilcoxon_signed_rank(
    scores_a: list[float],
    scores_b: list[float],
) -> dict:
    """Wilcoxon signed-rank test (non-parametric paired test).

    Manual implementation — no scipy dependency.
    """
    n = len(scores_a)
    diffs = [b - a for a, b in zip(scores_a, scores_b)]

    # Remove zeros
    nonzero = [(abs(d), d) for d in diffs if d != 0]
    if not nonzero:
        return {"statistic": 0.0, "p_value": 1.0, "n_nonzero": 0}

    # Rank by absolute value
    nonzero.sort(key=lambda x: x[0])
    ranks = []
    i = 0
    while i < len(nonzero):
        j = i
        while j < len(nonzero) and nonzero[j][0] == nonzero[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2
        for k in range(i, j):
            ranks.append((avg_rank, nonzero[k][1]))
        i = j

    # Sum positive and negative ranks
    w_plus = sum(r for r, d in ranks if d > 0)
    w_minus = sum(r for r, d in ranks if d < 0)
    w = min(w_plus, w_minus)

    n_nz = len(ranks)

    # Normal approximation for p-value (valid for n >= 10)
    if n_nz >= 10:
        mean_w = n_nz * (n_nz + 1) / 4
        std_w = math.sqrt(n_nz * (n_nz + 1) * (2 * n_nz + 1) / 24)
        z = (w - mean_w) / std_w if std_w > 0 else 0
        # Two-sided p-value using normal approximation
        p_value = 2 * (1 - _norm_cdf(abs(z)))
    else:
        # For small samples, return NaN — would need exact tables
        p_value = float("nan")

    return {
        "statistic": w,
        "w_plus": w_plus,
        "w_minus": w_minus,
        "p_value": p_value,
        "n_nonzero": n_nz,
    }


def _norm_cdf(x: float) -> float:
    """Standard normal CDF approximation (Abramowitz & Stegun)."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


# ---------------------------------------------------------------------------
# Confidence intervals
# ---------------------------------------------------------------------------

def mean_with_ci(values: list[float], confidence: float = 0.95) -> dict:
    """Mean with bootstrap confidence interval."""
    n = len(values)
    if n == 0:
        return {"mean": 0.0, "ci_lo": 0.0, "ci_hi": 0.0, "n": 0}

    mean = sum(values) / n

    if n < 3:
        return {"mean": mean, "ci_lo": mean, "ci_hi": mean, "n": n}

    rng = random.Random(42)
    boot_means = sorted(
        sum(rng.choice(values) for _ in range(n)) / n
        for _ in range(5000)
    )
    alpha = 1 - confidence
    ci_lo = boot_means[int(alpha / 2 * len(boot_means))]
    ci_hi = boot_means[int((1 - alpha / 2) * len(boot_means))]

    return {"mean": mean, "ci_lo": ci_lo, "ci_hi": ci_hi, "n": n}


# ---------------------------------------------------------------------------
# Table generators
# ---------------------------------------------------------------------------

def generate_main_results_table(results: dict) -> str:
    """Generate the main results table (Table 1 in the paper).

    Rows: metrics. Columns: Baseline / RAG / MCP.
    """
    by_cond = results["by_condition"]

    lines = [
        "| Metric | Baseline | RAG | MCP |",
        "|--------|----------|-----|-----|",
    ]

    for metric in METRICS:
        row = f"| {_metric_name(metric)} |"
        for cond in CONDITIONS:
            scores = [s[metric] for s in by_cond.get(cond, [])]
            stats = mean_with_ci(scores)
            row += f" {stats['mean']:.1%} |"
        lines.append(row)

    return "\n".join(lines)


def generate_band_breakdown_table(results: dict) -> str:
    """Generate per-band composite scores (Table 2).

    Rows: bands. Columns: Baseline / RAG / MCP.
    """
    lines = [
        "| Band | n | Baseline | RAG | MCP | RAG-Base | MCP-Base | MCP-RAG |",
        "|------|---|----------|-----|-----|----------|----------|---------|",
    ]

    for band in BANDS:
        entries = results["by_band"].get(band, [])
        if not entries:
            continue

        n = len(entries)
        row = f"| {band} | {n} |"

        means = {}
        for cond in CONDITIONS:
            scores = [e[cond]["composite"] for e in entries]
            m = sum(scores) / len(scores) if scores else 0
            means[cond] = m
            row += f" {m:.1%} |"

        # Deltas
        row += f" {means['rag'] - means['baseline']:+.1%} |"
        row += f" {means['mcp'] - means['baseline']:+.1%} |"
        row += f" {means['mcp'] - means['rag']:+.1%} |"
        lines.append(row)

    return "\n".join(lines)


def generate_significance_table(results: dict) -> str:
    """Generate statistical significance tests (Table 3).

    Compares pairs: RAG vs Baseline, MCP vs Baseline, MCP vs RAG.
    """
    lines = [
        "| Metric | Comparison | Diff | 95% CI | p (bootstrap) | p (Wilcoxon) | Sig |",
        "|--------|------------|------|--------|---------------|--------------|-----|",
    ]

    comparisons = [
        ("baseline", "rag", "RAG vs Base"),
        ("baseline", "mcp", "MCP vs Base"),
        ("rag", "mcp", "MCP vs RAG"),
    ]

    by_cond = results["by_condition"]

    for metric in ["composite", "pinyin_accuracy", "definition_completeness", "example_authenticity"]:
        for cond_a, cond_b, label in comparisons:
            scores_a = [s[metric] for s in by_cond.get(cond_a, [])]
            scores_b = [s[metric] for s in by_cond.get(cond_b, [])]

            if len(scores_a) != len(scores_b) or not scores_a:
                continue

            boot = paired_bootstrap_test(scores_a, scores_b)
            wilc = wilcoxon_signed_rank(scores_a, scores_b)

            sig = ""
            if boot["p_value"] < 0.001:
                sig = "***"
            elif boot["p_value"] < 0.01:
                sig = "**"
            elif boot["p_value"] < 0.05:
                sig = "*"

            lines.append(
                f"| {_metric_name(metric)} | {label} | "
                f"{boot['observed_diff']:+.3f} | "
                f"[{boot['ci_95_lo']:+.3f}, {boot['ci_95_hi']:+.3f}] | "
                f"{boot['p_value']:.4f} | "
                f"{wilc['p_value']:.4f} | "
                f"{sig} |"
            )

    return "\n".join(lines)


def generate_context_size_table(prompts: list[dict]) -> str:
    """Generate context size comparison (Table 4).

    Shows average RAG vs MCP context sizes by band.
    """
    by_band = defaultdict(list)
    for p in prompts:
        by_band[p.get("band", "unknown")].append(p)

    lines = [
        "| Band | n | Avg RAG (chars) | Avg MCP (chars) | MCP/RAG Ratio |",
        "|------|---|-----------------|-----------------|---------------|",
    ]

    all_rag, all_mcp = [], []
    for band in BANDS:
        entries = by_band.get(band, [])
        if not entries:
            continue

        rag_sizes = [e["rag_context_chars"] for e in entries]
        mcp_sizes = [e["mcp_context_chars"] for e in entries]
        all_rag.extend(rag_sizes)
        all_mcp.extend(mcp_sizes)

        avg_rag = sum(rag_sizes) / len(rag_sizes)
        avg_mcp = sum(mcp_sizes) / len(mcp_sizes)
        ratio = avg_mcp / avg_rag if avg_rag > 0 else 0

        lines.append(
            f"| {band} | {len(entries)} | "
            f"{avg_rag:,.0f} | {avg_mcp:,.0f} | {ratio:.1f}x |"
        )

    # Total row
    if all_rag:
        avg_r = sum(all_rag) / len(all_rag)
        avg_m = sum(all_mcp) / len(all_mcp)
        ratio = avg_m / avg_r if avg_r > 0 else 0
        lines.append(
            f"| **Total** | {len(prompts)} | "
            f"{avg_r:,.0f} | {avg_m:,.0f} | {ratio:.1f}x |"
        )

    return "\n".join(lines)


def generate_error_analysis(results: dict) -> str:
    """Identify headwords where conditions diverge most."""
    lines = ["| Term | Band | Baseline | RAG | MCP | MCP-Base |",
             "|------|------|----------|-----|-----|----------|"]

    scored = []
    for entry in results["scores"]:
        b = entry.get("baseline", {}).get("composite", 0)
        r = entry.get("rag", {}).get("composite", 0)
        m = entry.get("mcp", {}).get("composite", 0)
        scored.append((entry["term"], entry["band"], b, r, m, m - b))

    # Sort by biggest MCP advantage
    scored.sort(key=lambda x: -x[5])

    # Top 10 MCP wins
    lines.append("")
    lines.append("### Biggest MCP Advantages")
    lines.append("| Term | Band | Baseline | RAG | MCP | MCP-Base |")
    lines.append("|------|------|----------|-----|-----|----------|")
    for term, band, b, r, m, delta in scored[:10]:
        lines.append(f"| {term} | {band} | {b:.2f} | {r:.2f} | {m:.2f} | {delta:+.2f} |")

    # Top 10 MCP losses
    lines.append("")
    lines.append("### Biggest MCP Disadvantages")
    lines.append("| Term | Band | Baseline | RAG | MCP | MCP-Base |")
    lines.append("|------|------|----------|-----|-----|----------|")
    for term, band, b, r, m, delta in scored[-10:]:
        lines.append(f"| {term} | {band} | {b:.2f} | {r:.2f} | {m:.2f} | {delta:+.2f} |")

    return "\n".join(lines)


def generate_latex_main_table(results: dict) -> str:
    """Generate LaTeX version of Table 1 for the paper."""
    by_cond = results["by_condition"]

    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Main results: metric scores by condition. Best in \textbf{bold}.}",
        r"\label{tab:main-results}",
        r"\begin{tabular}{lccc}",
        r"\toprule",
        r"Metric & Baseline & RAG & MCP \\",
        r"\midrule",
    ]

    for metric in METRICS:
        row_vals = {}
        for cond in CONDITIONS:
            scores = [s[metric] for s in by_cond.get(cond, [])]
            row_vals[cond] = sum(scores) / len(scores) if scores else 0

        best_cond = max(CONDITIONS, key=lambda c: row_vals[c])

        parts = [_metric_name(metric)]
        for cond in CONDITIONS:
            val = f"{row_vals[cond]:.1%}"
            if cond == best_cond:
                val = r"\textbf{" + val + "}"
            parts.append(val)

        lines.append(" & ".join(parts) + r" \\")

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])

    return "\n".join(lines)


def _metric_name(key: str) -> str:
    """Human-readable metric name."""
    return {
        "pinyin_accuracy": "Pinyin Accuracy",
        "definition_completeness": "Def. Completeness",
        "term_present": "Term Present",
        "example_authenticity": "Example Auth.",
        "composite": "**Composite**",
    }.get(key, key)


# ---------------------------------------------------------------------------
# Summary report
# ---------------------------------------------------------------------------

def generate_full_report(
    responses: list[dict],
    references: list[dict],
    prompts: list[dict],
) -> str:
    """Generate the complete analysis report."""
    results = score_all(responses, references)

    sections = [
        "# Paper C: MCP vs RAG vs Baseline — Analysis Report\n",
        f"**Headwords**: {len(responses)} | "
        f"**Model**: {_extract_model(responses)} | "
        f"**Date**: {_today()}\n",

        "## Table 1: Main Results",
        generate_main_results_table(results),
        "",

        "## Table 2: Per-Band Breakdown (Composite Score)",
        generate_band_breakdown_table(results),
        "",

        "## Table 3: Statistical Significance",
        generate_significance_table(results),
        "",

        "## Table 4: Context Sizes",
        generate_context_size_table(prompts),
        "",

        "## Error Analysis",
        generate_error_analysis(results),
        "",

        "## LaTeX Table 1",
        "```latex",
        generate_latex_main_table(results),
        "```",
    ]

    return "\n".join(sections)


def _extract_model(responses: list[dict]) -> str:
    """Extract model name from first response metadata."""
    for r in responses:
        meta = r.get("response_baseline_meta", {})
        if meta.get("model"):
            return meta["model"]
    return "unknown"


def _today() -> str:
    from datetime import date
    return date.today().isoformat()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.command()
@click.option("--responses", type=click.Path(exists=True), required=True)
@click.option("--references", type=click.Path(exists=True), required=True)
@click.option("--prompts", type=click.Path(exists=True), required=True)
@click.option("--output-dir", default="docs/Projects/paper-c-mcp-vs-rag/tables")
def main(responses: str, references: str, prompts: str, output_dir: str):
    """Generate Paper C analysis report with tables and statistical tests."""
    with open(responses) as f:
        resp_data = json.load(f)
    with open(references) as f:
        ref_data = json.load(f)
    with open(prompts) as f:
        prompt_data = json.load(f)

    click.echo(f"Loaded {len(resp_data)} responses, {len(ref_data)} references")

    # Generate full report
    report = generate_full_report(resp_data, ref_data, prompt_data)

    # Save
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report_path = out_dir / "analysis-report.md"
    with open(report_path, "w") as f:
        f.write(report)
    click.echo(f"\nSaved analysis report to {report_path}")

    # Also save raw scores as JSON for further analysis
    results = score_all(resp_data, ref_data)
    scores_path = out_dir / "scores.json"
    with open(scores_path, "w") as f:
        json.dump(results["scores"], f, ensure_ascii=False, indent=2)
    click.echo(f"Saved raw scores to {scores_path}")

    # Print summary to terminal
    click.echo("\n" + report)


if __name__ == "__main__":
    main()
