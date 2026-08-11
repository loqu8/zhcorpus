# 26-Language Expansion Plan

Extend dictmaster from 18 to 26 languages by adding 8 new target languages.

## Motivation

A user's wife teaches Chinese to students in Estonia. This surfaces real demand for
underserved European and Central Asian languages. The 8 new languages span Belt & Road
economies, Central/Eastern Europe, and the Balkans — markets where no Chinese dictionary
product exists in the target language.

## New Languages

| # | Lang | Code | Script | Speakers | Why |
|---|------|------|--------|----------|-----|
| 1 | Turkish | tr | Latin | 85M | Belt & Road, huge trade growth with China |
| 2 | Malay | ms | Latin | 33M | Malaysia has 7M ethnic Chinese; distinct from id |
| 3 | Polish | pl | Latin | 45M | Largest Central European economy, 15 Confucius Institutes |
| 4 | Hungarian | hu | Latin | 13M | Chinese investment hub in EU, Fudan campus |
| 5 | Czech | cs | Latin | 10M | Prague has large Chinese community |
| 6 | Greek | el | Greek | 13M | Piraeus port (COSCO), growing China ties |
| 7 | Romanian | ro | Latin | 24M | EU, growing Belt & Road ties |
| 8 | Estonian | et | Latin | 1.1M | Real user demand right now |

**Total new speakers reached: ~225M**

## Script Analysis

7 of 8 use Latin script — straightforward, same as en/de/fr/es/etc.

**Greek (el)** is the only non-Latin script. Considerations:
- Greek script (U+0370–U+03FF) — already detected by `_detect_scripts()` as `"greek"`
- Needs its own `VALID_SCRIPTS` entry: `{"greek", "latin"}` (Greek uses some Latin loanwords/acronyms)
- Needs CJK reference patterns in Greek: "παραλλαγή" (variant), "συντομογραφία" (abbreviation), etc.
- Script purity prompt rule: "Write in Greek script. Do NOT transliterate from English."
- Lower contamination risk than Arabic/Thai (Greek keyboard is standard, LLMs handle it well)

## Files to Modify

### 1. `tools/dictmaster/translate/prompts.py`

- Add 8 entries to `LANG_NAMES`:
  ```python
  "tr": "Turkish",
  "ms": "Malay",
  "pl": "Polish",
  "hu": "Hungarian",
  "cs": "Czech",
  "el": "Greek",
  "ro": "Romanian",
  "et": "Estonian",
  ```

- Append 8 codes to `ALL_TARGET_LANGS` (order: existing 18, then new 8)

- Update `UNIVERSAL_SYSTEM_PROMPT`:
  - Change "18 languages" to "26 languages"
  - Add language-specific rules for Greek:
    ```
    - el (Greek): Write in Greek script. Use proper diacritics (tonos). Do NOT transliterate from English.
    ```
  - Add rules for languages with special characters:
    ```
    - tr (Turkish): Use proper Turkish characters (ğ, ş, ç, ı, ö, ü). Do NOT substitute ASCII.
    - pl (Polish): Use proper Polish diacritics (ą, ć, ę, ł, ń, ó, ś, ź, ż).
    - cs (Czech): Use proper Czech diacritics (á, č, ď, é, ě, í, ň, ó, ř, š, ť, ú, ů, ý, ž).
    - hu (Hungarian): Use proper Hungarian accents (á, é, í, ó, ö, ő, ú, ü, ű).
    - ro (Romanian): Use proper Romanian diacritics (ă, â, î, ș, ț). Use comma-below (ș, ț), NOT cedilla.
    - et (Estonian): Use proper Estonian characters (ä, ö, ü, õ, š, ž).
    - ms (Malay): Write in standard Malay (Bahasa Melayu). Distinguish from Indonesian where conventions differ.
    ```

### 2. `tools/dictmaster/script_validator.py`

- Add to `VALID_SCRIPTS`:
  ```python
  "tr": {"latin"},
  "ms": {"latin"},
  "pl": {"latin"},
  "hu": {"latin"},
  "cs": {"latin"},
  "el": {"greek", "latin"},
  "ro": {"latin"},
  "et": {"latin"},
  ```

- Add Greek CJK reference patterns to `_REF_PATTERNS`:
  ```python
  # Greek
  re.compile(rf'(?:παραλλαγή|συντομογραφία|στοιχείο|χαρακτήρας|μορφή)\s.*?({_CJK_RUN})', re.IGNORECASE),
  ```

