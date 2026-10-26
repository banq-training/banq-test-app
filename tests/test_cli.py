"""Exercise CLI output and errors using only synthetic source files."""

import json
import shlex
from pathlib import Path

import pytest

from src.vendor_assurance.cli import main


def test_cli_stdout_is_json_and_report_is_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """A redirected CLI result can be handed directly to the writer agent."""
    monkeypatch.setattr("sys.argv", [
        "vendor-assurance", "src/vendor_assurance/samples/synthetic_soc2_report.md",
        "--output-directory", str(tmp_path / "reports"), "--as-of", "2026-10-26",
    ])

    main()
    captured = capsys.readouterr()

    assert json.loads(captured.out)["score"] == 8
    assert "Wrote" in captured.err
    assert len(list((tmp_path / "reports").glob("*_2026_10_26.md"))) == 1


def test_agent_handoff_reference_command_preserves_the_agent_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """The baseline command from the post-workshop handoff guide keeps the agent's report separate."""
    command = (
        "uv run vendor-assurance src/vendor_assurance/samples/synthetic_soc2_meridian_outreach.md"
        " --as-of 2026-10-26 --output-directory reports/baseline/ > reports/evaluation.json"
    )
    arguments = shlex.split(command)
    redirect = arguments.index(">")
    assert arguments[redirect + 1:] == ["reports/evaluation.json"]
    argv = arguments[2:redirect]
    directory_index = argv.index("--output-directory") + 1
    assert Path(argv[directory_index]) == Path("reports/baseline")
    argv[directory_index] = str(tmp_path / "reports" / "baseline")

    filename = "PrivacyReview_Meridian_Patient_Outreach_2026_10_26.md"
    agent_report = tmp_path / "reports" / filename
    agent_report.parent.mkdir()
    agent_report.write_text("Separate synthetic agent report.", encoding="utf-8")
    monkeypatch.setattr("sys.argv", argv)

    main()

    assert json.loads(capsys.readouterr().out)["score"] == 2
    assert (tmp_path / "reports" / "baseline" / filename).is_file()
    assert agent_report.read_text(encoding="utf-8") == "Separate synthetic agent report."


@pytest.mark.parametrize("path", ["missing.md", "unsupported.pdf"])
def test_cli_errors_are_actionable(
    path: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """Unsupported files and missing inputs should not print a traceback."""
    monkeypatch.setattr("sys.argv", ["vendor-assurance", path])

    with pytest.raises(SystemExit) as caught:
        main()

    assert caught.value.code == 2
    assert "Traceback" not in capsys.readouterr().err