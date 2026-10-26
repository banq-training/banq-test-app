"""Exercise the learner website independently of the preserved vendor app."""

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import site as site_module
from app.config import deployment_name, slugify
from app.site import create_app, site_manifest, slot_banner

HTML = '<!doctype html><html lang="en"><body><h1>Synthetic planner</h1></body></html>'
KIT = Path(".github/skills/create-website/assets/js/workshop.js")
PROJECT_BLUEPRINT = Path(".github/skills/create-website/assets/blueprints/project")
CATEGORIES = ("project", "calendar", "ideas", "weather", "map", "photo")
# Tested own-idea patterns: same kit and rules, but never offered in the first question.
PATTERNS = ("tracker", "dashboard", "game")
PAGES = CATEGORIES + PATTERNS


@pytest.fixture
def website(tmp_path: Path) -> Path:
    """Create a tiny synthetic site, not a prebuilt learner solution in the repository."""
    directory = tmp_path / "site"
    directory.mkdir()
    (directory / "index.html").write_text(HTML, encoding="utf-8")
    return directory


def test_website_serves_assets_and_identifies_revision(website: Path, monkeypatch) -> None:
    """Health and asset content must describe the actual requested website revision."""
    config = website.parent / "config.json"
    config.write_text(json.dumps({"displayName": "Synthetic Web Team"}), encoding="utf-8")
    (website / "main.js").write_text('document.title = "Synthetic";', encoding="utf-8")
    (website / "README.md").write_text("Draft notes", encoding="utf-8")
    monkeypatch.setenv("WORKSHOP_COMMIT", "b" * 40)
    client = TestClient(create_app(website, config))
    assert client.get("/").text == HTML
    assert client.get("/main.js").status_code == 200
    assert client.get("/README.md").status_code == 404
    assert client.get("/../config.json").status_code == 404
    result = client.get("/healthz").json()
    assert result["target"] == "website"
    assert result["label"] == "Synthetic Web Team"
    assert result["commit"] == "b" * 40
    assert result["index_sha256"] == hashlib.sha256(HTML.encode()).hexdigest()
    assert result["site_digest"] == site_manifest(website)["digest"]


@pytest.mark.parametrize(
    "filename", ["report.pdf", ".env", "server.py", "files.zip", ".private/data.json"]
)
def test_site_rejects_unintended_publication(website: Path, filename: str) -> None:
    """A website build must fail before copying reports, hidden files, or source code."""
    path = website / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("Synthetic content", encoding="utf-8")
    with pytest.raises(ValueError):
        site_manifest(website)


def test_own_idea_pages_open_by_their_folder_address(website: Path) -> None:
    """A shared idea link such as /ideas/team-lunch/ opens the page; other folders stay closed."""
    idea = website / "ideas" / "team-lunch"
    idea.mkdir(parents=True)
    (idea / "index.html").write_text(HTML, encoding="utf-8")
    (website / "ideas" / "empty").mkdir()
    client = TestClient(create_app(website))
    assert client.get("/ideas/team-lunch/index.html").status_code == 200
    assert client.get("/ideas/team-lunch/").text == HTML
    moved = client.get("/ideas/team-lunch", follow_redirects=False)
    assert moved.status_code == 307 and moved.headers["location"] == "team-lunch/"
    assert client.get("/ideas/team-lunch").text == HTML
    assert client.get("/ideas/").status_code == 404
    assert client.get("/ideas/empty/").status_code == 404
    assert client.get("/ideas/missing/").status_code == 404
    assert client.get("/ideas/team-lunch/README.md").status_code == 404