- Add new language terms to the "used in" pattern and "of X" pattern:
  - Turkish: "kullanılan", "varyant"
  - Polish: "wariant", "skrót", "używany"
  - Czech: "varianta", "zkratka", "používaný"
  - Hungarian: "változat", "rövidítés"
  - Romanian: "variantă", "abreviere"
  - Estonian: "variant", "lühend"
  - Malay: "varian", "singkatan" (already present via Indonesian overlap)
  - Greek: "παραλλαγή", "συντομογραφία"

### 3. `tools/dictmaster/backfill_langs.py`

- Update `BACKFILL_SYSTEM_PROMPT`:
  - Add language-specific rules for Greek, Turkish, Polish, Czech, Hungarian, Romanian, Estonian, Malay
  - Same diacritics/script rules as the universal prompt

### 4. No schema changes needed

The `definitions` table stores `lang` as a free text column — no enum, no migration.

## Execution Plan

### Phase 1: Code changes (this session)
1. Update `prompts.py` — LANG_NAMES, ALL_TARGET_LANGS, UNIVERSAL_SYSTEM_PROMPT
2. Update `script_validator.py` — VALID_SCRIPTS, reference patterns
3. Update `backfill_langs.py` — BACKFILL_SYSTEM_PROMPT

### Phase 2: Initial translation run
```bash
# Main run via build_master.py (produces ~99K defs per new lang)
PYTHONPATH=. .venv/bin/python tools/dictmaster/build_master.py \
  --step translate --backend api
```

This translates all 428K headwords but only fills the 8 new language slots
(existing 18 langs already have definitions and are skipped).

### Phase 3: Backfill remaining gaps
```bash
# In tmux (ALWAYS — this takes ~24-48h)
cd /home/tim/Projects/loqu8/zhcorpus
tmux new-session -d -s backfill \
  "PYTHONPATH=. .venv/bin/python -u tools/dictmaster/backfill_langs.py \
   --workers 20 --batch-size 20 2>&1 | tee logs/backfill-26lang-$(date +%Y%m%d).log"
```

### Phase 4: Audit coverage
```bash
PYTHONPATH=. .venv/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/artifacts/dictmaster.db')
total = conn.execute('SELECT COUNT(*) FROM headwords').fetchone()[0]
for lang in ['tr','ms','pl','hu','cs','el','ro','et']:
    c = conn.execute('SELECT COUNT(*) FROM definitions WHERE lang=? AND source=\"minimax\"', (lang,)).fetchone()[0]
    print(f'  {lang}: {c:,} / {total:,} ({c/total*100:.1f}%)')
"
```

## Cost Estimate

- 428K headwords x 8 new langs = 3,424,000 definition slots
- Main run: ~428K headwords in batches of 20 = ~21,400 API calls
  - Each call produces 8 new lang lines (existing 18 already filled)
  - ~500 system + 20 x 200 input + 20 x 8 x 30 output = ~9,300 tokens per call
  - Total: ~200M tokens
  - **MiniMax cost: ~$50-70** (at list price; likely ~$10-15 on Coding Plan)
- Backfill pass: ~$5-10 additional

## Model

Using **MiniMax-M2.7** (upgrade from M2.5 used in the original 18-lang run).
Config: `~/.claude/settings.minimax.json` already set to `ANTHROPIC_MODEL: "MiniMax-M2.7"`.

M2.7 improvements relevant to this task:
- Better multilingual quality (especially for lower-resource languages like Estonian, Hungarian)
- Same Anthropic-compatible API endpoint (`api.minimax.io/anthropic`)
- No code changes needed — `minimax_api.py` reads model from config

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| MiniMax API outage | Blocks translation | Resumable script; restart anytime |
| Greek script contamination | Bad defs rejected | Script validator catches it; backfill retries |
| Malay/Indonesian confusion | Wrong register | Explicit prompt: "Bahasa Melayu, NOT Indonesian" |
| Romanian cedilla vs comma-below | Wrong diacritics | Explicit prompt: "comma-below (ș, ț)" |
| Turkish I/ı confusion | Wrong casing | Explicit prompt; validator passes Latin either way |
| Low MiniMax quality for Estonian | Rare language | Estonian is grammatically complex; may need spot-check |

## Malay vs Indonesian

Malay (ms) and Indonesian (id) share ~80% mutual intelligibility but have distinct:
- Vocabulary: ms "kereta" (car) vs id "mobil"
- Spelling: ms "imbuhan" conventions differ
- Register: ms uses more English/Malay loanwords; id uses more Dutch/Javanese

The prompt explicitly tells the model to produce Malay, not Indonesian. Both are kept
as separate languages in the dictionary.

## After Completion

- Update MEMORY.md with new lang count (26 languages)
- Update dictmaster stats in docs
- Run `build_split_dbs.py` in nomad-builder to produce shipping databases
- 26 languages x 428K headwords = **11.1M definitions** (target)
