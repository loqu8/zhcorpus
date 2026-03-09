"""Parse Cantonese and Hokkien dialect data sources.

Supports:
- CC-Canto (CEDICT format with {jyutping})
- CC-CEDICT Cantonese Readings (pronunciation overlay)
- iTaigi (CSV, CC0)
- 台華線頂對照典 (CSV, CC BY-SA 4.0)
"""

import csv
import re
import sqlite3
from pathlib import Path
from typing import Optional

from tools.dictmaster.schema import (
    ensure_source,
    upsert_dialect_form,
    upsert_headword,
)


# ---------------------------------------------------------------------------
# CC-Canto: CEDICT format with {jyutping} braces
# Format: TRAD SIMP [pinyin] {jyutping} /def1/def2/
# ---------------------------------------------------------------------------

_JYUTPING_RE = re.compile(r"\{([^}]+)\}")


def parse_cccanto_line(line: str) -> Optional[dict]:
    """Parse a CC-Canto line. Returns dict or None for comments/blank/no-jyutping."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    # Must have jyutping in braces
    jm = _JYUTPING_RE.search(line)
    if not jm:
        return None

    jyutping = jm.group(1).strip()

    try:
        trad_simp, rest = line.split("[", 1)
        pinyin_part, after_pinyin = rest.split("]", 1)

        parts = trad_simp.strip().split(" ", 1)
        traditional = parts[0]
        simplified = parts[1].strip() if len(parts) > 1 else traditional
        pinyin = pinyin_part.strip()

        # Extract definitions (after {jyutping})
        after_jyutping = _JYUTPING_RE.sub("", after_pinyin).strip()
        definitions = []
        if after_jyutping.startswith("/"):
            after_jyutping = after_jyutping[1:]
        if after_jyutping.endswith("/"):
            after_jyutping = after_jyutping[:-1]
        if after_jyutping:
            definitions = [d.strip() for d in after_jyutping.split("/") if d.strip()]

        return {
            "traditional": traditional,
            "simplified": simplified,
            "pinyin": pinyin,
            "jyutping": jyutping,
            "definitions": definitions,
        }
    except (ValueError, IndexError):
        return None


# ---------------------------------------------------------------------------
# CC-CEDICT Cantonese Readings: pronunciation overlay (no definitions)
# Format: TRAD SIMP [pinyin] {jyutping}
# ---------------------------------------------------------------------------


def parse_cccedict_readings_line(line: str) -> Optional[dict]:
    """Parse a CC-CEDICT Cantonese readings line. Returns dict or None."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    jm = _JYUTPING_RE.search(line)
    if not jm:
        return None

    jyutping = jm.group(1).strip()

    try:
        trad_simp, rest = line.split("[", 1)
        pinyin_part, _ = rest.split("]", 1)

        parts = trad_simp.strip().split(" ", 1)
        traditional = parts[0]
        simplified = parts[1].strip() if len(parts) > 1 else traditional
        pinyin = pinyin_part.strip()

        return {
            "traditional": traditional,
            "simplified": simplified,
            "pinyin": pinyin,
            "jyutping": jyutping,
        }
    except (ValueError, IndexError):
        return None


# ---------------------------------------------------------------------------
# iTaigi: CSV with HoaBun (Mandarin) ↔ HanLoTaibunPoj (Hokkien chars)
# Columns: DictWordID, PojUnicode, PojInput, KipUnicode, KipInput,
#          HanLoTaibunPoj, HanLoTaibunKip, HoaBun, DataProvidedBy
# ---------------------------------------------------------------------------


def parse_itaigi_row(row: dict) -> Optional[dict]:
    """Parse an iTaigi CSV row. Returns dict or None if insufficient data."""
    mandarin = row.get("HoaBun", "").strip()
    if not mandarin:
        return None

    native_chars = row.get("HanLoTaibunPoj", "").strip()
    pronunciation = row.get("PojUnicode", "").strip()
    if not pronunciation:
        pronunciation = row.get("KipUnicode", "").strip()
    if not pronunciation:
        return None

    # If Hokkien chars are the same as Mandarin, it's pronunciation-only
    if native_chars == mandarin:
        native_chars = None

    return {
        "mandarin": mandarin,
        "native_chars": native_chars or None,
        "pronunciation": pronunciation,
    }


