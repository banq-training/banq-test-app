"""Bring the latest workshop fixes from the template into your own repository.

Usage (from the repository root, in your Codespace):

    python3 scripts/update_from_template.py

It downloads the template's newest version and copies only the workshop's own files: the
daily guides, prepared skills, helper scripts, workflow starters and ticket templates. A workshop
file the template has since deleted is removed too, but only one that came with the copy. It never
touches your website (site/), config.json, your own agents, skills or instructions, your
workflows, or your tests. Nothing is committed or pushed: review the changes in Source Control,
then commit and push them yourself, through a pull request from Day 4 on.
"""

import argparse
import subprocess
import sys
from pathlib import Path

TEMPLATE_URL = "https://github.com/agentic-dev-labs/copilot-hackathon-template.git"

# The template's own files. Attendees never edit these, so taking the newest copy is safe.
WORKSHOP_PATHS = (
    "README.md",
    "docs",
    "scripts",
    "checks/README.md",
    "checks/website.py",
    ".github/ISSUE_TEMPLATE",
    ".github/workflow-starters",
    ".github/skills/add-chart",
    ".github/skills/add-chat",
    ".github/skills/create-website",
    ".github/skills/publish-website",
    ".github/skills/start-website",
    ".github/skills/stop-website",
)


class UpdateError(Exception):
    """A plain-language reason the update stopped before changing anything."""


def _git(repository: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run one git command in the repository and return its result."""
    return subprocess.run(["git", *args], cwd=repository, capture_output=True, text=True, check=False)


def _workshop_files(repository: Path, tree: str) -> set[str]:
    """List the workshop files in one commit or fetched tree."""
    listed = _git(repository, "ls-tree", "-r", "--name-only", tree, "--", *WORKSHOP_PATHS)
    return set(listed.stdout.splitlines())


def update(repository: Path, source: str = TEMPLATE_URL, branch: str = "main") -> list[str]:
    """Copy the template's newest workshop files into the repository; return what changed."""
    edited = _git(repository, "diff", "--name-only", "HEAD", "--", *WORKSHOP_PATHS)
    if edited.returncode != 0:
        raise UpdateError(f"Git could not read this repository: {edited.stderr.strip()}")
    if edited.stdout.strip():
        raise UpdateError(
            "These workshop files have changes that are not committed yet, so nothing was "
            "updated:\n  " + "\n  ".join(edited.stdout.split())
            + "\nCommit them, or undo them in Source Control, then run this again."
        )

    fetched = _git(repository, "fetch", "--quiet", "--no-tags", "--depth", "1", source, branch)
    if fetched.returncode != 0:
        raise UpdateError(f"Could not download the template: {fetched.stderr.strip()}")

    present = [path for path in WORKSHOP_PATHS
               if _git(repository, "cat-file", "-e", f"FETCH_HEAD:{path}").returncode == 0]
    if present:
        copied = _git(repository, "checkout", "FETCH_HEAD", "--", *present)
        if copied.returncode != 0:
            raise UpdateError(f"Could not copy the new files: {copied.stderr.strip()}")
        # checkout stages the files; unstage them so the attendee reviews and commits as usual.
        _git(repository, "reset", "--quiet", "--", *present)

    # Files the copy started with (its first commit) that the template no longer has. Files the
    # attendee added later were never in that first commit, so they are never removed.
    shipped: set[str] = set()
    for first in _git(repository, "rev-list", "--max-parents=0", "HEAD").stdout.split():
        shipped |= _workshop_files(repository, first)
    retired = sorted(path for path in shipped - _workshop_files(repository, "FETCH_HEAD")
                     if (repository / path).is_file())
    if retired:
        removed = _git(repository, "rm", "--quiet", "--", *retired)
        if removed.returncode != 0:
            raise UpdateError(f"Could not remove the old files: {removed.stderr.strip()}")
        _git(repository, "reset", "--quiet", "--", *retired)

    if not present and not retired:
        return []
    status = _git(repository, "status", "--porcelain", "--untracked-files=all", "--", *present, *retired)
    return [line[3:] for line in status.stdout.splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    """Run the update and explain the next step in plain words."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", default=TEMPLATE_URL, help="template repository to copy from")
    arguments = parser.parse_args(argv)

    repository = Path.cwd()
    try:
        changed = update(repository, arguments.source)
    except UpdateError as error:
        print(error, file=sys.stderr)
        return 1

    if not changed:
        print("Already up to date: you have the template's newest workshop files.")
        return 0
    print(f"Updated {len(changed)} workshop file(s) from the template:")
    for path in changed:
        print(f"  {path}" if (repository / path).exists() else f"  {path} (removed: the template no longer has it)")
    print("Your website, config.json, agents, skills, instructions, workflows and tests are unchanged.")
    print("Next: review them in Source Control, then commit with the message")
    print("'Fetch workshop updates' and push. From Day 4 on, do it on a new branch")
    print("and merge it with a pull request.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
