"""Tests for CC-CEDICT parser."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from zhcorpus.db import get_connection, init_db
from zhcorpus.ingest.cedict_parser import load_cedict, parse_cedict_line, iter_cedict


class TestParseLine:
    """Parse individual CC-CEDICT lines."""

    def test_standard_entry(self):
        line = "銀行 银行 [yin2 hang2] /bank/CL:家[jia1],個|个[ge4]/"
        result = parse_cedict_line(line)
        assert result == ("銀行", "银行", "yin2 hang2", "bank/CL:家[jia1],個|个[ge4]")

    def test_single_definition(self):
        line = "你好 你好 [ni3 hao3] /hello/"
        result = parse_cedict_line(line)
        assert result == ("你好", "你好", "ni3 hao3", "hello")

    def test_multiple_definitions(self):
        line = "行 行 [xing2] /to walk/to go/to travel/a row/"
        result = parse_cedict_line(line)
        assert result is not None
        trad, simp, pinyin, defn = result
        assert trad == "行"
        assert pinyin == "xing2"
        assert "to walk" in defn
        assert "a row" in defn

    def test_comment_line(self):
        assert parse_cedict_line("# CC-CEDICT") is None

    def test_empty_line(self):
        assert parse_cedict_line("") is None
        assert parse_cedict_line("   ") is None

    def test_traditional_differs(self):
        line = "選任 选任 [xuan3 ren4] /to select and appoint/"
        result = parse_cedict_line(line)
        assert result is not None
        assert result[0] == "選任"
        assert result[1] == "选任"


class TestIterCedict:
    """Iterate over a CC-CEDICT file."""

    def test_reads_file(self, tmp_path):
        cedict_file = tmp_path / "cedict.txt"
        cedict_file.write_text(
            "# CC-CEDICT\n"
            "# Comment\n"
            "你好 你好 [ni3 hao3] /hello/hi/\n"
            "謝謝 谢谢 [xie4 xie5] /thanks/thank you/\n",
            encoding="utf-8",
        )
        entries = list(iter_cedict(cedict_file))
        assert len(entries) == 2
        assert entries[0][1] == "你好"
        assert entries[1][1] == "谢谢"

    def test_skips_malformed(self, tmp_path):
        cedict_file = tmp_path / "cedict.txt"
        cedict_file.write_text(
            "你好 你好 [ni3 hao3] /hello/\n"
            "this is not a valid entry\n"
            "謝謝 谢谢 [xie4 xie5] /thanks/\n",
            encoding="utf-8",
        )
        entries = list(iter_cedict(cedict_file))
        assert len(entries) == 2


class TestLoadCedict:
    """Load CC-CEDICT into the database."""

    def test_load_small_file(self, tmp_path):
        cedict_file = tmp_path / "cedict.txt"
        cedict_file.write_text(
            "# CC-CEDICT\n"
            "你好 你好 [ni3 hao3] /hello/hi/\n"
            "銀行 银行 [yin2 hang2] /bank/\n"
            "選任 选任 [xuan3 ren4] /to select and appoint/\n",
            encoding="utf-8",
        )

        conn = get_connection()
        init_db(conn)
        count = load_cedict(conn, cedict_file)

        assert count == 3
        row = conn.execute(
            "SELECT * FROM cedict WHERE simplified = '银行'"
        ).fetchone()
        assert row is not None
        assert row["traditional"] == "銀行"
        assert row["pinyin"] == "yin2 hang2"
        conn.close()

    def test_deduplication(self, tmp_path):
        cedict_file = tmp_path / "cedict.txt"
        cedict_file.write_text(
            "你好 你好 [ni3 hao3] /hello/\n"
            "你好 你好 [ni3 hao3] /hello/\n",
            encoding="utf-8",
        )

        conn = get_connection()
        init_db(conn)
        load_cedict(conn, cedict_file)

        count = conn.execute("SELECT COUNT(*) FROM cedict").fetchone()[0]
        assert count == 1
        conn.close()

    def test_load_real_cedict(self):
        """Load the actual CC-CEDICT file if available."""
        cedict_path = Path("data/raw/cedict_1_0_ts_utf-8_mdbg.txt")
        if not cedict_path.exists():
            pytest.skip("CC-CEDICT file not downloaded yet")

        conn = get_connection()
        init_db(conn)
        count = load_cedict(conn, cedict_path)

        assert count > 120000, f"Expected 120K+ entries, got {count}"

        # Spot-check some entries
        row = conn.execute(
            "SELECT * FROM cedict WHERE simplified = '银行'"
        ).fetchone()
        assert row is not None

        row = conn.execute(
            "SELECT * FROM cedict WHERE simplified = '长城'"
        ).fetchone()
        assert row is not None
        assert row["traditional"] == "長城"

        conn.close()
