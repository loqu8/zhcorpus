# ARR March 2026 — Review Summary
**Paper:** Dictionarium Sinicum (Submission #513)
**Fetched:** 2026-08-10 from https://openreview.net/forum?id=sVPHR4PSzR

## Scores

| Metric | gKVr | SamJ | cky5 | Avg |
|---|---|---|---|---|
| Overall Assessment | 3.5 (Borderline) | 3 (Findings) | 3.5 (Borderline) | **3.33** |
| Confidence | 3 | 3 | 4 | 3.33 |
| Soundness | 4 | 4 | 3 | 3.67 |
| Excitement | 3 | 3 | 3.5 | 3.17 |
| Reproducibility | 4 | 3 | 4 | 3.67 |
| **Datasets** | 4 | **5 (Enabling)** | 4 | **4.33** |
| **Software** | **1** | 3 | **1** | **1.67** |

**Meta-review (AC zfRe): 3.5 = Borderline Conference, "No Recommendation"**

## The Story the Numbers Tell

- **Soundness 3.67, Datasets 4.33** — the paper is technically fine and the resource is genuinely valued
- **Excitement 3.17** — reviewers found it "interesting" but not exciting; novelty read as engineering, not conceptual
- **Software 1.67** — TWO reviewers gave literal 1 = "No usable software released." This is the single biggest own-goal in the numbers, and it's the easiest to fix.

## Consistent Criticisms (all three reviewers + AC agree)

1. **Single closed-source model** (MiniMax M2.5). Everyone wants an open-weight comparison.
2. **Engineering not conceptual novelty** — this is the ceiling on excitement.
3. **Human evaluation missing** — LLM-judge over 100 entries isn't enough; need native speakers.
4. **English pivot** for 12 languages — Anglocentric bias unmeasured.
5. **Better metrics beyond lexical overlap** — COMET / BERTScore.
6. **Per-language error breakdown missing.**

## Cleanly Actionable Fixes (weeks, not months)

| Fix | Effort | Reviewer objection killed |
|---|---|---|
| **Release the code repo publicly** | 1 day | Software: 1 → 4+ (huge score jump) |
| **Rerun pipeline with 1 open-weight model** (Qwen2.5-72B or Aya-Expanse) on a subset for comparison | 1 week | Single-proprietary-model criticism |
| **Native-speaker human eval on 3–5 languages, 100 entries each** (Fiverr / Prolific ~$500) | 2 weeks | Human eval gap |
| **Add COMET or BERTScore column** to Tables 2–4 | 2 days | Metric criticism |
| **Per-language error taxonomy table** in §5 | 3 days | Error analysis gap |
| **English-pivot ablation** on 2 languages (direct-from-Chinese vs pivot) | 4 days | Anglocentric bias |
| Fix hyphenation glitches / PDF layout | 1 day | Cosmetic |

Total: ~4-6 focused weeks to a substantially stronger paper.

## Ceiling

Excitement of 3.17 is real — this is a resource paper, not a modeling breakthrough, and no amount of rework changes that. So the ceiling is:
- **Findings of ACL / EMNLP** (very achievable with the fixes above)
- **ACL/EMNLP main** (possible but requires the excitement to move; unlikely on this topic)
- **LREV journal** (Language Resources and Evaluation, Springer) — best natural fit; resource papers are the whole point of the venue and it rewards exactly the strengths reviewers noted (Datasets: Enabling)
- **LREC-COLING 2026** — resource-friendly venue

## Recommendation

**Two-track:**
1. **Revise + resubmit to next ARR cycle** targeting Findings-EMNLP (fixes above, then commit)
2. **In parallel, prep for LREV journal submission** — same fixes, longer format, no conference deadline pressure

The overlap in prep work is ~90%. Do the fixes once, submit to both tracks.
