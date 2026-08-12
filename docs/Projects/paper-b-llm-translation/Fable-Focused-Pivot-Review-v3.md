# Focused Re-Review — §5.3 English-Pivot Ablation (Paper B v0.9.8 candidate)

> **Package for `claude -p --model claude-fable-5` review.** The v2 Fable
> review caught a sign-inversion in the tagged v0.9.7 §5.3 paragraph.
> This v3 package asks you to independently verify the CORRECTED
> paragraph. Return a short markdown review headed `# Review:`.

## Context

Paper B (Dictionarium Sinicum, ARR October 2026 cycle → NAACL/COLING 2027
Findings) contains an English-pivot ablation in §5.3. The v0.9.7 tagged
release contains a paragraph whose directional interpretation appears to
have the sign backwards.

**Sign convention (verified against source):**
- `eval/eval_pivot_ablation.py:263` defines
  `per_pair_delta = [d - p for p, d in zip(ck_pivot["scores"], ck_direct["scores"])]`
- `eval/eval_pivot_ablation.py:277` defines
  `cometkiwi_delta = ck_direct["system_score"] - ck_pivot["system_score"]`
- Both mean `delta = direct − pivot`.
- CometKiwi: higher = better.
- Therefore: a **negative delta means pivot > direct** (pivot scores higher).

**Measured results (from `eval/results/pivot_ablation.json`):**

```
Vietnamese (vi):
  n = 324
  cometkiwi_pivot  = 0.5220
  cometkiwi_direct = 0.5162
  cometkiwi_delta  = -0.0058    (direct - pivot)
  cometkiwi_delta_ci95 = [-0.0201, +0.0091]   (percentile bootstrap, B=2000)
  mean_agreement = 0.613, agreement_ci95 = [0.5649, 0.6605]

Thai (th):
  n = 324
  cometkiwi_pivot  = 0.5217
  cometkiwi_direct = 0.4973
  cometkiwi_delta  = -0.0243    (direct - pivot)
  cometkiwi_delta_ci95 = [-0.0388, -0.0097]   (percentile bootstrap, B=2000)
  mean_agreement = 0.408, agreement_ci95 = [0.3637, 0.4527]
```

**Verified experiment integrity (post-hoc, from checkpoint files):**
- Both languages have exactly 324 usable pairs.
- The 324 `hw_id`s are identical across languages (intersection=324, symmetric
  difference=0). Both iterate the same sample list drawn once at
  `eval_pivot_ablation.py:158`.
- `empty_direct = 0` and `empty_pivot = 0` for both languages — no
  post-hoc condition-dependent filtering.
- Attrition (324 out of ~448 sampled, ~28%) is caused by
  `eval_pivot_ablation.py:201` dropping headwords without a CC-CEDICT
  English gloss. This filter is upstream of translation and applied
  identically to both languages, so it cannot bias the direct-vs-pivot
  comparison.

## Experiment design (in case v3 is your first look)

Two prompts to the SAME model (Llama-3.3-70B, non-reasoning, open-weight,
via Groq free tier, temperature 0, max_tokens 128) on the SAME 324
headwords per language:

**Direct (Chinese-only prompt):**
```
Chinese: {zh}
{lang_name}: 
```

**Pivot (Chinese + CC-CEDICT English gloss as context):**
```
Chinese: {zh}
English (CC-CEDICT): {en_gloss}
{lang_name}:
```

The English CC-CEDICT gloss is a curated human-authored dictionary entry,
not a machine translation. The Chinese source remains in the prompt.
This is "pivot-as-context," not classical A→MT(en)→MT(B) cascade pivot.

Judge: `Unbabel/wmt22-cometkiwi-da` (reference-free, GPU inference).

## Current committed paragraph (v0.9.7 — the one you flagged in v2)

Direct quote from `dictionarium_sinicum.tex:496`:

