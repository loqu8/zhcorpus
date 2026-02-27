"""Tests for JMdict XML parser."""

import gzip
import pytest

from tools.dictmaster.schema import get_connection, init_db
from tools.dictmaster.parsers.jmdict import (
    JmdictEntry,
    _is_pure_cjk,
    _map_pos,
    iter_jmdict,
    import_jmdict,
)


SAMPLE_JMDICT_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<JMdict>
<entry>
<ent_seq>1000220</ent_seq>
<k_ele>
<keb>明白</keb>
</k_ele>
<r_ele>
<reb>めいはく</reb>
</r_ele>
<sense>
<pos>noun (common) (futsuumeishi)</pos>
<gloss>obvious</gloss>
<gloss>clear</gloss>
<gloss>plain</gloss>
</sense>
<sense>
<gloss xml:lang="fre">clair</gloss>
</sense>
</entry>
<entry>
<ent_seq>1001000</ent_seq>
<k_ele>
<keb>銀行</keb>
</k_ele>
<r_ele>
<reb>ぎんこう</reb>
</r_ele>
<sense>
<pos>noun (common) (futsuumeishi)</pos>
<gloss>bank</gloss>
</sense>
<sense>
<gloss xml:lang="fre">banque</gloss>
</sense>
</entry>
<entry>
<ent_seq>1002000</ent_seq>
<k_ele>
<keb>走る</keb>
</k_ele>
<r_ele>
<reb>はしる</reb>
</r_ele>
<sense>
<pos>Godan verb with ru ending</pos>
<gloss>to run</gloss>
</sense>
</entry>
<entry>
<ent_seq>1003000</ent_seq>
<r_ele>
<reb>すごい</reb>
</r_ele>
<sense>
<pos>adjective (keiyoushi)</pos>
<gloss>amazing</gloss>
</sense>
</entry>
</JMdict>
"""


@pytest.fixture
def db():
    conn = get_connection()
    init_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def jmdict_file(tmp_path):
    """Write sample JMdict XML to a file."""
    f = tmp_path / "JMdict.xml"
    f.write_text(SAMPLE_JMDICT_XML, encoding="utf-8")
    return f


@pytest.fixture
def jmdict_gz(tmp_path):
    """Write sample JMdict XML to a gzipped file."""
    f = tmp_path / "JMdict.gz"
    with gzip.open(f, "wt", encoding="utf-8") as gz:
        gz.write(SAMPLE_JMDICT_XML)
    return f


class TestIsPureCjk:
    """Test CJK character detection."""

    def test_pure_cjk(self):
        assert _is_pure_cjk("明白")
        assert _is_pure_cjk("銀行")

    def test_mixed(self):
        assert not _is_pure_cjk("走る")  # Has hiragana

    def test_kana_only(self):
        assert not _is_pure_cjk("すごい")

    def test_empty(self):
        assert not _is_pure_cjk("")


class TestMapPos:
    """Test POS mapping."""

    def test_noun(self):
        assert _map_pos("noun (common) (futsuumeishi)") == "noun"

    def test_verb(self):
        assert _map_pos("Godan verb with ru ending") == "verb"

    def test_adjective(self):
        assert _map_pos("adjective (keiyoushi)") == "adj"

    def test_unknown(self):
        assert _map_pos("something unusual") is None


class TestIterJmdict:
    """Test iterating over JMdict XML."""

    def test_yields_pure_cjk_entries(self, jmdict_file):
        entries = list(iter_jmdict(jmdict_file))
        # Should get 明白 and 銀行, but NOT 走る (mixed) or すごい (no kanji)
        assert len(entries) == 2
        kanji_set = {e.kanji for e in entries}
        assert "明白" in kanji_set
        assert "銀行" in kanji_set

    def test_skips_mixed_kanji(self, jmdict_file):
        entries = list(iter_jmdict(jmdict_file))
        kanji_set = {e.kanji for e in entries}
        assert "走る" not in kanji_set

    def test_skips_kana_only(self, jmdict_file):
        entries = list(iter_jmdict(jmdict_file))
        kanji_set = {e.kanji for e in entries}
        assert "すごい" not in kanji_set

    def test_entry_fields(self, jmdict_file):
        entries = list(iter_jmdict(jmdict_file))
        meihaku = [e for e in entries if e.kanji == "明白"][0]
        assert meihaku.reading == "めいはく"
        assert meihaku.pos == "noun"
        assert "obvious" in meihaku.glosses_en
        assert "clear" in meihaku.glosses_en

    def test_gzipped(self, jmdict_gz):
        entries = list(iter_jmdict(jmdict_gz))
        assert len(entries) == 2

    def test_japanese_reading_as_glosses_ja(self, jmdict_file):
        entries = list(iter_jmdict(jmdict_file))
        ginkou = [e for e in entries if e.kanji == "銀行"][0]
        assert ginkou.glosses_ja == "ぎんこう"


class TestImportJmdict:
    """Test importing JMdict into the database."""

    def test_import(self, db, jmdict_file):
        count = import_jmdict(db, jmdict_file)
        assert count == 2

        # Check Japanese definitions exist
        ja_defs = db.execute(
            "SELECT COUNT(*) FROM definitions WHERE lang = 'ja' AND source = 'jmdict'"
        ).fetchone()[0]
        assert ja_defs == 2

    def test_import_with_limit(self, db, jmdict_file):
        count = import_jmdict(db, jmdict_file, limit=1)
        assert count == 1

    def test_import_matches_existing_headword(self, db, jmdict_file):
        """If a headword already exists, JMdict should add ja definition to it."""
        from tools.dictmaster.schema import upsert_headword, upsert_definition

        # Pre-populate 銀行 from CEDICT
        hw_id = upsert_headword(db, "銀行", "银行", "yin2 hang2", pos="noun")
        upsert_definition(db, hw_id, "en", "bank", "cedict")
        db.commit()

        import_jmdict(db, jmdict_file)

        # The ja definition should be linked to the existing headword
        ja_def = db.execute(
            "SELECT d.definition FROM definitions d "
            "JOIN headwords h ON d.headword_id = h.id "
            "WHERE h.simplified = '银行' AND d.lang = 'ja'"
        ).fetchone()
        assert ja_def is not None
        assert "ぎんこう" in ja_def["definition"]

    def test_import_gzipped(self, db, jmdict_gz):
        count = import_jmdict(db, jmdict_gz)
        assert count == 2
