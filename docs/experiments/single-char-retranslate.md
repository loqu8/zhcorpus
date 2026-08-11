# Single-Char Community-Anchored Re-translation

**Date**: 2026-03-26
**Status**: In Progress
**Model**: MiniMax M2.7 (via API)

## Problem

~200 of ~13,700 single-char headwords in dictmaster.db have wrong MiniMax English
definitions that propagate to all 26 languages. Three failure modes:

| Mode | Example | Description |
|------|---------|-------------|
| Compound leak | 猪→"pig offal" (猪杂) | LLM returned compound-word meaning |
| Definition swap | 钱→"wrong; mistake" | Definitions swapped between characters |
| Wrong reading | 曲 qū→"song" (that's qǔ) | LLM picked wrong tonal reading |

## Approach

Re-translate ALL ~13,700 single-char entries with community dictionary definitions
(cedict, cfdict, handedict, cidict, jmdict, wiktextract) as authoritative anchors.

### Key Design Decisions

1. **Generate all 26 languages** — minimax is the product, community defs are input
2. **Batch up to 20 entries per API call** — tune down if quality degrades
3. **Keep old defs** — store new as `confidence='v2'`, old remain as `'medium'`
4. **Resumable** — DB as live queue, safe to kill and restart

### Prompt Design

New `SINGLE_CHAR_SYSTEM_PROMPT` extends `UNIVERSAL_SYSTEM_PROMPT` with:
- Community defs presented as "Authoritative reference definitions"
- Instruction: "Translate these primary meanings only. Do NOT introduce meanings
  from compound words containing this character."
- All existing language-specific rules carried forward

## Experiments

### Experiment 1: Batch size 20 with known-bad + known-good

**Test set**: 猪, 事, 钱, 菜, 错, 员 (known bad) + 人, 大, 水, 马, 鸡, 狗 (known good)

| Entry | Old MiniMax EN | Community EN | New MiniMax EN | Verdict |
|-------|---------------|-------------|---------------|---------|
| | | | | |

*(to be filled during experiment)*

### Experiment 2: Batch size comparison (if needed)

| Batch Size | Accuracy (bad→fixed) | Accuracy (good→preserved) | Notes |
|-----------|---------------------|--------------------------|-------|
| 20 | | | |
| 10 | | | |
| 5 | | | |

## Execution

```bash
# In tmux
tmux new -s retranslate
cd ~/Projects/loqu8/zhcorpus
.venv/bin/python tools/dictmaster/retranslate_single_chars.py
```

## Results

*(to be filled after run)*

- Total entries processed:
- Total API calls:
- Total cost:
- Time elapsed:
- v2 definitions written:
- Comparison vs old: (improvement rate on known-bad, stability on known-good)
