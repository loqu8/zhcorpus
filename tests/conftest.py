"""Shared fixtures for zhcorpus tests."""

import pytest

from zhcorpus.db import ensure_source, init_db, insert_article, insert_chunk, get_connection
from zhcorpus.ingest.chunker import chunk_text
from tests.fixtures.sample_corpus import SAMPLE_ARTICLES


@pytest.fixture
def db():
    """In-memory database with schema initialized."""
    conn = get_connection()
    init_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def populated_db(db):
    """Database populated with the sample corpus, chunked into sentences."""
    source_ids = {}
    for source_name, title, text in SAMPLE_ARTICLES:
        if source_name not in source_ids:
            source_ids[source_name] = ensure_source(db, source_name)

        sid = source_ids[source_name]
        article_id = insert_article(db, sid, title, title, len(text))

        chunks = chunk_text(text)
        for idx, chunk in enumerate(chunks):
            insert_chunk(db, article_id, idx, chunk)

    db.commit()
    yield db
