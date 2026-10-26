"""Exercise the lab hook without a live Copilot session."""

import io
import json
from pathlib import Path

import pytest

from scripts import audit_hook


def test_log_keeps_metadata_only(tmp_path: Path) -> None:
    """Prompts, tool arguments, and tool results must not reach the log."""
    payload = {
        "toolName": "view",
        "initialPrompt": "synthetic-private-prompt",
        "toolArgs": {"token": "synthetic-secret"},
        "toolResult": "synthetic-private-result",
    }
    assert audit_hook.record_event("preToolUse", payload, tmp_path) == {}
    audit_hook.record_event("postToolUse", payload, tmp_path)
    content = (tmp_path / "agent-audit.jsonl").read_text(encoding="utf-8")
    entries = [json.loads(line) for line in content.splitlines()]

    assert len(entries) == 2
    assert entries[0]["tool"] == "view"
    assert all(set(entry) == {"timestamp", "event", "tool", "decision"} for entry in entries)
    assert "synthetic-private" not in content
    assert "synthetic-secret" not in content


def test_deny_decision_is_specific_and_not_an_allow_all(tmp_path: Path) -> None:
    """Only the selected tool is denied; other tools retain normal permissions."""
    decision = audit_hook.record_event("preToolUse", {"toolName": "bash"}, tmp_path, "bash")

    assert decision["permissionDecision"] == "deny"
    assert decision["permissionDecisionReason"]
    assert audit_hook.record_event("preToolUse", {"toolName": "view"}, tmp_path, "bash") == {}
    assert audit_hook.record_event("postToolUse", {"toolName": "bash"}, tmp_path, "bash") == {}


@pytest.mark.parametrize("raw", ["[]", "invalid", '{"toolName": 3}'])
def test_invalid_input_fails_without_echoing_input(
    raw: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """Errors should not copy raw input into a terminal or session log."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["audit_hook.py", "preToolUse"])
    monkeypatch.setattr("sys.stdin", io.StringIO(raw))

    with pytest.raises(SystemExit) as caught:
        audit_hook.main()

    assert caught.value.code == 2
    assert capsys.readouterr().out == ""
    assert not (tmp_path / "logs" / "agent-audit.jsonl").exists()