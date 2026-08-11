# External Review Round v1 — Dictionarium Sinicum

**Manuscript:** `Dictionarium-Sinicum-v1.md` (compiled from
`dictionarium_sinicum.tex` at commit-hash to be pinned at dispatch;
if you're reading this hand-carried into a chat window, the manuscript
follows this preamble or is attached alongside it)

**Round:** v1 (first external AI review round of the ARR October 2026
revision cycle)

**Target venue:** ACL Rolling Review → NAACL 2027 / COLING 2027 Findings

**Submission deadline:** 12 October 2026

---

## What this paper is

An open multilingual Chinese dictionary system: 428,073 headwords with
definitions in 18 target languages, built by merging seven
community-maintained dictionaries with LLM-generated glosses from a
single open-weight model (MiniMax M2.5) for ~$150 in API cost. Ten
pages ACL long-paper format (8 body + refs + 3 appendices).

## What changed since the March 2026 ARR submission

The March 2026 version was reviewed by three ARR reviewers (SamJ, gKVr,
cky5) plus a meta-review. This revision folds in:

1. **Public code repo** — the pipeline and eval scripts are now at
   `github.com/loqu8/dictionarium-sinicum` (currently v0.3.2; will be
   mirrored anonymously via anonymous.4open.science at submission time).
   Fixes gKVr Software=1 + cky5 Software=1.
2. **PDF hyphenation fixes** — dozens of two-letter fragment splits
   the previous submission carried. Fixes SamJ cosmetic list.
3. **Semantic MT metrics (§5.2 and §5.3)** — BERTScore F1 + COMET-DA on
   the four community-reference languages (**Table 7**, folded into the
   existing Cov/False columns); reference-free CometKiwi with the
   Chinese headword as source-language anchor across all 18 languages
   (**Table 11**); the same three model-based metrics applied to four
   MT baselines (**Table 10**: Claude Sonnet 4.5, GPT-4o-mini, Google
   Translate, DeepL). Fixes SamJ "consider COMET or BERTScore" and
   gKVr "limited eval scope on the 12 non-community languages".
4. **English-pivot ablation** (English-pivot ablation paragraph in
   §5.3, near the end of the section) — Vietnamese + Thai, same model
   (Llama-3.3-70B, open-weight, Groq) with vs. without the CC-CEDICT
   English gloss as pivot input. CometKiwi: pivot 0.568 vs. direct
   0.502 for Vietnamese (Δ +0.067 favouring pivot), 0.520 vs. 0.526
   for Thai (essentially neutral). Fixes AC pivot criticism + gKVr
   Anglocentric bias.
5. **Per-language error taxonomy** (Per-language error taxonomy
   paragraph in §5.3 + Appendix C table) — full-corpus automated
   per-language error signals (mono-gloss rate, CJK inclusion,
   Chinese-headword echo). 18-lang breakdown table in appendix. Fixes
   AC error-analysis + gKVr per-language-breakdown + cky5
   hallucination-analysis asks.
6. **Second-model verification of the backfill** (Second-model
   verification paragraph in §5.3) — Gemma-4-31B (open-weight,
   Cerebras) rates 2,800 MiniMax outputs across 14 non-community-ref
   languages 1-5 for zh-source semantic preservation. Macro 4.47/5;
   9.6% flagged as low-quality (rating < 3). Fixes SamJ "second-model
   verification" suggestion.
7. **Open-weight framing** — MiniMax M2.5 is open-weight (Fireworks
   + NVIDIA NIM host it). Abstract, §1, §4.1, §6 Limitations, and §7
   Conclusion now say so explicitly. Fixes gKVr "single proprietary
   model".
8. **Native-speaker human eval** — explicitly framed as gold-standard
   validation deferred pending per-language recruitment funding (§7
   Future Work paragraph). Addresses the reviewer ask by
   acknowledgement rather than execution.

## What we're asking you to do

Peer-review this paper the way you would a real ARR submission. Rate
it against the ARR October 2026 form:

1. **Soundness** (1-5): are the claims supported by the evidence?
   Do the numbers add up? Any statistical, methodological, or
   experimental-design errors?
