from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from src.vendor_assurance.chunker import chunk_document
from src.vendor_assurance.evaluator import Evaluation, Finding, evaluate_document
from src.vendor_assurance.report_writer import render_report, write_report

TEMPLATE = Path("src/vendor_assurance/templates/privacy_review_template.md")
SAMPLE = Path("src/vendor_assurance/samples/synthetic_soc2_report.md")


def _evaluation() -> Evaluation:
    """Evaluate the sample at the fixed workshop date."""
    text = SAMPLE.read_text(encoding="utf-8")
    return evaluate_document(chunk_document(text, max_tokens=220, overlap_tokens=30), today=date(2026, 10, 26))


def test_writes_into_a_directory_that_does_not_exist_yet(tmp_path: Path) -> None:
    """An automation runs in a fresh clone, where the output directory is absent."""
    output = write_report(
        _evaluation(),
        TEMPLATE,
        tmp_path / "reports",
        review_date=date(2026, 10, 26),
    )

    assert output.exists()
    assert output.name.endswith("_2026_10_26.md")
    assert output.parent.name == "reports"


def test_unfilled_placeholder_is_rejected() -> None:
    with pytest.raises(ValueError, match="MISSING"):
        render_report(_evaluation(), "Vendor {{VENDOR}} and {{MISSING}}")


def test_table_escapes_multiline_evidence() -> None:
    """Source text cannot create new table columns, rows, or HTML elements."""
    quote = "A | B\n<script>"
    finding = Finding("Control", "Unclear", quote, "Needs review.")
    rendered = render_report(replace(_evaluation(), findings=[finding]), "{{FINDINGS}}")

    assert len(rendered.splitlines()) == 1
    assert rendered.count("|") == 5
    assert "A &#124; B<br>&lt;script&gt;" in rendered
    assert finding.evidence == quote


def test_source_placeholders_are_not_template_code() -> None:
    """Braces in a document are data, not additional substitutions."""
    evaluation = replace(_evaluation(), vendor="Synthetic {{SCORE}}")

    assert render_report(evaluation, "{{VENDOR}}") == "Synthetic {{SCORE}}"


def test_metadata_cannot_break_report_table_structure() -> None:
    """A system name is data even when it contains table or HTML punctuation."""
    evaluation = replace(_evaluation(), system="Synthetic | Portal\n<script>")

    rendered = render_report(evaluation, "| System | {{SYSTEM}} |")

    assert rendered == "| System | Synthetic &#124; Portal<br>&lt;script&gt; |"
    assert evaluation.system == "Synthetic | Portal\n<script>"
