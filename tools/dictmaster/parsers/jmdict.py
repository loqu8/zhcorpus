"""Parse JMdict XML for Japanese definitions of CJK words.

JMdict entries with kanji elements (keb) that contain only CJK characters
are matched to Chinese headwords. The Japanese reading (reb) and English
glosses are extracted and imported as Japanese definitions.

Handles gzip-compressed XML files.
"""

import gzip
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterator, NamedTuple, Optional

from tools.dictmaster.schema import ensure_source, upsert_definition, upsert_headword


class JmdictEntry(NamedTuple):
    """A parsed JMdict entry relevant to Chinese."""

    kanji: str  # CJK kanji (used as both traditional and simplified)
    reading: str  # Japanese reading in kana
    pos: str  # Part of speech (first one found)
    glosses_en: list[str]  # English glosses
    glosses_ja: str  # Japanese reading as the "definition" for ja


# JMdict ISO 639-2 (3-letter) -> our ISO 639-1 codes
JMDICT_LANG_MAP = {
    "eng": "en",
    "ger": "de",
    "fre": "fr",
    "spa": "es",
    "rus": "ru",
    "swe": "sv",
    "kor": "ko",
    "ind": "id",
    "vie": "vi",
    "dut": "nl",  # Dutch — not a target lang but present in data
}

def _is_pure_cjk(text: str) -> bool:
    """Check if text contains only CJK Unified Ideographs."""
    return bool(text) and all("\u4e00" <= c <= "\u9fff" for c in text)


def _map_pos(pos_text: str) -> Optional[str]:
    """Map JMdict POS description text to our POS tags."""
    t = pos_text.lower()
    if "verb" in t:
        return "verb"
    if "noun" in t:
        return "noun"
    if "adjective" in t or "adj" in t.split():
        return "adj"
    if "adverb" in t:
        return "adv"
    if "conjunction" in t:
        return "conj"
    if "interjection" in t:
        return "intj"
    if "particle" in t:
        return "particle"
    if "pronoun" in t:
        return "pronoun"
    if "counter" in t:
        return "classifier"
    if "suffix" in t:
        return "suffix"
    if "prefix" in t:
        return "prefix"
    if "expression" in t:
        return "phrase"
    return None


def _resolve_entities(gz_path: Path) -> str:
    """Read JMdict XML, replacing entity references with their values.

    JMdict uses XML entities like &n; &adj-na; for POS tags. We need to
    either resolve them or strip them. We resolve by reading the DTD
    declarations from the file header.
    """
    opener = gzip.open if gz_path.suffix == ".gz" else open
    entities = {}
    lines = []
    in_dtd = False

    with opener(gz_path, "rt", encoding="utf-8") as f:
        for line in f:
            if "<!DOCTYPE" in line:
                in_dtd = True
            if in_dtd:
                # Parse entity declarations: <!ENTITY n "noun (common)">
                import re

                m = re.match(r'<!ENTITY\s+(\S+)\s+"([^"]*)"', line.strip())
                if m:
                    entities[m.group(1)] = m.group(2)
                if "]>" in line:
                    in_dtd = False
                    lines.append(line[line.index("]>") + 2 :])
                    continue
                if not in_dtd:
                    lines.append(line)
                continue
            lines.append(line)

    xml_text = "".join(lines)
    # Replace entity references with their values
    for name, value in entities.items():
        xml_text = xml_text.replace(f"&{name};", value)

    return xml_text


def iter_jmdict(path: Path) -> Iterator[JmdictEntry]:
    """Iterate over JMdict entries that have pure-CJK kanji elements.

    Args:
        path: Path to JMdict XML file (plain or .gz)

    Yields:
        JmdictEntry for each entry with pure-CJK kanji
    """
    xml_text = _resolve_entities(path)
    root = ET.fromstring(xml_text)

    for entry in root.findall("entry"):
        # Get kanji elements
        k_eles = entry.findall("k_ele")
        if not k_eles:
            continue

        # Find pure-CJK kanji
        cjk_kanji = []
        for k_ele in k_eles:
            keb = k_ele.findtext("keb", "")
            if _is_pure_cjk(keb):
                cjk_kanji.append(keb)

        if not cjk_kanji:
            continue

        # Get first reading
        reb = entry.findtext(".//reb", "")
        if not reb:
            continue

        # Get POS and English glosses from sense elements
        pos = None
        glosses_en = []
        for sense in entry.findall("sense"):
            # POS from first sense that has it
            if pos is None:
                for pos_elem in sense.findall("pos"):
                    mapped = _map_pos(pos_elem.text or "")
                    if mapped:
                        pos = mapped
                        break

            # English glosses (no xml:lang attribute = English)
            for gloss in sense.findall("gloss"):
                lang = gloss.get("{http://www.w3.org/XML/1998/namespace}lang")
                if lang is None:  # Default is English
                    glosses_en.append(gloss.text or "")

        if not glosses_en:
            continue

        # Yield one entry per CJK kanji form
        for kanji in cjk_kanji:
            yield JmdictEntry(
                kanji=kanji,
                reading=reb,
                pos=pos or "",
                glosses_en=glosses_en,
                glosses_ja=reb,  # The kana reading IS the Japanese definition
            )


def import_jmdict(
    conn: sqlite3.Connection,
    path: Path,
    *,
    batch_size: int = 5000,
    limit: Optional[int] = None,
) -> int:
    """Import JMdict entries into the master database.

    For each CJK kanji entry:
    - Creates/finds a headword using kanji as both traditional and simplified
    - The pinyin field stores the Japanese reading (kana) since we don't
      have Chinese pinyin from JMdict
    - Imports the kana reading as the Japanese (ja) definition
    - Does NOT import English glosses (we have better English from CC-CEDICT)

    Args:
        conn: Database connection
        path: Path to JMdict XML file
        batch_size: Commit every N entries
        limit: Max entries to import

    Returns:
        Number of entries imported
    """
    ensure_source(conn, "jmdict")
    count = 0

    for entry in iter_jmdict(path):
        if limit and count >= limit:
            break

        # Use kanji as both trad/simp, reading as pinyin placeholder
        # This will match existing headwords if they share the same kanji
        # We look for existing headwords first
        existing = conn.execute(
            "SELECT id FROM headwords WHERE traditional = ? OR simplified = ?",
            (entry.kanji, entry.kanji),
        ).fetchone()

        if existing:
            hw_id = existing["id"]
        else:
            # Create new headword with kana as pinyin placeholder
            hw_id = upsert_headword(
                conn, entry.kanji, entry.kanji, entry.reading, pos=entry.pos or None
            )

        # Import Japanese definition (the kana reading + glosses for context)
        ja_def = entry.reading
        upsert_definition(conn, hw_id, "ja", ja_def, "jmdict")

        count += 1
        if count % batch_size == 0:
            conn.commit()

    conn.commit()
    return count
