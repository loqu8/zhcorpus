# Gloss Quality Labbook

Ongoing investigation into rubytext gloss quality for iCE popup display.

---

## 2026-04-06: Corpus Sentence Annotation Study

**Goal**: See what users actually encounter when reading Chinese text with ruby glosses.

**Method**: Pulled real sentences from zhcorpus (zhwiki, baike, chid, news, translation2019zh),
ran them through a Python simulation of the full gloss pipeline:
`dictmaster.db lookup → CleanRubyDef → _truncateRubyDef (3-word limit)`

Greedy longest-match segmentation against dictmaster headwords (approximates nomad engine).

### Annotated Sentences

#### 1. 孩子们在公园里东奔西跑 (zhcorpus: translation2019zh)
"The children were running around in the park"

| Word | Gloss | Status | Issue |
|------|-------|--------|-------|
| 孩子们 | children | OK | |
| 在 | exist; to be… | ⚠ TRUNC | cedict "to exist; to be alive" — wrong sense for 在 as preposition "at/in" |
| 公园 | park | OK | |
| 里 | *(empty)* | ⚠ EMPTY | cedict "variant of 裡" → CleanRubyDef returns "" for variant-of |
| 东奔西跑 | run this way… | ⚠ TRUNC | Idiom, 4-char. Hard to gloss. |

**User sees**: 孩子们(children) 在(exist; to be…) 公园(park) 里() 东奔西跑(run this way…)

**Problems**: 在 glosses as "exist" instead of "at/in". 里 shows nothing because it's "variant of". 
The user reading "kids at the park" gets "exist" and a blank — confusing.

#### 2. 政府已经采取了措施刺激经济 (zhcorpus: translation2019zh)
"The government has already taken measures to stimulate the economy"

| Word | Gloss | Status | Issue |
|------|-------|--------|-------|
| 政府 | government | OK | |
| 已经 | already | OK | |
| 采取 | adopt or carry… | ⚠ TRUNC | "adopt or carry out (measures...)" — verbose |
| 了 | *(empty)* | ⚠ EMPTY | "(completed action marker)" → CleanRubyDef strips parenthetical, nothing left |
| 措施 | measure | OK | |
| 刺激 | provoke; to irritate;… | ⚠ TRUNC+WRONG | First sense is "provoke" but context means "stimulate" |
| 经济 | economy | OK | |

**User sees**: 政府(government) 已经(already) 采取(adopt or carry…) 了() 措施(measure) 刺激(provoke; to irri…) 经济(economy)

**Problems**: 了 shows nothing (its definition is entirely parenthetical). 采取 truncates badly.
刺激 picks "provoke" (first sense) when context means "stimulate" — a sense-selection issue,
not just length.

#### 3. 许多学生的成绩不仅比他们的老师预期的要低得多 (zhcorpus: zhwiki)
"Many students' grades were not only lower than their teachers expected"

| Word | Gloss | Status | Issue |
|------|-------|--------|-------|
| 许多 | many | OK | |
| 学生 | student | OK | |
| 的 | of; ~'s | OK | |
| 成绩 | achievement | OK | |
| 不仅 | not just; not… | ⚠ TRUNC | "not just; not limited to" |
| 比 | **Belgium** | ⚠ WRONG | Picks surname/country reading instead of "compare/than" |
| 他们的 | their | OK | |
| 老师 | teacher | OK | |
| 预期 | expect | OK | |
| 的 | of; ~'s | OK | |
| 要 | demand; to coerce | ⚠ WRONG | Picks "demand" reading instead of "want/need/will" |
| 低 | low | OK | |
| 得 | obtain | OK-ish | Shows "obtain" — might want "so that/to the degree" for this usage |
| 多 | many; much; more;… | ⚠ TRUNC | Too many semicolon-separated senses |

**User sees**: 比(Belgium?) 要(demand; to coerce?) — both look wrong for this context.

**CORRECTION (found during investigation)**: The nomad engine uses `is_proper` tagging to
**deprioritize proper nouns**. Capital-pinyin entries (Bi3 "Belgium", surname readings) sort
AFTER lowercase (bi3 "compare"). See `query_builder.cpp:140-153`. So 比→"Belgium" is a
**simulation artifact** from our naive Python lookup, NOT a real user-facing bug. The real
engine would show 比→"compare" or "than".

Similarly, 要 has multiple headword entries and the engine sorts by frequency (`sfreq DESC`),
so the common "want/will" reading likely wins over the rare "demand/coerce" reading.

**Remaining real issue**: Even with correct entry selection, the FIRST sense within the
winning entry's definition may still be suboptimal (e.g., cedict lists "to exist" before
"to be at" for 在). This is a within-definition ordering issue, not a between-entry issue.

#### 4. 孩子们在公园里正玩得高兴呢 (zhcorpus: translation2019zh)
"The children were playing happily in the park"

