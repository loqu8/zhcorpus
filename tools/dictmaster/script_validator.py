"""Post-translation script validator for dictionary definitions.

Deterministic check that a definition uses only scripts valid for its
target language.  Prompt engineering alone cannot prevent the ~0.3-0.5%
contamination rate from MiniMax (Cyrillic leaking into Arabic, Hangul
into Japanese, etc.).  This module provides the hard reject gate.

CJK characters are allowed in metalinguistic cross-references
("variant of 迥", "used in 躊躇") — detected via regex patterns that
match common reference frames across all target languages.

WHY GAPS EXIST (see docs/translation-backfill-plan.md for full analysis):

  Most residual gaps are bound morphemes whose definitions inherently
  cite Chinese compounds: 躊 → "used in 躊躇".  The LLM correctly
  writes e.g. Arabic "يُستخدم في 躊躇 (chóuchú)" but this mixes three
  scripts (Arabic + CJK + Latin pinyin).

  - CJK in cross-references: ALLOWED (the reference patterns below
    detect "used in X", "variant of X", etc. in all 18 target languages)
  - Latin pinyin in Arabic/Persian/Thai: CORRECTLY REJECTED (the LLM
    should transliterate to target script or omit the parenthetical)
  - Multiple CJK runs joined by slashes/conjunctions (躊躇／踌躇):
    ALLOWED via conjunction patterns

Usage:
    from tools.dictmaster.script_validator import validate_definition

    ok, bad_scripts = validate_definition("ar", "بنك مالي")
    # ok=True, bad_scripts=set()

    ok, bad_scripts = validate_definition("ar", "жизнь واحدة")
    # ok=False, bad_scripts={"cyrillic"}
"""

import re

# ---------------------------------------------------------------------------
# Script detection
# ---------------------------------------------------------------------------

def _detect_scripts(text: str) -> set[str]:
    """Return the set of script families present in *text*."""
    scripts: set[str] = set()
    for ch in text:
        cp = ord(ch)
        if 0x0041 <= cp <= 0x024F:
            scripts.add("latin")
        elif 0x0400 <= cp <= 0x04FF:
            scripts.add("cyrillic")
        elif 0x0600 <= cp <= 0x06FF:
            scripts.add("arabic")
        elif 0x0750 <= cp <= 0x077F or 0xFB50 <= cp <= 0xFDFF or 0xFE70 <= cp <= 0xFEFF:
            scripts.add("arabic_ext")
        elif 0x0900 <= cp <= 0x097F:
            scripts.add("devanagari")
        elif 0x0E00 <= cp <= 0x0E7F:
            scripts.add("thai")
        elif 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or 0x20000 <= cp <= 0x2A6DF:
            scripts.add("cjk")
        elif 0xAC00 <= cp <= 0xD7AF:
            scripts.add("hangul")
        elif 0x3040 <= cp <= 0x309F or 0x30A0 <= cp <= 0x30FF:
            scripts.add("kana")
        elif 0x0590 <= cp <= 0x05FF:
            scripts.add("hebrew")
        elif 0x0370 <= cp <= 0x03FF:
            scripts.add("greek")
    return scripts


# Scripts considered valid for each target language.
# "latin" includes ASCII letters and Extended Latin (accented).
VALID_SCRIPTS: dict[str, set[str]] = {
    "en": {"latin"},
    "de": {"latin"},
    "fr": {"latin"},
    "es": {"latin"},
    "it": {"latin"},
    "pt": {"latin"},
    "sv": {"latin"},
    "nl": {"latin"},
    "id": {"latin"},
    "tl": {"latin"},
    "vi": {"latin"},

    "ru": {"cyrillic", "latin"},

    "ar": {"arabic", "arabic_ext"},
    "fa": {"arabic", "arabic_ext"},

    "hi": {"devanagari", "latin"},

    "th": {"thai", "latin"},

    "ja": {"cjk", "kana", "latin"},
    "ko": {"cjk", "hangul", "latin"},

    "tr": {"latin"},
    "ms": {"latin"},
    "pl": {"latin"},
    "hu": {"latin"},
    "cs": {"latin"},
    "el": {"greek", "latin"},
    "ro": {"latin"},
    "et": {"latin"},
}


