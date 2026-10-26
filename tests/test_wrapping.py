"""A report must score the same however its lines happen to be wrapped."""

import textwrap
from pathlib import Path

import pytest

from src.vendor_assurance.chunker import chunk_document
from src.vendor_assurance.evaluator import evaluate_document

SAMPLES = Path("src/vendor_assurance/samples")


def _statuses(text: str) -> dict[str, str]:
    result = evaluate_document(chunk_document(text, max_tokens=220, overlap_tokens=30))
    return {finding.control: finding.status for finding in result.findings}


@pytest.mark.parametrize("sample", sorted(p.name for p in SAMPLES.glob("*.md")))
@pytest.mark.parametrize("width", [60, 80])
def test_line_wrapping_does_not_change_any_status(sample: str, width: int) -> None:
    original = (SAMPLES / sample).read_text(encoding="utf-8")
    wrapped = "\n".join(
        "\n".join(textwrap.wrap(line, width=width)) if line.strip() else line
        for line in original.splitlines()
    )

    assert _statuses(wrapped) == _statuses(original)
