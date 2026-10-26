#!/usr/bin/env bash
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
export UV_NATIVE_TLS="${UV_NATIVE_TLS:-true}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

EDITOR_RELOAD_REQUIRED=false

ensure_editor_extension() {
	local extension="$1"
	if code --list-extensions | grep -Fxiq "$extension"; then
		return
	fi
	code --install-extension "$extension"
	EDITOR_RELOAD_REQUIRED=true
	printf 'Installed editor extension %s.\n' "$extension"
}

case "${1:-core}" in
	core)
		bash .devcontainer/hide-template-demo.sh
		if ! uv sync --locked --extra dev --extra web; then
			printf '\nDependency setup failed; TLS verification remains enabled.\n' >&2
			printf 'Facilitator: run python -m rehearsal.network --fresh-install\n' >&2
			printf 'Package-host and approved certificate guidance: the facilitator rehearsal notes.\n' >&2
			exit 1
		fi
		npm ci --prefix .devcontainer/website-preview --ignore-scripts --no-audit --no-fund
		;;
	preview)
		# The Python extension can type Ctrl+C into this terminal while the editor opens;
		# ignore it so the helper still gets installed.
		trap '' INT
		if ! command -v code >/dev/null 2>&1; then
			printf 'Preview helper installation needs an attached Codespaces editor.\n' >&2
			exit 1
		fi
		ensure_editor_extension "ms-python.python"
		ensure_editor_extension "ms-python.vscode-python-envs"
		VERSION="$(node -p 'require("./.devcontainer/website-preview/package.json").version')"
		if ! code --list-extensions --show-versions | grep -Fxq "workshop-local.workshop-site-preview@$VERSION"; then
			# Package and install quietly: beginners only need the welcome line below.
			mkdir -p .workshop-preview
			if ! (cd .devcontainer/website-preview \
				&& node_modules/.bin/vsce package --no-dependencies --allow-missing-repository --skip-license --out "$ROOT/.workshop-preview/workshop-site-preview.vsix" \
				&& code --install-extension "$ROOT/.workshop-preview/workshop-site-preview.vsix" --force) \
				>"$ROOT/.workshop-preview/install.log" 2>&1; then
				printf 'Website preview setup failed; show a helper .workshop-preview/install.log.\n' >&2
				exit 1
			fi
		fi
		if "$EDITOR_RELOAD_REQUIRED"; then
			printf 'Run Developer: Reload Window once so Python can use the project environment.\n'
		fi
		printf '\nWelcome! Follow the presenter. Your guide for each day is in docs: DAY-1.md on Monday, DAY-2.md on Tuesday, and so on.\n'
		;;
	cli)
		# Runs just after the editor opens; download Copilot CLI only when it is missing.
		if ! command -v copilot >/dev/null 2>&1; then
			curl -fsSL https://gh.io/copilot-install | bash
		fi
		copilot --version
		# Day 3 lists and reads tickets through the built-in GitHub MCP server, whose issue tools
		# are not in the CLI's default set. Attendees type plain `copilot`; this adds them, and starts
		# on the workshop's model (the one the enterprise enables), so nobody lands on another one.
		ISSUE_TOOLS="alias copilot='copilot --add-github-mcp-toolset issues --model claude-sonnet-5.5'"
		sed -i "/^alias copilot='copilot --add-github-mcp-toolset issues'$/d" "$HOME/.bashrc" 2>/dev/null || true
		if ! grep -qxF "$ISSUE_TOOLS" "$HOME/.bashrc" 2>/dev/null; then
			printf '%s\n' "$ISSUE_TOOLS" >> "$HOME/.bashrc"
		fi
		;;
	browser)
		# Playwright installs Chromium's Linux libraries with apt. The base image's Yarn package
		# source is unused here and can fail its signature check, which stops apt. Set it aside
		# (renamed, so it is reversible) instead of trusting a new key or skipping verification.
		if [ -f /etc/apt/sources.list.d/yarn.list ]; then
			sudo mv /etc/apt/sources.list.d/yarn.list /etc/apt/sources.list.d/yarn.list.disabled
		fi
		npm ci --prefix .devcontainer/browser --ignore-scripts --no-audit --no-fund
		node .devcontainer/browser/node_modules/playwright/cli.js install --with-deps chromium
		if ! bash .devcontainer/mcp.sh check-browser; then
			printf '\nThe browser could not start in this Codespace. Show a helper this message,\n' >&2
			printf 'then follow the presenter for the browser demonstration.\n' >&2
			exit 1
		fi
		python3 scripts/enable_playwright_mcp.py
		;;
	research)
		uv venv --allow-existing .venv-research --python 3.12
		uv pip install --python .venv-research/bin/python --requirement .devcontainer/research-requirements.txt
		bash .devcontainer/mcp.sh check-research
		;;
	*)
		printf 'Usage: bash .devcontainer/setup.sh [core|preview|cli|browser|research]\n' >&2
		exit 2
		;;
esac