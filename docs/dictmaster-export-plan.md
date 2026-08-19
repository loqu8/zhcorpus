# Dictmaster Export Plan

How to ship dictmaster's multilingual dictionary into downstream products
(Copyworks, Intuition) — replacing the CC-CEDICT-only dictgen pipeline.

## Status Quo

### What dictmaster has

- **428,073 headwords** (traditional, simplified, pinyin, pos)
- **5.1M definitions** across **12 languages**: en, de, fr, es, sv, ja, ko, ru, id, vi, tl, fa
- **30,546 single-char headwords** (19,471 distinct chars, 7,838 multi-reading)
- **184K dialect forms** (Cantonese Jyutping + Hokkien POJ)
- Source priority: cedict > cfdict/handedict/cidict > jmdict > wiktextract > minimax
- DB path: `data/artifacts/dictmaster.db` (752 MB)
- Existing export: CEDICT-format text files per language (`tools/dictmaster/export.py`)

### The full pipeline today (4 repos)

```
zhcorpus/dictmaster.db          nomad-builder/dictgen              loqu8-dart              copyworks
━━━━━━━━━━━━━━━━━━━━━          ━━━━━━━━━━━━━━━━━━━━━━             ━━━━━━━━━━              ━━━━━━━━━
428K headwords x 12 lang        build_dict_db.py                   DataService             NomadService
                                  |                                  |                       |
(not connected today)           CC-CEDICT (en only)                resolves path           DictEngine (FFI)
                                  + chardata sources               core.xdb or             ChardataDb (FFI)
                                  + HSK + Rated + lessons          core.sqlite               |
                                  |                                  |                     annotateJson()
                                  v                                  v                       |
                                core.sqlite (136 MB)  --CEROD-->  core.xdb (~65 MB)         v
                                  |                               uploaded to GH        CharacterData
                                release-copyworks-data.sh         releases as             (definition field
                                  encrypts + uploads              nomad_core-data           = English only)
                                                                  .tar.gz
```

### Key touchpoints per repo

| Repo | File | Role |
|------|------|------|
| **zhcorpus** | `tools/dictmaster/export.py` | CEDICT-format export per language |
| **zhcorpus** | `tools/dictmaster/schema.py` | dictmaster DB schema (headwords, definitions) |
| **nomad-builder** | `tools/dictgen/build_dict_db.py` | Builds core.sqlite from CC-CEDICT + chardata |
| **nomad-builder** | `tools/release-copyworks-data.sh` | Orchestrates: dictgen → CEROD encrypt → GH upload |
| **nomad-builder** | `bindings/flutter/packages/nomad_core/` | Flutter FFI bindings (DictEngine, ChardataDb) |
| **loqu8-dart** | `lib/src/data_service.dart` | Resolves `core.xdb` path (env, shared dir, bundled, dev fallback) |
| **loqu8-dart** | `lib/src/app_config.dart` | App identity (appId, appName, etc.) |
| **copyworks** | `lib/services/nomad_service.dart` | Wraps DictEngine + ChardataDb, calls `annotateJson()` |
| **copyworks** | `lib/models/character_data.dart` | `CharacterData.definition` — currently always English |

---

## Architecture Decision: One App + Language Packs

**Decision**: Ship one Copyworks binary that downloads language packs on demand.

**Rationale**: A Spanish-speaking Chinese learner should open "Copyworks" and
see everything in Spanish. They should never have to think about English. But
we don't want to maintain 12 separate app store listings, 12 CI pipelines, or
ship a 47 MB polyglot bundle to everyone.

### How it works

```
User installs Copyworks (one binary, ~15 MB app, no dict data)
  |
  v
First launch: "Choose your language"
  [English] [Espanol] [Deutsch] [Francais] [Russkiy] ...
  |
  v
Downloads language pack: core-es.xdb (~28 MB)
  --> stored in DataService shared dir (~/.loqu8/data/ or platform equivalent)
  |
  v
App loads core-es.xdb, all definitions in Spanish
  打 → "golpear/pegar/jugar"  (not "to hit/to strike/to play")
  |
  v
User can switch language later (Settings → Dictionary Language)
  --> downloads core-ru.xdb, swaps active DB
```

### Why language packs beat separate SKUs

