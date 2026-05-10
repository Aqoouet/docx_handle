from __future__ import annotations

import re
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

CYRILLIC_TRANSLITERATION = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "yo",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}
CYRILLIC_TRANSLITERATION.update(
    {
        "А": "A",
        "Б": "B",
        "В": "V",
        "Г": "G",
        "Д": "D",
        "Е": "E",
        "Ё": "Yo",
        "Ж": "Zh",
        "З": "Z",
        "И": "I",
        "Й": "Y",
        "К": "K",
        "Л": "L",
        "М": "M",
        "Н": "N",
        "О": "O",
        "П": "P",
        "Р": "R",
        "С": "S",
        "Т": "T",
        "У": "U",
        "Ф": "F",
        "Х": "Kh",
        "Ц": "Ts",
        "Ч": "Ch",
        "Ш": "Sh",
        "Щ": "Shch",
        "Ъ": "",
        "Ы": "Y",
        "Ь": "",
        "Э": "E",
        "Ю": "Yu",
        "Я": "Ya",
    }
)

CYRILLIC_MACRO_TRANSLITERATION = {
    "cyra": "a",
    "cyrb": "b",
    "cyrv": "v",
    "cyrg": "g",
    "cyrd": "d",
    "cyre": "e",
    "cyryo": "yo",
    "cyrzh": "zh",
    "cyrz": "z",
    "cyri": "i",
    "cyrishrt": "y",
    "cyrk": "k",
    "cyrl": "l",
    "cyrm": "m",
    "cyrn": "n",
    "cyro": "o",
    "cyrp": "p",
    "cyrr": "r",
    "cyrs": "s",
    "cyrt": "t",
    "cyru": "u",
    "cyrf": "f",
    "cyrkh": "kh",
    "cyrts": "ts",
    "cyrch": "ch",
    "cyrsh": "sh",
    "cyrshch": "shch",
    "cyrery": "y",
    "cyrsoftsign": "",
    "cyrhard": "",
    "cyrhrdsn": "",
    "cyrh": "kh",
    "cyrc": "ts",
    "cyryu": "yu",
    "cyrya": "ya",
}
CYRILLIC_MACRO_TRANSLITERATION.update({name.upper(): value.upper() for name, value in CYRILLIC_MACRO_TRANSLITERATION.items() if value})

_DOCLING_BROKEN_MACROS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\\text\{\s*\\texttimes\s*\}"), r"\\times"),
    (re.compile(r"\\text\{\s*\\textellipsis\s*\}"), r"\\ldots"),
]

# Reverse map: \cyrX macro name → actual Cyrillic Unicode character
_CYRILLIC_MACRO_TO_UNICODE: dict[str, str] = {
    "cyra": "а", "cyrb": "б", "cyrv": "в", "cyrg": "г", "cyrd": "д",
    "cyre": "е", "cyryo": "ё", "cyrzh": "ж", "cyrz": "з", "cyri": "и",
    "cyrishrt": "й", "cyrk": "к", "cyrl": "л", "cyrm": "м", "cyrn": "н",
    "cyro": "о", "cyrp": "п", "cyrr": "р", "cyrs": "с", "cyrt": "т",
    "cyru": "у", "cyrf": "ф", "cyrkh": "х", "cyrts": "ц", "cyrch": "ч",
    "cyrsh": "ш", "cyrshch": "щ", "cyrery": "ы", "cyrsoftsign": "ь",
    "cyrhrdsn": "ъ", "cyrhard": "ъ", "cyrh": "х", "cyrc": "ц",
    "cyryu": "ю", "cyrya": "я",
    "CYRA": "А", "CYRB": "Б", "CYRV": "В", "CYRG": "Г", "CYRD": "Д",
    "CYRE": "Е", "CYRYO": "Ё", "CYRZH": "Ж", "CYRZ": "З", "CYRI": "И",
    "CYRISHRT": "Й", "CYRK": "К", "CYRL": "Л", "CYRM": "М", "CYRN": "Н",
    "CYRO": "О", "CYRP": "П", "CYRR": "Р", "CYRS": "С", "CYRT": "Т",
    "CYRU": "У", "CYRF": "Ф", "CYRKH": "Х", "CYRTS": "Ц", "CYRCH": "Ч",
    "CYRSH": "Ш", "CYRSHCH": "Щ", "CYRERY": "Ы", "CYRSOFTSIGN": "Ь",
    "CYRHRDSN": "Ъ", "CYRHARD": "Ъ", "CYRH": "Х", "CYRC": "Ц",
    "CYRYU": "Ю", "CYRYA": "Я",
}

