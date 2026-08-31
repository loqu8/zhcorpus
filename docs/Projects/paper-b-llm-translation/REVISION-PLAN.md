# Dictionarium Sinicum — Revision Plan for Next ARR Cycle
**Written:** 2026-08-10
**Based on:** ARR March 2026 reviews (see `reviews/`)
**Target:** ARR October 2026 cycle → commit to NAACL 2027 or COLING 2027 (Findings track)

---

## Timing Situation

We missed two windows already:
- ❌ ARR August 2026 cycle: submission deadline was **August 3** (missed by 1 week — today is Aug 10)
- ❌ EMNLP 2026 / AACL 2026 commit: was **August 2, 2026**
- ❌ EACL 2027 commit path: required ARR August 2026 submission (missed)

**Next viable window:**

| Cycle | Submission | Meta-review | Commit-to venues |
|---|---|---|---|
| **ARR October 2026** | **Oct 12, 2026** (9 weeks 2 days from today) | Dec 20 | **NAACL 2027, COLING 2027** |
| ARR (Jan 2027) | ~Jan 2027 | ~Mar 2027 | ACL 2027 |

**Target: October 12, 2026 submission** — enough runway for the fixes below plus writing/QA cycles.

---

## Fix List — Ranked by Score-Per-Hour

### Tier 1: High-impact, low-effort (do first, weeks 1–2)

| # | Fix | Effort | Reviewer objection killed | Est. score delta |
|---|---|---|---|---|
| 1 | **Publish the code repo publicly** — GitHub, MIT/Apache, README with quickstart, docker-compose if applicable | 1–2 days | gKVr Software: 1, cky5 Software: 1 → both jump to ≥3 | +0.3 overall |
| 2 | **Fix PDF hyphenation glitches** (SamJ typo list) — LaTeX `\hyphenation{}`, `microtype` package, manual `\-` for long CJK-adjacent words | 1 day | SamJ cosmetic list | Removes "sloppy" impression |
| 3 | **Add COMET + BERTScore columns** to Tables 2–4 alongside existing sense-coverage — reuse the same 100-entry eval set | 2–3 days | SamJ metric criticism, gKVr "limited eval scope" | Directly answers a specific ask |

### Tier 2: Medium-effort, kills the biggest meta-review objection (weeks 2–4)

| # | Fix | Effort | Reviewer objection killed |
|---|---|---|---|
| 4 | **Add one open-weight model comparison** — pick ONE of Qwen2.5-72B-Instruct, Aya-Expanse-32B, or Llama-3.3-70B. Run the same pipeline on a 3-language subset (e.g., de/es/id — cover Romance, Germanic, low-resource). Report cost, coverage, contamination rate side-by-side with MiniMax M2.5 | 1 week | **AC's #1 objection**, gKVr "single proprietary model", SamJ "reproducibility" |
| 5 | **English-pivot ablation** — pick 2 non-reference languages (e.g., Vietnamese, Thai). Run: (A) current English-pivoted, (B) direct Chinese→target. Report sense agreement, native-speaker preference on 50 entries each | 4–5 days | AC pivot criticism, gKVr Anglocentric bias, SamJ semantic loss |
| 6 | **Per-language error taxonomy** in §5 — new subsection with a table: for each of 18 langs, break down error types (script contamination, sense compression, hallucination, missing sense, register drift). Use existing pipeline outputs — this is analysis, not new experiments | 3 days | AC error analysis, gKVr per-language breakdown, cky5 hallucination analysis |

### Tier 3: The one that costs real money and time (weeks 3–5, parallel with Tier 2)

| # | Fix | Effort | Reviewer objection killed |
|---|---|---|---|
| 7 | **Native-speaker human evaluation** — hire via Prolific / Upwork. Target: 3–5 languages × 100 entries × 2 annotators = 600–1000 annotations. Score axes: accuracy (1–5), naturalness (1–5), completeness (1–5). Budget: $500–$1,500. Prioritize: (a) 1 European (de or fr), (b) 1 Asian non-CJK (id, vi, or th), (c) 1 low-resource-ish (fa or hi). Report inter-annotator agreement | 2–3 weeks wall-clock, ~4 days our effort | gKVr "restricted to LLM judges", SamJ "small-scale human eval", cky5 "human evaluation of definitions", **AC direct ask** |

### Tier 4: Optional / stretch (only if Tier 1–3 finish early)

| # | Fix | Effort | Reviewer objection killed |
|---|---|---|---|
| 8 | **Second-model verification for backfill** (SamJ suggestion) — re-run the 12 no-reference-language backfill through a second model (e.g., Claude Sonnet), report divergence rate | 3 days | SamJ specific suggestion |
| 9 | **Sense-discrimination pass** for polysemous headwords — WSD-style tagging for top-5000 most-frequent polysemous entries | 1 week | gKVr "glosses vs full definitions", "median 2 vs 3 senses" |
| 10 | **Grammatical info** (POS, gender, aspect) — extract from source dictionaries where available, generate for target langs | 4 days | gKVr "grammatical information absent" |

---

## Cross-Cutting Writing Tasks (weeks 5–6)