| | Separate SKUs | Language packs |
|---|---------------|----------------|
| App store listings | 12 (or more) | 1 |
| CI/CD pipelines | 12 builds | 1 build + data gen |
| User discovery | Fragmented | One app, clear upgrade path |
| App binary size | Same everywhere | Same (~15 MB) |
| Data download | Bundled (~28 MB) | On-demand (~28 MB per lang) |
| Language switching | Reinstall different app | Settings toggle |
| Upsell path | None | "Unlock more languages" |

### Marketing implications

- **App store listing**: "Copyworks - Chinese Character Practice"
  - Screenshots in English by default
  - Feature callout: "Available in 12 languages"
  - Localized store descriptions per market (Spanish App Store → Spanish screenshots)
- **Spanish learner experience**: Everything in Spanish from first launch
  - No English UI anywhere (already handled by Flutter l10n)
  - No English definitions (handled by language pack)
  - Lesson titles and descriptions still need translation (future work)
- **Free tier**: English definitions included, other languages as in-app purchase
  or free download (TBD based on monetization strategy)

---

## Implementation Plan

### Phase 1: Direct DB Assembly (zhcorpus — no text export needed)

**Key insight**: Both dictmaster.db and core.sqlite are SQLite databases.
Instead of exporting to CEDICT text and re-parsing, we ATTACH dictmaster.db
and swap definitions directly via SQL queries. No serialization round-trip.

**Why this works**:
- `searchix` is language-independent (generated from trad + simp + pinyin)
- Chardata tables are language-independent (strokes, HSK, radicals, etymology)
- sfreq/tfreq are language-independent (corpus frequency)
- Lessons are language-independent (character lists)
- **Only `Entries_content.definition` and `Terms/TermEntries` change per language**

**New script: `tools/dictmaster/build_langpack.py`** (~150 lines):

```python
"""Build a per-language core.sqlite by swapping definitions in an existing DB.

Usage:
    python tools/dictmaster/build_langpack.py \
        --template core.sqlite \      # existing English core.sqlite (has all chardata)
        --dictmaster dictmaster.db \  # dictmaster DB (428K headwords x 12 langs)
        --lang es \                   # target language
        --output core-es.sqlite       # output DB
        --chars-only                  # optional: single chars only (Copyworks)
"""
import shutil, sqlite3

def build_langpack(template, dictmaster, lang, output, chars_only=False):
    # 1. Copy template (keeps chardata, HSK, strokes, lessons, pops intact)
    shutil.copy2(template, output)
    conn = sqlite3.connect(output)

    # 2. ATTACH dictmaster
    conn.execute("ATTACH DATABASE ? AS dm", (str(dictmaster),))

    # 3. Clear language-dependent tables
    conn.execute("DELETE FROM Entries_content")
    conn.execute("DELETE FROM Terms_content")
    conn.execute("DELETE FROM TermEntries")

    # 4. Insert definitions from dictmaster (best source wins)
    char_filter = "AND length(h.simplified) = 1" if chars_only else ""
    conn.execute(f"""
        INSERT INTO Entries_content
            (traditional, simplified, definition, pinyin, searchix, entryorder)
        SELECT h.traditional, h.simplified, d.definition, h.pinyin,
               '',  -- searchix filled below
               ROW_NUMBER() OVER (ORDER BY h.pinyin, h.simplified)
        FROM dm.headwords h
        JOIN dm.definitions d ON d.headword_id = h.id
        WHERE d.lang = ?
          AND length(h.simplified) <= 100
          {char_filter}
        GROUP BY h.traditional, h.simplified, h.pinyin  -- best def per headword
    """, (lang,))

    # 5. Generate searchix (language-independent, pure Python UDF)
    conn.create_function('build_searchix', 3, build_searchix)
    conn.execute("""
        UPDATE Entries_content
        SET searchix = build_searchix(traditional, simplified, pinyin)
    """)

    # 6. Rebuild Terms + TermEntries (trad/simp as terms + def fragments)
    rebuild_terms(conn)  # reuse extract_def_terms logic from dictgen

    # 7. Rebuild FTS4 indexes
    conn.execute("INSERT INTO Entries(Entries) VALUES ('rebuild')")
    conn.execute("INSERT INTO Terms(Terms) VALUES ('rebuild')")

    # 8. Backfill sfreq/tfreq (already in template, but re-match on new entries)
    # ... UPDATE Entries_content SET sfreq = ... from pops if available

    conn.execute("DETACH DATABASE dm")
    conn.execute("VACUUM")
    conn.commit()
    conn.close()
```

