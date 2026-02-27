"""Headword merging, deduplication, and POS inference.

Handles:
- Pinyin normalization (u: -> v, consistent spacing, tone format)
- POS inference from multiple signals
- Definition deduplication across sources
"""

import re
import sqlite3
from typing import Optional


def normalize_pinyin(pinyin: str) -> str:
    """Normalize pinyin to consistent numbered-tone format.

    Normalizations:
    - u: -> v (CEDICT convention for ü)
    - Strip extra whitespace
    - Lowercase
    - Normalize tone number placement

    Examples:
        "lu:4" -> "lv4"
        "nü3" -> "nv3"
        "zhong1  guo2" -> "zhong1 guo2"
        "Zhong1 Guo2" -> "zhong1 guo2"
    """
    pinyin = pinyin.strip().lower()
    # u: -> v (CEDICT convention)
    pinyin = pinyin.replace("u:", "v")
    pinyin = pinyin.replace("ü", "v")
    # Normalize whitespace
    pinyin = re.sub(r"\s+", " ", pinyin)
    return pinyin


def infer_pos_from_definition(definition: str) -> Optional[str]:
    """Infer part of speech from CEDICT-style definition text.

    Heuristics:
    - "CL:" present -> noun (classifier reference)
    - Starts with "to " -> verb
    - Starts with "(particle)" or ends with "particle" -> particle
    - Starts with "(classifier" -> classifier
    """
    if not definition:
        return None

    # Check first sense (before first /)
    first = definition.split("/")[0].strip()

    if "CL:" in definition:
        return "noun"
    if first.startswith("to "):
        return "verb"
    if "(particle)" in first.lower() or "particle" in first.lower():
        return "particle"
    if "(classifier" in first.lower():
        return "classifier"
    if first.startswith("(") and first.endswith(")"):
        return "phrase"

    return None


def merge_pos(existing: Optional[str], new: Optional[str]) -> Optional[str]:
    """Merge POS from multiple sources, preferring specific over None."""
    if existing and new:
        # Both have POS — prefer the existing unless new is more specific
        return existing
    return existing or new


def reconcile_headwords(conn: sqlite3.Connection) -> int:
    """Reconcile headwords that may have been inserted with different pinyin normalization.

    Finds headwords where (traditional, simplified) match but pinyin differs only
    by normalization. Merges definitions to the canonical (first-inserted) headword.

    Returns number of headwords merged.
    """
    # Find potential duplicates: same trad+simp but different pinyin
    dupes = conn.execute("""
        SELECT h1.id AS keep_id, h2.id AS merge_id,
               h1.pinyin AS keep_pinyin, h2.pinyin AS merge_pinyin
        FROM headwords h1
        JOIN headwords h2 ON h1.traditional = h2.traditional
            AND h1.simplified = h2.simplified
            AND h1.id < h2.id
        WHERE REPLACE(REPLACE(LOWER(h1.pinyin), 'u:', 'v'), 'ü', 'v')
            = REPLACE(REPLACE(LOWER(h2.pinyin), 'u:', 'v'), 'ü', 'v')
    """).fetchall()

    merged = 0
    for row in dupes:
        keep_id = row["keep_id"]
        merge_id = row["merge_id"]

        # Move definitions to the canonical headword
        conn.execute(
            "UPDATE OR IGNORE definitions SET headword_id = ? WHERE headword_id = ?",
            (keep_id, merge_id),
        )
        # Delete orphaned definitions (UNIQUE constraint violations)
        conn.execute("DELETE FROM definitions WHERE headword_id = ?", (merge_id,))
        # Delete the duplicate headword
        conn.execute("DELETE FROM headwords WHERE id = ?", (merge_id,))
        merged += 1

    if merged:
        conn.commit()
    return merged


def fill_pos_from_definitions(conn: sqlite3.Connection) -> int:
    """Infer POS for headwords that have NULL pos, using their definitions.

    Returns number of headwords updated.
    """
    rows = conn.execute(
        "SELECT h.id, d.definition FROM headwords h "
        "JOIN definitions d ON d.headword_id = h.id "
        "WHERE h.pos IS NULL AND d.lang = 'en' "
        "ORDER BY h.id"
    ).fetchall()

    updated = 0
    seen = set()
    for row in rows:
        hw_id = row["id"]
        if hw_id in seen:
            continue
        seen.add(hw_id)

        pos = infer_pos_from_definition(row["definition"])
        if pos:
            conn.execute("UPDATE headwords SET pos = ? WHERE id = ?", (pos, hw_id))
            updated += 1

    if updated:
        conn.commit()
    return updated


def get_coverage_report(conn: sqlite3.Connection) -> dict:
    """Generate a coverage report: how many headwords have definitions per language."""
    total = conn.execute("SELECT COUNT(*) FROM headwords").fetchone()[0]

    langs = conn.execute("""
        SELECT d.lang, COUNT(DISTINCT d.headword_id) as covered,
               GROUP_CONCAT(DISTINCT d.source) as sources
        FROM definitions d
        GROUP BY d.lang
        ORDER BY d.lang
    """).fetchall()

    coverage = {}
    for row in langs:
        coverage[row["lang"]] = {
            "count": row["covered"],
            "pct": round(100 * row["covered"] / total, 1) if total else 0,
            "sources": row["sources"],
        }

    # Find headwords with no definitions in each target language
    target_langs = ["en", "de", "fr", "es", "sv", "ja", "ko", "ru", "id", "vi", "tl"]
    gaps = {}
    for lang in target_langs:
        gap_count = conn.execute("""
            SELECT COUNT(*) FROM headwords h
            WHERE NOT EXISTS (
                SELECT 1 FROM definitions d WHERE d.headword_id = h.id AND d.lang = ?
            )
        """, (lang,)).fetchone()[0]
        gaps[lang] = gap_count

    return {
        "total_headwords": total,
        "coverage": coverage,
        "gaps": gaps,
    }
