# Paper C: MCP vs RAG vs Baseline — Prior Art

## Our Claim
Structured MCP evidence reports produce higher-quality dictionary entries than raw corpus passages (RAG) or parametric knowledge alone.

## Closest Related Work

### MCP vs RAG Comparisons
- **TrueFoundry blog**: "MCP vs RAG" — conceptual architecture comparison. No empirical evaluation.
- **ByteByteGo blog**: "RAG vs MCP" — system design perspective. Diagrams, no experiments.
- **Scott Chacon (GitHub co-founder) blog**: Discusses MCP in context of AI tooling. Architectural perspective.
- **Contentful blog**: MCP for content management. Use case discussion, no benchmarks.
- **Multiple Medium/dev.to posts**: All conceptual comparisons (when to use MCP vs RAG). Zero empirical data.

### CRITICAL FINDING: Zero Academic Papers
As of March 2026, there are **NO published academic papers** that empirically compare MCP-based evidence retrieval against RAG on any task. The entire MCP vs RAG discussion exists only in:
- Blog posts (architectural comparisons)
- Conference talks (conceptual)
- Product documentation

This is a wide-open gap for a first-mover academic contribution.

### RAG for Knowledge-Intensive Tasks
- Extensive literature on RAG (Lewis et al. 2020, original paper). Hundreds of follow-up papers.
- RAG for question answering, fact verification, dialogue — well-studied.
- RAG for structured output generation — less studied but exists.
- RAG for lexicography — sparse. Most dictionary construction doesn't use RAG.

### MCP (Model Context Protocol)
- Anthropic's MCP specification (Nov 2024): Protocol for AI-tool communication.
- Growing adoption (Cursor, Claude Code, various IDE integrations).
- No academic evaluation of MCP's impact on output quality.

### Structured vs Unstructured Context
- Some work on comparing structured prompts vs raw text for LLM tasks.
- "Lost in the Middle" (Liu et al. 2023): LLMs struggle with information in the middle of long contexts. Supports our hypothesis that structured reports > raw passages.
- Knowledge graph-augmented generation: similar spirit (structured > unstructured) but different mechanism.

## Novelty Assessment
- **First empirical MCP vs RAG comparison**: HIGHEST novelty. No prior academic work.
- **Domain-specific evaluation** (lexicography): Additional novelty layer.
- **Concrete metrics**: Pinyin accuracy, definition completeness, example authenticity — measurable claims.
- **Weakness**: MCP is Anthropic-specific protocol. Reviewers may question generalizability. Counter: frame as "structured tool-mediated retrieval vs unstructured retrieval" — the principle transcends MCP.

## Potential Venues
- ACL/EMNLP (NLP flagship), NAACL
- NeurIPS/ICML (if framed as retrieval-augmented generation)
- CHI (if framed as human-AI collaboration for lexicography)
- SIGIR (information retrieval)

## Gap Rating: HIGHEST
Zero academic papers on MCP vs RAG. First-mover advantage. Timely topic (MCP adoption accelerating in 2025-2026).