def test_idea_pages_find_the_shared_kit_without_rewritten_paths(website: Path) -> None:
    """A page in site/ideas/ asking for any shared file next to itself gets site/'s file, never its data."""
    idea = website / "ideas" / "team-lunch"
    (idea / "data").mkdir(parents=True)
    (idea / "index.html").write_text(HTML, encoding="utf-8")
    (idea / "data" / "items.json").write_text("{}", encoding="utf-8")
    for folder, name in (("css", "workshop.css"), ("js", "workshop.js"), ("art", "monday.svg"),
                         ("images", "my-photo.jpg")):
        (website / folder).mkdir(exist_ok=True)
        (website / folder / name).write_text(f"/* {name} */", encoding="utf-8")
    (website / "logo.png").write_text("logo", encoding="utf-8")
    (website / "data").mkdir()
    (website / "data" / "tasks.json").write_text("[]", encoding="utf-8")
    client = TestClient(create_app(website))
    assert client.get("/ideas/team-lunch/css/workshop.css").text == "/* workshop.css */"
    assert client.get("/ideas/team-lunch/js/workshop.js").status_code == 200
    assert client.get("/ideas/team-lunch/art/monday.svg").status_code == 200
    assert client.get("/ideas/team-lunch/images/my-photo.jpg").status_code == 200, "the learner's own pictures"
    assert client.get("/ideas/team-lunch/logo.png").text == "logo"
    assert client.get("/ideas/team-lunch/data/items.json").text == "{}"
    assert client.get("/ideas/team-lunch/data/tasks.json").status_code == 404, "never another page's data"
    assert client.get("/ideas/team-lunch/art/missing.svg").status_code == 404
    assert client.get("/ideas/team-lunch/.env").status_code == 404


def test_publisher_leaves_out_what_the_server_would_never_publish() -> None:
    """The publisher's keep-list matches the server's, so attendee files never fail a publish."""
    publisher = Path(".github/workflows/website-publisher.yml").read_text(encoding="utf-8")
    kept = re.search(r"case \"\$\{extension,,\}\" in\n\s+([^)]+)\)", publisher).group(1).split("|")
    assert set(kept) == site_module.ALLOWED_EXTENSIONS | {".md"}
    assert "Leave out files a website cannot use" in publisher and "$((8 * 1024 * 1024))" in publisher
    assert site_module.MAX_FILE_BYTES == 8 * 1024 * 1024


def test_site_digest_changes_with_assets_not_planning_notes(website: Path) -> None:
    """The fingerprint covers shipped bytes but excludes unserved Markdown notes such as site/README.md."""
    initial = site_manifest(website)
    (website / "README.md").write_text("Synthetic planning", encoding="utf-8")
    assert site_manifest(website) == initial
    (website / "main.css").write_text("body { color: black; }", encoding="utf-8")
    assert site_manifest(website)["digest"] != initial["digest"]


def test_knowledge_md_is_served_next_to_its_page_and_counts_in_the_fingerprint(website: Path) -> None:
    """The chat reads knowledge.md beside its page; an idea page never gets the first page's notes."""
    initial = site_manifest(website)
    (website / "knowledge.md").write_text("Synthetic lunch is on Fridays.", encoding="utf-8")
    assert site_manifest(website)["digest"] != initial["digest"], "a notes-only change still publishes"
    idea = website / "ideas" / "team-lunch"
    idea.mkdir(parents=True)
    (idea / "index.html").write_text(HTML, encoding="utf-8")
    (idea / "README.md").write_text("Synthetic planning", encoding="utf-8")
    client = TestClient(create_app(website))
    assert client.get("/knowledge.md").text == "Synthetic lunch is on Fridays."
    assert client.get("/ideas/team-lunch/knowledge.md").status_code == 404, "never another page's notes"
    assert client.get("/ideas/team-lunch/README.md").status_code == 404
    (idea / "knowledge.md").write_text("Synthetic idea notes.", encoding="utf-8")
    assert client.get("/ideas/team-lunch/knowledge.md").text == "Synthetic idea notes."
    assert "!site/**/knowledge.md" in Path(".dockerignore").read_text(encoding="utf-8").splitlines()


def test_version_file_is_served_but_does_not_change_the_fingerprint(website: Path) -> None:
    """Day 5 rollback: a rebuilt known-good page keeps its fingerprint while the build number moves on."""
    initial = site_manifest(website)
    version = website / "version.json"
    version.write_text(json.dumps({"version": "1.0.7", "build": 7, "commit": "a" * 40}), encoding="utf-8")
    assert site_manifest(website) == initial
    version.write_text(json.dumps({"version": "1.0.8", "build": 8, "commit": "b" * 40}), encoding="utf-8")
    assert site_manifest(website) == initial
    assert TestClient(create_app(website)).get("/version.json").json()["build"] == 8
    nested = website / "ideas" / "team-lunch"
    nested.mkdir(parents=True)
    (nested / "version.json").write_text("{}", encoding="utf-8")
    assert site_manifest(website)["digest"] != initial["digest"], "only the publisher's root file is excluded"


