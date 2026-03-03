# Paper F: Benchmarks vs Reality — Prior Art

## Our Claim
SWE-bench and coding benchmarks have zero predictive value for structured multilingual output quality. Models ranked low on coding benchmarks can outperform top coding models on dictionary tasks.

## Closest Related Work

### Benchmark Criticism
- Extensive literature on benchmark limitations, contamination, overfitting.
- "Benchmarks are broken" is a well-trodden theme in ML community.
- **Chatbot Arena** (LMSYS): Attempts to address benchmark limitations with human preferences. Already established.
- **HELM** (Stanford): Holistic evaluation framework. Covers many dimensions but not structured multilingual output.

### Task-Specific vs General Benchmarks
- Known that domain-specific tasks often don't correlate with general benchmarks.
- Medical LLM evals, legal LLM evals — established that general benchmarks don't predict domain performance.
- **Gap**: No study specifically on multilingual structured output tasks.

### Our Evidence
- Mostly anecdotal: Nemotron Ultra (low coding scores) performed well on dictionary tasks in our eval rounds.
- Would need controlled experiment: N models, standard coding benchmarks, our dictionary task, correlation analysis.

## Novelty Assessment
- **Low novelty**: "Benchmarks don't predict real-world performance" is well-known.
- **Potential angle**: Specific to multilingual structured output, which is understudied.
- **Weakness**: Need substantial experimental work. Current data is anecdotal.

## Potential Venues
- Workshop papers at NeurIPS/ICML
- Position papers at ACL

## Gap Rating: LOW
Well-trodden theme. Would need strong experimental evidence to stand out. High effort, low novelty.
