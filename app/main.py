"""Minimal vendor review web app.

Reads vendor reviews from Dataverse when configured, and falls back to evaluating the
local synthetic samples so the app runs in a Codespace with no credentials at all.
"""

from __future__ import annotations

import html
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from app.config import load
from src.vendor_assurance.dataverse import DataverseClient, DataverseError

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "src" / "vendor_assurance" / "samples"

PREFIX = os.environ.get("DATAVERSE_PREFIX", "cr522")

app = FastAPI()


class FictionalVendor(BaseModel):
    """Accept bounded names only; the server owns the workshop label and assessment."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    vendor: str = Field(min_length=1, max_length=200, strict=True)
    system: str = Field(min_length=1, max_length=200, strict=True)


@app.post("/vendors", status_code=201)
def add_vendor(vendor: FictionalVendor) -> dict[str, str]:
    """Write a fictional unassessed row only in an explicitly enabled training preview."""
    if os.environ.get("WORKSHOP_ALLOW_WRITES") != "true" or not os.environ.get("DATAVERSE_URL"):
        raise HTTPException(status_code=403, detail="Training writes are not enabled. Ask a helper.")
    try:
        settings = load()
    except (OSError, ValueError) as error:
        raise HTTPException(status_code=400, detail="Training configuration needs a helper.") from error
    try:
        DataverseClient.from_environment().request("POST", f"{PREFIX}_vendorreviews", {
            f"{PREFIX}_vendor": vendor.vendor,
            f"{PREFIX}_system": vendor.system,
            f"{PREFIX}_attendee": settings["displayName"],
        })
    except (DataverseError, ValueError) as error:
        raise HTTPException(
            status_code=503, detail="Could not confirm the save. Ask a helper before retrying.",
        ) from error
    return {"status": "created", "assessment": "Not assessed"}


def _from_dataverse(attendee: str) -> list[dict]:
    """Load this attendee's display rows; the filter is not an access boundary."""
    escaped = attendee.replace("'", "''")
    rows = DataverseClient.from_environment().rows(
        f"{PREFIX}_vendorreviews",
        **{
            "$select": f"{PREFIX}_vendor,{PREFIX}_score,{PREFIX}_sensitivity,{PREFIX}_attendee",
            "$filter": f"{PREFIX}_attendee eq '{escaped}'",
        },
    )
    return [
        {
            "vendor": row.get(f"{PREFIX}_vendor", ""),
            "score": row.get(f"{PREFIX}_score"),
            "sensitivity": row.get(f"{PREFIX}_sensitivity", ""),
        }
        for row in rows
    ]