_CYR_MACRO_NAMES = "|".join(
    sorted(map(re.escape, _CYRILLIC_MACRO_TO_UNICODE), key=len, reverse=True)
)
# Matches one or more consecutive \cyrX tokens (with optional spaces between them)
_CYR_RUN_RE = re.compile(
    r"(?:\\(?:" + _CYR_MACRO_NAMES + r")\s*)+"
)

_CYRILLIC_MACRO_RE = re.compile(
    r"\\(?P<macro>"
    + "|".join(sorted(map(re.escape, CYRILLIC_MACRO_TRANSLITERATION.keys()), key=len, reverse=True))
    + r")"
)
_SPACED_ASCII_WORDS_RE = re.compile(r"(?<![A-Za-z])(?:[A-Za-z]+(?:\s+[A-Za-z]+)+)(?![A-Za-z])")
_SPACE_AFTER_OPEN_RE = re.compile(r"([({\[])\s+")
_SPACE_BEFORE_CLOSE_RE = re.compile(r"\s+([)}\]])")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([.,;:!?])")
_MATH_TEXT_RE = re.compile(r"(<m:t\b[^>]*>)(.*?)(</m:t>)", re.DOTALL)


def normalize_formula_text(text: str) -> str:
    """Normalize OMML text so Docling is less likely to emit broken LaTeX macros."""
    text = _CYRILLIC_MACRO_RE.sub(_replace_cyrillic_macro, text)
    text = "".join(CYRILLIC_TRANSLITERATION.get(char, char) for char in text)
    text = _SPACED_ASCII_WORDS_RE.sub(lambda match: match.group(0).replace(" ", ""), text)
    text = _SPACE_AFTER_OPEN_RE.sub(r"\1", text)
    text = _SPACE_BEFORE_CLOSE_RE.sub(r"\1", text)
    text = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", text)
    return text


def fix_docling_latex(md: str) -> str:
    """Replace broken LaTeX macros emitted by Docling for certain Unicode math chars."""
    for pattern, replacement in _DOCLING_BROKEN_MACROS:
        md = pattern.sub(replacement, md)
    md = _CYR_RUN_RE.sub(_cyr_run_to_text, md)
    return md


def _cyr_run_to_text(match: re.Match[str]) -> str:
    """Convert a run of \\cyrX macros to \\text{Cyrillic unicode}."""
    single = re.compile(r"\\(" + _CYR_MACRO_NAMES + r")\s*")
    chars = "".join(
        _CYRILLIC_MACRO_TO_UNICODE.get(m.group(1), m.group(1))
        for m in single.finditer(match.group(0))
    )
    return r"\text{" + chars + "}"


def normalize_docx_math_cyrillic(docx_path: Path) -> int:
    """Rewrite Cyrillic text in math runs inside *docx_path* in place.

    Returns the number of <m:t> nodes that were changed.
    """
    docx_path = Path(docx_path)
    replacements = 0
    with tempfile.NamedTemporaryFile(dir=str(docx_path.parent), suffix=".docx", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        with ZipFile(docx_path, "r") as source, ZipFile(tmp_path, "w", compression=ZIP_DEFLATED) as target:
            for item in source.infolist():
                data = source.read(item.filename)
                if item.filename.startswith("word/") and item.filename.endswith(".xml"):
                    text = data.decode("utf-8")
                    text, count = _rewrite_math_text_nodes(text)
                    replacements += count
                    if count:
                        data = text.encode("utf-8")
                target.writestr(item, data)
        tmp_path.replace(docx_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    return replacements


def _rewrite_math_text_nodes(xml_text: str) -> tuple[str, int]:
    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        prefix, inner, suffix = match.groups()
        normalized = normalize_formula_text(inner)
        if normalized != inner:
            count += 1
        return f"{prefix}{normalized}{suffix}"

    return _MATH_TEXT_RE.sub(repl, xml_text), count


def _replace_cyrillic_macro(match: re.Match[str]) -> str:
    macro = match.group("macro")
    return CYRILLIC_MACRO_TRANSLITERATION.get(macro, macro.replace("cyr", "").replace("CYR", ""))
