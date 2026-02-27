"""Tests for classical Chinese text importers."""

import json
import sqlite3
from pathlib import Path

import pytest

from zhcorpus.db import get_connection, init_db
from zhcorpus.ingest.classics import (
    import_classics,
    iter_niutrans_bilingual,
    iter_niutrans_raw,
    iter_poetry_json,
)


@pytest.fixture
def zhcorpus_db():
    conn = get_connection()
    init_db(conn)
    yield conn
    conn.close()


# ---- Mock NiuTrans directory ----

def _make_mock_niutrans(tmp_path: Path) -> Path:
    """Create a mock NiuTrans/Classical-Modern directory."""
    base = tmp_path / "Classical-Modern"

    # Bilingual: 论语/学而篇
    chapter = base / "双语数据" / "论语" / "学而篇"
    chapter.mkdir(parents=True)
    (chapter / "source.txt").write_text(
        "子曰：学而时习之，不亦说乎？\n"
        "有朋自远方来，不亦乐乎？\n"
        "人不知而不愠，不亦君子乎？\n",
        encoding="utf-8",
    )
    (chapter / "target.txt").write_text(
        "孔子说：学了又时常温习，不是很愉快吗？\n",
        encoding="utf-8",
    )

    # Bilingual: 道德经/第一章
    chapter2 = base / "双语数据" / "道德经" / "第一章"
    chapter2.mkdir(parents=True)
    (chapter2 / "source.txt").write_text(
        "道可道，非常道。名可名，非常名。\n"
        "无名天地之始；有名万物之母。\n",
        encoding="utf-8",
    )

    # Raw only: 红楼梦/第一回 (not in bilingual)
    chapter3 = base / "古文原文" / "红楼梦" / "第一回"
    chapter3.mkdir(parents=True)
    (chapter3 / "text.txt").write_text(
        "甄士隐梦幻识通灵贾雨村风尘怀闺秀。"
        "此开卷第一回也。作者自云：因曾历过一番梦幻之后，故将真事隐去。",
        encoding="utf-8",
    )

    # Raw: 论语 (should be skipped — already in bilingual)
    chapter4 = base / "古文原文" / "论语" / "学而篇"
    chapter4.mkdir(parents=True)
    (chapter4 / "text.txt").write_text("duplicate", encoding="utf-8")

    return base


# ---- Mock chinese-poetry directory ----

def _make_mock_poetry(tmp_path: Path) -> Path:
    """Create a mock chinese-poetry directory."""
    base = tmp_path / "chinese-poetry"

    # Tang poetry
    tang_dir = base / "全唐诗"
    tang_dir.mkdir(parents=True)
    (tang_dir / "poet.tang.0.json").write_text(
        json.dumps([
            {
                "author": "李白",
                "title": "静夜思",
                "paragraphs": ["床前明月光，", "疑是地上霜。", "举头望明月，", "低头思故乡。"],
                "id": "test-1",
            },
            {
                "author": "杜甫",
                "title": "春望",
                "paragraphs": ["国破山河在，", "城春草木深。"],
                "id": "test-2",
            },
        ], ensure_ascii=False),
        encoding="utf-8",
    )

    # Chuci
    chuci_dir = base / "楚辞"
    chuci_dir.mkdir(parents=True)
    (chuci_dir / "chuci.json").write_text(
        json.dumps([
            {
                "title": "离骚",
                "section": "屈原",
                "content": ["帝高阳之苗裔兮，朕皇考曰伯庸。", "摄提贞于孟陬兮，惟庚寅吾以降。"],
            }
        ], ensure_ascii=False),
        encoding="utf-8",
    )

    # 四书五经
    classics_dir = base / "四书五经"
    classics_dir.mkdir(parents=True)
    (classics_dir / "daxue.json").write_text(
        json.dumps([
            {"chapter": "经一章", "paragraphs": ["大学之道，在明明德，在亲民，在止于至善。"]},
        ], ensure_ascii=False),
        encoding="utf-8",
    )

    # 蒙学
    mengxue_dir = base / "蒙学"
    mengxue_dir.mkdir(parents=True)
    (mengxue_dir / "tangshisanbaishou.json").write_text(
        json.dumps([
            {"author": "张九龄", "title": "感遇·其一", "paragraphs": ["兰叶春葳蕤，桂华秋皎洁。"]},
        ], ensure_ascii=False),
        encoding="utf-8",
    )

    return base


# ---- Tests ----

class TestIterNiutransBilingual:
    def test_reads_source_txt(self, tmp_path):
        base = _make_mock_niutrans(tmp_path)
        articles = list(iter_niutrans_bilingual(base))
        assert len(articles) == 2  # 论语 + 道德经
        titles = [a[1] for a in articles]
        assert any("论语" in t for t in titles)
        assert any("道德经" in t for t in titles)

    def test_text_content(self, tmp_path):
        base = _make_mock_niutrans(tmp_path)
        articles = list(iter_niutrans_bilingual(base))
        lunyu = [a for a in articles if "论语" in a[1]][0]
        assert "学而时习之" in lunyu[2]


