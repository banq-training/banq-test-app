"""Record workshop hook metadata without storing prompts, arguments, or results."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

EVENTS = ("sessionStart", "preToolUse", "postToolUse", "sessionEnd")
MAX_INPUT_CHARS = 1024 * 1024


def record_event(
    event: str, payload: dict[str, Any], directory: Path, deny_tool: str = "",
) -> dict[str, str]:
    """Log one event and optionally deny one exact tool name for the demo."""
    if event not in EVENTS:
        raise ValueError("Unsupported workshop event")
    tool = payload.get("toolName", payload.get("tool_name", ""))
    if not isinstance(tool, str) or len(tool) > 200:
        raise ValueError("Expected a tool name of at most 200 characters")
    decision: dict[str, str] = {}
    if event == "preToolUse" and deny_tool and tool == deny_tool:
        decision = {
            "permissionDecision": "deny",
            "permissionDecisionReason": "This tool is disabled for the workshop demonstration.",
        }
    entry = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "event": event,
        "tool": tool,
        "decision": decision.get("permissionDecision", "default"),
    }
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "agent-audit.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(entry) + "\n")
    return decision


def main() -> None:
    """Read the hook JSON from stdin and emit one decision object on stdout."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("event", choices=EVENTS)
    parser.add_argument("--deny-tool", default="", help="Exact tool name for a temporary demo denial")
    args = parser.parse_args()
    try:
        raw = sys.stdin.read(MAX_INPUT_CHARS + 1)
        if len(raw) > MAX_INPUT_CHARS:
            raise ValueError("Hook input exceeds the workshop limit")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Hook input must be a JSON object")
        decision = record_event(args.event, payload, Path("logs"), args.deny_tool)
    except (OSError, ValueError):
        parser.exit(2, "Workshop hook could not read valid input or write its log.\n")
    print(json.dumps(decision))


if __name__ == "__main__":
    main()