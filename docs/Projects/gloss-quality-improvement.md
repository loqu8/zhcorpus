# Gloss Quality Improvement for Rubytext Display

**Date**: 2026-04-06
**Status**: Planning
**Scope**: ~1000+ single-char headwords with verbose MiniMax definitions that produce poor rubytext glosses

## Problem

Rubytext (small text above Chinese characters) needs **short, meaningful glosses** — ideally 1-3 words. Many single-character entries have MiniMax-generated definitions that are descriptive phrases rather than concise glosses. After truncation, these become meaningless fragments.

**Example**: 的 (de) should gloss as "of" but MiniMax might produce "structural particle indicating possession or modification" → truncated to "structural particle indicating…" → useless as rubytext.

## Truncation Pipeline (Three Layers)

The display pipeline applies three layers of truncation, none of which can rescue a bad source definition:

| Layer | Location | Rule | Limit |
|-------|----------|------|-------|
| **C++ `CleanRubyDef()`** | `nomad-builder/src/libdict/src/utils/definition_formatter.cpp:326-349` | Strip parentheses, brackets, prefixes ("to", "the", "abbr. for"), then truncate | 4 words + … |
| **Dart `_truncateRubyDef()`** | `ice/lib/widgets/magic_ruby_stack.dart:283-300` | Take first sense (before comma/semicolon), then truncate | 3 words + … |
| **Flutter visual** | `ice/lib/widgets/magic_ruby_stack.dart:190-200` | `maxLines: 1, TextOverflow.ellipsis` | pixel width (130px max cell) |

### Ice Single-Char Override

Ice already prefers chardata definitions for single characters (`magic_ruby_stack.dart:135-142`):
```dart
final isSingleChar = widget.headwordVm.text.runes.length == 1;
if (effectiveShowDefs && isSingleChar) {
  final charDef = nomad.getChardataDefinition(widget.headwordVm.text);
  if (charDef != null && charDef.isNotEmpty) {
    rubyDefOverride = _truncateRubyDef(charDef);
  }
}
```

But chardata definitions can also be verbose (sourced from Unihan + CC-CEDICT merge).

## Root Cause

MiniMax (and community dictionaries) optimize for **comprehension** — full explanations of meaning. Rubytext needs **recognition** — a 1-3 word reminder that triggers recall. These are different tasks.

### Failure Modes

| Mode | Example | Result After Truncation |
|------|---------|------------------------|
| **Descriptive phrase** | "structural particle indicating possession" | "structural particle indicating…" |
| **Multiple qualifiers** | "used in formal written Chinese to express" | "used in formal…" |
| **Geographic/usage context first** | "Mainland China slang for very" | "Mainland China slang…" |
| **Cross-reference** | "variant of 說, to speak" | "variant of 說…" |
| **Over-specified** | "the sound made when something falls" | "the sound made…" |

In all cases, the **core meaning gets pushed past the truncation boundary**.

## Definition Sources Available

| Source | Typical Style | Gloss Quality |
|--------|--------------|---------------|
| **CC-CEDICT** | Concise English glosses, slash-separated | Good for common words, verbose for rare |
| **Chardata (Unihan)** | Brief, sometimes cryptic | Variable |
| **MiniMax v2** | Full explanatory definitions, 26 langs | Poor for glosses — optimized for comprehension |
| **Wiktextract** | Multi-sense with glosses | Variable, often good first sense |

## Prior Art in This Project

- **Single-char retranslation** (`docs/experiments/single-char-retranslate.md`): Fixed ~200 wrong definitions using community anchors, but didn't address verbosity
- **v2 prompt design** (`tools/dictmaster/translate/prompts.py`): Community defs as anchors constrain sense selection but don't enforce brevity
- **UX gauntlet** (`ice/docs/resources/reviews/ux-designer-review-2026-03-10.md:87`): Recommended "single-word gloss, first sense, max ~8 characters" for parts breakdown

## Approach Options

## Data Analysis (2026-04-06)

29,165 unique single-char entries. Multiple EN definitions per entry from different sources.

### Correct methodology: split on `/` and `;` first

The Dart `_truncateRubyDef()` and C++ `CleanRubyDef()` both split on `/` and `;` before
counting words. So "to finish; to understand; clear" → first sense "to finish" → "finish"
(1 word after prefix stripping). The raw word count of the full definition is misleading.

