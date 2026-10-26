"""Keep executable examples and timetable claims aligned with the labs."""

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml


# David's final slides for Days 3-5: four hours each, written in elapsed time.
SLIDE_SLOTS = ["00:00-00:20", "00:20-00:50", "00:50-01:30", "01:30-01:45",
               "01:45-02:30", "02:30-03:15", "03:15-03:45", "03:45-04:00"]


def active_lab_guides() -> list[Path]:
    """Every attendee guide the template ships: one per day."""
    return [Path(f"docs/DAY-{day}.md") for day in range(1, 6)]


def day_one_section(number: int) -> str:
    """Return one numbered section of the Day 1 guide, without the sections after it."""
    text = Path("docs/DAY-1.md").read_text(encoding="utf-8")
    return text.split(f"\n## {number}. ", 1)[1].split("\n## ", 1)[0]


def test_lab_timeboxes_match_the_day_routes() -> None:
    """Optional exercises must not silently extend the published core blocks."""
    route = Path("docs/DAY-1.md").read_text(encoding="utf-8").split("## Today's Route", 1)[1]
    rows = re.findall(r"\| (\d\d):(\d\d)-(\d\d):(\d\d) \| \[(\d)\. ", route)
    assert [row[-1] for row in rows] == ["1", "2", "3", "4", "5", "6", "7"]
    timed = set()
    for start_hour, start_minute, end_hour, end_minute, number in rows:
        minutes = (int(end_hour) - int(start_hour)) * 60 + int(end_minute) - int(start_minute)
        blocks = re.findall(r"^### .*\((\d+) minutes\)", day_one_section(int(number)), re.MULTILINE)
        if blocks:
            timed.add(number)
            assert sum(map(int, blocks)) == minutes, number
    assert timed == {"4", "6", "7"}
    # The cloud agent is Thursday's 40-minute 00:50-01:30 delegation block.
    assert "00:50-01:30" in day_route("DAY-4.md")
    assert "| 09:30-10:00 | [2. Your copy, your Codespace, and Chat]" in route
    # Owner, 25 October 2026: one guide per day, linked from a minimal README; no labs folder.
    assert not Path("labs").exists() and not Path("docs/START-HERE.md").exists()
    readme = Path("README.md").read_text(encoding="utf-8")
    for day in range(1, 6):
        assert f"](docs/DAY-{day}.md)" in readme, day
    assert "](docs/QUICK-REFERENCE.md)" in readme and "](docs/QUICK-COMMANDS.md)" in readme
    assert len(readme.splitlines()) < 40, "the README stays a short front page"


def test_first_lab_requires_chat_not_terminal_setup() -> None:
    """The beginner entry path must not silently reintroduce diagnostic commands."""
    guide = Path("docs/DAY-1.md").read_text(encoding="utf-8")
    morning = guide.split("\n## 1. This Is GitHub", 1)[1].split("\n## 4. ", 1)[0]
    assert "```" not in morning
    assert "copilot --version" not in morning
    assert "gh auth status" not in morning
    for heading in ("## 2. Your Copy, Your Codespace, and Chat", "## 3. Your First Website"):
        assert heading in morning
    flat = " ".join(morning.split())
    assert "Concepts only: no commands." in flat
    assert "Use this template > Create a new repository" in flat
    assert "choose **agentic-dev-labs**" in flat and "choose **Private**" in flat
    assert "Make only one." in flat
    assert "save -> review -> commit -> push" in flat
    assert "presenter shows `/create-website`" in flat
    # Agreed 21 October 2026: attendees watch at 09:00, copy the template at 09:30, and build
    # and push the first website at 10:00. Owner, 25 October 2026: no brief.md notes file.
    tour = day_one_section(1)
    chat = day_one_section(2)
    first_site = day_one_section(3)
    assert "Use this template" not in tour and "Just watch" in tour
    assert "Use this template" in chat and "Trust Folder & Continue" in chat
    assert "**DAY-1.md**" in chat and "**Open Preview**" in chat
    # Rehearsed 22 October 2026: New Chat opens the Copilot harness, with manual approvals and no
    # Keep or Undo, so Monday stays in the first (Local) chat.
    assert "**New Chat**" not in chat and "Stay in this chat" in chat
    assert "`/create-website`" in first_site
    assert "`Add my first website`" in first_site and "**... > Push**" in first_site
    assert "expect -> try -> compare -> improve -> repeat" in guide


def test_no_brief_notes_file() -> None:
    """Owner, 25 October 2026: brief.md confused beginners, so no guide or skill mentions it."""
    texts = [Path("README.md"), Path("site/README.md"), Path("checks/README.md"),
             *Path("docs").glob("*.md"), *Path(".github/skills").rglob("SKILL.md")]
    for path in texts:
        assert "brief.md" not in path.read_text(encoding="utf-8"), path
    assert "Write no notes file" in " ".join(
        Path(".github/skills/create-website/SKILL.md").read_text(encoding="utf-8").split())


def test_monday_build_checks_are_manual_and_extensions_are_optional() -> None:
    """Tool configuration, persistence and publication must not gate a first website."""
    guide = Path("docs/DAY-1.md").read_text(encoding="utf-8")
    first_page = " ".join((day_one_section(4) + day_one_section(5)).split())
    interaction = day_one_section(6)
    sharing = day_one_section(7)
    assert "python3 scripts/website_preview.py status" in guide
    assert "appear by itself" in first_page
    assert "MCP: Add Server" not in guide
    assert "1 of 4 done" in first_page
    assert "localStorage" not in guide.split("## Optional extras")[0]
    assert "not a requirement" in interaction
    assert "A deployment or saved browser state is not required" in sharing
    assert "## Optional extras" in guide and "### Publish Your Page" in guide


