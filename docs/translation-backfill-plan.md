# Translation Backfill Plan

Fill missing language definitions after the main v2 MiniMax translation run.

## Scope

Two categories of incomplete headwords:

| Category | Count | Description |
|----------|-------|-------------|
| **Partial** (1-11 langs) | 81,744 | Model dropped some langs during main run |
| **Zero defs** | 840 | API returned unparseable responses both times |
| **Total** | **82,584** | |

### Lang count distribution

| Langs present | Headwords | Strategy |
|--------------|-----------|----------|
| 11           | 73,215    | Backfill 1 missing lang |
| 10           | 7,026     | Backfill 2 missing langs |
| 9            | 309       | Backfill 3 missing langs |
| 1-8          | 1,194     | Backfill (may need full retranslation for 1-2 lang entries) |
| 0            | 840       | Full 12-lang translation via backfill prompt |

### Per-language gaps

| Lang | Missing | % of total |
|------|---------|------------|
| fa (Persian) | 33,274 | 7.8% |
| vi (Vietnamese) | 25,564 | 6.0% |
| tl (Tagalog) | 7,753 | 1.8% |
| es (Spanish) | 7,559 | 1.8% |
| sv (Swedish) | 6,376 | 1.5% |
| id (Indonesian) | 5,034 | 1.2% |
| en (English) | 4,157 | 1.0% |
| fr (French) | 2,817 | 0.7% |
| de (German) | 2,595 | 0.6% |
| ja (Japanese) | 2,059 | 0.5% |
| ru (Russian) | 1,655 | 0.4% |
| ko (Korean) | 1,098 | 0.3% |
| **Total slots** | **~110K** | |

## Design: Context-Aware Backfill

### Key principle

Send existing translations as read-only context so the model produces definitions
that are consistent/parallel with what's already there.

### How it works

For a headword with 11 langs present (missing `vi`):

```
System: Fill in ONLY the missing language definitions.
        Existing translations are provided for consistency.
        [same v2 rules: CJK prohibition, ja meaning, ko hangul-only, etc.]

User:
1. 三角褲 / 三角裤
   Pinyin: sān jiǎo kù
   Existing translations:
     en: briefs/underwear
     de: Slip/Unterhose
     fr: slip/caleçon
     ja: ブリーフ
     ko: 삼각 팬티
     ru: трусы/плавки
     ...
   MISSING — fill these:
     vi:
```

The model sees all existing translations and produces `vi: quần lót/quần sịp`
matching the style and specificity of the others.

### Script

```bash
# Dry run — show what would be backfilled
PYTHONPATH=. .venv/bin/python tools/dictmaster/backfill_langs.py --dry-run

# Test 20 entries (sequential, 1 worker)
PYTHONPATH=. .venv/bin/python tools/dictmaster/backfill_langs.py --limit 20

# Full backfill with 20 parallel workers
PYTHONPATH=. .venv/bin/python -u tools/dictmaster/backfill_langs.py --workers 20

# Include the 840 zero-def headwords too
PYTHONPATH=. .venv/bin/python -u tools/dictmaster/backfill_langs.py --workers 20 --include-zero
```

Implementation: `tools/dictmaster/backfill_langs.py`

### Prompt differences from main run

| Aspect | Main run | Backfill |
|--------|----------|----------|
| System prompt | "produce definitions in 12 languages" | "fill in ONLY the missing languages" |
| Context | CC-CEDICT English defs as context | Existing minimax defs in all present langs |
| Output | All 12 langs per entry | Only missing langs |
| `prompt_version` | `v2` | `v2-backfill` |

### Parser

Handles two response formats:
1. **Numbered** (multi-lang gaps): `1. 三角褲\n  fr: slip\n  id: celana dalam`
2. **Unnumbered** (single-lang gaps): `id: variasi lama dari 廉\n\nid: varian dari 迥`

The model drops entry numbers when each entry only needs 1 definition.

### Token estimate

- Avg missing langs per partial entry: 1.2
- Per entry: ~150 tokens context (existing 10-11 defs) + ~30 tokens per missing lang
- Batch of 20: ~500 system + 20×150 input + 20×36 output = ~4,220 tokens
- **Total**: ~82K entries ÷ 20 per batch = 4,100 requests × ~4.2K tokens = ~17M tokens
- **Cost: ~$5-7 on MiniMax** (vs $93 for full run)