After proper first-sense extraction (split on `/;`, strip parentheticals/brackets, strip
"to/the/a/an/abbr. for" prefixes):

### Per-language verbosity (all single-char EN defs)

| Lang | 1w | 2w | 3w | 4w | 5+w | % bad |
|------|-----|-----|-----|-----|------|-------|
| en | 26,477 | 10,453 | 8,138 | 7,638 | 6,800 | 11.3% |
| de | 20,289 | 9,063 | 5,648 | 3,877 | 2,809 | 6.6% |
| fr | 20,455 | 5,078 | 5,332 | 4,162 | 3,966 | 9.9% |
| es | 14,137 | 4,863 | 4,574 | 3,444 | 3,408 | 11.1% |
| ja | 32,185 | 983 | 330 | 83 | 68 | 0.2% |
| ko | 15,475 | 8,496 | 3,797 | 1,462 | 1,088 | 3.6% |
| ru | 14,040 | 7,251 | 3,518 | 3,233 | 2,238 | 7.3% |
| vi | 6,802 | 10,363 | 3,457 | 4,376 | 5,289 | 17.3% |
| tl | 13,601 | 3,491 | 5,791 | 3,050 | 4,358 | 14.3% |
| ar | 11,928 | 7,171 | 4,502 | 4,004 | 2,706 | 8.9% |

**Key insight**: This is NOT just an English problem. Vietnamese (17.3%) and Tagalog (14.3%)
are worse than English (11.3%). Spanish (11.1%) is equally bad. Only Japanese (0.2%) and
Korean (3.6%) are naturally concise. **A gloss solution needs to cover all 26 languages.**

### High-frequency chars with verbose best-available first-sense

186 entries with freq >= 1M where even the shortest available first-sense is >= 4 words.
These are the ones users actually see in rubytext.

The worst offenders are **grammatical particles and structural words** — the most common
characters in the language:

| Char | Freq | Best Available | Words | Problem |
|------|------|---------------|-------|---------|
| 得 de | 12.8M | "structural particle indicating result, degree, possibility" | 6w | Grammar explanation, not gloss |
| 們 men | 11.8M | "plural marker for pronouns and human nouns" | 7w | Grammar explanation |
| 地 di | 13.4M | "adverbial particle after reduplicated adjective" | 5w | Grammar explanation |
| 子 zi | 12.2M | "nominal suffix as in chair" | 5w | Grammar explanation |
| 嘛 ma | 9.6M | "modal particle indicating obviousness" | 4w | Grammar explanation |
| 著 zhe | 6.6M | "aspect particle indicating ongoing action or state" | 7w | Grammar explanation |
| 經 jing | 15.7M | "through, via, by means of" | 5w | Comma-separated alternatives |
| 理 li | 11.8M | "cut and polish jade" | 4w | Wrong reading selected |

Many are also **variant/archaic forms** ("old variant of X", "only used in XY") that appear
because frequency is shared across readings.

### Critical finding: most "problems" are secondary readings

The initial scan flagged 有 (freq 37M) as problematic, but that's the archaic you4 reading
("also, moreover, in addition, besides"). The common you3 reading ("to have") is fine (1 word
after "to" stripping). Same for 不, 上, 可, 日, 能 — all have a primary reading with a clean
gloss. The verbose entry is an obscure secondary reading.

**The real problem set is smaller than it appears.** After filtering to chars where ALL
readings have verbose best-first-sense: **2,394 chars** (down from ~7,900).

Of those 2,394, most are rare (freq < 100K). Only ~50 have freq > 1M.

### Pattern categorization (4,405 verbose entries across all readings)

| Pattern | Count | Example | Systematic Fix |
|---------|-------|---------|----------------|
| **other** (misc verbose) | 1,987 | 上 "musical note do in Kunqu" | LLM gloss needed |
| **only used in XY** | 809 | 不 "only used in 不不鐙兒" | Show XY's meaning or suppress |
| **old variant of X** | 550 | 㠯 "old variant of 以" | Resolve to X's gloss |
| **used in XY** | 449 | 傢 "used in 傢伙 and 傢俱" | Show primary compound meaning |
| **proper name** | 211 | 筑 "Name of a river" | "(river)" or "(place)" |
| **comma list** | 172 | 經 "through, via, by means of" | Take first item only |
| **variant of X** | 172 | 瞭 "unofficial variant of 瞭" | Resolve to X's gloss |
| **particle/suffix** | 35 | 得 "structural particle indicating result" | "(degree)" "(plural)" etc. |
| **classifier** | 20 | 通 "classifier for a bout of activity" | "clf." |

