# Response to Reviewers — Dictionarium Sinicum (ARR October 2026)

**Target venue:** NAACL 2027 / COLING 2027 Findings
**Manuscript version:** v1 (this submission)
**Previous review round:** ARR March 2026 (reviewers gKVr, SamJ, cky5)

We are grateful to the March 2026 reviewers for their detailed
feedback. This response letter maps every substantive objection from
the previous round to the specific manuscript changes that address it,
and preempts likely questions from this round by anticipating them
below.

---

## Section 1 — Changes since ARR March 2026

### 1.1 SamJ: "Consider including COMET or BERTScore alongside lexical overlap to better support claims and capture semantic accuracy."

**Addressed.** §5.2 (Table 7) now reports BERTScore F1 and COMET-DA
alongside sense-coverage and false-sense rate on the four community
reference languages (en, de, fr, id; macro F1 0.924, COMET-DA 0.774).
§5.3 (Table 11) reports reference-free CometKiwi across all 18 target
languages with the Chinese headword as the anchor (macro 0.547; ref
langs 0.562, non-community 0.542). §5.3 (Table 10) reports the same
three model-based metrics for four API-accessible MT baselines
(Claude Sonnet 4.5, GPT-4o-mini, Google Translate, DeepL); the
pipeline leads on all three metrics.

### 1.2 SamJ: "For the backfill phase, did the authors consider a second-model verification approach?"

**Addressed.** §5.3 "Second-model verification" paragraph reports an
independent Gemma-4-31B (open-weight, Cerebras) rating of MiniMax
outputs across all 14 non-community-reference languages, 200
stratified headwords each (n=2{,}800 total). Macro mean rating
4.47/5; only 9.6% of glosses are flagged as low-quality (rating $<$3).
The two lowest per-language means (Tagalog 4.14, Thai 4.35) coincide
with the lowest CometKiwi scores (0.471, 0.521) — two independent
open-weight quality-estimation methods agree on which languages need
the most improvement.

### 1.3 SamJ: PDF hyphenation typos.

**Addressed.** The hyphenation glitches were fixed in a dedicated
Tier 1 pass: `microtype` factor 1050, explicit
`\lefthyphenmin=3 \righthyphenmin=3`, targeted `\hyphenation{}`
list of $\sim$50 words. Over 20 two-letter fragment splits in the
March 2026 version are now zero.

### 1.4 gKVr / cky5: "Software: 1" — no public code.

**Addressed.** The pipeline and evaluation code are released at an
anonymized mirror (see the Data and Code Availability section). The
production repository is Apache-2.0 licensed and includes: the full
three-phase translation pipeline, all six eval scripts (community
comparison, MT baselines, semantic metrics, pivot ablation, error
taxonomy, second-model verification), the dictmaster SQLite schema
and importers, and 189 passing unit tests.

### 1.5 gKVr: "Single proprietary model."

**Addressed as a paper-clarity issue.** MiniMax M2.5 is open-weight;
it is hosted on multiple third-party inference providers (Fireworks,
NVIDIA NIM) and can be self-hosted. The Abstract, §1, §4.1, §6, and
§7 now explicitly call this out. Additionally, §5.4 (English-pivot
ablation) uses Llama-3.3-70B (open-weight, Meta) to demonstrate the
pipeline pattern works with a second open-weight model family.

### 1.6 gKVr: "Limited eval scope on the 12 non-community-reference languages."

**Addressed by two independent evaluations covering all 18 languages
(not just the reference-language subset)**: (a) reference-free
CometKiwi with Chinese as source (§5.3 Table 11) shows the
non-community-language macro (0.542) is only 0.02 below the
reference-language macro (0.562); (b) second-model verification
(§5.3, 14 non-community-ref languages including Spanish and Japanese)
gives macro 4.47/5 with all 14 languages above 4.0.

### 1.7 gKVr: "Anglocentric bias / pivot criticism."

**Addressed by explicit pivot-vs-direct ablation** (§5.3 English-pivot
ablation paragraph). Vietnamese and Thai, same open-weight model
(Llama-3.3-70B), with vs. without CC-CEDICT English gloss as pivot
input. Vietnamese: pivot CometKiwi 0.568 vs. direct 0.502
($\Delta=+0.067$ favouring pivot). Thai: 0.520 vs. 0.526
(essentially neutral). Finding: pivot bias is language-dependent,
not a uniform quality loss.

### 1.8 AC: "Error analysis / hallucination analysis / per-language breakdown."

**Addressed.** §5.3 "Per-language error taxonomy" paragraph points to
Appendix C, which reports full-corpus automated per-language error
signals (mono-gloss rate, mean segments, median length, CJK-character
inclusion, Chinese-headword echo) for all 18 languages. Notable
patterns: mono-gloss rate ranges 55% (English) to 74.6% (Indonesian
/ Tagalog); CJK inclusion is $\sim$1% for non-CJK targets except
Japanese (87%, legitimate kanji) and Korean (2.7%, low-level hanja
mixing).

### 1.9 cky5: Human evaluation.

**Framed as future work pending funding** (§7). A realistic
native-speaker instrument (2 annotators, 3--5 languages, $\sim$100
stratified entries, 5-point accuracy/naturalness/completeness
scales) would raise soundness scores substantially. The model-based
metrics in §5.2--§5.3 are the strongest automated proxy currently
available; we prioritized deploying them for this revision rather
than the more expensive human study.

