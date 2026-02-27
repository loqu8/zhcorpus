"""Parse Wiktextract (Kaikki.org) Chinese dictionary JSONL extracts.

Source: kaikki.org/dictionary/Chinese/kaikki.org-dictionary-Chinese.jsonl.gz
Format: one JSON object per line, one entry per word+POS combination.

Key fields:
- word: headword (typically Traditional Chinese)
- pos: part of speech (noun, verb, adj, ...)
- forms[]: alternative forms with tags ("Simplified-Chinese")
- sounds[]: pronunciation with tags ("Mandarin", "Pinyin") -> zh_pron field
- senses[].glosses[]: English definitions
- translations[]: translations from Chinese into other languages
"""

import gzip
import json
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Iterator, NamedTuple, Optional

from tools.dictmaster.schema import ensure_source, upsert_definition, upsert_headword


# Tone-marked vowel -> (base vowel, tone number)
_TONE_MAP = {}
_TONE_MARKS = {
    "\u0304": "1",  # macron (ā)
    "\u0301": "2",  # acute (á)
    "\u030C": "3",  # caron (ǎ)
    "\u0300": "4",  # grave (à)
}
# Build lookup for precomposed characters
for _base in "aeiouüAEIOUÜ":
    for _mark, _tone in _TONE_MARKS.items():
        _composed = unicodedata.normalize("NFC", _base + _mark)
        if len(_composed) == 1:
            _TONE_MAP[_composed] = (_base, _tone)


def tone_marked_to_numbered(pinyin: str) -> str:
    """Convert tone-marked pinyin to numbered pinyin.

    Examples:
        "diànnǎo" -> "dian4 nao3"
        "zhōngguó" -> "zhong1 guo2"
        "nǐ hǎo" -> "ni3 hao3"
    """
    if not pinyin:
        return ""

    # Split on whitespace or detect syllable boundaries
    # First, normalize to handle combining marks
    pinyin = unicodedata.normalize("NFC", pinyin)

    # Split into syllables (space-separated or run together)
    # If already space-separated, process each syllable
    if " " in pinyin:
        syllables = pinyin.split()
        return " ".join(_convert_syllable(s) for s in syllables)

    # Run-together pinyin: split on known boundaries
    return _split_and_convert(pinyin)


def _convert_syllable(syllable: str) -> str:
    """Convert a single tone-marked syllable to numbered."""
    tone = "5"  # neutral tone by default
    result = []
    for ch in syllable:
        if ch in _TONE_MAP:
            base, t = _TONE_MAP[ch]
            result.append(base)
            tone = t
        else:
            result.append(ch)
    return "".join(result) + tone


# Pinyin initials for syllable splitting
_INITIALS = [
    "zh", "ch", "sh", "b", "p", "m", "f", "d", "t", "n", "l",
    "g", "k", "h", "j", "q", "x", "z", "c", "s", "r", "y", "w",
]

# Pinyin finals (without tones) for validation
_FINALS_RE = re.compile(
    r"(?:iang|iong|uang|ang|eng|ing|ong|uai|uan|ian|iao|"
    r"ai|ei|ao|ou|an|en|in|un|er|ia|ie|iu|ua|ue|ui|uo|"
    r"a|e|i|o|u|ü|v)(?:n(?![aeiouüv])|ng|r)?",
    re.IGNORECASE,
)


def _split_and_convert(pinyin: str) -> str:
    """Split run-together tone-marked pinyin into syllables and convert."""
    # Simple approach: convert first, then use syllable boundaries
    # Convert all tone marks to find tone positions
    converted = []
    tone_positions = []  # (position_in_result, tone_number)

    for ch in pinyin:
        if ch in _TONE_MAP:
            base, tone = _TONE_MAP[ch]
            converted.append(base)
            tone_positions.append((len(converted) - 1, tone))
        else:
            converted.append(ch)

    base_str = "".join(converted).lower()

    # Try to split into valid syllables
    syllables = []
    pos = 0
    tone_idx = 0

    while pos < len(base_str):
        if base_str[pos] in "' -":
            pos += 1
            continue

        # Find initial
        initial = ""
        for ini in _INITIALS:
            if base_str[pos:].startswith(ini):
                initial = ini
                break

        # Find final
        remaining = base_str[pos + len(initial):]
        match = _FINALS_RE.match(remaining)
        if match:
            final = match.group()
            syllable = initial + final
            # Find the tone for this syllable
            syl_start = pos
            syl_end = pos + len(syllable)
            tone = "5"
            for tpos, tnum in tone_positions:
                if syl_start <= tpos < syl_end:
                    tone = tnum
                    break
            syllables.append(syllable + tone)
            pos = syl_end
        elif initial:
            # Initial with no valid final — just append it
            syllables.append(initial)
            pos += len(initial)
        else:
            # Skip non-pinyin characters
            pos += 1

    return " ".join(syllables) if syllables else pinyin


