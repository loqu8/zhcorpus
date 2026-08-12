The committed tex at `dictionarium_sinicum.tex:496` matches the package's quote exactly (I could not re-open `eval/eval_pivot_ablation.py` or the results JSON — they're outside this session's allowed working directory — so I take the package's line-verified sign convention as given, noting it was independently confirmed in the v2 round). Here is the review:

---

# Review: §5.3 English-Pivot Ablation Rewrite (v0.9.8 candidate)

## 1. Sign correctness — CORRECT

Under `delta = direct − pivot` with higher CometKiwi = better: Thai direct (0.4973) minus Thai pivot (0.5217) = −0.0243, and the CI $[-0.039, -0.010]$ lies entirely below zero. That means direct scores significantly *lower* than pivot-context. The rewrite's claim — "providing the CC-CEDICT English gloss as prompt context … produces measurably higher-quality Thai output" — states the direction correctly. The v0.9.7 paragraph is indeed inverted and must not ship.

One clarity gap: the rewrite still reports "delta (direct minus pivot)" but never defines which condition is "direct" and which is "pivot" in the new wording. Add a half-sentence: *direct = Chinese-only prompt; pivot = Chinese + CC-CEDICT gloss*. Without it, the sign convention sentence does extra work the term definitions should do.

## 2. Number accuracy — ALL CHECK OUT

- vi delta −0.0058 → −0.006 ✓; CI [−0.0201, +0.0091] → [−0.020, +0.009] ✓
- th delta −0.0243 → −0.024 ✓; CI [−0.0388, −0.0097] → [−0.039, −0.010] ✓
- Agreement 61.3% [56.5, 66.1] and 40.8% [36.4, 45.3] ✓
- "Roughly 5% of the direct score": 0.0243 / 0.4973 = 4.9% ✓

Suggest adding "paired" before "bootstrap": `per_pair_delta` is computed per headword, so this is a paired bootstrap — a stronger design than unpaired, and reviewers will want to know which it is.

## 3. Overreach — dropping the mechanism is the right call

Yes, drop it. The Sino-Vietnamese/Tai-Kadai story was fitted to the *wrong* sign — a mechanism flexible enough to explain either direction explains neither, and with n=2 target languages any family-level claim is unfalsifiable. The explicit "we do not claim a mechanism" sentence is good ARR hygiene.

Note also that the corrected sign is a *better* story for this paper: "a curated dictionary gloss as context improves LLM translation output" aligns directly with the paper's dictionary-as-resource thesis, whereas the old (inverted) reading undercut it. If you want any interpretive gesture at all, one hedged sentence — e.g., "one plausible reading is that the curated gloss disambiguates polysemous headwords, with more headroom where the model's direct quality is lower" — is defensible as an explicitly labeled hypothesis. But the paragraph is fine without it.

## 4. Terminology caveat — necessary, and consider going further

The pivot-as-context caveat is necessary, not pedantic. Prior negative results on pivoting (cascade A→en→B) are about information *loss* through a bottleneck; this design *adds* information and removes nothing. Without the caveat, reviewers will map "pivot" onto the cascade literature and object that the experiment doesn't test what its name says. Consider renaming the paragraph heading itself — "English-gloss-context ablation" or similar — since keeping "English-pivot ablation" as the bolded label invites exactly the misreading the mid-paragraph caveat tries to prevent.

## 5. Residual weaknesses a reviewer will still raise

1. **"Symmetric under any such bias" is too strong.** Caveat (i) assumes judge bias cancels within-language, but bias can interact with condition: gloss-conditioned outputs may differ systematically in length, register, or English leakage, and CometKiwi's response to those properties need not be neutral. Soften to "should largely cancel" — or better, add a second QE metric on the same 648 outputs.
2. **No output-language sanity check.** The pivot prompt contains English; nothing reported rules out code-switched or partially English output, on which CometKiwi behavior is unpredictable. A language-ID pass over all outputs is cheap and closes this hole.
3. **No human eval.** Even a 50-item spot check on the Thai pairs would materially strengthen the significant finding. Expect this request from at least one reviewer.
4. **Agreement inference slightly overreaches.** Low agreement shows the two conditions produce *lexically distinct* strings — it rules out the delta being noise between near-identical outputs, but it cannot certify a "genuine quality difference," which still rests entirely on CometKiwi. Reword the clause to the weaker, correct claim.
5. **Scope.** 2 of 12 non-community languages; and attrition means the population is "headwords with CC-CEDICT English glosses" (324/~448). That's the right population for this paper's use case, but the tex should say so — currently the attrition is invisible.
6. Minor: "We do not claim a mechanism from two target languages; two caveats bound the finding:" is an awkward splice — break into two sentences.

**Verdict:** the rewrite is correct on sign and numbers and is a clear improvement. Fix the direct/pivot definition gap, soften caveat (i) and the agreement clause, add "paired," and consider the heading rename. Items 2–3 are the highest-value cheap additions before submission.