**What we copy from dictgen** (embed or import, ~80 lines):
- `build_searchix()` — 30 lines of pure string manipulation
- `extract_def_terms()` — 40 lines of definition fragment splitting
- `rebuild_terms()` — ~10 lines of INSERT loops + FTS rebuild

**What we DON'T need**: CEDICT parser, Unihan parser, makemeahanzi parser,
HSK parser, stroke SVG importer, lessons importer — all of that is already
in the template DB.

**xsqlite3 requirement**: The template core.sqlite has FTS4 tables with
`tokenize=snowball`. Rebuilding the FTS4 index requires xsqlite3 (nomad's
custom SQLite with snowball tokenizer). Two options:
1. Run the script from nomad-builder where xsqlite3 is available
2. Pre-build xsqlite3 bindings for zhcorpus (one-time setup)
3. Or: just copy the xsqlite3 build script from nomad-builder

### Phase 2: Build matrix (nomad-builder — minimal changes)

Update `release-copyworks-data.sh` to call `build_langpack.py` instead of
dictgen for non-English languages.

```bash
# Build all 12 language packs from a single English template
TEMPLATE="ext/data/out/CE/core.sqlite"  # existing English build
DICTMASTER="../zhcorpus/data/artifacts/dictmaster.db"

for lang in en de fr es sv ja ko ru id vi tl fa; do
  python3 ../zhcorpus/tools/dictmaster/build_langpack.py \
    --template "$TEMPLATE" \
    --dictmaster "$DICTMASTER" \
    --lang "$lang" \
    --output "ext/data/out/${lang^^}/core.sqlite" \
    --chars-only  # for Copyworks; omit for Intuition
done
```

Produces 12 `core-{lang}.sqlite` files in ~30 seconds total (mostly VACUUM).
CEROD encrypt + upload as before.

### Phase 3: Language Pack Download (loqu8-dart + copyworks)

**loqu8-dart `DataService` changes**:

```dart
class DataService {
  // Current: resolves single core.xdb
  // New: resolves core-{lang}.xdb based on active language

  static const _defaultLang = 'en';

  /// Active dictionary language code.
  String _dictLang = _defaultLang;

  /// Available language packs (downloaded to shared dir).
  List<String> get availableLanguages => ...;

  /// Download a language pack from the release URL.
  Future<void> downloadLanguagePack(String lang) async {
    // Download nomad_core-data-{lang}.tar.gz from GH releases
    // Extract core-{lang}.xdb to shared dir
    // Verify integrity (checksum)
  }

  /// Switch active dictionary language.
  /// Returns true if the language pack is available.
  bool setLanguage(String lang) {
    final path = '$_sharedDir/core-$lang.xdb';
    if (!File(path).existsSync()) return false;
    _dictLang = lang;
    _dbPath = path;
    return true;
  }
}
```

**copyworks changes**:

1. **Settings screen**: Add "Dictionary Language" picker
2. **First-run flow**: Language selection before anything else
3. **NomadService**: Re-initialize when language changes (`dispose()` + `initConsolidated()`)
4. **Download UI**: Progress indicator for language pack download

### Phase 4: Full Localization

- Translate etymology hints (currently English: "picture of a person")
- Translate lesson titles and descriptions
- Localized App Store descriptions and screenshots per market

---

## Data Flow (Target State)