def test_personalisation_lab_follows_the_chosen_category() -> None:
    """Learners improve their own page, with visual and feature changes kept small."""
    text = day_one_section(6)
    extras = Path("docs/DAY-1.md").read_text(encoding="utf-8").split("## Optional extras", 1)[1]
    for category in ("Project Planner", "Calendar", "Ideas Wall", "Weather", "Princeton Map", "Photo Studio"):
        assert f"| {category} |" in extras
    flat = " ".join(text.split())
    assert "Add **one feature**, a chart or a chat, and make **one appearance change**" in flat
    assert "Type **`/add-chart`**" in text and "Type **`/add-chat`**" in text
    assert "not a new creation interview" in text
    assert "If a feature already works" in text
    assert "Keep the design unchanged" in extras
    assert "](#5-check-it-yourself)" in text
    checks = day_one_section(5)
    assert "2 of 4" in checks and "3 notes planned" in checks and "2 of 5" in checks


def test_day_one_teaches_reading_code_undo_and_history() -> None:
    """First-timers build a second website, undo a change, and find their history; reading code is optional."""
    second_site = day_one_section(4)
    assert "### Build It" in second_site and "site/ideas/" in second_site
    assert "Peek" not in second_site, "owner, 25 October 2026: the code peek is an optional extra"
    extras = Path("docs/DAY-1.md").read_text(encoding="utf-8").split("## Optional extras", 1)[1]
    # The 11:45 checks cover every starter, with the counts the starters really show.
    checking = day_one_section(5)
    for category in ("Project Planner", "Calendar", "Ideas Wall", "Weather", "Princeton Map", "Photo Studio"):
        assert f"| {category}" in checking, category
    starters = {
        starter["id"]: starter
        for starter in json.loads(Path(".github/skills/create-website/assets/starters.json")
                                  .read_text(encoding="utf-8"))["starters"]
    }
    assert "18 places" in starters["map"]["manual_check"] and "**18 places**" in checking
    assert "6 pictures" in starters["photo"]["manual_check"] and "**6 pictures**" in checking
    assert "**Peek inside the code.**" in extras
    assert "Explain the lines I selected" in extras and "`<h1>`" in extras
    # The example headline in the extra must be the Project Planner starter's real headline.
    example = re.search(r"for example \*(.+?)\*", extras).group(1)
    planner = Path(".github/skills/create-website/assets/blueprints/project/index.html")
    assert f"<h1>{example}</h1>" in planner.read_text(encoding="utf-8")

    interaction = day_one_section(6)
    assert "select **Undo**" in interaction and "**Keep** and **Undo**" in interaction
    sketch = Path("docs/images/sketch-example.png")
    assert "](images/sketch-example.png)" in interaction
    assert sketch.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" and sketch.stat().st_size < 100 * 1024
    assert "never a picture with real work information" in interaction

    sharing = day_one_section(7)
    assert "**sparkle icon**" in sharing and "**Commits**" in sharing and "**History**" in sharing
    for level in ("**Bronze**", "**Silver**", "**Gold**"):
        assert level in sharing
    quick_reference = Path("docs/QUICK-REFERENCE.md").read_text(encoding="utf-8")
    assert "Undo Copilot's change" in quick_reference and "Show Copilot a picture" in quick_reference


def test_daily_schedule_has_no_gaps_or_overlaps() -> None:
    """Each day guide's route fills the published day without adding hidden time."""
    days = {"DAY-1.md": 360, "DAY-2.md": 360, "DAY-3.md": 240, "DAY-4.md": 240, "DAY-5.md": 240}
    for guide, expected in days.items():
        intervals = [
            tuple(int(time[:2]) * 60 + int(time[3:]) for time in slot.split("-"))
            for slot in day_route(guide)
        ]
        assert all(end > start for start, end in intervals), guide
        assert sum(end - start for start, end in intervals) == expected, guide
        assert all(
            previous[1] == following[0] for previous, following in zip(intervals, intervals[1:])
        ), guide


def test_customization_examples_parse() -> None:
    """Broken frontmatter can silently prevent a customization from loading."""
    for lab in active_lab_guides():
        text = lab.read_text(encoding="utf-8")
        for language, body in re.findall(
            r"```(json|yaml|markdown)\n(.*?)\n[ \t]*```", text, re.DOTALL
        ):
            body = "\n".join(
                line[3:] if line.startswith("   ") else line for line in body.splitlines()
            )
            if language == "json":
                json.loads(body)
            elif language == "yaml":
                yaml.safe_load(body)
            elif body.startswith("---\n"):
                metadata = yaml.safe_load(body.split("---", 2)[1])
                assert isinstance(metadata, dict)
                assert metadata.get("description")


def test_guided_website_skill_is_explicit_and_preserves_learner_work() -> None:
    """A provided workflow must wait for choices and never count invented checks as success."""
    path = Path(".github/skills/create-website/SKILL.md")
    text = path.read_text(encoding="utf-8")
    metadata = yaml.safe_load(text.split("---", 2)[1])
    assert metadata["name"] == path.parent.name
    assert metadata["user-invocable"] is True
    assert metadata["disable-model-invocation"] is True
    assert "Stop after the question and wait" in text
    assert "Choosing a category is the approval to build it" in text
    assert "not yet checked" in text
    assert "Never overwrite the first page" in text
    assert "No deployment or public port" in text
    assert "python3 scripts/website_preview.py start" in text
    assert "paid reference service" in text
    assert "No logo-generation API" in text
    assert 'git remote get-url origin' in text
    assert "Describe your idea in one sentence." in text
    # Monday 10:45: everyone builds one own idea right after the first page is pushed.
    assert "Never ask for checks or a demonstration first" in text
    assert "never replace the first page" in text
    assert "moves on to the next lab" not in text and "offer a second idea only after" not in text
    assert "or build\n  your own idea in its own folder?" in text
    for name in ("project", "calendar", "ideas", "weather", "map", "photo"):
        assert f"./assets/blueprints/{name}/index.html" in text
    assert "Workshop.store" in text and "Workshop.loadJSON" in text
    assert "Workshop.enableBoard" in text and "Workshop.addButton" in text
    assert "./assets/art/" in text
    assert "Vue" not in text and "Vite" not in text
    assert "100 KiB" in text
    assert "../start-website/SKILL.md" in text
    assert "../stop-website/SKILL.md" in text
    assert "category-specific ideas" in text


