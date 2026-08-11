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

---

# MANUSCRIPT: Dictionarium Sinicum v1

          Dictionarium Sinicum: Building a 428K-Headword Chinese Dictionary
                   in 18 Languages with a Single LLM for Under $150



                                            Anonymous ACL submission




001                         Abstract                               entries)—but no comparable resources exist for         041
                                                                   Korean, Russian, Vietnamese, Tagalog, Persian,         042
002        We present Dictionarium Sinicum, an open
                                                                   Swedish, Dutch, Portuguese, Arabic, Thai, Hindi,       043
003        multilingual Chinese dictionary comprising
004        428,073 headwords with definitions in 18                or Italian (CHEDICC provides a small Spanish           044

005        languages, constructed by merging seven                 dictionary of ∼4,400 entries). Creating such dictio-   045
006        community-maintained dictionaries with                  naries manually requires years of expert effort per    046
007        glosses generated by a single open-weight               language pair.                                         047
008        LLM (MiniMax M2.5) at a total API inference                Recent advances in large language models sug-       048
009        cost of approximately $150 at published                 gest an alternative: using a single multilingual       049
           pay-as-you-go rates. A three-phase pipeline—
010
                                                                   model to generate dictionary-quality definitions at    050
011        batch translation, retry, and context-aware
012        backfill—achieves 99.3% coverage across
                                                                   scale. However, prior work on LLM-assisted lex-        051

013        all 7.7M headword–language slots (100%                  icography has been limited to small-scale experi-      052
014        for multi-character headwords). We describe             ments. The closest precedent is a Pre-Qin philoso-     053
015        prompt engineering techniques that prevent              phy lexicon project using Qwen3-14B to generate        054
016        script contamination in CJK-target languages,           bilingual dictionary entries for approximately 1,000   055
017        including Japanese kanji echo and Korean hanja          classical Chinese philosophical terms in a single      056
018        mixing, and a deterministic post-translation            language pair (Wu and Wang, 2025). Lu et al.           057
019        script validator that detects and rejects
                                                                   (2024) use existing bilingual dictionaries as chain-   058
020        cross-language contamination at a rate of
021        0.83% of all generated definitions. Automated           of-thought context to improve LLM translation of       059

022        comparison against four community reference             rare words—a complementary approach where dic-         060
023        dictionaries shows 87.3% sense coverage,                tionaries help LLMs translate, whereas we use          061
024        outperforming ten MT baselines (Google                  LLMs to build dictionaries. No published work          062
025        Translate, DeepL, Claude, GPT-4o, and five              has attempted dictionary generation at the scale of    063
026        free LLMs) by 12–22 percentage points; the              hundreds of thousands of headwords across more         064
           same model with a generic prompt scores 14
027
                                                                   than two target languages.                             065
028        points lower, isolating prompt engineering
029        value. The dictionary, augmented with 511K
                                                                      We address this gap with Dictionarium Sinicum,      066

030        Cantonese and Hokkien dialect forms, is                 a system that:                                         067
031        released under CC BY-SA 4.0.
                                                                     1. Merges       seven     community-maintained       068
