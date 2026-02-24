"""Tests for Chinese sentence-level chunking."""

from zhcorpus.ingest.chunker import chunk_text


class TestChineseSentenceBoundaries:
    """Chunker splits on Chinese sentence-ending punctuation."""

    def test_splits_on_period(self):
        text = "第一句话。第二句话。第三句话。"
        chunks = chunk_text(text)
        assert len(chunks) == 3
        assert chunks[0] == "第一句话。"
        assert chunks[1] == "第二句话。"
        assert chunks[2] == "第三句话。"

    def test_splits_on_mixed_punctuation(self):
        text = "这是陈述。这是感叹！这是疑问？"
        chunks = chunk_text(text)
        assert len(chunks) == 3

    def test_splits_on_semicolon(self):
        text = "前半句；后半句。"
        chunks = chunk_text(text)
        # Semicolon is a sentence boundary
        assert len(chunks) == 2

    def test_each_chunk_ends_with_punctuation(self):
        text = "第一句话。第二句话！第三句话？第四句话；"
        chunks = chunk_text(text)
        for chunk in chunks:
            assert chunk[-1] in "。！？；", f"Chunk does not end with punctuation: {chunk!r}"


class TestMergeShortFragments:
    """Short fragments get merged with the preceding chunk."""

    def test_short_fragment_merged(self):
        text = "嗯。这是一个完整的句子。"
        chunks = chunk_text(text, min_chars=5)
        # "嗯。" is only 2 chars, below min_chars=5, should merge with next
        assert len(chunks) == 1
        assert "嗯" in chunks[0]
        assert "完整" in chunks[0]

    def test_long_sentences_stay_separate(self):
        text = "这是一个比较长的句子，包含了很多内容。另一个同样很长的句子也在这里。"
        chunks = chunk_text(text, min_chars=5)
        assert len(chunks) == 2


class TestEdgeCases:
    """Edge cases for the chunker."""

    def test_empty_string(self):
        assert chunk_text("") == []

    def test_whitespace_only(self):
        assert chunk_text("   ") == []

    def test_no_punctuation(self):
        """Text without sentence enders stays as one chunk."""
        text = "一个没有句号的短语"
        chunks = chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_single_sentence(self):
        text = "只有一句话。"
        chunks = chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == "只有一句话。"

    def test_classical_chinese(self):
        """Classical Chinese with short clauses."""
        text = "子曰：学而时习之，不亦说乎？有朋自远方来，不亦乐乎？"
        chunks = chunk_text(text)
        # Two questions — should produce 2 chunks
        assert len(chunks) == 2

    def test_preserves_all_content(self):
        """No text is lost during chunking."""
        text = "第一句。第二句！第三句？"
        chunks = chunk_text(text)
        rejoined = "".join(chunks)
        assert rejoined == text


class TestRealCorpusText:
    """Test with realistic Wikipedia/Baike-style text."""

    def test_wikipedia_paragraph(self):
        text = (
            "选任制是指通过选举方式任用干部的制度。"
            "在中国古代，选任官员的方式经历了从世袭到科举的演变。"
            "现代民主国家普遍采用选任与委任相结合的方式。"
        )
        chunks = chunk_text(text)
        assert len(chunks) == 3
        assert "选任制" in chunks[0]
        assert "科举" in chunks[1]
        assert "委任" in chunks[2]
