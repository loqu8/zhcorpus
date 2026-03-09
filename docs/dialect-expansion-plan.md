# Dialect Expansion Plan: Phase 2 (Production)

Status: Steps 1-3 COMPLETE (2026-03-09). Step 4 + Phase 3 pending.

## Licensing Constraints

| Source | License | Status |
|--------|---------|--------|
| WikiHan | CC BY-SA 4.0 | **GO** — production safe |
| CDDB/Hou2004 | CC BY 4.0 | **GO** — production safe |
| Rime-cantonese | CC BY 4.0 | **GO** — already partially imported |
| common-tl | MIT | **GO** — runtime tool |
| MCPDict | GPL-3.0 | **NO** — copyleft, excluded from production |
| Xiaoxuetang | Academic (Academia Sinica) | **PENDING** — write letter, wait for reply |
| All current sources | CC BY-SA / CC0 / Unicode ToU | **GO** — already in DB |

## Current State

### Single-Character

| Dialect | Chars | Coverage |
|---------|-------|----------|
| Cantonese | 16,547 / 17,593 | 94.1% — **done** |
| Hokkien | 5,501 / 17,593 | 31.3% |

### Word-Level

| Dialect | Multi-char forms | % of multi-char headwords |
|---------|-----------------|--------------------------|
| Cantonese | 114,768 | 28.5% |
| Hokkien | 110,166 | 14.5% |

## Production-Safe Expansion (no AI backfill)

### What We Get

**Single-char Hokkien: 5,501 → 6,751 (+23%)**
- WikiHan: +1,185 new chars (CC BY-SA 4.0, POJ romanization, multi-reading)
- CDDB Hou2004 Xiamen+Shantou: +72 new chars (CC BY 4.0, IPA)
- (Deduped — some overlap between sources)

**Single-char Cantonese: 16,547 → 18,628 (+13%)**
- WikiHan: +2,081 new chars (CC BY-SA 4.0, Jyutping)

**Word-level Cantonese: 114,768 → ~218K (+90%)**
- Rime-cantonese words: +103,074 entries (CC BY 4.0, parser exists)

**Word-level Hokkien: 110,166 (unchanged)**
- No new word-level sources in production-safe set
- Already strong from ChhoeTaigi (taihua 40K, maryknoll 28K, etc.)

### Is This Solid?

**Cantonese: Excellent.** 99.9% single-char was already done. Adding 103K word-level
readings from rime-cantonese nearly doubles compound coverage. This is comprehensive
enough for any product (iCE, Intuition Reader, Copyworks).

**Hokkien: Good, with known limits.** 23% increase in single-char is meaningful but
modest. The real strength is the existing 110K word-level forms. For practical use:
- HSK 1-6 (~2,600 chars): likely 90%+ covered already
- Common daily vocabulary: strong coverage from taihua (91K Mandarin↔Hokkien pairs)
- Rare/literary chars: this is where the gap remains

**What we're missing without MCPDict/xiaoxuetang**: ~6,500 additional single-char
Hokkien readings (mostly literary forms, archaic chars, and Chaozhou variants). These
matter for completeness and Paper E, but not for worksheets or reader products.

**What we're missing without AI backfill**: nothing critical. The production sources
give us real, attested readings. AI-generated readings would be speculative for chars
that don't have established Hokkien pronunciations.

## Plan: 4 Steps

### Step 1: Import WikiHan (1 hr)

New parser in `tools/dictmaster/parsers/dialect.py`:
- Read `wikihan-romanization.tsv`
- Hokkien column → `dialect='nan'`, `source='wikihan'`
- Cantonese column → `dialect='yue'`, `source='wikihan'`
- Handle multi-reading (slash-separated: `bé/bée/má`) — take all readings
- Match Character against existing headwords
- Also store IPA from `wikihan-ipa.tsv` if we add the `ipa` column

WikiHan has 8 varieties. For now, import Hokkien + Cantonese. The other 6
(Gan, Hakka, Jin, Wu, Xiang, Middle Chinese) are available if we ever expand.

### Step 2: Import CDDB Hou2004 Min entries (1 hr)

