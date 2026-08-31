#!/usr/bin/env python3
"""Path C: HY-MT-1.8B translation + SimAlign word alignment.

Two-pass:
  1. HY-MT-1.8B translates zh -> en (simple translate-only prompt)
  2. SimAlign (XLM-R-base) aligns (source_tokens, target_tokens)

Writes results in the same {t, a} format used by Phase 1 so the existing
scorer (tools/score_alignment.py) just works.

Usage:
    .venv/bin/python tools/run_path_c.py --test-set pilot
"""

import argparse
import json
import time
import warnings
from pathlib import Path

import httpx
import jieba

warnings.filterwarnings("ignore")

OLLAMA_URL = "http://localhost:11434"
PILOT = Path("data/alignment_eval/pilot.jsonl")
RESULTS_DIR = Path("data/alignment_eval/results")


def hymt_translate(client: httpx.Client, text: str, target_lang: str = "en") -> dict:
    """Translate with HY-MT-1.8B using the same prompt as the MT eval."""
    target_name = {"en": "English", "de": "German", "ja": "Japanese", "ko": "Korean"}.get(target_lang, target_lang)
    # HY-MT works best with bare-message translate-only prompt
    messages = [{"role": "user",
                 "content": f"Translate the following Chinese to {target_name}:\n{text}"}]
    t0 = time.time()
    r = client.post(
        f"{OLLAMA_URL}/api/chat",
        json={"model": "hy-mt-1.8b:latest", "messages": messages,
              "stream": False, "options": {"temperature": 0.0, "num_predict": 256}},
        timeout=120,
    )
    r.raise_for_status()
    return {
        "translation": r.json()["message"]["content"].strip(),
        "elapsed_s": round(time.time() - t0, 3),
    }


def tokenize_zh(text: str) -> list[str]:
    """Word-segment Chinese with jieba; drop pure whitespace."""
    return [t for t in jieba.cut(text) if t.strip()]


def tokenize_en(text: str) -> list[str]:
    """Whitespace tokenize; strip trailing punctuation off tokens for cleaner alignment.
    Keep the punctuation as separate token if attached."""
    out = []
    for w in text.split():
        # Pull off trailing/leading punctuation
        i, j = 0, len(w)
        while i < j and not w[i].isalnum() and w[i] not in "'-":
            out.append(w[i]); i += 1
        # Find tail punct
        k = j
        while k > i and not w[k-1].isalnum() and w[k-1] not in "'-":
            k -= 1
        if i < k:
            out.append(w[i:k])
        for ch in w[k:j]:
            out.append(ch)
    return [t for t in out if t.strip()]


def pairs_to_a(src_tokens: list[str], tgt_tokens: list[str],
               alignment_pairs: list[tuple[int, int]]) -> list[list[str]]:
    """Convert SimAlign (i, j) pairs to [[zh_word, en_word], ...] in source order.

    For source tokens with multiple alignments, group target words by closest
    contiguous run. For unaligned source tokens, emit ['zh_word', ''].
    """
    by_src: dict[int, list[int]] = {}
    for i, j in alignment_pairs:
        by_src.setdefault(i, []).append(j)
    a: list[list[str]] = []
    for i, src in enumerate(src_tokens):
        if i in by_src:
            tgt_idxs = sorted(set(by_src[i]))
            tgt_phrase = " ".join(tgt_tokens[j] for j in tgt_idxs)
            a.append([src, tgt_phrase])
        else:
            # Function words / unaligned — keep with empty target like iCE prompt asks
            a.append([src, ""])
    return a


def run(test_set: Path) -> Path:
    from simalign import SentenceAligner

    items = [json.loads(l) for l in test_set.open()]
    print(f"Loading SimAlign (xlm-roberta-base)...")
    t0 = time.time()
    # SimAlign letter→method mapping (verified empirically): m=mwmf, i=itermax,
    # a=inter (intersection). Confusingly named. We use intersection — sparser,
    # higher precision, what alignment papers usually report.
    aligner = SentenceAligner(model="xlm-roberta-base", token_type="bpe",
                              matching_methods="a", device="cpu")
    print(f"  ready in {time.time()-t0:.1f}s")

    out_path = RESULTS_DIR / f"pilot_path-c_en.jsonl"
    rows: list[dict] = []
    with httpx.Client() as http:
        for it in items:
            # 1) HY-MT translation
            tr = hymt_translate(http, it["text"], "en")
            translation = tr["translation"]
            t_translate_s = tr["elapsed_s"]

            # 2) SimAlign on tokenized pair
            src_tokens = tokenize_zh(it["text"])
            tgt_tokens = tokenize_en(translation)
            t_a = time.time()
            pairs = []
            err = None
            try:
                pairs = aligner.get_word_aligns(src_tokens, tgt_tokens)["inter"]
                a = pairs_to_a(src_tokens, tgt_tokens, pairs)
            except Exception as e:
                a = []
                err = str(e)
            t_align_s = round(time.time() - t_a, 3)

            # 3) Pack as {t, a} JSON to match Phase 1 raw format
            raw_obj = {"t": translation, "a": [["s:" + s, "t:" + t] for s, t in a]}
            raw = json.dumps(raw_obj, ensure_ascii=False)

            row = {
                "id": it["id"],
                "source": it.get("source", ""),
                "text": it["text"],
                "char_count": it.get("char_count", len(it["text"])),
                "system": "path-c",
                "target_lang": "en",
                "raw": raw,
                "elapsed_s": round(t_translate_s + t_align_s, 3),
                "elapsed_translate_s": t_translate_s,
                "elapsed_align_s": t_align_s,
                "error": err,
            }
            rows.append(row)
            print(f"  [{it['id'][:25]:<25}] tr={t_translate_s:>5.2f}s "
                  f"al={t_align_s:>5.2f}s  src_toks={len(src_tokens):>2} "
                  f"tgt_toks={len(tgt_tokens):>2}  pairs={len(pairs) if not err else '-'} "
                  f"trans={translation[:50]!r}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"\nWrote {out_path} ({len(rows)} rows)")
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-set", default="pilot")
    args = ap.parse_args()
    test_path = PILOT if args.test_set == "pilot" else Path(
        f"data/alignment_eval/{args.test_set}.jsonl")
    run(test_path)


if __name__ == "__main__":
    main()
