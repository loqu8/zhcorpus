"""Tests for the MCP server tool functions.

Tests tool functions directly (not via MCP transport) using in-memory
databases populated with sample fixtures.
"""

import asyncio
import sqlite3

import pytest

from zhcorpus.db import get_connection, init_db, ensure_source, insert_article, insert_chunk
from zhcorpus.ingest.chunker import chunk_text
from zhcorpus.mcp.server import (
    configure_test_dbs,
    corpus_stats,
    dictionary_stats,
    get_dialect_forms,
    lookup_word,
    search_corpus,
    server_stats,
    word_report,
)
from tests.fixtures.sample_corpus import SAMPLE_ARTICLES


@pytest.fixture
def dict_db():
    """In-memory dictmaster-style database with sample data."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row

    conn.executescript("""
        CREATE TABLE headwords (
            id INTEGER PRIMARY KEY,
            traditional TEXT NOT NULL,
            simplified TEXT NOT NULL,
            pinyin TEXT NOT NULL,
            pos TEXT,
            UNIQUE(traditional, simplified, pinyin)
        );
        CREATE INDEX idx_headwords_simplified ON headwords(simplified);
        CREATE INDEX idx_headwords_traditional ON headwords(traditional);

        CREATE TABLE definitions (
            id INTEGER PRIMARY KEY,
            headword_id INTEGER NOT NULL REFERENCES headwords(id),
            lang TEXT NOT NULL,
            definition TEXT NOT NULL,
            source TEXT NOT NULL,
            confidence TEXT,
            UNIQUE(headword_id, lang, source)
        );

        CREATE TABLE sources (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            entry_count INTEGER,
            license TEXT
        );

        CREATE TABLE dialect_forms (
            id INTEGER PRIMARY KEY,
            headword_id INTEGER NOT NULL REFERENCES headwords(id),
            dialect TEXT NOT NULL,
            native_chars TEXT,
            pronunciation TEXT NOT NULL,
            gloss TEXT,
            source TEXT NOT NULL,
            UNIQUE(headword_id, dialect, source)
        );

        CREATE TABLE schema_info (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)

    # Insert sample headwords + definitions
    conn.execute(
        "INSERT INTO headwords (id, traditional, simplified, pinyin) VALUES (1, '銀行', '银行', 'yín háng')"
    )
    conn.execute(
        "INSERT INTO headwords (id, traditional, simplified, pinyin) VALUES (2, '長城', '长城', 'cháng chéng')"
    )
    conn.execute(
        "INSERT INTO definitions (headword_id, lang, definition, source) "
        "VALUES (1, 'en', 'bank; financial institution', 'cedict')"
    )
    conn.execute(
        "INSERT INTO definitions (headword_id, lang, definition, source) "
        "VALUES (1, 'fr', 'banque', 'cfdict')"
    )
    conn.execute(
        "INSERT INTO definitions (headword_id, lang, definition, source) "
        "VALUES (2, 'en', 'Great Wall', 'cedict')"
    )

    # Insert sample dialect forms
    conn.execute(
        "INSERT INTO dialect_forms (headword_id, dialect, pronunciation, source) "
        "VALUES (1, 'yue', 'ngan4 hong4', 'cccanto')"
    )
    conn.execute(
        "INSERT INTO dialect_forms (headword_id, dialect, native_chars, pronunciation, gloss, source) "
        "VALUES (1, 'nan', '銀行', 'gîn-hâng', 'bank', 'itaigi')"
    )

    # Insert sources
    conn.execute("INSERT INTO sources (name, entry_count, license) VALUES ('cedict', 120000, 'CC BY-SA 4.0')")
    conn.execute("INSERT INTO sources (name, entry_count, license) VALUES ('cfdict', 40000, 'CC BY-SA 3.0')")

    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def mcp_dbs(populated_db, dict_db):
    """Configure the MCP server with both test DBs."""
    configure_test_dbs(populated_db, dict_db)
    yield populated_db, dict_db


