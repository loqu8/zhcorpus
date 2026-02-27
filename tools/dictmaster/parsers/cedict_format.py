"""Parse CEDICT-format dictionary files (CC-CEDICT, CFDICT, HanDeDict, CC-CIDICT).

All use the same line format:
    Traditional Simplified [pin1 yin1] /def1/def2/

Handles plain text and gzip-compressed files.
"""

import gzip
import sqlite3
from pathlib import Path
from typing import Iterator, NamedTuple, Optional

from tools.dictmaster.schema import ensure_source, upsert_definition, upsert_headword


class CedictEntry(NamedTuple):
    traditional: str
    simplified: str
    pinyin: str
    definition: str


def parse_cedict_line(line: str) -> Optional[CedictEntry]:
    """Parse a single CEDICT-format line.

    Returns CedictEntry or None for comments/blank/malformed lines.
    """
    line = line.strip()
    if not line or line.startswith("#") or line.startswith("%"):
        return None

    try:
        trad_simp, rest = line.split("[", 1)
        pinyin, definitions = rest.split("]", 1)

        parts = trad_simp.strip().split(" ", 1)
        traditional = parts[0]
        simplified = parts[1].strip() if len(parts) > 1 else traditional

        pinyin = pinyin.strip()

        definition = definitions.strip()
        if definition.startswith("/"):
            definition = definition[1:]
        if definition.endswith("/"):
            definition = definition[:-1]

        if not definition:
            return None

        return CedictEntry(traditional, simplified, pinyin, definition)
    except (ValueError, IndexError):
        return None


def _open_file(path: Path):
    """Open a file, handling .gz transparently."""
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, "r", encoding="utf-8")


def iter_cedict(path: Path) -> Iterator[CedictEntry]:
    """Iterate over CEDICT-format entries from a file (plain or gzipped)."""
    with _open_file(path) as f:
        for line in f:
            entry = parse_cedict_line(line)
            if entry:
                yield entry


def infer_pos(definition: str) -> Optional[str]:
    """Infer part of speech from CEDICT definition patterns."""
    if definition.startswith("to "):
        return "verb"
    if "CL:" in definition:
        return "noun"
    if definition.startswith("(") and definition.endswith(")"):
        return "phrase"
    return None


# Source name -> lang mapping for known CEDICT-family dictionaries
SOURCE_LANG_MAP = {
    "cedict": "en",
    "cfdict": "fr",
    "handedict": "de",
    "cidict": "id",
}


def import_cedict_file(
    conn: sqlite3.Connection,
    path: Path,
    source_name: str,
    lang: str,
    *,
    batch_size: int = 5000,
    limit: Optional[int] = None,
) -> int:
    """Import a CEDICT-format file into the master database.

    Args:
        conn: Database connection
        path: Path to dictionary file (plain text or .gz)
        source_name: Source identifier (cedict/cfdict/handedict/cidict)
        lang: ISO 639-1 language code for definitions (en/fr/de/id)
        batch_size: Commit every N entries
        limit: Max entries to import (None for all)

    Returns:
        Number of entries imported
    """
    ensure_source(conn, source_name)
    count = 0

    for entry in iter_cedict(path):
        if limit and count >= limit:
            break

        pos = infer_pos(entry.definition)
        hw_id = upsert_headword(conn, entry.traditional, entry.simplified, entry.pinyin, pos)
        upsert_definition(conn, hw_id, lang, entry.definition, source_name)
        count += 1

        if count % batch_size == 0:
            conn.commit()

    conn.commit()
    return count