### Tested

| Test | Result |
|------|--------|
| Single missing lang (sv, vi) | 5/5 filled |
| Multi missing langs (fa+vi, fr+id) | 10/10 filled |
| Zero-def headwords (all 12) | 36/36 filled |
| Parallel workers | Same pattern as main run |
| `prompt_version = 'v2-backfill'` | Correctly tagged in DB |

## Execution

```bash
# 1. Run the backfill (in tmux for safety)
tmux new-session -s backfill
PYTHONPATH=. .venv/bin/python -u tools/dictmaster/backfill_langs.py \
  --workers 20 --include-zero 2>&1 | tee logs/backfill.log

# 2. After completion, audit coverage
.venv/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/artifacts/dictmaster.db')
total = conn.execute('SELECT COUNT(*) FROM headwords').fetchone()[0]
full = conn.execute('''
    SELECT COUNT(*) FROM (
        SELECT headword_id FROM definitions WHERE source='minimax'
        GROUP BY headword_id HAVING COUNT(DISTINCT lang) = 12
    )
''').fetchone()[0]
print(f'Full 12-lang coverage: {full:,} / {total:,} ({full/total*100:.1f}%)')
"

# 3. Target: 428,073 × 12 = 5,136,876 definitions
```

## Results (2026-03-02)

Backfill completed in 92 minutes at 14 entries/s with 20 workers.

| Metric | Before backfill | After backfill |
|--------|----------------|----------------|
| Full 12-lang coverage | 345,489 (80.7%) | **422,198 (98.6%)** |
| Zero-def headwords | 840 | **0** |
| Total minimax defs | 5,026,855 | **5,130,189** |
| Worst lang (fa) | 393,959 (92.0%) | **425,840 (99.5%)** |

### Final per-language coverage

| Lang | Count | Coverage |
|------|-------|----------|
| de | 427,973 | 100.0% |
| ko | 427,970 | 100.0% |
| ru | 427,922 | 100.0% |
| fr | 427,904 | 100.0% |
| ja | 427,819 | 99.9% |
| en | 427,818 | 99.9% |
| es | 427,716 | 99.9% |
| id | 427,712 | 99.9% |
| sv | 427,592 | 99.9% |
| tl | 427,523 | 99.9% |
| vi | 426,400 | 99.6% |
| fa | 425,840 | 99.5% |

5,875 headwords still have partial coverage (model dropped 1-2 langs on these).
A second backfill pass could reduce this further but diminishing returns — 98.6%
full coverage is effectively complete.

## Phase 2: 18-Language Expansion (2026-03-09)

After completing the initial 12-language run, 6 new languages were added to the pipeline:
**nl** (Dutch), **pt** (Portuguese), **ar** (Arabic), **th** (Thai), **hi** (Hindi), **it** (Italian).

The main translation run (`build_master.py --step translate`) produced ~99K definitions
per new language. This left 329,122 headwords × 6 languages = 1,974,732 slots to backfill.

### MiniMax API Outage

The MiniMax API experienced a brief outage on 2026-03-09 during which API calls returned
errors. The backfill for the 6 new languages was blocked until the API recovered later
the same day.

### Backfill Run

**IMPORTANT: Always use tmux** — this job takes ~24h and will die if the parent
process (Claude Code, terminal) closes.

```bash
# Launch in tmux (the canonical command — copy-paste this)
cd /home/tim/repos/loqu8/zhcorpus
tmux new-session -d -s backfill \
  "PYTHONPATH=. .venv/bin/python -u tools/dictmaster/backfill_langs.py \
   --workers 20 --batch-size 20 2>&1 | tee logs/backfill-\$(date +%Y%m%d).log"

# Monitor
tmux attach -t backfill          # watch live
tail -f logs/backfill-*.log      # follow log
tmux ls                          # verify session alive

# Check coverage anytime
PYTHONPATH=. .venv/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/artifacts/dictmaster.db')
total = conn.execute('SELECT COUNT(*) FROM headwords').fetchone()[0]
for lang in ['nl','pt','ar','th','hi','it']:
    c = conn.execute('SELECT COUNT(*) FROM definitions WHERE lang=? AND source=\"minimax\"', (lang,)).fetchone()[0]
    print(f'  {lang}: {c:,} / {total:,} ({c/total*100:.1f}%)')
"
```

