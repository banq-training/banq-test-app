"""Offline checks for shared Dataverse transport behavior."""

import io
import json
import urllib.error
import urllib.request
import urllib.response
from email.message import Message
from unittest.mock import Mock

import pytest

from src.vendor_assurance import dataverse
from src.vendor_assurance.dataverse import DataverseClient, DataverseError


def test_construction_never_authenticates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing or configuring a helper cannot contact a cloud service."""
    run = Mock(side_effect=AssertionError("unexpected process"))
    monkeypatch.setattr("subprocess.run", run)

    DataverseClient("https://synthetic.example", allow_cli=True)
    run.assert_not_called()


def test_requests_have_timeouts_and_keep_errors_private(monkeypatch: pytest.MonkeyPatch) -> None:
    """Do not leak a server response or token to the workshop page."""
    client = DataverseClient("https://synthetic.example")
    monkeypatch.setattr(client, "_token", lambda: "synthetic-token")
    opening = Mock(side_effect=urllib.error.HTTPError(
        "https://synthetic.example", 403, "Forbidden", {}, io.BytesIO(b"private details"),
    ))
    monkeypatch.setattr(dataverse, "_open", opening)

    with pytest.raises(DataverseError, match="HTTP 403") as caught:
        client.request("GET", "reviews")

    assert "private details" not in str(caught.value)
    assert opening.call_args.kwargs["timeout"] == 30


def test_pagination_reads_every_page(monkeypatch: pytest.MonkeyPatch) -> None:
    """A full lab table may be larger than one service page."""
    client = DataverseClient("https://synthetic.example")
    request = Mock(side_effect=[
        {"value": [{"vendor": "Synthetic A"}], "@odata.nextLink": "reviews?$skiptoken=2"},
        {"value": [{"vendor": "Synthetic B"}]},
    ])
    monkeypatch.setattr(client, "request", request)

    assert len(client.rows("reviews")) == 2
    assert request.call_count == 2


def test_pagination_cannot_forward_credentials_elsewhere(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reject a foreign URL before obtaining or sending a token."""
    client = DataverseClient("https://synthetic.example")
    token = Mock(side_effect=AssertionError("must not authenticate"))
    monkeypatch.setattr(client, "_token", token)

    with pytest.raises(DataverseError, match="outside"):
        client.request("GET", "https://other.example/api/data/v9.2/reviews")


def test_client_credentials_do_not_require_an_azure_login(monkeypatch: pytest.MonkeyPatch) -> None:
    """The attendee seed script can use the same environment as the app."""
    for key in ("CLIENT_ID", "CLIENT_SECRET", "TENANT_ID"):
        monkeypatch.setenv(f"DATAVERSE_{key}", "synthetic")
    response = io.BytesIO(json.dumps({"access_token": "synthetic-token"}).encode())
    opening = Mock(return_value=response)
    monkeypatch.setattr(dataverse, "_open", opening)
    client = DataverseClient("https://synthetic.example", allow_cli=True)

    assert client._token() == "synthetic-token"
    assert client._token() == "synthetic-token"
    assert opening.call_count == 1


@pytest.mark.parametrize("payload", [[], "invalid", {"access_token": 123}])
def test_malformed_token_responses_are_readable_errors(
    monkeypatch: pytest.MonkeyPatch, payload: object,
) -> None:
    """Invalid service data must not turn into an uncaught type error."""
    for key in ("CLIENT_ID", "CLIENT_SECRET", "TENANT_ID"):
        monkeypatch.setenv(f"DATAVERSE_{key}", "synthetic")
    response = io.BytesIO(json.dumps(payload).encode())
    monkeypatch.setattr(dataverse, "_open", Mock(return_value=response))

    with pytest.raises(DataverseError):
        DataverseClient("https://synthetic.example")._token()


@pytest.mark.parametrize("link", [None, 1, [], {}])
def test_invalid_pagination_is_not_silently_accepted(
    monkeypatch: pytest.MonkeyPatch, link: object,
) -> None:
    """A corrupt continuation must not masquerade as a complete result set."""
    client = DataverseClient("https://synthetic.example")
    monkeypatch.setattr(client, "request", Mock(return_value={"value": [], "@odata.nextLink": link}))

    with pytest.raises(DataverseError, match="pagination link"):
        client.rows("reviews")


@pytest.mark.parametrize("status,exists", [(404, False), (403, None)])
def test_only_not_found_is_treated_as_absent(
    monkeypatch: pytest.MonkeyPatch, status: int, exists: bool | None,
) -> None:
    """Authorization failures are not mistaken for a missing table."""
    client = DataverseClient("https://synthetic.example")
    monkeypatch.setattr(client, "request", Mock(side_effect=DataverseError("failed", status)))

    if exists is None:
        with pytest.raises(DataverseError):
            client.exists("EntityDefinitions")
    else:
        assert client.exists("EntityDefinitions") is exists


@pytest.mark.parametrize("code", [301, 302, 303, 307, 308])
@pytest.mark.parametrize("location", [
    "https://other.example/api/data/v9.2/reviews",
    "https://synthetic.example/api/data/v9.2/other",
])
def test_authenticated_requests_never_follow_redirects(
    code: int, location: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise urllib's real redirect machinery with an offline HTTPS transport."""
    attempts = []

    class RedirectTransport(urllib.request.HTTPSHandler):
        """Return a synthetic redirect without opening a socket."""

        def https_open(self, request: urllib.request.Request) -> urllib.response.addinfourl:
            """Record every attempted send, including any unsafe follow-up."""
            attempts.append(request)
            headers = Message()
            headers["Location"] = location
            response = urllib.response.addinfourl(io.BytesIO(b""), headers, request.full_url, code)
            response.msg = "Synthetic redirect"
            return response

    original_builder = urllib.request.build_opener
    monkeypatch.setattr(urllib.request, "build_opener", lambda *handlers: original_builder(
        *handlers, RedirectTransport(),
    ))
    client = DataverseClient("https://synthetic.example")
    monkeypatch.setattr(client, "_token", lambda: "synthetic-token")
    with pytest.raises(DataverseError) as caught:
        client.request("GET", "reviews")
    assert caught.value.status == code
    assert len(attempts) == 1
    assert attempts[0].get_header("Authorization") == "Bearer synthetic-token"


def test_token_exchange_uses_the_same_no_redirect_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    """Client credentials must not be forwarded by token-endpoint redirects either."""
    for key in ("CLIENT_ID", "CLIENT_SECRET", "TENANT_ID"):
        monkeypatch.setenv(f"DATAVERSE_{key}", "synthetic")
    opening = Mock(side_effect=urllib.error.HTTPError(
        "https://login.microsoftonline.com/synthetic", 307, "Redirect", {}, io.BytesIO(b""),
    ))
    monkeypatch.setattr(dataverse, "_open", opening)
    with pytest.raises(DataverseError, match="sign-in failed"):
        DataverseClient("https://synthetic.example")._token()
    assert opening.call_count == 1
    assert opening.call_args.args[0].get_method() == "POST"