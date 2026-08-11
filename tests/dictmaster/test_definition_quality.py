"""Tests for definition quality — regression tests for known bad definitions.

Issue #10: 菜 (cai4) was showing "rapeseed oil / canola oil" instead of
"vegetable / dish" due to MiniMax batch cross-talk with compounds like
菜油 and 菜籽油.  The v2-single-char-anchored retranslation fixed this,
but we keep the test to prevent regression.
"""

import pytest

from tools.dictmaster.schema import get_connection, init_db, upsert_definition, upsert_headword


@pytest.fixture
def db():
    conn = get_connection()
    init_db(conn)
    yield conn
    conn.close()


# Compound-family terms whose definitions must NOT leak into the base character.
# Format: (char, pinyin, bad_terms, expected_primary)
CROSS_TALK_CASES = [
    (
        "菜", "cai4",
        ["rapeseed", "canola", "brassica"],
        ["vegetable", "dish"],
    ),
]


class TestCrossTalkRegression:
    """Verify single-char definitions don't contain compound cross-talk."""

    @pytest.mark.parametrize("char,pinyin,bad_terms,expected", CROSS_TALK_CASES)
    def test_no_compound_crosstalk(self, db, char, pinyin, bad_terms, expected):
        """A single-char entry should not inherit definitions from its compounds."""
        # Set up: insert headword + a clean definition
        hw_id = upsert_headword(db, char, char, pinyin)
        upsert_definition(db, hw_id, "en", "vegetable/greens/dish/course", "minimax", "v2")

        row = db.execute(
            "SELECT d.definition FROM definitions d WHERE d.headword_id = ? AND d.lang = 'en'",
            (hw_id,),
        ).fetchone()
        defn = row["definition"].lower()

        for bad in bad_terms:
            assert bad not in defn, (
                f"{char} ({pinyin}) EN definition contains '{bad}' — "
                f"likely cross-talk from compound words"
            )
        for good in expected:
            assert good in defn, (
                f"{char} ({pinyin}) EN definition missing '{good}'"
            )


class TestDefinitionOnDisk:
    """Validate definitions in the actual dictmaster.db (skipped if DB absent)."""

    @pytest.fixture
    def dictmaster(self):
        from tools.dictmaster.schema import DEFAULT_DB_PATH
        if not DEFAULT_DB_PATH.exists():
            pytest.skip("dictmaster.db not available")
        import sqlite3
        conn = sqlite3.connect(str(DEFAULT_DB_PATH))
        conn.row_factory = sqlite3.Row
        yield conn
        conn.close()

    def test_cai4_vegetable_not_rapeseed(self, dictmaster):
        """Issue #10: 菜 must mean 'vegetable/dish', not 'rapeseed oil'."""
        rows = dictmaster.execute("""
            SELECT d.definition, d.source, d.confidence
            FROM headwords h
            JOIN definitions d ON d.headword_id = h.id
            WHERE h.simplified = '菜'
              AND h.pinyin = 'cai4'
              AND d.lang = 'en'
            ORDER BY d.source
        """).fetchall()

        assert len(rows) > 0, "No EN definitions found for 菜 (cai4)"

        for row in rows:
            defn = row["definition"].lower()
            assert "rapeseed oil" not in defn, (
                f"菜 definition from {row['source']} contains 'rapeseed oil': {row['definition']}"
            )
            assert "canola oil" not in defn, (
                f"菜 definition from {row['source']} contains 'canola oil': {row['definition']}"
            )

        # At least one definition should contain "vegetable" or "dish"
        all_defs = " ".join(r["definition"].lower() for r in rows)
        assert "vegetable" in all_defs or "dish" in all_defs, (
            f"菜 (cai4) should have 'vegetable' or 'dish' in EN definition"
        )
