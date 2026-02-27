"""Tests for dictmaster parsers (CEDICT-format and Wiktextract)."""

import gzip
import json
import pytest

from tools.dictmaster.schema import get_connection, init_db
from tools.dictmaster.parsers.cedict_format import (
    CedictEntry,
    import_cedict_file,
    infer_pos,
    iter_cedict,
    parse_cedict_line,
)
from tools.dictmaster.parsers.wiktextract import (
    WiktEntry,
    import_wiktextract,
    iter_wiktextract,
    parse_wiktextract_entry,
    tone_marked_to_numbered,
    _get_simplified,
    _get_pinyin,
    _get_glosses,
)


@pytest.fixture
def db():
    conn = get_connection()
    init_db(conn)
    yield conn
    conn.close()


# ---- CEDICT-format parser ----

class TestCedictParseLine:
    """Parse individual CEDICT-format lines."""

    def test_standard_entry(self):
        line = "銀行 银行 [yin2 hang2] /bank/CL:家[jia1],個|个[ge4]/"
        result = parse_cedict_line(line)
        assert result == CedictEntry("銀行", "银行", "yin2 hang2", "bank/CL:家[jia1],個|个[ge4]")

    def test_single_definition(self):
        result = parse_cedict_line("你好 你好 [ni3 hao3] /hello/")
        assert result == CedictEntry("你好", "你好", "ni3 hao3", "hello")

    def test_multiple_definitions(self):
        result = parse_cedict_line("行 行 [xing2] /to walk/to go/to travel/a row/")
        assert result is not None
        assert result.traditional == "行"
        assert "to walk" in result.definition
        assert "a row" in result.definition

    def test_comment_line(self):
        assert parse_cedict_line("# CC-CEDICT") is None

    def test_percent_comment(self):
        assert parse_cedict_line("% metadata") is None

    def test_empty_line(self):
        assert parse_cedict_line("") is None
        assert parse_cedict_line("   ") is None

    def test_malformed_line(self):
        assert parse_cedict_line("this is not a valid entry") is None

    def test_empty_definition_skipped(self):
        assert parse_cedict_line("你 你 [ni3] //") is None


class TestCedictIterFile:
    """Iterate over CEDICT-format files."""

    def test_plain_text(self, tmp_path):
        f = tmp_path / "dict.txt"
        f.write_text(
            "# Header\n"
            "你好 你好 [ni3 hao3] /hello/\n"
            "謝謝 谢谢 [xie4 xie5] /thanks/\n",
            encoding="utf-8",
        )
        entries = list(iter_cedict(f))
        assert len(entries) == 2
        assert entries[0].simplified == "你好"
        assert entries[1].simplified == "谢谢"

    def test_gzipped(self, tmp_path):
        f = tmp_path / "dict.txt.gz"
        content = "你好 你好 [ni3 hao3] /hello/\n"
        with gzip.open(f, "wt", encoding="utf-8") as gz:
            gz.write(content)
        entries = list(iter_cedict(f))
        assert len(entries) == 1


class TestCedictInferPos:
    """Test POS inference from definitions."""

    def test_verb(self):
        assert infer_pos("to walk/to go") == "verb"

    def test_noun_with_classifier(self):
        assert infer_pos("bank/CL:家[jia1]") == "noun"

    def test_phrase(self):
        assert infer_pos("(greeting)") == "phrase"

    def test_unknown(self):
        assert infer_pos("hello") is None