032   1    Introduction                                                 Chinese dictionaries (CC-CEDICT, HanDe-           069
                                                                        Dict, CFDICT, CC-CIDICT, CHEDICC,                 070
033   Bilingual and multilingual dictionaries remain                    Wiktextract, JMdict) covering 6 language          071
034   essential infrastructure for language learning, trans-            pairs into a unified headword table of 428,073    072
035   lation, and NLP. For Chinese, the open-source                     entries.                                          073
036   community has produced high-quality dictionaries
037   for a handful of language pairs—CC-CEDICT for                  2. Translates all headwords into 18 languages        074
038   English (∼124K entries), HanDeDict for German                     using a single open-weight LLM (MiniMax           075
039   (∼159K entries), CFDICT for French (∼56K                          M2.5, available on multiple inference             076
040   entries), and CC-CIDICT for Indonesian (∼124K                     providers) with carefully engineered prompts      077


                                                               1
078         that produce dictionary-style output and                  Source        Lang    Entries   License
079         prevent script contamination.                             CC-CEDICT     en      123,127   CC BY-SA 4.0
                                                                      HanDeDict     de      159,809   CC BY-SA 3.0
080       3. Backfills gaps using a context-aware prompt              CFDICT        fr       56,280   CC BY-SA 3.0
081          that sends existing translations as read-                CC-CIDICT     id      123,157   CC BY-SA 4.0
                                                                      CHEDICC       es        4,400   CC BY-SA 4.0
082          only context, ensuring consistency across                Wiktextract   multi   140,577   CC BY-SA 4.0
083          languages.                                               JMdict        ja      131,427   CC BY-SA 4.0

084       4. Augments the dictionary with 511,514               Table 1: Source dictionaries. All use compatible
085          dialect forms from 18 open sources covering        Creative Commons licenses (BY-SA 3.0/4.0).
086          Cantonese (Jyutping, 99.9% single-character
087          coverage) and Hokkien (POJ/Tâi-lô) pronun-
                                                                languages but are designed for sentence-level trans-     125
088          ciations and lexical equivalents.
                                                                lation, not dictionary-style glosses. Tower (Alves       126
089     Total inference cost was approximately $150 and         et al., 2024) focuses on high-resource language          127
090   the full pipeline completed in under one week.            pairs. Neither has been evaluated for or applied         128
                                                                to dictionary construction. These models do not          129
091   2     Related Work                                        natively produce multi-sense gloss lists, making         130

092   2.1    Multilingual Lexical Resources                     direct comparison nontrivial (see Limitations).          131

093   Large-scale multilingual lexical resources have           2.4    Community Chinese Dictionaries                    132
094   been constructed through both manual and auto-            The open Chinese dictionary ecosystem is built on        133
095   mated methods. PanLex (Kamholz et al., 2014)              the CC-CEDICT model: community-maintained,               134
096   aggregates bilingual dictionaries into a graph            CEDICT-format text files released under Creative         135
097   covering ∼5,700 languages with over 1.2 billion           Commons licenses. CC-CEDICT (CC-CEDICT),                 136
098   pairwise translations, but its Chinese coverage is        HanDeDict (HanDeDict), CFDICT (CFDICT), and              137
099   limited to headword-level mappings without defini-        CC-CIDICT (CC-CIDICT) together cover four                138
100   tion glosses. BabelNet (Navigli and Ponzetto, 2012)       European languages and Indonesian. Wiktex-               139
101   combines WordNet, Wikipedia, and other resources          tract (Ylonen, 2022) provides multilingual glosses       140
102   into a multilingual encyclopedic dictionary, but is       extracted from Wiktionary, and JMdict (Breen,            141
103   not open-access for bulk redistribution and focuses       2024) covers Japanese. CHEDICC provides a small          142
104   on synset alignment rather than dictionary-style          Spanish resource (∼4,400 entries), but no compa-         143
105   glosses. Our work differs from both in producing          rable community dictionaries exist for Korean,           144
106   complete, human-readable definition glosses for a         Russian, Vietnamese, Tagalog, Persian, Swedish,          145
107   single source language across 18 targets, released        Dutch, Portuguese, Arabic, Thai, Hindi, or Italian.      146
108   under CC BY-SA 4.0.
                                                                3     Data Sources and Headword Unification              147
109   2.2    LLM-Assisted Lexicography
110   The use of LLMs for dictionary construction is            3.1    Source Dictionaries                               148

111   an emerging area with limited published work.             Table 1 lists the seven source dictionaries. All         149
112   The closest precedent is a Pre-Qin philosophy             sources use compatible Creative Commons licenses,        150
113   lexicon (Wu and Wang, 2025) that uses Qwen3-14B           allowing the combined work to be distributed under       151
114   to generate ∼1,000 bilingual entries for classical        CC BY-SA 4.0.                                            152
115   Chinese philosophical terms—two orders of magni-
116   tude smaller than our work. Chain-of-Dictionary           3.2    Headword Unification                              153

117   prompting (Lu et al., 2024) uses existing bilingual       Source dictionaries use varying conventions for          154
118   dictionaries as chain-of-thought context to improve       pinyin romanization, traditional/simplified charac-      155
119   LLM translation of rare words—a complementary             ter pairs, and entry granularity. We unified head-       156
120   approach where dictionaries help LLMs translate,          words on the triple (traditional, simplified, pinyin),   157
121   whereas we use LLMs to build dictionaries.                yielding 428,073 unique headwords. Of these,             158
                                                                30,546 are single-character entries covering 19,471      159
122   2.3    Multilingual Translation Models                    distinct Chinese characters (many characters have        160
123   General-purpose multilingual translation models           multiple pinyin readings—e.g., 参 has 12 distinct         161
124   such as NLLB (Costa-jussà et al., 2022) cover 200+        entries).                                                162


                                                            2
163   3.3    Dialect Forms                                        M2.1 served by NVIDIA NIM took 167s per entry          212

164   We augmented the dictionary with Cantonese                  with thinking mode silently enabled, while the         213

165   and Hokkien dialect data from 18 open sources               same weights on Fireworks took 5.4s with thinking      214

166   (Table 2). Cantonese coverage is effectively                disabled. Benchmark scores (SWE-bench, MMLU)           215

167   complete: 16,564 unique single-character readings           showed no predictive value for this structured         216

168   covering 99.9% of BMP CJK characters. Hokkien               multilingual task: DeepSeek V3.2 (SWE-bench            217

169   coverage spans 6,850 single-character readings—             73.1%) echoed headwords, while MiniMax M2.5            218

170   lower in percentage terms (37% BMP) but repre-              (unranked) produced flawless output. These obser-      219

171   senting all characters with documented Hokkien              vations align with emerging evidence that inference    220

172   pronunciations in open data.                                acceleration introduces unpredictable behavioral       221

173      Hokkien romanization uses two systems: Tâi-lô            changes (Kirsten et al., 2025).                        222

174   (the MOE standard) and traditional POJ (Peh-ōe-jī).         4.2   Prompt Engineering                               223
175   A distinctive feature of Hokkien is its high lexical
176   divergence from Mandarin: 68–78% of Hokkien                 The production prompt generates all 18 languages       224

177   forms use different characters entirely (e.g., 漂            simultaneously for each batch of 20 headwords.         225

178   亮 piàoliang “beautiful” → 媠 suí; 東西 dōngxi
                                                                  Key design decisions:                                  226

179   “thing” → 物件 mih-kiānn).                                    System prompt (176 tokens): Establishes                227
                                                                  the lexicographer persona, output format (xx:          228
180   3.4    Chinese Text Corpus
                                                                  def1/def2), conciseness constraints (max 5             229
181   To provide real-world usage context during trans-           glosses), and language-specific rules addressing       230
182   lation, we constructed a large-scale Chinese text           three classes of script contamination:                 231
183   corpus from eight publicly available sources
184   (Table 3). Articles were chunked at sentence bound-           1. Japanese kanji echo: Without explicit             232

185   aries (。！？ ；) into segments averaging 40–80                      instruction, LLMs frequently “define” a           233

186   characters. All chunks are indexed with FTS5 using               Chinese word in Japanese by repeating the         234

187   a character-level CJK tokenizer, enabling sub-15ms               same characters (e.g., 銀行 → 銀行). The              235

188   lookup for any Chinese term. During translation,                 prompt requires: “Provide the MEANING in          236

189   1–2 example sentences per headword are retrieved                 Japanese, not just kanji echo or kana read-       237

190   from this corpus to provide the LLM with attested                ing.”                                             238

      usage context (§4.2).
                                                                    2. Korean hanja mixing: Korean definitions
191
                                                                                                                         239

192   4     Translation Pipeline                                       often include Chinese characters (hanja) unrec-   240
                                                                       ognizable to most modern Korean readers.          241
193   4.1    Model Selection                                           The prompt specifies: “Write in Hangul only.”     242

194   We evaluated 20+ LLMs across 10 inference                     3. General CJK leakage: A blanket prohibition:       243
195   providers on a 5-headword test suite covering                    “Every non-Chinese definition must contain        244
196   emergency service numbers (culturally specific),                 ZERO Chinese characters.”                         245
197   anime titles (transliteration challenges), and medi-
198   cal terminology. Selection criteria were: (1) correct       User prompt (batch of 20): Each entry includes         246
199   18-language output in the prescribed format, (2) no         traditional/simplified characters, pinyin, POS tag,    247
200   script contamination, (3) geographic context preser-        all existing community definitions as context,         248
201   vation, (4) sustainable throughput at 428K head-            and 1–2 example sentences drawn from the               249
202   words, and (5) cost under $200 at published rates.          113M-chunk Chinese corpus (Table 3). The corpus        250
203      MiniMax M2.5 was selected for production:                examples—sourced from Chinese Wikipedia,               251
204   zero issues on the test suite, 1.2s/entry through-          Baidu Baike, THUCNews, and news2016zh—                 252
205   put, no observed rate limits with 20 parallel work-         provide real-world usage context that helps            253
206   ers, and an estimated cost of ∼$150 for the full run        disambiguate polysemous headwords. Example             254
207   at published pay-as-you-go rates ($0.30/M input             sentences are retrieved via FTS5 lookup (<15ms         255
208   tokens, $1.20/M output tokens; Table 4).                    per headword), filtered to prefer 20–100 character     256
209      A notable finding is that the same open-weight           chunks.                                                257
210   model can produce dramatically different output                This constitutes pivot translation: for the         258
211   depending on the inference provider. MiniMax                twelve languages without community dictionaries        259


                                                              3
       Source               Dialect         Forms    License            Notes
       rime-cantonese       Cantonese      110,064   CC BY 4.0          Largest single source; community Jyutping readings
       CC-Canto readings    Cantonese       96,278   CC BY-SA 3.0       Jyutping overlay for CC-CEDICT headwords (Pleco)
       CC-Canto             Cantonese       29,762   CC BY-SA 3.0       Dedicated Cantonese dictionary (CC-Canto)
       Unihan kCantonese    Cantonese       28,800   Unicode ToU        Unicode standard Cantonese readings
       WikiHan              Cant.+Hok.      38,794   CC BY-SA 4.0       Wiktionary-derived readings for both dialects
       TaiHua               Hokkien         48,154   CC BY-SA 4.0       Taiwanese Hokkien dictionary (Tâi-lô romanization)
       Taibun               Hokkien         39,814   MIT                POJ-based Hokkien corpus
       Wiktextract          Hokkien         25,606   CC BY-SA 3.0       Hokkien readings from Wiktionary (Ylonen, 2022)
       iTaigi               Hokkien         10,572   CC BY 4.0          Crowdsourced Taiwanese Hokkien (iTaigi)
       7 additional         Mixed           83,670   Various open       ChhoeTaigi, early missionary sources, others

      Table 2: Dialect data sources. Total: 511,514 forms (290,421 Cantonese, 221,093 Hokkien) from 18 open sources.
      All sources use open licenses compatible with CC BY-SA 4.0 redistribution; three sources with NC/ND restrictions
      (Maryknoll, Embree, Kauiokpoo) are excluded from commercial builds.


       Source               Articles    Chunks    Type                     Phase         Entries    Defs   Time     Cost
       Chinese Wikipedia      1.4M        14M     Encyclopedia             1. Main       374,602   4.41M     24h   $130
       Baidu Baike            5.6M        33M     Encyclopedia             2. Retry       53,471    616K    92m     $12
       THUCNews               0.8M        11M     News                     3. Backfill    82,550    110K   105m      $4
       news2016zh             2.5M        18M     News
       NiuTrans Classical     0.3M         4M     Literary                 Total         428,073   7.70M     27h   $146
       chinese-poetry         0.3M         2M     Poetry
       ChID                   0.6M         7M     Idiom cloze        Table 5: Three-phase execution summary. Costs at
       LCCC                    22M        24M     Dialogue           published pay-as-you-go rates.
       Total                   34M       113M

      Table 3: Chinese text corpus sources. Articles are chun-       4.3    Three-Phase Execution                            273
      ked at sentence boundaries into segments of 40–80 char-        Table 5 summarizes the three-phase execution.           274
      acters.                                                        Phase 1 processed all 428,073 headwords in              275
                                                                     batches of 20 with 20 parallel workers. The             276
          Model             Provider     s/ent   Issues              API returned unparseable responses for 53,471           277
          MiniMax M2.5      MiniMax        1.2   None                headwords (12.5%), primarily due to batch-level         278
          Kimi K2           Groq           1.8   None
          MiniMax M2.1      Fireworks      5.4   None                formatting errors where the model’s response was        279
          Nemotron 253B     NIM            7.0   None                cut off or malformed. Phase 2 retried failed head-      280
          Sonnet 4.6        Anthropic    19.8    HW echo             words using the same prompt, recovering 616,276         281
          DeepSeek V3.2     NIM          35.3    HW echo
          MiniMax M2.1      NIM           167    Think ON            additional definitions and leaving 5,875 headwords      282
                                                                     with partial coverage. Phase 3 used a distinct          283
      Table 4: Model evaluation (5-headword test). HW echo           context-aware backfill prompt that sends all exist-     284
      = headword echo in output. Think ON = thinking mode            ing translations as read-only context, asking the       285
      silently enabled.                                              model to produce only the missing languages. This       286
                                                                     design ensures consistency: the model sees existing     287

260   (Swedish, Korean, Russian, Vietnamese, Tagalog,                glosses and produces output that matches in style       288

261   Persian, Dutch, Portuguese, Arabic, Thai, Hindi,               and specificity. Three backfill passes closed all       289

262   Italian), the model effectively translates from the            remaining multi-character gaps, achieving 100.0%        290

263   English and other community-language glosses                   coverage for the 397,527 multi-character head-          291

264   rather than directly from Chinese.                             words.                                                  292


265   Token economics: Approximately 5,700 tokens                    4.4    Parser Robustness                                293

266   per batch (500 system + 2,200 input including exam-            Parsing structured LLM output at scale required         294
267   ples + 3,000 output). Full run: 21,403 batches.                handling several failure modes: (1) multi-              295
268   At MiniMax M2.5 published rates ($0.30/M input,                language line collapse—the model outputs en:            296
269   $1.20/M output), the estimated cost is ∼$146 with-             bank/de: Bank/fr: banque on a single line;              297
270   out prompt caching or ∼$118 with the platform’s                a regex normalizer splits on /xx: boundaries;           298
271   automatic caching ($0.03/M for cached system                   (2) numbered vs. unnumbered responses—the               299
272   prompts).                                                      backfill prompt causes the model to drop entry          300


                                                                 4
          Language          Rate    Primary Contamination                regex patterns covering all 18 target languages) and             337
          Arabic            3.91%   Latin (9.7K), CJK (6.1K)             Latin in Arabic/Persian when constituting single                 338
          Persian           1.70%   Latin (4.5K), CJK (2.3K)             letters, scientific binomials, proper names, or uni-             339
          Japanese          1.15%   Hangul (3.1K), Cyrillic (1.8K)
          Hindi             0.87%   CJK (3.0K), Arabic (0.4K)
                                                                         versal acronyms; (2) deletion of contaminated                    340
          Indonesian        0.66%   CJK (2.3K), Cyrillic (0.5K)          minimax-sourced definitions (community entries                   341
          Korean            0.56%   Kana (1.4K), Cyrillic (0.7K)         never touched); (3) context-aware re-translation                 342
          Other 12     0.34–0.58%   CJK, Cyrillic
                                                                         via the backfill pipeline with the validator inte-               343

      Table 6: Script contamination by target language (full             grated as a hard reject gate—contaminated output                 344

      corpus). Uniformly distributed across headword ranges.             is discarded before database write.                              345

                                                                         Post-cleanup status. Multi-character headwords                   346
