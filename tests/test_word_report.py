"""Tests for the Word Report builder — the core deliverable."""

import pytest

from zhcorpus.db import get_connection, init_db
from zhcorpus.report import build_word_report, WordReport


class TestWordReportStructure:
    """The word report has all expected sections."""

    def test_has_required_fields(self, populated_db):
        report = build_word_report(populated_db, "选任")
        assert isinstance(report, WordReport)
        assert report.term == "选任"
        assert report.total_hits >= 1
        assert len(report.sources) >= 1
        assert isinstance(report.best_snippets, list)
        assert isinstance(report.cedict_entries, list)

    def test_serializes_to_dict(self, populated_db):
        report = build_word_report(populated_db, "选任")
        d = report.to_dict()
        assert d["term"] == "选任"
        assert "total_hits" in d
        assert "sources" in d
        assert "cedict_entries" in d
        assert "best_snippets" in d
        assert "pinyin_suggestion" in d


class TestPerSourceBreakdown:
    """Report shows hits broken down by source."""

    def test_sources_have_counts(self, populated_db):
        report = build_word_report(populated_db, "选任")
        for source in report.sources:
            assert source.name
            assert source.hit_count >= 1

    def test_sources_have_snippets(self, populated_db):
        report = build_word_report(populated_db, "选任")
        for source in report.sources:
            assert len(source.best_snippets) >= 1

    def test_multiple_sources(self, populated_db):
        """选任 appears in wikipedia, baidu_baike, and news."""
        report = build_word_report(populated_db, "选任")
        source_names = {s.name for s in report.sources}
        # Should appear in at least 2 different sources
        assert len(source_names) >= 2

    def test_sources_sorted_by_count(self, populated_db):
        report = build_word_report(populated_db, "选任")
        counts = [s.hit_count for s in report.sources]
        assert counts == sorted(counts, reverse=True)


class TestCedictCrossReference:
    """Report includes CEDICT entries when they exist."""

    def test_no_cedict_for_missing_word(self, populated_db):
        """选任 is not in CEDICT (that's why we're defining it)."""
        report = build_word_report(populated_db, "选任")
        assert report.cedict_entries == []

    def test_cedict_found_when_present(self, populated_db):
        """If we add a CEDICT entry, the report finds it."""
        populated_db.execute(
            "INSERT INTO cedict (traditional, simplified, pinyin, definition) "
            "VALUES (?, ?, ?, ?)",
            ("銀行", "银行", "yin2 hang2", "bank/CL:家[jia1],個|个[ge4]"),
        )
        populated_db.commit()

        report = build_word_report(populated_db, "银行")
        assert len(report.cedict_entries) >= 1
        assert report.cedict_entries[0].pinyin == "yin2 hang2"
        assert "bank" in report.cedict_entries[0].definition


class TestBestSnippets:
    """The report picks the best snippets across all sources."""

    def test_has_snippets(self, populated_db):
        report = build_word_report(populated_db, "选任")
        assert len(report.best_snippets) >= 1

    def test_snippets_contain_term(self, populated_db):
        report = build_word_report(populated_db, "选任")
        for snippet in report.best_snippets:
            assert "选任" in snippet["text"]

    def test_snippets_have_source_attribution(self, populated_db):
        report = build_word_report(populated_db, "选任")
        for snippet in report.best_snippets:
            assert "source" in snippet
            assert "title" in snippet
            assert "text" in snippet


class TestWordReportForDifferentTiers:
    """Reports work across all difficulty tiers."""

    def test_common_word(self, populated_db):
        report = build_word_report(populated_db, "银行")
        assert report.total_hits >= 1

    def test_domain_word(self, populated_db):
        report = build_word_report(populated_db, "辨证论治")
        assert report.total_hits >= 1

    def test_classical_word(self, populated_db):
        report = build_word_report(populated_db, "君子")
        assert report.total_hits >= 1

    def test_chengyu(self, populated_db):
        report = build_word_report(populated_db, "守株待兔")
        assert report.total_hits >= 1

    def test_no_hits_word(self, populated_db):
        """A word not in the corpus returns an empty report gracefully."""
        report = build_word_report(populated_db, "不存在的词")
        assert report.total_hits == 0
        assert report.sources == []
        assert report.best_snippets == []


class TestWordReportClassicalChinese:
    """Reports work for classical Chinese terms."""

    def test_classical_passage(self, populated_db):
        report = build_word_report(populated_db, "窈窕淑女")
        assert report.total_hits >= 1
        assert any("classical" in s.name for s in report.sources)

    def test_philosophical_term(self, populated_db):
        report = build_word_report(populated_db, "逍遥游")
        assert report.total_hits >= 1
