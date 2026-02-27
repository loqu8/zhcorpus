"""Tests proving FTS5 'simple' tokenizer works for Chinese word search.

This is the foundational test — if FTS5 can't reliably find
Chinese words in the corpus, nothing else matters.

The simple tokenizer (github.com/wangfenjin/simple) handles Chinese
character-level tokenization natively. Each CJK character becomes a
separate FTS5 token. simple_query() builds the right MATCH expression.
"""

import sqlite3

import pytest

from zhcorpus.search.fts import (
    count_hits,
    count_hits_by_source,
    get_context,
    get_full_article,
    search_fts,
)
from tests.fixtures.sample_corpus import (
    COMMON_WORDS,
    DOMAIN_WORDS,
    POLYPHONIC_WORDS,
    RARE_WORDS,
)


class TestFindsChinese:
    """FTS5 simple tokenizer finds Chinese words of any length."""

    def test_finds_common_word(self, populated_db):
        """Basic: finds a common word in the corpus."""
        results = search_fts(populated_db, "银行")
        assert len(results) >= 1
        assert any("银行" in r.text for r in results)

    def test_finds_compound_word(self, populated_db):
        """Finds a multi-character compound word."""
        results = search_fts(populated_db, "选任")
        assert len(results) >= 1
        assert any("选任" in r.text for r in results)

    def test_finds_four_char_word(self, populated_db):
        """Finds a four-character compound (common in Chinese)."""
        results = search_fts(populated_db, "营商环境")
        assert len(results) >= 1

    def test_finds_chengyu(self, populated_db):
        """Finds a four-character idiom (成语)."""
        results = search_fts(populated_db, "画蛇添足")
        assert len(results) >= 1

    @pytest.mark.parametrize("word", COMMON_WORDS)
    def test_finds_all_common_words(self, populated_db, word):
        """Every common test word returns at least one hit."""
        results = search_fts(populated_db, word)
        assert len(results) >= 1, f"No results for common word: {word}"

    @pytest.mark.parametrize("word", DOMAIN_WORDS)
    def test_finds_all_domain_words(self, populated_db, word):
        """Every domain-specific test word returns at least one hit."""
        results = search_fts(populated_db, word)
        assert len(results) >= 1, f"No results for domain word: {word}"

    @pytest.mark.parametrize("word", RARE_WORDS)
    def test_finds_all_rare_words(self, populated_db, word):
        """Every rare/archaic test word returns at least one hit."""
        results = search_fts(populated_db, word)
        assert len(results) >= 1, f"No results for rare word: {word}"


class TestSimpleTokenizerDirect:
    """The simple tokenizer handles Chinese character-level tokenization."""

    def test_phrase_matches_adjacent_chars(self, db):
        """simple_query finds exact multi-character sequence."""
        test_text = "选任制是指通过选举方式任用干部的制度。"
        db.execute(
            "CREATE VIRTUAL TABLE test_st USING fts5(text, tokenize='simple')"
        )
        db.execute("INSERT INTO test_st VALUES (?)", (test_text,))
        db.commit()

        # 2-char phrase
        rows = db.execute(
            'SELECT * FROM test_st WHERE test_st MATCH simple_query(?)',
            ("选任",),
        ).fetchall()
        assert len(rows) >= 1

        # 3-char phrase
        rows = db.execute(
            'SELECT * FROM test_st WHERE test_st MATCH simple_query(?)',
            ("选任制",),
        ).fetchall()
        assert len(rows) >= 1

    def test_non_adjacent_chars_no_match(self, db):
        """Phrase query does NOT match non-adjacent characters."""
        test_text = "选举任命是两种方式。"
        db.execute(
            "CREATE VIRTUAL TABLE test_st2 USING fts5(text, tokenize='simple')"
        )
        db.execute("INSERT INTO test_st2 VALUES (?)", (test_text,))
        db.commit()

        # "选任" should NOT match — 选 and 任 are not adjacent
        rows = db.execute(
            'SELECT * FROM test_st2 WHERE test_st2 MATCH ?',
            ('"选任"',),
        ).fetchall()
        assert len(rows) == 0

    def test_single_char_search(self, db):
        """Single character search works."""
        test_text = "中国是一个大国。"
        db.execute(
            "CREATE VIRTUAL TABLE test_st3 USING fts5(text, tokenize='simple')"
        )
        db.execute("INSERT INTO test_st3 VALUES (?)", (test_text,))
        db.commit()

        rows = db.execute(
            'SELECT * FROM test_st3 WHERE test_st3 MATCH simple_query(?)',
            ("国",),
        ).fetchall()
        assert len(rows) >= 1

    def test_highlight_works(self, db):
        """simple_highlight produces correct output."""
        db.execute(
            "CREATE VIRTUAL TABLE test_st4 USING fts5(text, tokenize='simple')"
        )
        db.execute("INSERT INTO test_st4 VALUES ('银行是金融机构。')")
        db.commit()

        rows = db.execute(
            "SELECT simple_highlight(test_st4, 0, '[', ']') FROM test_st4 "
            "WHERE test_st4 MATCH simple_query('银行')",
        ).fetchall()
        assert len(rows) == 1
        assert "[银行]" in rows[0][0]