2. **Excitement / significance** (1-5): does the resource matter?
   Is the contribution meaningful?
3. **Reproducibility** (1-5): can a reader reproduce the results?
   Is enough shared? Are the model IDs, pipeline steps, and eval
   scripts described precisely enough?
4. **Software** (1-5): is the released code artifact usable?
   (Reviewers will see an anonymized 4open.science mirror at
   submission time.)
5. **Datasets** (1-5): is the dataset well-documented, sized,
   licensed, and citable? (Will be at Zenodo with a DOI at
   submission time.)
6. **Meaningful comparison** (1-5): are baselines adequate? Any
   missing prior art?
7. **Ethical concerns**: any that we've missed?

Then write a review-body of the form ARR uses:

- **Summary**: 3-5 sentences on what the paper does.
- **Strengths**: bullet list.
- **Weaknesses**: bullet list, ranked by severity. Be specific — cite
  section, table, or line. Vague criticism (`"the eval could be
  stronger"`) is much less useful than concrete criticism
  (`"§5.4 line 496 claims pivot bias is language-dependent based on
  n=33 pairs per language; that's underpowered — need CI"`).
- **Questions for the authors**: any factual/methodological things
  you'd want them to clarify in a rebuttal.
- **Missing prior art**: any published papers we should be citing but
  aren't. Please give the citation in a form we can look up (author,
  year, venue).
- **Suggestions for the next revision**: what would move your soundness
  or excitement scores up 1 point.

## Review discipline

- **Do not fabricate citations**. If you cite a paper, we will look it
  up. A citation to a paper that doesn't exist is worse than no
  citation.
- **Do not invent numbers**. Every claim you make about the paper's
  content must be traceable to the manuscript text.
- **Section and line numbers** count as citations. If the manuscript
  doesn't have line numbers in your rendering, use section and
  paragraph identifiers ("§5.4 second paragraph", "Table 12 last row").
- **Be direct on weaknesses**. This paper has been through one round
  of blind review already; the authors want to hear what's still
  wrong, not what's fine.
- **Read the manuscript before commenting**. If a critique amounts to
  "the paper doesn't address X" and the paper DOES address X, please
  self-check before finalizing.

## Known limitations of this manuscript

We already know about these; you don't need to spend length on them
unless you have a specific fix or think they matter more than we do:

- No native-speaker human evaluation. Deferred to future work pending
  per-language recruitment funding. See §7.
- §5.6 second-model verification uses Gemma-4-31B, not the strongest
  open-weight verifier possible (Qwen3-235B was gated on the free
  Cerebras key we used); Gemma was validated 10/10 on a hard-language
  smoke test but a stronger verifier is future work.
- §5.4 pivot ablation is n=50 per language before the CC-CEDICT filter
  drops it to n≈33 in Vietnamese/Thai. Small sample, disclosed in
  paper text.
- §5.6 second-model verification hit the Cerebras free-tier per-hour
  cap on the first submission run; the paper reports n=2800 from a
  resumed PayGo run in the final draft (previously n=556). Sample
  sizes are documented per-language.
- No open-weight model comparison for the whole pipeline. We rely on
  the open-weight framing of MiniMax M2.5 (§4.1, §6, §7) and the
  Llama-3.3-70B pivot ablation as evidence that the pipeline generalizes
  across open-weight models, but we did not re-run the full pipeline
  with, e.g., Qwen or Llama end-to-end.

## Format for your reply

Please respond in Markdown, using this skeleton so we can compare across
Fable / Grok / Gemini reviews cleanly:

```
# Review: Dictionarium Sinicum v1 — <your name>

## Overall verdict
- Soundness: <n>/5
- Excitement: <n>/5
- Reproducibility: <n>/5
- Software: <n>/5 (based on paper's description; reviewer would see anon-mirror)
- Datasets: <n>/5 (based on paper's description; reviewer would see Zenodo DOI)
- Meaningful comparison: <n>/5

## Summary

## Strengths
- ...

## Weaknesses (ranked)
1. ...
2. ...

## Questions for the authors

## Missing prior art

## Suggestions for the next revision
```

Manuscript starts on the next page (or is attached if you got this
hand-carried into a chat window).
