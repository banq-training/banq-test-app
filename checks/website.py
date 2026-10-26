"""Read a workshop web page so a learner's test can check it in plain words.

Tests check what is written in the files: titles, buttons, sample data, and that every
picture, style and script the page uses is really there. Clicking and counting on the page
stays a manual check in the Website preview.

Example, in checks/test_my_page.py:

    from website import Page

    def test_page_has_a_hide_button():
        page = Page("site/index.html")
        assert page.has_button("Hide finished tasks")
"""

import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
_SKIPPED_TEXT = {"script", "style", "template"}


class _Reader(HTMLParser):
    """Collect the parts of a page that a learner can see or that it loads."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.headings: list[str] = []
        self.buttons: list[str] = []
        self.files: list[str] = []
        self.words: list[str] = []
        self.scripts: list[str] = []
        self._open: list[str] = []
        self._button_text: list[str] | None = None
        self._heading_text: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value or "" for name, value in attrs}
        self._open.append(tag)
        if tag == "button":
            self._button_text = []
            if values.get("aria-label"):
                self.buttons.append(values["aria-label"])
        if tag in {"h1", "h2", "h3"}:
            self._heading_text = []
        for name in ("src", "href"):
            if values.get(name) and not (tag == "a" and name == "href"):
                self.files.append(values[name])

    def handle_endtag(self, tag: str) -> None:
        if tag == "button" and self._button_text is not None:
            text = " ".join("".join(self._button_text).split())
            if text:
                self.buttons.append(text)
            self._button_text = None
        if tag in {"h1", "h2", "h3"} and self._heading_text is not None:
            self.headings.append(" ".join("".join(self._heading_text).split()))
            self._heading_text = None
        if tag in self._open:
            while self._open and self._open.pop() != tag:
                pass

    def handle_data(self, data: str) -> None:
        current = self._open[-1] if self._open else ""
        if current == "script":
            self.scripts.append(data)
            return
        if current == "title":
            self.title += data
        if current in _SKIPPED_TEXT:
            return
        self.words.append(data)
        if self._button_text is not None:
            self._button_text.append(data)
        if self._heading_text is not None:
            self._heading_text.append(data)


class Page:
    """One HTML page under site/, read from disk."""

    def __init__(self, path: str = "site/index.html") -> None:
        self.path = (ROOT / path).resolve()
        self.html = self.path.read_text(encoding="utf-8")
        reader = _Reader()
        reader.feed(self.html)
        self.title = " ".join(reader.title.split())
        self.headings = reader.headings
        self.buttons = reader.buttons
        self.text = " ".join(" ".join(reader.words).split())
        self.script = "\n".join(reader.scripts)
        self._files = reader.files

    def has_button(self, label: str) -> bool:
        """True when a button shows these words or is named them for screen readers."""
        wanted = label.casefold()
        return any(wanted in button.casefold() for button in self.buttons)

    def shows(self, words: str) -> bool:
        """True when these words are in the page's visible text or headings."""
        return words.casefold() in self.text.casefold()

    def data(self, relative: str) -> dict | list:
        """Load a JSON file next to the page, such as data/tasks.json."""
        return json.loads((self.path.parent / relative).read_text(encoding="utf-8"))

    def local_files(self) -> list[str]:
        """Every picture, style, script and font address the page loads from its own folder."""
        local = []
        for address in self._files:
            parts = urlsplit(address)
            if parts.scheme or parts.netloc or address.startswith(("#", "data:")):
                continue
            local.append(parts.path)
        return local

    def missing_files(self) -> list[str]:
        """Addresses the page uses that do not exist, so the published page would break."""
        return [name for name in self.local_files() if not (self.path.parent / name).is_file()]
