"""Add the reviewed Playwright server to the workspace MCP configuration.

On Day 3 each attendee runs ``bash .devcontainer/setup.sh browser`` once. That profile installs
the pinned, sandboxed browser and then calls this script, so nobody edits JSON by hand. Other
servers already in ``.vscode/mcp.json``, such as the read-only GitHub server, are kept.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / ".devcontainer" / "mcp.example.json"
TARGET = ROOT / ".vscode" / "mcp.json"


def enable_playwright(target: Path = TARGET, example: Path = EXAMPLE) -> bool:
    """Copy the example's ``playwright`` entry into ``target``.

    Returns True when the file changed and False when the same entry was already present.
    Raises ValueError instead of overwriting a file it cannot safely merge.
    """
    entry = json.loads(example.read_text(encoding="utf-8"))["servers"]["playwright"]
    config: dict = {}
    if target.exists():
        try:
            config = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(
                f"{target.name} is not plain JSON, so it was left unchanged. "
                "Ask a helper to add the playwright entry from .devcontainer/mcp.example.json."
            ) from error
        if not isinstance(config, dict) or not isinstance(config.setdefault("servers", {}), dict):
            raise ValueError(f"{target.name} has an unexpected shape, so it was left unchanged.")
    servers = config.setdefault("servers", {})
    if servers.get("playwright") == entry:
        return False
    if "playwright" in servers:
        raise ValueError(
            f"{target.name} already has a different playwright entry, so it was left unchanged."
        )
    servers["playwright"] = entry
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return True


def main() -> int:
    """Report the result in plain words for the attendee's terminal."""
    try:
        changed = enable_playwright()
    except (OSError, KeyError, ValueError) as error:
        print(f"Playwright connection: {error}", file=sys.stderr)
        return 1
    if changed:
        print("Added the playwright server to .vscode/mcp.json.")
    else:
        print("The playwright server is already in .vscode/mcp.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
