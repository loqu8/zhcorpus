# Local Alignment Pilot — 2026-05-17

**Question**: Can any local model produce iCE-style `{t, a}` JSON (translation + word-level alignment) good enough to replace the Cerebras Qwen3-235B cloud call for offline iCE Pro Forever users?

**Short answer**: **Yes, conditionally.** A small instruction-tuned model (qwen3.5:9b ≈ 5.5 GB) can produce real translations plus usable alignment when prompted carefully (`format=json` + clean placeholder). HY-MT — Tencent's WMT24-winning translation model — **cannot** be prompted to produce structured alignment at all (0–10% parse rate). For offline alignment in iCE, the path forward is a **separate instruct-class model** for the alignment job, *or* the classical **two-pass aligner** approach (HY-MT translation + multilingual encoder for alignment).

## Methods

### Prompt
The exact iCE production prompt (post-fix, from `loqu8/telemetry/src/index.js:1098`):

```
system: Translate Chinese to English. Return compact JSON:
{"t":"translation","a":[["s:源词","t:English1"],["s:源词2","t:English2"],...]}
The "a" array maps each Chinese word/phrase to its English equivalent in reading
order. Group compound words naturally. Include function words like 之/的/了 with
empty target if no English equivalent.

user:   Translate to English: <text>
        Return ONLY this JSON format, no other text:
        {"t":"<translation>","a":[["s:源","t:target"],...]}
```

### Test set
10 sentences sampled from `data/mt_eval/ice_realism.jsonl`, stratified across 8 sources (news, baike, wiki, subtitles, classical prose, idioms, chat), 13–50 chars. Stored at `data/alignment_eval/pilot.jsonl`.

### Systems
| Tag | Backend | Disk | Notes |
|---|---|---|---|
| `hy-mt-1.8b` | Ollama, fixed-template HY-MT GGUF | 1.1 GB | Tencent WMT24 winner, translation-specialized |
| `hy-mt-7b`   | Ollama, fixed-template HY-MT GGUF | 4.6 GB | Same family, larger |
| `qwen2.5:3b-instruct` | Ollama | 1.9 GB | Smallest instruct-class candidate |
| `qwen3.5:9b` (think disabled) | Ollama | 5.5 GB | Instruct + reasoning; `think:false` to get direct output |
| `gpt-oss:20b` (think disabled) | Ollama | 12 GB | Larger instruct candidate |
| `cerebras` | Cloud, qwen-3-235b-a22b-instruct-2507 | — | Silver reference |

All Ollama calls: `temperature=0`, `num_predict=1024`, `think=false`, no `format=json` (this is the iCE-production-equivalent call). Cerebras call matches production exactly.

