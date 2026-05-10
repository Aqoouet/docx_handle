from __future__ import annotations

import tempfile
from pathlib import Path
from zipfile import ZipFile

from docx_handle.formula_normalizer import fix_docling_latex, normalize_docx_math_cyrillic, normalize_formula_text


def test_normalize_formula_text_transliterates_cyrillic_macros() -> None:
    source = r"TH_{ \cyrr \cyre \cyrm \cyro \cyrn \cyrt .}=150 700"

    assert normalize_formula_text(source) == "TH_{remont.}=150 700"


def test_fix_docling_latex_replaces_broken_macros() -> None:
    md = r"$N=10^{5} \text{ \texttimes } {\left(\frac{AFI}{S_{eq}}\right)}^{p}$"
    fixed = fix_docling_latex(md)
    assert r"\texttimes" not in fixed
    assert r"\times" in fixed
    assert r"\text{ \texttimes }" not in fixed

    md2 = r"$F_{1} \text{ \textellipsis } F_{7}$"
    fixed2 = fix_docling_latex(md2)
    assert r"\textellipsis" not in fixed2
    assert r"\ldots" in fixed2


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
