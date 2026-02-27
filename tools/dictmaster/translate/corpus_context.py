"""Fetch example sentences from the zhcorpus database for translation context.

Uses unranked FTS5 lookup (<15ms per word) to grab 1-2 example sentences
containing the target word. The zhcorpus DB has 113M Chinese text chunks.
"""

import sqlite3
from pathlib import Path

# Default path to the zhcorpus database
ZHCORPUS_DB_PATH = Path("data/artifacts/zhcorpus.db")

# Path to the simple tokenizer extension
_LIB_DIR = Path(__file__).resolve().parent.parent.parent.parent / "lib" / "libsimple-linux-ubuntu-latest"
SIMPLE_EXT_PATH = str(_LIB_DIR / "libsimple")


def get_corpus_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a read-only connection to the zhcorpus database.

    Loads the simple tokenizer extension needed for FTS5 queries.
    """
    path = str(db_path or ZHCORPUS_DB_PATH)
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.enable_load_extension(True)
    conn.load_extension(SIMPLE_EXT_PATH)
    conn.enable_load_extension(False)
    conn.row_factory = sqlite3.Row
    return conn


def get_example_sentences(
    conn: sqlite3.Connection,
    word: str,
    limit: int = 2,
) -> list[str]:
    """Fetch example sentences containing the word from zhcorpus.

    Uses unranked FTS5 lookup (no ORDER BY rank) for speed (<15ms).
    Filters: skip chunks shorter than 10 chars, prefer 20-100 chars.

    Args:
        conn: zhcorpus database connection (with simple tokenizer loaded).
        word: Chinese word to search for.
        limit: Maximum number of example sentences to return.

    Returns:
        List of example sentence strings.
    """
    if not word:
        return []

    try:
        match_expr = conn.execute("SELECT simple_query(?)", (word,)).fetchone()[0]
    except Exception:
        return []

    # Fetch more candidates than needed so we can filter
    fetch_limit = limit * 5
    try:
        rows = conn.execute(
            """
            SELECT c.text, c.char_count
            FROM chunks_fts
            JOIN chunks c ON c.id = chunks_fts.rowid
            WHERE chunks_fts MATCH ?
            LIMIT ?
            """,
            (match_expr, fetch_limit),
        ).fetchall()
    except Exception:
        return []

    # Filter and rank by preference
    good = []
    ok = []
    for row in rows:
        text = row["text"]
        length = row["char_count"]

        # Skip very short chunks
        if length < 10:
            continue
        # Skip if the chunk is just the word repeated
        if text.strip() == word:
            continue
        # Skip very long chunks
        if length > 200:
            continue

        # Prefer chunks in the 20-100 char range
        if 20 <= length <= 100:
            good.append(text)
        else:
            ok.append(text)

        if len(good) >= limit:
            break

    results = (good + ok)[:limit]
    return results