class TestSearchCorpus:
    """search_corpus tool returns ranked results."""

    def test_finds_common_word(self, mcp_dbs):
        result = asyncio.run(search_corpus("银行"))
        assert "银行" in result
        assert "results" in result.lower()

    def test_finds_domain_word(self, mcp_dbs):
        result = asyncio.run(search_corpus("选任"))
        assert "选任" in result

    def test_no_results(self, mcp_dbs):
        result = asyncio.run(search_corpus("不存在的词汇xyz"))
        assert "No corpus results" in result

    def test_limit_parameter(self, mcp_dbs):
        result = asyncio.run(search_corpus("选任", limit=2))
        # Should have at most 2 numbered results
        assert "选任" in result


class TestWordReport:
    """word_report tool builds comprehensive reports."""

    def test_basic_report(self, mcp_dbs):
        result = asyncio.run(word_report("银行"))
        assert "# Word Report: 银行" in result
        assert "Corpus Evidence" in result

    def test_report_with_dictionary(self, mcp_dbs):
        result = asyncio.run(word_report("银行"))
        assert "Dictionary Definitions" in result or "CC-CEDICT" in result

    def test_report_with_dialects(self, mcp_dbs):
        result = asyncio.run(word_report("银行"))
        assert "Dialect Forms" in result
        assert "Cantonese" in result

    def test_brief_detail(self, mcp_dbs):
        result = asyncio.run(word_report("选任", detail="brief"))
        assert "Word Report" in result

    def test_no_hits_report(self, mcp_dbs):
        result = asyncio.run(word_report("不存在的词"))
        assert "0 hits" in result


class TestLookupWord:
    """lookup_word tool returns dictionary definitions."""

    def test_finds_word(self, mcp_dbs):
        result = asyncio.run(lookup_word("银行"))
        assert "银行" in result or "銀行" in result
        assert "bank" in result.lower()

    def test_multiple_languages(self, mcp_dbs):
        result = asyncio.run(lookup_word("银行"))
        assert "en" in result
        assert "fr" in result

    def test_not_found(self, mcp_dbs):
        result = asyncio.run(lookup_word("不存在的词"))
        assert "No dictionary entries" in result


class TestGetDialectForms:
    """get_dialect_forms tool returns Cantonese/Hokkien data."""

    def test_finds_cantonese(self, mcp_dbs):
        result = asyncio.run(get_dialect_forms("银行"))
        assert "Cantonese" in result
        assert "ngan4 hong4" in result

    def test_finds_hokkien(self, mcp_dbs):
        result = asyncio.run(get_dialect_forms("银行"))
        assert "Hokkien" in result

    def test_not_found(self, mcp_dbs):
        result = asyncio.run(get_dialect_forms("不存在"))
        assert "No dialect forms" in result


class TestCorpusStats:
    """corpus_stats tool returns corpus overview."""

    def test_has_counts(self, mcp_dbs):
        result = asyncio.run(corpus_stats())
        assert "Corpus Statistics" in result
        assert "Articles" in result
        assert "Chunks" in result

    def test_has_sources(self, mcp_dbs):
        result = asyncio.run(corpus_stats())
        assert "Sources" in result


class TestDictionaryStats:
    """dictionary_stats tool returns dictionary overview."""

    def test_has_counts(self, mcp_dbs):
        result = asyncio.run(dictionary_stats())
        assert "Dictionary Statistics" in result
        assert "Headwords" in result
        assert "Definitions" in result

    def test_has_languages(self, mcp_dbs):
        result = asyncio.run(dictionary_stats())
        assert "Languages" in result


class TestServerStats:
    """server_stats tool returns server info."""

    def test_has_version(self, mcp_dbs):
        result = asyncio.run(server_stats())
        assert "zhcorpus Server" in result
        assert "Version" in result
        assert "Uptime" in result
