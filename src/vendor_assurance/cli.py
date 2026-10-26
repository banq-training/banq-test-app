"""Command-line entry point for the synthetic assurance workflow."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from .chunker import chunk_document
from .evaluator import evaluate_document
from .report_writer import write_report


def main() -> None:
    """Chunk, evaluate, and render a source report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--output-directory", type=Path, default=Path("."))
    parser.add_argument("--max-tokens", type=int, default=220)
    parser.add_argument("--overlap-tokens", type=int, default=30)
    parser.add_argument("--as-of", type=date.fromisoformat, help="Review date (YYYY-MM-DD); defaults to today")
    args = parser.parse_args()

    if args.report.suffix.lower() not in {".md", ".txt"}:
        parser.error("Use a UTF-8 .md or .txt report; convert PDF or Office files before evaluation")
    try:
        text = args.report.read_text(encoding="utf-8")
        chunks = chunk_document(text, args.max_tokens, args.overlap_tokens)
        evaluation = evaluate_document(chunks, today=args.as_of)
        template = Path(__file__).parent / "templates" / "privacy_review_template.md"
        output = write_report(evaluation, template, args.output_directory, review_date=args.as_of)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(evaluation.to_json())
    print(f"Wrote {output}", file=sys.stderr)


if __name__ == "__main__":
    main()
