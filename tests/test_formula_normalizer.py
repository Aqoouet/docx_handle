from __future__ import annotations

import tempfile
from pathlib import Path
from zipfile import ZipFile

from docx_handle.formula_normalizer import normalize_docx_math_cyrillic, normalize_formula_text


def test_normalize_formula_text_transliterates_cyrillic_macros() -> None:
    source = r"TH_{ \cyrr \cyre \cyrm \cyro \cyrn \cyrt .}=150 700"

    assert normalize_formula_text(source) == "TH_{remont.}=150 700"


def test_normalize_docx_math_cyrillic_only_touches_math_nodes() -> None:
    xml = (
        '<root xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
        'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:p><w:t>Привет мир</w:t></w:p>"
        "<m:oMath><m:r><m:t>TH_{ \\cyrr \\cyre \\cyrm \\cyro \\cyrn \\cyrt .}=150 700</m:t></m:r></m:oMath>"
        "</root>"
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        docx_path = Path(tmp_dir) / "sample.docx"
        with ZipFile(docx_path, "w") as archive:
            archive.writestr("word/document.xml", xml)
            archive.writestr("word/header1.xml", xml)

        replacements = normalize_docx_math_cyrillic(docx_path)

        assert replacements == 2
        with ZipFile(docx_path, "r") as archive:
            document_xml = archive.read("word/document.xml").decode("utf-8")
            header_xml = archive.read("word/header1.xml").decode("utf-8")

        assert "Привет мир" in document_xml
        assert "TH_{remont.}=150 700" in document_xml
        assert "\\cyrr" not in document_xml
        assert "TH_{remont.}=150 700" in header_xml
