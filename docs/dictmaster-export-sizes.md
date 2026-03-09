# Dictmaster Export Size Estimates

Estimated dictionary sizes for Copyworks and Intuition SKUs across all 12
languages. Based on actual dictmaster.db measurements and validated against
the existing dictgen core.sqlite (2026-03-07).

## Source Data

```
Total headwords:           428,073
Single-char headwords:      30,546  (19,471 distinct simplified chars, 7,838 multi-reading)
Multi-char headwords:      397,527
Languages:                 12       (en de fr es sv ja ko ru id vi tl fa)
Coverage:                  98.6%    (all langs at 99.5%+)
```

## Reference: Current dictgen core.sqlite (English-only, 115K entries)

Validated table sizes from `dbstat` on the actual 135.7 MB production DB:

```
Component                  Measured     Notes
─────────────────────────  ──────────   ────────────────────────────────────
Entries_content            21.1 MB      114,959 rows (dict entries)
FTS4 Entries index         25.0 MB      Segments + docsize + stat
Terms_content + indexes    13.2 MB      297,318 term rows + autoindex
Terms FTS4 index            5.3 MB      Segments
TermEntries + indexes      11.2 MB      366,329 cross-refs
────────── dict subtotal   75.8 MB
characters + indexes        9.8 MB      103,007 chars + 4 indexes
strokes + index            34.4 MB      112,617 stroke paths (SVG)
dict_single_chars           1.6 MB      17,047 pre-joined rows
hsk tables                  2.5 MB      HSK + MinHSK + hsk_words/chars
DictFts5 (experimental)    10.9 MB      FTS5 with simple tokenizer
lessons                     0.2 MB      1,695 lesson entries
other (Rated, Fields)       0.1 MB
═══════════════════════════════════════════════════════════════════════════
TOTAL                     135.7 MB
```

### Derived scaling ratios (for estimating other languages)

```
FTS4 index  = 1.19x Entries_content        (25.0 / 21.1)
Terms total = 1.16x Entries_content        (24.5 / 21.1)
Chardata    = 48.5 MB fixed                (chars + strokes + hsk + dict_single)
```

---

## Copyworks SKU -- Single Characters Only

Each Copyworks edition ships **one target language** with ~30.5K single-char
headword entries plus chardata (strokes, HSK, radicals, etymology, decomposition).

### Definition data per language (measured from dictmaster.db)

```
Lang  Entries   Avg Def   Total Defs   Est. Entries_content   Notes
----  -------   -------   ----------   --------------------   -----
en    30,535     39 B       2.2 MB         5.6 MB             Largest (verbose English glosses)
de    30,514     35 B       1.5 MB         4.9 MB             German compounds
fr    30,499     28 B       1.1 MB         4.5 MB
id    30,515     30 B       1.3 MB         4.7 MB
es    30,483     27 B       0.8 MB         4.2 MB
tl    30,466     28 B       0.8 MB         4.2 MB
ru    30,491     27 B       0.8 MB         4.2 MB             Cyrillic
sv    30,489     23 B       0.7 MB         4.1 MB
fa    30,419     22 B       0.7 MB         4.1 MB             Persian/RTL
vi    30,202     22 B       0.7 MB         4.1 MB
ko    30,108     11 B       0.3 MB         3.7 MB             Hangul (compact)
ja    30,542      9 B       0.3 MB         3.7 MB             Kanji/kana (compact)
```

*Est. Entries_content = trad + simp + pinyin + searchix overhead (~113 B/row
from measured 21.1 MB / 115K rows) + definition text. Scaled to 30.5K rows.*

### Full Copyworks DB size per language

Using measured ratios from the reference DB:

