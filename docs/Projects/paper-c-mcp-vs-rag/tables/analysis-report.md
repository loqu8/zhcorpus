# Paper C: MCP vs RAG vs Baseline — Analysis Report

**Headwords**: 5 | **Model**: MiniMax-M2.5 | **Date**: 2026-03-02

## Table 1: Main Results
| Metric | Baseline | RAG | MCP |
|--------|----------|-----|-----|
| Pinyin Accuracy | 20.0% | 40.0% | 60.0% |
| Def. Completeness | 86.7% | 93.3% | 93.3% |
| Term Present | 100.0% | 100.0% | 100.0% |
| Example Auth. | 100.0% | 100.0% | 100.0% |
| **Composite** | 76.7% | 83.3% | 88.3% |

## Table 2: Per-Band Breakdown (Composite Score)
| Band | n | Baseline | RAG | MCP | RAG-Base | MCP-Base | MCP-RAG |
|------|---|----------|-----|-----|----------|----------|---------|
| high | 5 | 76.7% | 83.3% | 88.3% | +6.7% | +11.7% | +5.0% |

## Table 3: Statistical Significance
| Metric | Comparison | Diff | 95% CI | p (bootstrap) | p (Wilcoxon) | Sig |
|--------|------------|------|--------|---------------|--------------|-----|
| **Composite** | RAG vs Base | +0.067 | [+0.000, +0.167] | 0.1612 | nan |  |
| **Composite** | MCP vs Base | +0.117 | [+0.017, +0.217] | 0.0176 | nan | * |
| **Composite** | MCP vs RAG | +0.050 | [+0.000, +0.150] | 0.6378 | nan |  |
| Pinyin Accuracy | RAG vs Base | +0.200 | [+0.000, +0.600] | 0.6588 | nan |  |
| Pinyin Accuracy | MCP vs Base | +0.400 | [+0.000, +0.800] | 0.1446 | nan |  |
| Pinyin Accuracy | MCP vs RAG | +0.200 | [+0.000, +0.600] | 0.6378 | nan |  |
| Def. Completeness | RAG vs Base | +0.067 | [+0.000, +0.200] | 0.6454 | nan |  |
| Def. Completeness | MCP vs Base | +0.067 | [+0.000, +0.200] | 0.6454 | nan |  |
| Def. Completeness | MCP vs RAG | +0.000 | [+0.000, +0.000] | 1.0000 | 1.0000 |  |
| Example Auth. | RAG vs Base | +0.000 | [+0.000, +0.000] | 1.0000 | 1.0000 |  |
| Example Auth. | MCP vs Base | +0.000 | [+0.000, +0.000] | 1.0000 | 1.0000 |  |
| Example Auth. | MCP vs RAG | +0.000 | [+0.000, +0.000] | 1.0000 | 1.0000 |  |

## Table 4: Context Sizes
| Band | n | Avg RAG (chars) | Avg MCP (chars) | MCP/RAG Ratio |
|------|---|-----------------|-----------------|---------------|
| high | 2 | 1,827 | 3,304 | 1.8x |
| mid | 2 | 513 | 1,930 | 3.8x |
| low | 2 | 1,361 | 3,018 | 2.2x |
| rare | 2 | 1,140 | 2,346 | 2.1x |
| **Total** | 8 | 1,210 | 2,650 | 2.2x |

## Error Analysis
| Term | Band | Baseline | RAG | MCP | MCP-Base |
|------|------|----------|-----|-----|----------|

### Biggest MCP Advantages
| Term | Band | Baseline | RAG | MCP | MCP-Base |
|------|------|----------|-----|-----|----------|
| 学校 | high | 0.75 | 1.00 | 1.00 | +0.25 |
| 人工流产 | high | 0.67 | 0.67 | 0.92 | +0.25 |
| 癌 | high | 0.92 | 1.00 | 1.00 | +0.08 |
| 子公司 | high | 0.75 | 0.75 | 0.75 | +0.00 |
| 踏板摩托车 | high | 0.75 | 0.75 | 0.75 | +0.00 |

### Biggest MCP Disadvantages
| Term | Band | Baseline | RAG | MCP | MCP-Base |
|------|------|----------|-----|-----|----------|
| 学校 | high | 0.75 | 1.00 | 1.00 | +0.25 |
| 人工流产 | high | 0.67 | 0.67 | 0.92 | +0.25 |
| 癌 | high | 0.92 | 1.00 | 1.00 | +0.08 |
| 子公司 | high | 0.75 | 0.75 | 0.75 | +0.00 |
| 踏板摩托车 | high | 0.75 | 0.75 | 0.75 | +0.00 |

## LaTeX Table 1
```latex
\begin{table}[t]
\centering
\caption{Main results: metric scores by condition. Best in \textbf{bold}.}
\label{tab:main-results}
\begin{tabular}{lccc}
\toprule
Metric & Baseline & RAG & MCP \\
\midrule
Pinyin Accuracy & 20.0% & 40.0% & \textbf{60.0%} \\
Def. Completeness & 86.7% & \textbf{93.3%} & 93.3% \\
Term Present & \textbf{100.0%} & 100.0% & 100.0% \\
Example Auth. & \textbf{100.0%} & 100.0% & 100.0% \\
**Composite** & 76.7% & 83.3% & \textbf{88.3%} \\
\bottomrule
\end{tabular}
\end{table}
```