# POS mapping from Wiktextract POS to our simplified tags
POS_MAP = {
    "noun": "noun",
    "verb": "verb",
    "adj": "adj",
    "adv": "adv",
    "name": "proper_noun",
    "prep": "prep",
    "conj": "conj",
    "intj": "intj",
    "pron": "pron",
    "det": "det",
    "num": "num",
    "particle": "particle",
    "classifier": "classifier",
    "phrase": "phrase",
    "proverb": "phrase",
    "idiom": "phrase",
    "suffix": "affix",
    "prefix": "affix",
    "affix": "affix",
}

# Wiktextract lang_code -> our ISO 639-1 codes for target languages we care about
WIKT_LANG_MAP = {
    "en": "en",
    "de": "de",
    "fr": "fr",
    "es": "es",
    "sv": "sv",
    "ja": "ja",
    "ko": "ko",
    "ru": "ru",
    "id": "id",
    "vi": "vi",
    "tl": "tl",
}


class WiktEntry(NamedTuple):
    traditional: str
    simplified: str
    pinyin: str
    pos: Optional[str]
    glosses_en: list[str]  # English glosses from senses
    translations: dict[str, list[str]]  # lang -> [gloss, ...]


def _get_simplified(entry: dict) -> Optional[str]:
    """Extract simplified form from forms[] array."""
    for form in entry.get("forms", []):
        tags = form.get("tags", [])
        if "Simplified-Chinese" in tags and "Second-Round-Simplified-Chinese" not in tags:
            return form.get("form")
    return None


def _get_pinyin(entry: dict) -> Optional[str]:
    """Extract Mandarin Pinyin from sounds[] array."""
    for sound in entry.get("sounds", []):
        tags = sound.get("tags", [])
        if "Mandarin" in tags and "Pinyin" in tags:
            zh_pron = sound.get("zh_pron", "")
            if zh_pron:
                return zh_pron
    return None


def _get_glosses(entry: dict) -> list[str]:
    """Extract English glosses from senses[].glosses[]."""
    glosses = []
    for sense in entry.get("senses", []):
        # Skip senses that are just form-of references
        if sense.get("form_of") or sense.get("alt_of"):
            continue
        raw = sense.get("glosses", [])
        if raw:
            # Take the last gloss (most specific if multiple)
            gloss = raw[-1] if len(raw) > 1 else raw[0]
            if gloss and gloss not in glosses:
                glosses.append(gloss)
    return glosses


def _get_translations(entry: dict) -> dict[str, list[str]]:
    """Extract translations from translations[] for our target languages."""
    result: dict[str, list[str]] = {}
    for trans in entry.get("translations", []):
        lang_code = trans.get("lang_code", "")
        word = trans.get("word", "")
        if lang_code in WIKT_LANG_MAP and word:
            our_code = WIKT_LANG_MAP[lang_code]
            if our_code not in result:
                result[our_code] = []
            if word not in result[our_code]:
                result[our_code].append(word)
    return result


def parse_wiktextract_entry(entry: dict) -> Optional[WiktEntry]:
    """Parse a single Wiktextract JSON entry into a WiktEntry.

    Returns None if the entry lacks essential fields (word, pinyin, glosses).
    """
    word = entry.get("word", "")
    if not word:
        return None

    # Skip non-Chinese entries (shouldn't happen in Chinese-specific file)
    if entry.get("lang_code") and entry["lang_code"] != "zh":
        return None

    traditional = word
    simplified = _get_simplified(entry) or traditional

    pinyin_marked = _get_pinyin(entry)
    if not pinyin_marked:
        return None

    pinyin = tone_marked_to_numbered(pinyin_marked)

    pos = POS_MAP.get(entry.get("pos", ""), None)

    glosses_en = _get_glosses(entry)
    if not glosses_en:
        return None

    translations = _get_translations(entry)

    return WiktEntry(
        traditional=traditional,
        simplified=simplified,
        pinyin=pinyin,
        pos=pos,
        glosses_en=glosses_en,
        translations=translations,
    )


def iter_wiktextract(path: Path) -> Iterator[WiktEntry]:
    """Iterate over Wiktextract entries from a JSONL file (plain or gzipped)."""
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            parsed = parse_wiktextract_entry(entry)
            if parsed:
                yield parsed


def import_wiktextract(
    conn: sqlite3.Connection,
    path: Path,
    *,
    batch_size: int = 5000,
    limit: Optional[int] = None,
) -> int:
    """Import Wiktextract JSONL into the master database.

    Imports both English glosses and translations for all target languages.

    Returns number of headwords imported.
    """
    ensure_source(conn, "wiktextract")
    count = 0

    for entry in iter_wiktextract(path):
        if limit and count >= limit:
            break

        hw_id = upsert_headword(
            conn, entry.traditional, entry.simplified, entry.pinyin, entry.pos
        )

        # Import English glosses
        defn_en = "/".join(entry.glosses_en)
        upsert_definition(conn, hw_id, "en", defn_en, "wiktextract")

        # Import translations for each target language
        for lang, words in entry.translations.items():
            defn = "/".join(words)
            upsert_definition(conn, hw_id, lang, defn, "wiktextract")

        count += 1
        if count % batch_size == 0:
            conn.commit()

    conn.commit()
    return count
