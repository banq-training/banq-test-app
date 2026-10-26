"""Call the prepared editor helper without exposing an HTTP control port."""

import argparse
import json
import socket
import stat
import sys
from pathlib import Path


def request_preview(action: str, entry: str | None = None, workspace: Path | None = None) -> dict:
    """Send one bounded request to the workspace-owned Unix socket."""
    root = workspace or Path(__file__).resolve().parents[1]
    directory = root / ".workshop-preview"
    endpoint = directory / "site.sock"
    if action not in {"start", "stop", "status"}:
        raise ValueError("Use start, stop or status only")
    if not endpoint.exists():
        raise RuntimeError(
            "The preview helper is not active. Ask the facilitator to finish Codespace preparation."
        )
    if directory.is_symlink() or endpoint.is_symlink() or not stat.S_ISSOCK(endpoint.stat().st_mode):
        raise RuntimeError("The preview endpoint is not a local Unix socket")
    payload = {"action": action}
    if entry is not None:
        payload["entry"] = entry
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(30)
        connection.connect(str(endpoint))
        connection.sendall(json.dumps(payload).encode() + b"\n")
        response = bytearray()
        while b"\n" not in response:
            chunk = connection.recv(4096)
            if not chunk:
                raise RuntimeError("The preview helper closed without a result")
            response.extend(chunk)
            if len(response) > 65536:
                raise RuntimeError("The preview response exceeded its limit")
    result = json.loads(response.split(b"\n", 1)[0])
    if not result.get("ok"):
        raise RuntimeError(result.get("error", "Preview request failed"))
    return result["result"]


def main() -> int:
    """Provide the three scriptable actions used by the website skills."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "stop", "status"))
    parser.add_argument("entry", nargs="?", help="HTML path relative to site/")
    args = parser.parse_args()
    try:
        print(json.dumps(request_preview(args.action, args.entry), indent=2))
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Website preview: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())