# ---------------------------------------------------------------------------
# CJK cross-reference detection
# ---------------------------------------------------------------------------

# Patterns that frame a CJK character as a metalinguistic reference.
# Matches across all 18 target languages.  Each pattern is compiled once.
# The key insight: if every CJK run in the definition sits inside one of
# these frames, the CJK is legitimate.

_CJK_RUN = r'[\u4E00-\u9FFF\u3400-\u4DBF\U00020000-\U0002A6DF]+'

_REF_PATTERNS = [
    # English / Germanic / Romance
    re.compile(rf'(?:variant|old variant|archaic variant|ancient variant|ancient form|old form|'
               rf'same as|see also|see |abbr\b|abbrev|abbreviation|short for|'
               rf'component|radical|character|notation|form|'
               rf'surname|family name|given name|name)\s.*?({_CJK_RUN})', re.IGNORECASE),
    re.compile(rf'({_CJK_RUN})\s*(?:radical|component|stroke)', re.IGNORECASE),

    # German
    re.compile(rf'(?:Variante|Kurzform|Abkürzung|Bestandteil|Zeichen|Schreibweise|Notation)\s.*?({_CJK_RUN})', re.IGNORECASE),

    # French
    re.compile(rf'(?:variante|abréviation|composant|caractère|notation|forme)\s.*?({_CJK_RUN})', re.IGNORECASE),

    # Spanish
    re.compile(rf'(?:variante|abreviatura|componente|carácter|notación|forma)\s.*?({_CJK_RUN})', re.IGNORECASE),

    # Portuguese
    re.compile(rf'(?:variante|abreviatura|componente|caractere|notação|forma)\s.*?({_CJK_RUN})', re.IGNORECASE),

    # Italian
    re.compile(rf'(?:variante|abbreviazione|componente|carattere|notazione|forma)\s.*?({_CJK_RUN})', re.IGNORECASE),

    # Swedish
    re.compile(rf'(?:variant|förkortning|komponent|tecken|notation|form)\s.*?({_CJK_RUN})', re.IGNORECASE),

    # Dutch
    re.compile(rf'(?:variant|afkorting|component|karakter|notatie|vorm)\s.*?({_CJK_RUN})', re.IGNORECASE),

    # Indonesian
    re.compile(rf'(?:varian|singkatan|komponen|karakter|notasi|bentuk)\s.*?({_CJK_RUN})', re.IGNORECASE),

    # Tagalog
    re.compile(rf'(?:baryante|pagdadaglat|bahagi|karakter|notasyon|anyo)\s.*?({_CJK_RUN})', re.IGNORECASE),

    # Russian
    re.compile(rf'(?:вариант|сокращение|компонент|иероглиф|запись|форм\w*)\s.*?({_CJK_RUN})', re.IGNORECASE),

    # Japanese — 異体字 / 略字 / の variant patterns
    re.compile(rf'({_CJK_RUN})の(?:異体字|旧字体|略字|別字|俗字|本字|正字)'),
    re.compile(rf'(?:異体字|旧字体|略字|別字|古字).*?({_CJK_RUN})'),

    # Korean — 이체자 / 약자 patterns
    re.compile(rf'({_CJK_RUN})의\s*(?:이체자|약자|속자|본자|정자|변형)'),
    re.compile(rf'(?:이체자|약자|속자).*?({_CJK_RUN})'),

    # Vietnamese
    re.compile(rf'(?:biến thể|dạng cũ|dạng cổ|viết tắt|thành phần)\s.*?({_CJK_RUN})', re.IGNORECASE),

    # Arabic
    re.compile(rf'(?:شكل|بديل|مكون|عنصر|اختصار|واریانت|نوع|صورة)\s.*?({_CJK_RUN})'),

    # Persian
    re.compile(rf'(?:واریانت|شکل|مخفف|جزء|عنصر|کاراکتر)\s.*?({_CJK_RUN})'),

    # Hindi
    re.compile(rf'(?:रूप|प्रकार|संक्षेप|घटक|संस्करण)\s.*?({_CJK_RUN})'),

    # Thai
    re.compile(rf'(?:รูปแบบ|ตัวย่อ|ส่วนประกอบ|อักษร|แบบ)\s.*?({_CJK_RUN})'),

    # Greek
    re.compile(rf'(?:παραλλαγή|συντομογραφία|στοιχείο|χαρακτήρας|μορφή|σύντμηση)\s.*?({_CJK_RUN})'),

    # Turkish
    # Turkish: base forms and suffixed forms (varyantı, karakteri, kısaltması, etc.)
    re.compile(rf'(?:varyant\w*|kısaltma\w*|bileşen\w*|karakter\w*|biçim\w*|şekil\w*)\s.*?({_CJK_RUN})', re.IGNORECASE),

    # Polish
    re.compile(rf'(?:wariant|skrót|komponent|znak|forma|zapis)\s.*?({_CJK_RUN})', re.IGNORECASE),

    # Czech
    re.compile(rf'(?:varianta|zkratka|složka|znak|forma|zápis)\s.*?({_CJK_RUN})', re.IGNORECASE),

    # Hungarian
    re.compile(rf'(?:változat\w*|rövidítés\w*|összetevő\w*|karakter\w*|alak\w*|jelölés\w*)\s.*?({_CJK_RUN})', re.IGNORECASE),

    # Romanian
    re.compile(rf'(?:variantă|abreviere|componentă|caracter|formă|notație)\s.*?({_CJK_RUN})', re.IGNORECASE),

    # Estonian
    re.compile(rf'(?:variant\w*|lühend\w*|komponent\w*|märk\w*|vorm\w*|tähistus\w*|koostisosa\w*|variandi\w*)[/\s].*?({_CJK_RUN})', re.IGNORECASE),
    # CJK followed by Estonian variandina/koostisosa (reverse word order)
    re.compile(rf'({_CJK_RUN})\s+(?:variandi\w*|koostisosa\w*)', re.IGNORECASE),

    # Malay
    re.compile(rf'(?:varian|singkatan|komponen|aksara|bentuk|notasi)\s.*?({_CJK_RUN})', re.IGNORECASE),

    # Bare "of X" — catches "variant of 夂", "componente de 巽", etc.
    re.compile(rf'(?:of|de|di|von|van|av|dari|ng|của|의|の|ของ|для|für|pour|para|per|för)\s+({_CJK_RUN})'),

    # "used in X" / "verwendet in X" / "utilisé dans X" — cross-ref to compound
    # Allow up to 3 words between keyword and CJK (e.g. "używany w złożeniach 瑽瑢")
    # používá se = Czech verb form, kullanılır = Turkish passive, yalnızca = Turkish "only"
    re.compile(rf'(?:used|verwendet|utilisé|usado|usato|gebruikt|används|digunakan|ginagamit|dùng|используется|ใช้ใน|يُستخدم في|استفاده در|में प्रयुक्त|ใช้ใน|kullanıl\w*|używany|używane|używana|używano|používá\w*|používaný|használ\w*|utilizat|kasutatav|digunakan|χρησιμοποιείται|yalnızca)\s+(?:\w+\s+){{0,3}}({_CJK_RUN})', re.IGNORECASE),

    # Prepositions that immediately precede CJK: "في X", "در X"
    re.compile(rf'(?:dalam|في|در|trong|ใน)\s+({_CJK_RUN})'),
    # CJK followed by postposition (Hindi/Thai/Korean word order): "X में", "X का"
    re.compile(rf'({_CJK_RUN})\s*(?:में|ใน|에서|का|की|के|の|의|를|을|が|は|を)'),

    # CJK separated by conjunctions/slashes (躊躇／踌躇, 躊躇 و 踌躇)
    re.compile(rf'({_CJK_RUN})\s*[/／、，,]\s*({_CJK_RUN})'),
    re.compile(rf'({_CJK_RUN})\s*(?:and|or|و|и|dan|at|và|und|et|y|e|i|och|en|og|ve|és|a|și|ja|kai|και|lub|nebo|vagy|sau|või|veya)\s+({_CJK_RUN})'),

    # "after X" / grammatical context — "(after 得/不)", "setelah 得"
    re.compile(rf'(?:after|nach|après|después|dopo|na|efter|setelah|pagkatapos|sau|後|بعد|के बाद|หลัง)\s+({_CJK_RUN})', re.IGNORECASE),
    re.compile(rf'({_CJK_RUN})/({_CJK_RUN})'),  # X/Y patterns like 得/不

    # "name X" patterns for personal/place names with CJK
    re.compile(rf'(?:الاسم|الشخصي|نام|नाम|ชื่อ|이름|名前|nome|nom|name|Name|naam|namn).*?({_CJK_RUN})', re.IGNORECASE),

    # "see X" / "lihat X" — Malay, Indonesian, and other languages
    # bkz/bakınız = Turkish abbreviation for "see"
    re.compile(rf'(?:lihat|siehe|voir|ver|vedere|se|zie|tingnan|xem|انظر|देखें|ดู|görünce|patrz|viz|lásd|a se vedea|vaata|βλέπε|bak\w*|bkz)\W*\s*({_CJK_RUN})', re.IGNORECASE),

    # CJK followed by Turkish apostrophe + suffix (e.g. 靠北'nın varyantı, 蓬蓽生輝'ye bakınız)
    re.compile(rf"({_CJK_RUN})(?:\[[\w]+\])?[''ʼ]\w+\s+(?:varyant\w*|bileşik\w*|bakınız|bak\w*)", re.IGNORECASE),
    # CJK + Turkish "used in compound" (霹靂 ... bileşik sözcüğünde kullanılır)
    re.compile(rf'({_CJK_RUN})(?:\s*\([^)]*\))?\s+bileşik\w*\s+\w+\s+kullanıl\w*', re.IGNORECASE),

    # CJK followed by "means/bedeutet/significa" — definition-style cross-ref
    # e.g. "澒洞 bedeutet weit", "瑽瑢 significa sonido"
    re.compile(rf'({_CJK_RUN})\s+(?:bedeutet|means|significa|signifie|означает|berarti|bermaksud|หมายถึง|anlamına|znamená|oznacza|jelent|înseamnă|tähendab|σημαίνει)', re.IGNORECASE),

    # "synonym of X" — Polish synonim, Greek συνώνυμο, Romanian sinonim, etc.
    re.compile(rf'(?:synonym\w*|synonim\w*|sinónim\w*|sinonim\w*|συνώνυμο\w*|синоним\w*|sünonüüm\w*)\s+(?:\w+\s+){{0,3}}({_CJK_RUN})', re.IGNORECASE),

    # "shape of X" — kształt (Polish), tvar (Czech), alak (Hungarian), etc.
    re.compile(rf'(?:kształt|tvar|shape|forme?|Gestalt|alak|biçim|tüüp)\s+({_CJK_RUN})', re.IGNORECASE),

    # CJK at start followed by descriptor (reverse word order: "埋 régi formája", "比 régi karaktere")
    re.compile(rf'({_CJK_RUN})\s+(?:régi|alte?|vieille?|antigua?|antiga?|vecchi[ao]|gamla|oude|lama|lumang|cũ|ancien|eski|stara|starý|vechi|vana)\s', re.IGNORECASE),
    re.compile(rf'({_CJK_RUN})\s+régi\s+\w+', re.IGNORECASE),

    # CJK at start followed by "used in" keyword (reverse word order in new langs)
    # e.g. "怨埋 kifejezésben használt", "怨埋 wyrażeniu używany"
    re.compile(rf'({_CJK_RUN})\s+\w+\s+(?:használt|używany|używane|používaný|kullanılan|utilizat|kasutatav|χρησιμοποιείται|gebruikt|utilisé|используется)', re.IGNORECASE),

    # CJK at start followed by "component/character/variant of it" in new langs
    # e.g. "字 karakterinin bileşeni" (Turkish), "字 karakterinin parçası"
    re.compile(rf'({_CJK_RUN})\s+\w+\s+(?:bileşeni|parçası|součástí|składnikiem|összetevője|componentă|komponendiks|στοιχείο)', re.IGNORECASE),
    re.compile(rf'({_CJK_RUN})\s+\w+(?:nin|nın|nun|nün|nin|inin|unun|ünün)\s+\w+', re.IGNORECASE),  # Turkish genitive

    # "используется в X" — allow preposition between keyword and CJK
    re.compile(rf'используется\s+(?:в|при|для)\s+({_CJK_RUN})'),
]

