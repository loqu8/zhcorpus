# Translation Model Evaluation (2026-03-01)

Comparison of LLM providers for translating 428K Chinese dictionary headwords into 12 languages (en, de, fr, es, sv, ja, ko, ru, id, vi, tl, fa).

## Token Economics

Per batch of 20 headwords:
- System prompt: ~500 tokens
- User prompt (entries + context): ~2,000 tokens
- Output (12 langs × 20 entries): ~3,000 tokens
- **Total: ~5,500 tokens/batch**

Full run: **21,403 batches** (428,029 headwords ÷ 20)

## Cost Comparison

| Model | Provider | Input $/M | Output $/M | Est. Total | SWE-bench | Notes |
|-------|----------|----------|-----------|------------|-----------|-------|
| GPT-OSS 120B | Groq Dev | $0.15 | $0.60 | **~$47** | 60.0% (S) | Drops geographic context |
| **MiniMax M2.5** | minimax API | $0.30 | $1.20 | **~$93** | — | **Best value — proven, no rate issues** |
| Kimi K2 Instruct | Groq Dev | $1.00 | $3.00 | **~$246** | 65.8% (S) | Best quality, too expensive |
| DeepSeek V3.2 | NIM free | — | — | free (credits) | 73.1% (S+) | Echoes headword — disqualified |
| Step 3.5 Flash | OpenRouter free | — | — | free | 74.4% (S+) | Decent but slow + verbose |
| MiniMax M2.1 | NIM free | — | — | free (credits) | 74.0% (S+) | 167s thinking mode — too slow |
| Claude Sonnet 4.6 | Anthropic | $3.00 | $15.00 | **~$1,124** | — | Good quality, echoes headword |
| Claude Haiku 4.5 | Anthropic | $0.80 | $4.00 | **~$300** | — | Untested (model config issue) |

## Free Tier Rate Limits

None of the free tiers can sustain the full 428K headword run.

| Provider | RPM | Tokens/min | Daily Cap | Est. Full Run |
|----------|-----|-----------|-----------|---------------|
| **Groq Free** | 30 | 10-12K | 300K tokens/day (Kimi K2) | ~393 days |
| **NVIDIA NIM** | 40 | — | 1K credits (one-time, can request +4K) | Credits exhaust |
| **Cerebras** | 30 | — | 1M tokens/day | ~118 days |
| **Google AI Studio** | 5 | 250K | 20 req/day (Gemini 2.5 Pro) | Years |
| **OpenRouter** | 20 | — | 50 req/day | Years |
| **Mistral** | 2 | 500K | 1B tokens/month | Feasible but slow |

### Groq Tier Details
- **Free**: No credit card, strict per-model limits. Kimi K2 = 10K tokens/min, 300K tokens/day.
- **Dev**: Pay-per-token with credit card. NOT free. Higher limits (up to 10×). Batch API at 25% discount.
- **Enterprise**: Custom SLAs, dedicated capacity.

### NVIDIA NIM Details
- 1,000 free credits on signup, can request up to 5,000 total
- Credits are **one-time** — they don't renew
- 40 RPM limit, OpenAI-compatible API at `https://integrate.api.nvidia.com/v1`
- Model catalog includes Kimi K2, K2.5, DeepSeek V3.2, GLM 5, MiniMax M2.1
- API key stored in `~/.model-radar/config.json` under `api_keys.nvidia`
- Good for prototyping, not for production-scale translation

## Quality Comparison

### Test Setup
- 5 identical headwords: 110 (police), 119 (fire), 11區 (Code Geass), 120 (ambulance), 2019冠狀病毒病 (COVID-19)
- Same v2 system prompt for all models
- CJK stripped from context definitions to prevent cross-reference leaks

### Side-by-Side Results (110/警察报警电话)