```
BUILD TIME (one-shot per release)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                     ┌─────────────────┐
                     │ core.sqlite     │  (existing English build from dictgen)
                     │ 136 MB          │  chardata + HSK + strokes + lessons + pops
                     │ TEMPLATE        │  = the language-independent foundation
                     └────────┬────────┘
                              │ shutil.copy()
                              │
zhcorpus                      │                        GitHub Releases
━━━━━━━━                      ▼                        ━━━━━━━━━━━━━━━
dictmaster.db ──ATTACH──> build_langpack.py             nomad_core-data-en.tar.gz
  428K × 12 lang            |                           nomad_core-data-es.tar.gz
                            ├── DELETE Entries_content   nomad_core-data-ru.tar.gz
                            ├── INSERT FROM dm.headwords/definitions WHERE lang='es'
                            ├── rebuild searchix (Python UDF, lang-independent)
                            ├── rebuild Terms/TermEntries (def fragment split)
                            ├── rebuild FTS4 indexes
                            ├── VACUUM
                            |
                            core-es.sqlite ──CEROD──> core-es.xdb ──upload──>


RUNTIME (user device)
━━━━━━━━━━━━━━━━━━━━━

copyworks                       loqu8-dart
━━━━━━━━━                       ━━━━━━━━━━
Settings → "Espanol"            DataService.downloadLanguagePack('es')
  |                               |
  v                             downloads nomad_core-data-es.tar.gz
NomadService.initConsolidated     extracts core-es.xdb to ~/.loqu8/data/
  (core-es.xdb)                   |
  |                             DataService.setLanguage('es')
  v                               returns path to core-es.xdb
CharacterData.definition
  = "golpear/pegar/jugar"
```

---

## Agent-Friendly Execution Order

Each step is independently testable. An agent can execute them sequentially
across repos without needing to hold context from earlier phases.

### Step 1: zhcorpus — build_langpack.py (self-contained)

```bash
cd ~/repos/loqu8/zhcorpus
# Create tools/dictmaster/build_langpack.py
# Copy build_searchix() + extract_def_terms() from nomad-builder/tools/dictgen/build_dict_db.py
# (just those two functions, ~80 lines — or import them)
#
# Inputs:
#   --template  ~/repos/loqu8/nomad-builder/ext/data/out/CE/core.sqlite  (136 MB)
#   --dictmaster data/artifacts/dictmaster.db  (752 MB)
#   --lang es
#   --output data/artifacts/langpacks/core-es.sqlite
#   --chars-only  (for Copyworks)
#
# Test:
.venv/bin/python tools/dictmaster/build_langpack.py \
  --template ~/repos/loqu8/nomad-builder/ext/data/out/CE/core.sqlite \
  --dictmaster data/artifacts/dictmaster.db \
  --lang es --chars-only \
  --output /tmp/core-es.sqlite

# Verify:
sqlite3 /tmp/core-es.sqlite "SELECT traditional, simplified, definition FROM Entries_content LIMIT 10"
# Should show Spanish definitions
```

**xsqlite3 note**: If FTS4 rebuild fails (missing snowball tokenizer), either:
- Run from nomad-builder dir where xsqlite3 is available
- Or skip FTS4 rebuild (risky — DictEngine may crash without it)
- Or build xsqlite3 bindings once: `cd nomad-builder && ./tools/dictgen/build_xsqlite3_bindings.sh`

### Step 2: copyworks — smoke test (depends on step 1 output)

```bash
cd ~/repos/loqu8/copyworks
NOMAD_DATA=/tmp flutter run -d linux
# core-es.sqlite is at /tmp/core-es.sqlite
# Verify: Spanish definitions appear in worksheet generation
```

### Step 3: nomad-builder — build matrix (depends on step 1 script)

```bash
cd ~/repos/loqu8/nomad-builder
# Update release-copyworks-data.sh to call build_langpack.py in a loop
# for all 12 languages, using the existing core.sqlite as template
# CEROD encrypt each one, upload to GH releases
```

### Step 4: loqu8-dart — language pack support (independent of steps 1-3)

```bash
cd ~/repos/loqu8/loqu8-dart
# Extend DataService:
#   - downloadLanguagePack(lang) — download core-{lang}.xdb from GH releases
#   - setLanguage(lang) — switch active DB path
#   - availableLanguages — list downloaded packs
#   - activeLanguage — current lang code
# Test: unit test with mock download
```

### Step 5: copyworks — language picker UI (depends on step 4)

```bash
cd ~/repos/loqu8/copyworks
# Add language picker to settings
# Add first-run language selection
# Add download progress UI
# Test: full flow on Linux, then cross-platform
```

---

## Size Estimates

See [dictmaster-export-sizes.md](dictmaster-export-sizes.md) for detailed
per-language size estimates.

Summary:
- **Copyworks language pack**: ~27-30 MB compressed per language
- **Intuition language pack**: ~96-174 MB compressed per language
- **Copyworks-Lite** (no strokes): ~11 MB per language

