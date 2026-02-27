"""Word Report builder — the core deliverable of zhcorpus.

Assembles a structured, multi-source evidence report for a Chinese word,
modeled on the SCAR/IPLVS "At-a-Glance" pattern: classification + summary
table + best evidence per source.
"""

import sqlite3
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .search.fts import (
    SearchResult,
    count_hits_by_source,
    get_context,
    search_fts,
)


@dataclass
class SourceEvidence:
    """Evidence from a single corpus source."""
    name: str
    hit_count: int
    best_snippets: List[str]


@dataclass
class CedictEntry:
    """A CC-CEDICT dictionary entry."""
    traditional: str
    simplified: str
    pinyin: str
    definition: str


@dataclass
class WordReport:
    """Multi-source evidence report for a single Chinese word."""
    term: str
    total_hits: int
    sources: List[SourceEvidence]
    cedict_entries: List[CedictEntry]
    best_snippets: List[Dict]  # top snippets across all sources
    pinyin_suggestion: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize for MCP JSON response."""
        return {
            "term": self.term,
            "total_hits": self.total_hits,
            "sources": [
                {
                    "name": s.name,
                    "hit_count": s.hit_count,
                    "best_snippets": s.best_snippets,
                }
                for s in self.sources
            ],
            "cedict_entries": [
                {
                    "traditional": e.traditional,
                    "simplified": e.simplified,
                    "pinyin": e.pinyin,
                    "definition": e.definition,
                }
                for e in self.cedict_entries
            ],
            "best_snippets": self.best_snippets,
            "pinyin_suggestion": self.pinyin_suggestion,
        }


def _lookup_cedict(conn: sqlite3.Connection, term: str) -> List[CedictEntry]:
    """Look up a term in the CEDICT table."""
    rows = conn.execute(
        "SELECT traditional, simplified, pinyin, definition "
        "FROM cedict WHERE simplified = ? OR traditional = ?",
        (term, term),
    ).fetchall()
    return [
        CedictEntry(
            traditional=row["traditional"],
            simplified=row["simplified"],
            pinyin=row["pinyin"],
            definition=row["definition"],
        )
        for row in rows
    ]


def _pick_best_snippets_per_source(
    results: List[SearchResult],
    max_per_source: int = 3,
) -> Dict[str, List[str]]:
    """Group results by source and pick the best snippets from each."""
    by_source: Dict[str, List[SearchResult]] = {}
    for r in results:
        by_source.setdefault(r.source, []).append(r)

    best = {}
    for source, items in by_source.items():
        # Already rank-sorted from FTS5
        best[source] = [item.text for item in items[:max_per_source]]
    return best


def build_word_report(
    conn: sqlite3.Connection,
    term: str,
    limit: int = 30,
    snippets_per_source: int = 3,
    context_chunks: int = 2,
) -> WordReport:
    """Build a comprehensive word report from all corpus sources.

    Args:
        conn: Database connection.
        term: Chinese word to report on.
        limit: Maximum total search results to consider.
        snippets_per_source: Best snippets to keep per source.
        context_chunks: Number of neighboring chunks to include
            before/after each hit (0 = hit chunk only).

    Returns:
        WordReport with per-source evidence breakdown.
    """
    # Search
    results = search_fts(conn, term, limit=limit)

    # Per-source hit counts
    source_counts = count_hits_by_source(conn, term)
    total_hits = sum(source_counts.values())

    # Best snippets per source — with context if requested
    best_per_source = _pick_best_snippets_per_source(results, snippets_per_source)

    # Build source evidence list
    sources = []
    for source_name, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        sources.append(
            SourceEvidence(
                name=source_name,
                hit_count=count,
                best_snippets=best_per_source.get(source_name, []),
            )
        )

    # Cross-reference CEDICT
    cedict_entries = _lookup_cedict(conn, term)

    # Top snippets across all sources — expand with context
    top_snippets = []
    for r in results[:6]:
        entry = {"source": r.source, "title": r.title, "text": r.text}
        if context_chunks > 0:
            ctx = get_context(conn, r, before=context_chunks, after=context_chunks)
            entry["context"] = ctx.context
        top_snippets.append(entry)

    return WordReport(
        term=term,
        total_hits=total_hits,
        sources=sources,
        cedict_entries=cedict_entries,
        best_snippets=top_snippets,
    )
