"""Tests for dictmaster merge and reconciliation logic."""

import pytest

from tools.dictmaster.schema import get_connection, init_db, upsert_definition, upsert_headword
from tools.dictmaster.merge import (
    _pinyin_merge_key,
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

    def test_case_preserved(self):
        # Case is preserved — CC-CEDICT uses caps for surnames/proper nouns
        assert normalize_pinyin("Zhong1 Guo2") == "Zhong1 Guo2"
        assert normalize_pinyin("he2") == "he2"
        assert normalize_pinyin("He2") == "He2"

    def test_normalize_whitespace(self):
        assert normalize_pinyin("zhong1  guo2") == "zhong1 guo2"

    def test_strip(self):
        assert normalize_pinyin("  ni3 hao3  ") == "ni3 hao3"

    def test_passthrough(self):
        assert normalize_pinyin("ni3 hao3") == "ni3 hao3"


class TestPinyinMergeKey:
    """Test pinyin merge key generation for duplicate detection."""

    def test_spacing_stripped(self):
        assert _pinyin_merge_key("dong4 tai4 zhu4 ci2") == _pinyin_merge_key("dongtai4 zhuci2")

    def test_u_colon_normalized(self):
        assert _pinyin_merge_key("lu:4") == _pinyin_merge_key("lv4")

    def test_umlaut_normalized(self):
        assert _pinyin_merge_key("nü3") == _pinyin_merge_key("nv3")

    def test_hyphens_stripped(self):
        assert _pinyin_merge_key("yibai-mi3") == _pinyin_merge_key("yibaimi3")

    def test_case_preserved(self):
        assert _pinyin_merge_key("He2") != _pinyin_merge_key("he2")

    def test_different_syllables_differ(self):
        # le vs liao — different syllables, must not merge
        assert _pinyin_merge_key("le5") != _pinyin_merge_key("liao3")

    def test_same_syllable_different_tones_merge(self):
        # de5 (particle) and de2 (obtain) — same base, merged under one headword
        assert _pinyin_merge_key("de5") == _pinyin_merge_key("de2")

    def test_parenthesized_annotations_stripped(self):
        # Wiktextract-style annotations like (ei¹)5
        assert _pinyin_merge_key("ei1 (ei¹)5") == _pinyin_merge_key("ei1")


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

    def test_no_merge_case_distinguished_pinyin(self, db):
        """He2 (surname) and he2 (common word) must NOT be merged."""
        id1 = upsert_headword(db, "和", "和", "He2")
        id2 = upsert_headword(db, "和", "和", "he2")
        upsert_definition(db, id1, "en", "surname He", "cedict")
        upsert_definition(db, id2, "en", "and; together with; harmonious", "cedict")
        db.commit()

        merged = reconcile_headwords(db)
        assert merged == 0

        # Both headwords must survive
        hw_count = db.execute("SELECT COUNT(*) FROM headwords").fetchone()[0]
        assert hw_count == 2

    def test_merge_spacing_variants(self, db):
        """char-level 'dong4 tai4 zhu4 ci2' merges with word-level 'dongtai4 zhuci2'."""
        id1 = upsert_headword(db, "動態助詞", "动态助词", "dong4 tai4 zhu4 ci2")
        id2 = upsert_headword(db, "動態助詞", "动态助词", "dongtai4 zhuci2")
        upsert_definition(db, id1, "en", "aspect particle", "cedict")
        upsert_definition(db, id2, "en", "aspect particle (Wiktextract)", "wiktextract")
        db.commit()

        merged = reconcile_headwords(db)
        assert merged == 1

        hw_count = db.execute("SELECT COUNT(*) FROM headwords").fetchone()[0]
        assert hw_count == 1

        # Both definitions should be on the surviving headword
        defs = db.execute(
            "SELECT * FROM definitions WHERE headword_id = ?", (id1,)
        ).fetchall()
        assert len(defs) == 2

    def test_merge_hyphenated_pinyin(self, db):
        """Hyphens in Wiktextract pinyin should not prevent merging."""
        id1 = upsert_headword(db, "一百米", "一百米", "yi1 bai3 mi3")
        id2 = upsert_headword(db, "一百米", "一百米", "yibai-mi3")
        upsert_definition(db, id1, "en", "100 meters", "cedict")
        upsert_definition(db, id2, "en", "one hundred meters", "wiktextract")
        db.commit()

        merged = reconcile_headwords(db)
        assert merged == 1

    def test_no_merge_different_syllables(self, db):
        """Different syllable bases (le vs liao) must not be merged."""
        id1 = upsert_headword(db, "了", "了", "le5")
        id2 = upsert_headword(db, "了", "了", "liao3")
        upsert_definition(db, id1, "en", "(particle)", "cedict")
        upsert_definition(db, id2, "en", "to finish", "cedict")
        db.commit()

        merged = reconcile_headwords(db)
        assert merged == 0
        assert db.execute("SELECT COUNT(*) FROM headwords").fetchone()[0] == 2

    def test_merge_same_syllable_different_tones(self, db):
        """Same base syllable with different tones → merge (e.g. 得 de2/de5)."""
        id1 = upsert_headword(db, "得", "得", "de2")
        id2 = upsert_headword(db, "得", "得", "de5")
        upsert_definition(db, id1, "en", "to obtain", "cedict")
        upsert_definition(db, id2, "en", "structural particle", "wiktextract")
        db.commit()

        merged = reconcile_headwords(db)
        assert merged == 1
        # Both definitions survive (different sources bypass UNIQUE constraint)
        defs = db.execute("SELECT * FROM definitions WHERE headword_id = ?", (id1,)).fetchall()
        assert len(defs) == 2


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
