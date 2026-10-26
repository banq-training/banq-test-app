"""Test provisioning and seeding without touching the shared environment."""

from unittest.mock import Mock

import pytest

from scripts import dataverse_app_user, dataverse_provision, dataverse_seed
from src.vendor_assurance.dataverse import DataverseError


def test_seed_updates_samples_without_deleting_attendee_work(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """Re-running the seed command preserves custom rows and scopes updates."""
    client = Mock()
    client.rows.side_effect = [[
        {"cr522_vendor": "Harborline Congress Services", "cr522_vendorreviewid": "synthetic-id"},
        {"cr522_vendor": "My fictional lab row", "cr522_vendorreviewid": "keep-me"},
    ], [{"cr522_vendor": "My fictional lab row"}]]
    factory = Mock(return_value=client)
    monkeypatch.setattr(dataverse_seed.DataverseClient, "from_environment", factory)
    monkeypatch.setattr(dataverse_seed, "load", lambda: {"displayName": "Synthetic O'Brien"})

    dataverse_seed.main()

    assert client.request.call_count == 3
    assert [call.args[0] for call in client.request.call_args_list].count("PATCH") == 1
    for call in client.request.call_args_list:
        assert call.args[0] != "DELETE"
        assert "keep-me" not in call.args[1]
        assert call.args[2]["cr522_attendee"] == "Synthetic O'Brien"
    assert client.rows.call_args_list[0].kwargs["$filter"] == "cr522_attendee eq 'Synthetic O''Brien'"
    factory.assert_called_once_with(allow_cli=False)
    assert "Not assessed" in capsys.readouterr().out


def test_failed_seed_read_stops_before_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed read must not turn a re-seed into duplicate inserts."""
    client = Mock()
    client.rows.side_effect = DataverseError("HTTP 403", 403)
    monkeypatch.setattr(dataverse_seed.DataverseClient, "from_environment", lambda **kwargs: client)
    monkeypatch.setattr(dataverse_seed, "load", lambda: {"displayName": "Synthetic Builder"})

    with pytest.raises(DataverseError):
        dataverse_seed.main()
    client.request.assert_not_called()


def test_provision_skips_existing_columns_but_surfaces_failures() -> None:
    """Existing metadata and denied access need different outcomes."""
    client = Mock()
    client.exists.return_value = True
    column = dataverse_provision.string_column("Attendee", "Attendee", 100)
    dataverse_provision.add_column(client, "vendorreview", column)
    client.request.assert_not_called()

    client.exists.side_effect = DataverseError("HTTP 403", 403)
    with pytest.raises(DataverseError):
        dataverse_provision.add_column(client, "vendorreview", column)


def test_role_assignment_requires_an_explicit_role(monkeypatch: pytest.MonkeyPatch) -> None:
    """Admin permissions must not be a script default."""
    monkeypatch.setenv("DATAVERSE_APP_ID", "00000000-0000-0000-0000-000000000001")
    monkeypatch.delenv("DATAVERSE_ROLE", raising=False)

    with pytest.raises(ValueError, match="DATAVERSE_ROLE"):
        dataverse_app_user.main()


def test_role_assignment_is_scoped_and_repeatable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use the user's business unit and do not duplicate an existing grant."""
    monkeypatch.setenv("DATAVERSE_APP_ID", "00000000-0000-0000-0000-000000000001")
    monkeypatch.setenv("DATAVERSE_ROLE", "Synthetic Reviewer's Role")
    client = Mock()
    client.rows.side_effect = [
        [{"systemuserid": "synthetic-user", "_businessunitid_value": "synthetic-unit"}],
        [{"roleid": "synthetic-role"}], [{"roleid": "synthetic-role"}],
    ]
    monkeypatch.setattr(dataverse_app_user.DataverseClient, "from_environment", lambda **kwargs: client)

    dataverse_app_user.main()

    assert "name eq 'Synthetic Reviewer''s Role'" in client.rows.call_args_list[1].kwargs["$filter"]
    assert "_businessunitid_value eq synthetic-unit" in client.rows.call_args_list[1].kwargs["$filter"]
    client.request.assert_not_called()