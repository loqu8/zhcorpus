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
