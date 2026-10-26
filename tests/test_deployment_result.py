"""Verify deployment checks with synthetic pages, not live Azure access."""

import html
import json
from unittest.mock import Mock
from urllib.error import URLError

import pytest

from app.main import healthz
from scripts import deployment_result

COMMIT = "a" * 40
LABEL = "Synthetic Rehearsal & Training"
SOURCE = "Source: local synthetic samples (Dataverse is not configured)"


def page(source: str = SOURCE) -> str:
    """Make the minimum recognizable synthetic app page."""
    return (
        f"<h1>{html.escape(LABEL)} - Vendor Reviews</h1><p class='source'>{html.escape(source)}</p>"
        "<table><tr><td>Harborline Congress Services</td></tr>"
        "<tr><td>Northstar Training Services</td></tr>"
        "<tr><td>Meridian Patient Outreach</td></tr></table>"
    )


def test_health_identifies_deployed_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    """A deployed old revision must be distinguishable from the requested commit."""
    monkeypatch.setenv("WORKSHOP_COMMIT", COMMIT)
    assert healthz() == {"status": "ok", "commit": COMMIT}
    monkeypatch.delenv("WORKSHOP_COMMIT")
    assert healthz() == {"status": "ok"}


def test_samples_are_verified_not_only_http_status() -> None:
    """Verify the label, source, and actual synthetic data."""
    assert deployment_result.validate_content(
        {"status": "ok", "commit": COMMIT}, page(), label=LABEL, commit=COMMIT, dataverse=False,
    ) == "samples"


@pytest.mark.parametrize("health,content,dataverse", [
    ({"status": "ok", "commit": "b" * 40}, page(), False),
    ({"status": "ok", "commit": COMMIT}, page().replace("Northstar", "Wrong"), False),
    ({"status": "ok", "commit": COMMIT}, page().replace("Rehearsal", "Someone Else"), False),
    ({"status": "ok", "commit": COMMIT}, page(), True),
    ({"status": "ok", "commit": COMMIT}, page("Source: Dataverse - no rows yet"), True),
])
def test_stale_wrong_or_fallback_results_fail(health: dict, content: str, dataverse: bool) -> None:
    """A running container is not necessarily the requested functioning app."""
    with pytest.raises(ValueError):
        deployment_result.validate_content(health, content, label=LABEL, commit=COMMIT, dataverse=dataverse)


def test_live_source_passes_without_claiming_form_completion(monkeypatch: pytest.MonkeyPatch) -> None:
    """The smoke result makes no claim about browser writes or all labs passing."""
    def fetch(url: str) -> bytes:
        if url.endswith("/healthz"):
            return json.dumps({"status": "ok", "commit": COMMIT}).encode()
        return page("Source: Dataverse").encode()

    monkeypatch.setattr(deployment_result, "fetch", fetch)
    result = deployment_result.verify(
        "https://synthetic.example.azurecontainerapps.io", label=LABEL, commit=COMMIT, dataverse=True,
    )
    assert result["source"] == "Dataverse"
    assert "labs" not in result


def test_verification_retries_a_previous_revision_during_rollout(monkeypatch: pytest.MonkeyPatch) -> None:
    """One request hitting an old replica must not fail an otherwise healthy rollout."""
    fetch = Mock(side_effect=[
        json.dumps({"status": "ok", "commit": "b" * 40}).encode(), page().encode(),
        json.dumps({"status": "ok", "commit": COMMIT}).encode(), page().encode(),
    ])
    pause = Mock()
    monkeypatch.setattr(deployment_result, "fetch", fetch)
    monkeypatch.setattr(deployment_result.time, "sleep", pause)

    result = deployment_result.verify(
        "https://synthetic.example.azurecontainerapps.io", label=LABEL, commit=COMMIT, dataverse=False,
    )

    assert result["commit"] == COMMIT
    assert fetch.call_count == 4
    pause.assert_called_once_with(5)


def test_verification_retries_a_transient_connection_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cold-start connection failures may recover, without bypassing content checks."""
    fetch = Mock(side_effect=[
        URLError("synthetic connection failure"),
        json.dumps({"status": "ok", "commit": COMMIT}).encode(), page().encode(),
    ])
    monkeypatch.setattr(deployment_result, "fetch", fetch)
    monkeypatch.setattr(deployment_result.time, "sleep", Mock())

    assert deployment_result.verify(
        "https://synthetic.example.azurecontainerapps.io", label=LABEL, commit=COMMIT, dataverse=False,
    )["source"] == "samples"
    assert fetch.call_count == 3


def test_verification_stops_after_three_unsuccessful_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Retries must never convert a persistent wrong revision into successful evidence."""
    fetch = Mock(side_effect=[
        json.dumps({"status": "ok", "commit": "b" * 40}).encode(), page().encode(),
    ] * 3)
    pause = Mock()
    monkeypatch.setattr(deployment_result, "fetch", fetch)
    monkeypatch.setattr(deployment_result.time, "sleep", pause)

    with pytest.raises(ValueError, match="expected healthy commit"):
        deployment_result.verify(
            "https://synthetic.example.azurecontainerapps.io", label=LABEL, commit=COMMIT, dataverse=False,
        )
    assert fetch.call_count == 6
    assert pause.call_count == 2


@pytest.mark.parametrize("url", [
    "https://example.invalid", "http://synthetic.example.azurecontainerapps.io",
    "https://user:secret@synthetic.example.azurecontainerapps.io",
    "https://synthetic.example.azurecontainerapps.io/path",
    "https://synthetic.example.azurecontainerapps.io?token=secret",
])
def test_endpoint_validation_rejects_wrong_targets(url: str) -> None:
    """Do not fetch arbitrary credential-bearing URLs from an artifact."""
    with pytest.raises(ValueError):
        deployment_result.validate_origin(url)


def test_website_verifies_exact_assets_without_vendor_heading(tmp_path) -> None:
    """Creative learner titles are allowed; a wrong asset revision is not."""
    content = '<html><body><h1>Synthetic Reading List</h1></body></html>'
    (tmp_path / "index.html").write_text(content, encoding="utf-8")
    expected = deployment_result.site_manifest(tmp_path)
    health = {"status": "ok", "commit": COMMIT, "target": "website", "label": LABEL,
              "site_digest": expected["digest"], "index_sha256": expected["index_sha256"]}
    arguments = {"label": LABEL, "commit": COMMIT, "dataverse": False,
                 "target": "website", "expected_site": expected}
    assert deployment_result.validate_content(health, content, **arguments) == "website"
    with pytest.raises(ValueError, match="asset content"):
        deployment_result.validate_content(health, content + "stale", **arguments)
    for key in ("target", "label", "site_digest", "index_sha256"):
        with pytest.raises(ValueError):
            deployment_result.validate_content({**health, key: "wrong"}, content, **arguments)
    with pytest.raises(ValueError, match="cannot connect Dataverse"):
        deployment_result.validate_content(health, content, **{**arguments, "dataverse": True})