301   numbers; the parser uses blank lines as separators;                (397,527): 100.0% complete across all 18                         347
302   (3) overwrite protection—three layers prevent                      languages—zero gaps. Single-character headwords                  348
303   backfill from corrupting existing data: query filter,              (30,546): 27,676 (90.6%) complete; 2,870 (9.4%)                  349
304   parser filter, and database existence check.                       have residual gaps in 1–6 languages. The largest                 350
                                                                         gaps are in Arabic (1,084), Thai (1,016), German                 351
305   5      Quality Assessment                                          (895), and Persian (660). These persist because the              352

306   5.1     Script Contamination Audit                                 affected headwords are obscure radicals whose defi-              353
                                                                         nitions inherently cite Chinese characters, which                354
307   A full-corpus audit of all 7.7M minimax defini-                    the validator correctly rejects. All HSK 3.0 charac-             355
308   tions using a deterministic script validator revealed              ters have complete 18-language coverage.                         356
309   63,712 definitions (0.83%) containing scripts that
310   do not belong to the target language.                              5.2 Comparison with Community Dictionaries                       357
311      Table 6 breaks down contamination by language.                  For the four languages with existing community                   358
312   We identified five distinct contamination modes:                   dictionaries providing glosses (English, German,                 359

313       1. Cyrillic-in-non-Cyrillic (∼10K): The model                  French, Indonesian), we compared LLM-generated                   360

