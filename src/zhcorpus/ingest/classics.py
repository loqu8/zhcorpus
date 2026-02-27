"""Import classical Chinese texts from NiuTrans/Classical-Modern and chinese-poetry.

NiuTrans/Classical-Modern structure:
    双语数据/<book>/<chapter>/source.txt  (classical Chinese, one sentence per line)
    双语数据/<book>/<chapter>/target.txt  (modern Chinese translation)
    古文原文/<book>/<chapter>/text.txt    (classical Chinese only)

chinese-poetry structure:
    全唐诗/poet.tang.*.json   — [{author, title, paragraphs, id}, ...]
    宋词/ci.song.*.json       — [{author, rhythmic, paragraphs}, ...]
    楚辞/chuci.json           — [{title, section, content}, ...]
    蒙学/tangshisanbaishou.json, guwenguanzhi.json, etc.
    四书五经/daxue.json, mengzi.json, zhongyong.json
    论语/lunyu.json
    诗经/shijing.json
"""

import json
import sqlite3
from pathlib import Path
from typing import Iterator, Tuple

from zhcorpus.db import ensure_source, insert_article, insert_chunk
from zhcorpus.ingest.chunker import chunk_text


def iter_niutrans_bilingual(base_dir: Path) -> Iterator[Tuple[str, str, str]]:
    """Iterate bilingual texts (source.txt = classical Chinese).

    Handles nested structures like 老子/道经/第一章/source.txt
    and flat structures like 论语/学而篇/source.txt.

    Yields (article_id, title, text) tuples.
    """
    bilingual = base_dir / "双语数据"
    if not bilingual.exists():
        return

    for source_file in sorted(bilingual.rglob("source.txt")):
        text = source_file.read_text(encoding="utf-8").strip()
        if not text:
            continue
        # Build path relative to bilingual dir, minus the filename
        rel = source_file.parent.relative_to(bilingual)
        parts = rel.parts  # e.g. ("老子", "道经", "第一章")
        article_id = "/".join(parts)
        title = "·".join(parts)
        yield article_id, title, text


def iter_niutrans_raw(base_dir: Path) -> Iterator[Tuple[str, str, str]]:
    """Iterate raw classical texts (text.txt files).

    Only yields texts from books NOT in the bilingual set (to avoid duplicates).

    Yields (article_id, title, text) tuples.
    """
    raw_dir = base_dir / "古文原文"
    bilingual_dir = base_dir / "双语数据"
    if not raw_dir.exists():
        return

    # Collect bilingual book names to skip duplicates
    bilingual_books = set()
    if bilingual_dir.exists():
        bilingual_books = {d.name for d in bilingual_dir.iterdir() if d.is_dir()}

    for text_file in sorted(raw_dir.rglob("text.txt")):
        rel = text_file.parent.relative_to(raw_dir)
        parts = rel.parts
        if not parts:
            continue

        # Skip books already in bilingual set
        book_name = parts[0]
        if book_name in bilingual_books:
            continue

        text = text_file.read_text(encoding="utf-8").strip()
        if not text:
            continue

        article_id = "/".join(parts)
        title = "·".join(parts)
        yield article_id, title, text


