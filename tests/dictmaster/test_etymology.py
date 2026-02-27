"""Tests for cross-dialect etymology lookup."""

import pytest

from tools.dictmaster.schema import (
    get_connection,
    init_db,
    upsert_definition,
    upsert_dialect_form,
    upsert_headword,
)
from tools.dictmaster.etymology import (
    lookup_etymology,
    format_etymology,
)


@pytest.fixture
def db():
    """In-memory DB with sample cross-dialect data."""
    conn = get_connection()
    init_db(conn)

    # 豆腐 — the canonical example
    hw_id = upsert_headword(conn, "豆腐", "豆腐", "dou4 fu5", pos="noun")
    upsert_definition(conn, hw_id, "en", "tofu/bean curd", "cedict")
    upsert_definition(conn, hw_id, "id", "tahu", "cidict")
    upsert_definition(conn, hw_id, "vi", "đậu phụ", "minimax")
    upsert_definition(conn, hw_id, "tl", "tokwa/taho", "minimax")
    upsert_definition(conn, hw_id, "ja", "とうふ", "jmdict")
    upsert_definition(conn, hw_id, "de", "Tofu", "handedict")
    upsert_dialect_form(conn, hw_id, "yue", "dau6 fu6", "cccedict-readings")
    upsert_dialect_form(conn, hw_id, "nan", "tāu-hū", "taihua")

    # 媽媽 — lexical divergence in Hokkien
    hw_id2 = upsert_headword(conn, "媽媽", "妈妈", "ma1 ma5", pos="noun")
    upsert_definition(conn, hw_id2, "en", "mama/mommy/mother", "cedict")
    upsert_definition(conn, hw_id2, "tl", "ina/nanay", "minimax")
    upsert_definition(conn, hw_id2, "vi", "mẹ/má", "minimax")
    upsert_dialect_form(conn, hw_id2, "yue", "maa1 maa1", "cccedict-readings")
    upsert_dialect_form(conn, hw_id2, "nan", "niû-né", "taihua",
                        native_chars="娘né")

    # 你好 — pronunciation only (no lexical divergence)
    hw_id3 = upsert_headword(conn, "你好", "你好", "ni3 hao3")
    upsert_definition(conn, hw_id3, "en", "hello/hi", "cedict")
    upsert_definition(conn, hw_id3, "id", "halo", "cidict")
    upsert_dialect_form(conn, hw_id3, "yue", "nei5 hou2", "cccedict-readings")
    upsert_dialect_form(conn, hw_id3, "nan", "lí hó", "itaigi")

    conn.commit()
    yield conn
    conn.close()


class TestLookupEtymology:
    """Test the etymology lookup function."""

    def test_lookup_by_traditional(self, db):
        results = lookup_etymology(db, "豆腐")
        assert len(results) >= 1
        entry = results[0]
        assert entry["traditional"] == "豆腐"
        assert entry["pinyin"] == "dou4 fu5"

    def test_lookup_by_simplified(self, db):
        results = lookup_etymology(db, "妈妈")
        assert len(results) >= 1
        assert results[0]["traditional"] == "媽媽"

    def test_lookup_not_found(self, db):
        results = lookup_etymology(db, "不存在的词")
        assert results == []

    def test_entry_has_definitions(self, db):
        results = lookup_etymology(db, "豆腐")
        entry = results[0]
        assert "en" in entry["definitions"]
        assert entry["definitions"]["en"]["text"] == "tofu/bean curd"

    def test_entry_has_dialect_forms(self, db):
        results = lookup_etymology(db, "豆腐")
        entry = results[0]
        assert "yue" in entry["dialects"]
        assert entry["dialects"]["yue"]["pronunciation"] == "dau6 fu6"
        assert "nan" in entry["dialects"]
        assert entry["dialects"]["nan"]["pronunciation"] == "tāu-hū"

    def test_dialect_with_native_chars(self, db):
        results = lookup_etymology(db, "媽媽")
        entry = results[0]
        assert entry["dialects"]["nan"]["native_chars"] == "娘né"

    def test_dialect_without_native_chars(self, db):
        results = lookup_etymology(db, "你好")
        entry = results[0]
        assert entry["dialects"]["yue"]["native_chars"] is None

    def test_se_asian_languages_grouped(self, db):
        results = lookup_etymology(db, "豆腐")
        entry = results[0]
        # Should have SE Asian languages in definitions
        assert "id" in entry["definitions"]
        assert "vi" in entry["definitions"]
        assert "tl" in entry["definitions"]


class TestFormatEtymology:
    """Test the human-readable etymology formatting."""

    def test_format_basic(self, db):
        results = lookup_etymology(db, "豆腐")
        output = format_etymology(results[0])
        assert "豆腐" in output
        assert "dou4 fu5" in output
        assert "tofu" in output

    def test_format_includes_dialects(self, db):
        results = lookup_etymology(db, "豆腐")
        output = format_etymology(results[0])
        assert "dau6 fu6" in output  # Cantonese
        assert "tāu-hū" in output   # Hokkien

    def test_format_includes_se_asian(self, db):
        results = lookup_etymology(db, "豆腐")
        output = format_etymology(results[0])
        assert "tahu" in output      # Indonesian
        assert "taho" in output      # Tagalog

    def test_format_lexical_divergence(self, db):
        results = lookup_etymology(db, "媽媽")
        output = format_etymology(results[0])
        assert "娘né" in output      # Hokkien native chars

    def test_format_empty_results(self, db):
        # Create a minimal entry with no dialects
        hw_id = upsert_headword(db, "測試", "测试", "ce4 shi4")
        upsert_definition(db, hw_id, "en", "test", "cedict")
        db.commit()
        results = lookup_etymology(db, "測試")
        output = format_etymology(results[0])
        assert "測試" in output
        assert "test" in output