314          falls back to Russian when translating into                 definitions against human-curated references.1 We                361

315          less-resourced scripts. Example: Arabic for                 sampled 200 headwords stratified by community                    362

316          一世 → “zhizn’ ‫( ”واﺣﺪة‬Russian mixed with                     source coverage as a frequency proxy and measured                363

317          Arabic).                                                    two metrics across 453 headword–language pairs:                  364


318       2. Hangul-in-Japanese / Kana-in-Korean                           1. Sense coverage: proportion of reference                     365
319          (∼4.4K): Systematic confusion between CJK                        senses captured by the LLM gloss (automated                 366
320          languages.                                                       lexical overlap with 50% word-overlap thresh-               367
                                                                              old)                                                        368
321       3. Latin-in-Arabic/Persian (∼14K): English or
322          French words injected into Arabic/Persian defi-               2. False sense rate: proportion of LLM glosses                 369
323          nitions, after exempting proper names, scien-                    not matched by any reference sense                          370
324          tific binomials, and universal acronyms.
                                                                         Important caveat. The translation prompt pro-                    371
325       4. CJK-in-non-CJK (∼40K): Chinese charac-                      vides all existing community definitions as input                372
326          ters in non-CJK definitions, after exempting                context (§4.2). For these four languages, the model              373
327          metalinguistic cross-references (“variant of                sees the reference glosses. This comparison there-               374
328          迥”).                                                        fore measures context utilization—how faithfully                 375
                                                                         the model preserves reference senses—not inde-                   376
329       5. Multi-language field dumps (rare): Multiple
                                                                         pendent translation quality. We find that 42% of                 377
330          languages written into a single field.
                                                                         English, 40% of German, 55% of French, and 60%                   378

331   Cleanup methodology. We implemented a three-                       of Indonesian LLM glosses are substring matches                  379

332   stage pipeline: (1) a deterministic script valida-                 of the corresponding community definition.                       380

333   tor that detects all Unicode script families in each                  The overall sense coverage of 87.3% (95% boot-                381

334   definition and compares against a per-language                     strap CI: [84.7%, 89.8%]) with a false sense rate                382

335   allowlist, with exemptions for CJK in metalin-                        1
                                                                             JMdict was excluded because it stores kana readings rather
