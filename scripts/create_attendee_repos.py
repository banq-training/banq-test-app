"""Create attendee repositories from the template and grant the attendee team access.

The facilitator must configure organization secret access separately. Each repository needs
an explicit team grant when organization base permission is `none`.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys

ORG = "agentic-dev-labs"
TEMPLATE = f"{ORG}/copilot-hackathon-template"
TEAM = "hackathon-attendees"

GH = shutil.which("gh") or "gh"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a command and capture its output."""
    return subprocess.run(command, capture_output=True, text=True, check=False, timeout=120)


def validate_template(template: str) -> None:
    """Refuse a template whose root contains private preparation material."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9][A-Za-z0-9_.-]*", template):
        raise ValueError("Template must be an owner/repository name")
    result = run([GH, "api", f"repos/{template}/contents"])
    if result.returncode:
        raise ValueError("Cannot inspect the selected template; check GitHub access before copying it")
    entries = json.loads(result.stdout)
    if not isinstance(entries, list) or any(
        not isinstance(entry, dict) or not isinstance(entry.get("name"), str)
        for entry in entries
    ):
        raise ValueError("Template inspection did not return a directory listing")
    if any(
        entry["name"] in {".facilitator", "NN-NA-Hackathon-2026-10-Engagement-Brief.md"}
        or entry["name"].endswith(".private.md")
        for entry in entries
    ):
        raise ValueError(
            "Template contains private facilitator material. The owner must prepare an approved "
            "template excluding it; select that repository with --template owner/repository."
        )


def create_repo(name: str, *, template: str = TEMPLATE) -> bool:
    """Create one private repository from the template."""
    full = f"{ORG}/{name}"
    if run([GH, "repo", "view", full]).returncode == 0:
        print(f"{name}: already exists")
        return True
    result = run([GH, "repo", "create", full, "--template", template, "--private"])
    if result.returncode != 0:
        print(f"{name}: FAILED {result.stderr.strip()[:200]}")
        return False
    print(f"{name}: created")
    return True


def grant_team(name: str) -> bool:
    """Give the attendee team write access to the repository."""
    result = run([
        GH, "api", "-X", "PUT",
        f"/orgs/{ORG}/teams/{TEAM}/repos/{ORG}/{name}",
        "-f", "permission=push",
    ])
    print(f"  team access: {'ok' if result.returncode == 0 else result.stderr.strip()[:160]}")
    return result.returncode == 0


def main() -> int:
    """Create every requested repository and grant the attendee team access."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="+", help="repository names, for example nn-na-2026-10-team-01")
    parser.add_argument("--template", default=TEMPLATE, help="Owner-approved template without private notes")
    args = parser.parse_args()
    if any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name) for name in args.names):
        parser.error("Use repository names only, without an owner, path, or query string")
    try:
        validate_template(args.template)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Repository preparation stopped: {error}\n")

    failures = 0
    for name in args.names:
        if not create_repo(name, template=args.template) or not grant_team(name):
            failures += 1

    print("\nCheck Actions and Codespaces secret access separately for each repository.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
