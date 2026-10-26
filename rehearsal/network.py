"""Check real package downloads and fresh installation without weakening TLS."""

import argparse
import hashlib
import io
import json
import os
import platform
import socket
import ssl
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
MAX_DOWNLOAD = 8 * 1024 * 1024


@dataclass(frozen=True)
class Check:
    """Store a bounded diagnostic, never credentials or raw process output."""

    name: str
    status: str
    detail: str
    required: bool = True


def failure_kind(error: BaseException) -> str:
    """Classify common network failures without exposing proxy credentials."""
    reason = error.reason if isinstance(error, URLError) else error
    if isinstance(reason, ssl.SSLError):
        return "TLS trust or handshake failure; check the approved CA bundle and proxy"
    if isinstance(reason, socket.gaierror):
        return "DNS lookup failed"
    if isinstance(reason, TimeoutError):
        return "Network timeout"
    if isinstance(error, HTTPError):
        return f"HTTP {error.code}; check endpoint access and proxy policy"
    return f"Network or response failure ({type(reason).__name__})"


def download(url: str) -> bytes:
    """Read a bounded public HTTPS body with certificate verification enabled."""
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.username or parsed.password:
        raise ValueError("Only credential-free HTTPS probe URLs are allowed")
    request = Request(url, headers={"User-Agent": "workshop-rehearsal/1"})
    with urlopen(request, timeout=20, context=ssl.create_default_context()) as response:
        if response.status != 200 or urlsplit(response.url).scheme != "https":
            raise ValueError("Expected HTTPS HTTP 200")
        body = response.read(MAX_DOWNLOAD + 1)
    if not body or len(body) > MAX_DOWNLOAD:
        raise ValueError("Empty response or download exceeded 8 MiB")
    return body


def probe(
    name: str, url: str, *, sha256: str = "", json_body: bool = False,
    archive: bool = False, required: bool = True,
) -> Check:
    """Download a public endpoint, checking its body rather than only HEAD."""
    try:
        body = download(url)
        if sha256 and hashlib.sha256(body).hexdigest() != sha256:
            return Check(name, "failed", "Downloaded artifact did not match its locked hash", required)
        if json_body and not isinstance(json.loads(body), dict):
            return Check(name, "failed", "Expected a JSON object", required)
        if archive and not zipfile.is_zipfile(io.BytesIO(body)):
            return Check(name, "failed", "Expected a package ZIP, not a proxy/login page", required)
        detail = f"HTTPS GET 200; {len(body)} bytes"
        if sha256:
            detail += "; locked SHA-256 matched"
        return Check(name, "passed", detail, required)
    except (OSError, ValueError) as error:
        return Check(name, "failed", failure_kind(error), required)


def nuget_checks() -> list[Check]:
    """Discover PackageBaseAddress from NuGet's official service index."""
    try:
        body = download("https://api.nuget.org/v3/index.json")
        index = json.loads(body)
        base = next(resource["@id"] for resource in index["resources"]
                    if resource.get("@type") == "PackageBaseAddress/3.0.0")
        parsed = urlsplit(base)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.query or parsed.fragment
                or not parsed.hostname.endswith(".nuget.org")):
            raise ValueError("Expected a public HTTPS NuGet package base address")
        artifact = base.rstrip("/") + "/newtonsoft.json/13.0.3/newtonsoft.json.13.0.3.nupkg"
        return [
            Check("nuget-index", "passed", "HTTPS GET 200; package base address discovered", False),
            probe("nuget-artifact", artifact, archive=True, required=False),
        ]
    except (OSError, ValueError, KeyError, TypeError, AttributeError, StopIteration) as error:
        return [
            Check("nuget-index", "failed", failure_kind(error), False),
            Check("nuget-artifact", "blocked", "No verified package base address from the index", False),
        ]


def network_checks(root: Path = ROOT, *, nuget: bool = False) -> list[Check]:
    """Probe PyPI metadata and one actual locked wheel; NuGet remains optional."""
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    package = next(
        package for package in lock["package"]
        if any(wheel["url"].endswith("-py3-none-any.whl") for wheel in package.get("wheels", []))
    )
    wheel = next(
        wheel for wheel in package["wheels"] if wheel["url"].endswith("-py3-none-any.whl")
    )
    if (urlsplit(wheel["url"]).hostname != "files.pythonhosted.org"
            or not wheel["hash"].startswith("sha256:")):
        raise ValueError("The package probe requires a public PyPI artifact with a SHA-256 hash")
    checks = [
        probe("pypi-metadata", f"https://pypi.org/pypi/{package['name']}/json", json_body=True),
        probe("pythonhosted-artifact", wheel["url"], sha256=wheel["hash"].removeprefix("sha256:")),
    ]
    if nuget:
        checks.extend(nuget_checks())
    return checks


