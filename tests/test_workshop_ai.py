"""Check the workshop picture helper without calling Azure: the network is replaced by fakes."""

import base64
import io
import json
import random
import urllib.error
from pathlib import Path

import pytest

from scripts import workshop_ai
from scripts.workshop_ai import BlockedError, BusyError, SetupError, WorkshopAI

SECRET = "synthetic-client-secret-value"
JPEG = b"\xff\xd8\xff\xe0" + b"synthetic-jpeg" * 10
PNG = b"\x89PNG\r\n\x1a\n" + b"synthetic-png" * 10
SETTINGS = {
    "FOUNDRY_TENANT_ID": "00000000-0000-0000-0000-000000000001",
    "FOUNDRY_CLIENT_ID": "00000000-0000-0000-0000-000000000002",
    "FOUNDRY_CLIENT_SECRET": SECRET,
    "FOUNDRY_RESOURCE": "synthetic-foundry",
}


class FakeResponse(io.BytesIO):
    """A urlopen response that works as a context manager."""

    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeService:
    """Answer token and picture requests; replies maps a model name to a list of results."""

    def __init__(self, replies: dict[str, list] | None = None) -> None:
        self.replies = replies or {}
        self.requests: list = []

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        if "login.microsoftonline.com" in request.full_url:
            return FakeResponse(json.dumps({"access_token": "synthetic-token"}).encode())
        model = self.model_of(request)
        reply = self.replies.get(model, [200]).pop(0) if self.replies.get(model) else 200
        if isinstance(reply, bytes):
            return FakeResponse(json.dumps({"data": [{"b64_json": base64.b64encode(reply).decode()}]}).encode())
        if reply == 200:
            return FakeResponse(json.dumps({"data": [{"b64_json": base64.b64encode(JPEG).decode()}]}).encode())
        status, text = reply if isinstance(reply, tuple) else (reply, "synthetic failure")
        raise urllib.error.HTTPError(request.full_url, status, "fail", {}, io.BytesIO(text.encode()))

    @staticmethod
    def model_of(request) -> str:
        body = request.data or b""
        if request.headers.get("Content-type", "").startswith("application/json"):
            return json.loads(body)["model"]
        marker = b'name="model"\r\n\r\n'
        return body.split(marker, 1)[1].split(b"\r\n", 1)[0].decode()

    def picture_calls(self) -> list[str]:
        return [self.model_of(r) for r in self.requests if "login.microsoftonline.com" not in r.full_url]


def workshop(tmp_path: Path, service: FakeService, settings: dict | None = None, run=None) -> WorkshopAI:
    (tmp_path / "site").mkdir(exist_ok=True)
    return WorkshopAI(root=tmp_path, settings=dict(SETTINGS if settings is None else settings), opener=service,
                      run=run or (lambda *a, **k: pytest.fail("az must not be used")),
                      sleep=lambda seconds: None, rng=random.Random(1))


def test_settings_come_from_the_environment_or_the_codespace_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("FOUNDRY_CLIENT_SECRET=from-file\nFOUNDRY_RESOURCE=file-resource\nOTHER=x\n", encoding="utf-8")
    settings = workshop_ai.read_settings({"FOUNDRY_TENANT_ID": "t", "FOUNDRY_CLIENT_ID": "c"}, env_file)
    assert settings["FOUNDRY_CLIENT_SECRET"] == "from-file"
    assert settings["FOUNDRY_RESOURCE"] == "file-resource"
    assert "OTHER" not in settings
    with pytest.raises(SetupError):
        workshop_ai.read_settings({"FOUNDRY_RESOURCE": "https://evil.example"}, tmp_path / "missing")
    # No resource name is built into the public template.
    assert workshop_ai.read_settings({}, tmp_path / "missing")["FOUNDRY_RESOURCE"] == ""


def test_signs_in_with_the_workshop_identity_never_an_api_key(tmp_path: Path) -> None:
    service = FakeService()
    result = workshop(tmp_path, service).draw("a friendly rocket", name="header")
    login, picture = service.requests
    assert "client_credentials" in login.data.decode() and "cognitiveservices.azure.com" in login.data.decode()
    assert picture.headers["Authorization"] == "Bearer synthetic-token"
    assert "Api-key" not in picture.headers and "api-key" not in {k.lower() for k in picture.headers}
    assert picture.full_url.startswith("https://synthetic-foundry.services.ai.azure.com/openai/deployments/")
    assert result["path"] == "site/art/header.jpg"
    assert (tmp_path / "site/art/header.jpg").read_bytes() == JPEG


def test_facilitator_az_login_is_the_only_fallback(tmp_path: Path) -> None:
    calls = []

    def fake_az(command, **kwargs):
        calls.append(command)
        return type("Result", (), {"returncode": 0, "stdout": "az-token\n"})()

    settings = {"FOUNDRY_RESOURCE": "synthetic-foundry"}
    ai = workshop(tmp_path, FakeService(), settings=settings, run=fake_az)
    assert ai.status() == {"ok": True, "signed_in_as": "facilitator az login", "resource": "synthetic-foundry"}
    assert calls[0][:3] == ["az", "account", "get-access-token"]
    nothing = workshop(tmp_path, FakeService(), settings={"FOUNDRY_RESOURCE": "synthetic-foundry"},
                       run=lambda *a, **k: (_ for _ in ()).throw(OSError("no az")))
    with pytest.raises(SetupError, match="not switched on"):
        nothing.status()
    with pytest.raises(SetupError, match="not switched on"):
        workshop(tmp_path, FakeService(), settings={}).status()