Parse `datasets/Hou2004/words.tsv` for DOCULECT in (Xiamen, Shantou):
- Extract single chars from CHARACTERS column
- IPA from VALUE column
- Store with `source='hou2004-xiamen'` / `source='hou2004-shantou'`
- Small yield (+72 chars) but adds IPA data and a citable academic source

### Step 3: Import rime-cantonese words (1 hr)

Modify existing `import_rime_cantonese()` in `parsers/dialect.py`:
- Remove `if len(char) != 1: continue` filter
- Process `jyut6ping3.words.dict.yaml` (103,074 entries)
- Skip `jyut6ping3.phrase.dict.yaml` (330K, mostly proper nouns — low value)
- Match multi-char entries against existing headwords
- Source stays `rime-cantonese`

### Step 4: Cross-validate and document (2 hrs)

- Compare our Hokkien coverage against WikiHan (now both in DB)
- Generate coverage by HSK frequency tier
- Update Paper E research notes with findings
- Update MCP `get_dialect_forms()` / `word_report()` if needed

## After Pending Approvals

When xiaoxuetang permission comes through:
- Import Xiamen (#222): +~1,500 Hokkien chars with 文/白 annotations
- Import all 41 Min points: +~1,600 chars total
- Adds structured IPA with initial/final/tone separation
- May need schema addition for `initial`, `final`, `tone_value`, `tone_class`, `reading_type`

## Tone Sandhi Strategy

**Store citation forms. Apply sandhi at runtime.**

- Citation forms are what dictionaries record (stable, authoritative)
- Sandhi rules are algorithmic (97% accuracy, ROCLING 2012)
- `common-tl` (MIT) can serve as basis for runtime sandhi engine
- Different products may want different display (show both? highlight change?)
- For Cantonese: minimal sandhi, not a concern

## Phase 3: Cantonese-First Headwords

**Problem**: 22,414 rime-cantonese word entries don't match any Mandarin headword.
These are genuine Cantonese words that don't exist in Standard Written Chinese.

**Breakdown**:
- 3,914 with Cantonese-specific characters (嘅嘢唔冇啲嗰etc.)
- 18,024 are 2-3 char compounds (銀紙, 返工, 攞嘢)
- 12,028 are 4+ char phrases (lower priority)
- Only 206 contain truly unknown characters

**Use case**: HK informal text (LIHKG, WhatsApp, subtitles, HK01 lifestyle).
HK formal news is 95%+ Standard Written Chinese — already covered.

**Phased approach**:
1. **Phase 3a**: Add ~2,800 Cantonese-char words not yet in headwords (CC-Canto already created ~1,100)
2. **Phase 3b**: Add ~18K 2-3 char compounds as new headwords with `dialect_origin='yue'` tag
3. **Phase 3c (defer)**: 12K 4+ char phrases — phrase book territory

**Required work**:
- Add `dialect_origin` column to headwords (nullable, default NULL = Mandarin)
- Import script: create headwords from unmatched rime entries
- Targeted MiniMax translation run for English glosses on new entries
- Same pipeline as existing headwords — no architectural change

## License Attribution Requirements

**All products shipping dialect data (Copyworks, iCE, Intuition Reader) MUST include
attribution for the following sources.** This is a legal requirement of the CC BY / CC BY-SA licenses.

### Required Attribution (must appear in About/Credits/Documentation)

| Source | License | Attribution Text |
|--------|---------|-----------------|
| CC-CEDICT | CC BY-SA 4.0 | "CC-CEDICT by MDBG, CC BY-SA 4.0" |
| CC-Canto | CC BY-SA 3.0 | "CC-Canto by Pleco/MDBG, CC BY-SA 3.0" |
| Rime-cantonese | CC BY 4.0 | "Rime Cantonese Input dictionary, CC BY 4.0, https://github.com/rime/rime-cantonese" |
| WikiHan | CC BY-SA 4.0 | "WikiHan (Chang et al., COLING 2022), CC BY-SA 4.0" |
| CDDB/Hou2004 | CC BY 4.0 | "Chinese Dialect Database (List 2019, Hou 2004), CC BY 4.0, DOI:10.5281/zenodo.3534942" |
| Unihan | Unicode ToU | "Unicode Unihan Database, Unicode Terms of Use" |
| ChhoeTaigi (taihua) | CC BY-SA 4.0 | "ChhoeTaigi 台華線頂對照典, CC BY-SA 4.0" |
| ChhoeTaigi (itaigi) | CC0 | No attribution required (but nice to include) |
| ChhoeTaigi (maryknoll) | CC BY-NC-SA 3.0 | "Maryknoll Taiwanese-English Dictionary, CC BY-NC-SA 3.0" |
| ChhoeTaigi (embree) | CC BY-NC-SA 3.0 | "Embree Taiwanese-English Dictionary, CC BY-NC-SA 3.0" |
| ChhoeTaigi (kauiokpoo) | CC BY-ND 3.0 | "甘字典 Kam Dictionary, CC BY-ND 3.0" |
| ChhoeTaigi (taioankichhoo) | CC BY-SA 4.0 | "台灣白話基礎語句, CC BY-SA 4.0" |
| Taibun | MIT | "Taibun Taiwanese Hokkien Transliterator (andreihar/taibun), MIT" |
| Wiktextract | CC BY-SA 3.0 | "Wiktextract Chinese (kaikki.org), CC BY-SA 3.0" |

### NC (Non-Commercial) Warning

**Maryknoll and Embree are CC BY-NC-SA 3.0.** If Copyworks or iCE are sold commercially,
these two sources must either be:
1. Excluded from commercial builds, OR
2. Used under a separate license agreement with the rights holders

Currently these provide 57,662 Hokkien forms (36% of Hokkien data). Excluding them
would reduce Hokkien coverage but not catastrophically — taihua (48K, CC BY-SA) and
itaigi (10K, CC0) cover the most common vocabulary.

### Kauiokpoo (CC BY-ND 3.0) Warning

**No derivatives.** The data can be redistributed but not modified. If we transform
or restructure it (which we do — extracting into SQLite), this may violate ND.
Conservative approach: exclude from commercial builds or get permission.

### Share-Alike (SA) Implications

CC BY-SA sources (CC-CEDICT, CC-Canto, WikiHan, taihua, taioankichhoo) require that
**derivative works are shared under the same or compatible license**. This means:
- The dictmaster.db file itself (if distributed) must be CC BY-SA
- App binaries that merely *query* the data at runtime are NOT derivatives (safe)
- Exported subsets bundled with the app ARE derivatives → include license file

### Recommended Copyworks Implementation

Add an "Acknowledgements" or "Data Sources" screen accessible from About:
```
Cantonese pronunciation data from:
  • CC-CEDICT/CC-Canto (CC BY-SA 4.0/3.0, MDBG)
  • Rime Cantonese Input (CC BY 4.0)
  • Unicode Unihan Database
  • WikiHan (Chang et al., COLING 2022, CC BY-SA 4.0)

Hokkien pronunciation data from:
  • ChhoeTaigi Project (CC BY-SA 4.0/CC0)
  • WikiHan (Chang et al., COLING 2022, CC BY-SA 4.0)
  • Chinese Dialect Database (List 2019, CC BY 4.0)

Full license texts: [link or bundled file]
```

## Action Items

- [x] Step 1: WikiHan import (38,794 forms — 13,457 nan + 25,337 yue)
- [x] Step 2: CDDB Hou2004 import (518 forms — Xiamen + Shantou + Guangzhou)
- [x] Step 3: Rime-cantonese words import (80,660 multi-char forms added)
- [x] Back up dictmaster.db before imports
- [ ] Step 4: Cross-validate, update Paper E notes
- [ ] Write letter to Academia Sinica re: xiaoxuetang commercial use
- [ ] Phase 3a: Add Cantonese-char headwords (~2,800 new)
- [x] Step 5: Import taibun (MIT, +39,814 forms)
- [x] Step 6: Import wiktextract Hokkien (CC BY-SA 3.0, +25,606 forms)
- [ ] Phase 3b: Add 2-3 char Cantonese compounds (~18K new headwords)
- [ ] Resolve NC licensing for Maryknoll/Embree (exclude or get permission)
- [ ] Resolve ND licensing for Kauiokpoo (exclude or get permission)
- [ ] Add attribution screen to Copyworks
- [ ] Bundle license texts with exported DB files
