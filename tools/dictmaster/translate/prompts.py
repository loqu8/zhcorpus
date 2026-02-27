"""Prompt templates for MiniMax M2.5 dictionary translation and verification."""

SYSTEM_PROMPT = """\
You are a professional Chinese lexicographer producing dictionary-style definitions.

Rules:
- Output ONLY slash-separated glosses in the target language, nothing else
- Be concise: dictionary style, not full sentences
- Use the target language exclusively (no Chinese characters in the definition)
- For verbs, start with the infinitive form appropriate to the target language
- For nouns, give the most common equivalent(s)
- Maximum 5 glosses per entry
- No explanatory notes, no parenthetical qualifiers unless essential for disambiguation"""

TRANSLATE_TEMPLATE = """\
Translate this Chinese dictionary entry into {target_lang_name}.

Chinese: {traditional} / {simplified}
Pinyin: {pinyin}
POS: {pos}

Existing definitions for context:
{context_definitions}

Output the {target_lang_name} definition as slash-separated glosses.
Example format: meaning1/meaning2/meaning3"""

VERIFY_TEMPLATE = """\
Verify and improve this Chinese-{target_lang_name} dictionary definition.

Chinese: {traditional} / {simplified}
Pinyin: {pinyin}
POS: {pos}

Current {target_lang_name} definition: {current_definition}

Context from other languages:
{context_definitions}

If the definition is correct and well-formatted, output it unchanged.
If it needs improvement, output the corrected version.
Output ONLY the slash-separated glosses."""

BATCH_TRANSLATE_TEMPLATE = """\
Translate these Chinese dictionary entries into {target_lang_name}.
Output one line per entry, in the same order. Each line should contain ONLY slash-separated glosses.

{entries}"""

# Language names for prompts
LANG_NAMES = {
    "en": "English",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "sv": "Swedish",
    "ja": "Japanese",
    "ko": "Korean",
    "ru": "Russian",
    "id": "Indonesian",
    "vi": "Vietnamese",
    "tl": "Tagalog",
}


def build_translate_prompt(
    traditional: str,
    simplified: str,
    pinyin: str,
    pos: str,
    target_lang: str,
    context_defs: dict[str, str],
) -> str:
    """Build a translation prompt for a single entry."""
    context_lines = []
    for lang, defn in context_defs.items():
        lang_name = LANG_NAMES.get(lang, lang)
        context_lines.append(f"  {lang_name}: {defn}")

    return TRANSLATE_TEMPLATE.format(
        traditional=traditional,
        simplified=simplified,
        pinyin=pinyin,
        pos=pos or "unknown",
        target_lang_name=LANG_NAMES.get(target_lang, target_lang),
        context_definitions="\n".join(context_lines) if context_lines else "(none)",
    )


def build_verify_prompt(
    traditional: str,
    simplified: str,
    pinyin: str,
    pos: str,
    target_lang: str,
    current_definition: str,
    context_defs: dict[str, str],
) -> str:
    """Build a verification prompt for an existing definition."""
    context_lines = []
    for lang, defn in context_defs.items():
        if lang != target_lang:
            lang_name = LANG_NAMES.get(lang, lang)
            context_lines.append(f"  {lang_name}: {defn}")

    return VERIFY_TEMPLATE.format(
        traditional=traditional,
        simplified=simplified,
        pinyin=pinyin,
        pos=pos or "unknown",
        target_lang_name=LANG_NAMES.get(target_lang, target_lang),
        current_definition=current_definition,
        context_definitions="\n".join(context_lines) if context_lines else "(none)",
    )


def build_batch_prompt(
    entries: list[dict],
    target_lang: str,
) -> str:
    """Build a batch translation prompt for multiple entries.

    Each entry dict has: traditional, simplified, pinyin, pos, context_defs
    """
    lines = []
    for i, e in enumerate(entries, 1):
        ctx = ""
        for lang, defn in e.get("context_defs", {}).items():
            lang_name = LANG_NAMES.get(lang, lang)
            ctx += f" [{lang_name}: {defn}]"
        lines.append(
            f"{i}. {e['traditional']} / {e['simplified']} [{e['pinyin']}] "
            f"({e.get('pos', '?')}){ctx}"
        )

    return BATCH_TRANSLATE_TEMPLATE.format(
        target_lang_name=LANG_NAMES.get(target_lang, target_lang),
        entries="\n".join(lines),
    )