**5 of 9 categories are mechanically fixable** (old variant, variant, comma list, classifier,
and partially only-used-in/used-in). That's ~2,173 entries (49%) that don't need LLM help.

### Source comparison for high-frequency chars

| Char | CC-CEDICT 1st sense | MiniMax 1st sense | Wiktextract 1st sense |
|------|--------------------|--------------------|----------------------|
| 的   | of (1w)            | of (1w)            | Used in transcription (3w) |
| 了   | completed action marker (3w) | to finish... completely (7w) ⚠ | Used after a verb... (10w) ⚠ |
| 是   | to be... substantives only (6w) ⚠ | this; yes; true... (6w) ⚠ | this; this thing (3w) |
| 在   | to exist; to be alive (5w) ⚠ | to be; to exist; in (5w) ⚠ | to exist; to be present... (8w) ⚠ |
| 他   | third-person singular... (12w) ⚠ | he (1w) | he; him; she; her (4w) |
| 们   | plural marker for pronouns... (9w) ⚠ | plural suffix... (10w) ⚠ | (no short option) ⚠ |
| 个   | used in 自個兒... (5w) ⚠ | general classifier (2w) | this (1w) |

**Key insight**: No single source is consistently best. CC-CEDICT is verbose for 是, 在, 他, 们. MiniMax is verbose for 了. Wiktextract is verbose for 在, 人. The best gloss often comes from different sources per entry.

### The "unfixable" set

~3,112 entries where ALL sources produce >=5w first senses. These are mostly:
- Rare/archaic characters (㐄, 㫰, etc.)
- Characters that genuinely need explanation (Suzhou numerals, component descriptions)
- Characters with no simple English equivalent

These would need LLM-generated short glosses or could display pinyin-only in rubytext.

## Approach Options

## Approach Options (Revised — Multilingual)

Since Vietnamese (17.3%), Tagalog (14.3%), and Spanish (11.1%) are as bad or worse than
English (11.3%), an English-only fix is insufficient. The gloss solution must cover all
26 languages.

### Option A: `glosses` Table in dictmaster.db
New table: `glosses(headword_id, lang, gloss, source)`. Stores 1-3 word glosses per
headword per language. Populated in phases:
1. Rule-based extraction (pick shortest first-sense across sources per lang)
2. LLM pass for entries where all sources are verbose

**Pro**: Clean separation of concerns. Build pipeline reads glosses directly.
**Con**: 26× the generation work. Needs schema change + build pipeline update.

### Option B: LLM Gloss Generation (All 26 Languages)
Prompt: "Given these definitions for 得 (de), produce a 1-3 word gloss in each language."
Send all existing definitions as context. One API call per headword, same as translation.
For 186 high-freq + ~3,000 rare = ~3,200 entries × 1 call each = small run.

**Pro**: Best quality. LLM can compress "structural particle indicating result" → "(degree)".
**Con**: API cost (small — ~$3-5 on MiniMax for 3K entries).

### Option C: Improve Truncation Heuristics (C++ / Dart)
Teach `CleanRubyDef()` to handle specific patterns:
- "only used in XY" → suppress or show XY's meaning
- "old variant of X" → show X's meaning
- "classifier for X" → "clf."
- "structural particle..." → "(particle)"
- Comma-separated alternatives → take just the first

**Pro**: No data change needed. Fixes display immediately.
**Con**: Fragile heuristics. Doesn't fix the source. Language-specific rules needed × 26.

### Option D: Hybrid (Recommended)
1. **Phase 1** — Better heuristics in C++ `CleanRubyDef()` for the pattern categories
   (variant-of, only-used-in, classifier, particle). Immediate improvement, no data change.
2. **Phase 2** — Add `glosses` table. Populate with rule-based extraction for all 26 langs.
3. **Phase 3** — LLM pass for remaining verbose entries (~3K). Cheap, one-time.
4. **Phase 4** — Build pipeline reads `glosses` table, `CleanRubyDef()` becomes fallback only.

### Scale Estimate for Phase 3

- ~186 high-freq (>1M) entries that users see constantly
- ~3,000 rare chars where all sources are verbose
- At 20 entries/batch, ~160 API calls × 26 langs
- MiniMax at ~$0.005/call = **~$5 total**
- Could also do the 186 by hand for highest quality