def test_feature_slot_marks_every_page_and_keeps_the_fingerprint(website: Path, monkeypatch) -> None:
    """Day 5: a pull request's test copy names its build at the top; production serves the page as is."""
    idea = website / "ideas" / "team-lunch"
    idea.mkdir(parents=True)
    (idea / "index.html").write_text(HTML, encoding="utf-8")
    (website / "main.js").write_text("const answer = 42;", encoding="utf-8")
    config = website.parent / "config.json"
    config.write_text(json.dumps({"displayName": "Synthetic Web Team"}), encoding="utf-8")
    monkeypatch.delenv("WEBSITE_SLOT", raising=False)
    production = TestClient(create_app(website, config))
    assert production.get("/").text == HTML
    assert production.get("/healthz").json()["slot"] == "production"
    for name, value in {"WEBSITE_SLOT": "feature", "WEBSITE_PULL_REQUEST": "5",
                        "WEBSITE_VERSION": "1.0.3-feature", "WEBSITE_BUILD": "3"}.items():
        monkeypatch.setenv(name, value)
    feature = TestClient(create_app(website, config))
    page = feature.get("/")
    assert page.headers["cache-control"] == "no-store"
    strip = page.text.split("<body>", 1)[1].split("<h1>", 1)[0]
    assert 'data-workshop-slot="feature"' in strip
    for words in ("Feature slot", "Pull request #5", "Version 1.0.3-feature", "Build 3", "not your live website"):
        assert words in strip
    assert 'data-workshop-slot="feature"' in feature.get("/ideas/team-lunch/").text
    assert feature.get("/main.js").text == "const answer = 42;"
    health = feature.get("/healthz").json()
    assert health["slot"] == "feature"
    # The same files in both slots: what you tested is exactly what production gets.
    assert health["site_digest"] == production.get("/healthz").json()["site_digest"]
    assert health["index_sha256"] == hashlib.sha256(HTML.encode()).hexdigest()


def test_feature_strip_shows_values_as_text_only() -> None:
    """Build details reach the page as text, never as markup, and production has no strip."""
    strip = slot_banner({"WEBSITE_SLOT": "feature", "WEBSITE_VERSION": "<script>alert(1)</script>"})
    assert "<script>" not in strip and "&lt;script&gt;" in strip
    assert slot_banner({"WEBSITE_SLOT": "production"}) == "" and slot_banner({}) == ""


def test_guided_kit_assets_fit_the_website_target(website: Path) -> None:
    """A copied blueprint and kit publish as-is, without skill files or license notes."""
    source = Path(".github/skills/create-website/assets")
    copies = {
        "blueprints/project/index.html": "index.html",
        "blueprints/project/data/tasks.json": "data/tasks.json",
        "css/workshop.css": "css/workshop.css",
        "js/workshop.js": "js/workshop.js",
        "art/hero-project.svg": "art/hero-project.svg",
        "art/monday.svg": "art/monday.svg",
        "fonts/source-sans-3-latin.woff2": "fonts/source-sans-3-latin.woff2",
        "fonts/OFL.txt": "FONT-LICENSE.md",
    }
    for original, relative in copies.items():
        destination = website / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / original, destination)
    manifest = site_manifest(website)
    assert set(manifest["files"]) == set(copies.values()) - {"FONT-LICENSE.md"}
    client = TestClient(create_app(website))
    for relative in manifest["files"]:
        response = client.get("/" + relative)
        assert response.status_code == 200
        assert hashlib.sha256(response.content).hexdigest() == manifest["files"][relative]
    assert client.get("/FONT-LICENSE.md").status_code == 404


def board_columns(page: Path) -> list[str]:
    """Read the column names a board page renders from, as written in its inline SAMPLE."""
    inline = re.search(r"columns: \[(.+?)\]", page.read_text(encoding="utf-8"))
    assert inline is not None, "the board page must declare SAMPLE.columns"
    return [name.strip().strip("'") for name in inline.group(1).split(",")]