def test_preview_lifecycle_skills_reuse_the_helper_and_preserve_files() -> None:
    """Recovery must not recreate pages, bypass editor tool restrictions, or kill by port."""
    texts = {}
    for name in ("start-website", "stop-website"):
        path = Path(".github/skills") / name / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        metadata = yaml.safe_load(text.split("---", 2)[1])
        assert metadata["name"] == name
        assert metadata["description"]
        assert metadata["user-invocable"] is True
        assert metadata["disable-model-invocation"] is True
        texts[name] = text
    start = texts["start-website"]
    assert "python3 scripts/website_preview.py start" in start
    assert "relative to site/" in start
    assert "Do not create a placeholder" in start
    assert "Can you see your page beside Chat?" in " ".join(start.split())
    assert "no server, no port, no sign-in" in start
    stop = texts["stop-website"]
    assert "python3 scripts/website_preview.py stop" in stop
    assert "Do not edit, delete, reset" in stop
    assert "Do not use `pkill`, `killall`" in stop
    assert "previewOpen: false" in stop


def test_monday_chat_starts_with_same_question_different_answers() -> None:
    """Owner, 23 October 2026: a plain shared prompt replaces /next-word: no skill, no made-up numbers."""
    assert not Path(".github/skills/next-word").exists()
    guides = [Path("README.md"), Path("AGENTS.md"), *Path(".github").rglob("*.md"),
              *Path("docs").glob("*.md")]
    for path in guides:
        assert "next-word" not in path.read_text(encoding="utf-8"), path
    chat = " ".join(day_one_section(2).split())
    prompt = "Invent a fun name for my workshop table. Reply with the name only."
    assert f'"{prompt}"' in chat and chat.index(prompt) < chat.index("Stay in this chat")
    assert "the same question can give different answers" in chat and "check its work" in chat
    assert "table name" in Path("docs/DAY-1.md").read_text(encoding="utf-8")
    # Tried through Copilot CLI with these instructions loaded on 23 October 2026: Auto, Claude
    # Haiku 5.5 and GPT-5.6 Luna gave 3-4 different names in 5 tries. Copilot reads the instruction
    # files with every chat, and the open Day 1 guide can join it, so none of them may suggest a name.
    tried = ("brainy bunch", "idea forge", "prompt posse", "table tornado")
    for path in ("README.md", "docs/DAY-1.md", "AGENTS.md", ".github/copilot-instructions.md"):
        text = Path(path).read_text(encoding="utf-8").lower()
        assert not any(name in text for name in tried), path
    for path in ("AGENTS.md", ".github/copilot-instructions.md"):
        assert "workshop table" not in Path(path).read_text(encoding="utf-8"), path


def test_keep_comes_before_undo() -> None:
    """Undo in Chat takes back every change not kept yet, so learners keep what they like first."""
    first_site = " ".join(day_one_section(3).split())
    assert "select **Keep**" in first_site
    assert "**Undo** takes back every change you have not kept" in first_site
    interaction = " ".join(day_one_section(6).split())
    bold = interaction.split("**Be brave once, then undo it.**", 1)
    assert "select **Keep**" in bold[0], "the chart and look are kept before the wild change"
    assert "takes back every change you have not kept" in bold[1]
    quick_reference = Path("docs/QUICK-REFERENCE.md").read_text(encoding="utf-8")
    assert "| Keep Copilot's change |" in quick_reference
    assert "choose **Local**" in quick_reference


def test_template_ships_no_presenter_material() -> None:
    """Owner, 23 October 2026: presenter notes and tools live in the private final-workshop-david/."""
    for path in ("docs/FACILITATOR.md", "docs/AGENDA.md", "docs/PREREQS.md", "docs/REFERENCES.md",
                 "docs/RESEARCH.md", "docs/DAY-2-TOOLS.md", "post-workshop", "travel", ".github/prompts",
                 ".github/skills/workshop-reset", ".github/skills/workshop-rehearsal",
                 ".github/skills/visual-brief", "labs/00-setup", "labs/05-dataverse-app",
                 "labs/07-automations-hooks", "rehearsal/README.md", "infra/README.md",
                 ".devcontainer/README.md"):
        assert not Path(path).exists(), path
    # Attendees write their own agents on Days 3 and 4. Owner, 23 October 2026: the only agent
    # shipped is the blank GenericAgent. Monday's demo proves the guardrail: it cannot reach the
    # internet, then "execute" is added by hand and it can. It ships able only to read, and
    # nothing picks it by itself.
    agents = [path.name for path in Path(".github/agents").glob("*.agent.md")]
    assert agents == ["generic-agent.agent.md"], agents
    placeholder = Path(".github/agents/generic-agent.agent.md").read_text(encoding="utf-8")
    header = yaml.safe_load(placeholder.split("---", 2)[1])
    assert header["name"] == "GenericAgent" and "joke" not in placeholder.lower()
    assert header["tools"] == ["read", "search"]
    assert header["disable-model-invocation"] is True
    for ignore in (".gitignore", ".dockerignore"):
        assert "/final-workshop-david/" in Path(ignore).read_text(encoding="utf-8").splitlines()


