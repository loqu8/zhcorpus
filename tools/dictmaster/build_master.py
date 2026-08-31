#!/usr/bin/env python3
"""Build the master multilingual Chinese dictionary.

Orchestrates: parse -> merge -> translate -> export

Usage:
    python tools/dictmaster/build_master.py                    # Full build
    python tools/dictmaster/build_master.py --step import      # Import only
    python tools/dictmaster/build_master.py --step merge       # Merge/reconcile only
    python tools/dictmaster/build_master.py --step translate --lang es  # Translate Spanish
    python tools/dictmaster/build_master.py --step export      # Export only
    python tools/dictmaster/build_master.py --step dialect      # Import Cantonese + Hokkien
    python tools/dictmaster/build_master.py --limit 1000       # Limit imports for testing
"""

import argparse
import sys
import time
from pathlib import Path

from tools.dictmaster.schema import (
    DEFAULT_DB_PATH,
    get_connection,
    get_stats,
    init_db,
    update_source_count,
)
from tools.dictmaster.parsers.cedict_format import SOURCE_LANG_MAP, import_cedict_file
from tools.dictmaster.parsers.jmdict import import_jmdict
from tools.dictmaster.parsers.wiktextract import import_wiktextract
from tools.dictmaster.merge import (
    fill_pos_from_definitions,
    get_coverage_report,
    reconcile_headwords,
)
from tools.dictmaster.export import export_all_languages, export_stats
from tools.dictmaster.parsers.dialect import (
    derive_hokkien_from_compounds,
    import_cccanto,
    import_cccedict_readings,
    import_chhoetaigi_generic,
    import_itaigi,
    import_rime_cantonese,
    import_taihua,
    import_unihan_cantonese,
)

# Default data paths
RAW_DIR = Path("data/raw/dictmaster")
EXPORT_DIR = Path("data/artifacts/dictmaster")

# CEDICT-family dictionary files
CEDICT_FILES = {
    "cedict": {"path": "cedict_1_0_ts_utf-8_mdbg.txt.gz", "lang": "en"},
    "cfdict": {"path": "cfdict.txt", "lang": "fr"},
    "handedict": {"path": "handedict.txt", "lang": "de"},
    "cidict": {"path": "cidict.txt", "lang": "id"},
}

WIKTEXTRACT_FILE = "kaikki.org-dictionary-Chinese.jsonl.gz"
JMDICT_FILE = "JMdict.gz"


def step_import(db_path: Path, limit: int | None = None) -> None:
    """Import all available dictionary sources."""
    conn = get_connection(db_path)
    init_db(conn)

    # Import CEDICT-family dictionaries
    for source_name, info in CEDICT_FILES.items():
        fpath = RAW_DIR / info["path"]
        if not fpath.exists():
            # Try .gz variant
            fpath_gz = RAW_DIR / (info["path"] + ".gz")
            if fpath_gz.exists():
                fpath = fpath_gz
            else:
                print(f"  SKIP {source_name}: {fpath} not found")
                continue

        print(f"  Importing {source_name} ({info['lang']}) from {fpath.name}...")
        t0 = time.time()
        count = import_cedict_file(conn, fpath, source_name, info["lang"], limit=limit)
        update_source_count(conn, source_name)
        print(f"    -> {count:,} entries in {time.time() - t0:.1f}s")

    # Import Wiktextract
    wikt_path = RAW_DIR / WIKTEXTRACT_FILE
    if wikt_path.exists():
        print(f"  Importing wiktextract from {wikt_path.name}...")
        t0 = time.time()
        count = import_wiktextract(conn, wikt_path, limit=limit)
        update_source_count(conn, "wiktextract")
        print(f"    -> {count:,} entries in {time.time() - t0:.1f}s")
    else:
        print(f"  SKIP wiktextract: {wikt_path} not found")

    # Import JMdict
    jmdict_path = RAW_DIR / JMDICT_FILE
    if jmdict_path.exists():
        print(f"  Importing jmdict from {jmdict_path.name}...")
        t0 = time.time()
        count = import_jmdict(conn, jmdict_path, limit=limit)
        update_source_count(conn, "jmdict")
        print(f"    -> {count:,} entries in {time.time() - t0:.1f}s")
    else:
        print(f"  SKIP jmdict: {jmdict_path} not found")

    conn.close()