---

## Section 2 — Anticipated questions this round

We ran an unofficial pre-review round with three independent large
language models (Claude Fable 5, xAI Grok, Google Gemini) prior to
submission. Their strongest recurring critiques and our responses:

### Q1: Isn't the +12--22pp sense-coverage lead over MT baselines confounded because the pipeline sees community glosses in prompt context but the baselines don't?

Yes, and the manuscript acknowledges this. The Abstract, §5.2
caveat paragraph, and the framing around Tables 9/10 have been
softened for this revision: the +12--22pp gap is now explicitly
attributed partly to the pipeline's access to community-reference
glosses in its input context, not to independent generation
capability alone. The paper distinguishes two claims:

- The community-reference languages (en/de/fr/id) show
  **context utilization**: how faithfully does the model preserve
  reference senses when given them? (Not a fair test of
  independent quality.)
- The 14 non-community-reference languages show **pivot
  translation quality** under a genuine open-ended MT setting;
  these are scored with reference-free CometKiwi and independent
  Gemma-4-31B verification.

The +12--22pp headline claim was retained because the *same model*
(MiniMax M2.5) with a generic zero-context prompt scores 14 points
lower than our pipeline on the same 275-pair evaluation, isolating
a real prompt-engineering effect.

### Q2: The pivot ablation uses only ~33 pairs per language after CC-CEDICT filtering. Isn't that statistically underpowered?

**We agree, and rerunning changes the finding.** The original n=33
suggested pivot helped Vietnamese by +0.067 CometKiwi and was neutral
for Thai. Rerun at n=324 (vi) and n=181 (th) with percentile-bootstrap
95% CIs shows the delta shrinks by an order of magnitude AND both CIs
straddle zero: Vietnamese direct-minus-pivot Δ = $-0.006$
(CI $[-0.020, +0.009]$), Thai Δ = $-0.020$ (CI $[-0.040, +0.001]$).
The earlier "pivot helps Vietnamese" finding was noise, not signal.
The revised §5.3 paragraph reports the honest finding: at properly
powered sample sizes, English pivot has no statistically detectable
effect on translation quality for either language. Notably, the
gloss agreement is only 61% (vi) / 44% (th), meaning pivot and direct
produce lexically different translations of equivalent reference-free
quality — the model uses the pivot context but the target-language
sense boundaries land in similar semantic space either way.

### Q3: What is the sense-coverage performance on a held-out set of headwords whose community glosses were NEVER supplied in the prompt?

This is a fair follow-up. We defer a true held-out evaluation to a
future revision because the production pipeline unconditionally
supplies community glosses for all reference-language slots (this
is design intent — context utilization is the point). A retrospective
held-out slice would require rerunning the pipeline on a masked
subset and would fully replicate the ~\$146 cost per run. We commit
to running one such slice for the camera-ready if the paper is
accepted.

### Q4: Why MiniMax M2.5 over other open-weight models that also passed the 5-headword smoke test (Kimi K2, Nemotron)?

Table 4 (tab:models) documents the selection criteria: format
compliance, script contamination, throughput, and cost. MiniMax M2.5
was the only model that produced zero issues on the 5-headword suite
across all four criteria. Kimi K2 and Nemotron both passed format
compliance but had non-zero contamination rates on the smoke test.
The paper adds an explicit note that a full-scale rerun with a
different generator (e.g., Qwen3-235B or Llama-3.3-70B) is future
work; the Llama-3.3-70B pivot ablation and the Gemma-4-31B
verification pass demonstrate that the pipeline pattern generalizes
across open-weight model families.

### Q5: Are there residual data-integrity issues after the three backfill passes?

No. A post-cleanup audit (§5.1) shows every headword $\times$ language
slot is filled, and the deterministic script validator has an audit
tab in the released code. The paper's earlier claim of "90.6%
single-character coverage" was a snapshot from an intermediate run;
subsequent backfill iterations with alternative prompting for
metalinguistic definitions closed those gaps. The current DB
(released at Harvard Dataverse, doi:10.7910/DVN/HJWMKI) shows 100.0% coverage
across all 7{,}709{,}256 slots.

### Q6: Missing prior art?

Gemini flagged three references worth adding for context and
completeness: Bond & Paik (2012) on wordnet licensing, Haddow et
al. (2022) on low-resource MT, and Wang et al. (2023) on
document-level MT with LLMs. All three are now cited (§2.1, §2.3,
§7).

---

## Section 3 — Known remaining limitations

Documented in §6 Limitations. Highest-priority items for future work:
(a) native-speaker human evaluation on 3--5 non-community-ref
languages (deferred pending recruitment funding); (b) full-pipeline
rerun with an alternative open-weight generator (deferred pending
$\sim$\$150 compute budget); (c) sense discrimination and
grammatical enrichment (multi-year research program).

---

## Section 4 — Reproducibility

- Anonymized code mirror at anonymous.4open.science (link in
  §Data and Code Availability).
- Full 2 GB SQLite database archived at Harvard Dataverse under CC BY-SA 4.0
  (doi:10.7910/DVN/HJWMKI; see §Data and Code Availability).
- 189/189 unit tests pass on the released repository.
- All eval scripts accept `--seed` for reproducible sampling; every
  reported metric can be re-derived by running the corresponding
  script on the released database.
