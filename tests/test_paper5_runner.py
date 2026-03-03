"""Tests for Paper 5 experiment runner."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.paper5_runner import (
    CONDITION_KEYS,
    PROVIDERS,
    _resolve_api_key,
    call_llm,
    load_responses,
    run_single_headword,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_prompt():
    """A minimal prompt entry matching paper5_eval_prompts.json format."""
    return {
        "term": "测试",
        "pinyin": "ce4 shi4",
        "band": "mid",
        "corpus_hits": 5000,
        "condition_a_baseline": "Generate a dictionary entry for: 测试\n\nInclude pinyin, definition, example.",
        "condition_b_rag": "Generate a dictionary entry for: 测试\n\nPassages:\n[1] 测试结果显示...\n\nInclude pinyin, definition, example.",
        "condition_c_mcp": "Generate a dictionary entry for: 测试\n\n# Word Report: 测试\n## Definitions\n- test\n\nInclude pinyin, definition, example.",
        "rag_context_chars": 50,
        "mcp_context_chars": 100,
    }


@pytest.fixture
def sample_response():
    """A sample response in the expected output format."""
    return {
        "term": "测试",
        "band": "mid",
        "pinyin": "ce4 shi4",
        "response_baseline": "# 测试 (cè shì)\n\n**Pinyin**: ce4 shi4\n**Definition**: test, exam\n**Example**: 这次测试很难。",
        "response_baseline_meta": {
            "model": "test-model",
            "usage": {"prompt_tokens": 50, "completion_tokens": 80},
            "elapsed_s": 1.5,
            "error": None,
        },
        "response_rag": "# 测试 (cè shì)\n\n**Pinyin**: ce4 shi4\n**Definition**: test, exam, trial\n**Example**: 测试结果显示一切正常。",
        "response_rag_meta": {
            "model": "test-model",
            "usage": {"prompt_tokens": 100, "completion_tokens": 90},
            "elapsed_s": 2.0,
            "error": None,
        },
        "response_mcp": "# 测试 (cè shì)\n\n**Pinyin**: ce4 shi4\n**Definition**: test, exam, trial, quiz\n**Example**: 我们需要进行测试来验证结果。",
        "response_mcp_meta": {
            "model": "test-model",
            "usage": {"prompt_tokens": 150, "completion_tokens": 100},
            "elapsed_s": 2.5,
            "error": None,
        },
    }


# ---------------------------------------------------------------------------
# Provider profiles
# ---------------------------------------------------------------------------

class TestProviderProfiles:
    def test_minimax_profile_exists(self):
        assert "minimax" in PROVIDERS
        assert PROVIDERS["minimax"]["base_url"] == "https://api.minimax.io/v1"
        assert PROVIDERS["minimax"]["model"] == "MiniMax-M2.5"

    def test_groq_profile_exists(self):
        assert "groq" in PROVIDERS
        assert "groq.com" in PROVIDERS["groq"]["base_url"]

    def test_ollama_profile_exists(self):
        assert "ollama" in PROVIDERS
        assert "localhost" in PROVIDERS["ollama"]["base_url"]

    def test_resolve_api_key_literal(self):
        assert _resolve_api_key("literal:ollama", None) == "ollama"

    def test_resolve_api_key_cli_override(self):
        assert _resolve_api_key("literal:ollama", "my-key") == "my-key"

    def test_resolve_api_key_env(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY", "env-key-123")
        assert _resolve_api_key("env:TEST_KEY", None) == "env-key-123"


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

class TestCallLLM:
    def test_successful_call(self):
        """Test that call_llm returns expected structure."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response text"
        mock_response.model = "test-model"
        mock_response.usage.prompt_tokens = 50
        mock_response.usage.completion_tokens = 30
        mock_client.chat.completions.create.return_value = mock_response

        result = asyncio.run(call_llm(mock_client, "test-model", "Hello"))

        assert result["text"] == "Test response text"
        assert result["model"] == "test-model"
        assert result["error"] is None
        assert result["usage"]["prompt_tokens"] == 50
        assert result["usage"]["completion_tokens"] == 30
        assert result["elapsed_s"] >= 0

    def test_error_handling(self):
        """Test that call_llm captures errors gracefully."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = Exception("API timeout")

        result = asyncio.run(call_llm(mock_client, "test-model", "Hello"))

        assert result["text"] == ""
        assert result["error"] == "API timeout"
        assert result["elapsed_s"] >= 0


# ---------------------------------------------------------------------------
# Run single headword
# ---------------------------------------------------------------------------

class TestRunSingleHeadword:
    def test_runs_all_three_conditions(self, sample_prompt):
        """Test that all 3 conditions are called for each headword."""
        call_count = 0

        async def mock_create(**kwargs):
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            resp.choices = [MagicMock()]
            resp.choices[0].message.content = f"Response {call_count}"
            resp.model = "test-model"
            resp.usage.prompt_tokens = 50
            resp.usage.completion_tokens = 30
            return resp

        mock_client = AsyncMock()
        mock_client.chat.completions.create = mock_create

        result = asyncio.run(
            run_single_headword(mock_client, "test-model", sample_prompt, 0.0, 1024)
        )

        assert call_count == 3
        assert result["term"] == "测试"
        assert result["band"] == "mid"
        assert "response_baseline" in result
        assert "response_rag" in result
        assert "response_mcp" in result
        assert result["response_baseline"] == "Response 1"
        assert result["response_rag"] == "Response 2"
        assert result["response_mcp"] == "Response 3"

    def test_metadata_captured(self, sample_prompt):
        """Test that metadata is captured for each condition."""
        async def mock_create(**kwargs):
            resp = MagicMock()
            resp.choices = [MagicMock()]
            resp.choices[0].message.content = "Response"
            resp.model = "my-model-v1"
            resp.usage.prompt_tokens = 100
            resp.usage.completion_tokens = 50
            return resp

        mock_client = AsyncMock()
        mock_client.chat.completions.create = mock_create

        result = asyncio.run(
            run_single_headword(mock_client, "my-model-v1", sample_prompt, 0.0, 1024)
        )

        for _, resp_key in CONDITION_KEYS:
            meta = result[f"{resp_key}_meta"]
            assert meta["model"] == "my-model-v1"
            assert meta["error"] is None
            assert meta["usage"]["prompt_tokens"] == 100


# ---------------------------------------------------------------------------
# Load/save responses
# ---------------------------------------------------------------------------

class TestLoadResponses:
    def test_load_missing_file(self, tmp_path):
        """Returns empty list when file doesn't exist."""
        result = load_responses(tmp_path / "nonexistent.json")
        assert result == []

    def test_load_existing_file(self, tmp_path):
        """Loads responses from existing file."""
        data = [{"term": "好", "response_mcp": "good"}]
        path = tmp_path / "responses.json"
        with open(path, "w") as f:
            json.dump(data, f)

        result = load_responses(path)
        assert len(result) == 1
        assert result[0]["term"] == "好"


# ---------------------------------------------------------------------------
# Response format validation
# ---------------------------------------------------------------------------

class TestResponseFormat:
    def test_response_matches_metrics_format(self, sample_response):
        """Verify response format is compatible with paper5_metrics.py."""
        # paper5_metrics.py expects these keys
        assert "response_baseline" in sample_response
        assert "response_rag" in sample_response
        assert "response_mcp" in sample_response

        # And they should be strings
        assert isinstance(sample_response["response_baseline"], str)
        assert isinstance(sample_response["response_rag"], str)
        assert isinstance(sample_response["response_mcp"], str)

    def test_condition_keys_match(self):
        """Verify CONDITION_KEYS align with what metrics expects."""
        expected_response_keys = {"response_baseline", "response_rag", "response_mcp"}
        actual = {rk for _, rk in CONDITION_KEYS}
        assert actual == expected_response_keys