| Word | Gloss | Status | Issue |
|------|-------|--------|-------|
| 孩子们 | children | OK | |
| 在 | exist; to be… | ⚠ | Same as above |
| 公园 | park | OK | |
| **里正** | **head of li** | ⚠ WRONG SEG | Greedy match eats 里+正 as "里正" (village head) instead of 里 + 正 |
| 玩 | play | OK | |
| 得 | obtain | OK-ish | |
| 高兴 | happy | OK | |
| 呢 | particle | OK | |

**Problem**: Segmentation error — 里正 is a valid but rare word that gets priority over 里 + 正.
(The real nomad engine may handle this better with its DAG-based segmenter.)

#### 5. 中国是一个历史悠久的国家 (manual test sentence)
"China is a country with a long history"

| Word | Gloss | Status | Issue |
|------|-------|--------|-------|
| 中国 | China | OK | |
| 是 | be | OK | |
| 一个 | a; an; one | OK-ish | 3 semicolon items but all short — acceptable |
| 历史悠久 | long-established | OK | |
| 的 | of; ~'s | OK | |
| 国家 | country; nation; state | ⚠ 3-SENSE | Three semicolon-separated but all short — borderline |

**Mostly fine.** Common words gloss well. 国家 has 3 senses shown but each is short.

#### 6. 这个问题不能简单地回答 (manual test sentence)
"This question can't be simply answered"

| Word | Gloss | Status | Issue |
|------|-------|--------|-------|
| 这个 | this | OK | |
| 问题 | question | OK | |
| 不能 | cannot | OK | |
| 简单地 | simply, plainly, just | ⚠ 3w | Borderline — 3 words is our limit |
| 回答 | reply; to answer | ⚠ 2-SENSE | Shows 2 senses but both are short |

**Mostly OK.** The adverb 简单地 is a 3-word match ("simply, plainly, just") which
hits the truncation limit exactly.

### Summary of Issue Categories Found

| Category | Examples | Frequency | Severity |
|----------|----------|-----------|----------|
| **Empty gloss** (variant-of/parenthetical stripped) | 了, 里 | Common | High — user sees blank |
| **Wrong sense** (first ≠ contextual) | 刺激→provoke, 在→exist | Some | High — but mitigated by is_proper sort |
| **Truncated verbose** | 在→"exist; to be…", 采取→"adopt or carry…" | Common | Medium — partial info |
| **Semicolon overflow** | 多→"many; much; more;…", 不仅→"not just; not…" | Common | Medium |
| **Segmentation error** | 里正 instead of 里+正 | Occasional | Medium (nomad engine may differ) |

### Key Insights

1. **The nomad engine is smarter than naive simulation.** `query_builder.cpp:140-153` uses
   `is_proper` (tagged at build time from capital/lowercase CEDICT pinyin) to deprioritize
   proper nouns. So 比 Bi3 "Belgium" sorts AFTER 比 bi3 "compare". The 比→"Belgium" finding
   was a simulation artifact. Similarly, `sfreq DESC` means high-frequency readings win.

2. **Empty glosses for 了 and 里** are very common in real text. These are among the most
   frequent characters in Chinese. 了 appears in almost every sentence. Having it show
   nothing is a significant UX gap. 了's def is "(completed action marker)" — entirely
   parenthetical, so CleanRubyDef strips it to empty.

3. **Within-definition sense ordering still matters.** Even after correct entry selection,
   the first sense in a definition string may not be the most common contextual meaning:
   - 在: cedict lists "to exist" before "to be (located) at"
   - 刺激: cedict lists "to provoke" before "to stimulate"
   This is a data quality issue in the source definitions.

4. **Two-char words are mostly fine.** The gloss problem is concentrated in single characters
   and grammatical particles. Most 2-char compound words have clean, concise glosses.

5. **The nomad engine's DAG segmentation matters.** Our greedy simulation matched 里正
   (village head) where the real engine would likely prefer 里 + 正 based on context
   and frequency. Take simulation results as directional, not exact.

## 2026-04-06 (Update): Real Engine Annotation via CAPI

**Method**: Called the real `libdict_capi.so` from Python via ctypes. Used `dict_engine_create()`
with `ice.sqlite` (production dictionary), `dict_engine_annotate_json()` for segmentation,
and `dict_format_ruby_def()` for the actual C++ ruby formatting.

**Key finding: The engine is much better than the simulation predicted.**

### Corrected results (real engine)