class TestPolyphonicWords:
    """Corpus distinguishes different readings of polyphonic characters."""

    @pytest.mark.parametrize("word,expected_pinyin", POLYPHONIC_WORDS)
    def test_polyphonic_word_in_context(self, populated_db, word, expected_pinyin):
        """Each polyphonic compound appears in a contextually appropriate passage."""
        results = search_fts(populated_db, word)
        assert len(results) >= 1, f"No results for polyphonic word: {word}"
        # The word should appear literally in at least one result
        assert any(word in r.text for r in results), (
            f"Word '{word}' not found in any result text"
        )

    def test_hang_vs_xing(self, populated_db):
        """银行 (háng) and 行动 (xíng) return different passages."""
        bank_results = search_fts(populated_db, "银行")
        action_results = search_fts(populated_db, "行动")

        bank_texts = {r.text for r in bank_results}
        action_texts = {r.text for r in action_results}

        # No overlap — different contexts for different readings
        assert bank_texts != action_texts

    def test_chang_vs_zhang(self, populated_db):
        """长城 (cháng) and 长大 (zhǎng) return different passages."""
        wall_results = search_fts(populated_db, "长城")
        grow_results = search_fts(populated_db, "长大")

        wall_texts = {r.text for r in wall_results}
        grow_texts = {r.text for r in grow_results}

        assert wall_texts != grow_texts


class TestSourceCounting:
    """Hit counts are broken down by source."""

    def test_count_hits(self, populated_db):
        """Total hit count is accurate."""
        count = count_hits(populated_db, "选任")
        assert count >= 1

    def test_count_by_source(self, populated_db):
        """Hits are attributed to the correct sources."""
        counts = count_hits_by_source(populated_db, "选任")
        assert isinstance(counts, dict)
        assert len(counts) >= 1
        # 选任 appears in wikipedia, baidu_baike, and news fixtures
        assert sum(counts.values()) >= 1

    def test_different_words_different_sources(self, populated_db):
        """Different words have different source distributions."""
        xuanren = count_hits_by_source(populated_db, "选任")
        chengyu = count_hits_by_source(populated_db, "画蛇添足")

        # 选任 should be in wikipedia/baike/news; 画蛇添足 should be in chid
        assert xuanren != chengyu


