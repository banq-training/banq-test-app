"""Dispatch the prepared Actions deployment and verify its exact run and endpoint."""

import argparse
import json
import os
import re
import subprocess
import tempfile
import uuid
from pathlib import Path
from urllib.parse import quote, urlsplit

from app.config import deployment_name, load
from app.site import site_manifest
from rehearsal.evidence import ROOT, git_state, now
from scripts.deployment_result import validate_origin, verify

RUN_FIELDS = "databaseId,attempt,displayTitle,headSha,headBranch,event,status,conclusion,url"


def invoke(command: list[str], *, timeout: int = 60) -> str:
    """Call Git/GitHub only, keeping raw authenticated-process errors out of evidence."""
    if command[0] not in {"git", "gh"}:
        raise ValueError("Rehearsal deployment may invoke only Git and GitHub CLI")
    try:
        result = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, env={**os.environ, "GH_PROMPT_DISABLED": "1"},
        )
    except FileNotFoundError:
        raise ValueError(f"{command[0]} is missing from the Codespace") from None
    except subprocess.TimeoutExpired:
        raise ValueError("GitHub operation timed out; inspect the existing run before retrying") from None
    if result.returncode:
        raise ValueError(
            f"{' '.join(command[:3])} failed (exit {result.returncode}). "
            "Check GitHub access or the named workflow run; do not sign into Azure."
        )
    return result.stdout.strip()


