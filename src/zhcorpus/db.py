"""Database schema and connection management for zhcorpus."""

import hashlib
import sqlite3
from pathlib import Path
from typing import Optional


SCHEMA_VERSION = 1

SCHEMA_SQL = """
-- Sources: where the text came from
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    import_date TEXT,
    article_count INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0
);

-- Articles: metadata for each imported document
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    source_article_id TEXT,
    title TEXT,
    char_count INTEGER,
    UNIQUE(source_id, source_article_id)
);

-- Chunks: sentence-level units — the embedding and search target
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY,
    article_id INTEGER NOT NULL REFERENCES articles(id),
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    char_count INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    UNIQUE(article_id, chunk_index)
);
CREATE INDEX IF NOT EXISTS idx_chunks_article ON chunks(article_id);
CREATE INDEX IF NOT EXISTS idx_chunks_hash ON chunks(content_hash);

-- FTS5 with trigram tokenizer — CJK-friendly substring matching
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text,
    content='chunks',
    content_rowid='id',
    tokenize='trigram'
);

-- fts5vocab: exposes the trigram index vocabulary for short-term expansion.
-- For 2-char Chinese words (e.g. 选任), we find all trigrams containing the
-- term and build an OR query, giving proper BM25 ranking without LIKE scans.
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts_vocab
    USING fts5vocab(chunks_fts, row);

-- Keep FTS5 in sync with chunks table
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
END;
CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
END;
CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
    INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
END;

-- CEDICT reference for cross-referencing
CREATE TABLE IF NOT EXISTS cedict (
    id INTEGER PRIMARY KEY,
    traditional TEXT NOT NULL,
    simplified TEXT NOT NULL,
    pinyin TEXT NOT NULL,
    definition TEXT NOT NULL,
    UNIQUE(traditional, simplified, pinyin, definition)
);
CREATE INDEX IF NOT EXISTS idx_cedict_simplified ON cedict(simplified);
CREATE INDEX IF NOT EXISTS idx_cedict_traditional ON cedict(traditional);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_info (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def content_hash(text: str) -> str:
    """SHA-256 hash of text content, for change detection."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Get a database connection. Uses :memory: if no path given."""
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


def ensure_source(conn: sqlite3.Connection, name: str, description: str = "") -> int:
    """Get or create a source, return its id."""
    row = conn.execute("SELECT id FROM sources WHERE name = ?", (name,)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO sources (name, description) VALUES (?, ?)",
        (name, description),
    )
    conn.commit()
    return cur.lastrowid


def insert_article(
    conn: sqlite3.Connection,
    source_id: int,
    source_article_id: str,
    title: str,
    char_count: int,
) -> int:
    """Insert an article, return its id. Skips duplicates."""
    cur = conn.execute(
        "INSERT OR IGNORE INTO articles (source_id, source_article_id, title, char_count) "
        "VALUES (?, ?, ?, ?)",
        (source_id, source_article_id, title, char_count),
    )
    if cur.lastrowid and cur.rowcount > 0:
        return cur.lastrowid
    row = conn.execute(
        "SELECT id FROM articles WHERE source_id = ? AND source_article_id = ?",
        (source_id, source_article_id),
    ).fetchone()
    return row["id"]


def insert_chunk(
    conn: sqlite3.Connection,
    article_id: int,
    chunk_index: int,
    text: str,
) -> int:
    """Insert a chunk, return its id."""
    h = content_hash(text)
    cur = conn.execute(
        "INSERT OR IGNORE INTO chunks (article_id, chunk_index, text, char_count, content_hash) "
        "VALUES (?, ?, ?, ?, ?)",
        (article_id, chunk_index, text, len(text), h),
    )
    if cur.lastrowid and cur.rowcount > 0:
        return cur.lastrowid
    row = conn.execute(
        "SELECT id FROM chunks WHERE article_id = ? AND chunk_index = ?",
        (article_id, chunk_index),
    ).fetchone()
    return row["id"]
