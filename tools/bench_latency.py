#!/usr/bin/env python3
"""Latency + throughput benchmark for HY-MT models via Ollama.

For iCE Pro bundle decision: how long does a popup translation take?
Measures cold-start (first call after load) and warm latency (median, p95).

NOTE: Ollama runs on the Windows host accessible at localhost:11434.
RAM/VRAM stats reflect THIS host's load, not the Loqu8 QA box. For
production sizing, re-run on the target hardware (10.1.10.101).

Usage:
    .venv/bin/python tools/bench_latency.py --model hy-mt-1.8b
    .venv/bin/python tools/bench_latency.py --all
"""

import argparse
import json
import statistics
import time
import urllib.request
from pathlib import Path

import psutil  # type: ignore

OLLAMA = "http://localhost:11434"

# Representative iCE popup payloads (10-40 chars, mixed genres)
SAMPLES = [
    "当地媒体报道，一辆机场消防车在响应火警时翻了车。",
    "这家公司去年的营业收入增长了百分之十五。",
    "他在床上辗转反侧，怎么也睡不着。",
    "古之学者必有师。师者，所以传道授业解惑也。",
    "新政策将于下个月一日正式实施。",
    "孩子们在公园里玩得很开心。",
    "他的论文获得了优秀毕业论文奖。",
    "市场上的水果价格最近上涨了不少。",
    "她终于通过了驾照考试。",
    "今天的会议安排在下午三点开始。",
]


def chat(model: str, text: str, target_lang: str = "English") -> tuple[float, str]:
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system",
             "content": f"You are a professional Chinese-to-{target_lang} translator. "
                        "Respond ONLY with the translation."},
            {"role": "user",
             "content": f"Translate the following segment into {target_lang}, "
                        f"without additional explanation.\n\n{text}"},
        ],
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 256},
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA}/api/chat", data=body,
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read())
    return (time.time() - t0, data["message"]["content"].strip())


def unload(model: str) -> None:
    """Force Ollama to unload the model so the next call is a true cold start."""
    body = json.dumps({"model": model, "keep_alive": 0}).encode()
    req = urllib.request.Request(
        f"{OLLAMA}/api/generate", data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=10).read()
    except Exception:
        pass


def bench(model: str) -> dict:
    print(f"\n=== {model} ===")
    print("Unloading any prior copy...")
    unload(model)

    # Capture host RAM/VRAM stats
    mem_before = psutil.virtual_memory()
    print(f"Host RAM: {mem_before.used / 1e9:.1f} GB used / {mem_before.total / 1e9:.1f} GB")

    # Cold-start call (model not in memory)
    print("Cold-start call...")
    cold_s, cold_out = chat(model, SAMPLES[0])
    print(f"  cold: {cold_s:.1f}s  -> {cold_out[:80]}")

    mem_loaded = psutil.virtual_memory()
    delta_mb = (mem_loaded.used - mem_before.used) / 1e6
    print(f"Host RAM after load: {mem_loaded.used / 1e9:.1f} GB (delta {delta_mb:+.0f} MB)")

    # Warm calls
    print("Warm calls (10 samples)...")
    warm_times: list[float] = []
    for i, text in enumerate(SAMPLES):
        t, out = chat(model, text)
        warm_times.append(t)
        print(f"  [{i + 1}/10] {t:.2f}s  src={len(text)}ch  hyp={out[:60]}")

    warm_times.sort()
    return {
        "model": model,
        "cold_start_s": round(cold_s, 2),
        "warm_min_s": round(warm_times[0], 2),
        "warm_median_s": round(statistics.median(warm_times), 2),
        "warm_mean_s": round(statistics.mean(warm_times), 2),
        "warm_p95_s": round(warm_times[int(len(warm_times) * 0.95)], 2),
        "warm_max_s": round(warm_times[-1], 2),
        "host_ram_delta_mb": round(delta_mb, 0),
        "host_ram_used_gb": round(mem_loaded.used / 1e9, 1),
        "host_ram_total_gb": round(mem_loaded.total / 1e9, 1),
        "samples_n": len(SAMPLES),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=None,
                   help="Ollama model name (e.g. hy-mt-1.8b)")
    p.add_argument("--all", action="store_true",
                   help="Benchmark both hy-mt-1.8b and hy-mt-7b")
    p.add_argument("--out", default="data/mt_eval/latency_bench.json")
    args = p.parse_args()

    models = ["hy-mt-1.8b", "hy-mt-7b"] if args.all else [args.model]
    if not models[0]:
        p.error("--model or --all required")

    results = {}
    for m in models:
        results[m] = bench(m)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nWrote {out_path}")

    # Markdown summary
    print("\n## Latency benchmark")
    print("\n| Model | Cold start | Warm median | Warm p95 | RAM delta |")
    print("|---|---:|---:|---:|---:|")
    for m, r in results.items():
        print(f"| {m} | {r['cold_start_s']}s | {r['warm_median_s']}s | "
              f"{r['warm_p95_s']}s | {r['host_ram_delta_mb']:.0f} MB |")


if __name__ == "__main__":
    main()
