"""Tests for dictmaster translation prompts and response cleaning."""

import pytest

from tools.dictmaster.translate.prompts import (
    ALL_TARGET_LANGS,
    LANG_NAMES,
    build_batch_prompt,
    build_translate_prompt,
    build_universal_batch_prompt,
    build_universal_prompt,
    build_verify_prompt,
    parse_universal_batch_response,
    parse_universal_response,
)
from tools.dictmaster.translate.minimax_ollama import _clean_response


class TestPromptBuilding:
    """Test prompt template construction."""

    def test_translate_prompt_basic(self):
        prompt = build_translate_prompt(
            "你好", "你好", "ni3 hao3", "intj", "fr",
            {"en": "hello/hi"},
        )
        assert "你好" in prompt
        assert "ni3 hao3" in prompt
        assert "French" in prompt
        assert "English: hello/hi" in prompt

    def test_translate_prompt_no_context(self):
        prompt = build_translate_prompt(
            "你好", "你好", "ni3 hao3", "", "es", {},
        )
        assert "Spanish" in prompt
        assert "(none)" in prompt

    def test_verify_prompt(self):
        prompt = build_verify_prompt(
            "銀行", "银行", "yin2 hang2", "noun", "de",
            "Bank/Geldinstitut",
            {"en": "bank", "fr": "banque"},
        )
        assert "German" in prompt
        assert "Bank/Geldinstitut" in prompt
        assert "English: bank" in prompt
        assert "French: banque" in prompt

    def test_batch_prompt(self):
        entries = [
            {
                "traditional": "你好",
                "simplified": "你好",
                "pinyin": "ni3 hao3",
                "pos": "intj",
                "context_defs": {"en": "hello"},
            },
            {
                "traditional": "謝謝",
                "simplified": "谢谢",
                "pinyin": "xie4 xie5",
                "pos": "verb",
                "context_defs": {"en": "thanks"},
            },
        ]
        prompt = build_batch_prompt(entries, "ko")
        assert "Korean" in prompt
        assert "1." in prompt
        assert "2." in prompt
        assert "你好" in prompt
        assert "謝謝" in prompt


class TestCleanResponse:
    """Test LLM response cleaning."""

    def test_plain(self):
        assert _clean_response("hello/hi") == "hello/hi"

    def test_strips_whitespace(self):
        assert _clean_response("  hello/hi  ") == "hello/hi"

    def test_strips_slashes(self):
        assert _clean_response("/hello/hi/") == "hello/hi"

    def test_strips_quotes(self):
        assert _clean_response('"hello/hi"') == "hello/hi"

    def test_strips_numbered_prefix(self):
        assert _clean_response("1. hello/hi") == "hello/hi"
        assert _clean_response("12. something") == "something"

    def test_empty(self):
        assert _clean_response("") == ""


class TestUniversalPromptBuilding:
    """Test universal (all-languages) prompt construction."""

    def test_universal_prompt_basic(self):
        prompt = build_universal_prompt(
            "銀行", "银行", "yin2 hang2", "noun",
            {"en": "bank", "de": "Bank"},
        )
        assert "銀行 / 银行" in prompt
        assert "yin2 hang2" in prompt
        assert "noun" in prompt
        assert "English: bank" in prompt
        assert "German: Bank" in prompt
        # Should have all 11 lang lines
        for lang in ALL_TARGET_LANGS:
            assert f"{lang}:" in prompt

    def test_universal_prompt_with_examples(self):
        prompt = build_universal_prompt(
            "銀行", "银行", "yin2 hang2", "noun",
            {"en": "bank"},
            examples=["中国银行是中国五大银行之一。"],
        )
        assert "Example sentences:" in prompt
        assert "中国银行是中国五大银行之一" in prompt

    def test_universal_prompt_no_examples(self):
        prompt = build_universal_prompt(
            "你好", "你好", "ni3 hao3", "", {}, examples=None,
        )
        assert "Example sentences:" not in prompt

    def test_universal_prompt_custom_langs(self):
        prompt = build_universal_prompt(
            "你好", "你好", "ni3 hao3", "intj", {},
            target_langs=["es", "ko"],
        )
        assert "es:" in prompt
        assert "ko:" in prompt
        # Should NOT have langs not requested
        assert "\nde:" not in prompt

    def test_universal_prompt_no_context(self):
        prompt = build_universal_prompt(
            "你好", "你好", "ni3 hao3", "", {},
        )
        assert "(none)" in prompt

    def test_universal_batch_prompt(self):
        entries = [
            {
                "traditional": "銀行",
                "simplified": "银行",
                "pinyin": "yin2 hang2",
                "pos": "noun",
                "context_defs": {"en": "bank"},
                "examples": ["去银行取钱。"],
            },
            {
                "traditional": "你好",
                "simplified": "你好",
                "pinyin": "ni3 hao3",
                "pos": "intj",
                "context_defs": {"en": "hello"},
            },
        ]
        prompt = build_universal_batch_prompt(entries)
        assert "1." in prompt
        assert "2." in prompt
        assert "銀行" in prompt
        assert "你好" in prompt
        assert "去银行取钱" in prompt
        for lang in ALL_TARGET_LANGS:
            assert f"{lang}:" in prompt

    def test_universal_batch_prompt_custom_langs(self):
        entries = [
            {
                "traditional": "你好",
                "simplified": "你好",
                "pinyin": "ni3 hao3",
                "pos": "intj",
                "context_defs": {},
            },
        ]
        prompt = build_universal_batch_prompt(entries, target_langs=["fr", "ja"])
        assert "fr:" in prompt
        assert "ja:" in prompt