def repository_name(value: str) -> str:
    """Restrict repository identifiers to GitHub's ordinary OWNER/REPO form."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        raise ValueError("Specify the confirmed rehearsal repository as OWNER/REPO")
    return value


def dispatch(
    repository: str, ref: str, target: Path, *, dataverse: bool, approved: bool,
    deployment_target: str = "vendor",
) -> dict:
    """Refuse the source template, dirty work, unpushed commits, or unapproved cost."""
    repository_name(repository)
    if not approved:
        raise ValueError("Confirm the target and deployment usage, then supply --approve-deploy")
    if deployment_target not in {"website", "vendor"} or (deployment_target == "website" and dataverse):
        raise ValueError("Choose website without Dataverse, or the separate vendor target")
    if target.exists():
        raise ValueError("This request already exists. Collect it instead of dispatching a duplicate")
    if not ref or ref.startswith("-") or any(ord(character) < 32 for character in ref):
        raise ValueError("Specify the current pushed branch")
    current = json.loads(invoke(["gh", "repo", "view", "--json", "nameWithOwner"]))
    if current["nameWithOwner"].lower() != repository.lower():
        raise ValueError("The current repository differs from the approved deployment repository")
    metadata = json.loads(invoke([
        "gh", "repo", "view", repository, "--json", "nameWithOwner,isTemplate,visibility,viewerPermission",
    ]))
    if metadata["isTemplate"] or repository.lower() == "agentic-dev-labs/copilot-hackathon-template":
        raise ValueError("Use a dedicated rehearsal copy, not the source template")
    if metadata["visibility"] not in {"PRIVATE", "INTERNAL"}:
        raise ValueError("The complete rehearsal requires a private/internal repository for automations")
    if metadata["viewerPermission"] not in {"WRITE", "MAINTAIN", "ADMIN"}:
        raise ValueError("Repository write access is required; have the owner configure access")
    revision = git_state()
    if revision["dirty"]:
        raise ValueError("Review, commit, and push intended changes before deploying; the worktree is dirty")
    branch = invoke(["git", "branch", "--show-current"])
    if branch != ref:
        raise ValueError("The requested ref is not the checked-out branch that was tested")
    remote = json.loads(invoke(["gh", "api", f"repos/{repository}/commits/{quote(ref, safe='')}"]))
    if remote["sha"] != revision["commit"]:
        raise ValueError("The remote branch does not match the tested local commit; review and push first")
    settings = load()
    if not settings["displayName"].startswith("Synthetic Rehearsal "):
        raise ValueError("Use a unique label starting 'Synthetic Rehearsal ' to avoid attendee app collisions")
    correlation = uuid.uuid4().hex
    request = {
        "schema_version": 1, "repository": repository, "ref": ref, "commit": revision["commit"],
        "display_name": settings["displayName"],
        "app_name": deployment_name(settings["displayName"], deployment_target),
        "target": deployment_target,
        "connect_dataverse": dataverse, "rehearsal_id": correlation,
        "run_title": f"Deploy my app [{correlation}]", "requested_at": now(),
        "dispatch_state": "attempted",
    }
    if deployment_target == "website":
        request["expected_site"] = site_manifest()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(request, indent=2) + "\n")
    invoke([
        "gh", "workflow", "run", "deploy.yml", "--repo", repository, "--ref", ref,
        "-f", f"target={deployment_target}",
        "-f", f"connect_dataverse={str(dataverse).lower()}",
        "-f", f"rehearsal_id={correlation}", "-f", f"expected_sha={revision['commit']}",
    ])
    request["dispatch_state"] = "accepted"
    target.write_text(json.dumps(request, indent=2) + "\n", encoding="utf-8")
    return request


def select_run(runs: list[dict], request: dict) -> dict | None:
    """Match a unique dispatch, not the most recent unrelated deployment."""
    matches = [run for run in runs if (
        run.get("displayTitle") == request["run_title"]
        and run.get("headSha") == request["commit"]
        and run.get("headBranch") == request["ref"]
        and run.get("event") == "workflow_dispatch"
    )]
    if len(matches) > 1:
        raise ValueError("Multiple runs share this request ID; inspect them rather than guessing")
    return matches[0] if matches else None


def validate_result(result: dict, request: dict, run: dict) -> None:
    """Validate downloaded provenance before contacting the claimed endpoint."""
    expected = {
        "schema_version": 1, "repository": request["repository"], "commit": request["commit"],
        "display_name": request["display_name"], "app_name": request["app_name"],
        "connect_dataverse": request["connect_dataverse"], "run_id": str(run["databaseId"]),
        "run_attempt": str(run["attempt"]), "source": "website" if request.get("target") == "website"
        else "Dataverse" if request["connect_dataverse"] else "samples",
        "health_status": 200, "page_status": 200,
        "run_url": f"https://github.com/{request['repository']}/actions/runs/{run['databaseId']}",
    }
    if type(result.get("connect_dataverse")) is not bool:
        raise ValueError("Deployment result must state its data source as a boolean")
    if result.get("target", "vendor") != request.get("target", "vendor"):
        raise ValueError("Deployment result has the wrong website/vendor target")
    if request.get("target") == "website":
        if request["connect_dataverse"]:
            raise ValueError("A website request cannot enable Dataverse")
        expected["site_digest"] = request["expected_site"]["digest"]
        expected["index_sha256"] = request["expected_site"]["index_sha256"]
    if any(result.get(key) != value for key, value in expected.items()):
        raise ValueError("Downloaded deployment evidence does not match the requested run and commit")
    origin = validate_origin(result.get("url", ""))
    if urlsplit(origin).hostname.split(".", 1)[0] != request["app_name"]:
        raise ValueError("The endpoint hostname does not match the approved application name")


def collect(request_path: Path, *, wait: bool) -> int:
    """Download one named artifact and repeat endpoint checks without Azure access."""
    request = json.loads(request_path.read_text(encoding="utf-8"))
    repository = repository_name(request["repository"])
    if not re.fullmatch(r"[a-f0-9]{32}", request["rehearsal_id"]):
        raise ValueError("Invalid dispatch correlation ID")
    if (request["run_title"] != f"Deploy my app [{request['rehearsal_id']}]"
            or not re.fullmatch(r"[a-f0-9]{40}", request["commit"])):
        raise ValueError("Invalid dispatch title or commit")
    runs = json.loads(invoke([
        "gh", "run", "list", "--repo", repository, "--workflow", "deploy.yml",
        "--branch", request["ref"], "--commit", request["commit"], "--event", "workflow_dispatch",
        "--limit", "20", "--json", RUN_FIELDS,
    ]))
    run = select_run(runs, request)
    if run is None:
        print("No matching run is visible yet. Keep this request and collect again after GitHub creates the run.")
        return 2
    run_id = str(run["databaseId"])
    if not run_id.isdigit():
        raise ValueError("Invalid GitHub run ID")
    run_url = f"https://github.com/{repository}/actions/runs/{run_id}"
    print(run_url, flush=True)
    if run["status"] != "completed" and wait:
        print("Waiting for this specific run through GitHub CLI; no new deployment is dispatched.", flush=True)
        invoke(["gh", "run", "watch", run_id, "--repo", repository, "--exit-status"], timeout=2100)
        run = json.loads(invoke(["gh", "run", "view", run_id, "--repo", repository, "--json", RUN_FIELDS]))
        if select_run([run], request) is None:
            raise ValueError("The watched run no longer matches this request")
    if run["status"] != "completed":
        print("Deployment is pending. Collect when complete, or use --wait with supported GitHub authentication.")
        return 2
    if run["conclusion"] != "success":
        raise ValueError(f"Deployment did not succeed. Inspect {run_url}")
    artifact = f"deployment-result-{run_id}-{run['attempt']}"
    with tempfile.TemporaryDirectory(prefix="deployment-", dir=request_path.parent) as temporary:
        invoke(["gh", "run", "download", run_id, "--repo", repository,
                "--name", artifact, "--dir", temporary], timeout=120)
        result = json.loads((Path(temporary) / "deployment-result.json").read_text(encoding="utf-8"))
    validate_result(result, request, run)
    options = {}
    if request.get("target") == "website":
        options = {"target": "website", "expected_site": request["expected_site"]}
    current = verify(result["url"], label=request["display_name"], commit=request["commit"],
                     dataverse=request["connect_dataverse"], **options)
    destination = request_path.parent / f"{artifact}.json"
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (request_path.parent / f"endpoint-{run_id}-{run['attempt']}.json").write_text(
        json.dumps({**current, "run_url": run_url, "checked_from": "Codespaces" if
                    os.environ.get("CODESPACES") == "true" else "other environment"}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Verified application: {current['url']}\nCommit: {current['commit']}\nEvidence: {destination}")
    return 0


def main() -> int:
    """Expose two resumable steps so a lost session never causes a duplicate run."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("dispatch")
    start.add_argument("--repository", required=True)
    start.add_argument("--ref", required=True)
    start.add_argument("--request", type=Path, required=True)
    start.add_argument("--dataverse", action="store_true")
    start.add_argument("--target", choices=("website", "vendor"), default="vendor")
    start.add_argument("--approve-deploy", action="store_true")
    finish = commands.add_parser("collect")
    finish.add_argument("--request", type=Path, required=True)
    finish.add_argument("--wait", action="store_true")
    arguments = parser.parse_args()
    if not arguments.request.resolve().is_relative_to((ROOT / "rehearsal/results").resolve()):
        parser.error("Keep request files under rehearsal/results so they stay out of Git and images")
    try:
        if arguments.command == "collect":
            return collect(arguments.request, wait=arguments.wait)
        request = dispatch(arguments.repository, arguments.ref, arguments.request,
                           dataverse=arguments.dataverse, approved=arguments.approve_deploy,
                           deployment_target=arguments.target)
        print(f"Dispatch accepted for {request['commit']}; request saved to {arguments.request}.")
        print("Run the collect command for this request, with --wait if supported.")
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Rehearsal deployment stopped: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())