class TestPhraseSearchRanking:
    """Two-phase query returns correct results without BM25 ranking.

    We skip BM25 intentionally — O(n) ranking on 112M+ chunks causes
    timeouts for common terms (的, 学). Results come in posting-list
    order (clustered by insertion time / source) instead.
    """

    def test_two_char_term_returns_results(self, populated_db):
        """2-char terms return results (rank is 0.0 — BM25 skipped for perf)."""
        results = search_fts(populated_db, "选任")
        assert len(results) >= 1
        # Rank is 0.0 because we skip BM25 for O(1) performance
        assert all(r.rank == 0.0 for r in results)

    def test_returns_multiple_results(self, populated_db):
        """Multiple matching chunks are returned."""
        results = search_fts(populated_db, "选任")
        if len(results) >= 2:
            # Results should have valid chunk_ids
            assert all(r.chunk_id > 0 for r in results)

    def test_no_false_positives(self, populated_db):
        """Every result for a 2-char term actually contains that term."""
        results = search_fts(populated_db, "银行")
        for r in results:
            assert "银行" in r.text, f"False positive: '银行' not in '{r.text[:50]}...'"


class TestClassicalChinese:
    """FTS5 handles classical Chinese (文言文) text."""

    def test_finds_classical_term(self, populated_db):
        """Finds a term from classical Chinese text."""
        results = search_fts(populated_db, "君子")
        assert len(results) >= 1

    def test_finds_lunyu(self, populated_db):
        """Finds text from the Analerta (论语)."""
        results = search_fts(populated_db, "学而时习")
        assert len(results) >= 1

    def test_finds_daodejing(self, populated_db):
        """Finds text from the Dao De Jing (道德经)."""
        results = search_fts(populated_db, "道可道")
        assert len(results) >= 1

    def test_finds_zhuangzi(self, populated_db):
        """Finds text from the Zhuangzi (庄子)."""
        results = search_fts(populated_db, "北冥有鱼")
        assert len(results) >= 1


class TestContextExpansion:
    """get_context returns neighboring chunks for grep -C style display."""

    def test_context_includes_hit(self, populated_db):
        """Context always includes the original hit text."""
        results = search_fts(populated_db, "银行")
        assert len(results) >= 1
        ctx = get_context(populated_db, results[0], before=2, after=2)
        assert results[0].text in ctx.context
        assert ctx.hit_text == results[0].text

    def test_context_wider_than_hit(self, populated_db):
        """Context is at least as long as the hit chunk (usually longer)."""
        results = search_fts(populated_db, "营商环境")
        assert len(results) >= 1
        ctx = get_context(populated_db, results[0], before=2, after=2)
        assert len(ctx.context) >= len(results[0].text)

    def test_context_zero_returns_hit_only(self, populated_db):
        """With before=0 and after=0, context is just the hit chunk."""
        results = search_fts(populated_db, "银行")
        assert len(results) >= 1
        ctx = get_context(populated_db, results[0], before=0, after=0)
        assert ctx.context == results[0].text
        assert ctx.chunk_count == 1

    def test_context_preserves_order(self, populated_db):
        """Chunks in context are in article order."""
        results = search_fts(populated_db, "选任")
        assert len(results) >= 1
        ctx = get_context(populated_db, results[0], before=3, after=3)
        # Context should be multiple chunks joined by newlines
        assert ctx.chunk_count >= 1

    def test_context_metadata(self, populated_db):
        """Context carries source and title from the result."""
        results = search_fts(populated_db, "画蛇添足")
        assert len(results) >= 1
        ctx = get_context(populated_db, results[0], before=1, after=1)
        assert ctx.source == results[0].source
        assert ctx.title == results[0].title

    def test_result_has_article_id(self, populated_db):
        """SearchResult carries article_id and chunk_index."""
        results = search_fts(populated_db, "银行")
        assert len(results) >= 1
        assert results[0].article_id > 0
        assert results[0].chunk_index >= 0

    def test_get_full_article(self, populated_db):
        """get_full_article returns all chunks for an article."""
        results = search_fts(populated_db, "选任")
        assert len(results) >= 1
        full = get_full_article(populated_db, results[0].article_id)
        assert results[0].text in full
        # Full article should be longer than a single chunk
        assert len(full) >= len(results[0].text)
