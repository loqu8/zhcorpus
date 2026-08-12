# Review:

### 1. Fix Incorporation

All 7 items from the change checklist are accurately incorporated into the v0.9.8 candidate paragraph:

* **Item 1 (Heading Rename):** Correctly updated to `\paragraph{English-gloss-context ablation.}`.
* **Item 2 (Term Definitions):** *Direct* (Chinese-only) and *pivot-context* (adding CC-CEDICT English gloss) are explicitly defined in the opening sentence.
* **Item 3 (Attrition/Scope Disclosure):** Explicitly states "324 of $\sim$448 stratified samples per language".
* **Item 4 (Bootstrap & $B$ value):** Explicitly labeled as `95\% paired-bootstrap` with `B=2000`.
* **Item 5 (Agreement Inference):** Correctly softened to state that agreement rules out noise between near-identical outputs while noting the quality preference rests on CometKiwi.
* **Item 6 (Splice Fix):** Split into two clean, direct sentences ("We do not claim a mechanism... Two caveats bound the finding:").
* **Item 7 (Bias Softening):** Softened appropriately under caveat (i) to acknowledge potential interactions with output length or register.

---

### 2. New Errors

* **Numeric Accuracy:** All reported values and confidence intervals match the raw numbers rounded appropriately (Vietnamese $\Delta = -0.006$ with CI $[-0.020, +0.009]$; Thai $\Delta = -0.024$ with CI $[-0.039, -0.010]$; Agreements at $61.3\%$ and $40.8\%$).
* **Directionality:** The sign convention ($\Delta = \text{direct} - \text{pivot-context}$) is explicitly explained. The logic correctly concludes that a negative delta indicates superior quality for the `pivot-context` condition.
* **Logical Consistency:** No new errors were introduced by the edits.

---

### 3. Reading Flow

The paragraph is denser than v0.9.7, but the structure remains logical and easy to navigate for an ARR reviewer:

1. Definition & design setup
2. Quantitative results & sign convention
3. Primary finding/interpretation
4. Scope/mechanism disclaimer & two explicit caveats

The flow moves logically from empirical result to nuance without losing clarity.

---

### 4. Ship Gate

**Ready to ship as v0.9.8.** The sign inversion from v0.9.7 is fully resolved, all statistical parameters are rigorously contextualized, and potential methodological objections are proactively addressed.

---

### 5. Anything Else

A particularly strict reviewer might notice that 28% attrition occurs from requiring CC-CEDICT glosses. However, since this requirement is applied symmetrically across both conditions and languages, it affects scope rather than internal validity—a distinction already adequately addressed by your scope disclosure.