class TestIterNiutransRaw:
    def test_skips_bilingual_books(self, tmp_path):
        base = _make_mock_niutrans(tmp_path)
        articles = list(iter_niutrans_raw(base))
        # 论语 should be skipped (it's in bilingual), only 红楼梦 should appear
        assert len(articles) == 1
        assert "红楼梦" in articles[0][1]

    def test_raw_text_content(self, tmp_path):
        base = _make_mock_niutrans(tmp_path)
        articles = list(iter_niutrans_raw(base))
        assert "甄士隐" in articles[0][2]


class TestIterPoetryJson:
    def test_reads_tang_poetry(self, tmp_path):
        base = _make_mock_poetry(tmp_path)
        articles = list(iter_poetry_json(base))
        tang = [a for a in articles if "李白" in a[1]]
        assert len(tang) >= 1
        assert "床前明月光" in tang[0][2]

    def test_reads_chuci(self, tmp_path):
        base = _make_mock_poetry(tmp_path)
        articles = list(iter_poetry_json(base))
        chuci = [a for a in articles if "离骚" in a[1]]
        assert len(chuci) >= 1
        assert "高阳" in chuci[0][2]

    def test_reads_classics(self, tmp_path):
        base = _make_mock_poetry(tmp_path)
        articles = list(iter_poetry_json(base))
        daxue = [a for a in articles if "大学" in a[1] or "经一章" in a[1]]
        assert len(daxue) >= 1

    def test_reads_mengxue(self, tmp_path):
        base = _make_mock_poetry(tmp_path)
        articles = list(iter_poetry_json(base))
        tssbs = [a for a in articles if "感遇" in a[1]]
        assert len(tssbs) >= 1


class TestImportClassics:
    def test_import_niutrans(self, zhcorpus_db, tmp_path):
        base = _make_mock_niutrans(tmp_path)
        articles, chunks = import_classics(zhcorpus_db, niutrans_dir=base)
        assert articles == 3  # 2 bilingual + 1 raw-only
        assert chunks >= 3

        row = zhcorpus_db.execute(
            "SELECT * FROM sources WHERE name = 'classics_prose'"
        ).fetchone()
        assert row is not None

    def test_import_poetry(self, zhcorpus_db, tmp_path):
        base = _make_mock_poetry(tmp_path)
        articles, chunks = import_classics(zhcorpus_db, poetry_dir=base)
        assert articles >= 4  # tang x2, chuci, daxue, mengxue
        assert chunks >= 4

    def test_import_both(self, zhcorpus_db, tmp_path):
        niutrans = _make_mock_niutrans(tmp_path)
        poetry = _make_mock_poetry(tmp_path)
        articles, chunks = import_classics(
            zhcorpus_db, niutrans_dir=niutrans, poetry_dir=poetry
        )
        assert articles >= 7  # 3 prose + 4+ poetry

        sources = zhcorpus_db.execute("SELECT name FROM sources").fetchall()
        source_names = {s["name"] for s in sources}
        assert "classics_prose" in source_names
        assert "classics_poetry" in source_names

    def test_chunks_searchable(self, zhcorpus_db, tmp_path):
        niutrans = _make_mock_niutrans(tmp_path)
        import_classics(zhcorpus_db, niutrans_dir=niutrans)

        rows = zhcorpus_db.execute(
            'SELECT COUNT(*) AS n FROM chunks_fts WHERE chunks_fts MATCH simple_query(?)',
            ("学而时习",),
        ).fetchone()
        assert rows["n"] >= 1

    def test_import_with_limit(self, zhcorpus_db, tmp_path):
        niutrans = _make_mock_niutrans(tmp_path)
        articles, chunks = import_classics(
            zhcorpus_db, niutrans_dir=niutrans, limit=1
        )
        assert articles == 1


class TestImportRealClassics:
    """Integration tests against the real cloned repos."""

    @pytest.fixture
    def niutrans_path(self):
        path = Path("/home/tim/Projects/loqu8/zhcorpus/data/raw/Classical-Modern")
        if not path.exists():
            pytest.skip("NiuTrans/Classical-Modern not cloned")
        return path

    @pytest.fixture
    def poetry_path(self):
        path = Path("/home/tim/Projects/loqu8/zhcorpus/data/raw/chinese-poetry")
        if not path.exists():
            pytest.skip("chinese-poetry not cloned")
        return path

    def test_niutrans_has_key_texts(self, niutrans_path):
        articles = list(iter_niutrans_bilingual(niutrans_path))
        titles = " ".join(a[1] for a in articles)
        assert "论语" in titles
        assert "老子" in titles
        assert "史记" in titles
        assert len(articles) > 500  # Many chapters across 97 books

    def test_niutrans_raw_has_novels(self, niutrans_path):
        articles = list(iter_niutrans_raw(niutrans_path))
        titles = " ".join(a[1] for a in articles)
        # These should be in raw-only (not bilingual)
        assert len(articles) > 100

    def test_poetry_has_tang_poems(self, poetry_path):
        articles = list(iter_poetry_json(poetry_path))
        assert len(articles) > 10000  # 55K+ Tang poems alone

    def test_import_sample(self, zhcorpus_db, niutrans_path, poetry_path):
        articles, chunks = import_classics(
            zhcorpus_db,
            niutrans_dir=niutrans_path,
            poetry_dir=poetry_path,
            limit=200,
        )
        assert articles == 200
        assert chunks > 200

        from zhcorpus.search.fts import search_fts
        results = search_fts(zhcorpus_db, "子曰")
        assert len(results) >= 1
