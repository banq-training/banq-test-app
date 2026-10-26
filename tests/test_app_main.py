"""Exercise the starter page without credentials, Azure, or a live server."""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app import main
from src.vendor_assurance.dataverse import DataverseError


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Use a fictional attendee without editing the repository's config file."""
    monkeypatch.setattr(main, "load", lambda: {"displayName": "Synthetic Builder", "appName": "synthetic-builder"})
    monkeypatch.delenv("DATAVERSE_URL", raising=False)
    monkeypatch.delenv("WORKSHOP_ALLOW_WRITES", raising=False)
    return TestClient(main.app)


def test_sample_page_and_health(client: TestClient) -> None:
    """The separate vendor example runs with synthetic data and no service access."""
    response = client.get("/")

    assert response.status_code == 200
    assert "Synthetic Builder" in response.text
    assert "local synthetic samples" in response.text
    assert response.text.count("class='score'") == 3
    assert client.get("/healthz").json() == {"status": "ok"}


def test_config_failure_is_readable(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """The unedited placeholder gives instructions instead of a server error."""
    monkeypatch.setattr(main, "load", Mock(side_effect=ValueError("Edit config.json")))

    response = client.get("/")

    assert response.status_code == 400
    assert "Edit config.json" in response.text


def test_empty_dataverse_does_not_masquerade_as_samples(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty query result differs from unavailable Dataverse."""
    monkeypatch.setenv("DATAVERSE_URL", "https://synthetic.example")
    monkeypatch.setattr(main, "_from_dataverse", lambda attendee: [])

    response = client.get("/")

    assert "no rows tagged" in response.text
    assert "local synthetic samples" not in response.text


def test_dataverse_failure_is_labelled(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fallback must not look like a successful Dataverse connection."""
    monkeypatch.setenv("DATAVERSE_URL", "https://synthetic.example")
    monkeypatch.setattr(main, "_from_dataverse", Mock(side_effect=DataverseError("HTTP 403")))

    response = client.get("/")

    assert response.status_code == 200
    assert "Dataverse unavailable: HTTP 403" in response.text
    assert "local synthetic samples" in response.text


def test_unscored_dataverse_row_is_not_shown_as_a_result(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A manually added vendor has no score until the evaluator runs."""
    monkeypatch.setenv("DATAVERSE_URL", "https://synthetic.example")
    monkeypatch.setattr(main, "_from_dataverse", lambda attendee: [
        {"vendor": "Synthetic Pending Vendor", "score": None, "sensitivity": ""},
    ])

    response = client.get("/")

    assert response.status_code == 200
    assert "Not assessed" in response.text
    assert "None/10" not in response.text


def test_names_are_escaped_for_odata_and_html(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """A fictional apostrophe must not break a filter or inject page markup."""
    transport = Mock()
    transport.rows.return_value = [{"cr522_vendor": "<Synthetic>", "cr522_score": 8}]
    monkeypatch.setattr(main.DataverseClient, "from_environment", lambda: transport)

    assert main._from_dataverse("Synthetic O'Brien")[0]["vendor"] == "<Synthetic>"
    assert transport.rows.call_args.kwargs["$filter"] == "cr522_attendee eq 'Synthetic O''Brien'"
    monkeypatch.setenv("DATAVERSE_URL", "https://synthetic.example")
    assert "&lt;Synthetic&gt;" in client.get("/").text


@pytest.mark.parametrize("enabled,configured", [(False, False), (True, False), (False, True)])
def test_training_writes_are_disabled_by_default(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, enabled: bool, configured: bool,
) -> None:
    """Deploying a Dataverse reader must not expose an unauthenticated write form."""
    if enabled:
        monkeypatch.setenv("WORKSHOP_ALLOW_WRITES", "true")
    if configured:
        monkeypatch.setenv("DATAVERSE_URL", "https://synthetic.example")
    transport = Mock()
    monkeypatch.setattr(main.DataverseClient, "from_environment", transport)
    monkeypatch.setattr(main, "_from_dataverse", lambda attendee: [])
    assert 'id="vendor-form"' not in client.get("/").text
    response = client.post("/vendors", json={"vendor": "Synthetic New", "system": "Synthetic Portal"})
    assert response.status_code == 403
    transport.assert_not_called()


def test_prepared_form_writes_only_names_and_server_label(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A new fictional row has no model-made score, sensitivity, or browser-supplied identity."""
    monkeypatch.setenv("WORKSHOP_ALLOW_WRITES", "true")
    monkeypatch.setenv("DATAVERSE_URL", "https://synthetic.example")
    transport = Mock()
    transport.rows.return_value = []
    monkeypatch.setattr(main.DataverseClient, "from_environment", lambda: transport)
    assert 'id="vendor-form"' in client.get("/").text
    response = client.post("/vendors", json={"vendor": " Synthetic O'Brien ", "system": " Portal "})
    assert response.status_code == 201
    assert response.json()["assessment"] == "Not assessed"
    transport.request.assert_called_once_with("POST", "cr522_vendorreviews", {
        "cr522_vendor": "Synthetic O'Brien", "cr522_system": "Portal",
        "cr522_attendee": "Synthetic Builder",
    })


@pytest.mark.parametrize("body", [
    {"vendor": " ", "system": "Portal"},
    {"vendor": "Synthetic", "system": ""},
    {"vendor": "Synthetic"},
    {"vendor": 123, "system": "Portal"},
    {"vendor": "Synthetic" * 30, "system": "Portal"},
    {"vendor": "Synthetic", "system": "Portal", "attendee": "Other label"},
    {"vendor": "Synthetic", "system": "Portal", "score": 10},
])
def test_prepared_form_rejects_invalid_or_extra_fields(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, body: dict,
) -> None:
    """Invalid input cannot reach the shared service."""
    monkeypatch.setenv("WORKSHOP_ALLOW_WRITES", "true")
    monkeypatch.setenv("DATAVERSE_URL", "https://synthetic.example")
    transport = Mock()
    monkeypatch.setattr(main.DataverseClient, "from_environment", transport)
    assert client.post("/vendors", json=body).status_code == 422
    transport.assert_not_called()


def test_write_failure_is_not_reported_as_saved(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed or ambiguous write gives a safe message without leaking service details."""
    monkeypatch.setenv("WORKSHOP_ALLOW_WRITES", "true")
    monkeypatch.setenv("DATAVERSE_URL", "https://synthetic.example")
    transport = Mock()
    transport.request.side_effect = DataverseError("Synthetic private diagnostic")
    monkeypatch.setattr(main.DataverseClient, "from_environment", lambda: transport)
    response = client.post("/vendors", json={"vendor": "Synthetic", "system": "Portal"})
    assert response.status_code == 503
    assert "before retrying" in response.json()["detail"]
    assert "private diagnostic" not in response.text


def test_follow_up_filter_keeps_unassessed_distinct(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only assessed scores below five appear; reset restores the full scoped queue."""
    monkeypatch.setenv("DATAVERSE_URL", "https://synthetic.example")
    rows = [
        {"vendor": "Synthetic Low", "score": 4, "sensitivity": "Low"},
        {"vendor": "Synthetic Good", "score": 5, "sensitivity": "Low"},
        {"vendor": "Synthetic Pending", "score": None, "sensitivity": ""},
    ]
    loader = Mock(return_value=rows)
    monkeypatch.setattr(main, "_from_dataverse", loader)
    filtered = client.get("/?follow_up=true").text
    assert "Synthetic Low" in filtered
    assert "Synthetic Good" not in filtered
    assert "Synthetic Pending" not in filtered
    assert "Reviews shown: 1" in filtered
    reset = client.get("/").text
    assert "Synthetic Pending" in reset and "Not assessed" in reset
    assert "Reviews shown: 3" in reset
    loader.assert_called_with("Synthetic Builder")