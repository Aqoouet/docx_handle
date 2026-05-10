"""Post-processing of Docling-generated LaTeX/Markdown output.

This module is intended to be used in the report_checking pipeline, not in the
docx_handle service itself.  It will eventually move to that repo.
"""
from __future__ import annotations

import re

_DOCLING_BROKEN_MACROS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\\text\{\s*\\texttimes\s*\}"), r"\\times"),
    (re.compile(r"\\text\{\s*\\textellipsis\s*\}"), r"\\ldots"),
]

# \cyrX macro name → Cyrillic Unicode character
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
_CYR_RUN_RE = re.compile(r"(?:\\(?:" + _CYR_MACRO_NAMES + r")\s*)+")
_CYR_SINGLE_RE = re.compile(r"\\(" + _CYR_MACRO_NAMES + r")\s*")


def fix_docling_latex(md: str) -> str:
    """Fix broken LaTeX macros in Docling markdown output.

    - Replaces \\text{\\texttimes} → \\times and similar broken escapes.
    - Converts runs of \\cyrX macros back to \\text{Cyrillic unicode}.
    """
    for pattern, replacement in _DOCLING_BROKEN_MACROS:
        md = pattern.sub(replacement, md)
    md = _CYR_RUN_RE.sub(_cyr_run_to_text, md)
    return md


def _cyr_run_to_text(match: re.Match[str]) -> str:
    chars = "".join(
        _CYRILLIC_MACRO_TO_UNICODE.get(m.group(1), m.group(1))
        for m in _CYR_SINGLE_RE.finditer(match.group(0))
    )
    return r"\text{" + chars + "}"
