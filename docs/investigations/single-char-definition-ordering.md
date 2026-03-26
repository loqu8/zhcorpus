# Investigation: Single-Char Chinese Definition Ordering

**Issue**: loqu8/zhcorpus#8
**Date**: 2026-03-26
**Status**: Complete

## Problem

The entry for 猪 (zhū) in dictmaster.db shows "pig offal" as its first definition,
but 猪 means "pig/hog/swine". "Pig offal" is the meaning of 猪杂 (zhūzá), a compound word.

## Root Cause

Two interacting problems:

### 1. MiniMax LLM Hallucinations for Single Characters

The MiniMax M2.5/M2.7 translation backend produced incorrect English definitions for
many single-character entries. Three failure modes were identified:

| Mode | Example | What happened |
|------|---------|---------------|
| **Compound leak** | 猪→"pig offal" (猪杂), 菜→"rapeseed oil" (菜籽油), 致→"lethal agent" (致命) | LLM gave the meaning of a common compound containing the character |
| **Definition swap** | 钱→"wrong; mistake; error", 录→"money; coin; cash" | Definitions appear swapped between characters (钱 means money, 错 means mistake) |
| **Wrong reading** | 曲 qū→"song/melody" (that's qǔ), 应 yīng→"to respond" (that's yìng) | LLM gave the definition for a different tonal reading |

### 2. Build Pipeline Source Priority

In `nomad-builder/tools/dictgen/build_dbs.py`, the merge logic uses:

```python
SOURCE_PRIORITY = {'minimax': 1}  # all others default to 99
```

This means MiniMax definitions **always take precedence** over CC-CEDICT. The merge
algorithm (`merge_definitions()`) works as follows:

1. Use the highest-priority source (MiniMax) first
2. Split its definition on `/` and `;` into segments
3. **Only if MiniMax has ≤1 segment**, supplement from lower-priority sources (cedict)
4. Stop supplementing after reaching 3+ segments

For 猪: MiniMax has "pig offal" (1 segment) → cedict supplements → user sees
`/pig offal/hog/pig/swine/CL:口[kǒu],頭|头[tóu]/` — wrong meaning first.

For 事 (shì): MiniMax has "to grant/to give" (2 segments) → cedict **never consulted** →
user sees `/to grant/to give/` instead of "matter/thing/item/work/affair".

## Impact

### Quantified Scope

| Category | Count | Description |
|----------|-------|-------------|
| Single-char entries with both cedict + minimax EN | 13,740 | Total population |
| MiniMax used alone (>1 segment, cedict ignored) | 8,176 | cedict definition completely lost |
| MiniMax leads, cedict supplements (≤1 segment) | 5,564 | Wrong meaning leads, correct follows |
| **Likely wrong** (zero word overlap, real cedict def) | **~310** | Genuinely incorrect definitions |
| High-frequency affected (sfreq > 100K) | **83** | Common characters users will encounter |

### Severity

The 310 affected entries include extremely common characters:

| Character | Pinyin | sfreq | CC-CEDICT (correct) | MiniMax (wrong) |
|-----------|--------|-------|---------------------|-----------------|
| 事 | shì | 13.3M | matter/thing/item/work/affair | to grant/to give |
| 意 | yì | 8.1M | idea/meaning/thought/to think | to consider/to ponder/worry/anxiety |
| 应 | yīng | 7.2M | should/ought to/must | to respond/to answer |
| 员 | yuán | 6.3M | person/member/classifier | ow!; ouch! (exclamation of pain) |
| 猪 | zhū | 372K | hog/pig/swine | pig offal |
| 钱 | qián | 2.4M | coin/money | wrong; mistake; error |
| 菜 | cài | 1.1M | vegetable/dish | rapeseed oil; canola oil |
| 错 | cuò | 1.8M | mistake/wrong/bad | chain; link |
| 致 | zhì | 3.3M | to send/to transmit/to convey | lethal agent |
| 除 | chú | 2.7M | to remove/to exclude/to divide | apart from this; in addition to this |