def step_merge(db_path: Path) -> None:
    """Run merge and reconciliation."""
    conn = get_connection(db_path)

    print("  Reconciling headwords (pinyin normalization)...")
    merged = reconcile_headwords(conn)
    print(f"    -> {merged} headwords merged")

    print("  Inferring POS from definitions...")
    updated = fill_pos_from_definitions(conn)
    print(f"    -> {updated} headwords updated with POS")

    conn.close()


def step_translate(
    db_path: Path,
    lang: str,
    backend: str = "ollama",
    batch_size: int = 50,
    limit: int | None = None,
) -> None:
    """Translate missing definitions for a single language using MiniMax M2.5."""
    if backend == "ollama":
        from tools.dictmaster.translate.minimax_ollama import translate_batch
    else:
        from tools.dictmaster.translate.minimax_api import translate_batch

    from tools.dictmaster.schema import ensure_source, upsert_definition

    conn = get_connection(db_path)
    ensure_source(conn, "minimax")

    # Find headwords without definitions in the target language
    rows = conn.execute("""
        SELECT h.id, h.traditional, h.simplified, h.pinyin, h.pos
        FROM headwords h
        WHERE NOT EXISTS (
            SELECT 1 FROM definitions d WHERE d.headword_id = h.id AND d.lang = ?
        )
        ORDER BY h.id
    """, (lang,)).fetchall()

    if limit:
        rows = rows[:limit]

    total = len(rows)
    print(f"  {total:,} headwords need {lang} translations")

    translated = 0
    for i in range(0, total, batch_size):
        batch_rows = rows[i:i + batch_size]

        # Build batch entries with context definitions
        entries = []
        for row in batch_rows:
            context = conn.execute(
                "SELECT lang, definition FROM definitions WHERE headword_id = ?",
                (row["id"],),
            ).fetchall()
            context_defs = {r["lang"]: r["definition"] for r in context}

            entries.append({
                "id": row["id"],
                "traditional": row["traditional"],
                "simplified": row["simplified"],
                "pinyin": row["pinyin"],
                "pos": row["pos"] or "",
                "context_defs": context_defs,
            })

        # Translate the batch
        try:
            results = translate_batch(entries, lang)
        except Exception as e:
            print(f"    ERROR at batch {i}: {e}")
            continue

        # Save results
        for entry, defn in zip(entries, results):
            if defn:
                upsert_definition(
                    conn, entry["id"], lang, defn, "minimax", confidence="medium"
                )
                translated += 1

        conn.commit()
        print(f"    [{i + len(batch_rows):,}/{total:,}] translated {translated:,}")

    update_source_count(conn, "minimax")
    conn.close()
    print(f"  Done: {translated:,} translations for {lang}")