---

## Licensing

All dictmaster sources are CC BY-SA compatible:

| Source | License | Status |
|--------|---------|--------|
| CC-CEDICT (en) | CC BY-SA 4.0 | Safe |
| CFDICT (fr) | CC BY-SA 3.0 | Safe |
| HanDeDict (de) | CC BY-SA 2.0 | Safe |
| CC-CIDICT (id) | CC BY-SA 4.0 | Safe |
| Wiktextract | CC BY-SA 4.0 | Safe |
| JMdict (ja) | CC BY-SA 4.0 | Safe |
| MiniMax M2.5 (AI) | Generated | No input license restrictions |
| Chardata (makemeahanzi) | Arphic PL / LGPL | Safe |
| Unihan | Unicode License | Safe |

**No CJKI data** is used in any of these exports.

---

## Dialect Data in Dict-Tier DBs (Decision: 2026-03-09)

**Decision**: Replicate `dialect_forms` into every `dict-{lang}.sqlite`.
Single-char stays in `chardata.sqlite` (existing). Multi-char goes into dict-tier.

**Rationale**: When a user hovers over 銀行, the dict engine looks up that headword
and returns everything about it — definitions, pinyin, AND dialect pronunciation.
Co-locating dialect data with definitions avoids a second DB open at query time.

**Size cost**: ~26 MB per language (511K rows). Replicated across 18 languages = ~462 MB total.
Acceptable vs 96-174 MB dict-tier base size (adds ~15-27%).

### Schema Addition to dict-{lang}.sqlite

```sql
CREATE TABLE dialect_forms (
    entry_id INTEGER NOT NULL,          -- matches Entries_content.docid
    dialect TEXT NOT NULL,              -- 'yue' or 'nan'
    pronunciation TEXT NOT NULL,        -- Jyutping or POJ/Tai-lo
    tone INTEGER NOT NULL DEFAULT 0,   -- extracted tone number
    native_chars TEXT,                  -- NULL for TYPE 1, different chars for TYPE 2
    gloss TEXT,                         -- English meaning if TYPE 2
    source TEXT NOT NULL
);
CREATE INDEX idx_dialect_forms_entry ON dialect_forms(entry_id);
CREATE INDEX idx_dialect_forms_lookup ON dialect_forms(entry_id, dialect);
```

### Implementation in build_split_dbs.py

Add after Step 6 (dict_single_chars), before Step 7 (RowCounts):

```python
# --- Step 6b: Import dialect_forms from dictmaster ---
print(f"  [6b/7] Importing dialect_forms...")
dm = sqlite3.connect(str(dictmaster_path))
char_filter = "AND length(h.traditional) = 1" if chars_only else ""

# Build docid lookup: (trad, simp, pinyin) → docid in Entries_content
docid_map = {}
for row in dst.execute("SELECT docid, traditional, simplified, pinyin FROM Entries_content"):
    docid_map[(row[1], row[2], row[3])] = row[0]

# Query dialect_forms with headword info
dialect_rows = dm.execute(f"""
    SELECT h.traditional, h.simplified, h.pinyin,
           d.dialect, d.pronunciation, d.native_chars, d.gloss, d.source
    FROM dialect_forms d
    JOIN headwords h ON h.id = d.headword_id
    WHERE 1=1 {char_filter}
      AND d.source NOT IN ('maryknoll', 'embree', 'kauiokpoo')  -- exclude NC/ND
    ORDER BY h.id, d.dialect, d.source
""").fetchall()

# Insert, dedup by (entry_id, dialect, source)
dst.execute("""CREATE TABLE dialect_forms (...)""")  # as above
# ... insert with tone extraction, same as chardata logic
```

### Commercial Filtering

The `--commercial` flag (or default behavior) excludes NC/ND sources:
- `maryknoll` (CC BY-NC-SA 3.0)
- `embree` (CC BY-NC-SA 3.0)
- `kauiokpoo` (CC BY-ND 3.0)

This is applied at export time via `WHERE source NOT IN (...)`.
dictmaster.db keeps all sources for research/Paper E.

### Products Using This