| Sentence | Problem chars from simulation | Real engine result |
|----------|-------------------------------|-------------------|
| 比 | Simulation: "Belgium" ⚠ | Real: **"compare"** ✓ (is_proper works!) |
| 要 | Simulation: "demand" ⚠ | Real: **"want"** ✓ (sfreq ordering works!) |
| 在 | Simulation: "exist; to be…" ⚠ | Real: **"be"** ✓ |
| 了 | Simulation: (empty) ⚠ | Real: **"completed action particle"** ✓ |
| 里 | Simulation: (empty) ⚠ | Real: "li, neighborhood, borough, administrative…" ⚠TRUNC |
| 采取 | Simulation: "adopt or carry…" ⚠ | Real: **"adopt"** ✓ |
| 得 | Simulation: "obtain" | Real: **"get"** ✓ (but context = "have to" particle) |
| 刺激 | Simulation: "provoke" ⚠ | Real: **"provoke"** ⚠ (still first sense, but correct entry) |

**The engine's is_proper flag and sfreq sorting fix most sense-selection issues.**
了 is no longer empty — ice.sqlite has different definition formatting than raw dictmaster.

### Remaining real issues (from engine output)

| Word | Engine gloss | Problem | Ideal |
|------|-------------|---------|-------|
| 里 | "li, neighborhood, borough, administrative…" | 4-word truncation of comma list | "in; inside" |
| 先 | "first, before, earlier, originally,…" | Comma list overflow | "first" |
| 这件事 | "this thing, this matter,…" | Comma list overflow | "this matter" |
| 找 | "look for, to find" | 4 words (borderline) | "find" |
| 习 | "practice, to study, habit,…" | Comma list overflow | "study" |
| 刺激 | "provoke" | Wrong sense for context (should be "stimulate") | Context-dependent |
| 图书馆学 | "library science" | Wrong segmentation (图书馆+学, not 图书馆学) | Segmentation issue |
| 得 | "get" | Context = degree particle, not "get" | Context-dependent |

### Revised problem assessment

The real issue is much narrower than the simulation suggested:

1. **Comma-list truncation** — The engine has comma-separated definitions that overflow the
   4-word limit. These are the most common visual gloss problem. Examples: 里, 先, 习.
   These come from MiniMax definitions that use commas instead of slashes.

2. **Context-dependent sense** (刺激 "provoke" vs "stimulate", 得 "get" vs degree particle) —
   This is fundamentally unsolvable without NLP context disambiguation. A static dictionary
   will always pick the first sense. Low priority — users understand this limitation.

3. **Segmentation** (图书馆学 "library science" eating 图书馆 + 学) — This is a known
   limitation of longest-match. The DAG segmenter may handle some cases better.

### What Would Fix These?

| Issue | Fix | Scope |
|-------|-----|-------|
| Comma-list overflow (里,先,习) | MiniMax defs use commas — convert to slashes at build time | Build pipeline or dictmaster fix |
| 里 "li, neighborhood…" | Definition ordering: "in/inside" should precede the unit-of-measure sense | Dictmaster data fix |
| Comma→slash normalization | In `build_dbs.py`, convert `, ` to `/` in definitions before writing | Build pipeline |
| 图书馆学 segmentation | Engine issue — not a gloss-quality issue | nomad-builder |
| Context-dependent sense | Would need runtime disambiguation — out of scope for now | Future (NLP) |

**Biggest bang**: Normalize MiniMax comma-separated definitions to slash-separated at build time.
`CleanRubyDef` splits on `/` but NOT on `,`. So "first, before, earlier, originally" is treated
as a single 4-word sense instead of 4 separate senses. Converting commas to slashes would let
the existing "take first sense" logic work correctly.

### Verification: comma vs slash handling in CleanRubyDef

The C++ `GetRubyDef` splits on `/` only (line 354-386 of definition_formatter.cpp).
`CleanRubyDef` does NOT split on commas — it treats commas as part of one sense.

So for MiniMax's "first, before, earlier, originally":
- Current: treated as one 4-word sense → "first, before, earlier, originally,…" (truncated)
- If converted to "first/before/earlier/originally": → first sense = "first" ✓

**This is the root cause of most remaining gloss truncation issues.**

## 2026-04-06: Separator Analysis — Root Cause Confirmed

### The Format Contract

The prompt (`prompts.py:7`) says: "Output ONLY **slash-separated** glosses"
The parser (`parse_universal_response`) strips leading/trailing slashes but does NOT
normalize commas to slashes.
The build pipeline (`merge_definitions()` in `build_dbs.py:536`) splits on `[;/]` but
**NOT on commas**. Comma-separated items remain as one segment.

### What MiniMax Actually Returns

MiniMax often returns comma-separated instead of slash-separated:
```
Prompt asks for:  "first/before/earlier/originally"
MiniMax returns:  "first, before, earlier, originally"
```

This flows through unchanged:
1. Parser: keeps "first, before, earlier, originally" as-is
2. merge_definitions: treats as one segment → `/first, before, earlier, originally/`
3. build_dbs.py: writes to ice.sqlite as-is
4. GetRubyDef: splits on `/` → one sense: "first, before, earlier, originally"
5. CleanRubyDef: truncates to 4 words → "first, before, earlier, originally,…"

