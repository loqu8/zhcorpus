# Official Review — Reviewer SamJ
**Posted:** 22 Apr 2026 (modified 03 May 2026)
**Overall Assessment:** 3 = Findings of the ACL
**Confidence:** 3 · **Soundness:** 4 · **Excitement:** 3 · **Reproducibility:** 3 · **Datasets:** 5 (Enabling) · **Software:** 3

## Paper Summary

This paper introduces "Dictionarium Sinicum", a Chinese dictionary with 428,000 headwords across 18 languages. The authors utilize a single LLM (MiniMax M2.5) to generate glosses and merge seven existing community-maintained dictionaries by carefully executing the techniques: batched prompting, retrying, and context-aware backfilling. They have also focused on prompt engineering to prevent script contamination (e.g., preventing Japanese Kanji echoing in Korean Hanja mixing) and a validator that is able to reject cross-language contamination significantly. The final dictionary is augmented with ~511K dialect forms (Cantonese and Hokkien) and was completed for a cost of approximately $150.

## Summary of Strengths

- Extends open-source Chinese lexical resources to 18 major languages with 428K headwords, totalling 7.7M definitions for ~$150 — impressive and practically useful.
- Practical solutions (language-specific prompts and validators) to cross-script contamination.
- Three-stage pipeline (batch translation, retry, context-aware backfill) designed to maximise consistency.
- As a large-scale, open resource, valuable for NLP researchers who require multilingual Chinese lexicons.

## Summary of Weaknesses

- **Model is evaluated using reference glosses provided in input context.** Measures copying/consistency rather than true translation ability.
- **Novelty is scale and engineering.** LLMs generating dictionary definitions has been shown in prior small-scale work (as authors mention).
- **Model prefers "most common translation"**, losing nuance and specialized senses; risk of inheriting western-centric semantic boundaries (12 new languages translated from existing glosses rather than directly from Chinese).
- **Heavy reliance on MiniMax M2.5 + specialized prompting.** Different providers of the same open-weight model can produce different output — reproducibility risk. Cost claim is service-specific.
- Further limitations: (i) English-centric intermediate representations → loss of language-specific semantics + Anglocentric bias; (ii) single-LLM dataset → systematic bias, lack of diversity; (iii) contribution is primarily engineering + dataset, lacks theoretical insights; (iv) sense coverage metric based on lexical overlap (50% threshold) — fails to capture semantic equivalence and synonym variation; (v) sense compression mentioned but not analyzed — no fine-grained or cross-linguistic error taxonomy.

## Comments, Suggestions, and Typos

- For the backfill phase, did the authors consider a **second-model verification approach**? Using a second model to verify the MiniMax output for the 12 languages without references could catch semantic errors the deterministic script validator might miss.
- Conduct a **small-scale human evaluation for at least one of the "new" languages** to validate the 68.9% sense coverage claim.
- Consider including **COMET or BERTScore** alongside lexical overlap to better support claims and capture semantic accuracy.
- Several **hyphenation glitches** throughout the paper from the PDF layout require cleaning.
- Minor phrasing redundancy. Some tables lack detailed explanation (e.g., format compliance metric). Formatting inconsistencies in prompt descriptions.
