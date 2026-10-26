"""Taking the template's newest workshop files never touches an attendee's own work."""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import update_from_template  # noqa: E402


def git(repository: Path, *args: str) -> str:
    """Run git with a fixed identity so commits work on any machine."""
    return subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
         "-c", "init.defaultBranch=main", "-c", "commit.gpgsign=false", *args],
        cwd=repository, capture_output=True, text=True, check=True,
    ).stdout


def make_repository(path: Path, files: dict[str, str]) -> Path:
    """Create a one-commit repository with the given files."""
    path.mkdir()
    git(path, "init", "--quiet")
    for name, text in files.items():
        (path / name).parent.mkdir(parents=True, exist_ok=True)
        (path / name).write_text(text, encoding="utf-8")
    git(path, "add", "--all")
    git(path, "commit", "--quiet", "-m", "start")
    return path


@pytest.fixture
def template(tmp_path: Path) -> Path:
    """A template whose guide was fixed after the attendee made a copy."""
    return make_repository(tmp_path / "template", {
        "README.md": "fixed guide\n",
        "docs/QUICK-REFERENCE.md": "new rescue prompts\n",
        ".github/skills/create-website/SKILL.md": "fixed skill\n",
        "site/README.md": "template site note\n",
        "config.json": '{"websiteName": ""}\n',
        ".github/agents/generic-agent.agent.md": "blank helper\n",
        ".github/workflows/publish-website.yml": "# version: off\n",
    })


@pytest.fixture
def attendee(tmp_path: Path) -> Path:
    """An attendee copy with unrelated history and their own work."""
    return make_repository(tmp_path / "attendee", {
        "README.md": "old guide\n",
        ".github/skills/create-website/SKILL.md": "old skill\n",
        "site/README.md": "template site note\n",
        "site/index.html": "<h1>My planner</h1>\n",
        "config.json": '{"websiteName": "alex"}\n',
        ".github/agents/joker.agent.md": "my joker\n",
        ".github/skills/user-stories/SKILL.md": "my skill\n",
        ".github/workflows/publish-website.yml": "version: on\n",
    })


def test_update_copies_workshop_files_and_keeps_attendee_work(template: Path, attendee: Path) -> None:
    """Guides and prepared skills update; the website, settings, agents and workflows stay."""
    changed = update_from_template.update(attendee, source=str(template))

    assert sorted(changed) == [".github/skills/create-website/SKILL.md", "README.md",
                               "docs/QUICK-REFERENCE.md"]
    assert (attendee / "README.md").read_text(encoding="utf-8") == "fixed guide\n"
    assert (attendee / "docs/QUICK-REFERENCE.md").read_text(encoding="utf-8") == "new rescue prompts\n"
    assert (attendee / "site/index.html").read_text(encoding="utf-8") == "<h1>My planner</h1>\n"
    assert '"alex"' in (attendee / "config.json").read_text(encoding="utf-8")
    assert (attendee / ".github/agents/joker.agent.md").is_file()
    assert not (attendee / ".github/agents/generic-agent.agent.md").exists()
    assert (attendee / ".github/skills/user-stories/SKILL.md").read_text(encoding="utf-8") == "my skill\n"
    assert (attendee / ".github/workflows/publish-website.yml").read_text(encoding="utf-8") == "version: on\n"
    assert git(attendee, "diff", "--cached", "--name-only") == "", "nothing is staged for them"
    assert git(attendee, "log", "--oneline").count("\n") == 1, "nothing is committed for them"


def test_update_twice_reports_nothing_new(template: Path, attendee: Path) -> None:
    """After committing the update, running it again changes nothing."""
    update_from_template.update(attendee, source=str(template))
    git(attendee, "add", "--all")
    git(attendee, "commit", "--quiet", "-m", "Get the latest workshop fixes")

    assert update_from_template.update(attendee, source=str(template)) == []


def test_uncommitted_workshop_edits_stop_the_update(template: Path, attendee: Path) -> None:
    """A half-finished edit to a workshop file is never overwritten."""
    (attendee / "README.md").write_text("my own note\n", encoding="utf-8")

    with pytest.raises(update_from_template.UpdateError, match="README.md"):
        update_from_template.update(attendee, source=str(template))
    assert (attendee / "README.md").read_text(encoding="utf-8") == "my own note\n"


def test_update_removes_retired_workshop_files_but_never_attendee_files(tmp_path: Path) -> None:
    """A guide the template deleted disappears; a file the attendee added later stays."""
    template = make_repository(tmp_path / "template", {"docs/DAY-1.md": "day one\n"})
    attendee = make_repository(tmp_path / "attendee", {"docs/DAY-1.md": "day one\n",
                                                       "docs/EXTRAS.md": "old extras\n"})
    (attendee / "docs/my-notes.md").write_text("mine\n", encoding="utf-8")
    git(attendee, "add", "--all")
    git(attendee, "commit", "--quiet", "-m", "My notes")

    assert update_from_template.update(attendee, source=str(template)) == ["docs/EXTRAS.md"]
    assert not (attendee / "docs/EXTRAS.md").exists()
    assert (attendee / "docs/my-notes.md").read_text(encoding="utf-8") == "mine\n"
    assert git(attendee, "diff", "--cached", "--name-only") == "", "nothing is staged for them"


def test_main_explains_the_next_step(template: Path, attendee: Path, monkeypatch, capsys) -> None:
    """The output tells a beginner what changed and how to save it."""
    monkeypatch.chdir(attendee)

    assert update_from_template.main(["--source", str(template)]) == 0
    output = capsys.readouterr().out
    assert "Updated 3 workshop file(s)" in output and "pull request" in output

    assert update_from_template.main(["--source", str(template / "missing")]) == 1