class TestUniversalResponseParsing:
    """Test parsing of universal translation responses."""

    def test_parse_single_response(self):
        response = """en: bank/financial institution
de: Bank/Geldinstitut
fr: banque
es: banco
sv: bank
ja: 銀行
ko: 은행
ru: банк
id: bank
vi: ngân hàng
tl: bangko"""
        result = parse_universal_response(response)
        assert result["en"] == "bank/financial institution"
        assert result["de"] == "Bank/Geldinstitut"
        assert result["fr"] == "banque"
        assert result["ja"] == "銀行"
        assert result["ko"] == "은행"
        assert result["tl"] == "bangko"
        assert len(result) == 11

    def test_parse_single_with_custom_langs(self):
        response = """es: banco
ko: 은행"""
        result = parse_universal_response(response, target_langs=["es", "ko"])
        assert result == {"es": "banco", "ko": "은행"}

    def test_parse_ignores_unknown_langs(self):
        response = """en: hello
xx: something
de: hallo"""
        result = parse_universal_response(response)
        assert "en" in result
        assert "de" in result
        assert "xx" not in result

    def test_parse_strips_quotes(self):
        response = 'en: "bank/financial institution"'
        result = parse_universal_response(response)
        assert result["en"] == "bank/financial institution"

    def test_parse_strips_slashes(self):
        response = "en: /bank/financial institution/"
        result = parse_universal_response(response)
        assert result["en"] == "bank/financial institution"

    def test_parse_skips_empty_definitions(self):
        response = """en: bank
de:
fr: banque"""
        result = parse_universal_response(response)
        assert "en" in result
        assert "de" not in result
        assert "fr" in result

    def test_parse_batch_response(self):
        response = """1.
en: bank/financial institution
de: Bank
fr: banque

2.
en: hello/hi
de: Hallo
fr: bonjour"""
        results = parse_universal_batch_response(response, 2)
        assert len(results) == 2
        assert results[0]["en"] == "bank/financial institution"
        assert results[0]["fr"] == "banque"
        assert results[1]["en"] == "hello/hi"
        assert results[1]["de"] == "Hallo"

    def test_parse_batch_pads_missing(self):
        response = """1.
en: bank"""
        results = parse_universal_batch_response(response, 3)
        assert len(results) == 3
        assert results[0]["en"] == "bank"
        assert results[1] == {}
        assert results[2] == {}

    def test_parse_batch_truncates_extra(self):
        response = """1.
en: one

2.
en: two

3.
en: three"""
        results = parse_universal_batch_response(response, 2)
        assert len(results) == 2

    def test_parse_batch_with_inline_lang(self):
        """Handle case where first lang is on same line as entry number."""
        response = """1. en: bank
de: Bank

2. en: hello
de: Hallo"""
        results = parse_universal_batch_response(response, 2)
        assert len(results) == 2
        assert results[0]["en"] == "bank"
        assert results[1]["en"] == "hello"

    def test_parse_batch_custom_langs(self):
        response = """1.
es: banco
ko: 은행

2.
es: hola
ko: 안녕하세요"""
        results = parse_universal_batch_response(response, 2, target_langs=["es", "ko"])
        assert results[0] == {"es": "banco", "ko": "은행"}
        assert results[1] == {"es": "hola", "ko": "안녕하세요"}

    def test_parse_single_line_format(self):
        """Handle all langs on one line separated by /xx: boundaries."""
        response = "en: bank/de: Bank/fr: banque/es: banco"
        result = parse_universal_response(response)
        assert result["en"] == "bank"
        assert result["de"] == "Bank"
        assert result["fr"] == "banque"
        assert result["es"] == "banco"

    def test_parse_single_line_with_slashes_in_def(self):
        """Slash-separated glosses within a definition should be preserved."""
        response = "en: bank/financial institution/de: Bank/Geldinstitut/fr: banque"
        result = parse_universal_response(response)
        assert result["en"] == "bank/financial institution"
        assert result["de"] == "Bank/Geldinstitut"
        assert result["fr"] == "banque"

    def test_parse_batch_single_line_format(self):
        """Handle batch where each entry is on one line with /xx: separators."""
        response = (
            "1. en: bank/de: Bank/fr: banque\n"
            "\n"
            "2. en: hello/de: Hallo/fr: bonjour"
        )
        results = parse_universal_batch_response(response, 2)
        assert len(results) == 2
        assert results[0]["en"] == "bank"
        assert results[0]["de"] == "Bank"
        assert results[1]["en"] == "hello"
        assert results[1]["fr"] == "bonjour"


class TestLangNames:
    """Test language name coverage."""

    def test_all_target_langs_have_names(self):
        expected = {"en", "de", "fr", "es", "sv", "ja", "ko", "ru", "id", "vi", "tl"}
        assert expected.issubset(set(LANG_NAMES.keys()))
