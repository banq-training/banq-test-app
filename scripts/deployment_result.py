"""Verify a deployed revision and export non-secret, machine-readable evidence."""

import argparse
import hashlib
import json
import os
import re
import ssl
import time
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from app.config import deployment_name, load
from app.site import site_manifest


class NoRedirect(HTTPRedirectHandler):
    """Fail rather than mistake a login page or another host for the deployed app."""

    def redirect_request(self, *args: object, **kwargs: object) -> None:
        """Do not follow redirects during endpoint verification."""
        return None


class PageFacts(HTMLParser):
    """Extract visible heading and source text without depending on formatting."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.heading: list[str] = []
        self.source: list[str] = []
        self.visible: list[str] = []
        self.active: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Select the existing app's heading and explicit data-source indicator."""
        if tag == "h1":
            self.active = "heading"
        elif tag == "p" and "source" in (dict(attrs).get("class") or "").split():
            self.active = "source"

    def handle_endtag(self, tag: str) -> None:
        """End collection at the matching text container."""
        if (tag == "h1" and self.active == "heading") or (tag == "p" and self.active == "source"):
            self.active = None

    def handle_data(self, data: str) -> None:
        """Collect text; do not retain the original HTML in deployment evidence."""
        self.visible.append(data)
        if self.active == "heading":
            self.heading.append(data)
        elif self.active == "source":
            self.source.append(data)


def validate_origin(url: str) -> str:
    """Restrict smoke checks to a credential-free training Container Apps origin."""
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname
            or not parsed.hostname.endswith(".azurecontainerapps.io")
            or parsed.username or parsed.password or parsed.port
            or parsed.query or parsed.fragment or parsed.path not in ("", "/")):
        raise ValueError("Expected an HTTPS Azure Container Apps origin without credentials or a path")
    return f"https://{parsed.hostname}"


def fetch(url: str) -> bytes:
    """Read a small HTTPS response with verified TLS and no redirect fallback."""
    opener = build_opener(NoRedirect(), HTTPSHandler(context=ssl.create_default_context()))
    with opener.open(Request(url, headers={"User-Agent": "workshop-smoke/1"}), timeout=60) as response:
        if response.status != 200:
            raise ValueError("The deployed endpoint did not return HTTP 200")
        body = response.read(2 * 1024 * 1024 + 1)
    if not body or len(body) > 2 * 1024 * 1024:
        raise ValueError("The deployed response was empty or too large")
    return body


def validate_content(
    health: dict, page: str, *, label: str, commit: str, dataverse: bool,
    target: str = "vendor", expected_site: dict | None = None,
) -> str:
    """Reject stale revisions, wrong labels, and sample fallback for a live lab."""
    if health.get("status") != "ok" or health.get("commit") != commit:
        raise ValueError("The endpoint is not serving the expected healthy commit")
    if target == "website":
        if dataverse or expected_site is None:
            raise ValueError("A website needs expected asset fingerprints and cannot connect Dataverse")
        if (health.get("target") != "website" or health.get("label") != label
                or health.get("site_digest") != expected_site["digest"]
                or health.get("index_sha256") != expected_site["index_sha256"]
                or hashlib.sha256(page.encode("utf-8")).hexdigest() != expected_site["index_sha256"]):
            raise ValueError("The website does not match the requested label and asset content")
        return "website"
    if target != "vendor":
        raise ValueError("Unknown deployment target")
    facts = PageFacts()
    facts.feed(page)
    if "".join(facts.heading).strip() != f"{label} - Vendor Reviews":
        raise ValueError("The page does not display the expected workshop label")
    source = "".join(facts.source).strip()
    expected = "Source: Dataverse" if dataverse else (
        "Source: local synthetic samples (Dataverse is not configured)"
    )
    if source != expected:
        raise ValueError("The page is not using the requested data source (fallback/empty data is not a pass)")
    if not dataverse:
        visible = " ".join(facts.visible)
        for vendor in ("Harborline Congress Services", "Northstar Training Services", "Meridian Patient Outreach"):
            if vendor not in visible:
                raise ValueError("The sample-backed page is missing a seeded synthetic vendor")
    return "Dataverse" if dataverse else "samples"


def verify(
    url: str, *, label: str, commit: str, dataverse: bool, attempts: int = 3,
    target: str = "vendor", expected_site: dict | None = None,
) -> dict:
    """Allow brief rollout lag, but require every check to pass in the same attempt."""
    if not 1 <= attempts <= 3:
        raise ValueError("Endpoint verification allows one to three attempts")
    origin = validate_origin(url)
    for attempt in range(attempts):
        try:
            health = json.loads(fetch(origin + "/healthz"))
            if not isinstance(health, dict):
                raise ValueError("Expected a JSON health object")
            source = validate_content(
                health, fetch(origin + "/").decode("utf-8"),
                label=label, commit=commit, dataverse=dataverse,
                target=target, expected_site=expected_site,
            )
            result = {"url": origin, "source": source, "commit": commit, "display_name": label,
                      "target": target, "health_status": 200, "page_status": 200,
                      "verified_at": datetime.now(UTC).isoformat()}
            if target == "website":
                result.update(site_digest=expected_site["digest"], index_sha256=expected_site["index_sha256"])
            return result
        except (OSError, ValueError):
            if attempt + 1 == attempts:
                raise
            time.sleep(5)
    raise ValueError("Endpoint verification did not complete")


def main() -> int:
    """Run only inside Actions after deployment, emitting no secret material."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        commit = os.environ.get("GITHUB_SHA", "")
        repository = os.environ.get("GITHUB_REPOSITORY", "")
        run_id = os.environ.get("GITHUB_RUN_ID", "")
        attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
        if (not re.fullmatch(r"[a-f0-9]{40}", commit)
                or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)
                or not run_id.isdigit() or not attempt.isdigit()):
            raise ValueError("Deployment evidence requires the Actions commit, repository, run, and attempt")
        settings = load()
        dataverse = os.environ.get("CONNECT_DATAVERSE", "false") == "true"
        target = os.environ.get("DEPLOY_TARGET", "vendor")
        expected_site = site_manifest() if target == "website" else None
        result = verify(arguments.url, label=settings["displayName"], commit=commit,
                dataverse=dataverse, target=target, expected_site=expected_site)
        result.update({
            "schema_version": 1, "repository": repository, "run_id": run_id, "run_attempt": attempt,
            "run_url": f"https://github.com/{repository}/actions/runs/{run_id}",
            "app_name": deployment_name(settings["displayName"], target), "connect_dataverse": dataverse,
            "azure_authentication": "prepared GitHub Actions identity",
        })
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError) as error:
        parser.exit(1, f"Deployment verification failed ({type(error).__name__}). Check revision, label, source, and access.\n")


if __name__ == "__main__":
    raise SystemExit(main())