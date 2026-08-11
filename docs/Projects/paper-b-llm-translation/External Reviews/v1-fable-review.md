# Review: Dictionarium Sinicum v1 — Claude Fable 5

## Overall verdict
- Soundness: 3/5
- Excitement: 4/5
- Reproducibility: 4/5
- Software: 4/5 (based on paper's description; reviewer would see anon-mirror)
- Datasets: 4/5 (based on paper's description; reviewer would see Zenodo DOI)
- Meaningful comparison: 3/5

## Summary

The paper presents Dictionarium Sinicum, a 428,073-headword Chinese dictionary with glosses in 18 target languages, built by merging seven CC-licensed community dictionaries and filling the remaining ~7M headword–language slots with a single open-weight LLM (MiniMax M2.5) for ~$146 in API cost. A three-phase pipeline (batch, retry, context-aware backfill) plus a deterministic script validator achieves 100% coverage for multi-character headwords. Evaluation combines lexical sense-coverage against four community references, BERTScore/COMET/CometKiwi, an English-pivot ablation, a full-corpus error taxonomy, and a second-model verification pass. The resource, augmented with 511K Cantonese/Hokkien dialect forms, is released under CC BY-SA 4.0.

## Strengths
- **Genuinely useful resource at unprecedented scale for this task.** 428K headwords × 18 languages with open licensing fills a real gap (no community dictionary exists for 12 of the 18 targets), and the ~$150 cost makes the recipe transferable to other under-resourced source languages (§7).
- **Unusually honest self-disclosure.** The circularity of §5.2 ("context utilization, not independent translation quality"), the substring-match rates (42–60%), and the LLM-judge bias caveat are stated plainly. Many resource papers hide these.
- **The evaluation is genuinely multi-angle** — lexical overlap, three model-based metrics, reference-free QE across all 18 languages, back-translation, LLM judges, a full-corpus automated error taxonomy (Table 13), and a second-model verification. The convergence of CometKiwi and Gemma ratings on Tagalog/Thai as the weakest languages (lines 511–516) is a nice triangulation.
- **The script-contamination taxonomy and validator (§5.1) is a real methodological contribution** — the five contamination modes and the hard reject gate are reusable by anyone doing CJK-adjacent multilingual generation.
- **Dialect augmentation (511K forms, Table 2) with careful per-source licensing**, including explicit NC/ND exclusions. (Table 2's totals sum exactly — I checked.)
- **Practical engineering findings others will cite:** the provider-dependence result (§4.1 — same weights, 5.4s vs 167s with thinking silently enabled) and the benchmark-scores-don't-predict-structured-output observation.

## Weaknesses (ranked)

1. **The headline comparison (abstract, Table 9) is confounded by in-context reference leakage.** The pipeline's 87.3% sense coverage is measured on outputs where the model *saw the community reference glosses in its prompt* (§4.2, acknowledged in §5.2's "Important caveat"), while all ten baselines got a generic prompt with only the headword. The abstract nevertheless claims "87.3% sense coverage, outperforming ten MT baselines … by 12–22 percentage points" — not apples-to-apples. The "14 points isolating prompt engineering value" (MiniMax-generic row) conflates prompt format with reference-context access, since the generic prompt also drops the community definitions and corpus examples. The honest comparison is the reference-free one (Table 10), where the lead is +0.016 CometKiwi / +0.058 COMET-DA — real, but far more modest. Either (a) re-run the 2–3 strongest baselines with the full production prompt including context, or (b) rewrite the abstract and §5.3 headline around the reference-free metrics. As written, a careful reviewer will call the +12–22pp claim unsupported.

2. **Internal arithmetic does not reproduce the headline numbers.**
   - Table 5's Defs column: 4.41M + 616K + 110K = 5.14M, but the Total row says 7.70M and Table 12 says 7,697,901 LLM-gloss slots. One of these is mislabeled or wrong.
   - §4.2 token economics: 21,403 batches × (2,700 input @ $0.30/M + 3,000 output @ $1.20/M) ≈ $94, not the "∼$146" the same paragraph states. And caching only the 500-token system prompt saves ~$3, not the $28 implied by "$146 → $118".
   - Abstract line 012 says "99.3% coverage across all 7.7M headword–language slots", but slot-level coverage is (7,705,314 − 7,413)/7,705,314 ≈ 99.9%; 99.3% is the *headword*-level complete-coverage rate ((428,073 − 2,870)/428,073). The metric is mislabeled — it actually understates.
   None of these change the qualitative story, but "do the numbers add up" is the first thing a resource-paper reviewer checks, and three of them currently don't.

3. **The pivot ablation (lines 481–493) is underpowered for the claim drawn from it.** n≈33 pairs per language after the CC-CEDICT filter, no confidence interval, and a different model (Llama-3.3-70B) than the production system. From Δ = +0.067 (vi) and Δ = +0.006 (th) the paper concludes "pivot bias is language-dependent … depends on target-language distance from English." Two languages and ~33 items cannot support a generalization about language distance; the Thai Δ is plainly within noise, and no test shows the Vietnamese Δ isn't. Report bootstrap CIs, soften the claim to an observation, and state explicitly that the ablation model differs from the production model.

4. **The count of "non-community" languages drifts between 12, 13, and 14 without explanation.** §1 and §4.2 say twelve languages lack community dictionaries; back-translation (line 453) covers "13 non-community languages" (evidently the twelve + Spanish); §5.6 covers "14 non-community-reference languages" (those + Japanese); and lines 474–475 say "the twelve non-community languages [average] 0.542" when Table 11 has *fourteen* non-† languages whose mean is 0.543. The sets are reconstructible (CHEDICC-es is tiny; JMdict-ja stores kana, footnote 1) but the paper never says which set each analysis uses.

5. **All model-based metrics are applied far out of domain, and the paper under-discusses this.** wmt22-comet-da and wmt22-cometkiwi-da are trained on sentence-level DA data; here the "source" is a bare headword and the "hypothesis" a slash-separated gloss list. Absolute values near 0.5 are hard to interpret, and cross-language comparisons may be dominated by encoder resource-level bias rather than gloss quality — which also undercuts the "near-flat profile" claim (lines 476–478): the macro gap is 0.02, but the per-language spread runs 0.471 (tl) to 0.614 (en), which is not flat. Limitations mentions calibration for low-resource targets but not the word-level/out-of-domain issue. Item-level correlation of CometKiwi with the Gemma ratings (not just the language-level agreement you note) would substantially strengthen §5.3.

6. **Baseline identity and sample-size inconsistencies across Tables 9/10.** Table 9 and line 434 say "Claude Sonnet 4"; Table 10 and line 448 say "Claude Sonnet 4.5". Which was run — or were different models used for the two tables on "the same 275 pairs"? Relatedly: the pipeline row in Table 10 is n=311 (the de/fr/id subset of the §5.2 sample) while baselines are n=275, yet the caption says "same 275 pairs"; and English silently disappears between Table 7 (en/de/fr/id) and Table 10 (de/fr/id) with no stated reason. If pairs are not identical across systems, paired "+X pt" language is not justified.

7. **Japanese — the largest single community source (131K JMdict entries) — has no reference-based evaluation at all.** Footnote 1 excludes JMdict because it stores kana readings, so Japanese quality rests entirely on CometKiwi (0.546) and Table 13's 87% CJK / 13% headword-echo rates — and the echo metric is ambiguous for Japanese, where the identical kanji string is often the *correct* Japanese word. Even a small manual check (100 ja glosses, using JMdict's English glosses as a bridge) would close the largest hole in the eval matrix.

8. **§5.3 is structurally overloaded.** It contains six distinct studies (MT baselines, model-based metrics, back-translation, LLM judges, CometKiwi-18, pivot ablation) in one section, while §5.4 "Source Priority and Coverage" is two paragraphs that partially repeat §5.1's coverage numbers (lines 346–356 vs 525–530). Promote the pivot ablation, error taxonomy, and second-model verification to their own subsections — your own revision summary already refers to them as §5.4–§5.6, which the manuscript's numbering doesn't match.

9. **The frequency-band analysis (Table 8) likely measures sense count, not frequency.** Using community source coverage as a frequency proxy means the "rare" band is mostly words with one reference source — fewer reference senses to cover — which mechanically inflates coverage (93.5% rare vs 84.7% high). The monotonic trend is presented without naming this confound.

## Questions for the authors

1. Please reconcile Table 5's Defs column (sums to 5.14M) with the 7.70M total, and show the arithmetic behind $146 given §4.2's own per-batch token counts (which yield ~$94), and behind the $28 caching saving.
2. Was the Claude baseline Sonnet 4 or Sonnet 4.5 — and if both were run (Table 9 vs Table 10), why?
3. What decoding parameters (temperature, top-p, max tokens) were used for the production run and each baseline? None are reported, and §4.1's own provider-variance finding shows configuration materially changes output.
4. How was the back-translation evaluation (line 453, n=1,571) performed — which model back-translates, and what scores the round-trip against what reference?
5. Do the 9.6% Gemma-flagged glosses (§5.6) and residual contaminated definitions ship in the released database, and if so, are they marked? A per-gloss quality flag would materially change the Datasets score.
6. The NC/ND sources (Maryknoll, Embree, Kauiokpoo) are "excluded from commercial builds" (Table 2) — but a build that *includes* them cannot be released under CC BY-SA 4.0, which permits commercial use. Under what license is the NC-inclusive build distributed, and is Unihan's Terms of Use actually compatible with BY-SA redistribution?
7. Which exact language sets underlie "13 non-community" (back-translation) and "14 non-community-reference" (§5.6)?
8. §5.2 samples 200 headwords over four languages but yields n=453 of a possible 800 pairs — was the 200-headword sample shared across languages, and does the ~43% attrition (empty references) bias the sample toward better-covered headwords?

## Missing prior art

The Related Work claim that automatic dictionary construction has essentially one precedent (Wu & Wang 2025) overlooks two established literatures:

- **Definition/gloss generation ("definition modeling"):**
  - Noraset, Liang, Birnbaum & Downey, 2017. "Definition Modeling: Learning to Define Word Embeddings in Natural Language." AAAI 2017.
  - Gadetsky, Yakubovskiy & Vetrov, 2018. "Conditional Generators of Words Definitions." ACL 2018.
  - Bevilacqua, Maru & Navigli, 2020. "Generationary or: 'How We Went beyond Word Sense Inventories and Learned to Gloss'." EMNLP 2020.
  - Mickus et al., 2022. "SemEval-2022 Task 1: CODWOE — Comparing Dictionaries and Word Embeddings." SemEval 2022.
- **Bilingual lexicon induction (BLI)** — decades of work on automatically building bilingual dictionaries, directly relevant to the "no published work has attempted dictionary generation at scale" framing:
  - Rapp, 1999. "Automatic Identification of Word Translations from Unrelated English and German Corpora." ACL 1999.
  - Irvine & Callison-Burch, 2017. "A Comprehensive Analysis of Bilingual Lexicon Induction." Computational Linguistics 43(2).
  - Conneau, Lample, Ranzato, Denoyer & Jégou, 2018. "Word Translation Without Parallel Data." ICLR 2018.
- **Multilingual wordnet construction:** Bond & Foster, 2013. "Linking and Extending an Open Multilingual Wordnet." ACL 2013.
- **LLMs in lexicography (recent):** de Schryver, 2023. "Generative AI and Lexicography: The Current State of the Art Using ChatGPT." International Journal of Lexicography 36(4). (Also worth checking Lew's 2023 work on ChatGPT as a dictionary and Jakubíček & Rundell's eLex 2023 piece — I'm confident of the de Schryver reference; verify exact titles/venues for the latter two before citing.)

Distinguishing your work from BLI is easy (glosses rather than word-level mappings; 18 targets at once; context-aware consistency) — but the distinction has to be made, or a reviewer will make it for you.

## Suggestions for the next revision

To move **Soundness** 3 → 4:
1. Fix weakness #1: re-run Google Translate, DeepL, and the strongest LLM baseline with the full production context (or re-scope the abstract's comparative claim to the reference-free metrics), and add a paired bootstrap significance test on identical pair sets.
2. Fix every number in weakness #2 — Table 5, the cost arithmetic, the 99.3%-vs-99.9% label. Cheap fixes with outsized reviewer impact.
3. Add CIs to the pivot ablation and soften its conclusion; state the model mismatch with production.
4. Reconcile the 12/13/14 language-set counts and the Sonnet 4/4.5 naming.

To move **Excitement** 4 → 5:
5. Even a minimal human evaluation — two languages, 100 items, 2 annotators each, exactly the §7 instrument — would transform reception. Vietnamese and Tagalog (your two weakest by both automated signals) have large, reachable diaspora communities; targeting the *weakest* languages makes the human eval maximally informative and signals confidence.
6. Ship per-gloss quality flags (Gemma rating, contamination status) in the released database — turning the verification pass from an eval into a dataset feature, which raises Datasets too.
7. Report decoding parameters and pin provider + config in the repo, neutralizing your own §4.1 provider-variance finding as a reproducibility objection.
