"""Evaluate the synthetic sample reports and write the results into Dataverse."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import load  # noqa: E402
from src.vendor_assurance.chunker import chunk_document  # noqa: E402
from src.vendor_assurance.dataverse import DataverseClient, DataverseError  # noqa: E402
from src.vendor_assurance.evaluator import evaluate_document  # noqa: E402

PREFIX = os.environ.get("DATAVERSE_PREFIX", "cr522")
SAMPLES = ROOT / "src" / "vendor_assurance" / "samples"


def main() -> None:
    """Upsert this attendee's samples, preserving rows created during the lab."""
    attendee = load()["displayName"]
    client = DataverseClient.from_environment(allow_cli=False)
    escaped = attendee.replace("'", "''")
    existing = client.rows(
        f"{PREFIX}_vendorreviews",
        **{"$select": f"{PREFIX}_vendorreviewid,{PREFIX}_vendor", "$filter": f"{PREFIX}_attendee eq '{escaped}'"},
    )
    by_vendor = {row[f"{PREFIX}_vendor"]: row[f"{PREFIX}_vendorreviewid"] for row in existing}

    for sample in sorted(SAMPLES.glob("*.md")):
        evaluation = evaluate_document(chunk_document(sample.read_text(encoding="utf-8"), 220, 30))
        record = {
            f"{PREFIX}_vendor": evaluation.vendor,
            f"{PREFIX}_system": evaluation.system,
            f"{PREFIX}_datatypes": ", ".join(evaluation.data_types),
            f"{PREFIX}_hostingregion": evaluation.hosting_region,
            f"{PREFIX}_dataresidency": evaluation.data_residency,
            f"{PREFIX}_subprocessors": ", ".join(evaluation.subprocessors),
            f"{PREFIX}_soc2type": evaluation.soc2_type,
            f"{PREFIX}_reportdate": evaluation.report_date,
            f"{PREFIX}_score": evaluation.score,
            f"{PREFIX}_sensitivity": evaluation.sensitivity,
            f"{PREFIX}_gaps": "\n".join(evaluation.gaps) or "No gaps identified.",
            f"{PREFIX}_attendee": attendee,
        }
        record_id = by_vendor.get(evaluation.vendor)
        method = "PATCH" if record_id else "POST"
        path = f"{PREFIX}_vendorreviews({record_id})" if record_id else f"{PREFIX}_vendorreviews"
        client.request(method, path, record)
        print(f"{evaluation.vendor}: {method} ok, score={evaluation.score}")

    rows = client.rows(
        f"{PREFIX}_vendorreviews",
        **{
            "$select": f"{PREFIX}_vendor,{PREFIX}_score,{PREFIX}_sensitivity",
            "$filter": f"{PREFIX}_attendee eq '{escaped}'",
        },
    )
    print(f"\nRows in Dataverse for {attendee}:")
    for row in rows:
        score = row.get(f"{PREFIX}_score")
        display_score = "Not assessed" if score is None else f"{score}/10"
        sensitivity = row.get(f"{PREFIX}_sensitivity") or "Not assessed"
        print(f"  {row[f'{PREFIX}_vendor']:<32} {display_score}  {sensitivity}")


if __name__ == "__main__":
    try:
        main()
    except (DataverseError, OSError, ValueError) as error:
        sys.exit(str(error))
