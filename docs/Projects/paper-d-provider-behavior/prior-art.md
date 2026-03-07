# Paper D: Provider-Dependent LLM Behavior — Prior Art

## Our Claim
The same open-weight model produces dramatically different output depending on the inference provider, due to silent differences in quantization, thinking mode defaults, and serving configuration.

## Closest Related Work

### Direct Prior Art (Emerging Topic)
- **Simon Willison blog (Aug 2025)**: "Open weight LLMs exhibit inconsistent performance across providers" — first widely-read treatment of this issue. Anecdotal evidence, no systematic study. Significant community discussion.
- **Rinberg, Karvonen et al., arXiv 2511.02620**: "Verifying LLM Inference to Detect Model Weight Exfiltration" (Nov 2025) — proposes methods to verify that providers are running the claimed model weights. Primary framing is detecting steganographic weight exfiltration, not output quality divergence.
- **Together AI blog**: "Same model, different results" — acknowledges the problem from a provider perspective. Explains quantization, batching, and serving differences. Marketing-adjacent.
- **Kirsten et al., NAACL 2025**: "The Impact of Inference Acceleration on Bias of LLMs" (NAACL 2025 Long Papers, pp. 1834-1853) — studies how quantization and acceleration change model bias in complex, unpredictable ways. Closest academic work but focuses on acceleration techniques, not cross-provider comparison.

### Quantization Effects
- Large literature on quantization effects on LLM performance (GPTQ, AWQ, GGUF).
- Most studies compare quantization levels on standard benchmarks (MMLU, HumanEval).
- **Gap**: No studies on quantization effects on structured multilingual output quality.

### Serving Framework Differences
- vLLM, TGI, TensorRT-LLM, SGLang — different frameworks with different optimizations.
- Known to produce slightly different outputs due to numerical precision, batching strategies.
- **Gap**: No systematic comparison of same-model-different-framework on real-world tasks.

### Our Unique Data Points
- MiniMax M2.1: 167s on NIM vs 5.4s on Fireworks (30x speed difference + quality shift)
- Llama 4 Maverick: CJK contamination on NIM, clean on SambaNova
- Qwen3 235B: Thinking mode forced ON by default on some providers, OFF on others
- GPT OSS 120B: Different behavior on DeepInfra vs Fireworks

## Novelty Assessment
- **Systematic cross-provider comparison**: Novel. Simon Willison blogged about it, one NAACL paper on acceleration bias, but no systematic study.
- **Structured output evaluation**: Our dictionary task exposes differences that standard benchmarks miss (CJK leaks, missing languages, script contamination).
- **Real-world task**: Unlike synthetic benchmarks, dictionary translation is a practical, measurable task.
- **Weakness**: Need rigorous experimental design (50+ headwords × 5 models × 3+ providers) to go beyond anecdotal. Current data is only 5 headwords.

## Potential Venues
- EMNLP/ACL (NLP), NeurIPS (ML systems)
- MLSys (systems for ML)
- COLM (Conference on Language Modeling) — new venue, very relevant

## Gap Rating: HIGH
Emerging topic with community interest but no systematic academic study. First rigorous paper would be impactful. Simon Willison's blog creates awareness; we can provide the evidence.