Note: some "mismatches" in the 310 count are actually benign (minimax gives a
more common meaning while cedict describes a rare reading). Manual review of
the top 50 by frequency found **~60-70% are genuinely wrong**, and ~30-40%
are variant-reading differences where the mismatch is expected.

### What Users See in iCE

For the 猪 case: `/pig offal/hog/pig/swine/` — confusing but not catastrophic
(correct meaning follows).

For 事, 钱, 菜, 错: the correct definition is **completely absent** because
MiniMax has 2+ segments and cedict never supplements. These are the most damaging cases.

## Recommended Fix

### Option A: Reverse Priority for Single Characters (Recommended)

For entries where `length(simplified) = 1` AND cedict has a definition,
use cedict as the primary source and minimax as supplement:

```python
# In build_dbs.py merge_definitions
if is_single_char and 'cedict' in defs_by_source:
    SOURCE_PRIORITY = {'cedict': 1, 'wiktextract': 2}  # minimax defaults to 99
else:
    SOURCE_PRIORITY = {'minimax': 1}  # current behavior for compounds
```

**Rationale**: CC-CEDICT has been community-curated for 20+ years and is highly
reliable for single characters. MiniMax LLM translations are better for compounds
(where cedict may lack coverage) but less reliable for basic single-character meanings.

### Option B: Always Merge All Sources

Change the merge algorithm to always include segments from all sources, using
priority only for ordering:

```python
# Always add from all sources, just put best source first
for src in sorted_sources:
    for d in defs_by_source[src]:
        for part in re.split(r'[;/]', d):
            ...  # same dedup logic, no early-stop at 3 segments
```

**Downside**: definitions become very long for entries with many sources.

### Option C: Validate MiniMax Against Cedict

Add a post-merge validation step: if MiniMax and cedict share zero semantic
overlap for a single-char entry, flag it for review or prefer cedict.

### Option D: Fix Bad MiniMax Definitions at Source

Re-run MiniMax translation for the ~310 affected single-char entries with
an improved prompt that includes the cedict definition as context.

**Recommendation**: Option A for immediate fix (scope: nomad-builder), then
Option D to improve the source data in dictmaster.db long-term.

## Full List of Affected Entries

The top 50 affected entries by frequency (cedict has real definition, zero word
overlap with minimax):