# ---------------------------------------------------------------------------
# Universal (all-languages-at-once) prompts
# ---------------------------------------------------------------------------

ALL_TARGET_LANGS = ["en", "de", "fr", "es", "sv", "ja", "ko", "ru", "id", "vi", "tl"]

UNIVERSAL_SYSTEM_PROMPT = """\
You are a professional multilingual Chinese lexicographer producing \
dictionary-style definitions in 11 languages.

Rules:
- Output EXACTLY one line per language in format "xx: def1/def2"
- Be concise: dictionary style, not full sentences
- Use the target language exclusively for each definition
- For verbs, start with the infinitive form appropriate to the target language
- For nouns, give the most common equivalent(s)
- Maximum 5 glosses per entry
- If an existing definition is provided, you may rewrite it for consistency
- No explanatory notes, no parenthetical qualifiers unless essential"""

UNIVERSAL_TRANSLATE_TEMPLATE = """\
Chinese: {traditional} / {simplified}
Pinyin: {pinyin}
POS: {pos}

Existing definitions:
{context_definitions}
{example_section}
Produce definitions for each language below. Output EXACTLY one line per \
language in format "xx: def1/def2". Each language MUST be on its own line.

{lang_lines}"""

UNIVERSAL_BATCH_TEMPLATE = """\
Translate these Chinese dictionary entries into all requested languages.

CRITICAL FORMAT: For each numbered entry, output ONE LINE PER LANGUAGE.
Each line must be "xx: def1/def2" on its own line. Do NOT combine languages on one line.
Separate entries with a blank line.

{entries}"""


def _format_context_defs(context_defs: dict[str, str]) -> str:
    """Format existing definitions as indented lines."""
    if not context_defs:
        return "  (none)"
    lines = []
    for lang, defn in context_defs.items():
        lang_name = LANG_NAMES.get(lang, lang)
        lines.append(f"  {lang_name}: {defn}")
    return "\n".join(lines)


def _format_example_section(examples: list[str] | None) -> str:
    """Format example sentences section (empty string if no examples)."""
    if not examples:
        return ""
    lines = "\n".join(f"  {ex}" for ex in examples)
    return f"\nExample sentences:\n{lines}\n"


def _format_lang_lines(target_langs: list[str] | None = None) -> str:
    """Format the 'xx:' lines the model should fill in."""
    langs = target_langs or ALL_TARGET_LANGS
    return "\n".join(f"{lang}:" for lang in langs)


def build_universal_prompt(
    traditional: str,
    simplified: str,
    pinyin: str,
    pos: str,
    context_defs: dict[str, str],
    examples: list[str] | None = None,
    target_langs: list[str] | None = None,
) -> str:
    """Build a universal translation prompt for a single entry (all languages)."""
    return UNIVERSAL_TRANSLATE_TEMPLATE.format(
        traditional=traditional,
        simplified=simplified,
        pinyin=pinyin,
        pos=pos or "unknown",
        context_definitions=_format_context_defs(context_defs),
        example_section=_format_example_section(examples),
        lang_lines=_format_lang_lines(target_langs),
    )


def build_universal_batch_prompt(
    entries: list[dict],
    target_langs: list[str] | None = None,
) -> str:
    """Build a universal batch translation prompt for multiple entries.

    Each entry dict has: traditional, simplified, pinyin, pos, context_defs,
    and optionally 'examples' (list of strings).
    """
    langs = target_langs or ALL_TARGET_LANGS
    lang_lines = "\n".join(f"{lang}:" for lang in langs)

    blocks = []
    for i, e in enumerate(entries, 1):
        ctx = _format_context_defs(e.get("context_defs", {}))
        example_section = _format_example_section(e.get("examples"))

        block = (
            f"{i}. {e['traditional']} / {e['simplified']}\n"
            f"   Pinyin: {e['pinyin']}\n"
            f"   POS: {e.get('pos') or 'unknown'}\n"
            f"   Existing definitions:\n{ctx}\n"
            f"{example_section}"
            f"   {lang_lines}"
        )
        blocks.append(block)

    return UNIVERSAL_BATCH_TEMPLATE.format(entries="\n\n".join(blocks))