```
Component                  Size         Notes
-------------------------  ----------   ------------------------------------
Entries_content (dict)     3.7-5.6 MB   Varies by language (see above)
FTS4 index (Entries)       4.4-6.7 MB   1.19x content (measured ratio)
Terms + TermEntries        4.3-6.5 MB   1.16x content (measured ratio)
chardata (fixed)          48.5 MB       characters + strokes + HSK + dict_single
DictFts5 (if included)     2.9 MB       FTS5 experimental (optional)
=====================================================================================

TOTAL PER COPYWORKS SKU          SIZE (uncompressed)    SIZE (compressed ~48%)
-----------------------          -------------------    ----------------------
Copyworks-English                62 MB                  ~30 MB
Copyworks-Deutsch                60 MB                  ~29 MB
Copyworks-Francais               59 MB                  ~28 MB
Copyworks-Bahasa                 59 MB                  ~28 MB
Copyworks-Espanol                58 MB                  ~28 MB
Copyworks-Tagalog                58 MB                  ~28 MB
Copyworks-Russkiy                58 MB                  ~28 MB
Copyworks-Svenska                57 MB                  ~27 MB
Copyworks-Farsi                  57 MB                  ~27 MB
Copyworks-Tieng Viet             57 MB                  ~27 MB
Copyworks-Hangugeo               56 MB                  ~27 MB
Copyworks-Nihongo                56 MB                  ~27 MB
-----------------------          -------------------    ----------------------
ALL 12 languages (bundled)       ~97 MB                 ~47 MB
```

*Bundled = shared chardata (48.5 MB) + 12 dict sets (~4 MB each). Not 12x.*

### Copyworks-Lite (no stroke SVGs)

Stripping stroke SVG paths saves **34.4 MB** (measured). Stroke order display
would be disabled, but all other features work.

```
Copyworks-Lite per language:    ~23 MB uncompressed    ~11 MB compressed
Copyworks-Lite all 12 langs:    ~62 MB uncompressed    ~30 MB compressed
```

---

## Intuition SKU -- Full Dictionary

Each Intuition edition ships **one target language** with all 428K headwords
plus chardata. Required for hover lookup, text segmentation, and annotation.

### Definition data per language (measured from dictmaster.db)

```
Lang  Defs       Avg Def   Total Defs   Est. Entries_content   Notes
----  --------   -------   ----------   --------------------   -----
en    691,502     33 B      21.7 MB        95 MB               Multi-source (cedict+wikt+minimax)
de    587,733     28 B      15.5 MB        75 MB
ja    559,493      9 B       4.8 MB        56 MB               Many entries, short defs
id    550,809     27 B      14.4 MB        73 MB
fr    484,141     25 B      11.6 MB        62 MB
es    432,268     24 B      10.1 MB        56 MB
tl    427,800     25 B      10.3 MB        56 MB
ru    427,953     24 B      10.1 MB        56 MB
sv    427,923     21 B       8.4 MB        53 MB
fa    427,609     18 B       7.3 MB        51 MB
vi    427,397     21 B       8.5 MB        53 MB
ko    423,840      9 B       3.6 MB        47 MB
```

*Est. Entries_content: entry count x measured per-row overhead (113 B) + definition text.
En/de/id/ja/fr have more entries because multiple dictionary sources contribute.*

### Full Intuition DB size per language

```
Component                  Size          Notes
-------------------------  -----------   ------------------------------------
Entries_content (dict)     47-95 MB      All headwords, varies by lang+sources
FTS4 index (Entries)       56-113 MB     1.19x content
Terms + TermEntries        55-110 MB     1.16x content
chardata (fixed)          48.5 MB        Same as Copyworks
DictFts5 (if included)    30-60 MB       FTS5 experimental (optional)
=====================================================================================

TOTAL PER INTUITION SKU (without DictFts5)

                                 SIZE (uncompressed)    SIZE (compressed ~48%)
------------------------         -------------------    ----------------------
Intuition-English                362 MB                 ~174 MB
Intuition-Deutsch                287 MB                 ~138 MB
Intuition-Nihongo                227 MB                 ~109 MB
Intuition-Bahasa                 281 MB                 ~135 MB
Intuition-Francais               246 MB                 ~118 MB
Intuition-Espanol                216 MB                 ~104 MB
Intuition-Tagalog                216 MB                 ~104 MB
Intuition-Russkiy                216 MB                 ~104 MB
Intuition-Svenska                210 MB                 ~101 MB
Intuition-Farsi                  206 MB                 ~99 MB
Intuition-Tieng Viet             210 MB                 ~101 MB
Intuition-Hangugeo               200 MB                 ~96 MB
------------------------         -------------------    ----------------------
ALL 12 languages (bundled)       ~700 MB                ~336 MB
```