def test_chat_bubble_is_optional_safe_and_holds_no_secret() -> None:
    """The chat kit talks to the preview, or on a published website only to its own /api/ask."""
    chat = (KIT.parent / "workshop-chat.js").read_text(encoding="utf-8")
    assert "innerHTML" not in chat and "eval(" not in chat and not re.search(r"https?://", chat)
    assert re.findall(r"fetch\(([^,]+),", chat) == ["'/api/ask'", "'knowledge.md'"], \
        "only its own website and the owner's notes next to the page, never another service"
    assert "XMLHttpRequest" not in chat
    assert "acquireVsCodeApi()" in chat and chat.count("acquireVsCodeApi()") == 1
    assert "'workshop.ask'" in chat and "'workshop.answer'" in chat
    assert "switched off" in chat, "a page opened as a file says so plainly"
    assert "box.checked ? 'Ticked' : 'Not ticked'" in chat, "the assistant can tell which boxes are ticked"
    assert "Picture: ${picture.alt.trim()}" in chat, "the assistant can tell what pictures show"
    assert "window.Workshop = Object.assign(window.Workshop || {}, { addChat })" in chat
    for category in PAGES:
        page = (PROJECT_BLUEPRINT.parent / category / "index.html").read_text(encoding="utf-8")
        assert "workshop-chat.js" not in page, "chat is added on request, not shipped in every starter"


def test_board_columns_come_from_the_page_not_older_browser_storage() -> None:
    """A requested column change must reach a learner who already has saved cards."""
    kit = KIT.read_text(encoding="utf-8")
    assert "function useColumns(" in kit
    assert "useColumns" in kit.split("window.Workshop = ")[1]
    page = (PROJECT_BLUEPRINT / "index.html").read_text(encoding="utf-8")
    assert "useColumns(valid(loaded) ? loaded : SAMPLE, SAMPLE.columns)" in page
    columns = board_columns(PROJECT_BLUEPRINT / "index.html")
    data = json.loads((PROJECT_BLUEPRINT / "data/tasks.json").read_text(encoding="utf-8"))
    assert columns == data["columns"]
    assert {item["column"] for item in data["items"]} <= set(columns)


@pytest.mark.parametrize("category", PAGES)
def test_examples_reload_themselves_without_a_reset_button(category: str) -> None:
    """Beginners get their examples back by emptying the page, not by finding a button."""
    blueprints = PROJECT_BLUEPRINT.parent
    page = (blueprints / category / "index.html").read_text(encoding="utf-8")
    assert "Start again with the examples" not in page
    assert 'id="reset"' not in page
    assert "saved.clear()" not in page
    # An emptied page counts as nothing saved, so start() falls back to the examples.
    assert re.search(r"const valid = data =>.*?\.length > 0", page, re.DOTALL) is not None


@pytest.mark.skipif(shutil.which("node") is None, reason="Node runs the browser helper kit")
def test_use_columns_keeps_saved_cards_while_following_a_renamed_board() -> None:
    """Renaming columns must not discard the learner's own entries or strand them."""
    stale = {
        "columns": ["Monday", "Friday"],
        "items": [
            {"id": "t1", "text": "Synthetic sample task", "column": "Monday", "done": True},
            {"id": "own", "text": "Synthetic learner task", "column": "Friday", "done": False},
        ],
    }
    renamed = ["To Do", "In Progress", "Done"]
    harness = f"""
        global.window = {{}}
        eval(require('node:fs').readFileSync({str(KIT)!r}, 'utf8'))
        const {{ useColumns }} = window.Workshop
        const once = useColumns({json.dumps(stale)}, {json.dumps(renamed)})
        console.log(JSON.stringify({{
            once,
            unchanged: useColumns(once, {json.dumps(renamed)}),
            noColumns: useColumns({json.dumps(stale)}, []),
        }}))
    """
    result = subprocess.run(
        ["node", "-e", harness], capture_output=True, text=True, check=True, timeout=60
    )
    once = json.loads(result.stdout)["once"]
    repeated = json.loads(result.stdout)["unchanged"]
    assert once["columns"] == renamed
    assert [item["id"] for item in once["items"]] == ["t1", "own"]
    assert [item["column"] for item in once["items"]] == ["To Do", "To Do"]
    assert once["items"][0]["done"] is True
    assert repeated == once
    assert json.loads(result.stdout)["noColumns"] == stale


