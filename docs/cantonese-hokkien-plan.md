# Cantonese & Hokkien Dialect Expansion Plan

Future development plan: extend the multilingual dictmaster with Cantonese (粵語)
and Hokkien/Min Nan (閩南語/台語) — not just pronunciation mappings, but the
**lexical divergences** where different Chinese characters/words are used entirely.

## Historical Inspiration

The **Dictionario Hispanico Sinicum** (DHS), compiled 1626-1642 by Spanish Dominican
missionaries in Manila, is the world's oldest and largest Spanish-Chinese dictionary.
Found at UST (University of Santo Tomas) Archives cataloged as "Vocabulario
Espanol-Chino con caracteres chinos (Tomo 215)" — ironically labeled "vale muy
poco" (of little value).

- 1,103 pages, 27,000 vocabulary entries
- Each page: Spanish phonetics | Chinese characters | Zhangzhou Hokkien phonetics | Mandarin phonetics
- Predates the Kangxi Dictionary (1716) by ~70 years
- Linked to the Spanish occupation of Taiwan (1626-1642)
- Source: https://lifestyle.inquirer.net/378777/worlds-oldest-and-largest-spanish-chinese-dictionary-found-in-ust/

The **EMHo Project** (Early Manila Hokkien) at University of Graz is digitizing a
related manuscript, the "Bocabulario de lengua sangleya por las letraz de el A.B.C."
(c. 1617) — a Spanish-Hokkien dictionary with TEI-encoded linguistic annotations.
- https://gams.uni-graz.at/emho
- Academic paper: https://zenodo.org/records/16023787

Our goal: be the modern, computational equivalent — a universal multilingual Chinese
dictionary spanning Mandarin, Cantonese, Hokkien, and 11+ foreign languages.

## Linguistic Relatives of Hokkien

### The Min Family Tree

Hokkien (Southern Min / Min Nan) belongs to the Min branch of Sinitic:
```
Sinitic
└── Min
    ├── Southern Min (Min Nan / Hokkien)
    │   ├── Quanzhou, Zhangzhou, Xiamen/Amoy
    │   ├── Taiwanese Hokkien (Quanzhang fusion)
    │   ├── Teochew/Swatow (reduced mutual intelligibility with Amoy)
    │   └── Diaspora: Penang, Manila, Medan
    ├── Eastern Min (Fuzhou)
    ├── Northern Min
    ├── Pu-Xian Min (Putian)
    ├── Leizhou Min
    └── Hainanese (Qiongwen)
```

Min shows extreme internal diversity — neighboring counties can be mutually
unintelligible. Even Teochew (technically Southern Min) has difficult mutual
intelligibility with Amoy Hokkien.

### The Vietnamese Connection: Sino-Vietnamese Vocabulary

Vietnamese and Hokkien are **not genetically related**, but share massive
vocabulary through layers of Chinese contact:

**Layer 1: Old Sino-Vietnamese (~400 words, Han dynasty era)**
Early loans fully assimilated as "native" Vietnamese: búa (axe, from 斧)

**Layer 2: Sino-Vietnamese proper (~3,000 morphemes, Tang-Song era)**
Systematic readings modeled on Middle Chinese rhyme dictionaries, used for
formal/technical/literary vocabulary. This is the largest layer.

**Layer 3: Dialectal/maritime borrowings (1,000+ items)**
Colloquial loans from southern Chinese vernaculars (Hokkien, Cantonese, Hakka)
via trade and migration — items outside the standard Sino-Vietnamese system.

**Estimated Chinese contribution to Vietnamese**: 40-75% of the lexicon
depending on definition (core vocab ~40%, with technical/literary domains up to 72%).
The wide range reflects different counting methods — morphemes vs lemmas vs tokens.

**Why the readings are similar**: Both Hokkien literary readings and Sino-Vietnamese
readings independently adapted from Middle Chinese prestige norms. Hokkien has
a unique **dual reading system**:
- 白 (colloquial) readings: native Min phonology (older stratum)
- 文 (literary) readings: borrowed from Tang-era prestige pronunciation

