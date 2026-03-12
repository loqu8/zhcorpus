# Dictmaster pinyin format: "ming2 (ming²)5" origin

**Last updated**: 2026-03-11

## What it is

Some headwords in dictmaster have pinyin stored as e.g. `ming2 (ming²)5` instead of plain `ming2`:

- **ming2** — standard numeric tone (syllable + 1–5).
- **(ming²)** — same reading in **superscript-tone notation**: syllable + Unicode superscript digit (²). Common in references (e.g. “Tone numbers: jie¹mi⁴ zhong¹wen²”, [Hacking Chinese](https://www.hackingchinese.com/7-ways-to-write-mandarin-tones/)); the parentheses are just grouping for the alternate form.
- **5** — In Mandarin, **tone 5 = neutral tone** (轻声, unstressed/short). Wiktionary’s Module:cmn-pron uses `"5"` as the default when tone isn’t determined and has `|tl=y` for “toneless variant”. So the trailing **5** likely means “this reading has (or may have) a neutral-tone variant” or was emitted by the Wiktionary Lua when outputting multiple forms. Not definitively documented in Kaikki; this is the standard interpretation of “5” in pinyin.

Roughly 7,134 headwords in dictmaster have this pattern; copyworks/ice see ~14k entry rows with it (one headword → multiple lang rows).

## Where it came from

Dictmaster **does not generate** this string. It is stored **as-is** from the raw dictionary files:

1. **Build script**: `tools/dictmaster/build_master.py`
   - `--step import`: CEDICT-family (cedict, cfdict, handedict, cidict), Wiktextract, JMdict
   - `--step dialect`: CC-Canto, CC-CEDICT Cantonese readings, rime-cantonese, etc.

2. **Parsers** take pinyin from whatever appears between `[` and `]` in each line:
   - `parsers/cedict_format.py`: `pinyin = pinyin.strip()` (line 41)
   - `parsers/dialect.py`: `pinyin = pinyin_part.strip()` for CC-Canto and CC-CEDICT readings (lines 51, 99)
   - No normalization before `schema.upsert_headword(..., pinyin, ...)`.

3. **Merge** (`merge.py`) only uses `normalize_pinyin()` for **comparison** when reconciling duplicates (u:/ü → v, lowercasing, whitespace). It does **not** rewrite stored pinyin or strip the " (xxx¹–⁵)5" suffix.

So the format comes from the **upstream data files** in `data/raw/dictmaster/`. Verified in dictmaster: headwords with this pinyin have definitions only from **Wiktextract** (and Minimax/JMDict); none from CC-CEDICT, CEDICT-family, or Cantonese readings.

- **Wiktextract** (Kaikki.org Chinese): `kaikki.org-dictionary-Chinese.jsonl.gz` — the parser stores the `[pinyin]` field as-is from the JSON. So the "(xxx²)5" form is in the Kaikki/Chinese dump.
- **Not** from CC-CEDICT Cantonese readings or CC-Canto (those headwords have no definitions from cccedict-readings or cccanto).

## What we did downstream

- **nomad-builder** (`tools/dictgen/build_dbs.py`): When building consolidated copyworks.sqlite and ice.sqlite, we call `normalize_pinyin_display(pinyin)` to strip the " (xxx¹–⁵)5" suffix so the DB and UI show only numeric tone (e.g. ming2). See `docs/Areas/data-release-playbook.md` and the `SUPERSCRIPT_TONE` regex in build_dbs.py.

## Optional fix at source (zhcorpus)

To store clean pinyin in dictmaster itself (so all consumers get it without per-consumer normalization):

1. **Option A**: In `schema.upsert_headword()`, normalize pinyin before insert (e.g. add a helper that strips the " (xxx¹–⁵)5" suffix, and call it on the pinyin argument). Then re-import or run a one-off migration to clean existing rows.
2. **Option B**: In each parser that calls `upsert_headword`, pass `normalize_pinyin_display(entry.pinyin)` (or a zhcorpus equivalent) so only numeric-tone pinyin is stored. Requires adding the strip logic to zhcorpus (e.g. in `merge.py` next to `normalize_pinyin()`).

Until then, downstream normalization in nomad-builder is sufficient for copyworks and ice.
