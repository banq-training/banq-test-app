"""Draw or edit a picture for a workshop website with the workshop's Foundry image models.

Attendees do not run this by hand: Copilot runs it for them, for example from a learner's own
/make-image skill. It signs in as the workshop identity that the facilitator stores as GitHub
Codespaces secrets (FOUNDRY_TENANT_ID, FOUNDRY_CLIENT_ID, FOUNDRY_CLIENT_SECRET), so nobody
logs in and no API key exists anywhere. FOUNDRY_RESOURCE names the Foundry resource. A
facilitator signed in with `az login` can use it too, after exporting FOUNDRY_RESOURCE.
Pictures are saved as ordinary files under site/, so the page itself stays static.

    python3 scripts/workshop_ai.py image "a friendly rocket over a desk" --name header
    python3 scripts/workshop_ai.py edit site/art/header.jpg "make it a night scene"
    python3 scripts/workshop_ai.py status
"""

import argparse
import base64
import json
import os
import random
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODESPACE_ENV = Path("/workspaces/.codespaces/shared/.env")
SCOPE = "https://cognitiveservices.azure.com/.default"
API_VERSION = "2025-04-01-preview"
CREDENTIAL_KEYS = ("FOUNDRY_TENANT_ID", "FOUNDRY_CLIENT_ID", "FOUNDRY_CLIENT_SECRET")
# The two fastest models (about 2-4 seconds, 30 pictures a minute each) share the load first;
# the gpt-image models are slower overflow when both are busy.
FAST_MODELS = ("FLUX-1.1-pro", "FLUX.1-Kontext-pro")
BACKUP_MODELS = ("gpt-image-1.5", "gpt-image-1", "gpt-image-1-mini")
EDIT_MODELS = ("FLUX.1-Kontext-pro", "gpt-image-1.5")
MAX_PROMPT = 600
MAX_PICTURE_BYTES = 1_900_000  # Published websites allow 2 MiB per file.
MAX_SOURCE_BYTES = 4 * 1024 * 1024
NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,39}")
PICTURE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp")
GUIDANCE = (
    "Friendly illustration for a fictional workshop website. "
    "No words, letters, logos, brands, or real people. "
)


class AIError(RuntimeError):
    """A problem explained in plain words for the learner; exit_code tells scripts what kind."""

    exit_code = 1


class SetupError(AIError):
    """The workshop identity is not available in this Codespace."""

    exit_code = 2


class BlockedError(AIError):
    """The request was refused by the content-safety filter."""

    exit_code = 3


class BusyError(AIError):
    """Every model was busy or unavailable."""

    exit_code = 4


def read_settings(env=None, env_file: Path = CODESPACE_ENV) -> dict:
    """Return the workshop identity from the environment, or from the Codespace's env file."""
    env = os.environ if env is None else env
    keys = (*CREDENTIAL_KEYS, "FOUNDRY_RESOURCE")
    settings = {key: env.get(key, "").strip() for key in keys}
    if not all(settings[key] for key in CREDENTIAL_KEYS) and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key in keys and not settings[key]:
                settings[key] = value.strip()
    if settings["FOUNDRY_RESOURCE"] and not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}", settings["FOUNDRY_RESOURCE"]):
        raise SetupError("FOUNDRY_RESOURCE must be a plain Foundry resource name.")
    return settings


def picture_suffix(data: bytes) -> str:
    """Name the file after what the model actually returned."""
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    raise AIError("The model did not return a picture.")