> **English-pivot ablation.** On a symmetric Vietnamese (n=324) + Thai
> (n=324) ablation using Llama-3.3-70B (open-weight, Groq) with vs.\
> without English pivot input, reference-free CometKiwi delta (direct
> minus pivot) is $-0.006$ for Vietnamese (95\% bootstrap CI
> $[-0.020, +0.009]$) and $-0.024$ for Thai (95\% CI
> $[-0.039, -0.010]$). Symmetric gloss agreement is 61.3\% (vi, CI
> $[56.5\%, 66.1\%]$) and 40.8\% (th, CI $[36.4\%, 45.3\%]$). The
> Vietnamese interval straddles zero, so a pivot effect is not
> statistically detectable at this sample size; the Thai interval is
> entirely negative, **indicating a small but statistically significant
> advantage for direct translation** (~0.024 CometKiwi points, roughly
> 5\% of the direct score). The pattern is consistent with the intuition
> that a Sino-Vietnamese target absorbs Chinese semantics with less loss
> than a Tai-Kadai target does, so **an English intermediate step distorts
> Thai output more than Vietnamese output**. The lower Thai gloss agreement
> (40.8\% vs.\ 61.3\% for Vietnamese) reinforces this reading: for Thai,
> pivot and direct produce meaningfully different translations, and the
> reference-free score prefers the direct one.

Under the confirmed sign convention `delta = direct − pivot` with higher
CometKiwi = better, a Thai CI entirely below zero means **pivot beats
direct significantly**, which is the opposite of what the paragraph says.

## Proposed rewrite (v0.9.8 candidate — please review)

> **English-pivot ablation.** On a symmetric Vietnamese (n=324) + Thai
> (n=324) ablation using Llama-3.3-70B (open-weight, Groq) with vs.\
> without a CC-CEDICT English gloss provided as additional prompt
> context, reference-free CometKiwi delta (direct minus pivot) is
> $-0.006$ for Vietnamese (95\% bootstrap CI $[-0.020, +0.009]$,
> B=2000) and $-0.024$ for Thai (95\% CI $[-0.039, -0.010]$). Under
> the convention that higher CometKiwi indicates better quality, a
> negative delta means the pivot-context condition scored higher. The
> Vietnamese interval straddles zero, so no pivot effect is
> statistically detectable at this sample size; the Thai interval is
> entirely negative, indicating that for Thai, providing the CC-CEDICT
> English gloss as prompt context alongside the Chinese source produces
> measurably higher-quality Thai output than a Chinese-only prompt
> ($\sim$0.024 CometKiwi points, roughly 5\% of the direct score).
> Symmetric gloss agreement is 61.3\% (vi, CI $[56.5\%, 66.1\%]$) and
> 40.8\% (th, CI $[36.4\%, 45.3\%]$); the lower Thai agreement confirms
> that the two conditions produce lexically distinct translations rather
> than paraphrases, so the CometKiwi preference reflects a genuine quality
> difference. We do not claim a mechanism from two target languages; two
> caveats bound the finding: (i) CometKiwi's training distribution is
> English-heavy, so absolute scores on Thai and Vietnamese carry more
> uncertainty than on high-resource pairs, though within-language
> comparison of the two conditions is symmetric under any such bias;
> and (ii) the ``pivot'' condition here is pivot-as-context (Chinese
> source retained, English gloss added), not the classical
> A$\to$MT(en)$\to$MT(B) cascade to which prior negative pivot-MT
> results apply.

## Ask

Please reply with a **short markdown review** headed `# Review:` covering:

1. **Sign correctness.** Does the proposed rewrite state the direction
   correctly under `delta = direct − pivot`, higher CometKiwi = better,
   for the given Thai CI of $[-0.039, -0.010]$?
2. **Number accuracy.** Any deltas, CIs, or percentages misstated
   relative to the raw numbers above?
3. **Overreach.** The old paragraph offered a Sino-Vietnamese vs.
   Tai-Kadai mechanism story; the rewrite drops it and explicitly says
   "we do not claim a mechanism from two target languages." Is that the
   right call, or is there defensible framing we should keep?
4. **Terminology fix.** The rewrite adds a caveat that this is
   "pivot-as-context" not classical cascade pivot. Necessary, or
   pedantic?
5. **Residual weaknesses** a reviewer at ARR October 2026 would still
   push back on: judge single-model risk (CometKiwi only), no human
   eval, only 2/12 non-community languages covered, attrition, any
   framing issue you notice.

Thanks!