def run_node(script: str) -> str:
    """Run a short script in Node and return its standard output."""
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    return result.stdout


def inline_block(page: str, start: str) -> str:
    """Return a top-level block of a blueprint's inline script, from its first line to its closing brace."""
    match = re.search(re.escape(start) + r".*?\n        \}\n", page, re.DOTALL)
    assert match is not None, start
    return match.group(0)


@pytest.mark.parametrize("category", PAGES)
def test_inline_sample_matches_the_data_file(category: str) -> None:
    """The skill keeps the inline SAMPLE and data/*.json identical, so an offline page looks the same."""
    blueprint = PROJECT_BLUEPRINT.parent / category
    starters = json.loads((blueprint.parent.parent / "starters.json").read_text(encoding="utf-8"))
    starter = next(item for item in starters["starters"] + starters["idea_patterns"] if item["id"] == category)
    page = (blueprint / "index.html").read_text(encoding="utf-8")
    literal = inline_block(page, "const SAMPLE = ").removeprefix("const SAMPLE = ")
    inline = json.loads(run_node(f"console.log(JSON.stringify({literal}))"))
    assert inline == json.loads((blueprint / starter["data_file"]).read_text(encoding="utf-8"))


def test_weather_starter_uses_us_units_and_local_cities() -> None:
    """The US audience sees Fahrenheit and mph, starting with Princeton."""
    blueprint = PROJECT_BLUEPRINT.parent / "weather"
    data = json.loads((blueprint / "data/weather.json").read_text(encoding="utf-8"))
    assert [city["name"] for city in data["cities"]] == ["Princeton", "Copenhagen", "Sydney"]
    page = (blueprint / "index.html").read_text(encoding="utf-8")
    assert "temperature_unit: 'fahrenheit', wind_speed_unit: 'mph'" in page
    assert "\\u00b0F`" in page and " mph`" in page
    assert "\\u00b0C" not in page and "km/h" not in page


def test_calendar_weeks_start_on_sunday_and_workdays_are_monday_to_friday() -> None:
    """Run the calendar's own date code: Month and Week start on Sunday, Workdays skip the weekend."""
    page = (PROJECT_BLUEPRINT.parent / "calendar" / "index.html").read_text(encoding="utf-8")
    helpers = "\n".join(
        re.search(rf"^\s*const {name} = .*$", page, re.MULTILINE).group(0)
        for name in ("addDays", "startOfWeek")
    )
    script = helpers + "\nlet state = { view: 'month' }\nlet cursor = new Date(2026, 9, 28)\n"
    script += inline_block(page, "function visibleDays() {")
    script += (
        "const out = {}\n"
        "for (const view of ['month', 'week', 'workdays']) {"
        " state.view = view; out[view] = visibleDays().map(day => day.getDay()) }\n"
        "console.log(JSON.stringify(out))"
    )
    days = json.loads(run_node(script))
    assert days["month"][0] == 0 and days["month"][-1] == 6 and len(days["month"]) % 7 == 0
    assert days["week"] == [0, 1, 2, 3, 4, 5, 6]
    assert days["workdays"] == [1, 2, 3, 4, 5]


def test_missing_site_and_invalid_markup_are_not_ready(tmp_path: Path, website: Path) -> None:
    """A blank template must not pass a website deployment check."""
    with pytest.raises(ValueError, match="index.html"):
        site_manifest(tmp_path)
    (website / "index.html").write_text("not a website", encoding="utf-8")
    with pytest.raises(ValueError, match="HTML"):
        site_manifest(website)
    assert TestClient(create_app(website)).get("/healthz").status_code == 503


