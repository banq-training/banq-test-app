"""Render a completed privacy review from an evaluation."""

from __future__ import annotations

import html
import re
from datetime import UTC, date, datetime
from pathlib import Path

from .evaluator import Evaluation

PLACEHOLDER = re.compile(r"\{\{[A-Z0-9_]+\}\}")


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")[:100] or "Vendor"


def _markdown_cell(value: str) -> str:
    """Encode a table cell without modifying the stored quotation."""
    escaped = html.escape(value, quote=False).replace("|", "&#124;")
    return escaped.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def render_report(evaluation: Evaluation, template: str) -> str:
    """Fill the report template and reject incomplete output."""
    rows = "\n".join(
        "| " + " | ".join(
            _markdown_cell(value)
            for value in (item.control, item.status, item.evidence, item.reasoning)
        ) + " |"
        for item in evaluation.findings
    )
    values = {
        "VENDOR": evaluation.vendor,
        "SYSTEM": evaluation.system,
        "DATA_TYPES": ", ".join(evaluation.data_types),
        "HOSTING_REGION": evaluation.hosting_region,
        "DATA_RESIDENCY": evaluation.data_residency,
        "SUBPROCESSORS": ", ".join(evaluation.subprocessors),
        "SOC2_TYPE": evaluation.soc2_type,
        "REPORT_DATE": evaluation.report_date,
        "SCORE": str(evaluation.score),
        "SENSITIVITY": evaluation.sensitivity,
        "FINDINGS": rows,
        "GAPS": "\n".join(f"- {_markdown_cell(gap)}" for gap in evaluation.gaps) or "- No gaps identified.",
    }
    rendered_values = {
        key: value if key in {"FINDINGS", "GAPS"} else _markdown_cell(value)
        for key, value in values.items()
    }
    unknown = {
        placeholder for placeholder in PLACEHOLDER.findall(template)
        if placeholder[2:-2] not in values
    }
    if unknown:
        raise ValueError(f"Unfilled template placeholders: {', '.join(sorted(unknown))}")
    return PLACEHOLDER.sub(lambda match: rendered_values[match.group()[2:-2]], template)


def write_report(
    evaluation: Evaluation,
    template_path: Path,
    output_directory: Path = Path("."),
    review_date: date | None = None,
) -> Path:
    """Write a dated report and return its path."""
    rendered = render_report(evaluation, template_path.read_text(encoding="utf-8"))
    stamp = (review_date or datetime.now(tz=UTC).date()).strftime("%Y_%m_%d")
    output_directory.mkdir(parents=True, exist_ok=True)
    output = output_directory / f"PrivacyReview_{_safe_name(evaluation.vendor)}_{stamp}.md"
    output.write_text(rendered, encoding="utf-8")
    return output
