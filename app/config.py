"""Read the attendee configuration and derive Azure-safe names from it."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"
MAX_APP_NAME = 32
PLACEHOLDER = "your name"


def slugify(display_name: str) -> str:
    """Turn a display name into a valid Container App name.

    Container App names are lowercase, alphanumeric with hyphens, must start with a letter,
    must end alphanumerically, and are capped at 32 characters.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", display_name.strip().lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)[:MAX_APP_NAME].rstrip("-")
    if not slug:
        raise ValueError("displayName must contain at least one letter or digit")
    if not slug[0].isalpha():
        slug = f"a-{slug}"[:MAX_APP_NAME].rstrip("-")
    return slug


def load(path: Path | None = None) -> dict[str, str]:
    """Load config.json and return the display name with its derived app name."""
    config_path = path or CONFIG_PATH
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("displayName"), str):
        raise ValueError("config.json must contain a string displayName")
    display_name = data["displayName"].strip()
    if not display_name:
        raise ValueError("config.json is missing displayName")
    if any(ord(character) < 32 for character in display_name):
        raise ValueError("displayName must be a single line without control characters")
    if len(display_name) > 100:
        raise ValueError("displayName must be at most 100 characters")
    if display_name.lower() == PLACEHOLDER:
        raise ValueError("Edit config.json and replace 'Your Name' with your own name")
    return {"displayName": display_name, "appName": slugify(display_name)}


def deployment_name(display_name: str, target: str = "vendor") -> str:
    """Keep vendor names stable and give websites a separate, bounded name."""
    base = slugify(display_name)
    if target == "vendor":
        return base
    if target != "website":
        raise ValueError("Deployment target must be website or vendor")
    suffix = hashlib.sha256(display_name.strip().encode("utf-8")).hexdigest()[:6]
    return f"{base[:20].rstrip('-')}-{suffix}-web"


if __name__ == "__main__":
    # A traceback here would read as broken materials, so fail with a plain sentence.
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--target", choices=("website", "vendor"), default="vendor")
        arguments = parser.parse_args()
        settings = load()
    except (OSError, ValueError) as error:
        print(f"config.json needs attention: {error}", file=sys.stderr)
        raise SystemExit(1) from None
    print(f"displayName={settings['displayName']}")
    print(f"appName={deployment_name(settings['displayName'], arguments.target)}")