**Safe to restart** — the script uses the DB as a live queue. Completed entries are
automatically skipped. Just re-run the tmux command above.

| Metric | Value |
|--------|-------|
| Headwords at start | 329,122 |
| Missing definition slots | 1,974,732 |
| Languages | nl, pt, ar, th, hi, it |
| Workers | 20 |
| Rate | ~3.6 entries/s |
| Estimated time | ~24 hours |

#### Run history

| Date | Progress | Notes |
|------|----------|-------|
| 2026-03-09 | 14,000/342,869 (~4%) | Ran in Claude Code without tmux, died when session closed |
| 2026-03-10 | Restarted at 315,824 remaining | Launched in tmux properly |
| 2026-03-11 | 1,400/87,871 (~1.6%) | Restarted with 20 workers, ~4 entries/s |

### Concurrency Architecture (for publication notes)

**Current Implementation (backfill_langs.py):**
- Single shared SQLite connection across all workers
- ThreadPoolExecutor with `as_completed()` processes futures **one at a time**
- Each result is saved synchronously before fetching the next
- This serializes writes, defeating parallelism benefits
- SQLite is NOT thread-safe for concurrent writes

**Problem:**
- At 20 workers, actual throughput is ~4 entries/sec (vs 14 entries/sec on 2026-03-02)
- The bottleneck is serialized DB writes, not API calls
- Higher workers (50, 100) would hit "database is locked" errors

**Improved Design (backfill_langs_v2.py):**
```
Workers (API calls) → Queue.Queue → Single writer thread → SQLite
```