336   guistic reference frames (detected via compiled                    than Japanese-language glosses.


                                                                     5
       Lang Ref.                 n Cov. False BSc COMET                   System               n    Cov.   False   Fmt.
       en    CC-CEDICT 139 85.8          14.1   .932     .777             Our pipeline        453   87.3   12.5    ∼100
       de    HanDeDict 105 87.9          17.9   .905     .712             MiniMax (generic)   275   73.0   27.8    91.0
       fr    CFDICT     70 81.2          18.6   .926     .787
                                                                          Claude Sonnet 4     275   75.4   28.7    74.9
       id    CC-CIDICT 139 91.3           3.7   .933     .820
                                                                          Google Translate    275   70.9   28.9    72.0
       Overall              453 87.3     12.5   .924     .774             GPT-4o-mini         275   70.4   32.3    74.2
                                                                          Azure Translator    275   70.4   29.6    69.5
      Table 7: LLM vs. community dictionary. Cov./False in                DeepL               275   67.5   33.2    70.2
      %; BSc = BERTScore F1 (XLM-R-large); COMET =                        DeepSeek V3.1       275   72.0   36.5    82.1
      wmt22-comet-da (Rei et al., 2022a). Semantic-metric                 Kimi K2             275   68.0   35.1    82.1
                                                                          Llama 4 Scout       275   68.9   49.2    73.3
      n=139/105/67/139 (fr slightly reduced by non-empty-
                                                                          Qwen3-235B          275   65.2   43.4    78.8
      reference filter).
                                                                    Table 9: MT baseline comparison (%). Generic prompt
             Band                   n   Cov.     False              for all baselines. Free LLMs via Groq, Cerebras,
             high (4+ sources)    190   84.7%    16.7%              SambaNova.
             mid (3 sources)      146   87.4%    11.8%
             low (2 sources)       94   90.8%     5.7%
             rare (1 source)       23   93.5%    10.9%                For the twelve languages without community           414
                                                                    dictionaries, the model relies on pivot translation.   415
      Table 8: Comparison by frequency band (community
      source coverage as proxy).
                                                                    Section 5.3 addresses this gap.                        416

                                                                    5.3     MT Baselines and Non-Community                 417

383   of 12.5% (95% CI: [10.1%, 15.0%]) shows that                          Evaluation                                     418

384   the model successfully preserves most reference               We evaluated ten alternative systems on the            419
385   senses while introducing few unsupported glosses              same 275 headword–language evaluation pairs            420
386   (Tables 7–8). Manual inspection reveals that most             using a generic translation prompt (“Translate to      421
387   “false senses” are legitimate synonyms absent from            [Language]: [text]. Be concise—dictionary style.”),    422
388   the reference.                                                deliberately simpler than our production prompt        423
389      The main failure mode is sense compression:                (§4.2). We add a format compliance metric:             424
390   the LLM produces fewer glosses than community                 whether output matches CEDICT-style gloss format       425
391   dictionaries (median 2 vs. 3), preferring the                 (short slash-separated segments, ≤5 words, no          426
392   most common translation equivalent and omitting               sentence-ending punctuation).                          427
393   specialized or archaic senses. Manual inspection                 Table 9 shows our pipeline outperforms all          428
394   of the 57 headword–language pairs with sense                  baselines on sense coverage (+12–22pp) and             429
395   coverage below 50% reveals that sense compres-                false sense rate (−15–37pp). The same model            430
396   sion (38%) and register shift (22%) dominate, with            (MiniMax M2.5) with a generic prompt scores only       431
397   genuine errors (wrong meaning) accounting for                 73.0% coverage—14 points below our pipeline—           432
398   only 3%.                                                      isolating the value of dictionary-specific prompt      433
                                                                    engineering. Claude Sonnet 4, the strongest            434
      Semantic metric agreement. Because lexical
                                                                    baseline at 75.4%, still falls 12 points short.
399
                                                                                                                           435
      overlap can miss legitimate synonymy, Table 7 addi-
                                                                    Commercial MT and frontier LLMs produce
400
                                                                                                                           436
      tionally reports two model-based MT metrics on the
                                                                    CEDICT-compatible format only 70–75% of the
401
                                                                                                                           437
      same reference sample: BERTScore F1 with XLM-
                                                                    time; multiple LLMs cluster in the 65–78% range
402
                                                                                                                           438
      RoBERTa-large (Zhang et al., 2020) and COMET-
                                                                    regardless of model size, suggesting pipeline design
403
                                                                                                                           439
      DA (wmt22-comet-da, Rei et al., 2022a). Macro-
                                                                    matters more than model choice.
404
                                                                                                                           440
405   averaged BERTScore F1 is 0.924 and COMET-
406   DA is 0.774; the language ordering tracks sense               Model-based metrics on the MT baselines. We            441
407   coverage, with Indonesian highest on all three met-           additionally score the four API-accessible baselines   442
408   rics and German lowest on the two model-based                 with BERTScore F1, COMET-DA, and reference-            443
409   scores. As with sense coverage, the LLM sees the              free CometKiwi (Chinese source) on the same            444
410   community gloss as input context (§4.2), so these             275 pairs (Table 10). The pipeline lead extends        445
411   values characterize context utilization rather than           to all three metrics: +2.1 pt BSc F1, +5.8 pt          446
412   independent translation quality; independent qual-            COMET-DA, +1.6 pt CometKiwi over the next-best         447
413   ity across all 18 languages is addressed in §5.3.             system. Claude Sonnet 4.5 is the lowest baseline       448


                                                                6
       System               n    BSc. F1   COMET      CK                Lang     CK     Lang             CK
       Our pipeline        311    0.921     0.773     0.544             en†
                                                                                0.614   id†
                                                                                                        0.543
       Google Translate    275    0.900     0.715     0.524             de†     0.534   ja              0.546
       Claude Sonnet 4.5   275    0.900     0.711     0.501             fr†     0.555   ko              0.557
       DeepL               275    0.898     0.712     0.528             es      0.558   ru              0.568
       GPT-4o-mini         275    0.897     0.702     0.507             it      0.570   vi              0.554
                                                                        pt      0.554   tl              0.471
                                                                        nl      0.540   fa              0.535
      Table 10: Model-based metrics, macro-averaged over                sv      0.540   th              0.521
      de/fr/id (same 275 pairs as Table 9). BSc. F1 =                                   ar              0.503
      BERTScore F1 (XLM-R-large); COMET = wmt22-                                        hi              0.589
      comet-da; CK = reference-free wmt22-cometkiwi-                    Macro: 0.547 (ref 0.562 / non-community 0.542)
      da with the Chinese headword as source. Our-pipeline
      row: 3-lang macro over the same de/fr/id subset of           Table 11: Reference-free CometKiwi scores (higher
      Table 7. Azure and the free-LLM systems are omit-            is better) on 200 stratified headwords per language
      ted from this revision.                                      (n=3,600 total). † = language with a community ref-
                                                                   erence dictionary. Left column groups European targets;
                                                                   right column groups East Asian, Southeast Asian, and
449   on CometKiwi (0.501) despite the highest lexical             Middle Eastern targets.
450   sense coverage—fluent output can correlate less
451   tightly with the Chinese source than commercial
452   MT trained for translation fidelity.                         is 0.568 vs. 0.502 for Vietnamese (∆ = +0.067             485
453      Back-translation evaluation (n=1,571 across               favouring pivot) and 0.520 vs. 0.526 for Thai (∆ =        486
454   13 non-community languages) yields 68.9%                     +0.006, direct marginally higher). Symmetric gloss        487
455   sense coverage overall, with European languages              agreement is 60.6% (vi) and 37.1% (th). Pivot bias        488
456   strongest (Spanish 79.0%, Portuguese 75.2%) and              is language-dependent: English context measurably         489
457   Korean weakest (60.0%). Four LLM judges                      helps Vietnamese while being neutral for Thai, so         490
458   (Claude Sonnet 4, Kimi K2, GPT-OSS-120B,                     the pivot’s effect depends on target-language dis-        491
459   DeepSeek V3.1) rate MiniMax definitions across               tance from English rather than being uniform qual-        492
460   100 entries: accuracy 4.34/5, naturalness 4.31/5,            ity loss.                                                 493
461   completeness 3.38/5 (mean pairwise disagreement:
462   0.64 points). The lower completeness aligns with             Per-language error taxonomy. A full-corpus                494
463   sense compression (§5.2). Tagalog (3.90) and Hindi           analysis (Table 13, Appendix C) quantifies mono-          495
464   (4.04) show weakest accuracy. LLM judges may                 gloss rate (55% en → 74.6% id/tl), CJK-character          496
465   share biases with the evaluated model, but provide           rate (∼1% non-CJK targets, 87% ja, 2.7% ko), and          497
466   a quality signal where none previously existed.              Chinese-headword echo (13% for ja).                       498

467   Reference-free quality across all 18 languages.
                                                                   Second-model verification. Directly answering             499
468   We score our pipeline output with CometKiwi
                                                                   the reviewer suggestion to have a second model            500
469   (wmt22-cometkiwi-da, Rei et al., 2022b), a
                                                                   verify the no-community-reference backfill, we            501
470   reference-free quality-estimation model, on a 200-
                                                                   asked an independent open-weight model (Gemma-            502
471   headword stratified sample per language (n=3,600
                                                                   4-31B via Cerebras) to rate each MiniMax gloss            503
472   total). Macro-averaged CometKiwi is 0.547 across
                                                                   1–5 for semantic preservation of the Chinese              504
473   all 18 languages; the four community-reference
                                                                   source. Across 14 non-community-reference tar-            505
474   languages average 0.562 and the twelve non-
                                                                   get languages (n=2,800 rated, 200 per lang strati-        506
475   community languages 0.542—a gap of only 0.02
                                                                   fied by frequency band), the macro mean rating            507
476   (Table 11). This near-flat profile across resource
                                                                   is 4.47/5 and only 9.6% of glosses are flagged            508
477   tiers indicates that pipeline translation quality does
                                                                   as low-quality (rating <3). Per-language means            509
478   not degrade materially for languages lacking a
                                                                   range from 4.14 (Tagalog) to 4.65 (Portuguese/Rus-        510
479   community-dictionary anchor. Tagalog (0.471) is
                                                                   sian), with every language above 4.0. The two             511
480   the lowest and English (0.614) the highest.
                                                                   lowest per-language means (Tagalog 4.14, Thai             512
481   English-pivot ablation. On a 50-headword                     4.35) coincide with the lowest CometKiwi scores           513
482   Vietnamese + 50-headword Thai ablation using                 in Table 11 (0.471, 0.521)—two independent open-          514
483   Llama-3.3-70B (open-weight, Groq) with vs. with-             weight quality-estimation methods agree on which          515
484   out English pivot input, reference-free CometKiwi            languages need the most improvement.                      516


                                                               7
            Metric                                         Value       (§5.2). The model-based metrics we report—                556
            Headwords                                  428,073         BERTScore (Zhang et al., 2020), COMET-DA (Rei             557
            Languages                                       18         et al., 2022a), and reference-free CometKiwi (Rei         558
            Language slots (headword × language)     7,705,314
            Slots with LLM-generated gloss           7,697,901
                                                                       et al., 2022b)—mitigate the surface-form limita-          559
            Slots covered by community dict            738,777         tion of lexical overlap but inherit the biases of their   560
            Dialect forms (Cantonese + Hokkien)        511,514         underlying multilingual encoders, and CometKiwi           561
            Total cost (LLM inference, list price)      ∼$146
                                                                       scores are less well-calibrated for low-resource tar-     562

                  Table 12: Final dictionary statistics.               get languages. LLM-as-judge scores (§5.3) may             563
                                                                       share biases with the evaluated model. Human eval-        564
                                                                       uation across all 18 languages remains future work.       565
517   5.4     Source Priority and Coverage                                Pivot bias and single-model homogeneity. All           566
518   For headwords with definitions from multiple                     translations are mediated through English context,        567
519   sources, we apply a priority hierarchy: community                inheriting English sense boundaries. All 7.7M             568
520   dictionaries (CC-CEDICT, HanDeDict, CFDICT,                      glosses originate from MiniMax M2.5; model-               569
521   CC-CIDICT, CHEDICC, JMdict) > Wiktextract >                      specific biases propagate uniformly. Reproducibil-        570
522   MiniMax. Human-curated definitions take prece-                   ity is nevertheless supported by M2.5’s open              571
523   dence.                                                           weights, which are hosted by multiple third-party         572
524      Table 12 summarizes the final resource.                       providers (Fireworks, NVIDIA NIM) and can be              573
525   Multi-character headwords (397,527): 100.0%                      self-hosted.                                              574
526   complete—every headword has definitions in all 18                   Scope. The 428K headwords are inherited from           575
527   languages. Single-character headwords (30,546):                  community dictionaries without curation. The 18           576
528   90.6% complete; residual gaps are limited to                     target languages cover major families but omit            577
529   obscure radicals in Arabic, Thai, German, and                    Malay, Bengali, and Swahili.                              578
530   Persian. Zero headwords have zero definitions.
                                                                       7   Future Work                                           579
531   6     Downstream Application
                                                                       From glossary to dictionary. Sense-discriminated          580
532   To validate the dictionary’s practical utility, we               entries mapping each target-language gloss to             581
533   built a language pack generator that produces                    a specific Chinese sense with usage guidance,             582
534   consolidated SQLite databases for two Chinese                    combined with grammatical enrichment (German              583
535   learning applications. The consolidated archi-                   noun gender, Russian aspect pairs).                       584
536   tecture replaces per-language database files with                   Computational loanword detection. The                  585
537   a single database containing one column per                      dictionary contains both Hokkien source forms and         586
538   language, enabling column-scoped FTS4 search                     Southeast Asian target languages—infrastructure           587
539   (e.g., MATCH 'es:banco').          Databases are                 for tracing lexical diffusion at scale. Linking           588
540   encrypted for distribution. The dictionary is                    Hokkien tāu-hū to Indonesian tahu, Tagalog                589
541   currently deployed in production for English and                 taho, and Thai เต้า หู้ would produce a machine-          590
542   Spanish, with all 18 languages shipping in the next              readable atlas of Chinese vocabulary diffusion            591
543   release.                                                         across maritime Southeast Asia (Chan-Yap, 1980).          592
                                                                          Under-resourced languages. The ∼$150 cost
      Limitations
                                                                                                                                 593
544
                                                                       makes the pipeline relevant for languages with-           594
545   Glosses, not definitions. The resource produces                  out institutional support for manual lexicography—        595
546   translation equivalents, not full lexicographic defi-            Zhuang, Tibetan, Uyghur, and Yi within China              596
547   nitions with usage notes or grammatical patterns.                alone lack comprehensive bilingual dictionaries.          597
548   Entries lack sense discrimination: polysemous                       Community-in-the-loop evaluation. Native-              598
549   words produce flat gloss lists. Inflecting languages             speaker evaluation across all 18 target languages—        599
550   lack grammatical metadata (German noun gender,                   particularly by diaspora communities who are              600
551   Russian aspect pairs).                                           primary users of bilingual dictionaries—would             601
552      Evaluation limitations. Sense coverage is an                  establish gold-standard quality metrics. A realistic      602
553   automated lexical overlap proxy, not a human judg-               instrument would enrol 2 annotators for each of 3–5       603
554   ment, and partially circular for languages where the             languages on ∼100 stratified entries (accuracy, natu-     604
555   community gloss appears in the prompt context                    ralness, completeness on 5-point scales). We defer        605


                                                                   8
606   this pending per-language recruitment funding; the           Marta R. Costa-jussà, James Cross, Onur Çelebi, Maha        654
607   model-based semantic metrics in §5.2–§5.3 are the             Elbayad, Kenneth Heafield, et al. 2022. No language        655
                                                                    left behind: Scaling human-centered machine trans-
608   strongest automated proxy currently available.                                                                           656
                                                                    lation. arXiv preprint arXiv:2207.04672.                   657

609   8   Conclusion                                               HanDeDict. 2024. HanDeDict: Chinese-German                  658
                                                                     dictionary.  https://handedict.zydeo.net/.                659
610   A single open-weight LLM (MiniMax M2.5) can                    CC BY-SA 3.0.                                             660
611   produce a multilingual Chinese glossary of 428,073
612   headwords × 18 languages for approximately                   iTaigi. 2024. iTaigi: Crowdsourced Taiwanese Hokkien        661
613   $150. Enablers: batched cross-language prompt-                  dictionary. https://itaigi.tw/. CC0.                     662

614   ing, language-specific rules that reduce script              David Kamholz, Jonathan Pool, and Susan Colowick.           663
615   contamination to ∼0.83%, a deterministic script-               2014. PanLex: Building a resource for panlingual          664
616   validator gate, and context-aware backfill (100%               lexical translation. In Proceedings of the Ninth          665
617   multi-char, 90.6% single-char). Combined with                  International Conference on Language Resources            666
                                                                     and Evaluation (LREC 2014), pages 3145–3150,              667
618   511K Cantonese/Hokkien dialect forms, this is the              Reykjavik, Iceland. European Language Resources           668
619   first open multilingual Chinese lexical resource               Association (ELRA).                                       669
620   covering the major languages of Europe, East Asia,
                                                                   Elisabeth Kirsten, Ivan Habernal, Vedant Nanda, and
621   Southeast Asia, and the Middle East.                                                                                     670
                                                                      Muhammad Bilal Zafar. 2025. The impact of                671
                                                                      inference acceleration on bias of LLMs. In Proceed-
      Data and Code Availability
                                                                                                                               672
622
                                                                      ings of the 2025 Conference of the North American        673
                                                                      Chapter of the Association for Computational Linguis-
623   The full Dictionarium Sinicum SQLite database                                                                            674
                                                                      tics (NAACL 2025), pages 1834–1853. Association          675
624   (2 GB, 428,073 headwords × 18 languages, SHA-                   for Computational Linguistics.                           676
625   256 e647e163…8ea512) is archived at Zenodo:
626   [ZENODO_DOI]. All pipeline code, evaluation                  Hongyuan Lu, Haoran Yang, Haoyang Huang, Dong-              677
                                                                     dong Zhang, Wai Lam, and Furu Wei. 2024.                  678
627   scripts, and reproducibility artifacts (Apache-2.0)            Chain-of-dictionary prompting elicits translation in      679
628   are mirrored anonymously at [ANON_MIRROR_                      large language models. In Proceedings of the              680
629   URL] for the review period; the production reposi-             2024 Conference on Empirical Methods in Natu-             681
630   tory URL will be provided in the camera-ready.                 ral Language Processing (EMNLP 2024), pages               682
                                                                     958–976. Association for Computational Linguistics.       683

                                                                   Roberto Navigli and Simone Paolo Ponzetto. 2012.
      References
                                                                                                                               684
631                                                                  BabelNet: The automatic construction, evalua-             685
632   Duarte Alves, Nuno M. Guerreiro, João Albuquerque,             tion and application of a wide-coverage multilin-         686
633     and André F. T. Martins. 2024. Tower: An open multi-         gual semantic network.     Artificial Intelligence,       687
634     lingual large language model for translation-related         193:217–250.                                              688
635     tasks. In First Conference on Language Modeling
636     (COLM).                                                    Ricardo Rei, José G. C. De Souza, Duarte M. Alves,          689
                                                                     Chrysoula Zerva, Ana C. Farinha, Taisiya Glushkova,       690
637   Jim Breen. 2024. JMdict: Japanese-multilingual                 Alon Lavie, Luisa Coheur, and André F. T. Martins.        691
638      dictionary. https://www.edrdg.org/jmdict/j_                 2022a. COMET-22: Unbabel-IST 2022 submission              692
639      jmdict.html. CC BY-SA 4.0.                                  for the metrics shared task. In Proceedings of the        693
                                                                     Seventh Conference on Machine Translation (WMT),          694
640   CC-Canto. 2024. CC-Canto: Cantonese dictionary.                pages 578–585, Abu Dhabi, United Arab Emirates.           695
641     https://cantonese.org/. CC BY-SA 3.0.                        Association for Computational Linguistics.                696

642   CC-CEDICT. 2024.       CC-CEDICT: Community-                 Ricardo Rei, Marcos Treviso, Nuno M. Guerreiro,             697
643     maintained Chinese-English dictionary. https://              Chrysoula Zerva, Ana C. Farinha, Christine Maroti,        698
644     cc-cedict.org/. CC BY-SA 4.0.                                José G. C. De Souza, Taisiya Glushkova, Duarte M.         699
645   CC-CIDICT. 2024. CC-CIDICT: Chinese-Indonesian                 Alves, Luisa Coheur, Alon Lavie, and André F. T.          700
646     dictionary. https://cidict.org/. CC BY-SA                    Martins. 2022b. CometKiwi: IST-unbabel 2022 sub-          701
647     4.0.                                                         mission for the quality estimation shared task. In Pro-   702
                                                                     ceedings of the Seventh Conference on Machine Trans-      703
648   CFDICT. 2024. CFDICT: Chinese-French dictionary.               lation (WMT), pages 634–645, Abu Dhabi, United            704
649     https://chine.in/mandarin/dictionnaire/                      Arab Emirates. Association for Computational Lin-         705
650     CFDICT/. CC BY-SA 3.0.                                       guistics.                                                 706

651   Gloria Chan-Yap. 1980. Hokkien Chinese Borrowings            Mingfei Wu and Dingding Wang. 2025. Automatic               707
652     in Tagalog. Pacific Linguistics, Series B, No. 71.           compilation of a pre-Qin philosophy lexicon via large     708
653     Australian National University.                              language models. npj Heritage Science.                    709


                                                               9
710   Tatu Ylonen. 2022. Wiktextract: Wiktionary as                                                            775
711     machine-readable structured data. In Proceedings              Produce definitions for each language    776
712     of the Thirteenth Language Resources and Evalu-                   below.                               777
713     ation Conference (LREC 2022), pages 1317–1325,                Output EXACTLY one line per language .   778
714     Marseille, France. European Language Resources                                                         779
                                                                      en:                                      780
715     Association (ELRA).                                           de:                                      781
716   Tianyi Zhang, Varsha Kishore, Felix Wu, Kilian Q. Wein-         fr:                                      782
                                                                      es:                                      783
717      berger, and Yoav Artzi. 2020. BERTScore: Evalu-              sv:                                      784
718      ating text generation with BERT. In International            ja:                                      785
719      Conference on Learning Representations (ICLR).               ko:                                      786
                                                                      ru:                                      787
720   A     Prompt Templates                                          id:                                      788
                                                                      vi:                                      789
721   A.1    System Prompt (production)                               tl:                                      790
                                                                      fa:                                      791
722
723    You are a professional multilingual                            nl:                                      792
724        Chinese                                                    pt:                                      793
725    lexicographer producing dictionary -                           ar:                                      794
726        style                                                      th:                                      795
727    definitions in 18 languages .                                  hi:                                      796
728                                                                   it:                                      797
                                                                                                               798
729    Rules:
730    - Output EXACTLY one line per language
731         in                                                       A.3    Backfill Prompt (context-aware)    799
732      format "xx: def1/def2"
                                                                                                               800
733    - Be concise : dictionary style , not                          Fill in ONLY the missing language        801
734        full                                                           definitions .                        802
735      sentences                                                    Existing translations are provided for   803
736    - Maximum 5 glosses per entry                                  consistency -- match their style and     804
737    - CRITICAL : Every non - Chinese                                   specificity .                        805
738        definition must                                            Do NOT repeat or modify existing         806
739      contain ZERO Chinese characters .                                translations .                       807
740                                                                                                            808
741    Language - specific rules:                                     SCRIPT PURITY ( strictly enforced --     809
742    - ja: Provide the MEANING in Japanese ,                            output                               810
743         not                                                       that violates these rules will be        811
744      just kanji echo or kana reading .                                rejected ):                          812
745    - ko: Write in Hangul only. Do NOT mix                         Each definition must use ONLY the        813
746         in                                                            script of                            814
747      Chinese characters .                                         its target language .                    815
748    - vi: Write in Vietnamese with proper                                                                   816
749      diacritics . No Chinese characters .                         1. 三 角 褲 / 三 角 裤                         817
750    - ar: Write in Arabic script only. No                             Pinyin : san jiao ku                  818
751        Latin.                                                        Existing translations :               819
752    - th: Write in Thai script with tone                                en: briefs / underwear              820
753        marks.                                                          de: Slip/ Unterhose                 821
754    - hi: Write in Devanagari script .                                  fr: slip/ calecon                   822
755    - fa: Write in Persian script only.                                 [... 14 more languages ...]         823
756    - nl/pt/it: Write in standard Dutch/                              MISSING -- fill these:                824
757
758      Portuguese / Italian .                                            vi:                                 825
                                                                                                               826


759   A.2    User Prompt (with corpus examples)                      B     Sample Definitions                  827
760
       Chinese : 銀 行 / 银 行
761
762    Pinyin : yin hang
                                                                     B.1    Idiom: 画蛇添足                        828
763    POS: noun                                                     huà shé tiān zú “draw legs on a snake”    829
764                                                                                                            830
765    Existing definitions :                                         en: to improve something unnecessarily   831
766      English : bank/ financial institution                            ;                                    832
767      German : Bank/ Geldinstitut                                      to gild the lily                     833
768      French : banque / etablissement                              de: der Schlange Fuesse hinzumalen ;     834
769          bancaire                                                     etwas Ueberfluessiges tun            835
770                                                                   fr: dessiner un serpent et lui ajouter   836
771    Example sentences :                                                des pattes ; faire du zele           837
772      中国人民银行决定下调金融机构贷款和存                                           es: dibujar una serpiente y anadirle     838
773          款 基 准 利 率。                                                   patas; hacer algo innecesario        839
774      这 家 银 行 在 全 国 设 有 两 千 多 个 分 支 机 构。                           ko: 뱀 에 게 발 을 그 리 다 ;                    840


                                                                10
841        불필요한 것을 추가하다
842    vi: ve ran them chan;
843
844        them thu khong can thiet


845   B.2   Cultural term: 春节
846   chūn jié “Spring Festival”
847
848    en: Spring Festival ( Chinese New Year)
849    de: Chinesisches Neujahrsfest
850    fr: Nouvel An chinois /Fete du
851        printemps
852    id: Festival Musim Semi
853    ja: 春 節 ( 中 国 の 旧 正 月 )
854    ko: 춘 제 / 설 날
855
856    vi: Tet Nguyen dan


857   B.3   Loanword chain: 豆腐                                     Lang    Mono     Mean    Med.     CJK       Zh-
                                                                             %       seg.    len       %    echo%
858   dòufu “tofu”
859                                                                en        55.4    1.56      25    1.07     0.57
860    en: tofu / bean curd                                        de        67.4    1.40      23    1.02     0.51
861    de: Tofu / Bohnenkäse                                       fr        69.6    1.37      22    1.05     0.53
862    id: tahu          <- Hokkien tau -hu                        id        74.6    1.31      20    1.11     0.57
863    tl: tokwa         <- Hokkien tau -koan                      es        70.3    1.36      22    1.06     0.54
864    vi: dau phu       <- Sino - Vietnamese                      sv        71.5    1.35      18    1.02     0.53
865    ko: 두 부           <- Sino - Korean                          ja        61.7    1.45       9   87.45    13.01
866
867    ja: と う ふ         <- Sino - Japanese                        ko        68.0    1.40       7    2.73     0.53
                                                                   ru        71.0    1.35      21    0.98     0.49
868      This entry illustrates how the Hokkien maritime           vi        71.6    1.34      18    0.99     0.53
                                                                   tl        73.5    1.32      22    1.04     0.55
869   trade vocabulary seeded cognates across South-               fa        71.3    1.35      16    0.72     0.35
870   east Asian languages: tāu-hū (Hokkien) → tahu                nl        68.4    1.38      20    1.03     0.52
871   (Indonesian/Malay), taho/tokwa (Tagalog), đậu phụ            pt        69.1    1.37      21    1.07     0.52
                                                                   ar        65.1    1.41      17    1.46     0.40
872   (Vietnamese, Sino-Vietnamese route).                         th        68.3    1.38      18    0.80     0.36
                                                                   hi        67.1    1.39      18    0.77     0.39
873   C     Per-Language Error Taxonomy                            it        68.8    1.37      22    1.02     0.52

874   Table 13 reports automated per-language error sig-        Table 13: Per-language error signals from the full
875   nals across the full 428,073-headword MiniMax             428,073-headword MiniMax output. Mono % = frac-
876   output.                                                   tion of definitions with only one slash-separated gloss
                                                                (sense-compression proxy). Mean seg. = mean glosses
                                                                per definition. Med. len = median character length.
                                                                CJK % = fraction containing any CJK character (script
                                                                contamination for non-CJK targets; expected for ja/ko).
                                                                Zh-echo % = fraction containing the Chinese headword
                                                                string (metalinguistic reference, common in ja).




                                                           11