```
  en
    minimax:  police/emergency number in Mainland China and Taiwan
    kimi-k2:  police/emergency number in Mainland China and Taiwan
    gpt-oss:  police emergency number/ law‑enforcement hotline

  ja
    minimax:  中国本土・台湾の警察不通話        ← garbled (v1 issue, v2 fixes)
    kimi-k2:  警察の緊急通報番号               ← correct meaning
    gpt-oss:  警察への緊急通報番号/ 警察の緊急電話  ← correct + alternative

  ko
    minimax:  중국 본토 및 대만 긴급번호
    kimi-k2:  경찰 긴급 전화번호
    gpt-oss:  경찰 긴급 전화번호/ 경찰 비상 번호

  tl
    minimax:  numero ng pulis sa mainland China at Taiwan
    kimi-k2:  numero ng pulis sa mainland China at Taiwan
    gpt-oss:  numero ng pang-emergency ng pulis/ tawag pang-agarang pulis

  sv
    minimax:  polisens akutnummer (Fastlandskina och Taiwan)
    kimi-k2:  polisens akutnummer (Fastlandskina och Taiwan)
    gpt-oss:  polisnödsamtal/ polisens nödnummer
```

### Quality Summary

| Aspect | MiniMax M2.5 | Kimi K2 (Groq) | GPT-OSS 120B (Groq) |
|--------|-------------|----------------|---------------------|
| Geographic context | Preserves | Preserves | **Drops** |
| Japanese accuracy | v1 garbled; v2 fixes | Correct meanings | Correct + verbose |
| Korean (Hangul-only) | Pure Hangul | Pure Hangul | Pure Hangul |
| Tagalog natural | Mixes English | Mixes English | Better Tagalog vocab |
| Persian | Present | Present | Present |
| Output format | Clean `xx: def1/def2` | Clean | Bold markdown headers, breaks parser |
| Instruction following | Good | Best | Fair |

### GPT-OSS 120B Specific Issues
1. Wraps entries in `**1. title**` bold markdown — breaks `parse_universal_batch_response()`
2. Uses `/ ` (with spaces) for alternatives vs clean `/`
3. Drops geographic context that MiniMax/Kimi K2 preserve (e.g., "Mainland China and Taiwan")
4. More verbose output → higher output token count at scale

## Extended Model Evaluation (Round 2, 2026-03-01)

Tested 3 additional S+ tier models on the same 5 headwords.

### Models Tested

| Model | Tier | SWE-bench | Provider | Time | Tokens |
|-------|------|-----------|----------|------|--------|
| DeepSeek V3.2 | S+ | 73.1% | NVIDIA NIM | 35.3s | 1,854 |
| Step 3.5 Flash | S+ | 74.4% | OpenRouter (free) | 37.6s | 6,088 |
| MiniMax M2.1 | S+ | 74.0% | NVIDIA NIM | 167s | 6,058 |

### Head-to-Head: Entry 1 (110 — Police Emergency Number)

```
  --- en ---
    minimax-m25    police/emergency number in Mainland China and Taiwan
    kimi-k2        police/emergency number in Mainland China and Taiwan
    gpt-oss        police emergency number/ law‑enforcement hotline
    deepseek       police emergency number/110              ← ECHOES HEADWORD
    step35         police emergency number / law enforcement hotline
    minimax-m21    police emergency number/police

  --- ja ---
    minimax-m25    中国本土・台湾の警察不通話                    ← garbled (v1)
    kimi-k2        警察の緊急通報番号                          ← correct
    gpt-oss        警察への緊急通報番号/ 警察の緊急電話           ← correct + verbose
    deepseek       警察への緊急通報番号/110番                   ← echoes number
    step35         警察への緊急電話番号 / 法執行機関のホットライン  ← correct + verbose
    minimax-m21    中国本土・台湾の警察緊急通報番号/警察          ← ok

  --- ko ---
    minimax-m25    중국 본토 및 대만 긴급번호
    kimi-k2        경찰 긴급 전화번호                         ← cleanest
    gpt-oss        경찰 긴급 전화번호/ 경찰 비상 번호
    deepseek       경찰 긴급 신고 번호/110                    ← echoes number
    step35         경찰 긴급 전화번호 / 법 집행 긴급 전화
    minimax-m21    중국 본토와 대만의 경찰 긴급 전화번호/경찰

  --- tl ---
    minimax-m25    numero ng pulis sa mainland China at Taiwan
    kimi-k2        numero ng pulis sa mainland China at Taiwan
    gpt-oss        numero ng pang-emergency ng pulis/ tawag pang-agarang pulis
    deepseek       numero ng pulisya para sa emerhensiya/110  ← echoes number
    step35         numero ng emergency ng pulis / hotline ng pagpapatupad ng batas
    minimax-m21    numero ng pulisya/emergency
```

