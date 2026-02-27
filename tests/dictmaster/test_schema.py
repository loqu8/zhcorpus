"""Tests for dictmaster schema and DB helpers."""

import pytest

from tools.dictmaster.schema import (
    ensure_source,
    get_connection,
    get_stats,
    init_db,
    update_source_count,
    upsert_definition,
    upsert_headword,
)


@pytest.fixture
def db():
    """In-memory database with schema initialized."""
    conn = get_connection()
    init_db(conn)
    yield conn
    conn.close()


class TestSchema:
    """Test database schema creation."""

    def test_tables_created(self, db):
        tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = [r["name"] for r in tables]
        assert "headwords" in names
        assert "definitions" in names
        assert "sources" in names
        assert "schema_info" in names

    def test_schema_version(self, db):
        row = db.execute(
            "SELECT value FROM schema_info WHERE key = 'version'"
        ).fetchone()
        assert row["value"] == "2"

    def test_foreign_keys_enabled(self, db):
        result = db.execute("PRAGMA foreign_keys").fetchone()
        assert result[0] == 1

    def test_wal_mode(self, tmp_path):
        """WAL mode is set for file-based databases."""
        conn = get_connection(tmp_path / "test.db")
        init_db(conn)
        result = conn.execute("PRAGMA journal_mode").fetchone()
        assert result[0] == "wal"
        conn.close()


class TestEnsureSource:
    """Test source management."""

    def test_creates_known_source(self, db):
        sid = ensure_source(db, "cedict")
        assert sid > 0
        row = db.execute("SELECT * FROM sources WHERE id = ?", (sid,)).fetchone()
        assert row["name"] == "cedict"
        assert "CC BY-SA 4.0" in row["license"]

    def test_idempotent(self, db):
        id1 = ensure_source(db, "cedict")
        id2 = ensure_source(db, "cedict")
        assert id1 == id2

    def test_unknown_source(self, db):
        sid = ensure_source(db, "custom_dict")
        assert sid > 0
        row = db.execute("SELECT * FROM sources WHERE id = ?", (sid,)).fetchone()
        assert row["name"] == "custom_dict"


class TestUpsertHeadword:
    """Test headword upsert."""

    def test_insert_headword(self, db):
        hw_id = upsert_headword(db, "中國", "中国", "zhong1 guo2")
        assert hw_id > 0
        row = db.execute("SELECT * FROM headwords WHERE id = ?", (hw_id,)).fetchone()
        assert row["traditional"] == "中國"
        assert row["simplified"] == "中国"
        assert row["pinyin"] == "zhong1 guo2"

    def test_idempotent_headword(self, db):
        id1 = upsert_headword(db, "中國", "中国", "zhong1 guo2")
        id2 = upsert_headword(db, "中國", "中国", "zhong1 guo2")
        assert id1 == id2

    def test_headword_with_pos(self, db):
        hw_id = upsert_headword(db, "走", "走", "zou3", pos="verb")
        row = db.execute("SELECT pos FROM headwords WHERE id = ?", (hw_id,)).fetchone()
        assert row["pos"] == "verb"

    def test_pos_filled_when_null(self, db):
        hw_id = upsert_headword(db, "走", "走", "zou3")
        row = db.execute("SELECT pos FROM headwords WHERE id = ?", (hw_id,)).fetchone()
        assert row["pos"] is None

        # Second insert with POS should update
        upsert_headword(db, "走", "走", "zou3", pos="verb")
        row = db.execute("SELECT pos FROM headwords WHERE id = ?", (hw_id,)).fetchone()
        assert row["pos"] == "verb"

    def test_pos_not_overwritten(self, db):
        upsert_headword(db, "走", "走", "zou3", pos="verb")
        upsert_headword(db, "走", "走", "zou3", pos="noun")
        row = db.execute("SELECT pos FROM headwords WHERE simplified = '走'").fetchone()
        assert row["pos"] == "verb"  # First POS wins

    def test_different_pinyin_creates_new(self, db):
        id1 = upsert_headword(db, "行", "行", "xing2")
        id2 = upsert_headword(db, "行", "行", "hang2")
        assert id1 != id2


class TestUpsertDefinition:
    """Test definition upsert."""

    def test_insert_definition(self, db):
        hw_id = upsert_headword(db, "你好", "你好", "ni3 hao3")
        def_id = upsert_definition(db, hw_id, "en", "hello/hi", "cedict")
        assert def_id > 0

    def test_unique_per_headword_lang_source(self, db):
        hw_id = upsert_headword(db, "你好", "你好", "ni3 hao3")
        upsert_definition(db, hw_id, "en", "hello", "cedict")
        upsert_definition(db, hw_id, "en", "hi/hello", "wiktextract")

        defs = db.execute(
            "SELECT * FROM definitions WHERE headword_id = ? AND lang = ?",
            (hw_id, "en"),
        ).fetchall()
        assert len(defs) == 2

    def test_replace_on_conflict(self, db):
        hw_id = upsert_headword(db, "你好", "你好", "ni3 hao3")
        upsert_definition(db, hw_id, "en", "hello", "cedict")
        upsert_definition(db, hw_id, "en", "hello/hi", "cedict")

        defs = db.execute(
            "SELECT definition FROM definitions WHERE headword_id = ? AND lang = 'en' AND source = 'cedict'",
            (hw_id,),
        ).fetchall()
        assert len(defs) == 1
        assert defs[0]["definition"] == "hello/hi"

    def test_confidence_field(self, db):
        hw_id = upsert_headword(db, "你好", "你好", "ni3 hao3")
        upsert_definition(db, hw_id, "es", "hola", "minimax", confidence="medium")
        row = db.execute(
            "SELECT confidence FROM definitions WHERE headword_id = ? AND lang = 'es'",
            (hw_id,),
        ).fetchone()
        assert row["confidence"] == "medium"


class TestGetStats:
    """Test statistics."""

    def test_empty_db(self, db):
        stats = get_stats(db)
        assert stats["headwords"] == 0
        assert stats["definitions"] == 0
        assert stats["languages"] == []

    def test_with_data(self, db):
        hw_id = upsert_headword(db, "你好", "你好", "ni3 hao3")
        upsert_definition(db, hw_id, "en", "hello", "cedict")
        upsert_definition(db, hw_id, "fr", "bonjour", "cfdict")
        db.commit()
        update_source_count(db, "cedict")
        update_source_count(db, "cfdict")

        stats = get_stats(db)
        assert stats["headwords"] == 1
        assert stats["definitions"] == 2
        assert set(stats["languages"]) == {"en", "fr"}
