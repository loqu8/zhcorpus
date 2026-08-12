# Review: §5.3 English-Pivot Ablation (v0.9.7)

## Summary verdict

The numbers are transcribed faithfully, but the paragraph contains a **sign-interpretation error that inverts the paper's central claim for Thai**. This must be fixed before anything else in the paragraph matters.

## Accuracy — one critical error

**The delta is defined as direct − pivot, and it is negative.** Thai: `cometkiwi_direct = 0.4973`, `cometkiwi_pivot = 0.5217`, so direct − pivot = −0.0244. A CI of [−0.039, −0.010] entirely below zero means **direct scores significantly *lower* than pivot** — the English pivot *helps* Thai. The paragraph claims the opposite: "a small but statistically significant advantage for direct translation." The downstream sentences compound it ("an English intermediate step distorts Thai output more," "the reference-free score prefers the direct one"). Note the v0.9.6 paragraph had the same inversion ("the direction is very slightly toward direct translation") — it just didn't matter then because the CIs straddled zero.

All rounding is otherwise correct: −0.0058 → −0.006; [−0.0201, +0.0091] → [−0.020, +0.009]; −0.0243 → −0.024; [−0.0388, −0.0097] → [−0.039, −0.010]; both agreement CIs check out. The "~5% of the direct score" arithmetic is right (0.0243/0.4973 ≈ 4.9%), but see below.

## Interpretation

Once the sign is corrected, "small but statistically significant" is a fair characterization of [−0.039, −0.010] — the CI excludes zero comfortably rather than grazing it. Two caveats:

- **"~5% of direct score" is a weak effect-size frame.** CometKiwi is not a ratio scale; percent-of-mean is not meaningful. Contextualize against the pair-level standard deviation (Cohen's-d-style) or against deltas known to correspond to human-perceptible quality differences in the QE literature.
- Say "the 95% CI excludes zero" rather than bare "statistically significant," and note no multiple-comparison correction across the four intervals reported.

## Post-hoc explanation — must be rewritten, and then hedged

The Sino-Vietnamese/Tai-Kadai story is currently argued in the wrong direction. The corrected finding — *pivot helps Thai but is a wash for Vietnamese* — actually supports a coherent flipped version: direct zh→vi transfer works because Sino-Vietnamese vocabulary gives the model a low-loss path, while zh→th benefits from English scaffolding. That is defensible **as an explicitly labeled post-hoc hypothesis**, but a reviewer will immediately offer a rival explanation you should name: Llama-3.3's training data almost certainly contains far more en–th than zh–th parallel/comparable text, so this could be a data-availability effect, not a typological one. Present both, or cut the story to one hedged sentence.

## Residual concerns for October

1. **Judge confound (the big one).** CometKiwi-DA is trained predominantly on English-centric pairs, and pivot outputs are generated *through* English — the judge may systematically prefer English-mediated translationese. This confound runs in exactly the direction of your Thai result. A second judge (e.g., XCOMET or an LLM judge) or a small human check on ~50 Thai pairs would defuse it cheaply.
2. **Condition-dependent attrition.** 126/450 (28%) filtered per language, including "empty direct outputs" — dropping pairs where one condition failed biases the comparison and, worse, hides that direct zh→th sometimes fails outright (itself a finding). Report attrition per condition.
3. **Suspicious n symmetry.** Exactly 324 usable pairs in both languages after independent filtering is improbable; if Thai was truncated to match Vietnamese, disclose how.
4. Single model (one 70B), single judge, two languages — fine for an ablation, but the prose should scope the claim accordingly.

**Bottom line:** fix the sign inversion, rewrite the interpretation and the loanword story in the corrected direction with a training-data alternative acknowledged, and address the judge-confound and attrition points. As written, the paragraph would be caught by any careful reviewer — the raw numbers are printed right next to the inverted claim.
