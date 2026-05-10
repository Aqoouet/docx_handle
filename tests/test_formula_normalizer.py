from __future__ import annotations

from postprocess.latex_fix import fix_docling_latex


def test_fix_docling_latex_replaces_broken_macros() -> None:
    md = r"$N=10^{5} \text{ \texttimes } {\left(\frac{AFI}{S_{eq}}\right)}^{p}$"
    fixed = fix_docling_latex(md)
    assert r"\texttimes" not in fixed
    assert r"\times" in fixed

    md2 = r"$F_{1} \text{ \textellipsis } F_{7}$"
    fixed2 = fix_docling_latex(md2)
    assert r"\textellipsis" not in fixed2
    assert r"\ldots" in fixed2


def test_fix_docling_latex_converts_cyr_macros_to_text() -> None:
    md = r"$KDF=\frac{TH_{ \cyrr \cyre \cyrm \cyro \cyrn \cyrt .}}{TH_{ \cyri \cyrs \cyrh \cyro \cyrd \cyrn .}},$"
    fixed = fix_docling_latex(md)
    assert r"\cyrr" not in fixed
    assert r"\text{ремонт}" in fixed
    assert r"\text{исходн}" in fixed