Benefits:
- Parallel API calls (workers don't wait for each other)
- Serialized DB writes (no lock contention, safe)
- Batch inserts via `executemany()` for efficiency
- Can scale workers freely (50, 100+) without DB issues

See: `tools/dictmaster/backfill_langs_v2.py` for implementation.

### Per-language coverage before backfill

| Lang | Count | Coverage | Status |
|------|-------|----------|--------|
| ar | 98,951 | 23.1% | Backfilling |
| hi | 98,951 | 23.1% | Backfilling |
| it | 98,951 | 23.1% | Backfilling |
| nl | 98,951 | 23.1% | Backfilling |
| pt | 98,951 | 23.1% | Backfilling |
| th | 98,951 | 23.1% | Backfilling |
| fa | 428,117 | 100.0% | Complete |
| ko | 428,117 | 100.0% | Complete |
| ru | 428,117 | 100.0% | Complete |
| sv | 428,117 | 100.0% | Complete |
| tl | 428,117 | 100.0% | Complete |
| vi | 428,117 | 100.0% | Complete |
| es | 432,517 | 100.0% | Complete |
| fr | 484,397 | 100.0% | Complete (multi-source) |
| id | 551,274 | 100.0% | Complete (multi-source) |
| ja | 559,544 | 100.0% | Complete (multi-source) |
| de | 587,926 | 100.0% | Complete (multi-source) |
| en | 691,821 | 100.0% | Complete (multi-source) |

## Residual Single-Char Gaps: Root Cause Analysis (2026-03-12)

After all backfill passes and the contamination cleanup, **2,865 single-char
headwords** still have gaps in 1–6 languages (7,217 total definition slots).
All multi-char headwords are 100% complete. Zero headwords have zero definitions.

### Gap distribution by language

| Lang | Gaps | % of 30,546 |
|------|------|------------|
| ar (Arabic) | 1,084 | 3.5% |
| th (Thai) | 1,016 | 3.3% |
| de (German) | 892 | 2.9% |
| fa (Persian) | 660 | 2.2% |
| es (Spanish) | 635 | 2.1% |
| sv (Swedish) | 496 | 1.6% |
| ru (Russian) | 355 | 1.2% |
| hi (Hindi) | 301 | 1.0% |
| fr–it | 165–264 | 0.5–0.9% |

Arabic and Thai have the most gaps. **All HSK characters are 100% complete.**

### Root cause: bound morphemes + script purity

The vast majority (~90%) of these gaps are **bound morphemes** — characters with
no independent meaning that only appear inside specific compounds. Their English
definitions look like:

> 躊 [chóu]: "used in 躊躇／踌躇 (chóuchú), etc."
> 峍 [lù]: "used in 崛峍/峍矹/峍崪"
> 螔 [sī]: "only used in 螔䗔"

To define these in Arabic, the LLM correctly writes:

> يُستخدم في 躊躇／踌躇 (chóuchú)

But this contains **three scripts**: Arabic + CJK characters (躊躇) + Latin pinyin
(chóuchú). The script validator rejects it because:

1. **CJK characters** — the 躊躇 cross-reference IS legitimate (you can't explain
   what 躊 means without citing the compound it appears in), but the validator
   wasn't recognizing all cross-reference patterns in all languages.

2. **Latin pinyin in Arabic** — the `(chóuchú)` parenthetical is genuinely wrong
   for Arabic. Arabic readers can't read Latin pinyin. The LLM should either
   transliterate to Arabic script (تشو تشو) or omit it entirely. This rejection
   is **correct** and should remain.

### Why some languages are harder than others

- **Arabic/Persian**: No Latin script allowed at all. The LLM tends to include
  Latin pinyin in parentheticals, which is invalid. Also, the LLM sometimes falls
  back to Russian (Cyrillic) when it can't figure out Arabic.
- **Thai**: Same problem — the LLM includes Latin pinyin. Additionally, the Thai
  "used in" phrase (`ใช้ใน`) wasn't in the validator's reference pattern list until
  the 2026-03-12 fix.
- **German/French/Spanish**: These gaps are mostly from Wiktextract duplicate
  entries with unusual pinyin encodings (e.g., `shi4 (shi⁴)5`), not from
  validator rejections. The LLM sometimes fails to produce valid output for these.

### Validator fixes applied (2026-03-12)

1. **Added Thai/Arabic/Persian/Hindi "used in" phrases** to the reference pattern
   list: `ใช้ใน`, `يُستخدم في`, `استفاده در`, `में प्रयुक्त`
2. **Added conjunction/slash patterns** for multiple CJK runs:
   `躊躇／踌躇` and `躊躇 و 踌躇` now both pass (each CJK run is recognized
   as part of a reference frame)
3. **Added `ใน` (Thai "in")** as a preposition that can precede CJK

These fixes mean the next backfill pass will recover many of the Thai/Arabic gaps
where the LLM was producing correct output that the validator was wrongly rejecting.

### What won't be recovered

- Entries where the LLM includes Latin pinyin in Arabic/Persian/Thai definitions
  (correct rejection — the LLM needs to transliterate or omit)
- Entries where the LLM falls back to Cyrillic/wrong language
- Entries for extremely obscure characters with no real meaning in any language

### Wiktextract duplicate pinyin (82% of gaps)

2,346 of the 2,865 gap headwords are caused by a Wiktextract import artifact.
Wiktextract stores pinyin with both numeric and superscript tones plus a
trailing neutral-tone marker:

    suo3 (suo³)5     ← Wiktextract format
    suo3             ← CC-CEDICT format (the normal one)

Our parser imported these as separate headwords because the pinyin strings
differ. The clean `suo3` entry has 18/18 langs. The duplicate `suo3 (suo³)5`
sits partially filled.

**No shipping impact**: `build_dbs.py` already normalizes pinyin at export
via `normalize_pinyin_display()`, so duplicates merge into one row in
copyworks.xdb and ice.xdb. The duplicates only matter when counting "gaps"
in dictmaster.db.

**Future fix**: normalize Wiktextract pinyin at import time (in the parser)
to prevent duplicate headword creation. This would eliminate 82% of gaps.

### Impact on shipping

**None.** All HSK characters are complete. All high-frequency characters are
complete. The gaps are exclusively in obscure radicals, bound morphemes, and
Wiktextract duplicates that no learner will encounter.

## Notes

- Entries with only 1-2 langs may have had fundamentally bad API responses.
  The backfill prompt sends `(none)` for existing context, which is the same
  as a fresh translation. If they fail again, they're likely untranslatable
  edge cases (rare chars, empty pinyin, etc.).
- `--include-zero` is optional. The 840 zero-def entries failed twice already;
  the backfill prompt format may help since it's a different prompt structure.
- The backfill script has 3 layers of overwrite protection:
  1. Query only returns headwords with < 18 langs
  2. Parser only accepts langs listed in `missing_langs` (no fallback)
  3. `SELECT 1` DB check before every write — skips if definition exists
- **MiniMax API reliability**: The API had a brief outage on 2026-03-09. No status page
  or incident communication was available. Have a fallback provider ready for
  time-sensitive runs.