def iter_poetry_json(base_dir: Path) -> Iterator[Tuple[str, str, str]]:
    """Iterate chinese-poetry JSON files.

    Handles multiple formats:
    - Tang/Song poems: [{author, title, paragraphs}, ...]
    - Ci: [{author, rhythmic, paragraphs}, ...]
    - Chuci: [{title, section, content}, ...]
    - Classics (四书五经, 蒙学): [{chapter, paragraphs}, ...]

    Yields (article_id, title, text) tuples.
    """
    # Poetry collections with standard format
    poetry_dirs = {
        "全唐诗": "tangshi",
        "御定全唐詩": "yudingqts",
        "宋词": "songci",
        "五代诗词": "wudai",
        "元曲": "yuanqu",
    }

    for dir_name, prefix in poetry_dirs.items():
        poetry_dir = base_dir / dir_name
        if not poetry_dir.exists():
            continue
        for json_file in sorted(poetry_dir.glob("*.json")):
            if json_file.name.startswith("author") or json_file.name == "README.md":
                continue
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if not isinstance(data, list):
                continue
            for item in data:
                author = item.get("author", "") or ""
                title = item.get("title", "") or item.get("rhythmic", "") or ""
                paragraphs = item.get("paragraphs", []) or []
                if isinstance(paragraphs, list):
                    text = "\n".join(paragraphs)
                else:
                    text = str(paragraphs)
                if text.strip():
                    display_title = f"{title}（{author}）" if author else title
                    yield f"{prefix}/{title}/{author}", display_title, text

    # Chuci
    chuci_file = base_dir / "楚辞" / "chuci.json"
    if chuci_file.exists():
        try:
            data = json.loads(chuci_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for item in data:
                    title = item.get("title", "") or ""
                    section = item.get("section", "") or ""
                    content = item.get("content", []) or []
                    if isinstance(content, list):
                        text = "\n".join(content)
                    else:
                        text = str(content)
                    if text.strip():
                        display = f"楚辞·{section}·{title}" if section else f"楚辞·{title}"
                        yield f"chuci/{section}/{title}", display, text
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    # 四书五经
    for json_file in sorted((base_dir / "四书五经").glob("*.json")) if (base_dir / "四书五经").exists() else []:
        yield from _yield_from_classic_json(json_file, "四书五经")

    # 蒙学 (traditional education texts)
    for json_file in sorted((base_dir / "蒙学").glob("*.json")) if (base_dir / "蒙学").exists() else []:
        yield from _yield_from_classic_json(json_file, "蒙学")

    # 论语
    lunyu_file = base_dir / "论语" / "lunyu.json"
    if lunyu_file.exists():
        yield from _yield_from_classic_json(lunyu_file, "论语")

    # 诗经
    shijing_file = base_dir / "诗经" / "shijing.json"
    if shijing_file.exists():
        yield from _yield_from_classic_json(shijing_file, "诗经")


def _yield_from_classic_json(
    json_file: Path, collection: str
) -> Iterator[Tuple[str, str, str]]:
    """Parse a classic text JSON file (various formats)."""
    try:
        data = json.loads(json_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return

    stem = json_file.stem

    if isinstance(data, list):
        for i, item in enumerate(data):
            title = item.get("title", "") or item.get("chapter", "") or f"{stem}_{i}"
            paragraphs = item.get("paragraphs", []) or item.get("content", []) or []
            if isinstance(paragraphs, list):
                text = "\n".join(str(p) for p in paragraphs)
            else:
                text = str(paragraphs)
            if text.strip():
                yield f"{collection}/{stem}/{title}", f"{collection}·{title}", text
    elif isinstance(data, dict):
        # Some files have a top-level dict with chapter keys
        for key, value in data.items():
            if isinstance(value, list):
                text = "\n".join(str(p) for p in value)
            elif isinstance(value, str):
                text = value
            else:
                continue
            if text.strip():
                yield f"{collection}/{stem}/{key}", f"{collection}·{key}", text


def import_classics(
    conn: sqlite3.Connection,
    niutrans_dir: Path | None = None,
    poetry_dir: Path | None = None,
    limit: int = 0,
    batch_size: int = 5000,
    progress_fn=None,
) -> Tuple[int, int]:
    """Import classical Chinese texts into zhcorpus.

    Args:
        conn: zhcorpus database connection.
        niutrans_dir: Path to NiuTrans/Classical-Modern repo root.
        poetry_dir: Path to chinese-poetry repo root.
        limit: Max articles (0 = all).
        batch_size: Commit every N articles.
        progress_fn: Optional callback(articles, chunks).

    Returns:
        (articles_imported, chunks_imported)
    """
    articles = 0
    chunks = 0

    # Import NiuTrans classical prose
    if niutrans_dir and niutrans_dir.exists():
        source_id = ensure_source(
            conn, "classics_prose",
            "NiuTrans/Classical-Modern: 327 classical Chinese texts"
        )

        # Bilingual texts first (have source.txt)
        for article_id, title, text in iter_niutrans_bilingual(niutrans_dir):
            if limit > 0 and articles >= limit:
                break
            aid = insert_article(conn, source_id, article_id, title, len(text))
            for idx, sentence in enumerate(chunk_text(text)):
                insert_chunk(conn, aid, idx, sentence)
                chunks += 1
            articles += 1
            if articles % batch_size == 0:
                conn.commit()
                if progress_fn:
                    progress_fn(articles, chunks)

        # Raw-only texts (not in bilingual set)
        if limit == 0 or articles < limit:
            for article_id, title, text in iter_niutrans_raw(niutrans_dir):
                if limit > 0 and articles >= limit:
                    break
                aid = insert_article(conn, source_id, article_id, title, len(text))
                for idx, sentence in enumerate(chunk_text(text)):
                    insert_chunk(conn, aid, idx, sentence)
                    chunks += 1
                articles += 1
                if articles % batch_size == 0:
                    conn.commit()
                    if progress_fn:
                        progress_fn(articles, chunks)

        conn.commit()
        conn.execute(
            "UPDATE sources SET article_count = ?, chunk_count = ? WHERE id = ?",
            (articles, chunks, source_id),
        )
        conn.commit()

    # Import chinese-poetry
    if poetry_dir and poetry_dir.exists():
        poetry_articles = 0
        poetry_chunks = 0
        source_id = ensure_source(
            conn, "classics_poetry",
            "chinese-poetry: Tang/Song poetry, 楚辞, 四书五经, 蒙学"
        )

        for article_id, title, text in iter_poetry_json(poetry_dir):
            if limit > 0 and (articles + poetry_articles) >= limit:
                break
            aid = insert_article(conn, source_id, article_id, title, len(text))
            for idx, sentence in enumerate(chunk_text(text)):
                insert_chunk(conn, aid, idx, sentence)
                poetry_chunks += 1
            poetry_articles += 1
            if poetry_articles % batch_size == 0:
                conn.commit()
                if progress_fn:
                    progress_fn(articles + poetry_articles, chunks + poetry_chunks)

        conn.commit()
        conn.execute(
            "UPDATE sources SET article_count = ?, chunk_count = ? WHERE id = ?",
            (poetry_articles, poetry_chunks, source_id),
        )
        conn.commit()

        articles += poetry_articles
        chunks += poetry_chunks

    return articles, chunks
