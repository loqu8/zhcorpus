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
    - Normalize tone number placement

    Case is PRESERVED because CC-CEDICT uses initial caps to distinguish
    surnames/proper nouns from common words (e.g., He2 = surname He vs
    he2 = and/harmonious). Lowercasing collapses these distinct headwords.

    Examples:
        "lu:4" -> "lv4"
        "nü3" -> "nv3"
        "zhong1  guo2" -> "zhong1 guo2"
        "Zhong1 Guo2" -> "Zhong1 Guo2"
    """
    pinyin = pinyin.strip()
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


def _pinyin_merge_key(pinyin: str) -> str:
    """Build a merge key from pinyin for duplicate detection.

    Two pinyin strings that produce the same merge key are considered
    duplicates and will be merged.  The key strips spaces, hyphens, tone
    numbers, and normalizes u:/ü → v so that character-level pinyin
    (CC-CEDICT style, e.g. "dong4 tai4 zhu4 ci2") matches word-level
    pinyin (Wiktextract style, e.g. "dongtai4 zhuci2").

    Tone numbers must be stripped because Wiktextract omits intermediate
    tones within compound words (dongtai4 = dong+tai4, losing dong's tone).

    Case IS preserved so that He2 (surname) ≠ he2 (common word).
    """
    key = pinyin.replace(" ", "")
    key = key.replace("u:", "v").replace("ü", "v")
    key = key.replace("-", "")
    # Strip tone numbers — Wiktextract drops intermediate tones in compounds
    key = re.sub(r"[0-9]", "", key)
    # Strip parenthesized annotations like (ei¹)
    key = re.sub(r"\([^)]*\)", "", key)
    return key


def reconcile_headwords(conn: sqlite3.Connection) -> int:
    """Reconcile headwords that may have been inserted with different pinyin.

    Finds headwords where (traditional, simplified) match but pinyin differs only
    by normalization or spacing.  Merges definitions to the canonical
    (first-inserted) headword.

    Handled differences:
    - u:/ü normalization (lu:4 ↔ lv4)
    - Spacing (dong4 tai4 zhu4 ci2 ↔ dongtai4 zhuci2)
    - Hyphens (yibai-mi3 ↔ yibaimi3)

    Case differences are NOT merged (He2 ≠ he2).

    Returns number of headwords merged.
    """
    # Find all groups with multiple pinyin variants for the same trad+simp
    groups = conn.execute("""
        SELECT traditional, simplified
        FROM headwords
        GROUP BY traditional, simplified
        HAVING COUNT(*) > 1
    """).fetchall()

    merged = 0
    for group in groups:
        trad, simp = group["traditional"], group["simplified"]
        rows = conn.execute(
            "SELECT id, pinyin FROM headwords "
            "WHERE traditional = ? AND simplified = ? ORDER BY id",
            (trad, simp),
        ).fetchall()

        # Group by merge key — keep the first (lowest id) in each group
        seen: dict[str, int] = {}  # merge_key -> keep_id
        for row in rows:
            key = _pinyin_merge_key(row["pinyin"])
            if key not in seen:
                seen[key] = row["id"]
            else:
                keep_id = seen[key]
                merge_id = row["id"]
                # Move definitions to the canonical headword
                conn.execute(
                    "UPDATE OR IGNORE definitions SET headword_id = ? WHERE headword_id = ?",
                    (keep_id, merge_id),
                )
                # Move dialect forms too
                conn.execute(
                    "UPDATE OR IGNORE dialect_forms SET headword_id = ? WHERE headword_id = ?",
                    (keep_id, merge_id),
                )
                # Delete orphaned definitions/dialect_forms (UNIQUE constraint violations)
                conn.execute("DELETE FROM definitions WHERE headword_id = ?", (merge_id,))
                conn.execute("DELETE FROM dialect_forms WHERE headword_id = ?", (merge_id,))
                # Delete the duplicate headword
                conn.execute("DELETE FROM headwords WHERE id = ?", (merge_id,))
                merged += 1

    if merged:
        conn.commit()
    return merged


# Languages that use non-Latin scripts — definitions should not contain [A-Za-z]
_NON_LATIN_LANGS = {"ar", "fa", "hi", "th", "ko", "ja", "el", "ru"}

# Regex: one or more Latin letters (catches mixed-script artifacts)
_LATIN_RE = re.compile(r"[A-Za-z]")


def find_bad_translations(conn: sqlite3.Connection) -> list[dict]:
    """Find MiniMax translations with quality issues.

    Checks for:
    - Non-Latin-script languages containing Latin characters (e.g. Arabic with "Aspect")
    - Extremely short definitions (≤2 chars) that are likely truncated

    Returns list of dicts with headword_id, lang, definition, issue.
    """
    issues: list[dict] = []

    # Non-Latin languages with Latin character contamination
    placeholders = ",".join("?" for _ in _NON_LATIN_LANGS)
    rows = conn.execute(
        f"SELECT d.id, d.headword_id, d.lang, d.definition, h.traditional "
        f"FROM definitions d JOIN headwords h ON d.headword_id = h.id "
        f"WHERE d.source = 'minimax' AND d.lang IN ({placeholders})",
        list(_NON_LATIN_LANGS),
    ).fetchall()

    for row in rows:
        defn = row["definition"]
        if _LATIN_RE.search(defn):
            # Allow parenthesized romanization like (zhe, le, guo)
            stripped = re.sub(r"\([^)]*\)", "", defn)
            if _LATIN_RE.search(stripped):
                issues.append({
                    "def_id": row["id"],
                    "headword_id": row["headword_id"],
                    "traditional": row["traditional"],
                    "lang": row["lang"],
                    "definition": defn,
                    "issue": "latin_in_non_latin_script",
                })

    return issues


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
    target_langs = ["en", "de", "fr", "es", "sv", "ja", "ko", "ru", "id", "vi", "tl", "fa", "nl", "pt", "ar", "th", "hi", "it"]
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
