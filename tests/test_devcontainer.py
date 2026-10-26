"""Check the startup contract without requiring a container runtime."""

import asyncio
import json
import os
import re
import shutil
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import yaml

from scripts import check_workshop_mcp, enable_playwright_mcp


def test_machine_requirements_and_notes() -> None:
    """Keep machine minimums explicit and documentation out of schema properties."""
    config = json.loads(Path(".devcontainer/devcontainer.json").read_text(encoding="utf-8"))

    assert config["hostRequirements"] == {"cpus": 4, "memory": "16gb", "storage": "32gb"}
    assert "//" not in config


def test_codespaces_start_from_the_ready_made_image() -> None:
    """Attendee copies download one small published image instead of installing tools at start-up."""
    config = json.loads(Path(".devcontainer/devcontainer.json").read_text(encoding="utf-8"))
    workflow = yaml.load(
        Path(".github/workflows/codespace-image.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    assert config["image"] == f"{workflow['env']['IMAGE']}:latest"
    # Features would rebuild the image in every Codespace; attendees never use the Azure CLI.
    assert "features" not in config and "build" not in config
    # Plain Debian carries no dev container metadata, so the user is named here.
    assert config["remoteUser"] == "vscode"
    # Copilot CLI is a large download needed from Day 3: it installs after the editor opens.
    assert config["postCreateCommand"] == "bash -o pipefail .devcontainer/setup.sh cli"
    job = workflow["jobs"]["build"]
    assert job["if"] == "github.repository == 'agentic-dev-labs/copilot-hackathon-template'"
    steps = "\n".join(step.get("run", "") for step in job["steps"])
    assert "--network none" in steps and "--offline" in steps
    assert steps.index("--network none") < steps.index("push=true")
    assert steps.index(".devcontainer/setup.sh cli") < steps.index("push=true")
    assert "compression=zstd" in steps

    dockerfile = Path(".github/codespace-image/Dockerfile").read_text(encoding="utf-8")
    assert dockerfile.startswith("# The ready-made Codespace image.")
    # Measured 19 October 2026: devcontainer base images were mostly unused tools, and GitHub's
    # default universal image was not cached for derived images, so the image starts from Debian.
    assert re.findall(r"^FROM (\S+)", dockerfile, re.M) == ["debian:bookworm-slim"]
    assert "useradd --create-home --shell /bin/bash --uid 1000 vscode" in dockerfile
    assert "uv/0.9.7/install.sh" in dockerfile and "uv python install 3.12" in dockerfile
    assert "gh.io/copilot-install" not in dockerfile
    assert "uv sync --locked --extra dev --extra web" in dockerfile
    assert "npm ci --prefix website-preview --ignore-scripts" in dockerfile
    assert "--no-sandbox" not in dockerfile and "insecure" not in dockerfile.lower()
    # The image's build context holds only the dependency lists: no notes, secrets or learner work.
    ignore = Path(".github/codespace-image/Dockerfile.dockerignore").read_text(encoding="utf-8")
    rules = [line for line in ignore.splitlines() if line and not line.startswith("#")]
    assert rules == [
        "*",
        "!pyproject.toml",
        "!uv.lock",
        "!.devcontainer/website-preview/package.json",
        "!.devcontainer/website-preview/package-lock.json",
    ]
    for source in re.findall(r"^COPY (?!--from)(?:--chown=\S+ )?(.+) \S+$", dockerfile, re.M):
        for path in source.split():
            assert f"!{path}" in rules, path


def test_beginner_preview_is_installed_and_scoped_to_the_website() -> None:
    """Fresh Codespaces get a server-free editor preview: no ports, sign-in, or browser tabs."""
    config = json.loads(Path(".devcontainer/devcontainer.json").read_text(encoding="utf-8"))
    settings = json.loads(Path(".vscode/settings.json").read_text(encoding="utf-8"))
    assert "ms-vscode.live-server" not in config["customizations"]["vscode"]["extensions"]
    assert config["forwardPorts"] == [8000]
    assert not any(key.startswith("livePreview.") for key in settings)
    assert config["postAttachCommand"]["website-preview"] == "bash .devcontainer/setup.sh preview"
    manifest = json.loads(Path(".devcontainer/website-preview/package.json").read_text())
    assert manifest["name"] == "workshop-site-preview"
    assert manifest["extensionKind"] == ["workspace"]
    assert manifest["capabilities"]["untrustedWorkspaces"]["supported"] is False
    assert manifest["files"] == ["extension.cjs", "controller.cjs", "assistant.cjs", "photo.cjs"]
    extension = Path(".devcontainer/website-preview/extension.cjs").read_text()
    assert "createWebviewPanel" in extension
    assistant = Path(".devcontainer/website-preview/assistant.cjs").read_text()
    photo = Path(".devcontainer/website-preview/photo.cjs").read_text()
    # The preview, its page assistant and its photo studio start no processes, servers, or ports.
    for source in (extension, assistant, photo):
        assert "child_process" not in source and "createServer(" not in source.replace("net.createServer(", "")
    assert "onDidReceiveMessage" in extension and "createChatHandler" in extension
    assert "createPhotoHandler" in extension
    for source in (assistant, photo):
        assert "api-key" not in source.lower()
    assert "Bearer" in assistant
    assert "connect-src ${resources}" in extension
    assert "localResourceRoots: [site]" in extension


def test_website_helper_ownership_contracts() -> None:
    """Exercise the Node helper without depending on a real editor or browser."""
    result = subprocess.run(
        ["node", "--test", ".devcontainer/website-preview/controller.test.cjs",
         ".devcontainer/website-preview/assistant.test.cjs",
         ".devcontainer/website-preview/photo.test.cjs"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_website_toolchain_is_pinned_and_locked() -> None:
    """The only preparation dependency is the pinned extension packager."""
    package = json.loads(Path(".devcontainer/website-preview/package.json").read_text())
    lock = json.loads(Path(".devcontainer/website-preview/package-lock.json").read_text())
    assert "dependencies" not in package
    for name, version in package["devDependencies"].items():
        assert version[0].isdigit()
        assert lock["packages"][f"node_modules/{name}"]["version"] == version


def test_terminal_uses_the_installed_virtual_environment() -> None:
    """Bare Python and CLI commands must resolve to the project environment."""
    config = json.loads(Path(".devcontainer/devcontainer.json").read_text(encoding="utf-8"))

    assert config["waitFor"] == "updateContentCommand"
    assert config["updateContentCommand"] == "bash .devcontainer/setup.sh"
    setup = Path(".devcontainer/setup.sh").read_text(encoding="utf-8")
    assert "uv sync --locked --extra dev --extra web" in setup
    assert "npm ci --prefix .devcontainer/browser --ignore-scripts" in setup
    assert "--requirement .devcontainer/research-requirements.txt" in setup
    assert "install --with-deps chromium" in setup
    assert "bash .devcontainer/mcp.sh check-browser" in setup
    assert "bash .devcontainer/mcp.sh check-research" in setup
    assert 'case "${1:-core}" in' in setup
    assert set(config["onCreateCommand"]) == {"uv"}
    assert config["postCreateCommand"] == "bash -o pipefail .devcontainer/setup.sh cli"
    assert config["remoteEnv"]["UV_NATIVE_TLS"] == "true"
    assert 'export UV_NATIVE_TLS="${UV_NATIVE_TLS:-true}"' in setup
    assert "python -m rehearsal.network" in setup
    assert "exit 1" in setup
    assert config["remoteEnv"]["VIRTUAL_ENV"] == "${containerWorkspaceFolder}/.venv"
    assert config["remoteEnv"]["PATH"].startswith("${containerWorkspaceFolder}/.venv/bin:")


def test_python_environment_is_prepared_without_ruff_editor_extension() -> None:
    """Python tooling is ready, and no Ruff editor pop-up greets beginners (25 October 2026).

    Ruff still lints through `uv run ruff check .` and CI; only the editor extension is gone,
    because it showed a startup notice in every fresh Codespace.
    """
    config = json.loads(Path(".devcontainer/devcontainer.json").read_text(encoding="utf-8"))
    extensions = set(config["customizations"]["vscode"]["extensions"])
    required_extensions = {"ms-python.python", "ms-python.vscode-python-envs"}

    assert required_extensions <= extensions
    assert "charliermarsh.ruff" not in extensions
    assert "[python]" not in config["customizations"]["vscode"]["settings"]
    setup = Path(".devcontainer/setup.sh").read_text(encoding="utf-8")
    for extension in required_extensions:
        assert f'ensure_editor_extension "{extension}"' in setup
    assert "charliermarsh.ruff" not in setup


def test_terminals_are_not_interrupted_while_the_codespace_opens() -> None:
    """Terminal auto-activation typed Ctrl+C into the preview install (observed 19 October 2026)."""
    settings = json.loads(Path(".vscode/settings.json").read_text(encoding="utf-8"))
    # The project environment is already first on PATH, so activation adds nothing.
    assert settings["python.terminal.activateEnvironment"] is False
    assert settings["python-envs.terminal.autoActivationType"] == "off"
    setup = Path(".devcontainer/setup.sh").read_text(encoding="utf-8")
    preview = setup.split("\tpreview)", 1)[1].split("\t;;", 1)[0]
    assert "trap '' INT" in preview
    assert preview.index("trap '' INT") < preview.index("code --install-extension")


@pytest.mark.skipif(os.name == "nt", reason="Codespaces startup executes in Linux Bash")
@pytest.mark.parametrize("missing_environment_provider", [False, True])
def test_preview_setup_repairs_python_environment_provider(
    tmp_path: Path, missing_environment_provider: bool
) -> None:
    """Post-attach setup repairs old Codespaces once and stays quiet afterward."""
    tools = tmp_path / ".local" / "bin"
    tools.mkdir(parents=True)
    log = tmp_path / "calls.log"
    version = json.loads(Path(".devcontainer/website-preview/package.json").read_text())["version"]
    extensions = ["ms-python.python", "ms-python.vscode-python-envs"]
    if missing_environment_provider:
        extensions.remove("ms-python.vscode-python-envs")
    installed = "\\n".join(extensions)

    code = tools / "code"
    code.write_text(
        "#!/bin/sh\n"
        'case "$*" in\n'
        f'  "--list-extensions") printf \'%b\\n\' "{installed}" ;;\n'
        f"  \"--list-extensions --show-versions\") printf '%s\\n' "
        f'"workshop-local.workshop-site-preview@{version}" ;;\n'
        '  --install-extension\\ *) printf \'%s\\n\' "$*" >> "$SETUP_CALL_LOG" ;;\n'
        "  *) exit 97 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    code.chmod(0o755)
    node = tools / "node"
    node.write_text(f"#!/bin/sh\nprintf '%s\\n' '{version}'\n", encoding="utf-8")
    node.chmod(0o755)

    result = subprocess.run(
        ["bash", ".devcontainer/setup.sh", "preview"],
        env={**os.environ, "HOME": str(tmp_path), "SETUP_CALL_LOG": str(log)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    expected = ["--install-extension ms-python.vscode-python-envs"]
    assert calls == (expected if missing_environment_provider else [])
    assert ("Run Developer: Reload Window once" in result.stdout) is missing_environment_provider
    # The one terminal beginners see ends with the welcome, not packaging output.
    assert result.stdout.rstrip().endswith("DAY-2.md on Tuesday, and so on.")
    assert "Reload Window." not in result.stdout.replace("Reload Window once", "")


@pytest.mark.skipif(os.name == "nt", reason="Codespaces startup executes in Linux Bash")
@pytest.mark.parametrize("install_status", [0, 23])
def test_core_setup_prepares_website_tools_but_not_advanced_tools(
    tmp_path: Path, install_status: int
) -> None:
    """Core prepares Python and frontend dependencies without creating a learner page."""
    tools = tmp_path / ".local" / "bin"
    tools.mkdir(parents=True)
    log = tmp_path / "calls.log"
    for name in ("uv", "npm", "node", "curl", "copilot"):
        executable = tools / name
        status = install_status if name == "uv" else (0 if name == "npm" else 97)
        executable.write_text(
            f'#!/bin/sh\nprintf "%s\\n" "{name} $*" >> "$SETUP_CALL_LOG"\nexit {status}\n',
            encoding="utf-8",
        )
        executable.chmod(0o755)
    result = subprocess.run(
        ["bash", ".devcontainer/setup.sh"],
        env={
            **os.environ,
            "HOME": str(tmp_path),
            "SETUP_CALL_LOG": str(log),
            "GITHUB_REPOSITORY": "synthetic-owner/attendee-copy",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == (0 if install_status == 0 else 1)
    expected = ["uv sync --locked --extra dev --extra web"]
    if not install_status:
        expected.append(
            "npm ci --prefix .devcontainer/website-preview --ignore-scripts --no-audit --no-fund"
        )
    assert log.read_text(encoding="utf-8").splitlines() == expected
    if install_status:
        assert "TLS verification remains enabled" in result.stderr


@pytest.mark.skipif(os.name == "nt", reason="Codespaces startup executes in Linux Bash")
@pytest.mark.parametrize(
    "repository,hidden",
    [
        ("agentic-dev-labs/copilot-hackathon-template", True),
        ("agentic-dev-labs/nn-na-2026-10-team-01", False),
        ("someone/copilot-hackathon-template", False),
    ],
)
def test_only_the_template_codespace_hides_a_demo_site(
    tmp_path: Path, repository: str, hidden: bool
) -> None:
    """Attendee copies inherit .gitignore, so they must still see and commit their site/."""
    rules = Path(".gitignore").read_text(encoding="utf-8").splitlines()
    assert not [rule for rule in rules if "site" in rule and not rule.startswith("#")]
    assert "bash .devcontainer/hide-template-demo.sh" in Path(".devcontainer/setup.sh").read_text(
        encoding="utf-8"
    )
    script = Path(".devcontainer/hide-template-demo.sh").resolve()
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "site" / "js").mkdir(parents=True)
    for name in ("README.md", "index.html", "js/workshop.js"):
        (tmp_path / "site" / name).write_text("synthetic", encoding="utf-8")
    for _ in range(2):
        subprocess.run(
            ["bash", str(script)],
            cwd=tmp_path,
            env={**os.environ, "GITHUB_REPOSITORY": repository},
            check=True,
        )
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert "?? site/README.md" in status
    assert ("?? site/index.html" in status) is not hidden
    assert ("?? site/js/workshop.js" in status) is not hidden
    exclude_file = tmp_path / ".git" / "info" / "exclude"
    exclude = exclude_file.read_text(encoding="utf-8") if exclude_file.exists() else ""
    assert exclude.count("/site/*") == (1 if hidden else 0)


@pytest.mark.skipif(os.name == "nt", reason="Codespaces startup executes in Linux Bash")
@pytest.mark.parametrize(
    "preinstalled,install_status,version_status",
    [(False, 0, 0), (False, 23, 0), (False, 0, 5), (True, 0, 0), (True, 0, 5)],
)
def test_cli_install_and_version_failures_propagate(
    tmp_path: Path,
    preinstalled: bool,
    install_status: int,
    version_status: int,
) -> None:
    """The on-create CLI profile reuses the image's CLI, verifies it, and never hides a failure."""
    tools = tmp_path / ".local" / "bin"
    tools.mkdir(parents=True)
    log = tmp_path / "calls.log"
    copilot = tmp_path / "copilot-stub"
    copilot.write_text(
        f'#!/bin/sh\nprintf "%s\\n" "copilot $*" >> "$SETUP_CALL_LOG"\nexit {version_status}\n',
        encoding="utf-8",
    )
    copilot.chmod(0o755)
    if preinstalled:
        shutil.copy(copilot, tools / "copilot")
    # A successful download "installs" the CLI, as the real installer does.
    install = f'cp "{copilot}" "{tools / "copilot"}"\n' if not install_status else ""
    curl = tools / "curl"
    curl.write_text(
        f'#!/bin/sh\nprintf "%s\\n" "curl $*" >> "$SETUP_CALL_LOG"\n{install}exit {install_status}\n',
        encoding="utf-8",
    )
    curl.chmod(0o755)
    result = subprocess.run(
        ["bash", "-o", "pipefail", ".devcontainer/setup.sh", "cli"],
        env={**os.environ, "HOME": str(tmp_path), "SETUP_CALL_LOG": str(log)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == (install_status or version_status)
    expected = [] if preinstalled else ["curl -fsSL https://gh.io/copilot-install"]
    if not install_status:
        expected.append("copilot --version")
    assert log.read_text(encoding="utf-8").splitlines() == expected
    # Day 3's ticket tools and the workshop's model: a plain `copilot` gets both, written once.
    alias = "alias copilot='copilot --add-github-mcp-toolset issues --model claude-sonnet-5.5'"
    bashrc = tmp_path / ".bashrc"
    if result.returncode == 0:
        subprocess.run(
            ["bash", "-o", "pipefail", ".devcontainer/setup.sh", "cli"],
            env={**os.environ, "HOME": str(tmp_path), "SETUP_CALL_LOG": str(log)},
            capture_output=True,
            check=True,
        )
        assert bashrc.read_text(encoding="utf-8").splitlines().count(alias) == 1
    else:
        assert not bashrc.exists()


def test_setup_does_not_hide_failures_or_request_day_two_secrets() -> None:
    """The first lab needs working tools, not Dataverse credentials."""
    config = json.loads(Path(".devcontainer/devcontainer.json").read_text(encoding="utf-8"))

    for command in [*config["onCreateCommand"].values(), config["postCreateCommand"]]:
        assert "pipefail" in command
        assert "||" not in command
    assert "secrets" not in config


def test_mcp_examples_are_private_and_use_pinned_tools() -> None:
    """Learners add trusted remote-workspace connections, not a public MCP endpoint."""
    example = json.loads(Path(".devcontainer/mcp.example.json").read_text(encoding="utf-8"))
    assert set(example["servers"]) == {"playwright", "markitdown"}
    for name, server in example["servers"].items():
        assert server == {
            "type": "stdio",
            "command": "bash",
            "args": ["${workspaceFolder}/.devcontainer/mcp.sh", name],
        }
    launcher = Path(".devcontainer/mcp.sh").read_text(encoding="utf-8")
    assert "--headless --isolated --executable-path" in launcher
    assert "chromiumSandbox: true, executablePath: chromium.executablePath()" in launcher
    assert "--no-sandbox" not in launcher
    assert "--ignore-https-errors" not in launcher
    assert "--port" not in launcher
    package = json.loads(Path(".devcontainer/browser/package.json").read_text(encoding="utf-8"))
    lock = json.loads(Path(".devcontainer/browser/package-lock.json").read_text(encoding="utf-8"))
    assert package["dependencies"]["@playwright/mcp"] == "0.0.81"
    assert lock["packages"]["node_modules/@playwright/mcp"]["version"] == "0.0.81"
    requirements = Path(".devcontainer/research-requirements.txt").read_text(encoding="utf-8")
    assert "markitdown-mcp==0.0.1a7" in requirements
    assert "markitdown==0.1.7" in requirements
    assert "azure-ai-contentunderstanding==1.2.0b1" in requirements


def test_browser_profile_connects_only_the_reviewed_playwright_entry(tmp_path: Path) -> None:
    """Day 3's one setup command adds Playwright to Copilot without dropping other servers."""
    setup = Path(".devcontainer/setup.sh").read_text(encoding="utf-8")
    browser = setup.split("\tbrowser)", 1)[1].split(";;", 1)[0]
    assert browser.rstrip().endswith("python3 scripts/enable_playwright_mcp.py")
    assert "enable_playwright_mcp" not in setup.split("\tbrowser)", 1)[0]
    # An unverifiable, unused apt source is set aside before Playwright runs apt, never trusted
    # blindly, and a browser that cannot start stops with plain words, never --no-sandbox.
    set_aside = "sudo mv /etc/apt/sources.list.d/yarn.list /etc/apt/sources.list.d/yarn.list.disabled"
    assert browser.index(set_aside) < browser.index("install --with-deps chromium")
    assert "apt-key" not in setup and "--allow-unauthenticated" not in setup
    assert "if ! bash .devcontainer/mcp.sh check-browser; then" in browser
    assert "follow the presenter for the browser demonstration" in browser
    assert "--no-sandbox" not in setup and "chromiumSandbox: false" not in setup

    example = Path(".devcontainer/mcp.example.json")
    entry = json.loads(example.read_text(encoding="utf-8"))["servers"]["playwright"]
    target = tmp_path / ".vscode" / "mcp.json"
    assert enable_playwright_mcp.enable_playwright(target, example) is True
    assert json.loads(target.read_text(encoding="utf-8")) == {"servers": {"playwright": entry}}
    assert enable_playwright_mcp.enable_playwright(target, example) is False

    github = {"type": "http", "url": "https://api.githubcopilot.com/mcp/readonly"}
    target.write_text(json.dumps({"inputs": [], "servers": {"github": github}}), encoding="utf-8")
    assert enable_playwright_mcp.enable_playwright(target, example) is True
    merged = json.loads(target.read_text(encoding="utf-8"))
    assert merged == {"inputs": [], "servers": {"github": github, "playwright": entry}}
    assert "markitdown" not in merged["servers"]


def test_repository_ships_only_the_read_only_github_mcp_server(tmp_path: Path) -> None:
    """Attendees see one tool server, it starts only when they choose, and nothing needs Azure."""
    github = {"type": "http", "url": "https://api.githubcopilot.com/mcp/readonly"}
    workspace = json.loads(Path(".vscode/mcp.json").read_text(encoding="utf-8"))
    assert workspace == {"servers": {"github": github}}
    assert "/.vscode/mcp.json" not in Path(".gitignore").read_text(encoding="utf-8").splitlines()
    settings = json.loads(Path(".vscode/settings.json").read_text(encoding="utf-8"))
    assert settings["chat.mcp.autostart"] == "never"
    # No servers pulled in from other apps' configurations, including Copilot CLI's default.
    discovery = settings["chat.mcp.discovery.enabled"]
    assert set(discovery) == {"claude-desktop", "copilot", "cursor-global", "cursor-workspace", "windsurf"}
    assert not any(discovery.values())
    # Other extensions' chat tools and agent plugins stay out; Copilot's built-in tools remain.
    assert settings["chat.extensionTools.enabled"] is False
    assert settings["chat.plugins.enabled"] is False
    # New chats start in the Local harness, which enforces each custom agent's tools list
    # (tested in a browser Codespace, 25 October 2026); the Copilot harness did not.
    assert settings["chat.defaultToCopilotHarness"] is False
    assert settings["chat.editor.preferCopilotHarness"] is False
    config = json.loads(Path(".devcontainer/devcontainer.json").read_text(encoding="utf-8"))
    assert not any("azure" in name.lower() for name in config["customizations"]["vscode"]["extensions"])
    assert config["customizations"]["vscode"]["settings"]["github.copilot.chat.organizationCustomAgents.enabled"] is False
    # A later, owner-approved Playwright setup adds to this list without dropping GitHub.
    target = tmp_path / "mcp.json"
    target.write_text(Path(".vscode/mcp.json").read_text(encoding="utf-8"), encoding="utf-8")
    assert enable_playwright_mcp.enable_playwright(target, Path(".devcontainer/mcp.example.json"))
    assert set(json.loads(target.read_text(encoding="utf-8"))["servers"]) == {"github", "playwright"}


@pytest.mark.parametrize(
    "existing",
    [
        '{\n  // a comment makes this JSONC\n  "servers": {}\n}',
        "[]",
        '{"servers": []}',
        '{"servers": {"playwright": {"type": "http", "url": "https://example.invalid"}}}',
    ],
)
def test_playwright_connection_never_overwrites_a_file_it_cannot_merge(
    tmp_path: Path, existing: str
) -> None:
    """A learner's own configuration is left untouched and the failure is visible."""
    target = tmp_path / "mcp.json"
    target.write_text(existing, encoding="utf-8")
    with pytest.raises(ValueError, match="left unchanged"):
        enable_playwright_mcp.enable_playwright(target, Path(".devcontainer/mcp.example.json"))
    assert target.read_text(encoding="utf-8") == existing


def test_research_stays_out_of_git_and_container_builds() -> None:
    """Public research does not become synthetic fixture data or a deployed document archive."""
    for name in (".gitignore", ".dockerignore"):
        text = Path(name).read_text(encoding="utf-8")
        assert "/research/" in text.splitlines()
        assert ".venv-research" in text


@pytest.mark.parametrize(
    "is_error,text", [(False, "Synthetic check"), (True, "Synthetic check"), (False, "Wrong")]
)
@pytest.mark.parametrize("server", ["markitdown", "playwright"])
def test_mcp_smoke_checks_sdk_two_result_fields(
    monkeypatch, is_error: bool, text: str, server: str
) -> None:
    """Check actual converted/evaluated text, not a navigation snapshot's filename."""
    tool = "convert_to_markdown" if server == "markitdown" else "browser_navigate"
    results = [SimpleNamespace(is_error=is_error, content=[SimpleNamespace(text=text)])]
    if server == "playwright":
        results.insert(
            0,
            SimpleNamespace(
                is_error=False, content=[SimpleNamespace(text="Snapshot saved to file")]
            ),
        )
    client = SimpleNamespace(
        initialize=AsyncMock(),
        list_tools=AsyncMock(
            return_value=SimpleNamespace(
                tools=[SimpleNamespace(name=name) for name in (tool, "browser_evaluate")],
            )
        ),
        call_tool=AsyncMock(side_effect=results),
    )

    @asynccontextmanager
    async def transport(parameters):
        assert parameters.command == "bash"
        yield None, None

    @asynccontextmanager
    async def session(reader, writer):
        yield client

    modules = {
        "mcp": SimpleNamespace(StdioServerParameters=SimpleNamespace, ClientSession=session),
        "mcp.client.stdio": SimpleNamespace(stdio_client=transport),
    }
    monkeypatch.setattr(check_workshop_mcp, "import_module", modules.__getitem__)
    operation = check_workshop_mcp.invoke(server, tool, {}, "Synthetic check")
    if is_error or text != "Synthetic check":
        with pytest.raises(RuntimeError, match="expected synthetic content"):
            asyncio.run(operation)
    else:
        asyncio.run(operation)
    client.initialize.assert_awaited_once()
    assert client.call_tool.await_args_list[0].args == (tool, {})
    if server == "playwright":
        assert client.call_tool.await_count == 2
        client.call_tool.assert_awaited_with(
            "browser_evaluate",
            {
                "function": "() => document.querySelector('h1')?.textContent",
            },
        )
    else:
        client.call_tool.assert_awaited_once_with(tool, {})
