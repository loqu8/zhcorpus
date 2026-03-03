# Paper C: Structured Evidence Reports vs Raw Passages for AI-Assisted Lexicography

## Metadata
- **Working title**: Structured Evidence Reports vs Raw Passages for AI-Assisted Lexicography
- **Venue target**: ACL/EMNLP 2026 (short paper or findings)
- **Status**: Experiment scaffolded, running evaluation

## Abstract (draft)
We compare three approaches for generating dictionary entries with LLMs: (1) parametric knowledge alone (Baseline), (2) top-k raw corpus passages (RAG), and (3) structured evidence reports delivered via the Model Context Protocol (MCP). Using a 113M-chunk Chinese corpus and 428K-headword multilingual dictionary, we evaluate 200 headwords stratified by frequency across four automated metrics: pinyin accuracy, definition completeness, term presence, and example authenticity. [Results TBD]

## Paper Structure

### 1. Introduction
- AI-assisted lexicography: growing interest in using LLMs for dictionary construction
- The retrieval problem: how to supply relevant evidence to the LLM
- RAG (unstructured passages) vs MCP (structured tool-mediated retrieval)
- Our contribution: first empirical comparison of structured vs unstructured retrieval for lexicographic generation

### 2. Related Work
- RAG for knowledge-intensive tasks (Lewis et al. 2020)
- Lost in the Middle (Liu et al. 2023) — supports structured > unstructured
- LLM-based dictionary generation — limited prior work
- MCP (Anthropic, Nov 2024) — protocol description, no academic evaluation
- Knowledge graph-augmented generation — similar spirit

### 3. Method
#### 3.1 Corpus and Dictionary
- 113M chunks, 34M articles, 15 sources, 68 GB
- 428K headwords × 12 languages, 184K dialect forms
- FTS5 with simple tokenizer, per-source rowid sampling

#### 3.2 Experimental Conditions
- **Baseline**: Prompt with term only → parametric knowledge
- **RAG**: Top-5 BM25 passages as context
- **MCP**: Structured word_report (definitions, frequency table, source diversity, best examples)

#### 3.3 Headword Selection
- 200 headwords, stratified: 50 high / 50 mid / 50 low / 50 rare frequency
- Selection criteria: diverse character lengths (1-5), diverse domains

#### 3.4 Evaluation Metrics
1. Pinyin accuracy (exact match against CEDICT reference)
2. Definition completeness (key term coverage vs reference definitions)
3. Term presence (target word in generated entry)
4. Example authenticity (example contains target word)
5. Composite (mean of 1-4)

### 4. Results
- Table 1: Main results (metrics × conditions)
- Table 2: Per-band breakdown (frequency strata × conditions)
- Table 3: Statistical significance (paired bootstrap + Wilcoxon)
- Table 4: Context size comparison (RAG chars vs MCP chars)

### 5. Discussion
- Where does MCP help most? (hypotheses: rare words, multi-sense words)
- Where does RAG suffice?
- Cost of structured retrieval (implementation effort, latency)
- Generalizability beyond lexicography

### 6. Conclusion

## Key Files
- `tools/paper5_eval.py` — prompt generation (done)
- `tools/paper5_runner.py` — experiment runner (done)
- `tools/paper5_metrics.py` — automated scoring (done)
- `tools/paper5_analysis.py` — statistical analysis + tables (done)
- `data/paper5_eval_headwords.json` — 200 stratified headwords (done)
- `data/paper5_eval_prompts.json` — pre-generated prompts (done)
- `data/paper5_eval_references.json` — ground truth (done)

## Experiment Checklist
- [x] Headword selection (200, stratified)
- [x] Prompt generation (3 conditions × 200)
- [x] Reference data extraction
- [x] Experiment runner (async, resumable, checkpointed)
- [x] Automated metrics (4 metrics + composite)
- [x] Statistical tests (bootstrap + Wilcoxon)
- [x] Table generators (markdown + LaTeX)
- [ ] Choose LLM model for experiment
- [ ] Run 5-headword pilot
- [ ] Run full 600-call experiment
- [ ] Score and analyze results
- [ ] Human evaluation (30-entry subset)
- [ ] Write paper draft