*Bundled estimate assumes shared chardata + searchix, separate defs + FTS per lang.*

---

## Comparison Chart

```
                    Copyworks          Intuition          Copyworks-Lite
                    (single chars)     (full dict)        (no strokes)
                    ==============     ==============     ==============
Headwords           ~30.5K             428K-692K          ~30.5K
FTS index           Yes (small)        Yes (large)        Yes (small)
Chardata            Full (48.5 MB)     Full (48.5 MB)     No strokes (14 MB)
                    --------------     --------------     --------------
Per-lang (uncomp)   56-62 MB           200-362 MB         23 MB
Per-lang (compr.)   27-30 MB           96-174 MB          11 MB
All 12 (uncomp)     ~97 MB             ~700 MB            ~62 MB
All 12 (compr.)     ~47 MB             ~336 MB            ~30 MB
```

### Size by language (compressed, all SKUs)

```
Language        Copyworks   Intuition   Copyworks-Lite
----------      ---------   ---------   --------------
English            30 MB      174 MB        12 MB
Deutsch            29 MB      138 MB        11 MB
Francais           28 MB      118 MB        11 MB
Bahasa (id)        28 MB      135 MB        11 MB
Espanol            28 MB      104 MB        11 MB
Tagalog            28 MB      104 MB        11 MB
Russkiy            28 MB      104 MB        11 MB
Svenska            27 MB      101 MB        11 MB
Farsi              27 MB       99 MB        11 MB
Tieng Viet         27 MB      101 MB        11 MB
Hangugeo           27 MB       96 MB        10 MB
Nihongo            27 MB      109 MB        10 MB
```

---

## Key Observations

1. **Chardata dominates Copyworks size** -- the dict portion is only 12-19 MB
   per language, but strokes add 34 MB. All Copyworks editions land in a
   narrow 27-30 MB band (compressed).

2. **Intuition size varies dramatically by language** -- English at 174 MB
   (692K multi-source entries) vs Korean at 96 MB (424K entries, 9 B avg def).
   This is 1.8x difference, driven by entry count and definition verbosity.

3. **FTS + Terms doubles the dictionary cost** -- the FTS4 index (1.19x) and
   Terms tables (1.16x) together add 2.35x overhead on top of Entries_content.
   This is the main reason Intuition DBs are so much larger.

4. **Bundling all 12 languages is feasible for Copyworks** -- ~47 MB compressed
   for a polyglot edition (only ~17 MB more than single-language). The ~4 MB
   per-language dict cost is dwarfed by the shared 48.5 MB chardata.

5. **Copyworks-Lite is viable for web/WASM** -- at ~11 MB compressed per
   language, this fits comfortably in a web download. Loses stroke order
   visualization but keeps everything else.

6. **Intuition bundling is expensive** -- ~336 MB for all 12 languages.
   On-demand language download (choose your language, download ~100 MB)
   is probably the right UX.

7. **Current dictgen English is 136 MB with 115K entries**. Intuition-English
   at 362 MB with 692K entries is 2.7x larger -- reasonable given 6x more
   entries (sublinear because fixed chardata and per-row overhead).

---

## Assumptions and Methodology

- **Per-row overhead**: 113 bytes (measured: 21.1 MB content / 115K rows ≈ 192 B
  total per row, minus ~79 B avg definition = 113 B for trad+simp+pinyin+searchix)
- **FTS4 index ratio**: 1.19x content (measured: 25.0 MB / 21.1 MB)
- **Terms ratio**: 1.16x content (measured: 24.5 MB / 21.1 MB for terms+termEntries)
- **Chardata**: 48.5 MB fixed (measured: chars 9.8 + strokes 34.4 + hsk 2.5 + dsc 1.6 + lessons 0.2)
- **CEROD compression**: ~48% of uncompressed (conservative estimate for mixed
  text + binary SVG content)
- **Bundled sizes**: shared chardata counted once + per-language dict portions summed
- **Intuition entry counts**: use dictmaster def counts per lang (en has 692K because
  cedict + wiktextract + minimax all contribute; ru has 428K mostly minimax-only)

Source measurements:
- dictmaster.db: 752 MB (428K headwords, 5.1M definitions)
- core.sqlite: 135.7 MB (115K entries, English-only, measured via `dbstat`)
