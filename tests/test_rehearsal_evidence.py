"""Check that rehearsal records cannot pass by omitting live requirements."""

import json
import sys
from pathlib import Path

import pytest

from rehearsal import evidence


@pytest.fixture
def ledger(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Create a synthetic record without depending on the current Git revision."""
    monkeypatch.setattr(evidence, "git_state", lambda: {"commit": "a" * 40, "dirty": False})
    return evidence.initialize("synthetic/rehearsal")


def test_manifest_covers_all_labs_in_workshop_order() -> None:
    """Keep the five active labs and the four supported daily sessions discoverable."""
    labs = evidence.manifest()
    assert [lab["id"] for lab in labs] == [
        "00", "01", "02", "08", "day-2", "day-3", "day-4", "03", "day-5"
    ]
    for lab in labs:
        assert Path(lab["guide"]).is_file()
        assert lab["checks"]
        assert all(Path(path).is_file() for path in lab["tests"])
        assert not set(lab["checks"]) & set(lab.get("optional_checks", {}))


def test_every_live_condition_starts_pending(ledger: dict) -> None:
    """An initialized checklist is not a completed workshop."""
    assert all(evidence.lab_status(ledger, lab) == "pending" for lab in evidence.manifest())
    assert "pending" in evidence.render_summary(ledger)


def test_passing_requires_observation_and_evidence(ledger: dict) -> None:
    """A green unit suite must not automatically pass the browser journey."""
    with pytest.raises(ValueError, match="Passing requires"):
        evidence.record(ledger, "01", "manual-behaviour", "passed", [], "Tests passed")
    with pytest.raises(ValueError, match="Passing requires"):
        evidence.record(ledger, "01", "manual-behaviour", "passed",
                        ["https://github.com/synthetic/rehearsal/issues/1"], "Tests passed")


def test_old_research_checks_cannot_complete_the_first_page_lab(ledger: dict) -> None:
    """Previous curriculum evidence must not silently satisfy the new beginner journey."""
    lab = next(lab for lab in evidence.manifest() if lab["id"] == "01")
    ledger["labs"]["01"] = {
        check: {"status": "passed", "evidence": ["https://example.invalid/observed"],
            "observation_attested": True}
        for check in ("mcp-tools", "browser-download", "conversion", "facts", "visual-brief")
    }
    assert evidence.lab_status(ledger, lab) == "pending"


@pytest.mark.parametrize("required_check", ["implementation", "personalisation", "manual-checks", "preview"])
def test_website_work_requires_each_observation(ledger: dict, required_check: str) -> None:
    """Implementation, personalisation and manual checks are separate core requirements."""
    lab = next(lab for lab in evidence.manifest() if lab["id"] == "02")
    assert required_check in lab["checks"]
    assert "delegation" not in lab["checks"]
    for check in lab["checks"]:
        if check != required_check:
            evidence.record(
                ledger, "02", check, "passed",
                ["https://github.com/synthetic/rehearsal/issues/1"],
                "Synthetic observation for this test", observed=True,
            )
    assert evidence.lab_status(ledger, lab) == "pending"
    evidence.record(ledger, "02", required_check, "blocked", [], "Live stage unavailable")
    assert evidence.lab_status(ledger, lab) == "blocked"


def test_optional_extensions_are_visible_but_do_not_gate_core(ledger: dict) -> None:
    """Storage can be blocked while the first interactive page is honestly complete."""
    lab = next(lab for lab in evidence.manifest() if lab["id"] == "02")
    for key in lab["checks"]:
        evidence.record(ledger, "02", key, "passed", ["https://example.invalid/observed"],
                        "Synthetic observation", observed=True)
    evidence.record(ledger, "02", "storage", "blocked", [], "Extension not available")
    assert evidence.lab_status(ledger, lab) == "passed"
    assert "| 02 / storage | blocked |" in evidence.render_summary(ledger)
    del ledger["labs"]["02"]["manual-checks"]
    assert evidence.lab_status(ledger, lab) == "pending"


def test_optional_pass_still_needs_actual_evidence(ledger: dict) -> None:
    """Calling a task optional must not weaken the truth standard for a claimed pass."""
    with pytest.raises(ValueError, match="Passing requires"):
        evidence.record(ledger, "02", "storage", "passed", [], "Installed", observed=True)
    ledger["labs"]["02"]["storage"] = {"status": "passed"}
    assert evidence.check_status(ledger, "02", "storage") == "pending"


def test_tooling_and_release_gates_belong_to_later_sessions() -> None:
    """Monday's optional publishing does not erase the full week's live release checks."""
    labs = {lab["id"]: lab for lab in evidence.manifest()}
    assert "cli-turn" not in labs["00"]["checks"]
    assert "05" not in labs
    assert "cli-turn" in labs["day-3"]["checks"]
    assert {"requirements-agent", "criteria", "ticket-built", "tests"} <= labs["day-3"]["checks"].keys()
    assert {"github-mcp", "teach-copilot", "browser-demo"} <= labs["day-3"]["optional_checks"].keys()
    assert "04" not in labs and "06" not in labs, "Labs 04 and 06 are optional Day 3 extras"
    assert "browser-setup" not in labs["day-3"]["checks"]
    assert not {"seed", "private-journey", "cli-turn", "browser-tools"} & labs["day-2"]["checks"].keys()
    assert "actions" not in labs["08"]["checks"]
    assert "endpoint" in labs["08"]["optional_checks"]
    assert "07" not in labs
    assert "ai-picture" in labs["02"]["optional_checks"]
    assert {"issue-session", "review", "merged-check"} <= labs["03"]["checks"].keys()
    assert {"branch-pr", "review-agent", "report", "iteration", "decision"} <= labs["day-4"]["checks"].keys()
    assert {"ruleset", "version"} <= labs["day-4"]["checks"].keys()
    assert "publication" in labs["day-4"]["optional_checks"]
    # 21 October 2026: a simple automation on the learner's own website is an optional Day 4 extra.
    assert "criteria-automation" in labs["day-4"]["optional_checks"]
    assert "criteria-automation" not in labs["day-4"]["checks"]
    # Days 3-5 are deep dives people pick and choose: newcomers catch up on Days 4 and 5.
    assert "joining-today" in labs["day-4"]["optional_checks"]
    assert "joining-today" in labs["day-5"]["optional_checks"]
    assert {"workflow", "ci", "cd", "recovery", "demos", "handoff"} <= labs["day-5"]["checks"].keys()
    assert {"required-checks", "ui-check"} <= labs["day-5"]["checks"].keys()
    # 21 October 2026, later: Day 3 starts from tickets on a project board.
    assert {"tickets", "github-tool", "skill", "checkpoint"} <= labs["day-3"]["checks"].keys()
    advanced = {"repeatable-browser", "selected-release", "automation", "live-hook", "handoffs"}
    for lab in labs.values():
        assert not advanced & (lab["checks"].keys() | lab.get("optional_checks", {}).keys())


def test_require_complete_ignores_unfinished_extensions(
    ledger: dict, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """The CLI gates every core condition, not unselected extension work."""
    for lab in evidence.manifest():
        for key in lab["checks"]:
            evidence.record(ledger, lab["id"], key, "passed", ["https://example.invalid/observed"],
                            "Synthetic observation", observed=True)
    evidence.record(ledger, "01", "conversion", "blocked", [], "Optional tool unavailable")
    monkeypatch.setattr(evidence, "ROOT", tmp_path)
    output = tmp_path / "rehearsal" / "results" / "synthetic"
    output.mkdir(parents=True)
    (output / "ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["evidence", "--output", str(output), "summary", "--require-complete"])
    assert evidence.main() == 0
    del ledger["labs"]["day-2"]["manual-journey"]
    (output / "ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
    assert evidence.main() == 1


def test_missing_entries_never_pass(ledger: dict) -> None:
    """Removing a blocked check from JSON must not improve completion status."""
    lab = evidence.manifest()[0]
    ledger["labs"][lab["id"]] = {}
    assert evidence.lab_status(ledger, lab) == "pending"


def test_retired_dataverse_evidence_cannot_pass_own_idea_work(ledger: dict) -> None:
    """Preserve old observations without converting them into unrelated new completion claims."""
    old_entry = {"seed": {"status": "passed", "evidence": ["https://example.invalid/observed"],
                          "observation_attested": True}}
    ledger["labs"]["05"] = old_entry
    del ledger["labs"]["day-2"]
    session = next(lab for lab in evidence.manifest() if lab["id"] == "day-2")
    assert evidence.lab_status(ledger, session) == "pending"
    evidence.record(ledger, "day-2", "idea-brief", "passed", ["https://example.invalid/observed"],
                    "New own-idea brief actually observed", observed=True)
    assert evidence.lab_status(ledger, session) == "pending"
    assert ledger["labs"]["05"] == old_entry
    with pytest.raises(ValueError, match="Unknown lab"):
        evidence.record(ledger, "05", "seed", "passed", ["https://example.invalid/observed"],
                        "Retired requirement", observed=True)


def test_blocked_and_passed_are_distinct(ledger: dict) -> None:
    """Keep a concrete access blocker visible without requiring a fake proof link."""
    evidence.record(ledger, "00", "access", "blocked", [], "Copilot sign-in required")
    assert evidence.lab_status(ledger, evidence.manifest()[0]) == "blocked"
    for key in ledger["labs"]["00"]:
        evidence.record(ledger, "00", key, "passed",
                        ["https://github.com/synthetic/rehearsal/actions/runs/1"],
                        "Synthetic observation for this test", observed=True)
    assert evidence.lab_status(ledger, evidence.manifest()[0]) == "passed"


@pytest.mark.parametrize("reference", [
    "https://user:secret@example.invalid/run", "https://example.invalid/run?token=secret",
    "http://example.invalid/run", "missing-evidence.json", ".facilitator/README.md",
])
def test_references_reject_unsafe_or_missing_evidence(reference: str) -> None:
    """Do not preserve private files, signed tokens, or nonexistent attachments."""
    with pytest.raises(ValueError):
        evidence.validate_reference(reference)
