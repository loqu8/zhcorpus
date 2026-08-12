# Focused Sanity-Check — §5.3 English-Gloss-Context Ablation (Paper B v0.9.8 candidate)

> **Hand-carry / dispatch package.** One shared file for all reviewers.
> - Fable: `cat` this file into `claude -p --model claude-fable-5 --max-turns 10`, save reply to `External Reviews/v4-fable-review-5_3-only.md`.
> - Grok: paste this file into a fresh chat at grok.com, save reply to `External Reviews/v4-grok-review-5_3-only.md`.
> - Gemini: paste this file into a fresh chat at gemini.google.com, save reply to `External Reviews/v4-gemini-review-5_3-only.md`.
>
> **Ask:** confirm the fixes from the v3 review round are correctly incorporated, no NEW errors introduced, and the paragraph is ready to ship as v0.9.8. Reply with a short markdown review headed `# Review:`.

## Context

Paper B (Dictionarium Sinicum, ARR October 2026 → NAACL/COLING 2027 Findings) shipped v0.9.7 with an English-pivot ablation paragraph whose directional interpretation had the sign backwards. The v3 review round (Fable, Grok, Gemini) converged on:

- The rewrite corrects the sign (Thai pivot-context significantly outperforms direct).
- The numbers are all accurate under `delta = direct − pivot` with B=2000 paired bootstrap.
- Dropping the Sino-Vietnamese / Tai-Kadai mechanism story is the right call.
- The "pivot-as-context" terminology caveat is essential, not pedantic.

The v3 rewrite also drew **7 concrete edits** — 5 "must" (definition gap, "paired" wording, softened bias claim, weakened agreement clause, split awkward splice) and 2 "strongly recommended" (rename paragraph header from "English-pivot ablation" to "English-gloss-context ablation"; add attrition/scope disclosure). This v4 candidate incorporates all seven.

## Raw numbers (self-contained; do NOT try to open any files)

```
Sign convention:  delta = direct − pivot-context.  Higher CometKiwi = better.
                  Negative delta ⇒ pivot-context > direct.

Vietnamese (vi):  n = 324
  cometkiwi_pivot         = 0.5220
  cometkiwi_direct        = 0.5162
  cometkiwi_delta         = −0.0058
  cometkiwi_delta_ci95    = [−0.0201, +0.0091]  (percentile paired bootstrap, B=2000)
  mean_agreement          = 0.613
  agreement_ci95          = [0.5649, 0.6605]

Thai (th):        n = 324
  cometkiwi_pivot         = 0.5217
  cometkiwi_direct        = 0.4973
  cometkiwi_delta         = −0.0243
  cometkiwi_delta_ci95    = [−0.0388, −0.0097]  (percentile paired bootstrap, B=2000)
  mean_agreement          = 0.408
  agreement_ci95          = [0.3637, 0.4527]

Design: same model (Llama-3.3-70B, non-reasoning, open-weight, Groq, temp=0,
max_tokens=128) run on the SAME 324 headwords per language. Sample drawn
once, iterated per language, so both conditions and both languages see
identical hw_id sets (intersection = 324, symmetric difference = 0).
Attrition (324 out of ~448 stratified samples per language, ~28%) is
caused by an upstream filter that drops headwords lacking a CC-CEDICT
English gloss; applied identically to both languages and both conditions,
so it cannot bias the direct-vs-pivot-context comparison.

Judge:  Unbabel/wmt22-cometkiwi-da  (reference-free, GPU inference).
```

## Prompts (unchanged since v3)

**Direct (Chinese-only):**
```
Chinese: {zh}
{lang_name}:
```

**Pivot-context (Chinese + CC-CEDICT English gloss added):**
```
Chinese: {zh}
English (CC-CEDICT): {en_gloss}
{lang_name}:
```

The English CC-CEDICT gloss is a human-curated dictionary entry, not a machine translation. The Chinese source stays in the prompt. This is *pivot-as-context*, not the classical A→MT(en)→MT(B) cascade.

## v0.9.7 paragraph (shipped, with the sign inversion)

Quoted for contrast; the phrases in **bold** are the sign inversion the v2/v3 rounds flagged:

