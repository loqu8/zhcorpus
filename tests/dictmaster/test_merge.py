"""Tests for dictmaster merge and reconciliation logic."""

import pytest

from tools.dictmaster.schema import get_connection, init_db, upsert_definition, upsert_headword
from tools.dictmaster.merge import (
    fill_pos_from_definitions,
    get_coverage_report,
    infer_pos_from_definition,
    merge_pos,
    normalize_pinyin,
    reconcile_headwords,
)


@pytest.fixture
def db():
    conn = get_connection()
    init_db(conn)
    yield conn
    conn.close()


class TestNormalizePinyin:
    """Test pinyin normalization."""

    def test_u_colon_to_v(self):
        assert normalize_pinyin("lu:4") == "lv4"
        assert normalize_pinyin("nu:3") == "nv3"

    def test_umlaut_to_v(self):
        assert normalize_pinyin("nü3") == "nv3"
        assert normalize_pinyin("lü4") == "lv4"

    def test_lowercase(self):
        assert normalize_pinyin("Zhong1 Guo2") == "zhong1 guo2"

    def test_normalize_whitespace(self):
        assert normalize_pinyin("zhong1  guo2") == "zhong1 guo2"

    def test_strip(self):
        assert normalize_pinyin("  ni3 hao3  ") == "ni3 hao3"

    def test_passthrough(self):
        assert normalize_pinyin("ni3 hao3") == "ni3 hao3"


class TestInferPos:
    """Test POS inference from definitions."""

    def test_verb(self):
        assert infer_pos_from_definition("to walk/to go") == "verb"

    def test_noun(self):
        assert infer_pos_from_definition("bank/CL:家[jia1]") == "noun"

    def test_particle(self):
        assert infer_pos_from_definition("(particle) used after a verb") == "particle"

    def test_classifier(self):
        assert infer_pos_from_definition("(classifier for books)") == "classifier"

    def test_phrase(self):
        assert infer_pos_from_definition("(greeting)") == "phrase"

    def test_unknown(self):
        assert infer_pos_from_definition("hello") is None

    def test_empty(self):
        assert infer_pos_from_definition("") is None


class TestMergePos:
    """Test POS merging from multiple sources."""

    def test_both_none(self):
        assert merge_pos(None, None) is None

    def test_existing_wins(self):
        assert merge_pos("verb", "noun") == "verb"

    def test_new_fills_gap(self):
        assert merge_pos(None, "verb") == "verb"

    def test_existing_preserved(self):
        assert merge_pos("noun", None) == "noun"


class TestReconcileHeadwords:
    """Test headword reconciliation for pinyin variants."""

    def test_merge_u_colon_variant(self, db):
        # Insert same word with different pinyin representations
        id1 = upsert_headword(db, "女", "女", "nv3")
        id2 = upsert_headword(db, "女", "女", "nu:3")
        upsert_definition(db, id1, "en", "woman", "cedict")
        upsert_definition(db, id2, "en", "female", "handedict")
        db.commit()

        merged = reconcile_headwords(db)
        assert merged == 1

        # Only one headword should remain
        hw_count = db.execute("SELECT COUNT(*) FROM headwords").fetchone()[0]
        assert hw_count == 1

        # Definition from the merged headword should be moved
        defs = db.execute(
            "SELECT * FROM definitions WHERE headword_id = ?", (id1,)
        ).fetchall()
        assert len(defs) >= 1

    def test_no_merge_when_different_words(self, db):
        upsert_headword(db, "你", "你", "ni3")
        upsert_headword(db, "她", "她", "ta1")
        db.commit()

        merged = reconcile_headwords(db)
        assert merged == 0


class TestFillPos:
    """Test POS inference from definitions."""

    def test_fills_verb(self, db):
        hw_id = upsert_headword(db, "走", "走", "zou3")
        upsert_definition(db, hw_id, "en", "to walk/to go", "cedict")
        db.commit()

        updated = fill_pos_from_definitions(db)
        assert updated == 1

        hw = db.execute("SELECT pos FROM headwords WHERE id = ?", (hw_id,)).fetchone()
        assert hw["pos"] == "verb"

    def test_skips_existing_pos(self, db):
        hw_id = upsert_headword(db, "走", "走", "zou3", pos="noun")
        upsert_definition(db, hw_id, "en", "to walk", "cedict")
        db.commit()

        updated = fill_pos_from_definitions(db)
        assert updated == 0

    def test_skips_when_no_english(self, db):
        hw_id = upsert_headword(db, "走", "走", "zou3")
        upsert_definition(db, hw_id, "fr", "marcher", "cfdict")
        db.commit()

        updated = fill_pos_from_definitions(db)
        assert updated == 0  # Can't infer POS from French


class TestCoverageReport:
    """Test coverage reporting."""

    def test_empty_db(self, db):
        report = get_coverage_report(db)
        assert report["total_headwords"] == 0

    def test_with_data(self, db):
        hw1 = upsert_headword(db, "你好", "你好", "ni3 hao3")
        hw2 = upsert_headword(db, "走", "走", "zou3")
        upsert_definition(db, hw1, "en", "hello", "cedict")
        upsert_definition(db, hw2, "en", "to walk", "cedict")
        upsert_definition(db, hw1, "fr", "bonjour", "cfdict")
        db.commit()

        report = get_coverage_report(db)
        assert report["total_headwords"] == 2
        assert report["coverage"]["en"]["count"] == 2
        assert report["coverage"]["fr"]["count"] == 1
        assert report["gaps"]["fr"] == 1  # 走 has no French def
        assert report["gaps"]["en"] == 0
