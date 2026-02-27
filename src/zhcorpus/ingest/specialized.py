"""Import specialized domain corpora into zhcorpus.

Handles: webtext2019zh (Q&A), LCCC (dialogues), CAIL2018 (legal),
translation2019zh (bilingual), baike2018qa (encyclopedic Q&A),
CSL (scientific), Laws (statutes), cMedQA2 + medical dialogues,
OpenSubtitles (film/TV).
"""

import csv
import json
import sqlite3
from pathlib import Path
from typing import Iterator, Tuple

from zhcorpus.db import ensure_source, insert_article, insert_chunk
from zhcorpus.ingest.chunker import chunk_text


def _import_iter(
    conn: sqlite3.Connection,
    source_name: str,
    description: str,
    articles_iter: Iterator[Tuple[str, str, str]],
    limit: int = 0,
    batch_size: int = 5000,
    progress_fn=None,
) -> Tuple[int, int]:
    """Generic import from an (article_id, title, text) iterator."""
    source_id = ensure_source(conn, source_name, description)
    articles = 0
    chunks = 0

    for article_id, title, text in articles_iter:
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
                progress_fn(source_name, articles, chunks)

    conn.commit()
    conn.execute(
        "UPDATE sources SET article_count = ?, chunk_count = ? WHERE id = ?",
        (articles, chunks, source_id),
    )
    conn.commit()
    return articles, chunks


# ---- webtext2019zh (Community Q&A) ----