_CJK_RUN_RE = re.compile(_CJK_RUN)


# ---------------------------------------------------------------------------
# Latin-in-Arabic/Persian exemption
# ---------------------------------------------------------------------------

# Latin words that are acceptable in Arabic/Persian definitions:
# single letters, scientific binomials, proper names, universal units/acronyms

_LATIN_WORD_RE = re.compile(r'[a-zA-Z]+')

# Scientific binomial: Genus species (optionally with subspecies/authority)
_BINOMIAL_RE = re.compile(r'[A-Z][a-z]{2,}\s+[a-z]{2,}')

# Known universal acronyms/units that appear in all languages
_UNIVERSAL_ACRONYMS = {
    "DNA", "RNA", "USB", "LED", "GPS", "SMS", "TV", "CD", "DVD", "MP3",
    "WiFi", "HTTP", "HTTPS", "URL", "PDF", "API", "CPU", "GPU", "RAM",
    "SIM", "PIN", "ATM", "VPN", "HDMI", "JPEG", "PNG", "GIF", "IP",
    "mg", "kg", "km", "cm", "mm", "nm", "pm", "mL", "dL", "kL",
    "mA", "kW", "MW", "GW", "Hz", "kHz", "MHz", "GHz", "dB",
    "GB", "MB", "TB", "KB", "pH", "rpm",
}


