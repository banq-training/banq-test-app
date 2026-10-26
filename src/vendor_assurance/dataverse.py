"""Small, explicit Dataverse transport for the synthetic training environment."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any


class DataverseError(RuntimeError):
    """An actionable error that does not expose tokens or service response bodies."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never forward bearer tokens or client-secret POST bodies through redirects."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        """Treat all redirects as service errors, including same-origin redirects."""
        return None


def _open(request: urllib.request.Request, *, timeout: int) -> Any:
    """Use the normal verified HTTPS handler with redirects explicitly disabled."""
    return urllib.request.build_opener(_NoRedirect()).open(request, timeout=timeout)


@dataclass
class DataverseClient:
    """Use environment credentials, or explicitly permit an Azure CLI login."""

    url: str
    allow_cli: bool = False
    timeout: int = 30
    _access_token: str | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.url = self.url.rstrip("/")
        parsed = urllib.parse.urlsplit(self.url)
        if (
            parsed.scheme != "https" or not parsed.netloc or parsed.path
            or parsed.username or parsed.password or parsed.query or parsed.fragment
        ):
            raise ValueError("DATAVERSE_URL must be an HTTPS environment origin, without /api/data/v9.2")

    @classmethod
    def from_environment(cls, *, allow_cli: bool = False) -> DataverseClient:
        """Construct a client without making a network or sign-in request."""
        url = os.environ.get("DATAVERSE_URL", "")
        if not url:
            raise ValueError("Set DATAVERSE_URL to the training environment origin")
        return cls(url, allow_cli=allow_cli)

    def _token(self) -> str:
        if self._access_token:
            return self._access_token
        client_id = os.environ.get("DATAVERSE_CLIENT_ID", "")
        secret = os.environ.get("DATAVERSE_CLIENT_SECRET", "")
        tenant = os.environ.get("DATAVERSE_TENANT_ID", "")
        if all((client_id, secret, tenant)):
            payload = urllib.parse.urlencode({
                "client_id": client_id, "client_secret": secret,
                "scope": f"{self.url}/.default", "grant_type": "client_credentials",
            }).encode()
            request = urllib.request.Request(
                f"https://login.microsoftonline.com/{urllib.parse.quote(tenant, safe='')}/oauth2/v2.0/token",
                data=payload,
            )
            request.add_header("Content-Type", "application/x-www-form-urlencoded")
            try:
                with _open(request, timeout=self.timeout) as response:
                    token_response = json.load(response)
                if not isinstance(token_response, dict):
                    raise ValueError("Expected a token response object")
                self._access_token = token_response["access_token"]
            except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as error:
                raise DataverseError("Dataverse sign-in failed; check the three identity environment variables") from error
        elif any((client_id, secret, tenant)) or not self.allow_cli:
            raise DataverseError("Set all three DATAVERSE_CLIENT_ID, DATAVERSE_CLIENT_SECRET and DATAVERSE_TENANT_ID variables")
        else:
            try:
                result = subprocess.run(
                    [shutil.which("az") or "az", "account", "get-access-token", "--resource",
                     f"{self.url}/", "--query", "accessToken", "-o", "tsv"],
                    capture_output=True, text=True, check=True, timeout=self.timeout,
                )
                self._access_token = result.stdout.strip()
            except (OSError, subprocess.SubprocessError) as error:
                raise DataverseError("Azure CLI sign-in failed; sign in to the training tenant or configure application credentials") from error
        if not isinstance(self._access_token, str) or not self._access_token:
            raise DataverseError("Dataverse sign-in returned no access token")
        return self._access_token

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send one bounded request, rejecting cross-origin pagination links."""
        base = f"{self.url}/api/data/v9.2/"
        url = urllib.parse.urljoin(base, path)
        if not url.startswith(base):
            raise DataverseError("Dataverse returned a link outside the configured environment")
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": f"Bearer {self._token()}", "Content-Type": "application/json",
            "Accept": "application/json", "OData-MaxVersion": "4.0", "OData-Version": "4.0",
        })
        try:
            with _open(request, timeout=self.timeout) as response:
                raw = response.read()
            result = json.loads(raw) if raw else {}
            if not isinstance(result, dict):
                raise ValueError("Expected a JSON object")
            return result
        except urllib.error.HTTPError as error:
            raise DataverseError(
                f"Dataverse returned HTTP {error.code}; check access, table names and request fields",
                error.code,
            ) from None
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            raise DataverseError("Dataverse is unavailable or returned an invalid response") from error

    def rows(self, table: str, **params: str) -> list[dict[str, Any]]:
        """Read all result pages without dropping rows or following unsafe links."""
        path = f"{table}?{urllib.parse.urlencode(params)}"
        seen: set[str] = set()
        rows: list[dict[str, Any]] = []
        while path:
            if path in seen:
                raise DataverseError("Dataverse repeated a pagination link")
            seen.add(path)
            page = self.request("GET", path)
            values = page.get("value")
            if not isinstance(values, list) or any(not isinstance(row, dict) for row in values):
                raise DataverseError("Dataverse did not return a row list")
            rows.extend(values)
            path = page.get("@odata.nextLink", "")
            if not isinstance(path, str):
                raise DataverseError("Dataverse returned an invalid pagination link")
        return rows

    def exists(self, path: str) -> bool:
        """Only a 404 means absent; permission failures must stop provisioning."""
        try:
            self.request("GET", path)
        except DataverseError as error:
            if error.status == 404:
                return False
            raise
        return True