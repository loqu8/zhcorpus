"""Tests for dictmaster CEDICT export."""

import pytest

from tools.dictmaster.schema import get_connection, init_db, upsert_definition, upsert_headword
from tools.dictmaster.export import export_language, export_stats, _best_definition
from tools.dictmaster.parsers.cedict_format import parse_cedict_line


@pytest.fixture
def db():
    conn = get_connection()
    init_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def populated_db(db):
    """DB with sample multilingual entries."""
    hw1 = upsert_headword(db, "你好", "你好", "ni3 hao3", pos="intj")
    upsert_definition(db, hw1, "en", "hello/hi", "cedict")
    upsert_definition(db, hw1, "fr", "bonjour/salut", "cfdict")
    upsert_definition(db, hw1, "de", "Hallo", "handedict")
    upsert_definition(db, hw1, "en", "hello (greeting)", "wiktextract")

    hw2 = upsert_headword(db, "銀行", "银行", "yin2 hang2", pos="noun")
    upsert_definition(db, hw2, "en", "bank", "cedict")
    upsert_definition(db, hw2, "fr", "banque", "cfdict")

    hw3 = upsert_headword(db, "走", "走", "zou3", pos="verb")
    upsert_definition(db, hw3, "en", "to walk/to go", "cedict")
    upsert_definition(db, hw3, "es", "caminar/ir", "minimax", "medium")

    db.commit()
    return db


class TestBestDefinition:
    """Test definition priority selection."""

    def test_dictionary_beats_wiktextract(self):
        defs = [
            {"definition": "hello (greeting)", "source": "wiktextract"},
            {"definition": "hello/hi", "source": "cedict"},
        ]
        assert _best_definition(defs) == "hello/hi"

    def test_wiktextract_beats_ai(self):
        defs = [
            {"definition": "hola", "source": "minimax"},
            {"definition": "hola/saludo", "source": "wiktextract"},
        ]
        assert _best_definition(defs) == "hola/saludo"

    def test_single_source(self):
        defs = [{"definition": "bank", "source": "cedict"}]
        assert _best_definition(defs) == "bank"

    def test_empty(self):
        assert _best_definition([]) == ""


class TestExportLanguage:
    """Test per-language CEDICT file export."""

    def test_export_english(self, populated_db, tmp_path):
        path = export_language(populated_db, "en", tmp_path)
        assert path.exists()

        content = path.read_text(encoding="utf-8")
        # Check header
        assert "Dictmaster" in content
        assert "English" in content

        # Check entries
        lines = [l for l in content.split("\n") if l and not l.startswith("#")]
        assert len(lines) == 3

        # Parse back and verify
        for line in lines:
            entry = parse_cedict_line(line)
            assert entry is not None, f"Failed to parse: {line}"

    def test_export_french(self, populated_db, tmp_path):
        path = export_language(populated_db, "fr", tmp_path)
        content = path.read_text(encoding="utf-8")
        lines = [l for l in content.split("\n") if l and not l.startswith("#")]
        assert len(lines) == 2  # 你好 and 银行 have French defs

    def test_export_spanish(self, populated_db, tmp_path):
        path = export_language(populated_db, "es", tmp_path)
        content = path.read_text(encoding="utf-8")
        lines = [l for l in content.split("\n") if l and not l.startswith("#")]
        assert len(lines) == 1  # Only 走 has Spanish

    def test_export_sorted_by_pinyin(self, populated_db, tmp_path):
        path = export_language(populated_db, "en", tmp_path)
        content = path.read_text(encoding="utf-8")
        lines = [l for l in content.split("\n") if l and not l.startswith("#")]
        # ni3 hao3 < yin2 hang2 < zou3 (alphabetical pinyin order)
        assert "ni3 hao3" in lines[0]
        assert "yin2 hang2" in lines[1]
        assert "zou3" in lines[2]

    def test_export_best_definition_chosen(self, populated_db, tmp_path):
        """When multiple sources exist, dictionary source wins over wiktextract."""
        path = export_language(populated_db, "en", tmp_path)
        content = path.read_text(encoding="utf-8")
        # 你好 has cedict "hello/hi" and wiktextract "hello (greeting)"
        # cedict should win (priority 1 vs 3)
        assert "/hello/hi/" in content

    def test_export_custom_filename(self, populated_db, tmp_path):
        path = export_language(populated_db, "en", tmp_path, filename="custom.txt")
        assert path.name == "custom.txt"

    def test_roundtrip_integrity(self, populated_db, tmp_path):
        """Export and re-parse should produce valid CEDICT entries."""
        path = export_language(populated_db, "en", tmp_path)
        content = path.read_text(encoding="utf-8")

        parsed = []
        for line in content.split("\n"):
            if line and not line.startswith("#"):
                entry = parse_cedict_line(line)
                assert entry is not None
                parsed.append(entry)

        assert len(parsed) == 3
        # Check specific entry
        nihao = [e for e in parsed if e.simplified == "你好"][0]
        assert nihao.traditional == "你好"
        assert nihao.pinyin == "ni3 hao3"
        assert "hello" in nihao.definition


class TestExportStats:
    """Test export statistics."""

    def test_stats(self, populated_db):
        stats = export_stats(populated_db)
        assert stats["en"] == 3
        assert stats["fr"] == 2
        assert stats["de"] == 1
        assert stats["es"] == 1