| Product | chardata.sqlite | dict-{lang}.sqlite | What it gets |
|---------|-----------------|-------------------|-------------|
| Copyworks | single-char pronunciation | NOT USED | Jyutping/POJ badges on worksheets |
| iCE | single-char pronunciation | multi-char pronunciation + lexical equivalents | Hover: 銀行 → ngan4 hong4 |
| Intuition Reader | single-char pronunciation | multi-char pronunciation + lexical equivalents | Inline annotation |

### Compositional Fallback Strategy

Coverage drops off for longer compounds: 3+ char headwords have dialect entries
for only 24% (Cantonese) and 8% (Hokkien). The dict engine must handle the gap.

**Cascade lookup in C++ DictEngine:**

```
lookupDialect(segment, dialect):
  1. Exact match in dict-tier dialect_forms → return it
  2. Try sub-segmentation (2-way splits) → if both halves have entries, concatenate
  3. Fall back to character-by-character from chardata.dialect_pronunciation
```

**Why this works:**
- **Cantonese**: pronunciation is compositional. No tone sandhi. Concatenating
  single-char readings gives correct result 95%+ of the time.
  中國銀行 → no entry → 中國(zung1 gwok3) + 銀行(ngan4 hong4) → correct.
- **Hokkien**: tone sandhi means concatenated citation tones are technically
  wrong in running speech (every non-final syllable shifts). But still useful
  as reference. Runtime sandhi via common-tl (MIT) is a future enhancement.

**Three-tier data architecture:**

| Tier | Location | Role | Coverage |
|------|----------|------|----------|
| Known compounds | `dict-{lang}.sqlite` dialect_forms | Exact match | 128K yue, 64K nan |
| Single-char fallback | `chardata.sqlite` dialect_pronunciation | Compositional | 16.5K yue, 6.8K nan |
| No data | — | Show nothing | Rare/literary chars |

This means chardata single-char is the **ultimate fallback** — always available.
Dict-tier entries are "known good" compound readings. The compositional cascade
bridges the 76% gap for 3+ char Cantonese compounds.

### C++ / Dart Integration (downstream)

1. `DictEngine::lookupDialectForms(segment, dialect)` — cascading lookup
   - Check dict-tier `dialect_forms` for exact match
   - Try sub-segmentation fallback
   - Fall to `ChardataDb` character-by-character
2. Returns `List<DialectForm>` with {pronunciation, tone, nativeChars, gloss, isComposed}
3. Dart `WordData` model gains `dialectForms` field
4. UI: "Cantonese: ngan4 hong4" / "Hokkien: gîn-hâng" shown alongside definition
5. `isComposed` flag lets UI show "(composed)" hint for fallback readings

---

## Open Questions

1. **Monetization**: Free all 12 languages? English free + others paid?
   Per-language IAP? Subscription? Affects DataService download logic
   and whether we need entitlement checks.

2. **Language manifest**: Where does the app discover available language
   packs and their download URLs? Options:
   - Hardcoded in app (simple, requires app update to add languages)
   - JSON manifest at a known URL (flexible, needs hosting)
   - GitHub Releases API (already used for updates)

3. **Chardata per language**: Currently chardata (strokes, HSK, etc.) is
   baked into every language pack. Could we ship chardata once and
   language definitions separately? Would halve download size for users
   who switch languages. But adds complexity to DataService.

4. **UI language vs dictionary language**: Flutter l10n handles UI strings.
   Dictionary language is separate (the definition text). Should they be
   linked? (User sets "Espanol" → both UI and definitions switch.) Probably
   yes for simplicity.

5. **Offline-first**: Language packs must work fully offline after download.
   No runtime dependency on network for definitions.

6. **Etymology hints**: Currently English ("picture of a person"). Translate
   them? Low priority but breaks the "no English" promise for non-English
   users. Could be a Phase 4 task.

7. **Lessons**: Lesson text files are currently English. Need per-language
   lesson content? Or are lessons just lists of characters (language-independent)?

---

## Next Steps

1. Add `export_single_chars()` to `tools/dictmaster/export.py`
2. Export a test CEDICT file (Spanish, single chars only)
3. Feed it through dictgen, verify output DB has Spanish definitions
4. Load in Copyworks via `NOMAD_DATA`, screenshot Spanish worksheets
5. Quality review the top-200 characters in Spanish
6. Design the language manifest format
7. Implement `DataService.downloadLanguagePack()` in loqu8-dart