### Head-to-Head: Entry 5 (COVID-19)

```
  --- ja ---
    kimi-k2        新型コロナウイルス感染症/COVID-19             ← best
    deepseek       新型コロナウイルス感染症/2019年コロナウイルス病  ← good
    step35         COVID-19 / 新型コロナウイルス感染症           ← good
    minimax-m21    2019年に発見された新型冠状病毒による感染症       ← uses 冠状病毒 (Chinese!)
```

### Per-Model Issues

**DeepSeek V3.2** (S+, 73.1%):
- **CRITICAL: Echoes the headword** in definitions ("police emergency number/110", "110番")
- The headword IS the definition entry — echoing it is useless
- Very concise (1,854 tokens) but TOO concise — loses nuance
- No entry separators — may cause parser issues at scale
- **Verdict: Disqualified** — headword echo is a fundamental flaw

**Step 3.5 Flash** (S+, 74.4%):
- Good quality across all languages
- Clean numbered format, proper blank-line separation
- Very verbose — 6,088 tokens (2× Kimi K2)
- Uses `/ ` with spaces for alternatives (mildly annoying)
- Japanese quality is good — natural meanings, no echoing
- Tagalog still mixes English ("hotline", "emergency")
- 37.6s — slow
- **Verdict: Decent quality** but verbose and slow. Usable as fallback.

**MiniMax M2.1** (S+, 74.0%):
- **167 seconds** — enables thinking mode, spends 150s+ on internal reasoning
- Thinking output is 4,000+ tokens of repetitive self-deliberation
- Japanese uses 冠状病毒 (Chinese medical term, not Japanese コロナウイルス)
- Clean format, proper entry separation
- Geographic context preserved
- **Verdict: Too slow** and thinking mode wastes tokens. Not suitable.

## Anthropic Models (Round 3, 2026-03-01)

Tested Claude Sonnet 4.6 via subagent. Haiku 4.5 failed due to model config issue.

### Sonnet 4.6 Results
- **Time**: 19.8s | **Tokens**: ~20,000 (high — Sonnet is verbose)
- **Format**: Clean `xx: def1/def2`, proper entry separation, no markdown issues
- **Issue**: Echoes headword number in parentheses — "China emergency police number (110)"
  - 110 IS the headword, putting "(110)" in the definition is redundant
  - Same issue as DeepSeek V3.2 but parenthetical instead of gloss
- **Japanese**: Good — "新型コロナウイルス感染症/COVID-19" (proper medical terminology)
- **Korean**: Pure Hangul — "코로나바이러스감염증-19/COVID-19"
- **Tagalog**: Still mixes English — "numero ng emergency ng pulisya sa Tsina"
- **Cost**: $3.00/M in + $15.00/M out = **~$1,124 for full run** (12× MiniMax)

### Round 3 Scorecard (All 8 Cloud Models)

| Model | Time | Tokens | Quality | Format | Killer Issue |
|-------|------|--------|---------|--------|-------------|
| **Kimi K2** | ~9s | ~5,100 | **Best** | Clean | Groq free tier too slow |
| **MiniMax M2.5** | ~6s | ~5,100 | Good (v2) | Clean | $93 cost (acceptable) |
| Sonnet 4.6 | 19.8s | ~20,000 | Good | Clean | $1,124 cost, echoes headword |
| Step 3.5 Flash | 37.6s | 6,088 | Good | Clean | Slow + verbose |
| GPT-OSS 120B | 6.1s | 3,793 | Fair | Bold MD | Drops geographic context |
| MiniMax M2.1 | 167s | 6,058 | Fair | Clean | Thinking mode, 冠状病毒 |
| DeepSeek V3.2 | 35.3s | 1,854 | **Bad** | No seps | Echoes headword in defs |
| Haiku 4.5 | — | — | — | — | Model config error (untested) |

## Multi-Provider Evaluation (Round 4, 2026-03-01)

Expanded testing across 6 providers via model-radar MCP and direct API calls.
Tested 20+ additional models on the same 5-headword suite.

### Provider Landscape

