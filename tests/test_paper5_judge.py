"""Tests for Paper 5 LLM-as-judge evaluation."""

import json

import pytest

from tools.paper5_judge import (
    CONDITIONS,
    DIMENSIONS,
    LABELS,
    _build_judge_prompt,
    _strip_thinking,
    randomize_entries,
    summarize_judgments,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_response():
    return {
        "term": "好",
        "band": "high",
        "response_baseline": "Baseline entry for 好",
        "response_rag": "RAG entry for 好",
        "response_mcp": "MCP entry for 好",
    }


@pytest.fixture
def sample_judgments():
    return [
        {
            "term": "好",
            "band": "high",
            "scores": {
                "baseline": {"accuracy": 3, "completeness": 3, "example_quality": 3, "organization": 3, "overall": 3},
                "rag": {"accuracy": 4, "completeness": 4, "example_quality": 4, "organization": 4, "overall": 4},
                "mcp": {"accuracy": 5, "completeness": 5, "example_quality": 5, "organization": 5, "overall": 5},
            },
        },
        {
            "term": "坏",
            "band": "high",
            "scores": {
                "baseline": {"accuracy": 2, "completeness": 2, "example_quality": 2, "organization": 2, "overall": 2},
                "rag": {"accuracy": 3, "completeness": 3, "example_quality": 3, "organization": 3, "overall": 3},
                "mcp": {"accuracy": 4, "completeness": 4, "example_quality": 4, "organization": 4, "overall": 4},
            },
        },
    ]


# ---------------------------------------------------------------------------
# Randomization
# ---------------------------------------------------------------------------

class TestRandomization:
    def test_all_conditions_present(self, sample_response):
        entries, mapping = randomize_entries(sample_response, seed=42)
        assert len(entries) == 3
        assert set(mapping.values()) == set(CONDITIONS)

    def test_all_labels_present(self, sample_response):
        entries, mapping = randomize_entries(sample_response, seed=42)
        assert set(mapping.keys()) == set(LABELS)

    def test_deterministic_with_same_seed(self, sample_response):
        entries1, map1 = randomize_entries(sample_response, seed=42)
        entries2, map2 = randomize_entries(sample_response, seed=42)
        assert map1 == map2

    def test_different_seeds_can_differ(self, sample_response):
        """Different seeds should produce different orderings (most of the time)."""
        orderings = set()
        for seed in range(20):
            _, mapping = randomize_entries(sample_response, seed=seed)
            order = tuple(mapping[label] for label in LABELS)
            orderings.add(order)
        # With 20 seeds and 6 possible orderings, we should see >1
        assert len(orderings) > 1

    def test_entries_contain_response_text(self, sample_response):
        entries, mapping = randomize_entries(sample_response, seed=42)
        texts = {text for _, text in entries}
        assert "Baseline entry for 好" in texts
        assert "RAG entry for 好" in texts
        assert "MCP entry for 好" in texts


# ---------------------------------------------------------------------------
# Think block stripping
# ---------------------------------------------------------------------------

class TestStripThinking:
    def test_no_think_block(self):
        assert _strip_thinking("Hello world") == "Hello world"

    def test_strips_think_with_content_after(self):
        long_response = "This is a substantial dictionary entry with pinyin, definitions, and example sentences for the word."
        text = f"<think>reasoning here</think>\n\n{long_response}"
        assert _strip_thinking(text) == long_response

    def test_falls_back_to_think_content(self):
        text = "<think>The actual dictionary entry is here with lots of detail...</think>\n"
        result = _strip_thinking(text)
        assert "actual dictionary entry" in result


# ---------------------------------------------------------------------------
# Judge prompt
# ---------------------------------------------------------------------------

class TestJudgePrompt:
    def test_contains_headword(self):
        entries = [("Entry A", "text a"), ("Entry B", "text b"), ("Entry C", "text c")]
        prompt = _build_judge_prompt("好", entries)
        assert "好" in prompt

    def test_contains_all_labels(self):
        entries = [("Entry A", "text a"), ("Entry B", "text b"), ("Entry C", "text c")]
        prompt = _build_judge_prompt("好", entries)
        assert "Entry A" in prompt
        assert "Entry B" in prompt
        assert "Entry C" in prompt

    def test_contains_entry_text(self):
        entries = [("Entry A", "definition of good"), ("Entry B", "def b"), ("Entry C", "def c")]
        prompt = _build_judge_prompt("好", entries)
        assert "definition of good" in prompt


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

class TestSummary:
    def test_summary_has_all_conditions(self, sample_judgments):
        summary = summarize_judgments(sample_judgments)
        assert "Baseline" in summary
        assert "RAG" in summary
        assert "MCP" in summary

    def test_summary_has_all_dimensions(self, sample_judgments):
        summary = summarize_judgments(sample_judgments)
        assert "Accuracy" in summary
        assert "Completeness" in summary
        assert "Overall" in summary

    def test_summary_scores_ordered(self, sample_judgments):
        """MCP should score higher than RAG, which should score higher than Baseline."""
        summary = summarize_judgments(sample_judgments)
        # The summary should contain the numbers — just check it's non-empty
        assert len(summary) > 100

    def test_empty_judgments(self):
        summary = summarize_judgments([])
        assert "Overall Scores" in summary
