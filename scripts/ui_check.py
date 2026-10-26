"""Open the website in a real browser on a desktop and a phone screen, check it, and save screenshots.

Day 5's UI check runs this in GitHub Actions, after starting the website on the runner:

    uv run --with playwright==1.64.0 python scripts/ui_check.py http://127.0.0.1:8000 --out ui-check

It opens the first page and up to five own-idea pages under site/ideas/. On each screen it checks
that the page opens with a title and a visible main heading, shows no errors in the browser
console, loads all of its own files, gives every visible button a name, and fits a phone screen
without sideways scrolling. It saves a full-page screenshot of each, writes a table to the
workflow summary, and exits with 1 when any check failed. It only reads the website.

The browser cannot start inside a Codespace, so this check runs in GitHub Actions only. In the
Codespace, check the page yourself in the Website preview.
"""

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlsplit

SITE = Path(__file__).resolve().parents[1] / "site"
MAX_IDEA_PAGES = 5
SCREENS: dict[str, dict] = {
    "desktop": {"viewport": {"width": 1280, "height": 800}},
    "phone": {"viewport": {"width": 390, "height": 844}, "is_mobile": True, "has_touch": True},
}
SETTLE_MILLISECONDS = 1200
TIMEOUT_MILLISECONDS = 30_000
LONGEST_DETAIL = 160
# Software graphics, so 3D pages (charts, the Lab Chase game) draw on a runner without a graphics
# card. The browser sandbox stays on: run() asks for it, because Playwright otherwise starts
# Chromium with --no-sandbox.
BROWSER_ARGS = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
# Browsers ask for /favicon.ico by themselves, and a workshop page does not need one. The publisher
# writes /version.json only when it releases (Day 4), so a footer that shows the version asks for
# it here in vain and falls back to "Preview".
IGNORED_PATHS = {"/favicon.ico", "/version.json"}
# Visible buttons without words, a screen-reader label, or a tooltip.
UNNAMED_BUTTONS = """() => [...document.querySelectorAll('button')].filter((button) => {
  const shown = button.getClientRects().length > 0 && getComputedStyle(button).visibility !== 'hidden';
  const name = (button.innerText || '').trim() || button.getAttribute('aria-label')
    || button.getAttribute('title') || button.getAttribute('aria-labelledby');
  return shown && !name;
}).length"""