| Provider | Endpoint | Auth | Free Tier | Speed |
|----------|----------|------|-----------|-------|
| **NVIDIA NIM** | `integrate.api.nvidia.com/v1` | API key | 1K credits (one-time) | Moderate |
| **Groq** | `api.groq.com` | API key | 30 RPM, 10K TPM | Fast (LPU) |
| **OpenRouter** | `openrouter.ai/api/v1` | API key | Free models + balance | Varies |
| **Cerebras** | `api.cerebras.ai/v1` | API key | 1M tok/day | Fast (wafer) |
| **SambaNova** | `api.sambanova.ai/v1` | API key | $5 credit + 200K tok/day | **Fastest** |
| **SiliconFlow** | `api.siliconflow.com/v1` | API key | Free tier | Moderate |
| **Hugging Face** | `router.huggingface.co/v1` | HF token | Pay-per-token (via providers) | Varies |
| **Fireworks** | `api.fireworks.ai/inference/v1` | API key | $6 credit (signup bonus) | Fast |
| **DeepInfra** | `api.deepinfra.com/v1/openai` | API key | None (requires billing) | — |
| **Replicate** | `api.replicate.com/v1` | API key | Unknown | — |

All API keys stored in `~/.model-radar/config.json` (10 providers configured).

### NIM Round 2 Results (entry 110)

| Model | Time | Result | Issue |
|-------|------|--------|-------|
| **Nemotron Ultra 253B** | 7.7s | **Excellent** | Credits only |
| **GLM 5** | 97s | **Excellent** | Slow |
| Devstral 2 123B | 2.1s | Fair | Drops geographic context |
| Llama 4 Maverick | — | **Terrible** | Echoes "110" as definition |
| DeepSeek V3.1 | — | **Terrible** | Translates digits ("one one zero") |
| Qwen3 235B | — | Failed | Burns tokens on thinking |
| MiniMax M2 | — | Failed | EOL (HTTP 410, retired 2026-02-26) |

### Nemotron Ultra 253B

Made by NVIDIA — Llama 3.1 405B compressed via NAS to 253B params, then post-trained
(SFT for Math/Code/Reasoning/Chat, RL with GRPO).

- Open weights on HuggingFace, NVIDIA Open Model License (commercial OK)
- Hardware: INT4 = 2× H100 (~127GB VRAM), FP16 = 8× H100 (~506GB)
- **NIM-only for API** — NVIDIA doesn't sell per-token inference
- NIM credits: 1,000 on signup, up to 5,000 total, one-time non-renewable
- Production self-hosting: GPU rental + AI Enterprise license ($4,500/GPU/year)
- **General benchmarks**: Claude Opus 4.6 crushes Nemotron (SWE-bench 82% vs unranked,
  MMLU 91.3 vs 76.0). Nemotron is tier C-D for coding.
- **Our dictionary task**: Nemotron beat Sonnet 4.6 — no headword echo, 4× fewer tokens

### OpenRouter Nemotron Family (entry 110)

| Model | Size | Free? | Time | Geographic Context |
|-------|------|-------|------|--------------------|
| **Nemotron 70B Instruct** | 70B | No ($1.20/M) | 6.4s | "Mainland China and Taiwan" |
| Nemotron Super 49B | 49B | No ($0.10/M) | 13.2s | "China" (drops Taiwan) |
| Nemotron Nano 9B | 9B | Yes | 14.3s | Dropped entirely |
| Nemotron Nano 12B VL | 12B | Yes | 15.8s | Echoes "110" |
| Nemotron Nano 30B | 30B | Yes | 11.4s | FAILED: burns tokens on thinking |

### SambaNova Results (full 5-entry test, all free)

| Model | Total | Per entry | Geographic Context | Issues |
|-------|-------|-----------|-------------------|--------|
| **Llama 3.3 70B** | **4.8s** | **1.0s** | "Mainland China and Taiwan" | 0 |
| **Llama 4 Maverick** | **4.6s** | **0.9s** | "China and Taiwan" | 0 |
| **Qwen3 235B** | 18.7s | 3.7s | "China and Taiwan" | 0 |
| MiniMax M2.5 | — | — | — | "No valid service tier" |

