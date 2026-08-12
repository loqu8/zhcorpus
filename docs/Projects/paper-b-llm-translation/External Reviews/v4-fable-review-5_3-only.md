# Review: §5.3 English-Gloss-Context Ablation — v0.9.8 Candidate (Fable, v4 round)

## 1. Fix incorporation — all 7 verified

| # | Fix | Verdict |
|---|-----|---------|
| 1 | Header renamed to "English-gloss-context ablation" | ✅ Present, and now consistent with caveat (ii) |
| 2 | *direct* / *pivot-context* defined up front | ✅ First sentence defines both cleanly before any numbers |
| 3 | Attrition/scope disclosure | ✅ "324 of ~448 stratified samples per language," and the framing as a *scope restriction* ("drawn from headwords with CC-CEDICT English glosses") is the right one — it discloses that even the direct condition runs only on gloss-bearing headwords |
| 4 | "paired-bootstrap," B=2000 | ✅ Mostly. The full label appears on the Vietnamese CI only; the Thai CI is abbreviated to "95% CI." That's standard first-mention convention and fine — but note the checklist overclaims slightly ("both CIs"). Not a blocker |
| 5 | Weakened agreement clause | ✅ "Rules out the delta being noise between near-identical outputs" is now a narrow, factually supported claim (40.8% agreement ⇒ lexically distinct outputs), with the quality preference explicitly resting on CometKiwi |
| 6 | Splice split | ✅ Split. Minor wording nit below |
| 7 | Softened bias-symmetry claim | ✅ "Should largely cancel... not exact if bias interacts with output length or register" is appropriately hedged |

## 2. New errors — none found

All numbers re-verified against the raw block: vi delta −0.0058 → −0.006, CI [−0.020, +0.009]; th delta −0.024, CI [−0.039, −0.010]; agreement 61.3% [56.5, 66.1] and 40.8% [36.4, 45.3]; 0.0243/0.4973 ≈ 4.9%, so "roughly 5% of the direct score" holds. The sign convention sentence ("a negative delta means the pivot-context condition scored higher") matches the data block, and the Thai interpretation sentence now points the correct direction. Internal consistency (delta definition ↔ convention sentence ↔ conclusion) checks out.

## 3. Reading flow — acceptable, two optional tightenings

The paragraph is long but each sentence carries load; an ARR reviewer can follow it in one pass. Two spots read slightly awkwardly:

- "We do not claim a mechanism from two target languages" — the elided "on the basis of only" makes it parse oddly on first read. Suggest: "We do not infer a mechanism from only two target languages."
- The agreement sentence is three clauses deep. If you want one trim, drop "since the two conditions produce lexically distinct translations" — it restates what "near-identical outputs" already implies. Optional.

## 4. Ship gate — **ship it**

No residual directional, numeric, or logical issue justifies another round. The two flow nits above are cosmetic and can be applied (or not) without re-review.

## 5. Anything else

Two small things earlier rounds didn't surface, neither blocking:

- **"Symmetric gloss agreement" is used but not defined** in this paragraph. If it's defined elsewhere in §5.3 or the setup section, fine; if not, a parenthetical (even just naming the metric) would preempt a reviewer question.
- The judge is named only as "CometKiwi." If the exact checkpoint (`Unbabel/wmt22-cometkiwi-da`) appears in the experimental setup or appendix, no change needed here — just confirm it's cited somewhere, since caveat (i) leans on its training distribution.