def test_oversized_asset_is_rejected(website: Path, monkeypatch) -> None:
    """Bound asset reads and deployment validation responses."""
    monkeypatch.setattr("app.site.MAX_FILE_BYTES", 10)
    with pytest.raises(ValueError, match="nonempty and at most"):
        site_manifest(website)


@pytest.mark.parametrize("label", ["Synthetic Team", "7 Synthetic", "Synthetic " * 10])
def test_target_names_are_distinct_and_vendor_names_stay_stable(label: str) -> None:
    """Monday must not overwrite Tuesday's app or silently rename an existing vendor app."""
    vendor = deployment_name(label, "vendor")
    website = deployment_name(label, "website")
    assert vendor == slugify(label)
    assert website != vendor and len(website) <= 32
    assert website.endswith("-web")
    assert website == deployment_name(label, "website")
    with pytest.raises(ValueError):
        deployment_name(label, "unknown")


ASSETS = PROJECT_BLUEPRINT.parent.parent


def test_chart_kit_is_local_licensed_and_runs_without_eval() -> None:
    """ECharts ships in the kit with its licences, and ECharts GL needs no eval under the preview's policy."""
    vendor = ASSETS / "js/vendor"
    echarts = (vendor / "echarts.min.js").read_text(encoding="utf-8")
    assert "Licensed to the Apache Software Foundation" in echarts[:600]
    gl = (vendor / "echarts-gl.min.js").read_text(encoding="utf-8")
    # The one expression parser was replaced, so a strict Content-Security-Policy is enough.
    assert "workshop patch: no eval" in gl and 'new Function("width","height","dpr"' not in gl
    licences = (vendor / "CHART-LICENSES.md").read_text(encoding="utf-8")
    for name in ("Apache License", "ECharts GL LICENSE", "ClayGL LICENSE", "ZRender LICENSE", "d3.js LICENSE"):
        assert name in licences
    helper = (ASSETS / "js/workshop-charts.js").read_text(encoding="utf-8")
    assert "innerHTML" not in helper and "fetch(" not in helper and not re.search(r"https?://", helper)
    assert "zoomSensitivity: 0" in helper and "prefers-reduced-motion" in helper
    attributes = Path(".gitattributes").read_text(encoding="utf-8")
    assert "assets/js/vendor/*.min.js -text -diff" in attributes


def test_chart_recipes_are_offered_and_safe() -> None:
    """Every tested recipe is listed in /add-chart and draws through the kit helper only."""
    skill = Path(".github/skills/add-chart/SKILL.md").read_text(encoding="utf-8")
    recipes = sorted(Path(".github/skills/add-chart/recipes").glob("*.js"))
    assert len(recipes) >= 10
    for recipe in recipes:
        assert f"(recipes/{recipe.name})" in skill, recipe.name
        code = recipe.read_text(encoding="utf-8")
        assert "Workshop.chart(" in code and "Check:" in code
        assert "innerHTML" not in code and "fetch(" not in code and not re.search(r"https?://", code)
        if "3d" in recipe.stem:
            assert "echarts-gl.min.js" in code and "chart-stage" in code


def test_map_places_are_sourced_and_sit_on_the_map() -> None:
    """Every sample place has a short description, an official source, and lies inside the base map."""
    blueprint = ASSETS / "blueprints/map"
    places = json.loads((blueprint / "data/places.json").read_text(encoding="utf-8"))["items"]
    base = json.loads((blueprint / "data/map.json").read_text(encoding="utf-8"))
    (west, south), (east, north) = base["bounds"]
    assert len(places) == 18 and len({place["id"] for place in places}) == 18
    for place in places:
        assert place["category"] in {"Campus", "History", "Arts", "Nature", "Town"}
        assert west < place["lon"] < east and south < place["lat"] < north, place["id"]
        assert 0 < len(place["description"].split()) <= 22
        assert place["source"].startswith(("https://", "http://"))
    kinds = {feature["properties"]["kind"] for feature in base["areas"]["features"]}
    assert kinds == {"town", "campus", "water"}
    assert "public domain" in base["about"] and base["roads"] and base["rail"]