**Critical finding**: Same model, different provider, different results:
- Llama 4 Maverick: **terrible on NIM** (echoes "110"), **perfect on SambaNova**
- Qwen3 235B: **fails on Groq** (burns tokens on thinking), **perfect on SambaNova**

SambaNova free tier: $5 credits (30 days) + persistent 200K tokens/day, 40 RPD.
Full run at 200K/day = ~585 days — not viable for production.

### SiliconFlow Results (entry 110)

| Model | Tokens | Geographic Context | Issues |
|-------|--------|-------------------|--------|
| **GLM 5** | 1,586 | "Mainland China and Taiwan" | 0 — excellent |
| **ByteDance Seed 36B** | 2,612 | "Mainland China and Taiwan" | 0 — surprise discovery |
| MiniMax M2.5 | 4,009 | "Mainland China and Taiwan" | ja: Korean script contamination |
| Tencent Hunyuan 13B | 315 | Dropped entirely | Poor — generic |
| Baidu ERNIE 4.5 300B | 354 | — | **Terrible** — translates digits |
| Kimi K2.5 | — | — | Timeout (120s) |

**ByteDance Seed-OSS 36B** full 5-entry test: 275s total (55s/entry), 1 issue (Korean),
preserves geographic context on all entries. Quality excellent but too slow.

SiliconFlow API: endpoint is `.com` NOT `.cn`. Python urllib blocked by Cloudflare (1010); curl works.

### Cerebras Results

Mostly phantom catalog — only 2 of 7 listed models actually accessible:
- `llama3.1-8b`: Too small (echoes "110番", drops context)
- `gpt-oss-120b`: Burns tokens on reasoning, truncated output
- Qwen3 235B, GLM 4.7, Llama 4 Scout, Llama 3.3 70B: all 404

### Local Ollama Models (NOT VIABLE)

Tested on same 5 headwords. None viable for production.

| Model | Speed | Quality | Issue |
|-------|-------|---------|-------|
| qwen3:30b | 16-18 tok/s | — | `think: false` broken, burns all tokens on reasoning |
| qwen3:8b | 103 tok/s | Fair | Misses emergency number meaning, NON_HANGUL |
| qwen3:8b (think) | 105 tok/s | — | CRITICAL: 119 spent all tokens thinking, 0 output |
| qwen3-coder:30b | 10 tok/s | Good | Misses 110/120 meanings, too slow (weeks for full run) |

### Final Scorecard (All Models, All Providers)

**Top Tier** (0 issues, preserves geographic context):

| Model | Provider | Time/entry | Production? |
|-------|----------|-----------|------------|
| **MiniMax M2.5** | minimax API | ~1.2s | **YES — $93** |
| **Kimi K2 Instruct** | Groq | ~1.8s | No — $246 |
| **Llama 3.3 70B** | SambaNova | **1.0s** | No — 200K tok/day |
| **Llama 4 Maverick** | SambaNova | **0.9s** | No — 200K tok/day |
| **Nemotron Ultra 253B** | NIM | ~7s | No — credits only |
| **GLM 5** | NIM / SiliconFlow | ~19s | No — slow |
| **Qwen3 235B** | SambaNova | ~3.7s | No — 200K tok/day |
| **ByteDance Seed 36B** | SiliconFlow | ~55s | No — too slow |
| **MiniMax M2.1** | Fireworks | **5.4s** | Maybe — $6 credit, needs pricing check |
| **Kimi K2.5** | Fireworks | ~9.8s | Maybe — $6 credit |
| **GLM 5** | Fireworks | ~11.3s | Maybe — $6 credit |

**Failed/Terrible**:
- DeepSeek V3.1 (NIM) — translates digits
- DeepSeek V3.2 (NIM) — echoes headword
- Baidu ERNIE 4.5 300B (SiliconFlow) — translates digits
- Tencent Hunyuan 13B (SiliconFlow) — drops all context
- Llama 4 Maverick (NIM) — echoes headword (but works on SambaNova!)
- All local Ollama models — too slow or broken thinking

## Implementation Notes