def test_busy_models_fail_over_to_the_next_one(tmp_path: Path) -> None:
    service = FakeService({"FLUX-1.1-pro": [429], "FLUX.1-Kontext-pro": [503]})
    result = workshop(tmp_path, service).draw("a team calendar", name="calendar")
    assert result["model"] == "gpt-image-1.5"
    assert service.picture_calls()[-1] == "gpt-image-1.5"
    gpt_request = service.requests[-1]
    assert gpt_request.full_url == "https://synthetic-foundry.openai.azure.com/openai/v1/images/generations"
    assert json.loads(gpt_request.data)["output_format"] == "jpeg"


def test_every_model_busy_gives_a_plain_message(tmp_path: Path) -> None:
    replies = {model: [429, 429] for model in (*workshop_ai.FAST_MODELS, *workshop_ai.BACKUP_MODELS)}
    with pytest.raises(BusyError, match="busy"):
        workshop(tmp_path, FakeService(replies)).draw("anything")
    forbidden = {model: [403] for model in (*workshop_ai.FAST_MODELS, *workshop_ai.BACKUP_MODELS)}
    with pytest.raises(SetupError, match="may not use"):
        workshop(tmp_path, FakeService(forbidden)).draw("anything")


def test_safety_filter_and_oversized_pictures(tmp_path: Path) -> None:
    blocked = FakeService({model: [(400, '{"error":{"code":"content_filter"}}')] for model in workshop_ai.FAST_MODELS})
    with pytest.raises(BlockedError, match="safety filter"):
        workshop(tmp_path, blocked).draw("something")
    huge = b"\xff\xd8\xff" + b"0" * (workshop_ai.MAX_PICTURE_BYTES + 1)
    service = FakeService({"FLUX-1.1-pro": [huge], "FLUX.1-Kontext-pro": [huge]})
    assert workshop(tmp_path, service).draw("big", name="big")["model"] == "gpt-image-1.5"


def test_pictures_stay_inside_site_and_never_overwrite(tmp_path: Path) -> None:
    ai = workshop(tmp_path, FakeService())
    assert ai.draw("one", name="header")["path"] == "site/art/header.jpg"
    assert ai.draw("two", name="header")["path"] == "site/art/header-2.jpg"
    assert ai.draw("three", name="header", replace=True)["path"] == "site/art/header.jpg"
    assert ai.draw("idea", name="hero", folder="site/ideas/team-lunch/art")["path"] == "site/ideas/team-lunch/art/hero.jpg"
    for name in ("../escape", "Header", "with space", "a" * 41, ""):
        with pytest.raises(workshop_ai.AIError):
            ai.draw("x", name=name)
    with pytest.raises(workshop_ai.AIError, match="inside the site folder"):
        ai.draw("x", folder="scripts")
    with pytest.raises(workshop_ai.AIError, match="under 600"):
        ai.draw("x" * 601)


def test_edit_uses_the_editing_model_and_keeps_the_original(tmp_path: Path) -> None:
    service = FakeService({"FLUX.1-Kontext-pro": [PNG]})
    ai = workshop(tmp_path, service)
    (tmp_path / "site/art").mkdir(parents=True)
    (tmp_path / "site/art/header.jpg").write_bytes(JPEG)
    result = ai.edit("site/art/header.jpg", "make it night")
    assert result == {**result, "path": "site/art/header-edited.png", "model": "FLUX.1-Kontext-pro"}
    assert (tmp_path / "site/art/header.jpg").read_bytes() == JPEG
    request = service.requests[-1]
    assert request.full_url.split("?")[0].endswith("/openai/deployments/FLUX.1-Kontext-pro/images/edits")
    assert b'name="image"; filename="header.jpg"' in request.data
    for source in ("scripts/workshop_ai.py", "site/art/missing.jpg", "../outside.jpg"):
        with pytest.raises(workshop_ai.AIError):
            ai.edit(source, "x")


def test_cli_prints_one_json_line_and_never_the_secret(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ai = workshop(tmp_path, FakeService())
    assert workshop_ai.main(["image", "a friendly rocket", "--name", "rocket"], ai=ai) == 0
    assert json.loads(capsys.readouterr().out)["path"] == "site/art/rocket.jpg"
    failing = workshop(tmp_path, FakeService(), settings={**SETTINGS, "FOUNDRY_CLIENT_ID": "bad"})
    failing.opener = lambda request, timeout=None: (_ for _ in ()).throw(
        urllib.error.HTTPError(request.full_url, 401, SECRET, {}, io.BytesIO(SECRET.encode())))
    assert workshop_ai.main(["status"], ai=failing) == 2
    output = capsys.readouterr()
    assert SECRET not in output.out + output.err
    assert json.loads(output.out)["ok"] is False
