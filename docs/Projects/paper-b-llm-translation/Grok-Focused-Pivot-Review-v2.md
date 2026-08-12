# Focused Re-Review — §5.3 English-Pivot Ablation (Paper B v0.9.7)

> **Hand-carry file for grok.com chat window.** Paste this whole file into
> a fresh chat (no system prompt needed), then save Grok's reply to
> `External Reviews/v2-grok-review-5_3-only.md`.

## Context

This is a focused re-review of **just the §5.3 pivot-ablation paragraph** in
Paper B v0.9.7 (Dictionarium Sinicum, ARR October 2026 cycle, targeting
NAACL/COLING 2027 Findings). The v1 round of Fable/Grok/Gemini reviews flagged
that the original n=33-per-language ablation was underpowered. In v0.9.6 we
scaled to n=324 (vi) + n=181 (th), but Thai was blocked mid-run by Groq's
daily 1000-request cap on Llama-3.3-70B. Overnight the cap reset and we
completed Thai to n=324 with full bootstrap 95% CIs recomputed on GPU
(CometKiwi as the reference-free judge).

The Thai finding **materially changed** between v0.9.6 and v0.9.7. In v0.9.6
both language CIs straddled zero. In v0.9.7 Thai's CI is now entirely
negative. Vietnamese is still not distinguishable from zero.

We rewrote the paragraph to reflect the new asymmetry. Please rate:

1. Does the paragraph accurately report the new numbers?
2. Does the interpretation match what the data actually say? (**Pay careful
   attention to the sign convention:** `cometkiwi_delta = direct − pivot`,
   and higher CometKiwi = better. A negative delta means direct scores
   *lower* than pivot.)
3. Is the qualitative story about Sino-Vietnamese vs. Tai-Kadai loanword
   depth a reasonable post-hoc explanation, or is it overreach?
4. Any residual weaknesses (statistical, framing, or otherwise) that
   would still bother a reviewer at ARR October 2026?

Please reply with a **1-page markdown review** headed `# Review:`.

---

## v0.9.6 paragraph (old — for contrast)

> **English-pivot ablation.** On a Vietnamese (n=324) + Thai (n=181)
> ablation using Llama-3.3-70B (open-weight, Groq) with vs. without English
> pivot input, reference-free CometKiwi delta (direct minus pivot) is
> $-0.006$ for Vietnamese (95% bootstrap CI $[-0.020, +0.009]$) and
> $-0.020$ for Thai (95% CI $[-0.040, +0.001]$). Both intervals include
> zero. Symmetric gloss agreement is 61.3% (vi, CI $[56.5\%, 66.1\%]$)
> and 44.1% (th, CI $[38.1\%, 50.0\%]$). At this sample size the
> English pivot neither measurably helps nor hurts translation quality
> for these two target languages; the direction is very slightly toward
> direct translation but the effect is not statistically distinguishable
> from zero. The lower gloss agreement for Thai reflects that pivot and
> direct produce lexically different translations of equal reference-free
> quality, rather than that one is worse than the other.

## v0.9.7 paragraph (new — please review this one)

> **English-pivot ablation.** On a symmetric Vietnamese (n=324) + Thai
> (n=324) ablation using Llama-3.3-70B (open-weight, Groq) with vs.
> without English pivot input, reference-free CometKiwi delta (direct
> minus pivot) is $-0.006$ for Vietnamese (95% bootstrap CI
> $[-0.020, +0.009]$) and $-0.024$ for Thai (95% CI
> $[-0.039, -0.010]$). Symmetric gloss agreement is 61.3% (vi, CI
> $[56.5\%, 66.1\%]$) and 40.8% (th, CI $[36.4\%, 45.3\%]$). The
> Vietnamese interval straddles zero, so a pivot effect is not
> statistically detectable at this sample size; the Thai interval is
> entirely negative, indicating a small but statistically significant
> advantage for direct translation (~0.024 CometKiwi points, roughly
> 5% of the direct score). The pattern is consistent with the intuition
> that a Sino-Vietnamese target absorbs Chinese semantics with less loss
> than a Tai-Kadai target does, so an English intermediate step distorts
> Thai output more than Vietnamese output. The lower Thai gloss agreement
> (40.8% vs. 61.3% for Vietnamese) reinforces this reading: for Thai,
> pivot and direct produce meaningfully different translations, and the
> reference-free score prefers the direct one.

---

## Raw numbers (for your reference)

```
Vietnamese (vi):
  n = 324
  mean_agreement = 0.613
  agreement_ci95 = [0.5649, 0.6605]
  cometkiwi_pivot  = 0.5220
  cometkiwi_direct = 0.5162
  cometkiwi_delta  = -0.0058    (direct - pivot)
  cometkiwi_delta_ci95 = [-0.0201, +0.0091]

Thai (th):
  n = 324
  mean_agreement = 0.408
  agreement_ci95 = [0.3637, 0.4527]
  cometkiwi_pivot  = 0.5217
  cometkiwi_direct = 0.4973
  cometkiwi_delta  = -0.0243    (direct - pivot)
  cometkiwi_delta_ci95 = [-0.0388, -0.0097]
```

Sample seed = 42, per-language target = 450 (stratified by frequency band;
we hit 324 usable pairs per language after filtering). Judge model:
CometKiwi-DA (reference-free, GPU inference, bootstrap over pair-level
scores with 10k resamples).

## Ask

Please reply with a **1-page markdown review** headed `# Review:` covering:

- **Accuracy** — does the paragraph correctly restate the numbers?
- **Interpretation** — does the paragraph's directional claim about Thai
  match a delta CI of [-0.039, -0.010] under the convention
  delta = direct − pivot?
- **Post-hoc explanation** — Sino-Vietnamese vs. Tai-Kadai loanword
  depth: reasonable ARR-defensible framing, or should we cut it?
- **Residual concerns** — anything else a reviewer would still push
  back on at October 2026? (Judge single-model risk, no human eval,
  target language coverage, condition-dependent attrition, etc.)

Thanks!