@pytest.mark.parametrize("category", PAGES)
def test_every_starter_assembles_into_a_publishable_site(tmp_path: Path, category: str) -> None:
    """The blueprint plus the whole kit stays inside the website target's file and size limits."""
    site = tmp_path / "site"
    shutil.copytree(ASSETS / "blueprints" / category, site)
    for folder in ("css", "js", "art"):
        shutil.copytree(ASSETS / folder, site / folder)
    (site / "fonts").mkdir()
    shutil.copyfile(ASSETS / "fonts/source-sans-3-latin.woff2", site / "fonts/source-sans-3-latin.woff2")
    shutil.copyfile(ASSETS / "fonts/OFL.txt", site / "FONT-LICENSE.md")
    shutil.copyfile(ASSETS / "js/vendor/CHART-LICENSES.md", site / "CHART-LICENSES.md")
    if category == "game":
        # Only the game page carries three.js, copied beside the chart library.
        for name in ("three.module.js", "three.core.js"):
            shutil.copyfile(ASSETS / "game" / name, site / "js/vendor" / name)
        shutil.copyfile(ASSETS / "game/THREE-LICENSE.md", site / "THREE-LICENSE.md")
    manifest = site_manifest(site)
    assert "js/vendor/echarts.min.js" in manifest["files"]
    page = (site / "index.html").read_text(encoding="utf-8")
    for local in re.findall(r'(?:src|href)="((?:css|js|art|data|gallery)/[^"]+)"', page):
        assert (site / local).is_file(), local
    for module in re.findall(r"import .* from '\./([^']+)'", page):
        assert (site / module).is_file(), module


def test_photo_helper_talks_only_to_the_preview() -> None:
    """The photo page holds no key and makes pictures only through the Website preview."""
    helper = (ASSETS / "js/workshop-photo.js").read_text(encoding="utf-8")
    assert "Workshop.preview()" in helper and "acquireVsCodeApi" not in helper
    assert "'workshop.photo.edit'" in helper and "'workshop.photo.save'" in helper
    assert "innerHTML" not in helper and not re.search(r"https?://", helper)
    assert "switched off" not in helper and "gallery only" in helper
    kit = KIT.read_text(encoding="utf-8")
    assert kit.count("acquireVsCodeApi()") == 1 and "function preview()" in kit
    gallery = json.loads((ASSETS / "blueprints/photo/data/gallery.json").read_text(encoding="utf-8"))
    for item in gallery["items"]:
        picture = ASSETS / "blueprints/photo" / item["file"]
        assert picture.read_bytes()[:3] == b"\xff\xd8\xff" and picture.stat().st_size < 300 * 1024


@pytest.mark.skipif(shutil.which("node") is None, reason="Node runs the browser helper kit")
def test_photo_helper_trusts_picture_bytes_not_their_label() -> None:
    """The Website preview labels .jpg files image/jpg; the helper must still accept the sample photos."""
    helper = ASSETS / "js/workshop-photo.js"
    harness = f"""
        const fs = require('node:fs')
        global.window = {{ addEventListener() {{}} }}
        global.FileReader = class {{ readAsDataURL() {{ this.result = 'data:image/jpeg;base64,AA=='; this.onload() }} }}
        global.Image = class {{ set src(value) {{ this.naturalWidth = 2000; this.naturalHeight = 1000; this.onload() }} }}
        global.document = {{ createElement: () => ({{ getContext: () => ({{ drawImage() {{}} }}), toDataURL: () => 'data:image/jpeg;base64,BB==' }}) }}
        eval(fs.readFileSync({str(helper)!r}, 'utf8'))
        const {{ shrink }} = window.Workshop.photo
        const jpeg = new Blob([new Uint8Array([0xff, 0xd8, 0xff, 0xe0, 1, 2, 3])], {{ type: 'image/jpg' }})
        const text = new Blob(['not a picture'], {{ type: 'image/jpeg' }})
        Promise.all([
            shrink(jpeg).then(value => value, error => 'error: ' + error.message),
            shrink(text).then(value => value, error => 'error: ' + error.message),
        ]).then(results => console.log(JSON.stringify(results)))
    """
    accepted, refused = json.loads(run_node(harness))
    assert accepted == "data:image/jpeg;base64,BB=="
    assert refused == "error: Choose a JPEG, PNG or WebP photo."