def clean_install_environment(directory: Path, *, native_tls: bool) -> dict[str, str]:
    """Isolate uv's environment and cache while retaining approved network trust."""
    environment = {
        name: value for name, value in os.environ.items()
        if not name.startswith(("UV_", "PIP_")) and name != "VIRTUAL_ENV"
    }
    environment.update({
        "UV_PROJECT_ENVIRONMENT": str(directory / "venv"),
        "UV_CACHE_DIR": str(directory / "cache"),
        "UV_NATIVE_TLS": str(native_tls).lower(),
        "UV_HTTP_TIMEOUT": "20",
        "UV_HTTP_RETRIES": "1",
        "UV_NO_PROGRESS": "1",
    })
    return environment


def fresh_install(root: Path = ROOT, *, native_tls: bool = True) -> Check:
    """Install into new disposable directories; never change the current venv."""
    mode = "system" if native_tls else "bundled"
    command = [
        "uv", "--no-config", "sync", "--locked", "--extra", "dev", "--extra", "web",
        "--python", sys.executable, "--no-python-downloads",
        "--default-index", "https://pypi.org/simple",
    ]
    stage = "temporary directory creation"
    try:
        with tempfile.TemporaryDirectory(prefix="workshop-install-", ignore_cleanup_errors=True) as temporary:
            stage = "uv execution"
            completed = subprocess.run(
                command, cwd=root, env=clean_install_environment(Path(temporary), native_tls=native_tls),
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
            )
            stage = "temporary directory cleanup"
        if completed.returncode:
            output = (completed.stdout + completed.stderr).lower()
            category = "install/build failure"
            if any(word in output for word in ("certificate", "tls", "ssl")):
                category = "TLS trust/handshake failure"
            elif "proxy" in output:
                category = "proxy failure"
            elif "dns" in output or "resolve host" in output:
                category = "DNS failure"
            elif "timeout" in output or "timed out" in output:
                category = "network timeout"
            return Check("fresh-install", "failed", f"{mode} trust; {category}; exit {completed.returncode}")
        return Check("fresh-install", "passed", f"Fresh venv/cache; public PyPI; {mode} trust; locked sync")
    except FileNotFoundError:
        return Check("fresh-install", "blocked", "uv is not installed; inspect Codespaces creation logs")
    except subprocess.TimeoutExpired:
        return Check("fresh-install", "failed", "Fresh locked install exceeded 600 seconds")
    except OSError as error:
        return Check("fresh-install", "failed", f"{stage} failed ({type(error).__name__})")


def main() -> int:
    """Write an environment-specific report and fail on required check failures."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nuget", action="store_true", help="Also diagnose optional .NET package access")
    parser.add_argument("--fresh-install", action="store_true", help="Use a new venv and empty cache")
    parser.add_argument("--bundled-tls", action="store_true", help="Compare uv's bundled trust with system trust")
    parser.add_argument("--output", type=Path, default=Path("rehearsal/results/network.json"))
    arguments = parser.parse_args()
    checks = []
    if os.environ.get("UV_INSECURE_HOST") or os.environ.get("PYTHONHTTPSVERIFY") == "0":
        checks.append(Check("tls-policy", "failed", "Remove TLS-verification bypasses before rehearsal"))
    else:
        try:
            checks.extend(network_checks(nuget=arguments.nuget))
        except (OSError, ValueError, KeyError, StopIteration):
            checks.append(Check("lockfile", "failed", "Cannot select a public locked package probe"))
        if arguments.fresh_install:
            checks.append(fresh_install(native_tls=not arguments.bundled_tls))
    report = {
        "schema_version": 1,
        "checked_at": datetime.now(UTC).isoformat(),
        "environment": "codespaces" if os.environ.get("CODESPACES") == "true" else "other",
        "platform": platform.system(),
        "checks": [asdict(check) for check in checks],
        "fresh_install_requested": arguments.fresh_install,
        "note": "This checks package access, not completion of the nine live labs.",
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return int(any(check.required and check.status != "passed" for check in checks))


if __name__ == "__main__":
    raise SystemExit(main())