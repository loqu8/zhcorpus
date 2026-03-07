# Paper E: Dialect Bridge (Mandarin-Cantonese-Hokkien) — Prior Art

## Our Claim
Open-source dialect dictionaries (CC-Canto, iTaigi, TaiHua) can be unified into a single multilingual+multidialectal resource, revealing Hokkien-SE Asian loanword patterns.

## Closest Related Work

### Cantonese NLP Resources
- **words.hk** (DCLRL Workshop at LREC 2022): Comprehensive Cantonese dictionary dataset. Community-built, ~90K entries with Jyutping, definitions, example sentences. Published at the Dataset Creation for Lower-Resourced Languages workshop. Directly relevant — established resource we build upon (CC-Canto uses similar data).
- **YueTung-7b** (2024): Cantonese language model fine-tuned from Llama. Shows growing interest in Cantonese NLP.
- **PyCantonese**: Python library for Cantonese corpus linguistics. Analysis tool, not dictionary.

### Hokkien/Taiwanese NLP
- **Taiwanese Hokkien Dual Translation** (arXiv 2403.12024, 2024): LLM-based translation between Mandarin and Taiwanese Hokkien. Uses dual prompting strategy. Small-scale.
- **ATAIGI** (NAACL 2025): Hokkien learning application with speech recognition. Education-focused.
- **LangLearn Hokkien Flashcards** (NAACL 2025): Hokkien vocabulary learning app. Education-focused.
- **iTaigi**: Crowdsourced Taiwanese Hokkien dictionary. One of our source datasets.

### Cross-Dialect/Cross-Lingual Resources
- **Universal Dependencies**: Includes Cantonese treebank but no Hokkien.
- **Glottolog/WALS**: Typological databases covering Chinese dialect features.
- **DHS (Dictionnaire Historique des Sinogrammes)**: Historical dictionary connecting character readings across dialects. Our inspiration — user calls zhcorpus "the modern DHS."

### Hokkien-SE Asian Connections
- Linguistic literature on Hokkien loanwords in Tagalog (163+ documented), Indonesian, Malay.
- Sino-Vietnamese vocabulary studies (3 historical layers).
- **Gap**: No digital resource that programmatically links Hokkien forms to SE Asian cognates.

## Novelty Assessment
- **Unified multidialectal resource**: Moderate novelty. words.hk and iTaigi exist separately; combining with multilingual dictionary adds value but isn't groundbreaking.
- **184K dialect forms**: Good scale (126K Cantonese, 59K Hokkien).
- **Loanword detection**: Novel computational approach to Hokkien→SE Asian connections. But needs implementation.
- **Weakness**: Active research area with recent papers (NAACL 2025). Competition is real. Our contribution needs to be clearly differentiated from existing resources.

## Potential Venues
- LREC (language resources), ACL System Demonstrations
- Digital Humanities conferences
- EMNLP (if loanword detection is strong)

## Gap Rating: MODERATE
Active area with established resources. Our unified approach adds value but faces competition from existing projects. Loanword detection angle is more novel but needs work.
