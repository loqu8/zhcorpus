"""Tests for corpus extraction from cedict-backfill database."""

import sqlite3
from pathlib import Path

import pytest

from zhcorpus.db import get_connection, init_db
from zhcorpus.ingest.corpus_extract import (
    _clean_chid_text,
    import_source,
    iter_source_articles,
    SOURCE_MAP,
)


# ---- Fixtures: mock cedict-backfill database ----

def _make_mock_backfill_db() -> sqlite3.Connection:
    """Create a mock cedict-backfill database with sample data."""
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE corpus_texts (
            id INTEGER PRIMARY KEY,
            source TEXT,
            source_id TEXT,
            title TEXT,
            text TEXT,
            metadata TEXT,
            created_at TEXT
        )
    """)

    # Wikipedia articles
    conn.execute(
        "INSERT INTO corpus_texts (source, title, text) VALUES (?, ?, ?)",
        ("wikipedia", "银行", "银行是一种金融机构。商业银行的主要业务是吸收公众存款、发放贷款和办理结算。"
         "中国银行业监督管理委员会负责对银行业实施监管。"),
    )
    conn.execute(
        "INSERT INTO corpus_texts (source, title, text) VALUES (?, ?, ?)",
        ("wikipedia", "选任制", "选任制是指通过选举方式任用干部的制度。选任制度在中国有悠久的历史。"),
    )

    # Baidu Baike articles
    conn.execute(
        "INSERT INTO corpus_texts (source, title, text) VALUES (?, ?, ?)",
        ("baidu_baike", "长城", "长城是中国古代的军事防御工程。长城修筑的历史可上溯到西周时期。"),
    )

    # ChID with #idiom# markers
    conn.execute(
        "INSERT INTO corpus_texts (source, title, text) VALUES (?, ?, ?)",
        ("chid_train", None, "他做事总是#idiom#，从来不考虑后果。最终他为自己的行为付出了代价。"),
    )
    conn.execute(
        "INSERT INTO corpus_texts (source, title, text) VALUES (?, ?, ?)",
        ("chid_test", None, "这个故事#idiom#，告诉我们做事不能急于求成。"),
    )

    conn.commit()
    return conn


@pytest.fixture
def mock_backfill_db():
    conn = _make_mock_backfill_db()
    yield conn
    conn.close()


@pytest.fixture
def zhcorpus_db():
    conn = get_connection()
    init_db(conn)
    yield conn
    conn.close()


# ---- Tests ----

class TestCleanChid:
    """ChID #idiom# marker stripping."""

    def test_strips_idiom_marker(self):
        assert _clean_chid_text("他#idiom#了") == "他了"

    def test_strips_numbered_marker(self):
        assert _clean_chid_text("他#idiom0#和#idiom1#") == "他和"

    def test_no_markers(self):
        text = "这是正常文本。"
        assert _clean_chid_text(text) == text


class TestIterSourceArticles:
    """Iterate articles from a specific source."""

    def test_iter_wikipedia(self, mock_backfill_db):
        articles = list(iter_source_articles(mock_backfill_db, "wikipedia"))
        assert len(articles) == 2
        ids, titles, texts = zip(*articles)
        assert "银行" in titles
        assert "选任制" in titles

    def test_iter_baike(self, mock_backfill_db):
        articles = list(iter_source_articles(mock_backfill_db, "baidu_baike"))
        assert len(articles) == 1
        assert articles[0][1] == "长城"

    def test_iter_chid_strips_markers(self, mock_backfill_db):
        articles = list(iter_source_articles(mock_backfill_db, "chid_train"))
        assert len(articles) == 1
        # Marker should be stripped
        assert "#idiom#" not in articles[0][2]

    def test_iter_with_limit(self, mock_backfill_db):
        articles = list(iter_source_articles(mock_backfill_db, "wikipedia", limit=1))
        assert len(articles) == 1

    def test_iter_empty_source(self, mock_backfill_db):
        articles = list(iter_source_articles(mock_backfill_db, "nonexistent"))
        assert len(articles) == 0


class TestImportSource:
    """Import a source into zhcorpus."""

    def test_import_wikipedia(self, zhcorpus_db, mock_backfill_db):
        articles, chunks = import_source(
            zhcorpus_db, mock_backfill_db, "wikipedia", "Chinese Wikipedia"
        )
        assert articles == 2
        assert chunks >= 2  # At least one chunk per article

        # Verify source was created
        row = zhcorpus_db.execute(
            "SELECT * FROM sources WHERE name = 'wikipedia'"
        ).fetchone()
        assert row is not None
        assert row["article_count"] == 2

    def test_import_baike(self, zhcorpus_db, mock_backfill_db):
        articles, chunks = import_source(
            zhcorpus_db, mock_backfill_db, "baidu_baike", "Baidu Baike"
        )
        assert articles == 1
        assert chunks >= 1

    def test_import_chid_merges_sources(self, zhcorpus_db, mock_backfill_db):
        """chid_train and chid_test both map to 'chid' source."""
        a1, c1 = import_source(zhcorpus_db, mock_backfill_db, "chid_train")
        a2, c2 = import_source(zhcorpus_db, mock_backfill_db, "chid_test")

        # Both should map to the same source
        sources = zhcorpus_db.execute("SELECT * FROM sources WHERE name = 'chid'").fetchall()
        assert len(sources) == 1

    def test_chunks_are_searchable(self, zhcorpus_db, mock_backfill_db):
        """Imported chunks appear in FTS5 index."""
        import_source(zhcorpus_db, mock_backfill_db, "wikipedia")

        # FTS5 search via simple_query
        rows = zhcorpus_db.execute(
            'SELECT COUNT(*) AS n FROM chunks_fts WHERE chunks_fts MATCH simple_query(?)',
            ("金融机构",),
        ).fetchone()
        assert rows["n"] >= 1

    def test_progress_callback(self, zhcorpus_db, mock_backfill_db):
        """Progress callback is called."""
        calls = []
        import_source(
            zhcorpus_db, mock_backfill_db, "wikipedia",
            batch_size=1,
            progress_fn=lambda a, c: calls.append((a, c)),
        )
        assert len(calls) >= 1

    def test_source_map_coverage(self):
        """All expected cedict-backfill sources are mapped."""
        expected = {"wikipedia", "baidu_baike", "chid_train", "chid_test", "chid_validation"}
        assert expected == set(SOURCE_MAP.keys())


class TestImportFromRealDb:
    """Integration tests against the real cedict-backfill database."""

    @pytest.fixture
    def backfill_db_path(self):
        path = Path("/home/tim/Projects/loqu8/cedict-backfill/data/artifacts/jieba_candidates.db")
        if not path.exists():
            pytest.skip("cedict-backfill database not available")
        return path

    def test_import_wikipedia_sample(self, zhcorpus_db, backfill_db_path):
        """Import a small sample of Wikipedia articles."""
        src_conn = sqlite3.connect(str(backfill_db_path))
        src_conn.row_factory = sqlite3.Row

        articles, chunks = import_source(
            zhcorpus_db, src_conn, "wikipedia", "Chinese Wikipedia", limit=100
        )

        assert articles == 100
        assert chunks > 100  # Multiple chunks per article

        # Verify FTS5 works
        from zhcorpus.search.fts import search_fts
        # Search for something that should be in Wikipedia
        results = search_fts(zhcorpus_db, "中国")
        assert len(results) >= 1

        src_conn.close()