def _normalize_response_lines(response: str, langs: set[str]) -> list[str]:
    """Normalize response into one-lang-per-line format.

    Handles the case where the model puts all langs on one line like:
    "en: bank/de: Bank/fr: banque" — splits on "/xx:" boundaries.
    """
    import re
    # Build a regex that splits on "/xx:" where xx is a known lang code
    lang_pattern = "|".join(re.escape(l) for l in sorted(langs))
    splitter = re.compile(rf"/({lang_pattern}):")

    lines = []
    for raw_line in response.strip().split("\n"):
        raw_line = raw_line.strip()
        if not raw_line:
            lines.append("")
            continue
        # Check if this line contains multiple "xx:" segments
        parts = splitter.split(raw_line)
        if len(parts) > 1:
            # parts = [first_segment, lang1, rest1, lang2, rest2, ...]
            lines.append(parts[0])
            for j in range(1, len(parts), 2):
                lang_code = parts[j]
                rest = parts[j + 1] if j + 1 < len(parts) else ""
                lines.append(f"{lang_code}:{rest}")
        else:
            lines.append(raw_line)
    return lines


def parse_universal_response(response: str, target_langs: list[str] | None = None) -> dict[str, str]:
    """Parse a universal translation response into {lang: definition} dict.

    Expects lines like "en: bank/financial institution".
    Also handles single-line format where langs are separated by "/xx:".
    """
    langs = set(target_langs or ALL_TARGET_LANGS)
    lines = _normalize_response_lines(response, langs)
    result = {}
    for line in lines:
        line = line.strip()
        if not line or ":" not in line:
            continue
        prefix, _, defn = line.partition(":")
        prefix = prefix.strip().lower()
        if prefix in langs:
            cleaned = defn.strip()
            # Remove surrounding quotes
            if cleaned.startswith('"') and cleaned.endswith('"'):
                cleaned = cleaned[1:-1]
            # Remove leading/trailing slashes
            if cleaned.startswith("/"):
                cleaned = cleaned[1:]
            if cleaned.endswith("/"):
                cleaned = cleaned[:-1]
            cleaned = cleaned.strip()
            if cleaned:
                result[prefix] = cleaned
    return result


def parse_universal_batch_response(
    response: str,
    count: int,
    target_langs: list[str] | None = None,
) -> list[dict[str, str]]:
    """Parse a universal batch response into list of {lang: definition} dicts.

    Expects numbered entries separated by blank lines, each with "xx: ..." lines.
    Also handles single-line format where langs are separated by "/xx:".
    """
    langs = set(target_langs or ALL_TARGET_LANGS)
    lines = _normalize_response_lines(response, langs)
    results: list[dict[str, str]] = []
    current: dict[str, str] = {}

    for line in lines:
        line = line.strip()

        # Detect entry boundary: line starting with a number followed by period
        if line and line[0].isdigit():
            parts = line.split(".", 1)
            if len(parts) == 2 and parts[0].strip().isdigit():
                # Save previous entry if we had one
                if current:
                    results.append(current)
                    current = {}
                # The rest of this line might contain a lang: def
                remainder = parts[1].strip()
                if remainder and ":" in remainder:
                    prefix, _, defn = remainder.partition(":")
                    prefix = prefix.strip().lower()
                    if prefix in langs and defn.strip():
                        current[prefix] = defn.strip()
                continue

        # Parse "xx: definition" lines
        if not line or ":" not in line:
            continue
        prefix, _, defn = line.partition(":")
        prefix = prefix.strip().lower()
        if prefix in langs:
            cleaned = defn.strip()
            if cleaned.startswith('"') and cleaned.endswith('"'):
                cleaned = cleaned[1:-1]
            if cleaned.startswith("/"):
                cleaned = cleaned[1:]
            if cleaned.endswith("/"):
                cleaned = cleaned[:-1]
            cleaned = cleaned.strip()
            if cleaned:
                current[prefix] = cleaned

    # Don't forget the last entry
    if current:
        results.append(current)

    # Pad with empty dicts if response was short
    while len(results) < count:
        results.append({})

    return results[:count]