> **English-pivot ablation.** On a symmetric Vietnamese (n=324) + Thai (n=324) ablation using Llama-3.3-70B (open-weight, Groq) with vs. without English pivot input, reference-free CometKiwi delta (direct minus pivot) is −0.006 for Vietnamese (95% bootstrap CI [−0.020, +0.009]) and −0.024 for Thai (95% CI [−0.039, −0.010]). Symmetric gloss agreement is 61.3% (vi, CI [56.5%, 66.1%]) and 40.8% (th, CI [36.4%, 45.3%]). The Vietnamese interval straddles zero, so a pivot effect is not statistically detectable at this sample size; the Thai interval is entirely negative, **indicating a small but statistically significant advantage for direct translation** (∼0.024 CometKiwi points, roughly 5% of the direct score). The pattern is consistent with the intuition that a Sino-Vietnamese target absorbs Chinese semantics with less loss than a Tai-Kadai target does, so **an English intermediate step distorts Thai output more than Vietnamese output**. The lower Thai gloss agreement (40.8% vs. 61.3% for Vietnamese) reinforces this reading: for Thai, pivot and direct produce meaningfully different translations, and the reference-free score prefers the direct one.

## v0.9.8 candidate (please review THIS)

```latex
\paragraph{English-gloss-context ablation.} We compare two prompts to the
same model (Llama-3.3-70B, open-weight, via Groq): \textit{direct}, a
Chinese-only prompt; and \textit{pivot-context}, a prompt that adds the
CC-CEDICT English gloss alongside the Chinese source. On a symmetric
Vietnamese (n=324) + Thai (n=324) sample drawn from headwords with
CC-CEDICT English glosses (324 of $\sim$448 stratified samples per
language), the reference-free CometKiwi delta (direct minus pivot-context)
is $-0.006$ for Vietnamese (95\% paired-bootstrap CI $[-0.020, +0.009]$,
B=2000) and $-0.024$ for Thai (95\% CI $[-0.039, -0.010]$). Under the
convention that higher CometKiwi indicates better quality, a negative
delta means the pivot-context condition scored higher. The Vietnamese
interval straddles zero, so no effect is statistically detectable at
this sample size; the Thai interval is entirely negative, indicating
that for Thai, adding the CC-CEDICT English gloss as prompt context
alongside the Chinese source produces measurably higher-quality Thai
output than a Chinese-only prompt ($\sim$0.024 CometKiwi points,
roughly 5\% of the direct score). Symmetric gloss agreement is 61.3\%
(vi, CI $[56.5\%, 66.1\%]$) and 40.8\% (th, CI $[36.4\%, 45.3\%]$);
the lower Thai agreement rules out the delta being noise between
near-identical outputs, since the two conditions produce lexically
distinct translations, though the quality preference itself rests on
CometKiwi. We do not claim a mechanism from two target languages. Two
caveats bound the finding: (i)~CometKiwi's training distribution is
English-heavy, so absolute scores on Thai and Vietnamese carry more
uncertainty than on high-resource pairs; the within-language contrast
should largely cancel any such bias, but the cancellation is not exact
if bias interacts with output length or register; and (ii)~the ``pivot''
condition here is pivot-as-context (Chinese source retained, English
gloss added), not the classical A$\to$MT(en)$\to$MT(B) cascade to which
prior negative pivot-MT results apply.
```

## Change checklist (what v0.9.8 incorporates from v3 reviews)

| # | Fix | Where in the v0.9.8 paragraph |
|---|-----|-------------------------------|
| 1 | Paragraph heading renamed from "English-pivot ablation" to "English-gloss-context ablation" | `\paragraph{...}` |
| 2 | Terms *direct* and *pivot-context* defined at the start | first sentence |
| 3 | Attrition/scope disclosed: "324 of ~448 stratified samples per language" | second sentence |
| 4 | "paired-bootstrap" labeled explicitly, B=2000 named | second sentence, both CIs |
| 5 | Agreement inference weakened: "rules out the delta being noise between near-identical outputs... though the quality preference itself rests on CometKiwi" | agreement clause |
| 6 | Awkward splice split into two sentences: "We do not claim a mechanism from two target languages. Two caveats bound the finding:" | mid-paragraph |
| 7 | Bias-symmetry claim softened: "should largely cancel any such bias, but the cancellation is not exact if bias interacts with output length or register" | caveat (i) |

## Ask

Please reply with a **short markdown review** headed `# Review:` covering:

1. **Fix incorporation.** For each of the 7 items in the checklist, does the v0.9.8 paragraph actually contain the fix, and is the fix correctly expressed?
2. **New errors.** Did any of the edits introduce a NEW error (numeric, directional, or logical)?
3. **Reading flow.** The paragraph is longer than v0.9.7. Is it still readable at ARR-review pace, or should any sentences be tightened?
4. **Ship gate.** Is this paragraph ready to ship as v0.9.8, or is there a residual issue that would justify one more round?
5. **Anything else** a reviewer would still push back on that the earlier rounds missed.

Thanks!
