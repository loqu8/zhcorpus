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

## Notes

- Entries with only 1-2 langs may have had fundamentally bad API responses.
  The backfill prompt sends `(none)` for existing context, which is the same
  as a fresh translation. If they fail again, they're likely untranslatable
  edge cases (rare chars, empty pinyin, etc.).
- `--include-zero` is optional. The 840 zero-def entries failed twice already;
  the backfill prompt format may help since it's a different prompt structure.
- The backfill script has 3 layers of overwrite protection:
  1. Query only returns headwords with < 12 langs
  2. Parser only accepts langs listed in `missing_langs` (no fallback)
  3. `SELECT 1` DB check before every write — skips if definition exists