- Rewrite §1 (Intro) to lead with the **resource contribution** (Datasets: 4.33 was your highest score) and downplay the "novel LLM pipeline" framing (Excitement: 3.17 was your ceiling)
- Add subsection: "**Limitations and Reproducibility**" — explicitly document the model choice, pivot strategy, and human-eval scope, so reviewers can't ding you for what you already acknowledge
- Cover-letter equivalent for ARR: no explicit response letter, but the revision itself should visibly address every meta-review point in a "Response to March 2026 reviewers" appendix (allowed in ARR)

## Venue Framing

- **First-choice commit target: Findings of NAACL 2027 or COLING 2027**
- Do NOT commit to a main track unless post-revision scores lift to 4.0+ average
- Parallel prep: **LREV journal submission** — same fixes, ~30% longer, no deadline pressure. Resource papers are LREV's core, no conceptual-novelty bar. Submit ~2 weeks after the ARR October push.

## Handoff to New Session

Open a fresh Claude Code session with cwd `~/Projects/loqu8/zhcorpus/`. Point it here:

```
Read docs/Projects/paper-b-llm-translation/REVISION-PLAN.md and the reviews under
docs/Projects/paper-b-llm-translation/reviews/. Target: ARR October 2026 (Oct 12
submission). Start with Tier 1 item #1 (publish code repo).
```

The paper source is `docs/Projects/paper-b-llm-translation/dictionarium_sinicum.tex`.
The Markdown draft is `docs/Projects/paper-b-llm-translation/draft.md`.
Existing eval scripts are in `docs/Projects/paper-b-llm-translation/supplementary/`.

---

## Status + ARR timing (added 2026-08-31)

**Status:** writing complete. All reviewer requests addressed EXCEPT Tier 7 (native-speaker human
evaluation) — the remaining gap is exactly the AC's direct ask, echoed by all three reviewers
(gKVr "restricted to LLM judges", SamJ "small-scale human eval", cky5 "human evaluation of
definitions") and the meta-review.

**ARR October 2026 timing (verified 2026-08-31 vs aclrollingreview.org/dates):**
- Submission deadline: **October 12, 2026** → NAACL 2027 / COLING 2027, commitment Dec 20.
- The October form is NOT yet open (cycle details TBA). ARR's standard pattern opens the
  OpenReview form ~2 weeks before deadline → expect **~late September**; effectively the window
  is the first ~2 weeks of October.
- Submit as an ARR **revision linked to forum sVPHR4PSzR** (resubmission with response letter),
  not a fresh submission.
- **Fallback on the table:** existing completed reviews can be committed directly to
  **EACL 2027 (commitment deadline Oct 11)** with no new review cycle — only worth it if the
  revision slips; the revised paper is stronger than the reviewed one.

**Recommendation (2026-08-31): run Tier 7 NOW, in the 6-week window.**
1. Wall-clock fits: 2–3 weeks recruitment/annotation vs 6 weeks of runway — but only if
   recruitment starts THIS WEEK (Prolific/Upwork posting is the long pole, ~4 days of our effort).
2. Skipping the one thing every reviewer + the AC asked for, on a resubmission likely seen by
   overlapping reviewers, is the classic way a revision gets dinged a second time. The rest of
   the revision is strong; this is the credibility anchor.
3. Scope to the plan's minimum: 3 languages (de, id, fa/hi) × 100 entries × 2 annotators,
   accuracy/naturalness/completeness 1–5, report IAA. Budget $500–$1,500.
4. Degrade gracefully: if only 2 languages complete by Oct 12, ship those + state the third in
   Limitations ("in progress; full set in the LREV version"). Partial human eval with IAA still
   converts every "no human eval" objection into a scoping quibble.
5. LREV parallel (~2 weeks after the ARR push) gets the completed full set either way.

---

## DECISION (Tim, 2026-08-31): Tier 7 human evaluation is CUT — no paid annotation

Ruled out on budget ($500–$1,500 not happening). The recommendation above is superseded.
Zero-cost mitigation plan instead:

1. **LLM-jury with agreement stats (~$0, 2–3 days).** Replace the single LLM judge with a
   3–5 model panel on the SAME 100-entry sets (free/subscription models via model-radar —
   e.g., one Qwen, one Llama, one Gemini/Claude leg), report inter-judge agreement the way
   human IAA would be reported, plus disagreement analysis. Directly blunts gKVr's
   "LLM-judge bias/reliability" — bias is the objection, and a jury with measured agreement
   is the standard no-human answer to it.
2. **Tier 8 second-model backfill verification (~$0, ~3 days)** — SamJ's own suggested
   alternative; run the 12 no-reference-language backfill through a second model, report
   divergence. Do it; it was optional only because Tier 7 existed.
3. **Volunteer micro-eval IF free (0 days our effort):** if any native speakers in the
   Loqu8/community orbit will score 25–50 entries in 1–2 languages unpaid, include it as a
   "small-scale human spot-check" (SamJ asked for exactly "small-scale... at least one
   language"). If nobody volunteers, skip — do not pay.
4. **Own the gap in writing:** Limitations states plainly that evaluation is automatic +
   LLM-jury, scoped by resource constraints; the response letter answers the human-eval asks
   with items 1–2 above rather than silence. Reviewers punish evasion more than honest scope.
5. Venue posture unchanged: Findings-track + LREV are resource-paper-friendly; a
   dictionary resource with airtight automatic eval + jury agreement is committable there.
