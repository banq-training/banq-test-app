"""Smoke-test a published workshop website in a few seconds.

Usage (from the repository root):

    python3 scripts/smoke_test.py https://<name>.<domain>
    python3 scripts/smoke_test.py https://<name>.<domain> --expect-text "Plan our team week"

It checks that /healthz says ok, prints the live commit, content fingerprint, version and slot,
opens the page, optionally looks for words on it, and loads every picture, style and script the
page uses. It exits with 0 when every check passed and 1 otherwise. It only reads; it never
changes the website.
"""

import argparse
import http.client
import json
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

TIMEOUT_SECONDS = 45
RETRY_PAUSE_SECONDS = 5


class _Assets(HTMLParser):
    """Collect the local files a page loads."""

    def __init__(self) -> None:
        super().__init__()
        self.files: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if value and name in {"src", "href"} and not (tag == "a" and name == "href"):
                self.files.append(value)


def fetch(url: str) -> tuple[int, bytes]:
    """Return the status and body of one HTTPS request, never raising for HTTP errors.

    A website that has been resting can drop the first connection while it wakes up, so a request
    that gets no answer is tried once more. Status 0 means no answer; the body holds the reason.
    """
    request = urllib.request.Request(url, headers={"User-Agent": "workshop-smoke-test"})
    reason = ""
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            return error.code, b""
        except (OSError, http.client.HTTPException) as error:
            reason = str(getattr(error, "reason", error)) or type(error).__name__
            if attempt == 0:
                time.sleep(RETRY_PAUSE_SECONDS)
    return 0, reason.encode()


def _why(status: int, body: bytes) -> str:
    """Describe a failed request in words a beginner can act on."""
    if status == 0:
        return f"no answer: {body.decode('utf-8', errors='replace')}"
    return f"HTTP {status}"


def local_files(page_url: str, html: str) -> list[str]:
    """Absolute addresses of the page's own files, skipping other websites and data URLs."""
    reader = _Assets()
    reader.feed(html)
    site = urlsplit(page_url).netloc
    found = []
    for address in reader.files:
        if address.startswith(("#", "data:", "mailto:")):
            continue
        absolute = urljoin(page_url, address)
        if urlsplit(absolute).netloc == site and absolute not in found:
            found.append(absolute)
    return found


def smoke_test(base_url: str, expect_text: str = "", page: str = "/") -> list[tuple[str, bool, str]]:
    """Run every check and return (check, passed, detail) rows."""
    base = base_url.rstrip("/")
    results: list[tuple[str, bool, str]] = []
    status, body = fetch(f"{base}/healthz")
    try:
        health = json.loads(body) if status == 200 else {}
    except ValueError:
        health = {}
    healthy = status == 200 and health.get("status") == "ok"
    detail = f"commit {health.get('commit', '?')[:7]}, content {health.get('site_digest', '?')[:12]}"
    if healthy:
        # Day 4 releases carry a version; it moves on with every build, unlike the content.
        version_status, version_body = fetch(f"{base}/version.json")
        try:
            version = json.loads(version_body).get("version") if version_status == 200 else None
        except (ValueError, AttributeError):
            version = None
        if isinstance(version, str) and version:
            detail += f", version {version}"
        # Day 5: the production slot is the website's own address; the feature slot is a test copy.
        if health.get("slot") in {"production", "feature"}:
            detail += f", {health['slot']} slot"
    results.append(("Website says it is healthy", healthy, detail if healthy else _why(status, body)))

    page_url = urljoin(f"{base}/", page.lstrip("/"))
    status, body = fetch(page_url)
    html = body.decode("utf-8", errors="replace") if status else ""
    results.append(("Page opens", status == 200 and "<html" in html.lower(), f"{_why(status, body)} {page_url}"))
    if expect_text:
        results.append((f'Page shows "{expect_text}"', expect_text in html, ""))
    for address in local_files(page_url, html) if status == 200 else []:
        file_status, file_body = fetch(address)
        name = urlsplit(address).path
        results.append((f"Loads {name}", file_status == 200, _why(file_status, file_body)))
    return results


def main(arguments: list[str] | None = None) -> int:
    """Print a pass/fail table and return the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("url", help="The website address, such as https://ali-planner.<domain>")
    parser.add_argument("--expect-text", default="", help="Words the page must contain")
    parser.add_argument("--page", default="/", help="A page under the website, such as /ideas/team-lunch/")
    options = parser.parse_args(arguments)
    if urlsplit(options.url).scheme != "https":
        parser.error("Use the https:// address of your published website.")
    results = smoke_test(options.url, options.expect_text, options.page)
    for check, passed, detail in results:
        print(f"{'PASS' if passed else 'FAIL'}  {check}" + (f"  ({detail})" if detail else ""))
    failed = sum(not passed for _, passed, _ in results)
    print(f"\n{len(results) - failed} passed, {failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
