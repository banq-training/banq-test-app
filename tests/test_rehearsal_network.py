"""Verify package diagnostics with synthetic responses and no external requests."""

import hashlib
import io
import json
import ssl
import subprocess
from pathlib import Path
from urllib.error import URLError

import pytest

from rehearsal import network


class Response(io.BytesIO):
    """Model the fields used by the public HTTPS probe."""

    status = 200
    url = "https://files.pythonhosted.org/synthetic.whl"


def test_probe_checks_a_real_body_and_locked_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    """An index response must not masquerade as the requested distribution."""
    body = b"synthetic package contents"
    monkeypatch.setattr(network, "urlopen", lambda *args, **kwargs: Response(body))
    result = network.probe("artifact", Response.url, sha256=hashlib.sha256(body).hexdigest())
    assert result.status == "passed"
    assert network.probe("artifact", Response.url, sha256="0" * 64).status == "failed"


def test_probe_rejects_login_pages_and_oversized_downloads(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP 200 alone cannot pass JSON and package checks."""
    monkeypatch.setattr(network, "urlopen", lambda *args, **kwargs: Response(b"<html>login</html>"))
    assert network.probe("index", Response.url, json_body=True).status == "failed"
    assert network.probe("nuget", Response.url, archive=True).status == "failed"
    monkeypatch.setattr(network, "MAX_DOWNLOAD", 3)
    assert network.probe("artifact", Response.url).status == "failed"


def test_tls_error_does_not_expose_proxy_details(monkeypatch: pytest.MonkeyPatch) -> None:
    """Report a useful category without echoing exception messages or secrets."""
    def fail(*args: object, **kwargs: object) -> None:
        raise URLError(ssl.SSLError("synthetic-private-proxy-secret"))

    monkeypatch.setattr(network, "urlopen", fail)
    result = network.probe("artifact", Response.url)
    assert result.status == "failed"
    assert "TLS" in result.detail
    assert "synthetic-private" not in result.detail


def test_probe_keeps_certificate_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    """Native trust still requires a valid server certificate and hostname."""
    def fetch(*args: object, **kwargs: object) -> Response:
        context = kwargs["context"]
        assert isinstance(context, ssl.SSLContext)
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname
        return Response(b"{}")

    monkeypatch.setattr(network, "urlopen", fetch)
    assert network.probe("index", Response.url, json_body=True).status == "passed"
    assert network.probe("index", "http://example.invalid").status == "failed"
    assert network.probe("index", "https://user:secret@example.invalid").status == "failed"


def test_clean_install_does_not_reuse_cache_or_private_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep corporate trust/proxy configuration, not inherited package sources."""
    monkeypatch.setenv("UV_INDEX", "https://private.invalid")
    monkeypatch.setenv("PIP_INDEX_URL", "https://private.invalid")
    monkeypatch.setenv("UV_INSECURE_HOST", "files.pythonhosted.org")
    monkeypatch.setenv("VIRTUAL_ENV", "old-environment")
    monkeypatch.setenv("SSL_CERT_FILE", "approved-ca.pem")
    environment = network.clean_install_environment(tmp_path, native_tls=True)
    assert "UV_INDEX" not in environment
    assert "PIP_INDEX_URL" not in environment
    assert "UV_INSECURE_HOST" not in environment
    assert "VIRTUAL_ENV" not in environment
    assert environment["SSL_CERT_FILE"] == "approved-ca.pem"
    assert environment["UV_NATIVE_TLS"] == "true"
    assert environment["UV_PROJECT_ENVIRONMENT"] == str(tmp_path / "venv")
    assert environment["UV_CACHE_DIR"] == str(tmp_path / "cache")


def test_fresh_install_is_locked_and_propagates_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never turn a failing fresh install into a green preflight."""
    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert "--locked" in command
        assert "--no-config" in command
        assert "--no-sync" not in command
        assert "--no-python-downloads" in command
        return subprocess.CompletedProcess(command, 1, "", "TLS error with synthetic-secret")

    monkeypatch.setattr(network.subprocess, "run", run)
    result = network.fresh_install()
    assert result.status == "failed"
    assert "TLS" in result.detail
    assert "synthetic-secret" not in result.detail


def test_nuget_failure_is_separate_from_python(monkeypatch: pytest.MonkeyPatch) -> None:
    """Optional .NET diagnostics do not block the Python core labs."""
    def check(name: str, url: str, **kwargs: object) -> network.Check:
        optional = name.startswith("nuget")
        return network.Check(name, "failed" if optional else "passed", "synthetic", not optional)

    monkeypatch.setattr(network, "probe", check)
    monkeypatch.setattr(network, "nuget_checks", lambda: [
        network.Check("nuget-index", "failed", "Synthetic network failure", False),
        network.Check("nuget-artifact", "blocked", "No package base address", False),
    ])
    checks = network.network_checks(nuget=True)
    assert len(checks) == 4
    assert all(check.status == "passed" for check in checks if check.required)


def test_network_cli_records_failure_and_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A local result cannot claim to be a Codespaces rehearsal."""
    destination = tmp_path / "network.json"
    monkeypatch.delenv("CODESPACES", raising=False)
    monkeypatch.delenv("UV_INSECURE_HOST", raising=False)
    monkeypatch.delenv("PYTHONHTTPSVERIFY", raising=False)
    monkeypatch.setattr(network, "network_checks", lambda **kwargs: [
        network.Check("pythonhosted-artifact", "failed", "TLS failure"),
    ])
    monkeypatch.setattr("sys.argv", ["network", "--output", str(destination)])
    assert network.main() == 1
    report = json.loads(destination.read_text(encoding="utf-8"))
    assert report["environment"] == "other"
    assert report["fresh_install_requested"] is False


def test_nuget_discovers_package_location(monkeypatch: pytest.MonkeyPatch) -> None:
    """Follow the service's documented base address instead of a fixed path."""
    index = {"resources": [{"@type": "PackageBaseAddress/3.0.0",
                             "@id": "https://api.nuget.org/synthetic-base/"}]}
    monkeypatch.setattr(network, "download", lambda url: json.dumps(index).encode())
    calls = []

    def probe(name: str, url: str, **kwargs: object) -> network.Check:
        calls.append(url)
        assert kwargs["archive"] is True
        return network.Check(name, "passed", "Synthetic package", False)

    monkeypatch.setattr(network, "probe", probe)
    assert all(check.status == "passed" for check in network.nuget_checks())
    assert calls == [
        "https://api.nuget.org/synthetic-base/newtonsoft.json/13.0.3/newtonsoft.json.13.0.3.nupkg",
    ]


def test_nuget_missing_base_does_not_claim_an_artifact_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """A reachable but unsuitable index cannot count as successful package access."""
    monkeypatch.setattr(network, "download", lambda url: b'{"resources": []}')
    checks = network.nuget_checks()
    assert [check.status for check in checks] == ["failed", "blocked"]
    assert not any(check.required for check in checks)