class TestCedictImport:
    """Test importing CEDICT-format files into the database."""

    def test_import_small_file(self, db, tmp_path):
        f = tmp_path / "cedict.txt"
        f.write_text(
            "# CC-CEDICT\n"
            "你好 你好 [ni3 hao3] /hello/hi/\n"
            "銀行 银行 [yin2 hang2] /bank/\n"
            "走 走 [zou3] /to walk/to go/\n",
            encoding="utf-8",
        )
        count = import_cedict_file(db, f, "cedict", "en")
        assert count == 3

        # Check headwords
        hw = db.execute("SELECT COUNT(*) FROM headwords").fetchone()[0]
        assert hw == 3

        # Check definitions
        defs = db.execute("SELECT COUNT(*) FROM definitions").fetchone()[0]
        assert defs == 3

        # Check source
        src = db.execute("SELECT * FROM sources WHERE name = 'cedict'").fetchone()
        assert src is not None

    def test_import_with_limit(self, db, tmp_path):
        f = tmp_path / "cedict.txt"
        f.write_text(
            "你好 你好 [ni3 hao3] /hello/\n"
            "銀行 银行 [yin2 hang2] /bank/\n"
            "走 走 [zou3] /to walk/\n",
            encoding="utf-8",
        )
        count = import_cedict_file(db, f, "cedict", "en", limit=2)
        assert count == 2

    def test_import_french(self, db, tmp_path):
        f = tmp_path / "cfdict.txt"
        f.write_text(
            "你好 你好 [ni3 hao3] /bonjour/salut/\n",
            encoding="utf-8",
        )
        count = import_cedict_file(db, f, "cfdict", "fr")
        assert count == 1

        defn = db.execute(
            "SELECT d.lang, d.definition, d.source FROM definitions d"
        ).fetchone()
        assert defn["lang"] == "fr"
        assert defn["source"] == "cfdict"
        assert "bonjour" in defn["definition"]

    def test_import_pos_inference(self, db, tmp_path):
        f = tmp_path / "cedict.txt"
        f.write_text(
            "走 走 [zou3] /to walk/to go/\n",
            encoding="utf-8",
        )
        import_cedict_file(db, f, "cedict", "en")
        hw = db.execute("SELECT pos FROM headwords WHERE simplified = '走'").fetchone()
        assert hw["pos"] == "verb"


# ---- Wiktextract parser ----

class TestToneConversion:
    """Test tone-marked to numbered pinyin conversion."""

    def test_space_separated(self):
        assert tone_marked_to_numbered("nǐ hǎo") == "ni3 hao3"

    def test_run_together(self):
        result = tone_marked_to_numbered("diànnǎo")
        assert result == "dian4 nao3"

    def test_first_tone(self):
        assert tone_marked_to_numbered("zhōng") == "zhong1"

    def test_second_tone(self):
        assert tone_marked_to_numbered("guó") == "guo2"

    def test_neutral_tone(self):
        result = tone_marked_to_numbered("ma")
        assert result.endswith("5")

    def test_empty_string(self):
        assert tone_marked_to_numbered("") == ""


class TestWiktextractHelpers:
    """Test Wiktextract entry field extraction."""

    def test_get_simplified(self):
        entry = {
            "forms": [
                {"form": "电脑", "tags": ["Simplified-Chinese"]},
                {"form": "电㐫", "tags": ["Second-Round-Simplified-Chinese", "Simplified-Chinese"]},
            ]
        }
        assert _get_simplified(entry) == "电脑"

    def test_get_simplified_missing(self):
        assert _get_simplified({"forms": []}) is None
        assert _get_simplified({}) is None

    def test_get_pinyin(self):
        entry = {
            "sounds": [
                {"zh_pron": "diànnǎo", "tags": ["Mandarin", "Pinyin"]},
                {"zh_pron": "ㄉㄧㄢˋ ㄋㄠˇ", "tags": ["Mandarin", "Bopomofo"]},
            ]
        }
        assert _get_pinyin(entry) == "diànnǎo"

    def test_get_pinyin_missing(self):
        assert _get_pinyin({"sounds": []}) is None

    def test_get_glosses(self):
        entry = {
            "senses": [
                {"glosses": ["computer (electronic device)"]},
                {"glosses": ["brain (slang)"]},
            ]
        }
        glosses = _get_glosses(entry)
        assert "computer (electronic device)" in glosses
        assert "brain (slang)" in glosses

    def test_get_glosses_skips_form_of(self):
        entry = {
            "senses": [
                {"glosses": ["real meaning"]},
                {"glosses": ["alt form of X"], "form_of": [{"word": "X"}]},
            ]
        }
        glosses = _get_glosses(entry)
        assert len(glosses) == 1
        assert glosses[0] == "real meaning"


