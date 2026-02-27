# FTS5 Performance on 112M Chunks

## Problem

Single-character queries (的, 学) match tens of millions of chunks.
FTS5 BM25 ranking (`ORDER BY rank`) is O(n) — it must score every
matching document before returning even LIMIT 20 results.

| Term | Matches | With `ORDER BY rank` | Without |
|------|---------|---------------------|---------|
| 画蛇添足 (4-char idiom) | ~452 | 0.13s | instant |
| 银行 (2-char common) | ~500K+ | 1.4s | instant |
| 学 (1-char) | millions | 5–26s | instant |
| 的 (highest-freq char) | ~100M+ | **timeout** | instant |

## Root Cause

```sql
-- This is O(n) on ALL matching documents:
SELECT ... FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY rank LIMIT 20
```

FTS5 must compute BM25 for every matching row, sort them all, then return
the top 20. For 的 (matches 100M+ rows), this means scoring and sorting
100M documents — impossible in any reasonable time.

## Solution: Per-Source Sampling (no BM25)

### Source Diversity Problem

FTS5 posting lists are ordered by insertion time. Sources are imported
sequentially (Wikipedia first, then Baidu Baike, etc.), so each source
occupies a contiguous rowid range:

```
wikipedia           :            1 –   21,322,869
baidu_baike         :   21,322,870 –   28,023,113
chid                :   28,023,114 –   32,843,069
...
subtitles           :   99,307,857 –  104,445,223
```

A naive `LIMIT 200` grabs the first 200 posting-list entries — **all from
Wikipedia** for common terms. This gives zero source diversity.

### Per-Source Rowid Range Queries

FTS5 efficiently intersects posting lists with rowid ranges:

```sql
-- Instant: walks posting list, skips entries outside [lo, hi]
SELECT rowid FROM chunks_fts
WHERE chunks_fts MATCH ? AND rowid BETWEEN ? AND ?
LIMIT 2
```

We run one such query per source (15 sources × 0.1ms each = ~2ms total),
then JOIN the collected rowids for metadata:

```sql
SELECT c.id, c.text, s.name, a.title, ...
FROM chunks c
JOIN articles a ON a.id = c.article_id
JOIN sources s ON s.id = a.source_id
WHERE c.id IN (?, ?, ?, ...)
LIMIT 20
```

### Materialized Source Ranges

Computing source ranges from articles/chunks tables requires scanning 34M
articles — takes ~2.5s. We materialize them once in `source_chunk_ranges`:

```sql
CREATE TABLE source_chunk_ranges (
    name TEXT PRIMARY KEY,
    min_chunk_id INTEGER NOT NULL,
    max_chunk_id INTEGER NOT NULL
);
```

Call `materialize_source_ranges(conn)` after importing new data. Loads
in 0.0000s at query time (15 rows, instant).

### Why not re-MATCH in phase 2?

First attempt tried:
```sql
-- STILL SLOW — FTS5 re-evaluates the MATCH expression
SELECT ... FROM chunks_fts
WHERE chunks_fts.rowid IN (...) AND chunks_fts MATCH ?
```

FTS5 doesn't use the rowid filter to short-circuit — it re-evaluates
MATCH against its full index. The fix is to avoid FTS5 entirely in
phase 2 and JOIN directly on `chunks.id` (integer PK).

### Tradeoff: No BM25 Ranking

Results come in posting-list order per source, not relevance order.
This is acceptable because:
- Each source contributes equal representation (round-robin)
- For AI agents consuming the results, any example of usage is valuable
- The alternative (BM25) literally cannot return results for common terms

### Tradeoff: No Keyword Highlighting

Since phase 2 doesn't touch FTS5, `simple_snippet()` can't be used.
We use `substr(c.text, 1, N)` instead. This loses keyword highlighting
but keeps the response instant. The full `c.text` is still returned.

## Per-Source Hit Counts

`count_hits_by_source` uses the same per-source rowid range strategy:

```sql
-- For each source: cap=1000 per source
SELECT COUNT(*) FROM (
    SELECT 1 FROM chunks_fts
    WHERE chunks_fts MATCH ? AND rowid BETWEEN ? AND ?
    LIMIT 1000
)
```

