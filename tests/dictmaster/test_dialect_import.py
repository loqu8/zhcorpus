"""Tests for Cantonese and Hokkien dialect data parsing and import."""

import pytest

from tools.dictmaster.schema import (
    get_connection,
    init_db,
    upsert_dialect_form,
    upsert_headword,
)
from tools.dictmaster.parsers.dialect import (
    parse_cccanto_line,
    parse_cccedict_readings_line,
    parse_itaigi_row,
    parse_taihua_row,
)


@pytest.fixture
def db():
    """In-memory database with schema initialized."""
    conn = get_connection()
    init_db(conn)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Schema: dialect_forms table
# ---------------------------------------------------------------------------


class TestDialectFormsTable:
    """Test the dialect_forms table exists and works."""

    def test_table_exists(self, db):
        tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = [r["name"] for r in tables]
        assert "dialect_forms" in names

    def test_insert_cantonese_pronunciation(self, db):
        hw_id = upsert_headword(db, "銀行", "银行", "yin2 hang2")
        df_id = upsert_dialect_form(
            db, hw_id, "yue", "ngan4 hong4", "cccedict-readings",
        )
        assert df_id > 0
        row = db.execute(
            "SELECT * FROM dialect_forms WHERE id = ?", (df_id,)
        ).fetchone()
        assert row["dialect"] == "yue"
        assert row["pronunciation"] == "ngan4 hong4"
        assert row["native_chars"] is None
        assert row["source"] == "cccedict-readings"

    def test_insert_cantonese_lexical(self, db):
        hw_id = upsert_headword(db, "東西", "东西", "dong1 xi1")
        df_id = upsert_dialect_form(
            db, hw_id, "yue", "je5", "cccanto",
            native_chars="嘢", gloss="thing/stuff",
        )
        assert df_id > 0
        row = db.execute(
            "SELECT * FROM dialect_forms WHERE id = ?", (df_id,)
        ).fetchone()
        assert row["native_chars"] == "嘢"
        assert row["gloss"] == "thing/stuff"

    def test_insert_hokkien(self, db):
        hw_id = upsert_headword(db, "討厭", "讨厌", "tao3 yan4")
        df_id = upsert_dialect_form(
            db, hw_id, "nan", "siān-neh", "itaigi",
            native_chars="𤺪呢",
        )
        assert df_id > 0
        row = db.execute(
            "SELECT * FROM dialect_forms WHERE id = ?", (df_id,)
        ).fetchone()
        assert row["dialect"] == "nan"
        assert row["native_chars"] == "𤺪呢"

    def test_unique_constraint(self, db):
        hw_id = upsert_headword(db, "銀行", "银行", "yin2 hang2")
        upsert_dialect_form(db, hw_id, "yue", "ngan4 hong4", "cccedict-readings")
        # Same headword+dialect+source should replace
        upsert_dialect_form(db, hw_id, "yue", "ngan4 hong4-2", "cccedict-readings")
        rows = db.execute(
            "SELECT * FROM dialect_forms WHERE headword_id = ? AND dialect = 'yue'",
            (hw_id,),
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["pronunciation"] == "ngan4 hong4-2"

    def test_multiple_sources_same_dialect(self, db):
        hw_id = upsert_headword(db, "銀行", "银行", "yin2 hang2")
        upsert_dialect_form(db, hw_id, "yue", "ngan4 hong4", "cccedict-readings")
        upsert_dialect_form(db, hw_id, "yue", "ngan4 hong4", "cccanto",
                           gloss="bank")
        rows = db.execute(
            "SELECT * FROM dialect_forms WHERE headword_id = ? AND dialect = 'yue'",
            (hw_id,),
        ).fetchall()
        assert len(rows) == 2


# ---------------------------------------------------------------------------
# CC-Canto parser
# ---------------------------------------------------------------------------


class TestParseCCCanto:
    """Test CC-Canto CEDICT+Jyutping line parsing."""

    def test_basic_entry(self):
        line = "一件頭 一件头 [yi1 jian4 tou2] {jat1 gin6 tau4} /one-piece (swimwear)/"
        result = parse_cccanto_line(line)
        assert result["traditional"] == "一件頭"
        assert result["simplified"] == "一件头"
        assert result["pinyin"] == "yi1 jian4 tou2"
        assert result["jyutping"] == "jat1 gin6 tau4"
        assert result["definitions"] == ["one-piece (swimwear)"]

    def test_multiple_definitions(self):
        line = "一二 一二 [yi1 er4] {jat1 ji6} /one or two, a little, a few, one by one/"
        result = parse_cccanto_line(line)
        assert result["jyutping"] == "jat1 ji6"
        assert len(result["definitions"]) == 1
        assert "one or two" in result["definitions"][0]

    def test_cantonese_specific_chars(self):
        line = "一唔係 一唔系 [yi1 n2 xi4] {jat1 m4 hai6} /else/"
        result = parse_cccanto_line(line)
        assert result["traditional"] == "一唔係"
        assert result["jyutping"] == "jat1 m4 hai6"
        assert result["definitions"] == ["else"]

    def test_comment_line(self):
        assert parse_cccanto_line("# This is a comment") is None

    def test_empty_line(self):
        assert parse_cccanto_line("") is None
        assert parse_cccanto_line("   ") is None

    def test_no_jyutping(self):
        """Lines without {jyutping} should return None."""
        line = "一 一 [yi1] /one/"
        assert parse_cccanto_line(line) is None

    def test_multi_slash_definitions(self):
        line = (
            "一仆一碌 一仆一碌 [yi1 pu2 yi1 lu4] {jat1 puk1 jat1 luk1} "
            "/stumbling to the ground/running away in a hurry/"
        )
        result = parse_cccanto_line(line)
        assert len(result["definitions"]) == 2


# ---------------------------------------------------------------------------
# CC-CEDICT Cantonese Readings parser
# ---------------------------------------------------------------------------


class TestParseCCCEDICTReadings:
    """Test CC-CEDICT Cantonese readings (pronunciation-only) parsing."""

    def test_basic_reading(self):
        line = "伊莉莎白 伊莉莎白 [Yi1 li4 sha1 bai2] {ji1 lei6 saa1 baak6}"
        result = parse_cccedict_readings_line(line)
        assert result["traditional"] == "伊莉莎白"
        assert result["simplified"] == "伊莉莎白"
        assert result["pinyin"] == "Yi1 li4 sha1 bai2"
        assert result["jyutping"] == "ji1 lei6 saa1 baak6"

    def test_trad_simp_differ(self):
        line = "發佈 发布 [fa1 bu4] {faat3 bou3}"
        result = parse_cccedict_readings_line(line)
        assert result["traditional"] == "發佈"
        assert result["simplified"] == "发布"
        assert result["jyutping"] == "faat3 bou3"

    def test_comment_line(self):
        assert parse_cccedict_readings_line("# CC-CEDICT header") is None

    def test_empty_line(self):
        assert parse_cccedict_readings_line("") is None


# ---------------------------------------------------------------------------
# iTaigi parser
# ---------------------------------------------------------------------------


class TestParseITaigi:
    """Test iTaigi CSV row parsing."""

    def test_basic_row(self):
        row = {
            "HoaBun": "討厭",
            "HanLoTaibunPoj": "𤺪呢",
            "PojUnicode": "siān-neh",
            "KipUnicode": "siān-neh",
        }
        result = parse_itaigi_row(row)
        assert result["mandarin"] == "討厭"
        assert result["native_chars"] == "𤺪呢"
        assert result["pronunciation"] == "siān-neh"

    def test_same_chars(self):
        """When Hokkien chars match Mandarin, native_chars should be None."""
        row = {
            "HoaBun": "保鮮膜",
            "HanLoTaibunPoj": "保鮮膜",
            "PojUnicode": "pó-chhiⁿ-mo̍͘h",
            "KipUnicode": "pó-tshinn-mo̍oh",
        }
        result = parse_itaigi_row(row)
        assert result["native_chars"] is None
        assert result["pronunciation"] == "pó-chhiⁿ-mo̍͘h"

    def test_empty_mandarin(self):
        row = {
            "HoaBun": "",
            "HanLoTaibunPoj": "test",
            "PojUnicode": "test",
            "KipUnicode": "test",
        }
        assert parse_itaigi_row(row) is None

    def test_empty_pronunciation(self):
        row = {
            "HoaBun": "測試",
            "HanLoTaibunPoj": "test",
            "PojUnicode": "",
            "KipUnicode": "",
        }
        assert parse_itaigi_row(row) is None

    def test_kip_fallback(self):
        """If PojUnicode is empty, fall back to KipUnicode."""
        row = {
            "HoaBun": "測試",
            "HanLoTaibunPoj": "chhek-chhì",
            "PojUnicode": "",
            "KipUnicode": "tshik-tshì",
        }
        result = parse_itaigi_row(row)
        assert result["pronunciation"] == "tshik-tshì"


# ---------------------------------------------------------------------------
# 台華對照典 parser
# ---------------------------------------------------------------------------


class TestParseTaihua:
    """Test 台華線頂對照典 CSV row parsing."""

    def test_basic_row(self):
        row = {
            "HoaBun": "不然",
            "HanLoTaibunPoj": "á無",
            "PojUnicode": "á-bô",
            "PojUnicodeOthers": "",
            "KipUnicode": "á-bô",
            "KipUnicodeOthers": "",
        }
        result = parse_taihua_row(row)
        assert result["mandarin"] == "不然"
        assert result["native_chars"] == "á無"
        assert result["pronunciation"] == "á-bô"

    def test_same_chars(self):
        row = {
            "HoaBun": "急躁",
            "HanLoTaibunPoj": "急躁",
            "PojUnicode": "kip-sò",
            "PojUnicodeOthers": "",
            "KipUnicode": "kip-sò",
            "KipUnicodeOthers": "",
        }
        result = parse_taihua_row(row)
        assert result["native_chars"] is None

    def test_empty_mandarin(self):
        row = {
            "HoaBun": "",
            "HanLoTaibunPoj": "test",
            "PojUnicode": "test",
            "PojUnicodeOthers": "",
            "KipUnicode": "",
            "KipUnicodeOthers": "",
        }
        assert parse_taihua_row(row) is None