def test_hand_over_offers_ideas_for_every_category() -> None:
    """A beginner who does not know what to ask for must be shown concrete options."""
    assets = Path(".github/skills/create-website/assets")
    data = json.loads((assets / "starters.json").read_text(encoding="utf-8"))
    shared = data["any_page_ideas"]
    assert len(shared) >= 4
    assert any("color theme" in idea for idea in shared)
    assert any("tabs" in idea for idea in shared)
    seen: set[str] = set()
    for starter in data["starters"]:
        ideas = starter["later_ideas"]
        assert all(idea.strip() and idea[0].isupper() for idea in ideas)
        assert len(set(ideas)) == len(ideas)
        # Each category needs its own wording, not one list repeated four times.
        assert not seen & set(ideas)
        seen |= set(ideas)
        assert not set(ideas) & set(shared)
    skill = Path(".github/skills/create-website/SKILL.md").read_text(encoding="utf-8")
    assert "any_page_ideas" in skill and "later_ideas" in skill
    assert "Suggest, never build" in skill


def test_guided_starter_figures_and_shared_assets() -> None:
    """Every starter has a tested blueprint, matching sample data, a checkable count, and local art."""
    assets = Path(".github/skills/create-website/assets")
    data = json.loads((assets / "starters.json").read_text(encoding="utf-8"))
    assert data["source_mode"] == "synthetic_workshop"
    assert [starter["id"] for starter in data["starters"]] == ["project", "calendar", "ideas", "weather", "map", "photo"]
    assert data["default"] == "project"
    allowed_urls = {"http://www.w3.org/2000/svg", "https://api.open-meteo.com/v1/forecast",
                    "https://geocoding-api.open-meteo.com/v1/search",
                    "https://archive-api.open-meteo.com/v1/archive"}
    for starter in data["starters"]:
        assert starter["summary"] and starter["manual_check"]
        assert len(starter["later_ideas"]) >= 4
        blueprint = assets / "blueprints" / starter["id"]
        sample = json.loads((blueprint / starter["data_file"]).read_text(encoding="utf-8"))
        key = "cities" if starter["id"] == "weather" else "items"
        assert len(sample[key]) == starter["expected"]["item_count"]
        if "done_count" in starter["expected"]:
            assert sum(item["done"] for item in sample["items"]) == starter["expected"]["done_count"]
        page = (blueprint / "index.html").read_text(encoding="utf-8")
        assert f"store('{starter['storage_key']}')" in page
        assert f"'{starter['data_file']}'" in page
        assert '<script src="js/workshop.js"></script>' in page
        assert '<link rel="stylesheet" href="css/workshop.css">' in page
        assert "<title>My " in page and "logo-mark" in page
        assert "innerHTML" not in page
        # Places name the page that supports their description: a link to read, never a request.
        sources = {item["source"] for item in sample[key] if isinstance(item, dict) and item.get("source")}
        assert set(re.findall(r"https?://[^`'\"?$\s]+", page)) <= allowed_urls | sources
        for art in re.findall(r'src="(art/[^"]+)"', page):
            assert (assets / art).is_file(), art
    kit = (assets / "js/workshop.js").read_text(encoding="utf-8")
    assert "innerHTML" not in kit and "eval(" not in kit and not re.search(r"https?://", kit)
    for art in (assets / "art").glob("*.svg"):
        root = ET.parse(art).getroot()
        assert root.tag == "{http://www.w3.org/2000/svg}svg", art
        assert not any(element.tag.endswith("script") for element in root.iter()), art
        text = art.read_text(encoding="utf-8")
        assert "http" not in text.replace("http://www.w3.org/2000/svg", ""), art
        assert "prefers-reduced-motion: reduce" in text, art
    weekdays = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
    assert weekdays <= {art.stem for art in (assets / "art").glob("*.svg")}
    assert sum(art.stat().st_size for art in (assets / "art").glob("*.svg")) < 24 * 1024
    css = (assets / "css/workshop.css").read_text(encoding="utf-8")
    for resource in re.findall(r'url\("([^"]+)"\)', css):
        assert not urlsplit(resource).scheme
        assert (assets / "css" / resource).is_file()
    assert "prefers-reduced-motion" in css
    assert ":focus-visible" in css
    assert "color-scheme: light" in css
    # The Website preview's VS Code webview styles body with the editor's colors, font and padding.
    body_rule = re.search(r"^body \{([^}]*)\}", css, re.MULTILINE).group(1)
    for setting in ("color: var(--ink)", "padding: 0", "font: inherit", "background: var(--canvas)"):
        assert setting in body_rule
    assert len(css.encode("utf-8")) < 16 * 1024
    assert "@import" not in css
    assert "prefers-color-scheme: dark" not in css
    assert "letter-spacing: 0" in css
    assert "SIL OPEN FONT LICENSE" in (assets / "fonts/OFL.txt").read_text(encoding="utf-8")
    font = (assets / "fonts/source-sans-3-latin.woff2").read_bytes()
    assert font[:4] == b"wOF2"
    assert len(font) < 40 * 1024


