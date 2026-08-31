#!/usr/bin/env python3
"""Build the iCE-realism MT evaluation sample.

Pulls ~100 Chinese sentences from zhcorpus across genres that mirror what
iCE Pro users actually encounter when popping up the translator: news,
encyclopedia, modern conversation, classical prose, idioms.

Output: data/mt_eval/ice_realism.jsonl  (id, text, source, char_count)

Length window: 10..50 chars (typical iCE popup payload — long enough to be
non-trivial, short enough that LLM translation is bounded).
"""

import json
import sqlite3
import random
from pathlib import Path

DB = "data/artifacts/zhcorpus.db"
OUT = Path("data/mt_eval/ice_realism.jsonl")
SEED = 20260516

# (source_name, target_count) — sums to 100
QUOTAS = [
    ("thucnews", 25),
    ("news2016zh", 10),
    ("baidu_baike", 15),
    ("wikipedia", 15),
    ("subtitles", 15),
    ("lccc", 10),
    ("classics_prose", 5),
    ("chid", 5),
]
MIN_CHARS = 10
MAX_CHARS = 50
# Oversample factor — many chunks won't pass the length filter
OVERSAMPLE = 50


def main() -> None:
    random.seed(SEED)
    conn = sqlite3.connect(DB)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    # Map source_name -> id
    sources = dict(conn.execute("SELECT name, id FROM sources").fetchall())

    samples: list[dict] = []
    for src_name, want in QUOTAS:
        src_id = sources[src_name]
        # Get rowid range to do cheap random sampling without scanning the table
        rng = conn.execute(
            "SELECT MIN(id), MAX(id) FROM articles WHERE source_id = ?",
            (src_id,),
        ).fetchone()
        if not rng or rng[0] is None:
            print(f"[skip] {src_name}: no articles")
            continue
        lo, hi = rng

        picked: list[dict] = []
        attempts = 0
        # Random rowid probe — pull chunks until we have `want` that fit length
        while len(picked) < want and attempts < want * OVERSAMPLE:
            attempts += 1
            aid = random.randint(lo, hi)
            row = conn.execute(
                "SELECT chunks.id, chunks.text, chunks.char_count "
                "FROM chunks WHERE article_id = ? ORDER BY RANDOM() LIMIT 1",
                (aid,),
            ).fetchone()
            if not row:
                continue
            cid, text, cc = row
            text = text.strip()
            if not (MIN_CHARS <= len(text) <= MAX_CHARS):
                continue
            # Filter chunks that are mostly non-CJK (URLs, page furniture)
            cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
            if cjk < len(text) * 0.5:
                continue
            picked.append({
                "id": f"{src_name}-{cid}",
                "text": text,
                "source": src_name,
                "char_count": len(text),
            })

        print(f"  {src_name}: picked {len(picked)}/{want} in {attempts} attempts")
        samples.extend(picked)

    # Deduplicate (in case any source overlapped)
    seen = set()
    deduped = []
    for s in samples:
        if s["text"] in seen:
            continue
        seen.add(s["text"])
        deduped.append(s)

    with open(OUT, "w", encoding="utf-8") as f:
        for s in deduped:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    print(f"\nWrote {len(deduped)} samples -> {OUT}")
    conn.close()


if __name__ == "__main__":
    main()