### Groq Backend (`tools/dictmaster/translate/groq_api.py`)
- Uses `groq` Python SDK
- Rate limiter: 35s interval between requests (thread-safe `_rate_lock`)
- CJK stripping: `_strip_cjk_from_context()` removes Chinese chars from context defs
- Retry logic: 3 retries with exponential backoff on 429 errors
- API key loaded from: `GROQ_API_KEY` env → `~/.model-radar/config.json` → `~/.claude/settings.groq.json`
- Source name in DB: `groq-kimi-k2`
- CLI: `--backend groq` on build_master.py (default)

### MiniMax Backend (`tools/dictmaster/translate/minimax_api.py`)
- Uses Anthropic SDK with custom base URL
- Config: `~/.claude/settings.minimax.json`
- No observed rate limits with 20 workers
- Source name in DB: `minimax`
- CLI: `--backend api`

### model-radar MCP (v0.5.0)
- Discovery tool: 173 models across 17 providers
- Live model sync for 7 providers (OpenRouter, NIM, Groq, Cerebras, SambaNova, SiliconFlow, HuggingFace)
- SSE server on port 8743
- Config: `~/.claude.json` (NOT `settings.json`)
- Useful for scanning latency, comparing models, running test prompts

## Recommendation

**MiniMax M2.5 at ~$93** is the best cost/quality balance:
- Already proven pipeline with 20 parallel workers
- No rate limiting observed
- v2 prompt resolves all known quality issues (Japanese, Korean, Tagalog)
- ~35 hours for full 428K headword run
- $93 is 2× cheaper than Kimi K2 on Groq Dev, with comparable quality

**Runner-up: Kimi K2 Instruct** — best quality overall but only practical on Groq Dev tier ($246).

**Not recommended**: DeepSeek V3.2 (echoes headword), MiniMax M2.1 (167s thinking), GPT-OSS 120B (drops context).

## HuggingFace Router (Round 5, 2026-03-02)

HuggingFace Router (`router.huggingface.co/v1`) is a unified API frontend that routes to
backend providers (novita, together, cerebras, sambanova, groq, etc.). 120 text models
available. One API key, many models.

### Single-Entry Screening (entry 110)

| Model | Time | Langs | Geographic Context | Issue |
|-------|------|-------|--------------------|-------|
| **GPT OSS 120B** | 1.3s | 12/12 | No | Clean output |
| **Qwen3 235B** | 2.8s | 12/12 | Yes | Clean output |
| **GLM 5** | 15.5s | 12/12 | Yes | Clean output |
| **MiniMax M2.5** | 26.7s | 12/12 | Yes | Clean output |
| Llama 3.3 70B | 0.6s | 8/12 | Yes | Truncated (missing ja/ko/ru/id) |
| Kimi K2.5 | 12.9s | 0/12 | — | Empty content |
| DeepSeek V3.2 | 60s | — | — | Timeout |
| Qwen3 32B | 3.5s | 0/12 | — | Burns all tokens on `<think>` |
| DeepSeek R1 0528 | 4.4s | 0/12 | — | Burns all tokens on `<think>` |
| GPT OSS 20B | 1.6s | 0/12 | — | Empty response |

### Full 5-Entry Test (top 4 models)

| Model | Issues | Time | Langs | Notes |
|-------|--------|------|-------|-------|
| **Qwen3 235B** | **1** | 41.0s | 60/60 | Best quality (1 minor ko issue) |
| **GPT OSS 120B** | **2** | **4.0s** | 60/60 | Fastest, 2 minor ko issues |
| **MiniMax M2.5** | **2** | 107.4s | 58/60 | Missing 2 en defs, slow |
| GLM 5 | 13 | 147.3s | 48/60 | 1 empty response, 1 ko issue |

### HuggingFace Findings

1. **Router is a paid aggregator** — routes to novita, together, sambanova, etc. with per-token pricing.
   Not a free inference platform for larger models.
2. **Same models, slower** — GLM 5 at 147s via HF vs 97s via NIM; MiniMax M2.5 at 21s/entry
   vs <2s on SambaNova or direct API. Extra latency from routing layer.
3. **GPT OSS 120B via HF is fast** — 0.8s/entry, routed via groq. Best speed/quality on HF.
4. **Thinking models waste tokens** — Qwen3 32B, DeepSeek R1 0528 spend all 1024 tokens on
   `<think>` reasoning tags, produce zero actual output. Not usable for dictionary tasks on HF.