Examples of Hokkien literary/colloquial splits:
- 白 "white": pe̍h (colloquial) vs pe̍k (literary)
- 書 "book": chu (colloquial) vs su (literary)
- 不 "not": m̄ (colloquial) vs put (literary)

The literary readings often match Sino-Vietnamese more closely because both
descend from the same Middle Chinese source — parallel evolution, not direct borrowing.

### Hokkien Loanwords Across Southeast Asia

Maritime Hokkien merchants from Zhangzhou and Quanzhou established communities
at every major Southeast Asian port. Their vocabulary followed:

**Tagalog/Philippines** — most Chinese loanwords in Tagalog come from Hokkien:
- ate < á-ché 阿姊 (older sister)
- bihon < bí-hún 米粉 (rice vermicelli)
- biko < bí-ko 米糕 (sweet rice cake)
- siopao < sio-pau 燒包 (steamed bun)
- taho < tāu-hū 豆腐 (tofu)
- Gloria Chan-Yap documented 163+ Hokkien-derived Tagalog terms

**Malay/Indonesian** — almost all Chinese loanwords from Hokkien or Hakka:
- mie < mī 麵 (noodles)
- lumpia < lūn-piáⁿ 潤餅 (spring roll)
- teko < teh-ko 茶壺 (teapot)
- tahu < tāu-hū 豆腐 (tofu)
- In Baba Malay (Peranakan), Hokkien loans = ~15.6% of the glossary

**Thai** — 315+ documented Swatow/Hokkien loanwords:
- หมี่ (mī) < 麵 (noodles)
- เต้าหู้ (tofu) < 豆腐

**Semantic fields**: food, trade, kinship terms, household items — exactly the
vocabulary of daily commerce and family life.

### Why This Matters for Our Dictionary

The Hokkien diaspora created a **living bridge** between Chinese and Southeast
Asian languages. Our 11 target languages include Indonesian, Vietnamese, and
Tagalog — three languages heavily influenced by Hokkien. When we add Hokkien
forms to our dictionary, we're not just adding a Chinese dialect — we're
revealing the etymological backbone of thousands of words in languages we
already translate to. A user looking up 豆腐 should see:

```
豆腐 dòufu — Hokkien: tāu-hū [tāu-hū]
  → Vietnamese: đậu phụ (Sino-Vietnamese)
  → Indonesian: tahu (from Hokkien tāu-hū)
  → Tagalog: taho (from Hokkien tāu-hū)
  → Thai: เต้าหู้ (from Hokkien tāu-hū)
```

This is the modern DHS — not just Chinese↔foreign, but showing the **flow**
of vocabulary from Chinese through Hokkien into the languages of Southeast Asia.

## Scale of Lexical Divergence

Not just pronunciation differences — genuinely different words/characters:

| Concept | Mandarin | Cantonese | Hokkien |
|---------|----------|-----------|---------|
| thank you | 謝謝 xièxie | 多謝 do1ze6 / 唔該 m4goi1 | 多謝 to-siā / 感謝 kám-siā |
| thing | 東西 dōngxi | 嘢 je5 | 物件 mi̍h-kiānn |
| what | 什麼 shénme | 乜嘢 mat1je5 | 啥物 siánn-mih |
| he/she | 他/她 tā | 佢 keoi5 | 伊 i |
| eat | 吃 chī | 食 sik6 | 食 tsia̍h |
| house | 房子 fángzi | 屋企 uk1kei2 | 厝 tshù |
| not | 不 bù | 唔 m4 | 毋 m̄ |
| look | 看 kàn | 睇 tai2 | 看 khuànn |
| run | 跑 pǎo | 走 zau2 | 走 tsáu |
| beautiful | 漂亮 piàoliang | 靚 leng3 | 媠 suí |