@dataclass
class ScreenResult:
    """What one page showed on one screen."""

    page: str
    screen: str
    screenshot: str
    problems: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True when every check on this screen passed."""
        return not self.problems


def pages_to_check(site: Path = SITE) -> list[tuple[str, str]]:
    """The first page plus up to five own-idea pages, as (name, address) pairs."""
    pages = [("home", "/")]
    ideas = sorted(path.parent.name for path in site.glob("ideas/*/index.html"))
    pages += [(f"idea-{name}", f"/ideas/{name}/") for name in ideas[:MAX_IDEA_PAGES]]
    return pages


def _short(text: str) -> str:
    """One line of plain text that fits in a table cell."""
    flat = " ".join(str(text).split()).replace("|", "/")
    return flat if len(flat) <= LONGEST_DETAIL else flat[: LONGEST_DETAIL - 3] + "..."


def summary_markdown(results: list[ScreenResult]) -> str:
    """A table for the workflow summary: one row per page and screen."""
    rows = ["### UI check", "", "| Page | Screen | Result | What to look at |", "| --- | --- | --- | --- |"]
    for result in results:
        detail = "; ".join(_short(problem) for problem in result.problems) or "Every check passed"
        rows.append(f"| {result.page} | {result.screen} | {'Pass' if result.passed else 'Fail'} | {detail} |")
    failed = sum(not result.passed for result in results)
    rows += ["", f"{len(results) - failed} passed, {failed} failed. Screenshots: open **Artifacts** "
             "at the bottom of this run's summary page, for example **home-phone.png**."]
    return "\n".join(rows) + "\n"


def check_screen(browser, base: str, name: str, path: str, screen: str, out: Path) -> ScreenResult:
    """Open one page on one screen, run every check, and save a full-page screenshot."""
    from playwright.sync_api import Error as PlaywrightError

    url = urljoin(base.rstrip("/") + "/", path.lstrip("/"))
    own_site = urlsplit(url).netloc
    shot = out / f"{name}-{screen}.png"
    result = ScreenResult(name, screen, shot.name)
    errors: list[str] = []
    missing: dict[str, str] = {}

    def note_console(message) -> None:
        # Missing files are reported once, under "Files that did not load".
        if message.type == "error" and not message.text.startswith("Failed to load resource"):
            errors.append(message.text)

    def note_response(response) -> None:
        address = urlsplit(response.url)
        if address.netloc == own_site and response.status >= 400 and address.path not in IGNORED_PATHS:
            missing.setdefault(address.path, f"HTTP {response.status}")

    def note_failure(request) -> None:
        address = urlsplit(request.url)
        if address.netloc == own_site and address.path not in IGNORED_PATHS:
            missing.setdefault(address.path, "did not load")

    context = browser.new_context(**SCREENS[screen])
    page = context.new_page()
    page.on("console", note_console)
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("response", note_response)
    page.on("requestfailed", note_failure)
    page.on("dialog", lambda dialog: dialog.dismiss())
    try:
        response = page.goto(url, wait_until="networkidle", timeout=TIMEOUT_MILLISECONDS)
        page.wait_for_timeout(SETTLE_MILLISECONDS)
        if response is None or response.status != 200:
            result.problems.append(f"The page did not open ({response.status if response else 'no answer'})")
        else:
            if not page.title().strip():
                result.problems.append("The page has no title")
            heading = page.locator("h1").first
            if heading.count() == 0 or not heading.is_visible():
                result.problems.append("No visible main heading (h1)")
            unnamed = page.evaluate(UNNAMED_BUTTONS)
            if unnamed:
                result.problems.append(f"{unnamed} button(s) have no name for screen readers")
            if screen == "phone":
                # A phone browser zooms out to fit wide content, so compare with the real screen width.
                width = SCREENS[screen]["viewport"]["width"]
                overflow = page.evaluate("document.documentElement.scrollWidth") - width
                if overflow > 1:
                    result.problems.append(f"Wider than a phone screen by {overflow} pixels")
    except PlaywrightError as error:
        result.problems.append(f"The browser stopped: {str(error).splitlines()[0]}")
    try:
        page.screenshot(path=str(shot), full_page=True)
    except PlaywrightError:
        result.screenshot = ""
    context.close()
    if errors:
        result.problems.append("Browser console errors: " + " / ".join(dict.fromkeys(errors)))
    if missing:
        result.problems.append("Files that did not load: "
                               + ", ".join(f"{path} ({reason})" for path, reason in missing.items()))
    return result


def run(base: str, out: Path, site: Path = SITE) -> list[ScreenResult]:
    """Check every page on every screen in one headless Chromium."""
    from playwright.sync_api import sync_playwright

    out.mkdir(parents=True, exist_ok=True)
    results: list[ScreenResult] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(args=BROWSER_ARGS, chromium_sandbox=True)
        try:
            for name, path in pages_to_check(site):
                for screen in SCREENS:
                    results.append(check_screen(browser, base, name, path, screen, out))
        finally:
            browser.close()
    return results


def main(arguments: list[str] | None = None) -> int:
    """Print the table, add it to the workflow summary, and return the exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("url", help="Where the website runs, such as http://127.0.0.1:8000")
    parser.add_argument("--out", default="ui-check", help="Folder for the screenshots")
    parser.add_argument("--site", default=str(SITE), help="The website folder, to find idea pages")
    options = parser.parse_args(arguments)
    if not (Path(options.site) / "index.html").is_file():
        print("No site/index.html yet, so there is nothing to look at.")
        return 0
    results = run(options.url, Path(options.out), Path(options.site))
    summary = summary_markdown(results)
    print(summary)
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(summary)
    return 1 if any(not result.passed for result in results) else 0


if __name__ == "__main__":
    sys.exit(main())
