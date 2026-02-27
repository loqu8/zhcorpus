"""Tests for news corpus importers."""

import json
import sqlite3
from pathlib import Path

import pytest

from zhcorpus.db import get_connection, init_db
from zhcorpus.ingest.news import (
    import_news_iter,
    iter_news2016zh,
    iter_thucnews_hf,
    THUCNEWS_CATEGORIES,
)


@pytest.fixture
def zhcorpus_db():
    conn = get_connection()
    init_db(conn)
    yield conn
    conn.close()


class TestIterNews2016zh:
    """Parse news2016zh JSONL format."""

    def test_reads_jsonl(self, tmp_path):
        jsonl_file = tmp_path / "news.json"
        jsonl_file.write_text(
            json.dumps({"news_id": "1", "title": "测试新闻", "content": "这是一条测试新闻的正文。内容很丰富。"}) + "\n"
            + json.dumps({"news_id": "2", "title": "科技新闻", "content": "人工智能技术取得重大突破。研究人员表示这一成果意义深远。"}) + "\n",
            encoding="utf-8",
        )
        articles = list(iter_news2016zh(jsonl_file))
        assert len(articles) == 2
        assert articles[0][0] == "1"
        assert articles[0][1] == "测试新闻"
        assert "测试新闻" in articles[0][2]

    def test_skips_empty_content(self, tmp_path):
        jsonl_file = tmp_path / "news.json"
        jsonl_file.write_text(
            json.dumps({"news_id": "1", "title": "标题", "content": ""}) + "\n"
            + json.dumps({"news_id": "2", "title": "有内容", "content": "有内容的文章。"}) + "\n",
            encoding="utf-8",
        )
        articles = list(iter_news2016zh(jsonl_file))
        assert len(articles) == 1

    def test_skips_malformed_json(self, tmp_path):
        jsonl_file = tmp_path / "news.json"
        jsonl_file.write_text(
            '{"news_id": "1", "title": "好的", "content": "正文。"}\n'
            'not valid json\n'
            '{"news_id": "2", "title": "也好", "content": "正文二。"}\n',
            encoding="utf-8",
        )
        articles = list(iter_news2016zh(jsonl_file))
        assert len(articles) == 2


class TestIterThucnewsHf:
    """Parse THUCNews from a HuggingFace-like dataset."""

    def test_reads_dataset(self):
        # Simulate HuggingFace dataset as list of dicts
        mock_dataset = [
            {"title": "股市大涨", "content": "今日股市全面上涨。上证指数涨幅达到百分之三。", "label": "股票"},
            {"title": "足球比赛", "content": "中国队在世界杯预选赛中获胜。球迷们为之欢呼。", "label": "体育"},
        ]
        articles = list(iter_thucnews_hf(mock_dataset))
        assert len(articles) == 2
        assert articles[0][1] == "股市大涨"

    def test_skips_empty_content(self):
        mock_dataset = [
            {"title": "空文章", "content": "", "label": "科技"},
            {"title": "有内容", "content": "正文内容。", "label": "科技"},
        ]
        articles = list(iter_thucnews_hf(mock_dataset))
        # iter_thucnews_hf skips empty content
        assert len(articles) == 1
        assert articles[0][1] == "有内容"


class TestImportNewsIter:
    """Import news articles from an iterator."""

    def _make_articles(self, n=5):
        """Generate n fake news articles."""
        for i in range(n):
            yield (
                str(i),
                f"新闻标题{i}",
                f"这是第{i}条新闻的正文内容。新闻报道了一些重要的事件。相关部门表示将继续关注。"
            )

    def test_import_basic(self, zhcorpus_db):
        articles, chunks = import_news_iter(
            zhcorpus_db, "test_news", "Test news source",
            self._make_articles(5),
        )
        assert articles == 5
        assert chunks >= 5

        row = zhcorpus_db.execute(
            "SELECT * FROM sources WHERE name = 'test_news'"
        ).fetchone()
        assert row["article_count"] == 5

    def test_import_with_limit(self, zhcorpus_db):
        articles, chunks = import_news_iter(
            zhcorpus_db, "test_news", "Test",
            self._make_articles(10),
            limit=3,
        )
        assert articles == 3

    def test_chunks_in_fts_index(self, zhcorpus_db):
        import_news_iter(
            zhcorpus_db, "test_news", "Test",
            self._make_articles(3),
        )
        rows = zhcorpus_db.execute(
            'SELECT COUNT(*) AS n FROM chunks_fts WHERE chunks_fts MATCH simple_query(?)',
            ("新闻报道",),
        ).fetchone()
        assert rows["n"] >= 1

    def test_progress_callback(self, zhcorpus_db):
        calls = []
        import_news_iter(
            zhcorpus_db, "test_news", "Test",
            self._make_articles(5),
            batch_size=2,
            progress_fn=lambda a, c: calls.append((a, c)),
        )
        assert len(calls) >= 1

    def test_category_map_exists(self):
        """THUCNews category mapping covers expected categories."""
        assert len(THUCNEWS_CATEGORIES) == 14
        assert "财经" in THUCNEWS_CATEGORIES
        assert "科技" in THUCNEWS_CATEGORIES