def test_own_idea_patterns_are_tested_and_stay_out_of_the_first_question() -> None:
    """The Request Tracker and Team Dashboard back up common business ideas without lengthening Monday's menu."""
    assets = Path(".github/skills/create-website/assets")
    data = json.loads((assets / "starters.json").read_text(encoding="utf-8"))
    patterns = {pattern["id"]: pattern for pattern in data["idea_patterns"]}
    assert list(patterns) == ["tracker", "dashboard", "game"]
    starter_ideas = {idea for starter in data["starters"] for idea in starter["later_ideas"]}
    for pattern in patterns.values():
        assert pattern["summary"] and pattern["suits"] and pattern["try_it"].startswith("Try it:")
        assert pattern["manual_check"] and len(pattern["later_ideas"]) >= 4
        assert len(set(pattern["later_ideas"])) == len(pattern["later_ideas"])
        assert not set(pattern["later_ideas"]) & (starter_ideas | set(data["any_page_ideas"]))
        blueprint = assets / "blueprints" / pattern["id"]
        page = (blueprint / "index.html").read_text(encoding="utf-8")
        assert f"store('{pattern['storage_key']}')" in page and f"'{pattern['data_file']}'" in page
        assert '<script src="js/workshop.js"></script>' in page
        assert '<link rel="stylesheet" href="css/workshop.css">' in page
        assert "<title>My " in page and "logo-mark" in page and "innerHTML" not in page
        assert not re.search(r"https?://", page), "own-idea patterns stay offline"
        for art in re.findall(r'src="(art/[^"]+)"', page):
            assert (assets / art).is_file(), art

    tracker = json.loads((assets / "blueprints/tracker/data/requests.json").read_text(encoding="utf-8"))
    expected = patterns["tracker"]["expected"]
    last = tracker["columns"][-1]
    assert len(tracker["items"]) == expected["item_count"]
    assert sum(item["status"] == last for item in tracker["items"]) == expected["done_count"]
    late = [item for item in tracker["items"] if item["status"] != last and item["dueInDays"] < 0]
    assert len(late) == expected["overdue_count"]
    assert {item["status"] for item in tracker["items"]} <= set(tracker["columns"])
    assert {item["type"] for item in tracker["items"]} <= set(tracker["types"])

    metrics = json.loads((assets / "blueprints/dashboard/data/metrics.json").read_text(encoding="utf-8"))
    expected = patterns["dashboard"]["expected"]
    groups = metrics["groups"]
    assert len(metrics["items"]) == expected["item_count"]
    assert all(len(item["values"]) == len(groups) for item in metrics["items"])
    totals = {group: sum(item["values"][index] for item in metrics["items"]) for index, group in enumerate(groups)}
    assert sum(totals.values()) == expected["total"]
    assert max(totals, key=totals.get) == expected["top_group"] and totals["Northeast"] == expected["top_total"]
    assert "2,778" in patterns["dashboard"]["manual_check"] and f"{totals['South']}" in patterns["dashboard"]["manual_check"]
    dashboard = (assets / "blueprints/dashboard/index.html").read_text(encoding="utf-8")
    assert '<script src="js/vendor/echarts.min.js"></script>' in dashboard
    assert '<script src="js/workshop-charts.js"></script>' in dashboard and "chart('#trend-chart'" in dashboard

    skill = Path(".github/skills/create-website/SKILL.md").read_text(encoding="utf-8")
    first_question = skill.split("## 2. Build It Straight Away")[0]
    assert "Tracker" not in first_question and "Dashboard" not in first_question
    for name in ("tracker", "dashboard"):
        assert f"./assets/blueprints/{name}/index.html" in skill
    assert "idea_patterns" in skill and "question for IT" in skill


def test_lab_chase_game_is_playable_original_and_licensed() -> None:
    """The game pattern's maze works, its library is the approved unchanged three.js, and nothing is borrowed."""
    assets = Path(".github/skills/create-website/assets")
    data = json.loads((assets / "starters.json").read_text(encoding="utf-8"))
    pattern = next(item for item in data["idea_patterns"] if item["id"] == "game")
    game = json.loads((assets / "blueprints/game/data/game.json").read_text(encoding="utf-8"))
    maze = game["maze"]
    assert len({len(row) for row in maze}) == 1 and set("".join(maze)) <= set("#.oSMI")
    assert all(ch == "#" for ch in maze[0] + maze[-1]) and all(row[0] == row[-1] == "#" for row in maze)
    cells = {(c, r): ch for r, row in enumerate(maze) for c, ch in enumerate(row)}
    starts = [cell for cell, ch in cells.items() if ch == "S"]
    assert len(starts) == 1
    reachable, queue = {starts[0]}, [starts[0]]
    while queue:
        c, r = queue.pop()
        for step in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            near = (c + step[0], r + step[1])
            if cells.get(near, "#") not in "#I" and near not in reachable:
                reachable.add(near)
                queue.append(near)
    walkable = {cell for cell, ch in cells.items() if ch not in "#I"}
    assert reachable == walkable, "every data point, coffee and molecule start can be reached"
    expected = pattern["expected"]
    assert sum(ch == "." for ch in cells.values()) == expected["dots"]
    assert sum(ch == "o" for ch in cells.values()) == expected["coffee"]
    assert sum(ch == "M" for ch in cells.values()) >= 2 and sum(ch == "I" for ch in cells.values()) == 3
    assert len(game["items"]) == expected["item_count"]
    assert f"{expected['dots']} data points" in pattern["manual_check"]
    assert all(game["lines"][key] for key in ("start", "molecule", "caught", "coffee", "declined", "level", "over"))

    page = (assets / "blueprints/game/index.html").read_text(encoding="utf-8")
    assert "import * as THREE from './js/vendor/three.module.js'" in page
    # The scientist runs only while a direction is held, and stops when it is let go.
    assert "if (steering()) advance(scientist, dt)" in page
    assert "window.addEventListener('keyup'" in page and "window.addEventListener('blur', releaseAll)" in page
    assert "'pointerup', 'pointercancel', 'lostpointercapture'" in page
    assert "let go to stop" in page and "let go" in pattern["manual_check"]
    assert "lives: 3" in page and "prefers-reduced-motion" in page
    assert "cannot draw 3D" in page, "a browser without 3D gets a plain message"
    text = (page + json.dumps(game)).lower()
    for borrowed in ("pac-man", "pacman", "pac man", "namco", "blinky", "inky", "clyde"):
        assert borrowed not in text, borrowed

    readme = (assets / "README.md").read_text(encoding="utf-8")
    for name in ("three.module.js", "three.core.js"):
        library = (assets / "game" / name).read_bytes()
        assert hashlib.sha256(library).hexdigest() in readme, name
        source = library.decode("utf-8")
        assert "eval(" not in source and "new Function" not in source, name
    assert "from './three.core.js'" in (assets / "game/three.module.js").read_text(encoding="utf-8")
    licence = (assets / "game/THREE-LICENSE.md").read_text(encoding="utf-8")
    assert "The MIT License" in licence and "three@0.186.1" in licence
    assert "assets/game/*.js -text -diff" in Path(".gitattributes").read_text(encoding="utf-8")
    skill = Path(".github/skills/create-website/SKILL.md").read_text(encoding="utf-8")
    assert "./assets/game/three.module.js" in skill and "site/THREE-LICENSE.md" in skill
    assert "never use a real game's name" in skill