def iter_webtext2019zh(base_dir: Path) -> Iterator[Tuple[str, str, str]]:
    """Iterate webtext2019zh JSONL files.

    Fields: qid, title, desc, topic, star, content, answer_id, answerer_tags
    We use the answer content as the text body.
    """
    for json_file in sorted(base_dir.glob("web_text_zh_*.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                qid = str(obj.get("qid", ""))
                title = obj.get("title", "") or ""
                content = obj.get("content", "") or ""
                if not content.strip():
                    continue
                # Combine question title + answer for richer context
                text = content
                yield qid, title, text


def import_webtext2019zh(
    conn: sqlite3.Connection,
    base_dir: Path,
    limit: int = 0,
    progress_fn=None,
) -> Tuple[int, int]:
    return _import_iter(
        conn, "webtext2019zh",
        "brightmart Q&A: 4.1M answers across 28K topics",
        iter_webtext2019zh(base_dir),
        limit=limit, progress_fn=progress_fn,
    )


# ---- LCCC (Conversational Chinese) ----

def iter_lccc(json_path: Path) -> Iterator[Tuple[str, str, str]]:
    """Iterate LCCC dialogues.

    The file is a JSON array of dialogues, where each dialogue is a list
    of utterance strings (may be space-tokenized).
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for i, dialogue in enumerate(data):
        if not isinstance(dialogue, list) or len(dialogue) < 2:
            continue
        # Remove word segmentation spaces
        turns = [turn.replace(" ", "") for turn in dialogue]
        text = "\n".join(turns)
        if not text.strip():
            continue
        # Use first utterance as title (truncated)
        title = turns[0][:50]
        yield str(i), title, text


def import_lccc(
    conn: sqlite3.Connection,
    json_path: Path,
    limit: int = 0,
    progress_fn=None,
) -> Tuple[int, int]:
    return _import_iter(
        conn, "lccc",
        "LCCC-large: 12M Weibo dialogues, conversational Chinese",
        iter_lccc(json_path),
        limit=limit, progress_fn=progress_fn,
    )


# ---- CAIL2018 (Legal Cases) ----

def iter_cail2018(base_dir: Path) -> Iterator[Tuple[str, str, str]]:
    """Iterate CAIL2018 legal case JSONL files.

    Fields: fact, meta (with relevant_articles, accusation, etc.)
    """
    json_files = sorted(base_dir.rglob("*.json"))
    for json_file in json_files:
        if json_file.name == "README.md":
            continue
        with open(json_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                fact = obj.get("fact", "") or ""
                if not fact.strip():
                    continue
                article_id = f"{json_file.stem}/{line_num}"
                # Extract accusation for title if available
                meta = obj.get("meta", {}) or {}
                accusations = meta.get("accusation", []) or []
                if isinstance(accusations, list) and accusations:
                    title = "、".join(str(a) for a in accusations[:3])
                else:
                    title = fact[:50]
                yield article_id, title, fact


def import_cail2018(
    conn: sqlite3.Connection,
    base_dir: Path,
    limit: int = 0,
    progress_fn=None,
) -> Tuple[int, int]:
    return _import_iter(
        conn, "cail2018",
        "CAIL2018: 2.6M criminal case descriptions with charges",
        iter_cail2018(base_dir),
        limit=limit, progress_fn=progress_fn,
    )


# ---- translation2019zh (Bilingual Parallel) ----

def iter_translation2019zh(base_dir: Path) -> Iterator[Tuple[str, str, str]]:
    """Iterate translation2019zh JSONL files.

    Fields: english, chinese
    We store the Chinese text as the chunk, with English in the title.
    """
    for json_file in sorted(base_dir.glob("translation2019zh_*.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                chinese = obj.get("chinese", "") or ""
                english = obj.get("english", "") or ""
                if not chinese.strip():
                    continue
                article_id = f"{json_file.stem}/{line_num}"
                title = english[:80] if english else chinese[:50]
                yield article_id, title, chinese


def import_translation2019zh(
    conn: sqlite3.Connection,
    base_dir: Path,
    limit: int = 0,
    progress_fn=None,
) -> Tuple[int, int]:
    return _import_iter(
        conn, "translation2019zh",
        "brightmart: 5.2M zh-en parallel sentence pairs",
        iter_translation2019zh(base_dir),
        limit=limit, progress_fn=progress_fn,
    )


# ---- baike2018qa (Encyclopedic Q&A) ----

def iter_baike2018qa(base_dir: Path) -> Iterator[Tuple[str, str, str]]:
    """Iterate baike2018qa JSONL files.

    Fields: qid, category, title, desc, answer
    """
    for json_file in sorted(base_dir.glob("baike_qa_*.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                qid = str(obj.get("qid", ""))
                title = obj.get("title", "") or ""
                answer = obj.get("answer", "") or ""
                if not answer.strip():
                    continue
                yield qid, title, answer


def import_baike2018qa(
    conn: sqlite3.Connection,
    base_dir: Path,
    limit: int = 0,
    progress_fn=None,
) -> Tuple[int, int]:
    return _import_iter(
        conn, "baike2018qa",
        "brightmart: 1.5M encyclopedic Q&A pairs, 492 categories",
        iter_baike2018qa(base_dir),
        limit=limit, progress_fn=progress_fn,
    )


# ---- CSL (Scientific Abstracts) ----

def iter_csl(tsv_path: Path) -> Iterator[Tuple[str, str, str]]:
    """Iterate CSL scientific abstracts TSV.

    Tab-separated: title, abstract, keywords, discipline, category
    """
    with open(tsv_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f):
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2:
                continue
            title = parts[0]
            abstract = parts[1]
            if not abstract.strip():
                continue
            # Include keywords in text for better searchability
            keywords = parts[2] if len(parts) > 2 else ""
            text = abstract
            if keywords:
                text = abstract + "\n关键词：" + keywords.replace("_", "、")
            yield str(line_num), title, text


def import_csl(
    conn: sqlite3.Connection,
    tsv_path: Path,
    limit: int = 0,
    progress_fn=None,
) -> Tuple[int, int]:
    return _import_iter(
        conn, "csl",
        "CSL: 396K Chinese scientific paper abstracts, 13 categories",
        iter_csl(tsv_path),
        limit=limit, progress_fn=progress_fn,
    )


# ---- LawRefBook/Laws ----

def iter_laws(base_dir: Path) -> Iterator[Tuple[str, str, str]]:
    """Iterate Chinese law markdown files.

    Directory structure: category/law_name.md
    """
    # Legal category directories
    for md_file in sorted(base_dir.rglob("*.md")):
        if md_file.name in ("README.md", "法律法规模版.md"):
            continue
        text = md_file.read_text(encoding="utf-8").strip()
        if not text or len(text) < 20:
            continue
        rel = md_file.relative_to(base_dir)
        parts = rel.parts
        article_id = "/".join(parts)
        title = md_file.stem
        yield article_id, title, text


def import_laws(
    conn: sqlite3.Connection,
    base_dir: Path,
    limit: int = 0,
    progress_fn=None,
) -> Tuple[int, int]:
    return _import_iter(
        conn, "laws",
        "LawRefBook: PRC laws and regulations (刑法/民法典/宪法/etc)",
        iter_laws(base_dir),
        limit=limit, progress_fn=progress_fn,
    )


# ---- cMedQA2 (Medical Q&A) ----

def iter_cmedqa2(base_dir: Path) -> Iterator[Tuple[str, str, str]]:
    """Iterate cMedQA2 question and answer files."""
    import zipfile

    # Questions
    q_zip = base_dir / "question.zip"
    if q_zip.exists():
        with zipfile.ZipFile(q_zip) as zf:
            for name in zf.namelist():
                if not name.endswith(".csv"):
                    continue
                with zf.open(name) as f:
                    reader = csv.DictReader(
                        (line.decode("utf-8") for line in f)
                    )
                    for row in reader:
                        qid = row.get("question_id", "") or ""
                        content = row.get("content", "") or ""
                        if content.strip():
                            yield f"q/{qid}", f"问：{content[:50]}", content

    # Answers
    a_zip = base_dir / "answer.zip"
    if a_zip.exists():
        with zipfile.ZipFile(a_zip) as zf:
            for name in zf.namelist():
                if not name.endswith(".csv"):
                    continue
                with zf.open(name) as f:
                    reader = csv.DictReader(
                        (line.decode("utf-8") for line in f)
                    )
                    for row in reader:
                        aid = row.get("ans_id", "") or ""
                        content = row.get("content", "") or ""
                        if content.strip():
                            yield f"a/{aid}", f"答：{content[:50]}", content


def import_cmedqa2(
    conn: sqlite3.Connection,
    base_dir: Path,
    limit: int = 0,
    progress_fn=None,
) -> Tuple[int, int]:
    return _import_iter(
        conn, "cmedqa2",
        "cMedQA2: 108K medical questions + 203K answers",
        iter_cmedqa2(base_dir),
        limit=limit, progress_fn=progress_fn,
    )


# ---- Chinese Medical Dialogues ----

def iter_medical_dialogues(base_dir: Path) -> Iterator[Tuple[str, str, str]]:
    """Iterate Chinese medical dialogue CSVs (GBK-encoded).

    Fields: department, title, ask, answer
    """
    data_dir = base_dir / "Data_数据"
    if not data_dir.exists():
        return

    for dept_dir in sorted(data_dir.iterdir()):
        if not dept_dir.is_dir():
            continue
        dept_name = dept_dir.name.split("_")[-1] if "_" in dept_dir.name else dept_dir.name
        for csv_file in sorted(dept_dir.glob("*.csv")):
            try:
                with open(csv_file, "r", encoding="gbk", errors="replace") as f:
                    reader = csv.DictReader(f)
                    for i, row in enumerate(reader):
                        title = row.get("title", "") or ""
                        ask = row.get("ask", "") or ""
                        answer = row.get("answer", "") or ""
                        # Combine Q&A for richer context
                        text = ""
                        if ask.strip():
                            text += "问：" + ask.strip() + "\n"
                        if answer.strip():
                            text += "答：" + answer.strip()
                        if not text.strip():
                            continue
                        article_id = f"{dept_name}/{csv_file.stem}/{i}"
                        yield article_id, title or f"{dept_name}问答", text
            except (csv.Error, UnicodeDecodeError):
                continue


def import_medical_dialogues(
    conn: sqlite3.Connection,
    base_dir: Path,
    limit: int = 0,
    progress_fn=None,
) -> Tuple[int, int]:
    return _import_iter(
        conn, "medical_dialogues",
        "Chinese medical dialogues: ~800K across 6 departments",
        iter_medical_dialogues(base_dir),
        limit=limit, progress_fn=progress_fn,
    )


# ---- OpenSubtitles zh_cn ----

def iter_subtitles(txt_path: Path, group_size: int = 5) -> Iterator[Tuple[str, str, str]]:
    """Iterate OpenSubtitles zh_cn plain text.

    Groups consecutive subtitle lines into passages for better context.
    Individual subtitle lines are very short and often fragment sentences.
    """
    buffer = []
    group_num = 0

    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            buffer.append(line)
            if len(buffer) >= group_size:
                text = "\n".join(buffer)
                title = buffer[0][:50]
                yield str(group_num), title, text
                buffer = []
                group_num += 1

    # Remaining lines
    if buffer:
        text = "\n".join(buffer)
        title = buffer[0][:50]
        yield str(group_num), title, text


def import_subtitles(
    conn: sqlite3.Connection,
    txt_path: Path,
    limit: int = 0,
    progress_fn=None,
) -> Tuple[int, int]:
    return _import_iter(
        conn, "subtitles",
        "OpenSubtitles v2018 zh_cn: 16.3M subtitle lines (film/TV)",
        iter_subtitles(txt_path),
        limit=limit, progress_fn=progress_fn,
    )
