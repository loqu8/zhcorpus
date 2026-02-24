"""Sentence-level chunking for Chinese text.

Chinese text uses full-width punctuation for sentence boundaries:
  。(period)  ！(exclamation)  ？(question)  ；(semicolon)

This chunker splits on these boundaries to produce complete, meaningful
units — each chunk is a sentence or a small group of short clauses.
"""

import re
from typing import List

# Chinese sentence-ending punctuation
_SENTENCE_END = re.compile(r"([。！？；])")

# Minimum chunk length in characters — avoid fragments.
# Chinese sentences can be short (e.g. "子曰：..." is ~5 chars),
# so this is deliberately low. We merge only truly degenerate fragments.
MIN_CHUNK_CHARS = 4

# Maximum chunk length — split overly long passages
MAX_CHUNK_CHARS = 500


def chunk_text(text: str, min_chars: int = MIN_CHUNK_CHARS) -> List[str]:
    """Split Chinese text into sentence-level chunks.

    Args:
        text: Chinese text to chunk.
        min_chars: Minimum characters per chunk. Shorter fragments are
                   merged with the previous chunk.

    Returns:
        List of sentence-level chunks. Each chunk ends with sentence-ending
        punctuation (unless the text has none, in which case the whole
        text is returned as a single chunk).
    """
    text = text.strip()
    if not text:
        return []

    # Split on sentence boundaries, keeping the delimiter
    parts = _SENTENCE_END.split(text)

    # Reassemble: each sentence = content + its delimiter
    raw_sentences = []
    i = 0
    while i < len(parts):
        segment = parts[i]
        # If next part is a delimiter, attach it
        if i + 1 < len(parts) and _SENTENCE_END.match(parts[i + 1]):
            segment += parts[i + 1]
            i += 2
        else:
            i += 1
        segment = segment.strip()
        if segment:
            raw_sentences.append(segment)

    if not raw_sentences:
        return [text] if len(text) >= min_chars else [text]

    # Merge short fragments with preceding sentence
    chunks = []
    buffer = ""
    for sentence in raw_sentences:
        if buffer:
            candidate = buffer + sentence
        else:
            candidate = sentence

        if len(candidate) >= min_chars:
            # Check if we need to split overly long chunks
            if len(candidate) > MAX_CHUNK_CHARS:
                # If buffer already qualifies on its own, flush it first
                if buffer and len(buffer) >= min_chars:
                    chunks.append(buffer)
                    chunks.append(sentence)
                else:
                    chunks.append(candidate)
                buffer = ""
            else:
                chunks.append(candidate)
                buffer = ""
        else:
            buffer = candidate

    # Don't lose trailing fragment
    if buffer:
        if chunks:
            # Merge with last chunk
            chunks[-1] += buffer
        else:
            chunks.append(buffer)

    return chunks