def test_authoring_labs_do_not_embed_finished_customizations() -> None:
    """Give learners requirements rather than complete agent, skill, or hook files."""
    for path in active_lab_guides():
        text = path.read_text(encoding="utf-8")
        for body in re.findall(r"```markdown\n(.*?)\n[ \t]*```", text, re.DOTALL):
            parts = body.strip().split("---", 2)
            assert len(parts) != 3 or not parts[2].strip(), path
        for body in re.findall(r"```json\n(.*?)\n[ \t]*```", text, re.DOTALL):
            assert "hooks" not in json.loads(body), path


def test_labs_have_completion_checks_and_optional_work() -> None:
    """Attendees need an observable finish and a separate early-finisher path."""
    for path in active_lab_guides():
        text = path.read_text(encoding="utf-8")
        assert "**Done when:**" in text, path
        assert "## Optional extras" in text, path


def test_labs_link_official_references() -> None:
    """Each lab needs usable lookup links alongside its required and optional tasks."""
    official_hosts = {"docs.github.com", "code.visualstudio.com", "learn.microsoft.com"}
    for path in active_lab_guides():
        text = path.read_text(encoding="utf-8")
        assert "## Official References\n" in text, path
        section = text.split("## Official References\n", 1)[1]
        links = [urlsplit(target) for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", section)]
        assert any(link.scheme == "https" and link.hostname in official_hosts for link in links), (
            path
        )


def heading_anchors(document: Path) -> set[str]:
    """Return the GitHub-style anchors generated by a Markdown file's headings."""
    anchors = set()
    for heading in re.findall(r"^#{1,6}\s+(.*)$", document.read_text(encoding="utf-8"), re.M):
        text = re.sub(r"[`*_]", "", heading).strip()
        anchors.add(re.sub(r"[^\w\s-]", "", text.lower()).strip().replace(" ", "-"))
    return anchors


def test_local_document_links_resolve() -> None:
    """Check the simple relative links used by the workshop documentation."""
    files = [Path("README.md"), Path("AGENTS.md")]
    for directory in ("docs", ".github", "src", "checks", "site"):
        files.extend(
            path
            for path in Path(directory).rglob("*.md")
            if not {"results", "output"}.intersection(path.parts)
        )
    for path in files:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            link = urlsplit(target)
            if link.scheme or link.netloc or not link.path:
                continue
            document = path.parent / unquote(link.path)
            assert document.exists(), f"{path}: {target}"
            if link.fragment and document.suffix == ".md":
                assert link.fragment.lower() in heading_anchors(document), f"{path}: {target}"


def test_post_workshop_code_is_preserved() -> None:
    """The Dataverse and vendor code stays maintained; its guides live with the presenter."""
    for path in (
        "app/main.py",
        "src/vendor_assurance/dataverse.py",
        "scripts/dataverse_provision.py",
        "scripts/dataverse_app_user.py",
        "scripts/dataverse_seed.py",
        "scripts/audit_hook.py",
        ".github/workflows/deploy.yml",
    ):
        assert Path(path).is_file(), path


def test_tuesday_protects_own_idea_building() -> None:
    """The meeting refit removes required integration and tooling tasks from beginner Day 2."""
    guide = Path("docs/DAY-2.md").read_text(encoding="utf-8")
    route = guide.split("## Today's Route", 1)[1].split("\n## ", 1)[0]
    assert re.search(r"\| 09:00-09:30 +\| David:", route) and re.search(r"\| 09:30-10:30 +\| Jackie:", route)
    assert "Lab 05" not in route and "Guided tools" not in route
    assert "No database, login, API keys" in guide
    assert guide.count("Run `/create-website`") == 1
    assert "not completion gates" in guide
    assert "helpers work with you at the tables" in guide
    assert "site/ideas/" in guide and "prepared repository" not in guide
    assert "The presenter" not in guide
    quick_reference = Path("docs/QUICK-REFERENCE.md").read_text(encoding="utf-8")
    assert "Open Preview" in quick_reference
    assert "Do not delete accounts" in quick_reference


def test_lab_guides_have_one_current_title() -> None:
    """Catch accidentally retained old introductions alongside replacement instructions."""
    for path in active_lab_guides():
        assert len(re.findall(r"^# ", path.read_text(encoding="utf-8"), re.MULTILINE)) == 1, path


def day_route(guide: str) -> list[str]:
    """Return the elapsed or clock times in a day guide's route table."""
    text = Path("docs", guide).read_text(encoding="utf-8")
    route = text.split("## Today's Route", 1)[1].split("\n## ", 1)[0]
    return re.findall(r"\| (\d\d:\d\d-\d\d:\d\d) +\|", route)


def quoted_flat(text: str) -> str:
    """One line of guide text, with prompt quotes unwrapped even when they sit inside a list."""
    return " ".join(re.sub(r"\n\s*> ?", "\n", text).split())


def test_day_three_guide_follows_the_slides_on_the_learners_own_page() -> None:
    """Wednesday: tickets on a board, a learner-written skill and agent add criteria, one ticket is built and tested."""
    guide = Path("docs/DAY-3.md").read_text(encoding="utf-8")
    assert guide.startswith("# Day 3: VS Code and a Requirements Agent")
    assert day_route("DAY-3.md") == SLIDE_SLOTS
    flat = quoted_flat(guide)
    assert "/login" in guide and "Never paste a password or token" in guide
    assert ".github/agents/user-requirements.agent.md" in flat and "`name: user-requirements`" in flat
    # 21 October refit: the building blocks, a GitHub tool through MCP, and the learner's own skill.
    assert ".github/skills/user-stories/SKILL.md" in flat and "`name: user-stories`" in flat
    assert "uses the user-stories skill" in flat and "Use the GitHub tools" in flat and "**MCP**" in guide
    assert "Given ..., when ..., then ..." in flat and "**Your own idea.**" in guide
    # Later on 21 October: requirements live in tickets on a project board, approved by moving to Todo.
    assert "**Issues > New issue**" in flat and "**Requirement**" in flat
    assert "**Projects > New project**" in flat and "**Import items from repository**" in flat
    assert "the `gh issue edit` command" in flat and "Only when I say yes" in flat
    # Rehearsed 22 October 2026: a short prompt let the agent rebuild the whole ticket inside a
    # quoted shell argument and lose the learner's words; the raw read and stdin write keep them.
    assert "`gh issue view NUMBER --json body --jq .body`" in flat
    assert "`gh issue edit NUMBER --body-file -` through standard input" in flat
    assert "whether my own words under What I want are unchanged" in flat
    assert "your own words under What I want are unchanged" in flat
    assert "drag its card into **Todo**" in flat and "If Copilot says it may not update the ticket" in flat
    assert "`Mark urgent tasks. Closes #1`" in flat and "moved to **Done**" in flat
    # Monday's 11:45 check already builds "hide finished tasks", so Day 3 needs a new example.
    assert "Hide finished" not in guide
    # 21 October review: per-attendee boards, Tuesday's wishes, GxP wording, and a requirements list.
    assert "`<your username> website`" in flat and "repository's **Projects** tab" in flat
    assert "under **Next** in `site/README.md`" in flat and "It is not GxP validation" in flat
    assert "add a section called requirements" in flat.lower() and "validated README" in flat
    route = guide.split("## 1. Tickets, Board, and Tools", 1)[1].split("## 2.", 1)[0]
    assert "Meet the building blocks" not in route, "the building blocks open the 00:50 block"
    assert "**Meet the building blocks.**" in guide.split("## 2. Build Your User Requirements Agent", 1)[1]
    day2 = " ".join(Path("docs/DAY-2.md").read_text(encoding="utf-8").split())
    assert "under a heading called **Next**" in day2 and "become your first tickets" in day2
    assert "Copilot's browser try" not in day2
    assert "type `/exit`, then `copilot`" in flat, "the CLI loads new agents when it starts"
    assert "pytest checks" in guide and "from website import Page" in guide
    assert "**Break it on purpose:**" in guide and "How to build and run" in guide
    for target in ("DAY-4.md",):
        assert target in guide
    # The template ships the test helper, prompts and ticket template, never the finished agent, skill, or tests.
    assert not Path(".github/skills/user-stories").exists()
    assert not Path(".github/agents/user-requirements.agent.md").exists()
    assert not list(Path("checks").glob("test_*.py"))
    assert Path("checks/website.py").is_file() and Path("checks/README.md").is_file()
    assert "test_issue1.py" in Path("checks/README.md").read_text(encoding="utf-8")
    # Attendees read only their own steps; technical helper notes stay with the presenter.
    assert "Helper Preparation" not in guide
    assert "setup.sh browser" not in guide and "uvicorn" not in guide and "seccomp" not in guide


def test_days_three_to_five_follow_the_final_slides() -> None:
    """Owner-approved 20 October: requirements agent, cloud agents, and CI/CD, four hours each."""
    titles = {3: "VS Code and a Requirements Agent", 4: "GitHub Copilot Cloud Agents",
              5: "CI/CD with GitHub Actions"}
    guides = {3: "DAY-3.md", 4: "DAY-4.md", 5: "DAY-5.md"}
    for number, guide in guides.items():
        text = Path("docs", guide).read_text(encoding="utf-8")
        assert text.startswith(f"# Day {number}: {titles[number]}")
        assert day_route(guide) == SLIDE_SLOTS, guide
        assert "**Done when:**" in text and "## Optional extras" in text, guide
        assert "## Official References\n" in text, guide
        assert "made up" in text, guide
    day4 = quoted_flat(Path("docs/DAY-4.md").read_text(encoding="utf-8"))
    assert "pick a ticket in **Todo**" in day4 and "labs/" not in day4
    assert "drag the ticket into **In Progress**" in day4 and "moved to **Done**" in day4
    assert ".github/agents/code-review.agent.md" in day4 and "reviews/pr-NUMBER.md" in day4
    assert "**Confirmed** or **Not a problem**" in day4 and "@copilot" in day4
    assert "It never changes other files, comments on GitHub, or merges." in day4
    # 21 October refit: a feature-branch ruleset and a versioned pipeline. Copilot code review stays
    # off (owner decision, 21 October): the learner's own Code Review agent does the reviewing.
    assert "**Require a pull request before merging**, with required approvals left at **0**" in day4
    assert "Leave the bypass list empty" in day4
    assert "Copilot code review" not in day4 and "re-request" not in day4
    assert "**Joining today?**" in day4 and "**An agent that starts by itself:**" in day4
    assert "repository's **Projects** tab" in day4
    assert "`# version: 1.0.${{ github.run_number }}`" in day4 and "**Version 1.0.**" in day4
    assert ".github/instructions/review.instructions.md" in day4 and "`applyTo: \"site/**\"`" in day4
    day5 = " ".join(Path("docs/DAY-5.md").read_text(encoding="utf-8").split())
    starters = ("check-my-website.yml", "deploy-feature-slot.yml", "publish-website-with-approval.yml")
    assert sorted(path.name for path in Path(".github/workflow-starters").iterdir()) == list(starters)
    for starter in starters:
        assert f".github/workflow-starters/{starter}" in day5
    assert "change `contents: write` to `contents: read`" in day5
    assert "**Required reviewers**" in day5 and "**Approve and deploy**" in day5
    # Owner, 22 October: Copilot's ticket is tried in a feature slot, then approved into production.
    # Rehearsed 22 October: GitHub asks twice for Copilot's pull requests, with these labels.
    assert "**Assign to Agent**" in day5 and "**Approve workflows to run**" in day5
    assert "**Approve and run**" in day5 and "**View deployment**" in day5
    assert "name it `production`" in day5 and "plus `-feature`" in day5 and "`training`" not in day5
    assert "python3 scripts/smoke_test.py" in day5 and "select **Revert**" in day5
    assert "**Require status checks to pass**" in day5 and "**UI check**" in day5
    assert "**home-phone.png**" in day5 and "900 pixels wide" in day5
    assert "No password, key, or Azure sign-in" in day5 and "HANDOFF.md" in day5
    assert "**Joining today?**" in day5 and "Copilot reviews" not in day5
    # The handoff routes back into Novo's own platforms and its validation process.
    assert "Novo's own GitHub Enterprise" in day5 and "Power Apps code app" in day5
    assert "Novo's validation process" in day5
    assert not Path(".github/workflows/check-my-website.yml").exists()


def test_cloud_agent_lab_delegates_an_approved_ticket() -> None:
    """Day 4's 40-minute delegation block: an approved ticket from the board, with human review kept."""
    day4 = Path("docs/DAY-4.md").read_text(encoding="utf-8")
    cloud = " ".join(day4.split("\n## 3. Delegate an Approved Ticket", 1)[1].split("\n## ", 1)[0].split())
    assert "**00:50-01:30.** This is the delegation lab" in cloud
    assert "pick a ticket in **Todo**" in cloud and "Nothing changes until you merge" in cloud
    assert "**Assignees > Copilot**" in cloud and "Never wait idle for it" in cloud
    assert "**Requirement**" in day4 and "Website change for Copilot" in day4
    assert "Copilot code review" not in day4 and "practised" not in day4
    ticket = Path(".github/ISSUE_TEMPLATE/requirement.md").read_text(encoding="utf-8")
    metadata = yaml.safe_load(ticket.split("---", 2)[1])
    assert metadata["name"] == "Requirement" and metadata["labels"] == ["enhancement"]
    for section in ("## What I want", "## Which page", "## User story", "## Acceptance criteria", "## Only change"):
        assert section in ticket, section
    assert "site/index.html" in ticket and "fictional" in ticket
    # One ticket template replaces the earlier story and idea templates.
    assert not Path(".github/ISSUE_TEMPLATE/user-story.md").exists()
    assert not Path(".github/ISSUE_TEMPLATE/idea.md").exists()
    template = Path(".github/ISSUE_TEMPLATE/website-change.md").read_text(encoding="utf-8")
    metadata = yaml.safe_load(template.split("---", 2)[1])
    assert metadata["name"] == "Website change for Copilot"
    assert "site/index.html" in template and "fictional" in template


def test_quick_commands_bring_template_fixes_safely() -> None:
    """Owner, 25 October 2026: one prompts page replaces the extras, led by the template-fixes prompt."""
    commands = " ".join(re.sub(r"\n\s*> ?", "\n", Path("docs/QUICK-COMMANDS.md").read_text(encoding="utf-8")).split())
    fixes = commands.split("## Fetch Updates From the Main Workshop Repository", 1)[1].split("## ", 1)[0]
    assert "fetch the latest updates from the main workshop repository" in fixes.lower()
    assert "upstream" in fixes and "agentic-dev-labs/copilot-hackathon-template" in fixes
    assert "run python3 scripts/update_from_template.py" in fixes
    assert "Create a new branch called workshop-updates" in fixes and "From Thursday on" in fixes
    assert "never force-push" in commands and "None of these ever force-push" in commands
    for command in ("/create-website", "/start-website", "/stop-website", "/add-chart", "/add-chat",
                    "/publish-website", "pytest checks"):
        assert f"`{command}" in commands, command
    assert Path("scripts/update_from_template.py").is_file()
    quick_reference = Path("docs/QUICK-REFERENCE.md").read_text(encoding="utf-8")
    assert "](QUICK-COMMANDS.md)" in quick_reference and "update_from_template" not in quick_reference
    # The read-only GitHub server stays the repository's only MCP server.
    assert "https://api.githubcopilot.com/mcp/readonly" in Path(".vscode/mcp.json").read_text(encoding="utf-8")
    assert Path(".github/skills/add-chat/SKILL.md").is_file()


def test_attendee_pages_stand_alone_for_first_time_users() -> None:
    """Beginners never need the presenter's pages, which live outside the template."""
    days = [Path(f"docs/DAY-{day}.md") for day in range(1, 6)]
    for path in [Path("README.md"), Path("docs/QUICK-REFERENCE.md"), Path("docs/QUICK-COMMANDS.md"),
                 *active_lab_guides()]:
        text = path.read_text(encoding="utf-8")
        for presenter_page in ("AGENDA.md", "FACILITATOR.md", "REFERENCES.md", "PREREQS.md"):
            assert presenter_page not in text, (path, presenter_page)
    for path in days:
        route = path.read_text(encoding="utf-8").split("## Today's Route", 1)[1].split("\n## ", 1)[0]
        # Days 1-2 use clock times; Days 3-5 use elapsed times, as on the final slides.
        assert "| 10:30-10:45 | Break" in route or "| 01:30-01:45 | Break" in route, path
    words = " ".join(Path("docs/DAY-1.md").read_text(encoding="utf-8").split())
    assert "| Ask | In Chat: Copilot only answers." in words
    assert "| Agent | In Chat: Copilot can change your files." in words
    assert sorted(path.name for path in Path("docs").glob("*.md")) == [
        "DAY-1.md", "DAY-2.md", "DAY-3.md", "DAY-4.md", "DAY-5.md", "QUICK-COMMANDS.md", "QUICK-REFERENCE.md"
    ], "attendees get one guide per day, the quick reference, and the quick commands"