### Metrics
- **parse_rate** — fraction of outputs producing a `{t, a}` dict where `a` is a list (after stripping ```` ``` ```` fences and trying greedy `{...}` extraction)
- **pairs_mean** — mean alignment pairs in successful parses
- **coverage** — fraction of source Chinese characters covered by some alignment `s:` term (mean over parsed outputs)
- **chrF++** — translation `t` field vs. Cerebras silver
- **latency p50 / max** — warm + cold mixed (cold-start is the first call)

## Phase 1 Results

```
system                     parse  pairs    cov  chrF++   p50_s   max_s
----------------------------------------------------------------------
cerebras (silver)           100%   15.6    92%  100.00    0.38    1.22
qwen2.5:3b-instruct          80%    4.4    80%    2.25¹   0.59   18.80
qwen3.5:9b (think off)       50%   13.2    90%   48.32    1.73    8.23
gpt-oss:20b (think off)      30%    6.7    87%   25.09    7.47   34.45
hy-mt-1.8b                   10%    1.0     0%    2.79    2.03    5.18
hy-mt-7b                      0%    0.0     0%     n/a    4.00   18.30
```

¹ qwen2.5:3b's catastrophic chrF++ is a **prompt-following bug, not a translation-quality bug** — see below.

### Why each system landed where it did

**HY-MT (1.8B and 7B) — total failure on structured output.**
HY-MT is a translation-fine-tuned model with a fixed chat template; it is not an instruction-follower in the general sense. Asking for JSON alignment produces one of three failure modes:
- Bare translation in `t`, no `a` field at all → fails parse criterion (0/10 cases on 7B)
- Token-loop garbage: `{"t":"Translation to English", "a":[{""："，"a1":["Baxter Member"...`
- System-prompt echo: `The "a" array contains the English equivalent...`

The 7B is *worse* than the 1.8B — it tends to produce longer-form garbage, possibly because the larger model has more capacity to "elaborate" on a confused instruction. This **confirms what we suspected**: HY-MT is a translation specialist, not an instruction-follower.

Practical conclusion: **HY-MT cannot be used standalone for alignment**, regardless of size.

**qwen2.5:3b-instruct — high parse, terrible chrF++, by way of a prompt bug.**
The model achieved 80% parse rate but its `t` field is literally the string `"translation"` or `"<translation>"` in 7 of 8 successful parses. Example:
```json
{"t":"translation","a":[["s:而","t:and"],["s:且","t:and"],["s:在","t:on"],
                       ["s:1988年","t:1988"],["s:夏天","t:summer"],...]}
```
The alignment pairs *do* contain real translation pieces. The model interpreted the prompt's placeholder `"translation"` as the value to keep, and put actual content only in `a`. A 235B-class model knows "translation" is a placeholder; a 3B-class model doesn't.

This is a **fixable prompt issue**, not a model issue:
- Drop the literal `"translation"` example value, or change it to `"<your full english translation here>"`
- Or post-process: when `t` is `"translation"` or `"<translation>"`, reconstruct from `a` pair targets

With that fix, qwen2.5:3b becomes a real candidate: ~2 GB, 0.6 s latency, 80% parse rate, 80% coverage.

**qwen3.5:9b — the most promising local candidate, when it parses.**
50% parse rate sounds bad, but inspection shows the model is *trying*: it produces real translations (chrF++ 48 ≈ HY-MT-1.8B's FLORES level) and reasonable word-level alignment 90% covered. The 50% failures are all JSON-syntax glitches:
- Format drift: `["term", "t:eng"]` (drops `s:` prefix), `[{"s":"X","t":"Y"}]` (object form), `[,"t:Who"]` (stray commas)
- Trailing junk after the JSON closes

These are exactly the failure modes Ollama's **`format: "json"` constrained-decoding mode** fixes.

### Mini-experiment: format=json + cleaner prompt

I re-ran qwen3.5:9b with:
- `format: "json"` (Ollama constrains output to valid JSON)
- A simpler prompt: "Return compact JSON with two fields: 't' (full English translation) and 'a' (alignment array of [chinese, english] pairs)"
- No literal `"translation"` example

```
system        parse_rate   notes
qwen3.5:9b      80%        +30pp vs unconstrained; failures are now nested-JSON
                           escaping (Ollama wraps inner-string JSON), not format drift.
                           Translations are real ("Therefore, the soap film interface
                           has some flexibility", "Day Seven Denim top paired with
                           floral mini skirt, seasonal furry snow boots...")
```

The 2 remaining failures are Ollama's `format=json` returning the inner JSON as a string (`'"{\\"t\\":..."'`) rather than as an object, which a more permissive parser can recover. **Realistic ceiling on this model with proper engineering: 95%+.**

**gpt-oss:20b — too slow for popup UX.**
30% parse, decent translations when parsed (chrF++ 25), but **p50 = 7.5 s and max = 34 s**. The iCE popup target is sub-second. Even with constrained decoding this won't make latency. Useful only for "deliberate translate" workflows, not popup.

## Three paths for iCE offline alignment

| Path | Disk added | Latency | Alignment quality | Engineering |
|---|---|---|---|---|
| **A. Replace HY-MT-1.8B with qwen3.5:9b (instruct + JSON)** | +4.4 GB net | ~1.7 s | Good (qwen3.5:9b warm, format=json) | Smallest; one model does both jobs |
| **B. Keep HY-MT-1.8B for translation + qwen2.5:3b for alignment** | +2 GB | translation ~0.12 s; alignment ~0.6 s | Acceptable (prompt-fix needed) | Two models in VRAM concurrently |
| **C. HY-MT-1.8B + classical aligner (SimAlign / awesome-align)** | +1.1 GB (XLM-R-base) | translation ~0.12 s; alignment ~0.5 s CPU | Research-quality if XLM-R is good for zh-en | Two passes, two libs; *not yet tested* |

### Decision factors

- **Disk budget**: iCE Pro Forever wants a small bundle. Path B (+2 GB) or Path C (+1 GB) preserve the HY-MT translation-quality story. Path A trades 4.4 GB extra for single-model simplicity.
- **Latency**: Path A's 1.7 s is borderline-laggy for popup; Paths B & C keep 0.12 s translation latency and add ~0.5 s for alignment only when the user pauses on a word.
- **Translation quality**: Path A loses HY-MT's WMT24-winning translation strength. Paths B & C keep it.
- **Risk**: Path C is the research-correct way (a multilingual encoder for alignment is a solved problem) but unverified locally. Worth Phase 1b.

## Phase 2 plan

Do *both* Path A and Path C at scale on the full 100-sentence iCE-realism set, decide which goes into iCE Pro Forever based on numbers.

### Phase 2a: qwen3.5:9b (Path A) at scale
- 100 sentences × zh→en
- `format=json` + cleaned prompt (no `"translation"` placeholder)
- Permissive parser (handles all the JSON format drift variants observed in Phase 1)
- Metrics: parse_rate, coverage, chrF++ vs Cerebras, alignment-pair-accuracy spot-rated on 20 random examples

### Phase 2b: HY-MT-1.8B + SimAlign (Path C) at scale
- Install `simalign` (uses `xlm-roberta-base`, ~1.1 GB)
- For each sentence: HY-MT 1.8B produces translation, SimAlign produces word alignment over (source, hypothesis) pair
- Metrics: alignment coverage, alignment quality spot-rated, latency

### Phase 2c: 4-target language sweep
If a winner emerges, re-run Phase 2a on de/ja/ko (the languages iCE actually serves) since alignment quality may degrade differently across scripts.

## Files

- `data/alignment_eval/pilot.jsonl` — 10-sentence test set
- `data/alignment_eval/results/pilot_<system>_en.jsonl` — raw outputs per system
- `data/alignment_eval/pilot_scores.json` — final metrics table
- `tools/eval_alignment.py` — async runner (matches `eval_mt.py` patterns)
- `tools/score_alignment.py` — parse rate, coverage, chrF++

## Open items

- **Implement permissive alignment parser**: tolerate `["s:X","t:Y"]`, `["X","t:Y"]`, `["X","Y"]`, `{"s":"X","t":"Y"}` interchangeably; recover from trailing junk and double-encoded JSON. Required for production use of any local instruct model.
- **Prompt v2**: drop the literal `"translation"` placeholder (it traps small models). Use `"<...your full english translation...>"` or an angle-bracketed placeholder that small models reliably understand as a slot.
- **Phase 1b — SimAlign feasibility**: install `simalign`, run on 10 sentences, eyeball alignment quality before committing to Phase 2b at scale.
- **Cross-language alignment**: qwen3.5:9b may handle zh→ja or zh→ko worse than zh→en. Phase 2c will tell.
- **VRAM budget for Path B**: HY-MT-1.8B (1.3 GB VRAM) + qwen2.5:3b (~2 GB VRAM) concurrently is ~3.3 GB. Most iCE Pro Forever users will have integrated GPUs — verify this fits before committing.
