"""Tests for Paper 5 analysis and statistical tests."""

import math

import pytest

from tools.paper5_analysis import (
    BANDS,
    CONDITIONS,
    METRICS,
    generate_band_breakdown_table,
    generate_context_size_table,
    generate_main_results_table,
    generate_significance_table,
    mean_with_ci,
    paired_bootstrap_test,
    score_all,
    wilcoxon_signed_rank,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_responses():
    """Minimal responses for 4 headwords (1 per band)."""
    return [
        {
            "term": "好",
            "band": "high",
            "response_baseline": "# 好\nPinyin: hao3\n1. good\n2. well\n好人是值得尊敬的。",
            "response_rag": "# 好\nPinyin: hao3\n1. good, fine\n2. well, nice\n这本书好看。",
            "response_mcp": "# 好\nPinyin: hao3\n1. good, fine, nice\n2. well\n3. easy to\n你好！这是一个好主意。",
        },
        {
            "term": "屣",
            "band": "mid",
            "response_baseline": "# 屣\nPinyin: xi3\n1. shoes\n屣是古代用词。",
            "response_rag": "# 屣\nPinyin: xi3\n1. shoes, slippers\n弃如敝屣。",
            "response_mcp": "# 屣\nPinyin: xi3\n1. shoes, slippers, sandals\n弃如敝屣，意为像丢弃旧鞋一样。",
        },
        {
            "term": "鳌",
            "band": "low",
            "response_baseline": "# 鳌\nPinyin: ao2\n1. sea turtle\n独占鳌头。",
            "response_rag": "# 鳌\nPinyin: ao2\n1. legendary sea turtle\n独占鳌头。",
            "response_mcp": "# 鳌\nPinyin: ao2\n1. legendary giant sea turtle\n独占鳌头，形容获得第一名。",
        },
        {
            "term": "蹀",
            "band": "rare",
            "response_baseline": "# 蹀\n1. to stamp feet",
            "response_rag": "# 蹀\nPinyin: die2\n1. to stamp feet, to tread\n蹀躞不前。",
            "response_mcp": "# 蹀\nPinyin: die2\n1. to stamp feet, to tread, to walk\n蹀躞不前，心中忐忑。",
        },
    ]


@pytest.fixture
def sample_references():
    """Matching reference data for the 4 headwords."""
    return [
        {
            "term": "好",
            "pinyin": "hao3",
            "definitions": [
                {"definition": "good; well; proper; fine", "source": "cedict"},
                {"definition": "to be fond of; to have a tendency to", "source": "cedict"},
            ],
            "corpus_hits": 10000,
            "band": "high",
        },
        {
            "term": "屣",
            "pinyin": "xi3",
            "definitions": [
                {"definition": "slippers", "source": "cedict"},
            ],
            "corpus_hits": 869,
            "band": "mid",
        },
        {
            "term": "鳌",
            "pinyin": "ao2",
            "definitions": [
                {"definition": "sea turtle/mythical sea creature", "source": "cedict"},
            ],
            "corpus_hits": 200,
            "band": "low",
        },
        {
            "term": "蹀",
            "pinyin": "die2",
            "definitions": [
                {"definition": "to tread on; to stamp one's foot", "source": "cedict"},
            ],
            "corpus_hits": 50,
            "band": "rare",
        },
    ]


@pytest.fixture
def sample_prompts():
    """Minimal prompt data for context size analysis."""
    return [
        {"term": "好", "band": "high", "rag_context_chars": 500, "mcp_context_chars": 1500},
        {"term": "屣", "band": "mid", "rag_context_chars": 300, "mcp_context_chars": 900},
        {"term": "鳌", "band": "low", "rag_context_chars": 200, "mcp_context_chars": 800},
        {"term": "蹀", "band": "rare", "rag_context_chars": 100, "mcp_context_chars": 500},
    ]


# ---------------------------------------------------------------------------
# Score all
# ---------------------------------------------------------------------------

class TestScoreAll:
    def test_scores_all_entries(self, sample_responses, sample_references):
        results = score_all(sample_responses, sample_references)
        assert len(results["scores"]) == 4

    def test_scores_have_all_conditions(self, sample_responses, sample_references):
        results = score_all(sample_responses, sample_references)
        for entry in results["scores"]:
            for cond in CONDITIONS:
                assert cond in entry
                assert "composite" in entry[cond]

    def test_by_condition_populated(self, sample_responses, sample_references):
        results = score_all(sample_responses, sample_references)
        for cond in CONDITIONS:
            assert cond in results["by_condition"]
            assert len(results["by_condition"][cond]) == 4

    def test_by_band_populated(self, sample_responses, sample_references):
        results = score_all(sample_responses, sample_references)
        for band in BANDS:
            assert band in results["by_band"]
            assert len(results["by_band"][band]) == 1


# ---------------------------------------------------------------------------
# Statistical tests
# ---------------------------------------------------------------------------

class TestPairedBootstrap:
    def test_identical_scores_no_difference(self):
        scores = [0.5, 0.6, 0.7, 0.8, 0.5, 0.6, 0.7, 0.8, 0.5, 0.6]
        result = paired_bootstrap_test(scores, scores)
        assert result["observed_diff"] == 0.0
        assert result["p_value"] >= 0.05  # not significant

    def test_clearly_different_scores(self):
        a = [0.3] * 50
        b = [0.9] * 50
        result = paired_bootstrap_test(a, b)
        assert result["observed_diff"] == pytest.approx(0.6, abs=0.01)
        assert result["p_value"] < 0.01  # significant

    def test_returns_confidence_interval(self):
        a = [0.4, 0.5, 0.4, 0.5, 0.4, 0.5, 0.4, 0.5, 0.4, 0.5]
        b = [0.7, 0.8, 0.7, 0.8, 0.7, 0.8, 0.7, 0.8, 0.7, 0.8]
        result = paired_bootstrap_test(a, b)
        assert result["ci_95_lo"] > 0  # CI should be positive
        assert result["ci_95_hi"] > result["ci_95_lo"]

    def test_n_matches_input(self):
        a = [0.5] * 20
        b = [0.6] * 20
        result = paired_bootstrap_test(a, b)
        assert result["n"] == 20


class TestWilcoxonSignedRank:
    def test_identical_scores(self):
        scores = [0.5, 0.6, 0.7, 0.8, 0.5]
        result = wilcoxon_signed_rank(scores, scores)
        assert result["n_nonzero"] == 0

    def test_clearly_different_scores(self):
        a = [0.3] * 20
        b = [0.9] * 20
        result = wilcoxon_signed_rank(a, b)
        assert result["p_value"] < 0.01
        assert result["w_plus"] > result["w_minus"]

    def test_small_sample_nan(self):
        """Small samples (< 10 nonzero) return NaN p-value."""
        a = [0.3, 0.4, 0.5]
        b = [0.6, 0.7, 0.8]
        result = wilcoxon_signed_rank(a, b)
        assert math.isnan(result["p_value"])
        assert result["n_nonzero"] == 3


class TestMeanWithCI:
    def test_empty_list(self):
        result = mean_with_ci([])
        assert result["mean"] == 0.0
        assert result["n"] == 0

    def test_single_value(self):
        result = mean_with_ci([0.5])
        assert result["mean"] == 0.5
        assert result["n"] == 1

    def test_known_mean(self):
        result = mean_with_ci([0.4, 0.5, 0.6, 0.7, 0.8])
        assert result["mean"] == pytest.approx(0.6, abs=0.01)
        assert result["n"] == 5

    def test_ci_contains_mean(self):
        values = [0.3, 0.4, 0.5, 0.6, 0.7, 0.5, 0.6, 0.4, 0.5, 0.6]
        result = mean_with_ci(values)
        assert result["ci_lo"] <= result["mean"] <= result["ci_hi"]


# ---------------------------------------------------------------------------
# Table generation
# ---------------------------------------------------------------------------

class TestTableGeneration:
    def test_main_results_table_has_header(self, sample_responses, sample_references):
        results = score_all(sample_responses, sample_references)
        table = generate_main_results_table(results)
        assert "| Metric |" in table
        assert "Baseline" in table
        assert "RAG" in table
        assert "MCP" in table

    def test_main_results_table_has_all_metrics(self, sample_responses, sample_references):
        results = score_all(sample_responses, sample_references)
        table = generate_main_results_table(results)
        assert "Pinyin" in table
        assert "Completeness" in table
        assert "Composite" in table

    def test_band_breakdown_table(self, sample_responses, sample_references):
        results = score_all(sample_responses, sample_references)
        table = generate_band_breakdown_table(results)
        assert "high" in table
        assert "mid" in table
        assert "low" in table
        assert "rare" in table

    def test_significance_table(self, sample_responses, sample_references):
        results = score_all(sample_responses, sample_references)
        table = generate_significance_table(results)
        assert "RAG vs Base" in table
        assert "MCP vs Base" in table
        assert "MCP vs RAG" in table

    def test_context_size_table(self, sample_prompts):
        table = generate_context_size_table(sample_prompts)
        assert "RAG" in table
        assert "MCP" in table
        assert "Ratio" in table