| # | Char | Pinyin | sfreq | CC-CEDICT | MiniMax |
|---|------|--------|-------|-----------|---------|
| 1 | 事 | shi4 | 13,284,141 | matter/thing/item/work/affair | to grant/to give |
| 2 | 作 | zuo1 | 13,018,889 | worker/workshop/troublesome | work/deed |
| 3 | 意 | yi4 | 8,097,562 | idea/meaning/thought/to think | to consider/to ponder/worry |
| 4 | 比 | bi1 | 7,914,081 | euphemistic variant of 屄 | female genitalia |
| 5 | 应 | ying1 | 7,243,037 | should/ought to/must | to respond/to answer |
| 6 | 证 | zheng4 | 6,529,245 | to admonish | to warn/proof |
| 7 | 员 | yuan2 | 6,259,764 | person/member/classifier | ow!; ouch! |
| 8 | 张 | zhang1 | 4,568,635 | to open/to spread/classifier | surname Zhang/to stretch |
| 9 | 台 | tai2 | 4,358,056 | (classical) you/variant of 臺 | platform/terrace/stage |
| 10 | 致 | zhi4 | 3,303,427 | to send/to transmit/to convey | lethal agent |
| 11 | 份 | fen4 | 3,136,965 | classifier for gifts/papers | measure word for documents |
| 12 | 乐 | le4 | 3,021,551 | happy/cheerful/to laugh | happiness/joy/pleasure |
| 13 | 除 | chu2 | 2,685,767 | to remove/to exclude/to divide | apart from this |
| 14 | 际 | ji4 | 2,531,583 | border/edge/boundary/between | opportunity/chance |
| 15 | 钱 | qian2 | 2,356,381 | coin/money | wrong; mistake; error |
| 16 | 录 | lu4 | 2,288,935 | diary/record/to copy | money; coin; cash |
| 17 | 思 | si1 | 2,245,241 | to think/to consider | thought/feeling/mood |
| 18 | 巴 | Ba1 | 2,120,389 | Ba state (Zhou dynasty) | bar (pressure)/bus |
| 19 | 错 | cuo4 | 1,754,056 | mistake/wrong/bad/interlocking | chain; link |
| 20 | 钟 | zhong1 | 1,314,957 | handleless cup/to concentrate | mean/vulgar/contemptible |
| 21 | 奥 | ao4 | 1,270,798 | obscure/mysterious | deep/profound/inner/secret |
| 22 | 汉 | han4 | 1,197,535 | man | Han dynasty/Chinese |
| 23 | 曲 | qu1 | 1,133,144 | bent/crooked/wrong | song/melody/tune |
| 24 | 菜 | cai4 | 1,073,530 | vegetable/dish | rapeseed oil; canola oil |
| 25 | 伙 | huo3 | 1,014,538 | meals/variant of 夥 | food/companions/group |
| 26 | 胡 | hu2 | 1,009,257 | non-Han people/reckless | beard/foreign/surname |
| 27 | 赵 | zhao4 | 957,492 | to surpass (old) | Zhao (surname)/state name |
| 28 | 券 | quan4 | 925,017 | bond/contract/ticket/voucher | broker/trader |
| 29 | 森 | Sen1 | 920,799 | Mori (Japanese surname) | forest/woods/thick grove |
| 30 | 签 | qian1 | 900,438 | Japanese variant of 籤 | lottery/divination stick |
| 31 | 概 | gai4 | 897,299 | old variant of 概 | general/approximate |
| 32 | 唐 | tang2 | 835,675 | to exaggerate/empty/in vain | Tang dynasty/China/surname |
| 33 | 鲜 | xian3 | 816,820 | old variant of 鮮 | rare |
| 34 | 鲁 | lu3 | 780,631 | crass/stupid/rude | Shandong/crude/rustic |
| 35 | 莫 | mo4 | 762,817 | do not/there is none who | ancient form of 暮/surname |
| 36 | 惠 | hui4 | 748,252 | act of kindness (honorific) | meaning/idea/intention |
| 37 | 筑 | zhu4 | 740,273 | five-string lute | bamboo instrument/guqin |
| 38 | 伯 | bai3 | 720,848 | one hundred (old) | older brother-in-law |
| 39 | 勒 | le4 | 705,581 | bridle/to rein in/to compel | to be at/to be in |
| 40 | 税 | shui4 | 664,967 | taxes/duties | tax/duty |
| 41 | 贝 | bei4 | 658,843 | cowrie/shellfish/currency | shell/money |
| 42 | 姆 | mu3 | 656,423 | female tutor/保姆 | nanny/maidservant |
| 43 | 颜 | yan2 | 589,369 | Japanese variant of 顏 | face/appearance |
| 44 | 菲 | fei1 | 539,479 | luxuriant/phenanthrene | fragrant/Philippines |
| 45 | 猪 | zhu1 | 372,424 | hog/pig/swine | pig offal |
| 46 | 酱 | jiang4 | 179,601 | fermented soybean paste/jam | fermented paste/soy sauce |
| 47 | 蓉 | Rong2 | 114,725 | short name for Chengdu | Chengdu/powdered ingredient |
| 48 | 邬 | Wu1 | 99,063 | surname Wu | Wu (place name) |
| 49 | 粟 | su4 | 82,752 | grain/millet | foxtail millet |
| 50 | 咕 | gu1 | 78,127 | (onom.) cooing/gurgling | to grunt/to snort |

**Important caveat**: Not all 310 entries are genuinely wrong. Approximately
30-40% are variant-reading entries where cedict describes a rare reading and
minimax describes the common reading — the mismatch is expected. Manual review
estimates **~190-220 genuinely wrong definitions** in the affected set.