class WorkshopAI:
    """Talk to the workshop's Foundry resource with an Entra ID token, never an API key."""

    def __init__(self, root: Path = ROOT, settings: dict | None = None, opener=urllib.request.urlopen,
                 run=subprocess.run, sleep=time.sleep, rng: random.Random | None = None) -> None:
        self.root = root.resolve()
        self.site = self.root / "site"
        self.settings = settings if settings is not None else read_settings()
        self.opener = opener
        self.run = run
        self.sleep = sleep
        self.rng = rng or random.Random()
        self._token = ""
        self.signed_in_as = ""

    def token(self) -> str:
        """Sign in as the workshop identity, or as a facilitator who ran `az login`."""
        if self._token:
            return self._token
        if not self.settings.get("FOUNDRY_RESOURCE"):
            raise SetupError("AI pictures are not switched on in this Codespace yet. Ask a helper.")
        if all(self.settings.get(key) for key in CREDENTIAL_KEYS):
            form = urllib.parse.urlencode({
                "grant_type": "client_credentials",
                "client_id": self.settings["FOUNDRY_CLIENT_ID"],
                "client_secret": self.settings["FOUNDRY_CLIENT_SECRET"],
                "scope": SCOPE,
            }).encode()
            tenant = urllib.parse.quote(self.settings["FOUNDRY_TENANT_ID"], safe="")
            request = urllib.request.Request(
                f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token", data=form, method="POST")
            try:
                with self.opener(request, timeout=30) as response:
                    self._token = json.loads(response.read())["access_token"]
            except (urllib.error.URLError, KeyError, ValueError, OSError):
                raise SetupError(
                    "The workshop identity could not sign in. Ask a helper to check the Codespaces secrets."
                ) from None
            self.signed_in_as = "workshop identity"
            return self._token
        try:
            result = self.run(
                ["az", "account", "get-access-token", "--resource", "https://cognitiveservices.azure.com",
                 "--query", "accessToken", "-o", "tsv"],
                capture_output=True, text=True, check=False, timeout=60)
        except (OSError, subprocess.SubprocessError):
            result = None
        if result is not None and result.returncode == 0 and result.stdout.strip():
            self._token = result.stdout.strip()
            self.signed_in_as = "facilitator az login"
            return self._token
        raise SetupError("AI pictures are not switched on in this Codespace yet. Ask a helper.")

    def _post(self, url: str, *, payload: dict | None = None, fields: dict | None = None,
              image: tuple[str, bytes] | None = None) -> tuple[int, object]:
        """POST JSON or a multipart form; return the status and parsed JSON or error text."""
        headers = {"Authorization": f"Bearer {self.token()}"}
        if image is None:
            body = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        else:
            boundary = uuid.uuid4().hex
            parts = []
            for key, value in (fields or {}).items():
                parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
            filename, data = image
            kind = {".png": "image/png", ".webp": "image/webp"}.get(Path(filename).suffix.lower(), "image/jpeg")
            parts.append(
                f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{filename}"\r\n'
                f"Content-Type: {kind}\r\n\r\n".encode() + data + b"\r\n")
            parts.append(f"--{boundary}--\r\n".encode())
            body = b"".join(parts)
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with self.opener(request, timeout=150) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode("utf-8", "replace")[:500]
        except (urllib.error.URLError, OSError, ValueError) as error:
            return 0, str(error)[:200]

    def _endpoint(self, model: str, action: str) -> str:
        resource = self.settings["FOUNDRY_RESOURCE"]
        if model.startswith("gpt-image"):
            return f"https://{resource}.openai.azure.com/openai/v1/images/{action}"
        return (f"https://{resource}.services.ai.azure.com/openai/deployments/"
                f"{urllib.parse.quote(model)}/images/{action}?api-version={API_VERSION}")

    def _attempt(self, models: tuple[str, ...], call) -> tuple[str, bytes]:
        """Try each model in turn, then once more after a short pause if all were busy."""
        statuses = []
        for round_number in range(2):
            busy = False
            for model in models:
                status, data = call(model)
                statuses.append(status)
                if status == 200 and isinstance(data, dict):
                    try:
                        picture = base64.b64decode(data["data"][0]["b64_json"])
                        picture_suffix(picture)
                    except (KeyError, IndexError, TypeError, ValueError, AIError):
                        continue
                    if len(picture) <= MAX_PICTURE_BYTES:
                        return model, picture
                    continue
                text = str(data).lower()
                if status == 400 and any(word in text for word in ("content_filter", "content filter", "safety", "moderation")):
                    raise BlockedError("The safety filter stopped this picture. Try different, friendly words.")
                busy = busy or status in (0, 408, 429) or status >= 500
            if not busy or round_number:
                break
            self.sleep(8)
        if statuses and all(status in (401, 403) for status in statuses):
            raise SetupError("The workshop identity may not use the picture models. Ask a helper.")
        raise BusyError("The picture models are busy right now. Wait a minute and try again.")

    def _check_prompt(self, prompt: str) -> str:
        prompt = " ".join(prompt.split())
        if not prompt:
            raise AIError("Describe the picture in a few words.")
        if len(prompt) > MAX_PROMPT:
            raise AIError(f"Keep the description under {MAX_PROMPT} characters.")
        return GUIDANCE + prompt

    def _target(self, folder: str, name: str, suffix: str, replace: bool) -> Path:
        """Choose a file inside site/, never overwriting unless asked."""
        if not NAME.fullmatch(name):
            raise AIError("Use a short lowercase name such as header or team-photo.")
        directory = (self.root / folder).resolve()
        if directory != self.site.resolve() and self.site.resolve() not in directory.parents:
            raise AIError("Pictures are saved inside the site folder only.")
        directory.mkdir(parents=True, exist_ok=True)
        candidate = directory / f"{name}{suffix}"
        counter = 2
        while not replace and candidate.exists():
            candidate = directory / f"{name}-{counter}{suffix}"
            counter += 1
        return candidate

    def _save(self, folder: str, name: str, picture: bytes, replace: bool) -> Path:
        target = self._target(folder, name, picture_suffix(picture), replace)
        partial = target.with_name(f".{target.name}.partial")
        partial.write_bytes(picture)
        partial.replace(target)
        return target

    def draw(self, prompt: str, name: str = "picture", folder: str = "site/art", replace: bool = False) -> dict:
        """Create a new picture and save it under site/."""
        full_prompt = self._check_prompt(prompt)
        self._target(folder, name, ".jpg", replace)
        fast = list(FAST_MODELS)
        self.rng.shuffle(fast)

        def call(model: str):
            payload = {"model": model, "prompt": full_prompt, "size": "1024x1024", "n": 1, "output_format": "jpeg"}
            if model.startswith("gpt-image"):
                payload |= {"quality": "low", "output_compression": 85}
            return self._post(self._endpoint(model, "generations"), payload=payload)

        started = time.monotonic()
        model, picture = self._attempt((*fast, *BACKUP_MODELS), call)
        target = self._save(folder, name, picture, replace)
        return self._result(target, model, started)

    def edit(self, source: str, prompt: str, name: str = "", replace: bool = False) -> dict:
        """Change an existing picture and save the result as a new file next to it."""
        path = (self.root / source).resolve()
        if self.site.resolve() not in path.parents or path.suffix.lower() not in PICTURE_SUFFIXES:
            raise AIError("Choose a .jpg, .png, or .webp picture inside the site folder.")
        if not path.is_file():
            raise AIError(f"There is no picture at {source}.")
        data = path.read_bytes()
        if len(data) > MAX_SOURCE_BYTES:
            raise AIError("That picture is too large to edit; use one under 4 MiB.")
        full_prompt = self._check_prompt(prompt)
        name = name or f"{path.stem[:33]}-edited"
        folder = str(path.parent.relative_to(self.root))
        self._target(folder, name, ".jpg", replace)

        def call(model: str):
            fields = {"model": model, "prompt": full_prompt, "n": "1"}
            if model.startswith("gpt-image"):
                fields |= {"quality": "low", "output_format": "jpeg"}
            return self._post(self._endpoint(model, "edits"), fields=fields, image=(path.name, data))

        started = time.monotonic()
        model, picture = self._attempt(EDIT_MODELS, call)
        target = self._save(folder, name, picture, replace)
        return self._result(target, model, started)

    def _result(self, target: Path, model: str, started: float) -> dict:
        return {
            "ok": True,
            "path": target.relative_to(self.root).as_posix(),
            "model": model,
            "seconds": round(time.monotonic() - started, 1),
        }

    def status(self) -> dict:
        """Check sign-in without spending a picture."""
        self.token()
        return {"ok": True, "signed_in_as": self.signed_in_as, "resource": self.settings["FOUNDRY_RESOURCE"]}


def main(argv: list[str] | None = None, ai: WorkshopAI | None = None) -> int:
    """Print one JSON line, so Copilot can read the result and tell the learner what happened."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    draw = commands.add_parser("image", help="draw a new picture")
    draw.add_argument("prompt")
    draw.add_argument("--name", default="picture", help="file name without extension, such as header")
    draw.add_argument("--folder", default="site/art", help="folder inside site/")
    draw.add_argument("--replace", action="store_true", help="overwrite a picture with the same name")
    change = commands.add_parser("edit", help="change an existing picture")
    change.add_argument("source", help="picture inside site/, such as site/art/header.jpg")
    change.add_argument("prompt")
    change.add_argument("--name", default="", help="new file name without extension")
    change.add_argument("--replace", action="store_true")
    commands.add_parser("status", help="check that AI pictures are switched on")
    args = parser.parse_args(argv)
    try:
        ai = ai or WorkshopAI()
        if args.command == "image":
            result = ai.draw(args.prompt, args.name, args.folder, args.replace)
        elif args.command == "edit":
            result = ai.edit(args.source, args.prompt, args.name, args.replace)
        else:
            result = ai.status()
    except AIError as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return error.exit_code
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