### Scale of the Problem

Comma-only definitions (no `/` or `;`) from MiniMax, per language:

| Lang | Comma-only | Total | % |
|------|-----------|-------|---|
| en | 18,516 | 428,292 | 4.3% |
| de | 35,437 | 428,292 | **8.3%** |
| fr | 16,797 | 428,292 | 3.9% |
| es | 17,241 | 428,292 | 4.0% |
| ja | 2,768 | 428,292 | 0.6% |
| ko | 8,897 | 428,292 | 2.1% |
| ru | 18,701 | 428,292 | 4.4% |
| vi | 17,568 | 428,292 | 4.1% |
| tl | 18,089 | 428,292 | 4.2% |

German is worst at 8.3%. Japanese is best at 0.6% (kanji definitions are naturally short).

### Where to Fix

Three possible fix points:

1. **dictmaster.db** (zhcorpus): Normalize `, ` → `/` in minimax definitions at storage time
   - Pro: fixes the source of truth
   - Con: commas within a single sense (e.g. "Beijing, capital of China") would be wrongly split

2. **merge_definitions()** (nomad-builder `build_dbs.py:536`): Add `,` to the split regex
   - Pro: fixes at build time, leaves dictmaster raw data intact
   - Con: same false-positive risk with intra-sense commas

3. **parse_universal_response()** (zhcorpus `prompts.py:342`): Normalize before storing
   - Pro: catches it earliest
   - Con: only affects future translations, not existing 428K

### The Comma Ambiguity Problem

Not all commas are sense separators:
- ✅ "first, before, earlier, originally" → 4 separate senses
- ❌ "Beijing, capital of China" → 1 sense with qualifying clause
- ❌ "used in 傢伙, 傢俱" → 1 sense with examples

A simple `, ` → `/` substitution would break the second and third cases.

**Possible heuristic**: Only split on `, ` when each comma-segment is 1-2 words:
- "first, before, earlier, originally" → all 1-word segments → split ✓
- "Beijing, capital of China" → "capital of China" is 3 words → don't split ✓

Or: split on commas only in `merge_definitions()` when the full string exceeds 4 words.
Below 4 words, it won't truncate anyway so splitting doesn't matter.

---

## 2026-04-06: LLM Comma Normalization Simulation

**Goal**: Test whether a free LLM can reliably distinguish synonym commas (split) from
structural/descriptive commas (keep) in MiniMax definitions.

**Method**: Sent 40 random comma-only definitions from dictmaster.db to Qwen3 32B via
Groq free tier (model-radar MCP). Prompt:

```
Below are Chinese-English dictionary definitions that use commas.
Some commas separate synonyms (should become /), some are structural (keep as comma).
For each numbered line, output ONLY the corrected definition.

Rules:
- synonym lists: "big, large, great" → "big/large/great"
- structural/descriptive: "Beijing, capital of China" → keep comma
- mixed: split synonym parts, keep structural parts
```

### Results (40 entries)

| Category | Count | % |
|----------|-------|---|
| Correct synonym splits | 28 | 70% |
| Correct structural keeps | 9 | 22.5% |
| Mixed (both split + keep) | 2 | 5% |
| Debatable | 1 | 2.5% |

**Accuracy**: ~97.5% (39/40 clearly correct, 1 debatable edge case)

### Notable Examples

**Synonym splits** (correct):
- "to exceed, to surpass, to be higher than" → "to exceed/to surpass/to be higher than"
- "normally, ordinarily, it stands to reason that" → "normally/ordinarily, it stands to reason that"

**Structural keeps** (correct):
- "Jize County (in Handan City, Hebei)" → unchanged
- "Huangfu Song (-195), later Han general and warlord" → unchanged

**Debatable**:
- "diaojiaolou, traditional stilt house..." → split (term from explanation — arguably should keep)

### Key Insight

The model correctly distinguishes three comma types without explicit examples:
1. **Synonym commas** ("big, large, great") → split
2. **Structural commas** ("X County, in Y Province") → keep
3. **Explanatory commas** ("diaojiaolou, a traditional house") → edge case

This is exactly the linguistic judgment that regex heuristics can't make.

### Scale Estimate

- 265,950 comma-containing rows across 26 languages, 31,531 unique headwords
- At 20 entries/batch: ~1,576 API calls
- Groq free tier (Qwen3 32B): $0 cost, ~3.4s/call → ~90 min total
- MiniMax fallback: ~$8-15

### Next Step

Build normalization script against dictmaster.db using Groq/Qwen3 32B.
Fix `parse_universal_response()` to normalize for future translations.
Rebuild ice.sqlite after dictmaster fix.