**Estimated divergence rates from Mandarin:**
- **Cantonese**: ~15-25% of daily vocabulary uses different characters (up to 50% in colloquial register)
- **Hokkien**: ~30-40% of basic vocabulary (up to 80-90% for function words — pronouns, particles, negation)

From 410K headwords, expect:
- Cantonese: ~5,000-10,000 lexical divergences
- Hokkien: ~10,000-20,000 lexical divergences

## Data Sources: Cantonese (粵語)

### Tier 1: Direct Import (CEDICT-compatible)

**CC-Canto** — Cantonese dictionary in CEDICT format
- URL: https://cantonese.org/download.html
- License: CC BY-SA 3.0 (Pleco Software)
- Size: ~34,335 entries
- Format: CEDICT format with Jyutping in `{}` braces after Pinyin
- Three files: CC-Canto itself, CC-CEDICT, Cantonese readings for CC-CEDICT entries
- Import: trivial — use existing CEDICT parser with Jyutping extension

### Tier 2: Pronunciation Databases

**rime-cantonese** — largest Jyutping lexicon
- GitHub: https://github.com/rime/rime-cantonese
- License: CC BY 4.0
- Size: 185,809 items (characters + multi-character words)
- Used by PyCantonese for word segmentation

**LSHK Jyutping Table** — authoritative character→Jyutping
- GitHub: https://github.com/lshk-org/jyutping-table
- License: CC BY 4.0
- Format: TSV (list.tsv) + JSON

**Unicode Unihan kCantonese** — per-character Jyutping
- Part of Unihan.zip from unicode.org
- License: Unicode Terms of Use (permissive)

### Tier 3: Lexical Divergence Data

**Cross-Strait Life Difference Word Compilation** (兩岸三地生活差異詞語彙編)
- GitHub: https://github.com/g0v/moedict-data-csld
- License: CC BY-NC-ND 4.0 (original data), CC0 (CSV formatting by Audrey Tang)
- Two key files:
  - `同名異實.csv` — same word, different meaning across Taiwan/Mainland/HK
  - `同實異名.csv` — same concept, different words across Taiwan/Mainland/HK
- Directly answers "what's the Cantonese word for X?"

**CyberCan** — modern colloquial Cantonese from internet forums
- GitHub: https://github.com/shenfei1010/CyberCan
- License: CC BY 4.0
- Size: 133,212 words from LIHKG/HKGolden posts

**Cantonese WordNet** — concept-aligned with Mandarin via synsets
- GitHub: https://github.com/lmorgadodacosta/CantoneseWN
- License: CC BY 4.0
- Size: 3,500 concepts, 12,000 senses

**Cifu** — frequency-ranked Cantonese lexicon
- GitHub: https://github.com/gwinterstein/Cifu
- License: GPL-3.0
- Size: 51,798 words with spoken/written frequency data

### Tier 4: Corpora & Reference

**words.hk** — most comprehensive Cantonese dictionary (53K+ entries)
- URL: https://words.hk
- Tools: https://github.com/AlienKevin/wordshk-tools
- License: complex — check terms for commercial/derivative use

**Jyut Dictionary** — aggregator of 8 sources, 700K+ definitions
- GitHub: https://github.com/aaronhktan/jyut-dict
- Good reference for how to parse and combine sources

**HKCanCor** — 230K-word annotated spoken Cantonese corpus
- GitHub: https://github.com/fcbond/hkcancor
- License: CC BY 4.0

**Master resource list**: https://github.com/CanCLID/awesome-cantonese-nlp

## Data Sources: Hokkien (閩南語/台語)

### Tier 1: Direct Import

**ChhoeTaigi Database** (找台語) — THE motherlode
- GitHub: https://github.com/ChhoeTaigi/ChhoeTaigiDatabase
- Total: 353,511 entries across 9 CSV dictionaries
- All files include POJ and Tai-lo romanization in Unicode

