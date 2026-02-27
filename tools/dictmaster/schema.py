"""Database schema and connection management for dictmaster.

Master multilingual Chinese dictionary — SQLite relational DB (no FTS5).
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


SCHEMA_VERSION = 2

DEFAULT_DB_PATH = Path("data/artifacts/dictmaster.db")

SCHEMA_SQL = """
-- Headwords: unique (traditional, simplified, pinyin) triples
CREATE TABLE IF NOT EXISTS headwords (
    id INTEGER PRIMARY KEY,
    traditional TEXT NOT NULL,
    simplified TEXT NOT NULL,
    pinyin TEXT NOT NULL,
    pos TEXT,
    UNIQUE(traditional, simplified, pinyin)
);
CREATE INDEX IF NOT EXISTS idx_headwords_simplified ON headwords(simplified);
CREATE INDEX IF NOT EXISTS idx_headwords_traditional ON headwords(traditional);

-- Definitions: per-language definitions linked to headwords
CREATE TABLE IF NOT EXISTS definitions (
    id INTEGER PRIMARY KEY,
    headword_id INTEGER NOT NULL REFERENCES headwords(id),
    lang TEXT NOT NULL,
    definition TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence TEXT,
    verified INTEGER DEFAULT 0,
    UNIQUE(headword_id, lang, source)
);
CREATE INDEX IF NOT EXISTS idx_definitions_headword ON definitions(headword_id);
CREATE INDEX IF NOT EXISTS idx_definitions_lang ON definitions(lang);

-- Sources: metadata about each dictionary source
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    license TEXT,
    url TEXT,
    entry_count INTEGER,
    import_date TEXT
);

