"""Maintain explicit live evidence separately from deterministic test results."""

import argparse
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path(__file__).with_name("labs.json")
STATUSES = ("pending", "passed", "failed", "blocked")


def now() -> str:
    """Use UTC timestamps for resumable rehearsal records."""
    return datetime.now(UTC).isoformat()


def manifest() -> list[dict]:
    """Load core conditions and separately labelled optional extensions in workshop order."""
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["labs"]


def git_state() -> dict[str, object]:
    """Identify the tested revision without recording credential-bearing remotes."""
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()
    return {"commit": commit, "dirty": bool(dirty)}


def initialize(repository: str) -> dict:
    """Create a fresh ledger; no live condition starts in the passed state."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Use an OWNER/REPO repository name")
    return {
        "schema_version": 1, "repository": repository, "started_at": now(),
        "initial_revision": git_state(),
        "labs": {
            lab["id"]: {
                key: {"status": "pending", "evidence": [], "note": ""}
                for key in lab["checks"] | lab.get("optional_checks", {})
            } for lab in manifest()
        },
    }


def validate_reference(reference: str, root: Path = ROOT) -> None:
    """Accept existing workspace evidence or credential-free, stable HTTPS links."""
    link = urlsplit(reference)
    if link.scheme:
        if (link.scheme != "https" or not link.hostname or link.username
                or link.password or link.query):
            raise ValueError("Use a stable HTTPS evidence URL without credentials or query tokens")
        return
    path = (root / reference).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("Evidence must be an existing file inside this workspace")
    if any(part.startswith(".env") or part in {".facilitator", ".git"}
           for part in path.relative_to(root.resolve()).parts):
        raise ValueError("Private files and credential/config stores are not rehearsal evidence")


def record(
    ledger: dict, lab_id: str, check: str, status: str, evidence: list[str],
    note: str, *, observed: bool = False,
) -> None:
    """Require an explicit observation and a source for every passing condition."""
    expected = next((lab for lab in manifest() if lab["id"] == lab_id), None)
    if expected is None or check not in expected["checks"] | expected.get("optional_checks", {}):
        raise ValueError("Unknown lab or finish condition; use summary to see core and optional checks")
    if status not in STATUSES or not note.strip():
        raise ValueError("Supply a valid status and a short expected-versus-observed note")
    if status == "passed" and (not observed or not evidence):
        raise ValueError("Passing requires --observed and at least one evidence reference")
    for reference in evidence:
        validate_reference(reference)
    ledger.setdefault("labs", {}).setdefault(lab_id, {})[check] = {
        "status": status, "evidence": evidence, "note": note,
        "recorded_at": now(), "revision": git_state(),
        "observation_attested": observed,
    }


def check_status(ledger: dict, lab_id: str, key: str) -> str:
    """Apply the same evidence requirement to both core and optional observations."""
    entry = ledger.get("labs", {}).get(lab_id, {}).get(key, {})
    status = entry.get("status", "pending")
    if status not in STATUSES or (
        status == "passed" and not (entry.get("evidence") and entry.get("observation_attested"))
    ):
        return "pending"
    return status


def lab_status(ledger: dict, lab: dict) -> str:
    """Only manifest-defined core checks gate completion; missing entries stay pending."""
    statuses = [check_status(ledger, lab["id"], key) for key in lab["checks"]]
    for status in ("failed", "blocked", "pending"):
        if status in statuses:
            return status
    return "passed" if statuses and all(status == "passed" for status in statuses) else "pending"


def render_summary(ledger: dict) -> str:
    """Include outstanding conditions instead of silently dropping blocked labs."""
    lines = [
        "# Workshop Rehearsal Evidence", "", f"Repository: {ledger['repository']}", "",
        "Live statuses are recorded observations, not independent proof supplied by this script.",
        "Deterministic test results do not automatically pass any live condition.", "",
        "| Lab / Session | Status | Required Evidence Still Outstanding |", "|---|---|---|",
    ]
    for lab in manifest():
        missing = [key for key in lab["checks"] if check_status(ledger, lab["id"], key) != "passed"]
        lines.append(f"| {lab['id']}: {lab['title']} | {lab_status(ledger, lab)} | {', '.join(missing) or 'None'} |")
    lines.extend([
        "", "## Optional Extensions", "",
        "These observations never substitute for core checks or block core completion.",
        "Pending means not observed, not a pass or an installation claim.", "",
        "| Lab or Session / Check | Status |", "|---|---|",
    ])
    for lab in manifest():
        for key in lab.get("optional_checks", {}):
            lines.append(f"| {lab['id']} / {key} | {check_status(ledger, lab['id'], key)} |")
    return "\n".join(lines) + "\n"


def run_checks(lab_id: str | None, output: Path) -> int:
    """Run actual checks and record their exits without promoting live statuses."""
    tests = []
    if lab_id:
        lab = next((lab for lab in manifest() if lab["id"] == lab_id), None)
        if lab is None:
            raise ValueError("Unknown lab")
        tests = lab["tests"]
    commands = [
        ["uv", "run", "--no-sync", "pytest", *tests, "-q"],
        ["uv", "run", "--no-sync", "ruff", "check", "."],
    ]
    results = []
    revision = git_state()
    for command in commands:
        print("Running: " + " ".join(command), flush=True)
        try:
            process = subprocess.run(command, cwd=ROOT, timeout=600)
            code = process.returncode
        except (OSError, subprocess.TimeoutExpired):
            code = 1
        results.append({"command": command, "exit_code": code, "checked_at": now()})
    output.mkdir(parents=True, exist_ok=True)
    suffix = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    target = output / f"checks-{lab_id or 'all'}-{suffix}.json"
    target.write_text(json.dumps({
        "revision": revision, "checks": results,
        "note": "Code checks only; live lab statuses are unchanged.",
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Check results: {target}")
    return int(any(result["exit_code"] for result in results))


def main() -> int:
    """Create, update, resume, or summarize one explicit rehearsal run."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="This run's directory under rehearsal/results")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("init")
    create.add_argument("--repository", required=True)
    add = commands.add_parser("record")
    add.add_argument("--lab", required=True, help="Manifest lab or session ID, including day-2")
    add.add_argument("--check", required=True)
    add.add_argument("--status", choices=STATUSES, required=True)
    add.add_argument("--evidence", action="append", default=[])
    add.add_argument("--note", required=True)
    add.add_argument("--observed", action="store_true")
    summary = commands.add_parser("summary")
    summary.add_argument("--require-complete", action="store_true")
    checks = commands.add_parser("checks")
    checks.add_argument("--lab")
    arguments = parser.parse_args()
    if not arguments.output.resolve().is_relative_to((ROOT / "rehearsal/results").resolve()):
        parser.error("Keep rehearsal output under rehearsal/results (ignored by Git and Docker)")
    ledger_path = arguments.output / "ledger.json"
    try:
        if arguments.command == "checks":
            return run_checks(arguments.lab, arguments.output)
        if arguments.command == "init":
            ledger = initialize(arguments.repository)
            arguments.output.mkdir(parents=True, exist_ok=True)
            with ledger_path.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps(ledger, indent=2) + "\n")
        else:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        if arguments.command == "record":
            record(ledger, arguments.lab, arguments.check, arguments.status,
                   arguments.evidence, arguments.note, observed=arguments.observed)
            ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
        summary_text = render_summary(ledger)
        (arguments.output / "SUMMARY.md").write_text(summary_text, encoding="utf-8")
        print(summary_text)
        incomplete = any(lab_status(ledger, lab) != "passed" for lab in manifest())
        return int(arguments.command == "summary" and arguments.require_complete and incomplete)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())