5. **Useful for discovery** — one API key lets you test 120 models. Good for eval, not for
   production runs (go direct to the underlying provider for better speed/price).

## DeepInfra & Fireworks (Round 6, 2026-03-02)

Obtained API keys via GitHub OAuth for 3 new providers: Replicate, DeepInfra, Fireworks.
Together AI requires $5 deposit — skipped.

### Provider Access Summary

| Provider | OAuth | Free Tier |
|----------|-------|-----------|
| **Fireworks** | GitHub | **$6 credit** ($5 bonus + $1) |
| **DeepInfra** | GitHub | **None** — requires positive balance |
| **Replicate** | GitHub | Unknown |
| Together AI | GitHub | Requires $5 deposit |

API keys stored in `~/.model-radar/config.json`.

Now 10 of 17 model-radar providers configured (was 7).

### DeepInfra — All 402

All 8 models returned HTTP 402 "You need positive balance to do inference."
DeepInfra has **no free tier** — requires billing setup even for first call.
142 models available via `/v1/models` but all gated behind payment.

Models tested: Qwen3 235B, GPT OSS 120B, MiniMax M2.5, GLM 5, Kimi K2.5, DeepSeek V3.2, Qwen3 Coder 480B, GLM 4.7.

### Fireworks — Single-Entry Screening (entry 110)

| Model | Time | Langs | Geographic Context | Issues |
|-------|------|-------|--------------------|--------|
| **MiniMax M2.1** | **4.5s** | 12/12 | Yes | 0 — clean |
| **GPT OSS 120B** | 7.5s | 12/12 | No | 0 — clean output |
| **Kimi K2.5** | 7.3s | 12/12 | Yes | 0 — preamble text |
| **GLM 5** | 8.9s | 12/12 | Yes | 0 — clean |
| DeepSeek V3.2 | 90s | — | — | TIMEOUT |

All tested via model-radar dogfooding (`_call_model()` with manually constructed `Model` objects).

### Fireworks — Full 5-Entry Test (top 4 models)

| Model | Time | Langs | Tokens (p/c) | Issues | Notes |
|-------|------|-------|-------------|--------|-------|
| **MiniMax M2.1** | **26.8s** | **60/60** | — | **0** | **Best — fast + perfect** |
| **Kimi K2.5** | 49.1s | 60/60 | — | 0 | Perfect quality |
| **GLM 5** | 56.4s | 60/60 | — | 0 | Perfect quality |
| GPT OSS 120B | 31.6s | 53/60 | — | 1 | Missed 7 langs on entry 1 |

**MiniMax M2.1 on Fireworks is the surprise winner**: 5.4s/entry, zero issues across all 60 language slots.
This is the same model that was 167s on NIM due to thinking mode — Fireworks serves it WITHOUT thinking,
making it fast and clean.

### Fireworks Findings

1. **$6 free credit** goes far — 5-entry test on 4 models barely dents it
2. **MiniMax M2.1 = night and day vs NIM** — 5.4s/entry (FW) vs 167s/entry (NIM). No thinking mode on Fireworks.
3. **Kimi K2.5 and GLM 5 both perfect** — 60/60 langs, 0 issues, but 2× slower than MiniMax
4. **GPT OSS 120B inconsistent** — missed 7 languages on first entry but 12/12 on other 4
5. **DeepSeek V3.2 timeout** — consistent across providers (also timed out on HF)
6. **model-radar dogfooding works** — `_call_model()` with manual `Model` objects bypasses stale registry
7. **model-radar gap**: `provider_sync.py` has no fetch functions for deepinfra/fireworks (only 7 of 17 providers)

### Key Insight: Same Model, Different Provider, Wildly Different Results

| Model | NIM | SambaNova | Groq | Fireworks | HuggingFace |
|-------|-----|-----------|------|-----------|-------------|
| MiniMax M2.1 | 167s (thinking) | — | — | **5.4s (clean)** | — |
| Llama 4 Maverick | Echoes "110" | **Perfect** | — | — | — |
| Qwen3 235B | — | **Perfect** | Burns tokens | — | 8.2s (clean) |
| GPT OSS 120B | — | — | Drops context | Drops context | **0.8s (fastest)** |
| DeepSeek V3.2 | Echoes headword | — | — | Timeout | Timeout |