# ---------------------------------------------------------------------------
# 台華線頂對照典: CSV with HoaBun ↔ HanLoTaibunPoj
# Columns: DictWordID, PojUnicode, PojUnicodeOthers, PojInput, PojInputOthers,
#          HanLoTaibunPoj, KipUnicode, KipUnicodeOthers, KipInput,
#          KipInputOthers, HanLoTaibunKip, HoaBun
# ---------------------------------------------------------------------------


def parse_taihua_row(row: dict) -> Optional[dict]:
    """Parse a 台華對照典 CSV row. Returns dict or None if insufficient data."""
    mandarin = row.get("HoaBun", "").strip()
    if not mandarin:
        return None

    native_chars = row.get("HanLoTaibunPoj", "").strip()
    pronunciation = row.get("PojUnicode", "").strip()
    if not pronunciation:
        pronunciation = row.get("KipUnicode", "").strip()
    if not pronunciation:
        return None

    if native_chars == mandarin:
        native_chars = None

    return {
        "mandarin": mandarin,
        "native_chars": native_chars or None,
        "pronunciation": pronunciation,
    }


# ---------------------------------------------------------------------------
# Import functions: parse files and insert into DB
# ---------------------------------------------------------------------------


def import_cccanto(
    conn: sqlite3.Connection,
    file_path: Path,
    limit: Optional[int] = None,
) -> int:
    """Import CC-Canto entries into dialect_forms table.

    For entries that match existing headwords: add Jyutping as dialect form.
    For new entries (Cantonese-specific): create headword + dialect form + English def.
    Returns number of dialect forms inserted.
    """
    ensure_source(conn, "cccanto")
    count = 0

    with open(file_path, encoding="utf-8") as f:
        for line in f:
            if limit and count >= limit:
                break

            entry = parse_cccanto_line(line)
            if not entry:
                continue

            hw_id = upsert_headword(
                conn, entry["traditional"], entry["simplified"], entry["pinyin"],
            )

            gloss = "/".join(entry["definitions"]) if entry["definitions"] else None
            upsert_dialect_form(
                conn, hw_id, "yue", entry["jyutping"], "cccanto",
                gloss=gloss,
            )
            count += 1

    conn.commit()
    return count


def import_cccedict_readings(
    conn: sqlite3.Connection,
    file_path: Path,
    limit: Optional[int] = None,
) -> int:
    """Import CC-CEDICT Cantonese readings (pronunciation-only overlay).

    Only imports entries that match existing headwords.
    Returns number of dialect forms inserted.
    """
    ensure_source(conn, "cccedict-readings")

    # Build lookup of existing headwords for fast matching
    existing = {}
    for row in conn.execute("SELECT id, traditional, simplified, pinyin FROM headwords"):
        key = (row["traditional"], row["simplified"], row["pinyin"])
        existing[key] = row["id"]

    count = 0
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            if limit and count >= limit:
                break

            entry = parse_cccedict_readings_line(line)
            if not entry:
                continue

            key = (entry["traditional"], entry["simplified"], entry["pinyin"])
            hw_id = existing.get(key)
            if not hw_id:
                continue

            upsert_dialect_form(
                conn, hw_id, "yue", entry["jyutping"], "cccedict-readings",
            )
            count += 1

    conn.commit()
    return count