This gives independent counts per source (not biased by posting-list
order) in ~10ms total. For rare terms, counts are exact. For common
terms, each source caps at 1,000.

## Capped Total Count

`count_hits` uses a global cap (doesn't need per-source):

```sql
SELECT COUNT(*) FROM (
    SELECT 1 FROM chunks_fts WHERE chunks_fts MATCH ? LIMIT 10000
)
```

## Final Benchmarks (68GB / 104M chunks, 15 sources)

### search_fts (limit=20, source-diverse)
| Term | Time | Sources | Notes |
|------|------|---------|-------|
| 画蛇添足 | 14ms | 5 | 4-char idiom, 452 matches |
| 营商环境 | 8ms | 6 | 4-char domain term |
| 银行 | 4ms | 10 | 2-char, very common |
| 学 | 2ms | 10 | 1-char, millions of matches |
| 的 | 4ms | 10 | Highest-frequency char, 100M+ matches |

### count_hits_by_source (cap=1000 per source)
| Term | Time | Sources with Hits | Total |
|------|------|-------------------|-------|
| 画蛇添足 | 32ms | 10 | 452 (exact) |
| 营商环境 | 54ms | 13 | 2,603 (exact) |
| 银行 | 10ms | 15 | 12,546 |
| 学 | 2ms | 15 | 14,770 |
| 的 | 4ms | 15 | 15,000 |

### MCP tools end-to-end (word_report, brief mode)
| Term | Time | Dict Entries | Dialect Forms | Corpus Hits |
|------|------|-------------|---------------|-------------|
| 银行 | 17ms | 7 langs | Cantonese + Hokkien | 12,546 |
| 学 | 3ms | 15 langs | Cantonese + Hokkien | 14,770 |
| 的 | 30ms | 17 langs | Cantonese + Hokkien | 15,000 |
| 画蛇添足 | 48ms | 15 langs | Cantonese + Hokkien | 452 |

## Rejected Approaches

1. **BM25 ranking** — O(n) on matching docs. Times out for common terms
   (的, 学). Cannot be fixed without pre-computation.

2. **Re-MATCH in phase 2** — FTS5 re-evaluates MATCH on its full index
   regardless of rowid filter. Must avoid FTS5 entirely in phase 2.

3. **Global LIMIT sampling** — Posting-list order means all samples come
   from first-imported source. Per-source sampling with rowid ranges solves this.

4. **GROUP BY source on global sample** — Same posting-list bias. Plus the
   JOIN of 10K rowids through 3 tables takes 1-2s on cold cache.

5. **Separate FTS tables per source** — 15 FTS indexes to maintain,
   rebuild, and sync. Massive maintenance burden for no performance gain.

6. **Separate databases per source** — FTS5 can only search within its
   own database. Cross-DB search = N separate queries anyway, which is
   what we do with rowid ranges but faster (single index).

7. **Pre-materialized per-term stats** — Feasible for ~428K known headwords,
   but doesn't help for arbitrary query terms.

8. **Trigram tokenizer** — 12x index bloat (68GB → 800GB+), multi-minute
   queries. Rejected early.

9. **Frequency-aware routing** — Route common terms to unranked path,
   rare terms to BM25. Unnecessary; per-source sampling is fast enough
   for all term lengths.

## Key Insights

1. **FTS5 posting-list traversal is O(LIMIT), not O(matches).**
   `SELECT rowid ... WHERE MATCH ? LIMIT 200` reads exactly 200 entries
   and stops. Instant even for 的 (100M+ matches).

2. **`ORDER BY rank` forces O(n) materialization.** Must score every
   matching document. This is the single bottleneck.

3. **`AND rowid BETWEEN lo AND hi` intersects efficiently.** FTS5 can
   skip posting-list entries outside the range. This enables per-source
   sampling without N separate indexes.

4. **Source ranges are static.** They only change during import. Materialize
   once in `source_chunk_ranges` table, load in 0.0s at query time.