def _from_samples() -> list[dict]:
    """Evaluate the checked-in synthetic samples for the no-credentials path."""
    from src.vendor_assurance.chunker import chunk_document
    from src.vendor_assurance.evaluator import evaluate_document

    results = []
    for sample in sorted(SAMPLES.glob("*.md")):
        evaluation = evaluate_document(chunk_document(sample.read_text(encoding="utf-8"), 220, 30))
        results.append(
            {
                "vendor": evaluation.vendor,
                "score": evaluation.score,
                "sensitivity": evaluation.sensitivity,
            }
        )
    return results


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness probe for the container platform."""
    result = {"status": "ok"}
    if commit := os.environ.get("WORKSHOP_COMMIT"):
        result["commit"] = commit
    return result


@app.get("/", response_class=HTMLResponse)
def index(follow_up: bool = False) -> HTMLResponse:
    """Render the attendee's vendor review list."""
    try:
        settings = load()
    except (OSError, ValueError) as error:
        return HTMLResponse(
            f"<h1>Configuration needed</h1><p>{html.escape(str(error))}</p>", status_code=400,
        )
    if not os.environ.get("DATAVERSE_URL"):
        reviews = _from_samples()
        source = "local synthetic samples (Dataverse is not configured)"
    else:
        try:
            reviews = _from_dataverse(settings["displayName"])
            source = "Dataverse" if reviews else f"Dataverse - no rows tagged '{settings['displayName']}' yet"
        except (DataverseError, ValueError) as error:
            reviews = _from_samples()
            source = f"local synthetic samples (Dataverse unavailable: {error})"

    if follow_up:
        reviews = [item for item in reviews if type(item["score"]) is int and item["score"] < 5]

    rows = "\n".join(
        f"<tr><td>{html.escape(str(item['vendor']))}</td>"
        f"<td class='score'>{html.escape(str(item['score']) + '/10') if item['score'] is not None else 'Not assessed'}</td>"
        f"<td>{html.escape(str(item['sensitivity']))}</td></tr>"
        for item in reviews
    ) or "<tr><td colspan='3'>No reviews yet.</td></tr>"

    write_form = ""
    if os.environ.get("WORKSHOP_ALLOW_WRITES") == "true" and source.startswith("Dataverse"):
        write_form = """
 <h2>Add a fictional vendor</h2>
 <form id="vendor-form">
    <label for="vendor">Vendor</label>
    <input id="vendor" name="vendor" required maxlength="200" autocomplete="off">
    <label for="system">System</label>
    <input id="system" name="system" required maxlength="200" autocomplete="off">
    <button type="submit">Add fictional vendor</button>
    <p id="save-message" role="status" aria-live="polite"></p>
 </form>
 <script>
 const form = document.getElementById('vendor-form');
 form.addEventListener('submit', async (event) => {
     event.preventDefault();
     const button = form.querySelector('button');
     const message = document.getElementById('save-message');
     button.disabled = true;
     message.textContent = 'Saving...';
     try {
         const response = await fetch('/vendors', {
             method: 'POST', headers: {'Content-Type': 'application/json'},
             body: JSON.stringify({vendor: form.elements.vendor.value, system: form.elements.system.value})
         });
         if (!response.ok) {
             message.textContent = response.status === 422
                 ? 'Enter a vendor and system name, each between 1 and 200 characters.'
                 : 'Could not confirm the save. Ask a helper before retrying.';
             return;
         }
         window.location.assign('/');
     } catch {
         message.textContent = 'Could not confirm the save. Ask a helper before retrying.';
     } finally {
         button.disabled = false;
     }
 });
 </script>"""

    name = html.escape(settings["displayName"])
    checked = "checked" if follow_up else ""
    return HTMLResponse(f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} - Vendor Reviews</title>
<style>
 body {{ font-family: Segoe UI, system-ui, sans-serif; margin: 3rem auto; padding: 0 1rem; max-width: 46rem; overflow-wrap: anywhere; }}
 h1 {{ margin-bottom: 0.2rem; }}
 p.source {{ color: #555; margin-top: 0; }}
 table {{ border-collapse: collapse; width: 100%; margin-top: 1.5rem; }}
 th, td {{ border-bottom: 1px solid #ddd; padding: 0.6rem; text-align: left; }}
 th {{ white-space: nowrap; }}
 .score {{ font-variant-numeric: tabular-nums; }}
 form {{ margin-top: 1.5rem; }}
 #vendor-form label, #vendor-form input {{ display: block; }}
 #vendor-form input {{ box-sizing: border-box; width: 100%; margin: 0.25rem 0 0.75rem; padding: 0.5rem; }}
 button {{ padding: 0.5rem 0.75rem; }}
 footer {{ margin-top: 2rem; color: #777; font-size: 0.85rem; }}
</style>
</head>
<body>
 <h1>{name} - Vendor Reviews</h1>
 <p class="source">Source: {html.escape(source)}</p>
 <form method="get">
  <label><input type="checkbox" name="follow_up" value="true" {checked}> Assessed scores below 5</label>
  <button type="submit">Apply</button> <a href="/">Reset</a>
 </form>
 <p>Reviews shown: {len(reviews)}</p>
 <table>
  <thead><tr><th>Vendor</th><th>Score</th><th>Sensitivity</th></tr></thead>
  <tbody>{rows}</tbody>
 </table>
 {write_form}
 <footer>Synthetic training data only.</footer>
</body>
</html>""")