| # | Dictionary | Entries | License |
|---|-----------|---------|---------|
| 1 | 台華線頂對照典 (Mandarin-Hokkien pairs) | 91,339 | CC BY-SA 4.0 |
| 2 | 台日大辭典 (1932 Taiwan-Japanese) | 69,513 | CC BY-NC-SA 3.0 TW |
| 3 | Maryknoll台英辭典 (1976 Taiwanese-English) | 55,903 | CC BY-NC-SA 3.0 TW |
| 4 | Embree台英辭典 (1973, based on Douglas/Barclay) | 36,800 | CC BY-NC-SA 3.0 TW |
| 5 | 教育部台語辭典 (MoE official, 2011+) | 24,608 | CC BY-ND 3.0 TW |
| 6 | 甘字典 (Campbell 1913) | 24,367 | CC BY-NC-SA 3.0 TW |
| 7 | **iTaigi華台對照典** (crowdsourced) | 19,046 | **CC0** (public domain) |
| 8 | 台灣白話基礎語句 (1956) | 5,429 | CC BY-SA 4.0 |
| 9 | 台灣植物名彙 (1928 botanical) | 1,722 | CC BY-SA 4.0 |

**Best for our use case:**
- #7 iTaigi (CC0, 19K) — zero licensing friction, explicit Mandarin↔Hokkien pairs
- #1 台華線頂對照典 (CC BY-SA 4.0, 91K) — largest Mandarin-Hokkien parallel dataset
  - Has `HoaBun` (對應華文 = corresponding Mandarin) column alongside Hokkien forms

### Tier 2: Government & Official

**Taiwan MoE Taiwanese Dictionary** (教育部臺灣閩南語常用詞辭典)
- URL: https://sutian.moe.edu.tw/
- Direct download: https://sutian.moe.edu.tw/zh-hant/siongkuantsuguan/
  - `kautian.ods` (8.14 MB) — full dictionary data
  - Audio files (wav/mp3) for words and example sentences
- License: CC BY-ND 3.0 TW (No Derivatives — can use for reference but not remix)
- Machine-readable: https://github.com/g0v/moedict-data-twblg (Audrey Tang's JSON/CSV)

### Tier 3: Historical Dictionaries (Digitized)

**Campbell/Kam Dictionary (甘字典, 1913)** — corrected CSV
- GitHub: https://github.com/TongUanLab/CampbellAmoyDict
- License: CC BY-NC-SA 4.0 (data), MIT (code)
- 24K entries, normalized with Tai-lo