def _latin_is_acceptable(definition: str) -> bool:
    """Return True if all Latin words in *definition* are acceptable.

    Acceptable = single letter, scientific name, proper name, or universal acronym.
    """
    latin_words = _LATIN_WORD_RE.findall(definition)
    if not latin_words:
        return True

    for word in latin_words:
        if len(word) == 1:
            continue
        if word in _UNIVERSAL_ACRONYMS or word.upper() in _UNIVERSAL_ACRONYMS:
            continue
        # General acronym: all-caps, 2-6 chars (AIA, OPEC, NATO, etc.)
        if word.isupper() and 2 <= len(word) <= 6:
            continue
        # Proper name: starts with capital, rest lowercase, length >= 2
        if word[0].isupper() and word[1:].islower() and len(word) >= 2:
            continue
        # Part of a scientific binomial (check in full definition context)
        if _BINOMIAL_RE.search(definition):
            if word[0].isupper() and word[1:].islower():
                continue
            if word.islower() and len(word) >= 2:
                continue
        return False

    return True


def _cjk_is_reference(definition: str) -> bool:
    """Return True if every CJK run in *definition* is part of a cross-reference."""
    cjk_runs = set(_CJK_RUN_RE.findall(definition))
    if not cjk_runs:
        return True

    referenced: set[str] = set()
    for pat in _REF_PATTERNS:
        for m in pat.finditer(definition):
            referenced.update(_CJK_RUN_RE.findall(m.group(0)))

    return cjk_runs <= referenced


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_definition(lang: str, definition: str) -> tuple[bool, set[str]]:
    """Check whether *definition* uses only valid scripts for *lang*.

    Returns (is_valid, invalid_scripts).

    CJK characters inside metalinguistic references ("variant of 迥")
    are exempted and do not count as contamination.
    """
    if not definition:
        return True, set()

    valid = VALID_SCRIPTS.get(lang)
    if valid is None:
        return True, set()

    detected = _detect_scripts(definition)
    invalid = detected - valid

    if not invalid:
        return True, set()

    # If the only invalid script is CJK, check whether it's a reference
    if invalid == {"cjk"} and _cjk_is_reference(definition):
        return True, set()

    # Latin in Arabic/Persian: allow single letters, scientific binomials,
    # proper names, and universally-used acronyms/units
    if invalid == {"latin"} and lang in ("ar", "fa"):
        if _latin_is_acceptable(definition):
            return True, set()

    return False, invalid


def validate_batch(
    lang_defs: dict[str, str],
) -> tuple[dict[str, str], dict[str, tuple[str, set[str]]]]:
    """Validate a {lang: definition} dict.  Split into clean and rejected.

    Returns:
        (clean, rejected)
        clean:    {lang: definition}  — definitions that passed validation
        rejected: {lang: (definition, invalid_scripts)} — those that failed
    """
    clean: dict[str, str] = {}
    rejected: dict[str, tuple[str, set[str]]] = {}
    for lang, defn in lang_defs.items():
        ok, bad = validate_definition(lang, defn)
        if ok:
            clean[lang] = defn
        else:
            rejected[lang] = (defn, bad)
    return clean, rejected