## Lessons Learned

### Benchmarks vs Reality
1. **SWE-bench scores don't predict translation quality** — DeepSeek V3.2 (S+, 73.1%) echoes headwords; MiniMax M2.5 (unranked) produces the best dictionaries; Nemotron Ultra (tier C-D coding) beats Claude Sonnet 4.6 (top-3 coding) on dictionary output
2. **Chinese tech giants ≠ good at Chinese lexicography** — Baidu ERNIE 4.5 (300B flagship) translates digits; Tencent Hunyuan drops all context; MiniMax (smaller company) outperforms both
3. Thinking/reasoning models waste tokens on dictionary tasks — MiniMax M2.1 (167s), Nemotron Nano 30B, Qwen3 on Groq all burn tokens on internal reasoning with no quality benefit

### Provider Matters
4. **Same model, different provider = different results** — Llama 4 Maverick is terrible on NIM but perfect on SambaNova; Qwen3 235B fails on Groq but works on SambaNova; MiniMax M2.1 is 167s on NIM but 5.4s on Fireworks. The inference stack (quantization, serving framework, default parameters like thinking mode) matters as much as model weights.
5. **NVIDIA's business model is hardware, not inference** — NIM credits are a teaser to sell GPUs. No per-token pricing. AI Enterprise license ($4,500/GPU/yr) on top of compute costs.
6. Free tier rate limits are much more restrictive than marketing suggests — SambaNova: 200K tok/day (585 days for full run), Groq: 10K TPM, Cerebras catalog is mostly phantom models

### Pricing
7. Groq Dev tier is pay-per-token, NOT free (credit card required)
8. SambaNova paid: ~$5/$7 per M tokens (~$663 full run, 7× MiniMax)
9. OpenRouter Nemotron 70B: $1.20/$1.20 per M (~$180 full run)
10. **MiniMax M2.5 at $93 remains the only viable production option** — no rate limits, proven pipeline

### Technical
11. SQLite connections can't cross threads — prepare batches on main thread, API calls in workers only
12. Always back up DB before bulk deletes (lost v1 3.25M defs without backup)
13. Python `-u` flag needed for unbuffered output in nohup runs
14. SiliconFlow API is `.com` not `.cn` — Python urllib blocked by Cloudflare (1010), use curl
15. Ollama `think: false` doesn't work on Qwen3 models — model self-narrates in content field
16. HuggingFace Router adds latency vs going direct to providers — useful for eval/discovery, not production
17. model-radar expanded to 173 models / 17 providers / live sync for 7 (v0.5.0)
18. Together AI requires $5 deposit for API access — no free tier
19. DeepInfra requires positive balance — all calls return 402 without billing
20. Fireworks gives $6 free credit on signup (GitHub OAuth) — best free offering for eval
21. **Provider default parameters differ silently** — MiniMax M2.1 on NIM enables thinking mode (167s), same model on Fireworks disables it (5.4s). This is the #1 cause of "same model, different results."
22. model-radar `provider_sync.py` only has fetch functions for 7 of 17 providers — deepinfra/fireworks need to be added

## Production Run Results (2026-03-02)

### MiniMax M2.5 v2 — Full Translation

| Phase | Entries | Defs | Time | Rate |
|-------|---------|------|------|------|
| Main run | 374,602 / 428,073 | 4,410,579 | ~24h | 4.6/s |
| Retry pass | 53,471 remaining | +616,276 | 92m | 5.4/s |
| Backfill pass | 82,550 partial | +103,300 | 92m | 14.0/s |

### Final Coverage

- **428,073** headwords, **5,130,189** definitions, **12 languages**
- **422,198 (98.6%)** headwords with full 12-language coverage
- **0** headwords with zero definitions
- Every language at 99.5%+ coverage (worst: fa at 99.5%)
- Total cost: ~$98 on MiniMax API (main $93 + retry ~$3 + backfill ~$2)

### Backfill Script

`tools/dictmaster/backfill_langs.py` — context-aware gap filler that sends existing
translations as read-only context so new definitions stay consistent. See
`docs/translation-backfill-plan.md` for full details.