**Douglas's Chinese-English Dict of Amoy (1873)**
- Internet Archive: https://archive.org/details/chineseenglish00doug
- Public domain (1873)
- The Embree dictionary (#4 above) effectively subsumes Douglas/Barclay content

**Medhurst's Dictionary of Hok-keen (1832)**
- Internet Archive: https://archive.org/details/dictionaryofhokk00medhrich
- Public domain (1832), earliest substantial Hokkien dictionary (~12K characters)

### Tier 4: Wiktionary & Other

**Kaikki.org Wiktextract** — Hokkien entries from English Wiktionary
- URL: https://kaikki.org/dictionary/rawdata.html
- Filter for `lang_code = "nan"` or Hokkien categories
- License: CC BY-SA 4.0
- Multi-dialect pronunciation data (Xiamen, Zhangzhou, Quanzhou, Taiwan, Philippines)

**Taibun** — Python transliteration library (7 romanization systems)
- GitHub: https://github.com/andreihar/taibun
- License: MIT (code), CC BY-SA 4.0 (data)
- Handles tone sandhi, dialect variants

**Hokkien Wikipedia**: https://zh-min-nan.wikipedia.org (CC BY-SA)

## Data Analysis: What We Downloaded

All source data is in `data/raw/dictmaster/cantonese/` and `data/raw/dictmaster/hokkien/`.

### CC-Canto (downloaded)

```
data/raw/dictmaster/cantonese/cccanto-webdist.txt     — 34,335 entries
data/raw/dictmaster/cantonese/cccedict-canto-readings-150923.txt — 105,862 entries
```

**CC-Canto format** (CEDICT + Jyutping in `{}` braces):
```
一唔係 一唔系 [yi1 n2 xi4] {jat1 m4 hai6} /else/
一嘢 一嘢 [yi1 ye3] {jat1 je5} /one hit or strike/
上嚟 上嚟 [shang4 li2] {soeng5 lai2} /to come over, to come up/
```

**CC-CEDICT Cantonese Readings** (pronunciation overlay only — no definitions):
```
伊莉莎白 伊莉莎白 [Yi1 li4 sha1 bai2] {ji1 lei6 saa1 baak6}
發佈 发布 [fa1 bu4] {faat3 bou3}
```

**Overlap with dictmaster (410K headwords):**
- CC-Canto: 14,764 overlap (49.7%), 14,934 new entries (50.3%)
- CC-CEDICT readings: 102,155 overlap (97.9%) — excellent pronunciation coverage
- 1,103 entries contain Cantonese-specific characters (嘢唔佢睇靚咗嚟哋俾攞)

### ChhoeTaigi (downloaded)

```
data/raw/dictmaster/hokkien/ChhoeTaigiDatabase/ChhoeTaigiDatabase/
  ChhoeTaigi_iTaigiHoataiTuichiautian.csv         — 19,775 entries (CC0)
  ChhoeTaigi_TaihoaSoanntengTuichiautian.csv       — 91,339 entries (CC BY-SA 4.0)
  ChhoeTaigi_TaijitToaSutian.csv                   — 69,513 entries (CC BY-NC-SA)
  ChhoeTaigi_MaryknollTaiengSutian.csv             — 55,903 entries (CC BY-NC-SA)
  ChhoeTaigi_EmbreeTaiengSutian.csv                — 36,800 entries (CC BY-NC-SA)
  ChhoeTaigi_KauiokpooTaigiSutian.csv              — 24,608 entries (CC BY-ND)
  ChhoeTaigi_KamJitian.csv                         — 24,367 entries (CC BY-NC-SA)
  ChhoeTaigi_TaioanPehoeKichhooGiku.csv            — 5,429 entries (CC BY-SA 4.0)
  ChhoeTaigi_TaioanSitbutMialui.csv                — 1,722 entries (CC BY-SA 4.0)
```

**iTaigi CSV format** (CC0, crowdsourced):
```
DictWordID,PojUnicode,PojInput,KipUnicode,KipInput,HanLoTaibunPoj,HanLoTaibunKip,HoaBun,DataProvidedBy
"1","siān-neh","sian7-neh","siān-neh","sian7-neh","𤺪呢","𤺪呢","討厭","Liz Lin"
```
Key columns: `HoaBun` (Mandarin), `HanLoTaibunPoj` (Hokkien characters), `PojUnicode` (romanization)

**台華對照典 CSV format** (CC BY-SA 4.0):
```
DictWordID,PojUnicode,PojUnicodeOthers,...,HanLoTaibunPoj,...,HanLoTaibunKip,HoaBun
"1","á-bô","","a2-bo5","","á無",...,"á無","不然"
```
Key columns: same structure, `HoaBun` → `HanLoTaibunPoj` mapping

**Measured divergence rates:**
- iTaigi: 15,450 / 19,775 = **78.1% different characters** from Mandarin
- 台華對照典: 62,589 / 91,331 = **68.5% different characters** from Mandarin

**Overlap with dictmaster:**
- iTaigi: 8,572 Mandarin terms match dictmaster (65.7%)
- 台華對照典: 38,813 Mandarin terms match dictmaster (77.7%)
- Combined: 43,267 unique Mandarin terms match dictmaster (74.1%)
- 15,148 new Mandarin terms not in dictmaster

**Vivid divergence examples from the actual data:**
```
討厭 → 𤺪呢 [siān-neh]     (annoying)
口   → 喙 [chhùi]          (mouth)
巨蛋 → 大粒卵 [tōa-lia̍p-nn̄g] (stadium/giant egg)
水逆 → 水星倒頭行           (Mercury retrograde)
媽媽 → 阿母 [a-bó]         (mother)
不然 → á無 [á-bô]          (otherwise)
何必 → ā使 [ā-sái]         (why bother)
蟬   → á蛦 [á-î]           (cicada)
```

## Two Types of Dialect Data

Dialect data is fundamentally **two different things**:

### TYPE 1: Pronunciation Overlay (same characters, different reading)
The Mandarin headword is spelled the same in all dialects, just pronounced differently.
- 銀行: Mandarin yín háng → Cantonese ngan4 hong4 → Hokkien gîn-hâng
- 中國: Mandarin zhōngguó → Cantonese zung1 gwok3 → Hokkien Tiong-kok
- Sources: CC-CEDICT Cantonese Readings (102K), rime-cantonese (185K)
- **Import model**: attach pronunciation to existing headwords

### TYPE 2: Lexical Equivalent (different characters/words entirely)
A different word is used in daily speech — the Mandarin form exists but isn't natural.
- 東西 (thing) → Cantonese 嘢 → Hokkien 物件
- 漂亮 (beautiful) → Cantonese 靚 → Hokkien 媠
- 什麼 (what) → Cantonese 乜嘢 → Hokkien 啥物
- Sources: CC-Canto (34K), iTaigi (19K), 台華對照典 (91K)
- **Import model**: create NEW headwords or cross-reference entries

## Data Model Options

### Current schema
```sql
headwords (id, traditional, simplified, pinyin, pos)
definitions (id, headword_id, lang, definition, source, confidence, verified)
```

### Option A: Overload the definitions table
Use `lang="yue"` / `lang="nan"` in the existing definitions table:
- Definition text = "Cantonese form + pronunciation + English gloss"
- e.g. `lang="yue", definition="靚 leng3 — pretty/beautiful"`
- Pro: zero schema change, works with existing export
- Con: mixes two fundamentally different data types (foreign-language translation vs same-language dialect form); parsing the compound string is fragile

### Option B: New `dialect_forms` table (RECOMMENDED)
```sql
CREATE TABLE dialect_forms (
    id INTEGER PRIMARY KEY,
    headword_id INTEGER REFERENCES headwords(id),
    dialect TEXT NOT NULL,           -- 'yue' or 'nan'
    native_chars TEXT,               -- 靚, 嘢, 媠, 厝 (NULL if same as Mandarin)
    pronunciation TEXT NOT NULL,     -- Jyutping or POJ/Tai-lo
    gloss TEXT,                      -- English gloss for the dialect form
    source TEXT NOT NULL,            -- 'cccanto', 'cccedict-readings', 'itaigi', etc.
    UNIQUE(headword_id, dialect, source)
);
```
- TYPE 1 (pronunciation): `native_chars=NULL`, `pronunciation="ngan4 hong4"`
- TYPE 2 (lexical): `native_chars="嘢"`, `pronunciation="je5"`, `gloss="thing"`
- Pro: clean separation, proper columns for each field, queryable
- Con: new table, new export logic

### Option C: Hybrid — new table for dialect + definitions for glosses
Same as B, but ALSO add `lang="yue"`/`lang="nan"` entries in definitions
for the English glosses of Cantonese/Hokkien-specific words (e.g. 嘢 → "thing/stuff").
This way the existing 11-language translation pipeline can eventually cover
dialect-specific headwords too.

**Recommendation: Option B** — dialect forms are linguistically distinct from
foreign-language translations. A dedicated table keeps the data model clean and
allows proper queries like "what's the Cantonese pronunciation of X?" or "which
headwords have different Hokkien forms?"

## Target Audience

### Primary: Heritage speakers and language learners
- "If you go to the Philippines and don't learn Hokkien, you can forget about
  doing business. Same as going to Malaysia and not knowing Cantonese."
- Business travelers, diaspora reconnecting with roots, students
- Need: Mandarin↔dialect lookup in both directions

### Secondary: Linguists and NLP researchers
- Cross-dialect comparison data at scale
- Lexical divergence quantification
- Historical dictionary digitization (connecting to 400-year-old DHS tradition)

### Tertiary: AI/LLM training data
- Parallel Mandarin-Cantonese-Hokkien aligned at word level
- Rare: most Chinese NLP data is Mandarin-only

## Implementation Strategy

### Phase 1: Schema extension + basic import

1. Add `dialect_forms` table to dictmaster schema
2. **CC-CEDICT Cantonese Readings** → 102K pronunciation overlays (TYPE 1)
   - Parse CEDICT format, extract `{jyutping}`, match to existing headwords
   - Expected: ~102K entries, all pronunciation-only
3. **CC-Canto** → 34K entries with definitions (mix of TYPE 1 and TYPE 2)
   - Parse CEDICT format with `{jyutping}` extension
   - For entries matching existing headwords: add as dialect form
   - For new Cantonese-specific entries (嘢, 唔, 佢, etc.): create new headwords
4. **iTaigi** (CC0, 19K) → Mandarin↔Hokkien pairs (TYPE 2)
   - Parse CSV, match `HoaBun` to existing headwords
   - Store `HanLoTaibunPoj` as `native_chars`, `PojUnicode` as `pronunciation`

### Phase 2: Larger Hokkien import

5. **台華線頂對照典** (CC BY-SA 4.0, 91K) → largest parallel dataset
   - Same approach as iTaigi, much larger coverage
   - De-duplicate against iTaigi entries

### Phase 3: AI gap-fill for divergences

For headwords not covered by dictionary imports, use MiniMax to generate:
- Cantonese character form + Jyutping (if different from Mandarin)
- Hokkien character form + POJ/Tai-lo (if different from Mandarin)

The model prompt would include existing definitions as context plus a few
canonical examples of known divergences to calibrate the output.

Estimated exceptions to generate:
- Cantonese: ~3,000-5,000 (after CC-Canto + readings cover most)
- Hokkien: ~5,000-10,000 (after ChhoeTaigi import covers most)

### Phase 4: Corpus validation

Use the 113M-chunk zhcorpus to verify generated Cantonese/Hokkien forms
appear in real Chinese text. The Cantonese Wikipedia dump and Hokkien
Wikipedia could also be added as corpus sources.

### Phase 5: Export integration

Add Cantonese/Hokkien to the CEDICT export format:
```
靚 靓 [liang4] {leng3} /pretty/beautiful/handsome/
```
Or a separate dialect CEDICT file per language.

## Licensing Summary

| Source | License | Safe to use? |
|--------|---------|-------------|
| CC-Canto | CC BY-SA 3.0 | YES |
| rime-cantonese | CC BY 4.0 | YES |
| LSHK Jyutping | CC BY 4.0 | YES |
| CyberCan | CC BY 4.0 | YES |
| Cantonese WordNet | CC BY 4.0 | YES |
| ChhoeTaigi #7 iTaigi | CC0 | YES (public domain) |
| ChhoeTaigi #1 台華對照 | CC BY-SA 4.0 | YES |
| ChhoeTaigi #8 基礎語句 | CC BY-SA 4.0 | YES |
| ChhoeTaigi #9 植物名彙 | CC BY-SA 4.0 | YES |
| Campbell Dict (TongUanLab) | CC BY-NC-SA 4.0 | YES (non-commercial) |
| Wiktextract Hokkien | CC BY-SA 4.0 | YES |
| Cross-Strait comparison | CC BY-NC-ND 4.0 | REFERENCE ONLY (ND) |
| MoE Taiwanese Dict | CC BY-ND 3.0 TW | REFERENCE ONLY (ND) |
| ChhoeTaigi #2-4, #6 | CC BY-NC-SA 3.0 TW | NON-COMMERCIAL only |
| Cifu | GPL-3.0 | CHECK (copyleft) |
| words.hk | Complex | CHECK terms |