class TestWiktextractParseEntry:
    """Test full Wiktextract entry parsing."""

    def test_full_entry(self):
        entry = {
            "word": "電腦",
            "lang_code": "zh",
            "pos": "noun",
            "forms": [{"form": "电脑", "tags": ["Simplified-Chinese"]}],
            "sounds": [
                {"zh_pron": "diànnǎo", "tags": ["Mandarin", "Pinyin"]},
            ],
            "senses": [
                {"glosses": ["computer"]},
            ],
            "translations": [
                {"lang_code": "ja", "word": "コンピュータ"},
                {"lang_code": "ko", "word": "컴퓨터"},
            ],
        }
        result = parse_wiktextract_entry(entry)
        assert result is not None
        assert result.traditional == "電腦"
        assert result.simplified == "电脑"
        assert "dian4" in result.pinyin
        assert "nao3" in result.pinyin
        assert result.pos == "noun"
        assert "computer" in result.glosses_en
        assert "ja" in result.translations
        assert "ko" in result.translations

    def test_missing_pinyin_returns_none(self):
        entry = {
            "word": "test",
            "lang_code": "zh",
            "pos": "noun",
            "sounds": [],
            "senses": [{"glosses": ["test"]}],
        }
        assert parse_wiktextract_entry(entry) is None

    def test_missing_glosses_returns_none(self):
        entry = {
            "word": "test",
            "lang_code": "zh",
            "pos": "noun",
            "sounds": [{"zh_pron": "cè", "tags": ["Mandarin", "Pinyin"]}],
            "senses": [],
        }
        assert parse_wiktextract_entry(entry) is None

    def test_simplified_falls_back_to_traditional(self):
        entry = {
            "word": "人",
            "lang_code": "zh",
            "pos": "noun",
            "forms": [],
            "sounds": [{"zh_pron": "rén", "tags": ["Mandarin", "Pinyin"]}],
            "senses": [{"glosses": ["person"]}],
        }
        result = parse_wiktextract_entry(entry)
        assert result.simplified == "人"  # Same as traditional


class TestWiktextractImport:
    """Test importing Wiktextract JSONL into the database."""

    def test_import_jsonl(self, db, tmp_path):
        entries = [
            {
                "word": "電腦",
                "lang_code": "zh",
                "pos": "noun",
                "forms": [{"form": "电脑", "tags": ["Simplified-Chinese"]}],
                "sounds": [{"zh_pron": "diànnǎo", "tags": ["Mandarin", "Pinyin"]}],
                "senses": [{"glosses": ["computer"]}],
                "translations": [
                    {"lang_code": "ja", "word": "コンピュータ"},
                ],
            },
            {
                "word": "你好",
                "lang_code": "zh",
                "pos": "intj",
                "forms": [],
                "sounds": [{"zh_pron": "nǐ hǎo", "tags": ["Mandarin", "Pinyin"]}],
                "senses": [{"glosses": ["hello"]}],
                "translations": [],
            },
        ]

        f = tmp_path / "wikt.jsonl"
        with open(f, "w", encoding="utf-8") as fh:
            for e in entries:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")

        count = import_wiktextract(db, f)
        assert count == 2

        # Check headwords
        hw_count = db.execute("SELECT COUNT(*) FROM headwords").fetchone()[0]
        assert hw_count == 2

        # Check English definitions
        en_defs = db.execute(
            "SELECT COUNT(*) FROM definitions WHERE lang = 'en'"
        ).fetchone()[0]
        assert en_defs == 2

        # Check Japanese translation imported
        ja_def = db.execute(
            "SELECT definition FROM definitions WHERE lang = 'ja'"
        ).fetchone()
        assert ja_def is not None
        assert "コンピュータ" in ja_def["definition"]

    def test_import_gzipped(self, db, tmp_path):
        entry = {
            "word": "人",
            "lang_code": "zh",
            "pos": "noun",
            "sounds": [{"zh_pron": "rén", "tags": ["Mandarin", "Pinyin"]}],
            "senses": [{"glosses": ["person/people"]}],
        }

        f = tmp_path / "wikt.jsonl.gz"
        with gzip.open(f, "wt", encoding="utf-8") as gz:
            gz.write(json.dumps(entry, ensure_ascii=False) + "\n")

        count = import_wiktextract(db, f)
        assert count == 1

    def test_import_with_limit(self, db, tmp_path):
        entries = []
        for i, char in enumerate("人大中小"):
            entries.append({
                "word": char,
                "lang_code": "zh",
                "pos": "noun",
                "sounds": [{"zh_pron": "rén", "tags": ["Mandarin", "Pinyin"]}],
                "senses": [{"glosses": [f"meaning_{i}"]}],
            })

        f = tmp_path / "wikt.jsonl"
        with open(f, "w") as fh:
            for e in entries:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")

        count = import_wiktextract(db, f, limit=2)
        assert count == 2
