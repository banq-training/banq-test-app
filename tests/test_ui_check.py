"""The Day 5 UI check finds the learner's pages, reports plainly, and is wired the same way twice."""

import sys
import types
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import ui_check  # noqa: E402

PINNED = "playwright==1.64.0"


def test_first_page_and_up_to_five_idea_pages_are_checked(tmp_path: Path) -> None:
    """Idea pages come in name order; folders without a page are skipped."""
    site = tmp_path / "site"
    (site / "ideas" / "empty").mkdir(parents=True)
    for name in ("team-lunch", "a-map", "b", "c", "d", "e", "f"):
        (site / "ideas" / name).mkdir()
        (site / "ideas" / name / "index.html").write_text("<html><body></body></html>", encoding="utf-8")
    pages = ui_check.pages_to_check(site)
    assert pages[0] == ("home", "/")
    assert pages[1:] == [("idea-a-map", "/ideas/a-map/"), ("idea-b", "/ideas/b/"), ("idea-c", "/ideas/c/"),
                         ("idea-d", "/ideas/d/"), ("idea-e", "/ideas/e/")]


def test_summary_is_one_readable_row_per_screen() -> None:
    """Long or table-breaking messages stay inside their cell; the totals are honest."""
    results = [
        ui_check.ScreenResult("home", "desktop", "home-desktop.png"),
        ui_check.ScreenResult("home", "phone", "home-phone.png",
                              ["Wider than a phone screen by 12 pixels", "Browser console errors: a | b\n" + "x" * 300]),
    ]
    summary = ui_check.summary_markdown(results)
    assert "| home | desktop | Pass | Every check passed |" in summary
    phone = next(line for line in summary.splitlines() if "| phone |" in line)
    assert phone.count("|") == 5 and "a / b" in phone and phone.endswith("... |")
    assert "1 passed, 1 failed." in summary and "home-phone.png" in summary


def test_no_website_yet_is_not_a_failure(tmp_path: Path, capsys) -> None:
    """Before /create-website there is nothing to open, and no browser is started."""
    assert ui_check.main(["http://127.0.0.1:8000", "--site", str(tmp_path)]) == 0
    assert "nothing to look at" in capsys.readouterr().out


def test_browser_keeps_its_sandbox_and_draws_3d_in_software() -> None:
    """3D pages need software graphics on a runner; the sandbox is never switched off."""
    assert "--no-sandbox" not in ui_check.BROWSER_ARGS
    assert "--use-angle=swiftshader" in ui_check.BROWSER_ARGS
    assert ui_check.SCREENS["phone"]["viewport"]["width"] == 390


def test_browser_is_launched_with_its_sandbox_on(tmp_path: Path, monkeypatch) -> None:
    """Playwright starts Chromium with --no-sandbox unless asked, so the launch must ask."""
    launched: dict = {}

    class Browser:
        def close(self) -> None:
            pass

    class Chromium:
        def launch(self, **options):
            launched.update(options)
            return Browser()

    class Playwright:
        chromium = Chromium()

        def __enter__(self):
            return self

        def __exit__(self, *problem) -> bool:
            return False

    sync_api = types.ModuleType("playwright.sync_api")
    sync_api.sync_playwright = Playwright
    monkeypatch.setitem(sys.modules, "playwright", types.ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api)
    monkeypatch.setattr(ui_check, "check_screen", lambda browser, base, name, path, screen, out:
                        ui_check.ScreenResult(name, screen, f"{name}-{screen}.png"))
    (tmp_path / "site").mkdir()
    results = ui_check.run("http://127.0.0.1:8000", tmp_path / "shots", tmp_path / "site")
    assert launched["chromium_sandbox"] is True
    assert "--no-sandbox" not in launched["args"]
    assert [result.screen for result in results] == ["desktop", "phone"]


def test_version_file_is_expected_to_be_missing_before_release() -> None:
    """Day 4's footer asks for /version.json, which only the publisher writes, at release time."""
    assert "/version.json" in ui_check.IGNORED_PATHS
    assert "/favicon.ico" in ui_check.IGNORED_PATHS


def test_starter_and_template_ci_run_the_same_pinned_check() -> None:
    """The learner's starter keeps viewable screenshots; the template proves the same steps."""
    starter = yaml.load(Path(".github/workflow-starters/check-my-website.yml").read_text(encoding="utf-8"),
                        Loader=yaml.BaseLoader)
    template = yaml.load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    for steps in (starter["jobs"]["ui"]["steps"], template["jobs"]["ui-check"]["steps"]):
        script = "\n".join(step.get("run", "") for step in steps)
        assert f"uv run --with {PINNED} playwright install chromium" in script
        # 22 October 2026: --with-deps fetched 26 MB from Ubuntu's mirror at 47 kB/s, so the UI
        # check took up to 14 minutes; the runner image already has the browser's libraries.
        assert "--with-deps" not in script
        assert f"uv run --with {PINNED} python scripts/ui_check.py http://127.0.0.1:8000 --out ui-check" in script
        assert "uv run uvicorn app.site:app --host 127.0.0.1 --port 8000" in script
        assert "--no-sandbox" not in script
        # Ubuntu 24.04 blocks the user namespaces the sandbox needs until this step allows them.
        allow = "sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0"
        assert allow in script and script.index(allow) < script.index("scripts/ui_check.py")
    uploads = [step for step in starter["jobs"]["ui"]["steps"] if step.get("uses", "").startswith("actions/upload-artifact@")]
    single = {step["with"]["path"] for step in uploads if step["with"].get("archive") == "false"}
    assert single == {"ui-check/home-desktop.png", "ui-check/home-phone.png"}
    assert all(step["if"].startswith("${{ always()") for step in uploads)
    assert starter["jobs"]["ui"]["runs-on"] == "ubuntu-24.04"
    assert set(starter["on"]) == {"workflow_dispatch"}, "still inert until the learner edits it"
