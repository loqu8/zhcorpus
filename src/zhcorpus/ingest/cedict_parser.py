"""Parse CC-CEDICT dictionary file into the cedict table.

CC-CEDICT format (one entry per line):
    Traditional Simplified [pinyin] /definition1/definition2/.../

Lines starting with # are comments. The first few lines are metadata.
"""

import sqlite3
from pathlib import Path
from typing import Iterator, Tuple


def parse_cedict_line(line: str) -> Tuple[str, str, str, str] | None:
    """Parse a single CC-CEDICT line.

    Returns (traditional, simplified, pinyin, definition) or None for comments.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    # Format: Traditional Simplified [pinyin] /def1/def2/
    try:
        trad_simp, rest = line.split("[", 1)
        pinyin, definitions = rest.split("]", 1)

        parts = trad_simp.strip().split(" ", 1)
        traditional = parts[0]
        simplified = parts[1].strip() if len(parts) > 1 else traditional

        pinyin = pinyin.strip()

        # Strip leading/trailing slashes and join definitions
        definition = definitions.strip()
        if definition.startswith("/"):
            definition = definition[1:]
        if definition.endswith("/"):
            definition = definition[:-1]

        return traditional, simplified, pinyin, definition
    except (ValueError, IndexError):
        return None


def iter_cedict(path: Path) -> Iterator[Tuple[str, str, str, str]]:
    """Iterate over CC-CEDICT entries from a file."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            entry = parse_cedict_line(line)
            if entry:
                yield entry


def load_cedict(conn: sqlite3.Connection, path: Path) -> int:
    """Load CC-CEDICT entries into the cedict table.

    Returns the number of entries loaded.
    """
    count = 0
    batch = []
    for traditional, simplified, pinyin, definition in iter_cedict(path):
        batch.append((traditional, simplified, pinyin, definition))
        if len(batch) >= 5000:
            conn.executemany(
                "INSERT OR IGNORE INTO cedict (traditional, simplified, pinyin, definition) "
                "VALUES (?, ?, ?, ?)",
                batch,
            )
            count += len(batch)
            batch = []

    if batch:
        conn.executemany(
            "INSERT OR IGNORE INTO cedict (traditional, simplified, pinyin, definition) "
            "VALUES (?, ?, ?, ?)",
            batch,
        )
        count += len(batch)

    conn.commit()
    return count
