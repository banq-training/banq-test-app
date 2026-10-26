"""The learner test helper reads pages the way the Day 3 and Day 5 labs describe."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "checks"))

import website  # noqa: E402

PAGE = """<!doctype html><html><head><title> Team  Planner </title>
<link rel="stylesheet" href="css/workshop.css"><script src="js/missing.js"></script>
<script src="https://example.invalid/remote.js"></script></head>
<body><h1>Plan the <em>week</em></h1><button type="button">Hide finished tasks</button>
<button aria-label="Add a task on Monday">+</button><img src="art/hero.svg" alt="">
<a href="ideas/lunch/">Lunch</a><script>const secret = 'not visible text'</script>
<p>1 of 4 done</p></body></html>"""


@pytest.fixture
def page(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> website.Page:
    """A small site with one missing script, read through the helper."""
    (tmp_path / "site" / "css").mkdir(parents=True)
    (tmp_path / "site" / "art").mkdir()
    (tmp_path / "site" / "data").mkdir()
    (tmp_path / "site" / "index.html").write_text(PAGE, encoding="utf-8")
    (tmp_path / "site" / "css" / "workshop.css").write_text("body{}", encoding="utf-8")
    (tmp_path / "site" / "art" / "hero.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "site" / "data" / "tasks.json").write_text('{"items": [1, 2]}', encoding="utf-8")
    monkeypatch.setattr(website, "ROOT", tmp_path)
    return website.Page("site/index.html")


def test_page_reads_title_headings_buttons_and_text(page: website.Page) -> None:
    """Visible words are found; script code is not mistaken for page text."""
    assert page.title == "Team Planner"
    assert page.headings == ["Plan the week"]
    assert page.has_button("hide finished") and page.has_button("Add a task on Monday")
    assert not page.has_button("Delete everything")
    assert page.shows("1 of 4 done") and not page.shows("not visible text")
    assert "const secret" in page.script


def test_page_finds_missing_local_files_only(page: website.Page) -> None:
    """Remote addresses and links between pages are not counted as files to load."""
    assert page.local_files() == ["css/workshop.css", "js/missing.js", "art/hero.svg"]
    assert page.missing_files() == ["js/missing.js"]
    assert page.data("data/tasks.json") == {"items": [1, 2]}


def test_helper_reads_every_starter_blueprint() -> None:
    """Each starter page parses and lists the kit files it needs."""
    for blueprint in Path(".github/skills/create-website/assets/blueprints").glob("*/index.html"):
        starter = website.Page(blueprint.as_posix())
        assert starter.title and starter.headings, blueprint
        assert "js/workshop.js" in starter.local_files(), blueprint