def _read_csv_with_bom(file_path: Path) -> list[dict]:
    """Read a CSV file, handling BOM in header."""
    with open(file_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def import_itaigi(
    conn: sqlite3.Connection,
    file_path: Path,
    limit: Optional[int] = None,
) -> int:
    """Import iTaigi Mandarin-Hokkien pairs into dialect_forms.

    Matches HoaBun (Mandarin) against existing headwords (traditional or simplified).
    Returns number of dialect forms inserted.
    """
    ensure_source(conn, "itaigi")

    # Build lookup: text → list of headword IDs
    hw_by_text = _build_headword_lookup(conn)

    rows = _read_csv_with_bom(file_path)
    count = 0

    for row in rows:
        if limit and count >= limit:
            break

        parsed = parse_itaigi_row(row)
        if not parsed:
            continue

        hw_ids = hw_by_text.get(parsed["mandarin"], [])
        if not hw_ids:
            continue

        for hw_id in hw_ids:
            upsert_dialect_form(
                conn, hw_id, "nan", parsed["pronunciation"], "itaigi",
                native_chars=parsed["native_chars"],
            )
            count += 1

    conn.commit()
    return count


def import_taihua(
    conn: sqlite3.Connection,
    file_path: Path,
    limit: Optional[int] = None,
) -> int:
    """Import 台華線頂對照典 Mandarin-Hokkien pairs into dialect_forms.

    Matches HoaBun (Mandarin) against existing headwords.
    Returns number of dialect forms inserted.
    """
    ensure_source(conn, "taihua")

    hw_by_text = _build_headword_lookup(conn)

    rows = _read_csv_with_bom(file_path)
    count = 0

    for row in rows:
        if limit and count >= limit:
            break

        parsed = parse_taihua_row(row)
        if not parsed:
            continue

        hw_ids = hw_by_text.get(parsed["mandarin"], [])
        if not hw_ids:
            continue

        for hw_id in hw_ids:
            upsert_dialect_form(
                conn, hw_id, "nan", parsed["pronunciation"], "taihua",
                native_chars=parsed["native_chars"],
            )
            count += 1

    conn.commit()
    return count


def import_chhoetaigi_generic(
    conn: sqlite3.Connection,
    file_path: Path,
    source_name: str,
    limit: Optional[int] = None,
) -> int:
    """Import a ChhoeTaigi CSV with HoaBun + PojUnicode into dialect_forms.

    Works for Kauiokpoo, Embree, Maryknoll, TaioanPehoeKichhooGiku.
    Only imports entries matching existing headwords.
    Returns number of dialect forms inserted.
    """
    ensure_source(conn, source_name)
    hw_by_text = _build_headword_lookup(conn)

    rows = _read_csv_with_bom(file_path)
    count = 0

    for row in rows:
        if limit and count >= limit:
            break

        mandarin = row.get("HoaBun", "").strip()
        pronunciation = row.get("PojUnicode", "").strip()
        if not mandarin or not pronunciation:
            continue
        # KipUnicode as fallback
        if not pronunciation:
            pronunciation = row.get("KipUnicode", "").strip()
        if not pronunciation:
            continue

        # Try HanLoTaibunPoj for native chars if available
        native_chars = row.get("HanLoTaibunPoj", "").strip() or None
        if native_chars == mandarin:
            native_chars = None

        hw_ids = hw_by_text.get(mandarin, [])
        if not hw_ids:
            continue

        for hw_id in hw_ids:
            upsert_dialect_form(
                conn, hw_id, "nan", pronunciation, source_name,
                native_chars=native_chars,
            )
            count += 1

    conn.commit()
    return count


def derive_hokkien_from_compounds(
    conn: sqlite3.Connection,
    min_confidence: int = 1,
    limit: Optional[int] = None,
) -> int:
    """Derive single-char Hokkien readings from 2-char compound entries.

    For a 2-char compound like 注射 with pronunciation chù-siā,
    derives 注→chù and 射→siā. Uses frequency across compounds as confidence.

    Only inserts for chars that don't already have a Hokkien reading.
    Uses source='compound-derived'. Returns number of forms inserted.
    """
    from collections import Counter

    ensure_source(conn, "compound-derived")

    # Get all 2-char compounds with TYPE 1 (same chars) Hokkien pronunciations
    rows = conn.execute("""
        SELECT h.traditional, d.pronunciation
        FROM dialect_forms d JOIN headwords h ON h.id = d.headword_id
        WHERE d.dialect = 'nan' AND length(h.traditional) = 2
        AND d.native_chars IS NULL
        AND d.pronunciation NOT LIKE '%/%'
        AND d.pronunciation LIKE '%-%'
    """).fetchall()

    # Collect char→reading frequencies
    char_reading_freq: dict[str, Counter] = {}
    for trad, pron in rows:
        parts = pron.split("-")
        if len(parts) != 2:
            continue
        for i, ch in enumerate(trad):
            if ord(ch) >= 0x4E00:
                char_reading_freq.setdefault(ch, Counter())[parts[i]] += 1

    # Filter to chars missing Hokkien
    existing = set(r[0] for r in conn.execute("""
        SELECT DISTINCT h.traditional FROM headwords h
        JOIN dialect_forms d ON d.headword_id = h.id
        WHERE length(h.traditional) = 1 AND d.dialect = 'nan'
    """))

    # Build char→headword_id lookup
    hw_by_char: dict[str, list[int]] = {}
    for row in conn.execute(
        "SELECT id, traditional, simplified FROM headwords WHERE length(traditional) = 1"
    ):
        for text in (row["traditional"], row["simplified"]):
            if text:
                hw_by_char.setdefault(text, []).append(row["id"])
    for k in hw_by_char:
        hw_by_char[k] = list(set(hw_by_char[k]))

    count = 0
    for ch, freq in sorted(char_reading_freq.items(),
                           key=lambda x: -x[1].most_common(1)[0][1]):
        if ch in existing:
            continue

        best_reading, best_count = freq.most_common(1)[0]
        if best_count < min_confidence:
            continue

        hw_ids = hw_by_char.get(ch, [])
        if not hw_ids:
            continue

        for hw_id in hw_ids:
            upsert_dialect_form(
                conn, hw_id, "nan", best_reading, "compound-derived",
            )
            count += 1

        if limit and count >= limit:
            break

    conn.commit()
    return count


def _build_single_char_lookup(conn: sqlite3.Connection) -> dict[str, list[int]]:
    """Build a char→[headword_id] lookup for single-char headwords."""
    hw_by_char: dict[str, list[int]] = {}
    for row in conn.execute(
        "SELECT id, traditional, simplified FROM headwords WHERE length(traditional) = 1"
    ):
        for text in (row["traditional"], row["simplified"]):
            if text:
                hw_by_char.setdefault(text, []).append(row["id"])
    for k in hw_by_char:
        hw_by_char[k] = list(set(hw_by_char[k]))
    return hw_by_char


def _build_headword_lookup(conn: sqlite3.Connection) -> dict[str, list[int]]:
    """Build a text→[headword_id] lookup from both traditional and simplified."""
    hw_by_text: dict[str, list[int]] = {}
    for row in conn.execute("SELECT id, traditional, simplified FROM headwords"):
        for text in (row["traditional"], row["simplified"]):
            hw_by_text.setdefault(text, []).append(row["id"])
    # Deduplicate (same id may appear twice if trad == simp)
    for k in hw_by_text:
        hw_by_text[k] = list(set(hw_by_text[k]))
    return hw_by_text


# ---------------------------------------------------------------------------
# rime-cantonese: YAML char→jyutping mapping (CanCLID community project)
# Format after "..." marker: CHAR\tJYUTPING[\tWEIGHT]
# ---------------------------------------------------------------------------


def import_rime_cantonese(
    conn: sqlite3.Connection,
    file_path: Path,
    limit: Optional[int] = None,
) -> int:
    """Import rime-cantonese single-char Jyutping readings into dialect_forms.

    Only imports entries matching existing single-char headwords.
    Uses source='rime-cantonese' — won't touch existing cccanto/cccedict-readings rows.
    Returns number of dialect forms inserted.
    """
    ensure_source(conn, "rime-cantonese")

    # Build char→headword_id lookup (single chars only)
    hw_by_char: dict[str, list[int]] = {}
    for row in conn.execute(
        "SELECT id, traditional, simplified FROM headwords WHERE length(traditional) = 1"
    ):
        for text in (row["traditional"], row["simplified"]):
            if text:
                hw_by_char.setdefault(text, []).append(row["id"])
    for k in hw_by_char:
        hw_by_char[k] = list(set(hw_by_char[k]))

    count = 0
    matched_chars = set()
    in_data = False

    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line == "...":
                in_data = True
                continue
            if not in_data or not line:
                continue

            parts = line.split("\t")
            if len(parts) < 2:
                continue

            char = parts[0]
            jyutping = parts[1]

            if len(char) != 1:
                continue

            hw_ids = hw_by_char.get(char, [])
            if not hw_ids:
                continue

            # Only take first reading per char (highest weight in rime files)
            if char in matched_chars:
                continue
            matched_chars.add(char)

            for hw_id in hw_ids:
                upsert_dialect_form(
                    conn, hw_id, "yue", jyutping, "rime-cantonese",
                )
                count += 1

            if limit and count >= limit:
                break

    conn.commit()
    return count


# ---------------------------------------------------------------------------
# Unihan kCantonese: Unicode Consortium character readings
# Format: U+XXXX\tkCantonese\tREADING1 READING2
# ---------------------------------------------------------------------------


def import_unihan_cantonese(
    conn: sqlite3.Connection,
    file_path: Path,
    limit: Optional[int] = None,
) -> int:
    """Import Unihan kCantonese readings into dialect_forms.

    Only imports entries matching existing single-char headwords.
    Uses source='unihan' — won't touch existing rows from other sources.
    Returns number of dialect forms inserted.
    """
    import subprocess

    ensure_source(conn, "unihan")

    # Build char→headword_id lookup (single chars only)
    hw_by_char: dict[str, list[int]] = {}
    for row in conn.execute(
        "SELECT id, traditional, simplified FROM headwords WHERE length(traditional) = 1"
    ):
        for text in (row["traditional"], row["simplified"]):
            if text:
                hw_by_char.setdefault(text, []).append(row["id"])
    for k in hw_by_char:
        hw_by_char[k] = list(set(hw_by_char[k]))

    # Extract Unihan_Readings.txt from zip
    result = subprocess.run(
        ["unzip", "-p", str(file_path), "Unihan_Readings.txt"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to extract Unihan_Readings.txt from {file_path}")

    count = 0
    for line in result.stdout.split("\n"):
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 3 or parts[1] != "kCantonese":
            continue

        codepoint = int(parts[0][2:], 16)
        char = chr(codepoint)
        # Take first reading (most common)
        jyutping = parts[2].strip().split(" ")[0]

        hw_ids = hw_by_char.get(char, [])
        if not hw_ids:
            continue

        for hw_id in hw_ids:
            upsert_dialect_form(
                conn, hw_id, "yue", jyutping, "unihan",
            )
            count += 1

        if limit and count >= limit:
            break

    conn.commit()
    return count


def import_rime_cantonese_words(
    conn: sqlite3.Connection,
    file_path: Path,
    limit: Optional[int] = None,
) -> int:
    """Import rime-cantonese multi-char word Jyutping into dialect_forms.

    Imports entries matching existing multi-char headwords.
    Uses source='rime-cantonese' (same source as single-char import).
    Returns number of dialect forms inserted.
    """
    ensure_source(conn, "rime-cantonese")
    hw_by_text = _build_headword_lookup(conn)

    count = 0
    in_data = False

    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line == "...":
                in_data = True
                continue
            if not in_data or not line:
                continue

            parts = line.split("\t")
            if len(parts) < 2:
                continue

            word = parts[0]
            jyutping = parts[1]

            if len(word) < 2:
                continue

            hw_ids = hw_by_text.get(word, [])
            if not hw_ids:
                continue

            for hw_id in hw_ids:
                upsert_dialect_form(
                    conn, hw_id, "yue", jyutping, "rime-cantonese",
                )
                count += 1

            if limit and count >= limit:
                break

    conn.commit()
    return count


def import_wikihan(
    conn: sqlite3.Connection,
    file_path: Path,
    limit: Optional[int] = None,
) -> int:
    """Import WikiHan Hokkien and Cantonese readings into dialect_forms.

    Reads wikihan-romanization.tsv. Handles multi-reading chars (slash-separated).
    Only imports single-char entries matching existing headwords.
    Returns number of dialect forms inserted.
    """
    ensure_source(conn, "wikihan")
    hw_by_char = _build_single_char_lookup(conn)

    count = 0
    with open(file_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if limit and count >= limit:
                break

            char = row.get("Character", "").strip()
            if not char or len(char) != 1:
                continue

            hw_ids = hw_by_char.get(char, [])
            if not hw_ids:
                continue

            hokkien = row.get("Hokkien", "").strip()
            if hokkien and hokkien != "-":
                first_reading = hokkien.split("/")[0].strip()
                if first_reading:
                    for hw_id in hw_ids:
                        upsert_dialect_form(
                            conn, hw_id, "nan", first_reading, "wikihan",
                        )
                        count += 1

            cantonese = row.get("Cantonese", "").strip()
            if cantonese and cantonese != "-":
                first_reading = cantonese.split("/")[0].strip()
                if first_reading:
                    for hw_id in hw_ids:
                        upsert_dialect_form(
                            conn, hw_id, "yue", first_reading, "wikihan",
                        )
                        count += 1

    conn.commit()
    return count


def import_hou2004(
    conn: sqlite3.Connection,
    file_path: Path,
    doculects: Optional[list[str]] = None,
    limit: Optional[int] = None,
) -> int:
    """Import Hou2004 dialect readings into dialect_forms.

    Reads words.tsv for specified doculects (default: Xiamen, Shantou, Guangzhou).
    Extracts single-char readings from IPA VALUE column.
    Returns number of dialect forms inserted.
    """
    if doculects is None:
        doculects = ["Xiamen", "Shantou", "Guangzhou"]

    dialect_map = {
        "Xiamen": "nan",
        "Shantou": "nan",
        "Fuzhou": "nan",
        "Guangzhou": "yue",
        "Xianggang": "yue",
    }

    hw_by_char = _build_single_char_lookup(conn)
    count = 0

    for doc in doculects:
        dialect = dialect_map.get(doc)
        if not dialect:
            continue

        source_name = f"hou2004-{doc.lower()}"
        ensure_source(conn, source_name)

        with open(file_path, encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                if limit and count >= limit:
                    break

                if row.get("DOCULECT", "") != doc:
                    continue

                value = row.get("VALUE", "").strip()
                chars = row.get("CHARACTERS", "").strip()
                if not value or not chars:
                    continue

                if len(chars) == 1 and 0x4E00 <= ord(chars) <= 0x9FFF:
                    hw_ids = hw_by_char.get(chars, [])
                    for hw_id in hw_ids:
                        upsert_dialect_form(
                            conn, hw_id, dialect, value, source_name,
                        )
                        count += 1

    conn.commit()
    return count


def import_taibun(
    conn: sqlite3.Connection,
    data_dir: Path,
    limit: Optional[int] = None,
) -> int:
    """Import taibun Hokkien readings into dialect_forms.

    Reads words.msgpack (char/word→Tai-lo) and prons.msgpack (multi-reading).
    Matches against existing headwords. Source: 'taibun'. License: MIT.
    Returns number of dialect forms inserted.
    """
    import msgpack

    ensure_source(conn, "taibun")
    hw_lookup = _build_headword_lookup(conn)

    count = 0

    # Import words.msgpack (main dictionary)
    words_path = data_dir / "taibun" / "data" / "words.msgpack"
    with open(words_path, "rb") as f:
        words = msgpack.unpackb(f.read(), raw=False)

    for word, pronunciation in words.items():
        if limit and count >= limit:
            break
        if not word or not pronunciation:
            continue
        hw_ids = hw_lookup.get(word, [])
        if not hw_ids:
            continue
        # Take first reading if slash-separated
        pron = pronunciation.split("/")[0].strip()
        if not pron:
            continue
        for hw_id in hw_ids:
            upsert_dialect_form(conn, hw_id, "nan", pron, "taibun")
            count += 1

    conn.commit()
    return count


def import_wiktextract_hokkien(
    conn: sqlite3.Connection,
    file_path: Path,
    limit: Optional[int] = None,
) -> int:
    """Import Hokkien readings from Wiktextract Chinese JSONL.

    Filters entries with Min-Nan/Hokkien sound tags.
    Prefers zh_pron (romanization) over IPA.
    Source: 'wiktextract'. License: CC BY-SA 3.0.
    Returns number of dialect forms inserted.
    """
    import json

    ensure_source(conn, "wiktextract")
    hw_lookup = _build_headword_lookup(conn)

    count = 0
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            if limit and count >= limit:
                break
            obj = json.loads(line)
            word = obj.get("word", "").strip()
            if not word:
                continue
            hw_ids = hw_lookup.get(word, [])
            if not hw_ids:
                continue

            # Find first Hokkien pronunciation
            pron = None
            for s in obj.get("sounds", []):
                tags = s.get("tags", [])
                tag_str = " ".join(str(t) for t in tags).lower()
                if "min-nan" not in tag_str and "hokkien" not in tag_str:
                    continue
                pron = s.get("zh_pron", "") or s.get("ipa", "")
                if pron:
                    break

            if not pron:
                continue

            for hw_id in hw_ids:
                upsert_dialect_form(conn, hw_id, "nan", pron, "wiktextract")
                count += 1

    conn.commit()
    return count