-- Dialect forms: Cantonese (yue) and Hokkien (nan) pronunciation + lexical data
CREATE TABLE IF NOT EXISTS dialect_forms (
    id INTEGER PRIMARY KEY,
    headword_id INTEGER NOT NULL REFERENCES headwords(id),
    dialect TEXT NOT NULL,           -- 'yue' or 'nan'
    native_chars TEXT,               -- dialect-specific characters (NULL if same as Mandarin)
    pronunciation TEXT NOT NULL,     -- Jyutping (yue) or POJ/Tai-lo (nan)
    gloss TEXT,                      -- English gloss for the dialect form
    source TEXT NOT NULL,
    UNIQUE(headword_id, dialect, source)
);
CREATE INDEX IF NOT EXISTS idx_dialect_forms_headword ON dialect_forms(headword_id);
CREATE INDEX IF NOT EXISTS idx_dialect_forms_dialect ON dialect_forms(dialect);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_info (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

# Known sources with metadata
KNOWN_SOURCES = {
    "cedict": {
        "description": "CC-CEDICT Chinese-English dictionary",
        "license": "CC BY-SA 4.0",
        "url": "https://cc-cedict.org/",
    },
    "cfdict": {
        "description": "CFDICT Chinese-French dictionary",
        "license": "CC BY-SA 3.0",
        "url": "https://chine.in/mandarin/dictionnaire/CFDICT/",
    },
    "handedict": {
        "description": "HanDeDict Chinese-German dictionary",
        "license": "CC BY-SA 2.0",
        "url": "https://handedict.zydeo.net/",
    },
    "cidict": {
        "description": "CC-CIDICT Chinese-Indonesian dictionary",
        "license": "CC BY-SA 4.0",
        "url": "https://cidict.org/",
    },
    "wiktextract": {
        "description": "Wiktionary Chinese entries via Kaikki.org",
        "license": "CC BY-SA 4.0",
        "url": "https://kaikki.org/dictionary/Chinese/",
    },
    "jmdict": {
        "description": "JMdict Japanese-Multilingual dictionary",
        "license": "CC BY-SA 4.0",
        "url": "https://www.edrdg.org/jmdict/j_jmdict.html",
    },
    "minimax": {
        "description": "AI-generated translations via MiniMax M2.5",
        "license": "Generated",
        "url": None,
    },
    "cccanto": {
        "description": "CC-Canto Cantonese dictionary (CEDICT format with Jyutping)",
        "license": "CC BY-SA 3.0",
        "url": "https://cantonese.org/download.html",
    },
    "cccedict-readings": {
        "description": "CC-CEDICT Cantonese readings (Jyutping pronunciation overlay)",
        "license": "CC BY-SA 3.0",
        "url": "https://cantonese.org/download.html",
    },
    "itaigi": {
        "description": "iTaigi crowdsourced Mandarin-Hokkien dictionary",
        "license": "CC0",
        "url": "https://github.com/ChhoeTaigi/ChhoeTaigiDatabase",
    },
    "taihua": {
        "description": "台華線頂對照典 Mandarin-Hokkien parallel dictionary",
        "license": "CC BY-SA 4.0",
        "url": "https://github.com/ChhoeTaigi/ChhoeTaigiDatabase",
    },
}


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Get a database connection. No FTS5 extension needed."""
    path = str(db_path) if db_path else ":memory:"
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create all tables and indexes."""
    conn.executescript(SCHEMA_SQL)
    conn.execute(
        "INSERT OR REPLACE INTO schema_info (key, value) VALUES ('version', ?)",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()


def ensure_source(conn: sqlite3.Connection, name: str) -> int:
    """Get or create a source from KNOWN_SOURCES, return its id."""
    row = conn.execute("SELECT id FROM sources WHERE name = ?", (name,)).fetchone()
    if row:
        return row["id"]

    meta = KNOWN_SOURCES.get(name, {})
    cur = conn.execute(
        "INSERT INTO sources (name, description, license, url, import_date) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            name,
            meta.get("description", ""),
            meta.get("license", ""),
            meta.get("url"),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    return cur.lastrowid


def upsert_headword(
    conn: sqlite3.Connection,
    traditional: str,
    simplified: str,
    pinyin: str,
    pos: Optional[str] = None,
) -> int:
    """Insert or get a headword, return its id. Updates POS if provided and currently null."""
    cur = conn.execute(
        "INSERT OR IGNORE INTO headwords (traditional, simplified, pinyin, pos) "
        "VALUES (?, ?, ?, ?)",
        (traditional, simplified, pinyin, pos),
    )
    if cur.lastrowid and cur.rowcount > 0:
        return cur.lastrowid

    row = conn.execute(
        "SELECT id, pos FROM headwords WHERE traditional = ? AND simplified = ? AND pinyin = ?",
        (traditional, simplified, pinyin),
    ).fetchone()

    # Update POS if we have one and the existing row doesn't
    if pos and not row["pos"]:
        conn.execute(
            "UPDATE headwords SET pos = ? WHERE id = ?",
            (pos, row["id"]),
        )

    return row["id"]


def upsert_definition(
    conn: sqlite3.Connection,
    headword_id: int,
    lang: str,
    definition: str,
    source: str,
    confidence: Optional[str] = None,
) -> int:
    """Insert or update a definition, return its id."""
    cur = conn.execute(
        "INSERT OR REPLACE INTO definitions (headword_id, lang, definition, source, confidence) "
        "VALUES (?, ?, ?, ?, ?)",
        (headword_id, lang, definition, source, confidence),
    )
    return cur.lastrowid


def upsert_dialect_form(
    conn: sqlite3.Connection,
    headword_id: int,
    dialect: str,
    pronunciation: str,
    source: str,
    native_chars: Optional[str] = None,
    gloss: Optional[str] = None,
) -> int:
    """Insert or update a dialect form, return its id."""
    cur = conn.execute(
        "INSERT OR REPLACE INTO dialect_forms "
        "(headword_id, dialect, native_chars, pronunciation, gloss, source) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (headword_id, dialect, native_chars, pronunciation, gloss, source),
    )
    return cur.lastrowid


def update_source_count(conn: sqlite3.Connection, source_name: str) -> None:
    """Update the entry_count for a source based on actual definition rows."""
    conn.execute(
        "UPDATE sources SET entry_count = "
        "(SELECT COUNT(*) FROM definitions WHERE source = ?) "
        "WHERE name = ?",
        (source_name, source_name),
    )
    conn.commit()


def get_stats(conn: sqlite3.Connection) -> dict:
    """Get summary statistics for the database."""
    headwords = conn.execute("SELECT COUNT(*) FROM headwords").fetchone()[0]
    definitions = conn.execute("SELECT COUNT(*) FROM definitions").fetchone()[0]
    langs = conn.execute("SELECT DISTINCT lang FROM definitions ORDER BY lang").fetchall()
    sources = conn.execute(
        "SELECT name, entry_count FROM sources ORDER BY name"
    ).fetchall()
    return {
        "headwords": headwords,
        "definitions": definitions,
        "languages": [r["lang"] for r in langs],
        "sources": {r["name"]: r["entry_count"] for r in sources},
    }
