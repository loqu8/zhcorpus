# Paper G: Lexicon Omnium Gentium — Multilingual Strong's Concordance via LLM Translation

*Research notes, 2026-03-15*

## Vision

Apply the dictmaster pipeline (community lexicon + LLM backfill → 18+ languages) to Strong's
Concordance, producing the first open multilingual biblical lexicon keyed to Strong's numbers.
~14,298 Hebrew/Greek entries × 18 languages = ~257K definitions.

This is structurally identical to Dictionarium Sinicum (Paper B) but with key methodological
advantages: canonical sense IDs (Strong's numbers), non-circular evaluation (700+ Bible
translations as ground truth), and a fixed classical corpus.

---

## 1. What Currently Exists

### 1.1 Strong's Base Data (English, Public Domain)

The original Strong's Concordance (1890) is public domain. Several high-quality machine-readable
versions exist:

| Dataset | Format | License | Notes |
|---------|--------|---------|-------|
| [openscriptures/strongs](https://github.com/openscriptures/strongs) | XML, JSON | PD / CC BY 4.0 | Canonical open dataset, 280+ stars |
| [openscriptures/HebrewLexicon](https://github.com/openscriptures/HebrewLexicon) | XML | CC BY 4.0 | Strong's + BDB + TWOT bridge, augmented numbers (H1234a/b) |
| [morphgnt/strongs-dictionary-xml](https://github.com/morphgnt/strongs-dictionary-xml) | XML | PD | Greek only, proper Unicode |
| [STEPBible-Data](https://github.com/STEPBible/STEPBible-Data) | TSV | CC BY 4.0 | Enhanced definitions (TBESH/TBESG), Extended Strong's |
| [unfoldingWord UGL](https://git.door43.org/unfoldingWord/en_ugl) | Markdown | CC BY-SA 4.0 | Greek lexicon based on Abbott-Smith (1922) |
| [unfoldingWord UHAL](https://git.door43.org/unfoldingWord/en_uhal) | Markdown | CC BY-SA 4.0 | Hebrew/Aramaic lexicon |
| [scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases) | SQL, JSON, CSV | MIT | 140+ translations, some with Strong's tags |

### 1.2 Scale

- **Hebrew**: H0001–H8674 = 8,674 root words (Extended Strong's adds ~H9000-H9009 for prefixes)
- **Greek**: G0001–G5624 = 5,624 root words (some gaps from renumbering)
- **Total**: ~14,298 base entries
- Extended Strong's (STEPBible) adds letter suffixes (a, b, c) to disambiguate sub-senses

### 1.3 Entry Structure

A typical Strong's entry contains:

| Field | Example (H3068 יְהֹוָה) |
|-------|-------------------------|
| Strong's Number | H3068 |
| Original Script | יְהֹוָה (Hebrew) or λόγος (Greek) |
| Transliteration | Yᵉhôvâh |
| Pronunciation | Phonetic with stress |
| Etymology | Root references (e.g., "from H1961") |
| Gloss | Brief meaning |
| Definition | Lexicon entry with cross-references |
| Part of Speech | noun, verb, etc. |
| KJV Renderings | All English translations + frequency counts |

### 1.4 Non-English Strong's: The Gap

**No open-source project has systematically translated Strong's definitions into any other language.**

This is the fundamental gap. Unlike Chinese lexicography where CC-CEDICT (English), CFDICT (French),
and HanDeDict (German) provide community baselines, Strong's definitions exist almost exclusively
in English. What does exist:

| Language | What Exists | Source | License | Coverage |
|----------|-------------|--------|---------|----------|
| English | Complete (base + enhanced) | openscriptures, STEPBible | PD / CC BY 4.0 | 14,298 entries |
| Spanish | Partial NT glosses only | eliranwong/OpenGNT | CC BY-SA 4.0 | ~5,600 Greek entries |
| All others | **Nothing open** | — | — | 0 |

Commercial Strong's translations exist (Nueva Concordancia Strong Exhaustiva in Spanish, Korean
스트롱 concordances) but are copyrighted and not usable.

### 1.5 Tagged Bible Texts (Strong's Numbers in Context)

These provide the original-language text tagged with Strong's numbers — essential for evaluation:

| Dataset | Coverage | License |
|---------|----------|---------|
| [openscriptures/morphhb](https://github.com/openscriptures/morphhb) | Full Hebrew OT (WLC) | CC BY 4.0 |
| [STEPBible TAHOT](https://github.com/STEPBible/STEPBible-Data) | Hebrew OT, disambiguated | CC BY 4.0 |
| [STEPBible TAGNT](https://github.com/STEPBible/STEPBible-Data) | Greek NT (NA27/28, TR, SBL, Byz, WH) | CC BY 4.0 |
| [eliranwong/OpenGNT](https://github.com/eliranwong/OpenGNT) | Greek NT + Spanish interlinear | CC BY-SA 4.0 |
| [tahmmee/interlinear_bibledata](https://github.com/tahmmee/interlinear_bibledata) | OT + NT interlinear | PD |
| Berean Bible (berean.bible) | English interlinear with Strong's | PD (since 2023) |

### 1.6 Parallel Bible Corpora (Evaluation Data)

| Corpus | Languages | License | Use |
|--------|-----------|---------|-----|
| [BibleNLP/ebible](https://huggingface.co/datasets/bible-nlp/biblenlp-corpus) | 833 languages, 1,009 translations | Mixed (many CC) | Ground truth evaluation |
| [christos-c/bible-corpus](https://github.com/christos-c/bible-corpus) | ~100 languages | Mixed/academic | Evaluation baseline |
| Targum corpus (arXiv:2602.09724, Feb 2026) | 657 NT translations | Academic | Recent, deep English coverage |
| Mayer & Cysouw | NT in 1,169 languages | Academic | Typological evaluation |

---

## 2. What Is Possible

### 2.1 The Pipeline (Dictmaster Analogy)

```
Strong's (PD)  ──→  Parse 14,298 entries
STEPBible      ──→  Enhanced English definitions    ──→  Master DB
OpenGNT        ──→  Spanish NT glosses (community)  ──→  (keyed by Strong's #)
                                                          │
                                                    LLM Backfill
                                                    (MiniMax M2.5)
                                                          │
                                                          ▼
                                              18 languages × 14,298 entries
                                              = ~257,000 definitions
```

### 2.2 Cost and Time Estimate

Dictmaster: 428K entries × 18 langs = 7.7M defs, ~$20 (MiniMax Coding Plan), ~23 hours.

Strong's: 14K entries × 18 langs = 252K defs → **~$0.50, ~45 minutes**.

The entire project could run in under an hour. This is a trivial cost.

### 2.3 Evaluation: The Killer Advantage

The evaluation story is **dramatically stronger** than Paper B:

1. **Non-circular evaluation via Bible translations**: For each Strong's entry, identify its
   verse occurrences → look up those verses in target-language Bible translations → check whether
   the LLM-generated gloss aligns with how professional translators rendered the word. This
   eliminates the circular evaluation problem (Paper B's 87.3% was measured by sending community
   defs as context to the LLM, then evaluating whether the LLM used that context).

2. **Canonical sense IDs eliminate disambiguation errors**: Strong's H2617 (חֶסֶד, chesed,
   lovingkindness) is unambiguous. In Chinese, determining which sense of a polysemous character
   applies requires additional disambiguation — a major error source.

3. **Expert validation is feasible**: 14K entries is small enough that a domain expert can
   review the full output for a single language. This is impossible for 428K Chinese entries.

4. **Multiple independent translations as ground truth**: For major languages (French, German,
   Spanish), there are multiple Bible translations spanning centuries, providing robust consensus.

### 2.4 What Would Be Novel

1. **First open multilingual Strong's lexicon** — nobody has done this
2. **LLM translation of classical-language lexical resources** — extends the Dictionarium Sinicum
   method from modern to classical/dead languages
3. **Non-circular evaluation methodology** — Bible translations as independent ground truth
4. **Replicable pipeline** — same code, different lexicon, demonstrating generalizability

---

## 3. How We Accomplish This

### Phase 1: Data Acquisition and Schema

1. Parse `openscriptures/strongs` (JSON/XML) into a master SQLite DB
2. Layer STEPBible TBESH/TBESG enhanced definitions (CC BY 4.0)
3. Extract Spanish NT glosses from OpenGNT (CC BY-SA 4.0)
4. Schema: `headwords(strong_num, lang, script, transliteration, pos, definition, source)`

### Phase 2: LLM Translation (MiniMax M2.5)

Same pipeline as dictmaster `backfill_langs.py`:
- Context-aware prompts with etymology, part of speech, usage examples from KJV renderings
- 18 target languages (same set as dictmaster: en, de, fr, es, ja, ko, ru, id, vi, ar, fa, hi, pt, th, tl, nl, sv, it)
- Batch processing with resume capability
- Cost: ~$0.50, time: ~45 minutes

### Phase 3: Evaluation

1. **Bible translation back-validation**:
   - For each Strong's number, get all verse references
   - For each verse, look up the target-language Bible translation (from eBible corpus)
   - Check alignment between generated gloss and actual rendering
   - Compute sense coverage and false sense rate (same metrics as Paper B)

2. **Cross-reference with existing scholarship**:
   - BDB (Hebrew, PD) and Abbott-Smith (Greek, PD) provide detailed English definitions
   - BDAG and HALOT exist but are copyrighted — can cite but not use as data

3. **Expert evaluation** (if available):
   - Biblical scholars with Hebrew/Greek + target language expertise
   - The biblical studies community has many such experts

### Phase 4: Packaging

- SQLite DB with FTS5 (same architecture as dictmaster.db)
- MCP server for AI agent access (reuse zhcorpus MCP pattern)
- Potential: integrate into existing Bible software ecosystems (SWORD modules, USFM)

---

## 4. Comparison with Dictionarium Sinicum (Paper B)

| Dimension | Paper B (Chinese) | Paper G (Biblical) |
|-----------|-------------------|-------------------|
| Source lexicon | CC-CEDICT (428K entries) | Strong's (~14K entries) |
| Source languages | Modern Chinese (living) | Biblical Hebrew/Greek (classical) |
| Community sources | 3 (en, fr, de) | 1.5 (en + partial es) |
| Sense disambiguation | Hard (polysemy) | Easy (Strong's numbers) |
| Evaluation | Circular (87.3%) | Non-circular (Bible translations) |
| Parallel data for eval | Limited | 833 languages, 1,009 translations |
| Scale | 7.7M definitions | 252K definitions |
| Cost | ~$20 | ~$0.50 |
| Time | ~23 hours | ~45 minutes |
| Expert reviewable? | No (too large) | Yes (14K per language) |
| Existing scholarship | Moderate | Centuries of lexicography |
| Practical audience | Chinese learners, NLP | Bible translators, 700+ languages |

### Narrative Arc (Papers B + G Together)

Paper B demonstrates the method. Paper G demonstrates **generalizability**:
- Different source language family (Sino-Tibetan → Semitic/Hellenic)
- Different era (modern → classical/ancient)
- Different evaluation (circular → non-circular)
- Same pipeline, same LLM, same target languages
- Together they show the approach works for any structured lexicon

---

## 5. Academic Positioning

### Related Work

- **Liebeskind & Liebeskind (LT4HALA 2020)**: Automatic Aramaic-Hebrew lexicon construction
  using Strong's numbers as alignment anchors. Closest precedent — but bilingual only, not
  multilingual, and uses statistical methods rather than LLMs.
- **Christodouloupoulos & Steedman (2015)**: "A massively parallel corpus: the Bible in 100
  languages" (315 citations). Foundational parallel corpus work.
- **Targum corpus (Rapacz & Smywinski-Pohl, 2026)**: 657 NT translations. Very recent.
- **eBible corpus (ISI/USC, 2023)**: 833 languages. Standard benchmark.
- **ETCBC database (VU Amsterdam)**: Most comprehensive computational Hebrew Bible database.

### Key Projects and Organizations

- **BibleNLP / PAB-NLP** (pabnlp.org): Partnership of Applied Biblical NLP. GitHub repos,
  HuggingFace datasets, tools for Bible translation.
- **SIL AI** (ai.sil.org): FLExTrans (rule-based MT), Lynx (AI translation drafting, coming soon).
- **STEPBible / Tyndale House**: Open scholarly data for biblical languages.
- **unfoldingWord**: Open-license translation resources (translationWords, UGL, UHAL).
- **CrossWire SWORD Project**: Open Bible software modules.

### Target Venues

**Best fit (workshops)**:
- **ALP (Ancient Language Processing)** — NAACL 2025, explicitly covers ancient languages.
  Website: ancientnlp.com
- **NLP4DH (NLP for Digital Humanities)** — ACL 2026 (San Diego, July 6). Published in ACL
  Anthology.
- **LT4HALA (Language Technologies for Historical and Ancient Languages)** — LREC 2020/2022/2024.
  Where Liebeskind's Aramaic-Hebrew paper appeared.

**Conferences**:
- **LREC-COLING** — resource papers (where eBible corpus appeared)
- **SBL (Society of Biblical Literature)** — Digital Humanities section, reaches biblical studies
  audience directly

**Journals**:
- **LREV** — rolling submissions, good for resource papers
- **Digital Scholarship in the Humanities** (Oxford UP)

### Framing Options

**Option A: Standalone paper** — "Lexicon Omnium Gentium: LLM-Powered Multilingual Expansion of
Strong's Concordance" — focuses on the biblical lexicon as a product and the non-circular
evaluation methodology.

**Option B: Companion to Paper B** — "From Modern to Ancient: Generalizing LLM Lexicon Expansion
Across Language Families and Eras" — frames as a methodological validation showing the dictmaster
pipeline generalizes beyond Chinese.

**Option C: Resource paper** — "An Open Multilingual Biblical Lexicon in 18 Languages" — focuses
on the resource itself and its utility for Bible translation teams working in under-resourced
languages.

---

## 6. Unique Advantages of This Project

1. **Immediate practical value**: Bible translation is active in 700+ languages. SIL, Wycliffe,
   and United Bible Societies are well-funded organizations actively seeking AI/NLP solutions.
   A multilingual Strong's lexicon would be directly useful for translation teams.

2. **The evaluation story sells the paper**: Non-circular evaluation using 833-language parallel
   Bible corpus is a methodological contribution independent of the lexicon itself.

3. **Tiny cost, huge impact**: $0.50 and 45 minutes to produce a resource that doesn't exist
   anywhere in the world. The cost-effectiveness argument is even stronger than Paper B.

4. **Natural extension of existing work**: Same tools, same pipeline, same LLM — demonstrates
   that the approach is a general method, not a one-off for Chinese.

5. **Enormous existing community**: Biblical scholars, Bible software users, translation teams,
   digital humanities researchers — all potential users and reviewers.

---

## 7. Open Questions

- [ ] Should we use Extended Strong's (with sub-sense disambiguation) or base Strong's numbers?
- [ ] Which English definition to send to the LLM: raw Strong's (1890), STEPBible enhanced, or both?
- [ ] Should the evaluation sample all 833 eBible languages or focus on our 18 target languages?
- [ ] License choice: CC BY 4.0 (simpler) vs CC BY-SA 4.0 (if using unfoldingWord data)?
- [ ] Repo name: `strongs-multilingual`? `lexicon-omnium-gentium`? `biblical-lexicon`?
- [ ] Should we also include Louw-Nida semantic domain numbers (complementary to Strong's)?
- [ ] Partner with BibleNLP/PAB-NLP for distribution and visibility?

---

## 8. Resources

### GitHub Repos (Data Sources)
- https://github.com/openscriptures/strongs — canonical Strong's data
- https://github.com/openscriptures/HebrewLexicon — BDB + Strong's bridge
- https://github.com/openscriptures/morphhb — tagged Hebrew Bible
- https://github.com/STEPBible/STEPBible-Data — enhanced scholarly data
- https://github.com/eliranwong/OpenGNT — Greek NT + Spanish interlinear
- https://github.com/BibleNLP/ebible — 833-language parallel corpus
- https://github.com/scrollmapper/bible_databases — 140+ translations
- https://github.com/jcuenod/awesome-bible-data — curated index
- https://github.com/biblenerd/awesome-bible-developer-resources — developer resources
- https://github.com/markomanninen/strongs3 — Python 3 Strong's tools

### Academic References
- Liebeskind & Liebeskind (2020). Automatic Construction of Aramaic-Hebrew Translation Lexicon. LT4HALA.
- Christodouloupoulos & Steedman (2015). A massively parallel corpus: the Bible in 100 languages. (315 citations)
- Rapacz & Smywinski-Pohl (2026). Targum: A Multilingual NT Translation Corpus. arXiv:2602.09724.
- eBible Corpus (ISI/USC, 2023). Data and Model Benchmarks for Bible Translation.
- van Peursen & Kingham (2018). ETCBC Database of the Hebrew Bible.

### Organizations
- BibleNLP / PAB-NLP — pabnlp.org
- SIL AI — ai.sil.org
- Tyndale House / STEPBible — stepbible.org
- unfoldingWord — unfoldingword.org
- CrossWire SWORD Project — crosswire.org