def step_translate_universal(
    db_path: Path,
    backend: str = "ollama",
    batch_size: int = 20,
    limit: int | None = None,
    skip_corpus: bool = False,
    target_langs: list[str] | None = None,
    workers: int = 1,
    prompt_version: str = "v2",
) -> None:
    """Translate all headwords into all languages in one pass per batch.

    For each batch:
      1. Query all existing definitions for each headword
      2. Optionally fetch 1-2 corpus example sentences
      3. Call translate_universal_batch()
      4. Save all language definitions

    Checkpoint: skips headwords that already have source="minimax" definitions.
    With workers > 1, runs multiple API calls in parallel.
    """
    if backend == "groq":
        from tools.dictmaster.translate.groq_api import translate_universal_batch
    elif backend == "ollama":
        from tools.dictmaster.translate.minimax_ollama import translate_universal_batch
    else:
        from tools.dictmaster.translate.minimax_api import translate_universal_batch

    from tools.dictmaster.translate.prompts import ALL_TARGET_LANGS
    from tools.dictmaster.schema import ensure_source, upsert_definition

    source_name = "groq-kimi-k2" if backend == "groq" else "minimax"

    langs = target_langs or ALL_TARGET_LANGS

    conn = get_connection(db_path)
    ensure_source(conn, source_name)

    # Open corpus connection for example sentences
    corpus_conn = None
    if not skip_corpus:
        from tools.dictmaster.translate.corpus_context import (
            ZHCORPUS_DB_PATH,
            get_corpus_connection,
        )
        if ZHCORPUS_DB_PATH.exists():
            try:
                corpus_conn = get_corpus_connection()
                print("  Corpus DB connected for example sentences")
            except Exception as e:
                print(f"  WARNING: Could not open corpus DB: {e}")
                print("  Continuing without example sentences")
        else:
            print(f"  Corpus DB not found at {ZHCORPUS_DB_PATH}, skipping examples")

    # Find headwords that don't yet have definitions from this source
    rows = conn.execute("""
        SELECT h.id, h.traditional, h.simplified, h.pinyin, h.pos
        FROM headwords h
        WHERE NOT EXISTS (
            SELECT 1 FROM definitions d
            WHERE d.headword_id = h.id AND d.source = ?
        )
        ORDER BY h.id
    """, (source_name,)).fetchall()

    if limit:
        rows = rows[:limit]

    total = len(rows)
    print(f"  {total:,} headwords to translate into {len(langs)} languages")
    if workers > 1:
        print(f"  Using {workers} parallel workers")

    if total == 0:
        conn.close()
        if corpus_conn:
            corpus_conn.close()
        return

    translated_entries = 0
    translated_defs = 0
    t_start = time.time()

    def _prepare_batch(batch_rows):
        """Build entries list for a batch of headword rows."""
        entries = []
        for row in batch_rows:
            context = conn.execute(
                "SELECT lang, definition FROM definitions WHERE headword_id = ?",
                (row["id"],),
            ).fetchall()
            context_defs = {r["lang"]: r["definition"] for r in context}

            examples = None
            if corpus_conn:
                from tools.dictmaster.translate.corpus_context import get_example_sentences
                word = row["simplified"] or row["traditional"]
                examples = get_example_sentences(corpus_conn, word, limit=2)

            entries.append({
                "id": row["id"],
                "traditional": row["traditional"],
                "simplified": row["simplified"],
                "pinyin": row["pinyin"],
                "pos": row["pos"] or "",
                "context_defs": context_defs,
                "examples": examples,
            })
        return entries

    def _translate_one_batch(entries):
        """Send a single batch to the API. Thread-safe (no DB writes)."""
        return translate_universal_batch(entries, target_langs=langs)

    def _save_results(entries, results):
        """Save batch results to DB. Must be called from main thread."""
        nonlocal translated_entries, translated_defs
        for entry, lang_defs in zip(entries, results):
            if not lang_defs:
                continue
            for lang, defn in lang_defs.items():
                if defn and lang in langs:
                    upsert_definition(
                        conn, entry["id"], lang, defn, source_name,
                        confidence="medium", prompt_version=prompt_version,
                    )
                    translated_defs += 1
            translated_entries += 1

    if workers <= 1:
        # Sequential mode
        for i in range(0, total, batch_size):
            batch_rows = rows[i:i + batch_size]
            entries = _prepare_batch(batch_rows)

            try:
                results = _translate_one_batch(entries)
            except Exception as e:
                print(f"    ERROR at batch {i}: {e}")
                continue

            _save_results(entries, results)
            conn.commit()

            done = i + len(batch_rows)
            elapsed = time.time() - t_start
            rate = done / elapsed if elapsed > 0 else 0
            eta = (total - done) / rate if rate > 0 else 0
            print(
                f"    [{done:,}/{total:,}] "
                f"{translated_entries:,} entries, {translated_defs:,} defs "
                f"({rate:.1f} entries/s, ETA {eta / 60:.1f}m)"
            )
    else:
        # Parallel mode: prepare batches on main thread, API calls in workers
        from concurrent.futures import ThreadPoolExecutor, as_completed

        executor = ThreadPoolExecutor(max_workers=workers)
        pending = {}
        batch_entries = {}  # batch_idx -> entries (for saving results)
        next_batch_idx = 0
        completed_since_commit = 0
        progress_interval = batch_size * 10

        # Pre-prepare and submit initial batches
        for _ in range(min(workers * 2, (total + batch_size - 1) // batch_size)):
            if next_batch_idx >= total:
                break
            batch_rows = rows[next_batch_idx:next_batch_idx + batch_size]
            entries = _prepare_batch(batch_rows)
            batch_entries[next_batch_idx] = entries
            fut = executor.submit(_translate_one_batch, entries)
            pending[fut] = next_batch_idx
            next_batch_idx += batch_size

        # as_completed() snapshots its input — use a while loop so newly
        # submitted futures are picked up on each iteration.
        while pending:
            done_futures = set()
            for fut in as_completed(pending):
                done_futures.add(fut)
                break  # process one at a time so we can submit new work

            for fut in done_futures:
                bidx = pending.pop(fut)
                entries = batch_entries.pop(bidx)
                try:
                    results = fut.result()
                    _save_results(entries, results)
                    completed_since_commit += 1
                except Exception as e:
                    print(f"    ERROR at batch {bidx}: {e}")

                # Submit next batch (prepare on main thread, API call in worker)
                if next_batch_idx < total:
                    batch_rows = rows[next_batch_idx:next_batch_idx + batch_size]
                    new_entries = _prepare_batch(batch_rows)
                    batch_entries[next_batch_idx] = new_entries
                    new_fut = executor.submit(_translate_one_batch, new_entries)
                    pending[new_fut] = next_batch_idx
                    next_batch_idx += batch_size

            # Periodic commit
            if completed_since_commit >= workers * 2:
                conn.commit()
                completed_since_commit = 0

            # Progress reporting
            done = translated_entries
            if done % progress_interval < batch_size or not pending:
                elapsed = time.time() - t_start
                rate = done / elapsed if elapsed > 0 else 0
                eta = (total - done) / rate if rate > 0 else 0
                print(
                    f"    [{done:,}/{total:,}] "
                    f"{translated_entries:,} entries, {translated_defs:,} defs "
                    f"({rate:.1f} entries/s, ETA {eta / 60:.1f}m)"
                )

        # Final commit
        conn.commit()
        executor.shutdown(wait=False)

    update_source_count(conn, source_name)
    conn.close()
    if corpus_conn:
        corpus_conn.close()

    elapsed = time.time() - t_start
    print(
        f"  Done: {translated_entries:,} entries, {translated_defs:,} definitions "
        f"in {elapsed / 60:.1f}m"
    )


def step_export(db_path: Path) -> None:
    """Export per-language CEDICT files."""
    conn = get_connection(db_path)

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    results = export_all_languages(conn, EXPORT_DIR)

    for lang, path in sorted(results.items()):
        stats = export_stats(conn)
        count = stats.get(lang, 0)
        print(f"  {lang}: {count:,} entries -> {path}")

    conn.close()


def step_report(db_path: Path) -> None:
    """Print coverage report."""
    conn = get_connection(db_path)

    stats = get_stats(conn)
    print(f"  Headwords: {stats['headwords']:,}")
    print(f"  Definitions: {stats['definitions']:,}")
    print(f"  Languages: {', '.join(stats['languages'])}")

    report = get_coverage_report(conn)
    print(f"\n  Coverage by language:")
    for lang, info in sorted(report["coverage"].items()):
        print(f"    {lang}: {info['count']:,} ({info['pct']}%) from {info['sources']}")

    print(f"\n  Gaps (headwords without definitions):")
    for lang, gap in sorted(report["gaps"].items()):
        if gap > 0:
            print(f"    {lang}: {gap:,} missing")

    conn.close()


def step_dialect(db_path: Path, limit: int | None = None) -> None:
    """Import Cantonese and Hokkien dialect data."""
    conn = get_connection(db_path)
    init_db(conn)  # Ensure dialect_forms table exists

    # CC-Canto: Cantonese dictionary with definitions
    cccanto_path = RAW_DIR / "cantonese" / "cccanto-webdist.txt"
    if cccanto_path.exists():
        print(f"  Importing CC-Canto (yue) from {cccanto_path.name}...")
        t0 = time.time()
        count = import_cccanto(conn, cccanto_path, limit=limit)
        update_source_count(conn, "cccanto")
        print(f"    -> {count:,} dialect forms in {time.time() - t0:.1f}s")
    else:
        print(f"  SKIP CC-Canto: {cccanto_path} not found")

    # CC-CEDICT Cantonese Readings: pronunciation overlay
    readings_path = RAW_DIR / "cantonese" / "cccedict-canto-readings-150923.txt"
    if readings_path.exists():
        print(f"  Importing CC-CEDICT Cantonese readings (yue) from {readings_path.name}...")
        t0 = time.time()
        count = import_cccedict_readings(conn, readings_path, limit=limit)
        update_source_count(conn, "cccedict-readings")
        print(f"    -> {count:,} dialect forms in {time.time() - t0:.1f}s")
    else:
        print(f"  SKIP CC-CEDICT readings: {readings_path} not found")

    # iTaigi: Mandarin-Hokkien (CC0)
    itaigi_path = (
        RAW_DIR / "hokkien" / "ChhoeTaigiDatabase" / "ChhoeTaigiDatabase"
        / "ChhoeTaigi_iTaigiHoataiTuichiautian.csv"
    )
    if itaigi_path.exists():
        print(f"  Importing iTaigi (nan) from {itaigi_path.name}...")
        t0 = time.time()
        count = import_itaigi(conn, itaigi_path, limit=limit)
        update_source_count(conn, "itaigi")
        print(f"    -> {count:,} dialect forms in {time.time() - t0:.1f}s")
    else:
        print(f"  SKIP iTaigi: {itaigi_path} not found")

    # 台華線頂對照典: Mandarin-Hokkien (CC BY-SA 4.0)
    taihua_path = (
        RAW_DIR / "hokkien" / "ChhoeTaigiDatabase" / "ChhoeTaigiDatabase"
        / "ChhoeTaigi_TaihoaSoanntengTuichiautian.csv"
    )
    if taihua_path.exists():
        print(f"  Importing 台華對照典 (nan) from {taihua_path.name}...")
        t0 = time.time()
        count = import_taihua(conn, taihua_path, limit=limit)
        update_source_count(conn, "taihua")
        print(f"    -> {count:,} dialect forms in {time.time() - t0:.1f}s")
    else:
        print(f"  SKIP 台華對照典: {taihua_path} not found")

    # Additional ChhoeTaigi sources (Hokkien)
    chhoetaigi_sources = [
        ("kauiokpoo", "ChhoeTaigi_KauiokpooTaigiSutian.csv"),
        ("embree", "ChhoeTaigi_EmbreeTaiengSutian.csv"),
        ("maryknoll", "ChhoeTaigi_MaryknollTaiengSutian.csv"),
        ("taioankichhoo", "ChhoeTaigi_TaioanPehoeKichhooGiku.csv"),
    ]
    chhoetaigi_dir = (
        RAW_DIR / "hokkien" / "ChhoeTaigiDatabase" / "ChhoeTaigiDatabase"
    )
    for source_name, filename in chhoetaigi_sources:
        csv_path = chhoetaigi_dir / filename
        if csv_path.exists():
            print(f"  Importing {source_name} (nan) from {filename}...")
            t0 = time.time()
            count = import_chhoetaigi_generic(conn, csv_path, source_name, limit=limit)
            update_source_count(conn, source_name)
            print(f"    -> {count:,} dialect forms in {time.time() - t0:.1f}s")
        else:
            print(f"  SKIP {source_name}: {csv_path} not found")

    # Derive Hokkien single-char readings from 2-char compounds
    print("  Deriving Hokkien single-char readings from compounds...")
    t0 = time.time()
    count = derive_hokkien_from_compounds(conn, min_confidence=1)
    update_source_count(conn, "compound-derived")
    print(f"    -> {count:,} dialect forms in {time.time() - t0:.1f}s")

    # rime-cantonese: community-maintained char→Jyutping (CC BY 4.0)
    rime_path = RAW_DIR / "hokkien" / "rime-cantonese" / "jyut6ping3.chars.dict.yaml"
    if rime_path.exists():
        print(f"  Importing rime-cantonese (yue) from {rime_path.name}...")
        t0 = time.time()
        count = import_rime_cantonese(conn, rime_path, limit=limit)
        update_source_count(conn, "rime-cantonese")
        print(f"    -> {count:,} dialect forms in {time.time() - t0:.1f}s")
    else:
        print(f"  SKIP rime-cantonese: {rime_path} not found")

    # Unihan kCantonese: Unicode Consortium readings
    unihan_path = Path("/home/tim/repos/loqu8/nomad-builder/tools/chardata/raw/Unihan.zip")
    if unihan_path.exists():
        print(f"  Importing Unihan kCantonese (yue) from {unihan_path.name}...")
        t0 = time.time()
        count = import_unihan_cantonese(conn, unihan_path, limit=limit)
        update_source_count(conn, "unihan")
        print(f"    -> {count:,} dialect forms in {time.time() - t0:.1f}s")
    else:
        print(f"  SKIP Unihan: {unihan_path} not found")

    # Report
    total = conn.execute("SELECT COUNT(*) FROM dialect_forms").fetchone()[0]
    yue = conn.execute("SELECT COUNT(*) FROM dialect_forms WHERE dialect='yue'").fetchone()[0]
    nan = conn.execute("SELECT COUNT(*) FROM dialect_forms WHERE dialect='nan'").fetchone()[0]
    print(f"\n  Dialect forms total: {total:,} (Cantonese: {yue:,}, Hokkien: {nan:,})")

    # Per-source breakdown
    print("  Per-source:")
    for row in conn.execute(
        "SELECT source, COUNT(*) FROM dialect_forms GROUP BY source ORDER BY source"
    ):
        print(f"    {row[0]}: {row[1]:,}")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Build master multilingual Chinese dictionary")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="Database path")
    parser.add_argument("--step", choices=["import", "merge", "translate", "dialect", "export", "report", "all"],
                        default="all", help="Which step to run")
    parser.add_argument("--lang", default=None,
                        help="Target language for single-language translate (legacy mode)")
    parser.add_argument("--langs", default=None,
                        help="Comma-separated target languages for universal translate (default: all 11)")
    parser.add_argument("--backend", choices=["ollama", "api", "groq"], default="groq",
                        help="Translation backend (groq=Kimi K2 on Groq, api=MiniMax, ollama=local)")
    parser.add_argument("--limit", type=int, default=None, help="Limit entries for testing")
    parser.add_argument("--batch-size", type=int, default=20, help="Batch size for translation")
    parser.add_argument("--skip-corpus", action="store_true",
                        help="Skip corpus example sentence lookups (faster)")
    parser.add_argument("--workers", type=int, default=1,
                        help="Parallel API workers for universal translate (default: 1)")
    parser.add_argument("--prompt-version", default="v2",
                        help="Prompt version tag stored with definitions (default: v2)")
    args = parser.parse_args()

    # Ensure DB directory exists
    args.db.parent.mkdir(parents=True, exist_ok=True)

    if args.step in ("import", "all"):
        print("Step 1: Import")
        step_import(args.db, args.limit)

    if args.step in ("merge", "all"):
        print("Step 2: Merge")
        step_merge(args.db)

    if args.step == "translate":
        if args.lang:
            # Legacy single-language mode
            print(f"Step 3: Translate ({args.lang})")
            step_translate(args.db, args.lang, args.backend, args.batch_size, args.limit)
        else:
            # Universal mode: all languages at once
            target_langs = args.langs.split(",") if args.langs else None
            lang_desc = ",".join(target_langs) if target_langs else "all"
            print(f"Step 3: Universal Translate ({lang_desc})")
            step_translate_universal(
                args.db,
                backend=args.backend,
                batch_size=args.batch_size,
                limit=args.limit,
                skip_corpus=args.skip_corpus,
                target_langs=target_langs,
                workers=args.workers,
                prompt_version=args.prompt_version,
            )

    if args.step in ("dialect",):
        print("Step 3b: Dialect Import (Cantonese + Hokkien)")
        step_dialect(args.db, args.limit)

    if args.step in ("export", "all"):
        print("Step 4: Export")
        step_export(args.db)

    if args.step in ("report", "all"):
        print("Step 5: Report")
        step_report(args.db)


if __name__ == "__main__":
    main()
