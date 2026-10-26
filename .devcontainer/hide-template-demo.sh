#!/usr/bin/env bash
# Keep a facilitator's demo website out of Source Control in the template's own Codespace.
# This writes the local .git/info/exclude, never .gitignore: attendee repositories are copies
# of the template and must still save and push everything in their site/ folder.
set -euo pipefail

TEMPLATE="agentic-dev-labs/copilot-hackathon-template"

repository="${GITHUB_REPOSITORY:-$(git remote get-url origin 2>/dev/null || true)}"
repository="${repository#https://github.com/}"
repository="${repository%.git}"
[ "$repository" = "$TEMPLATE" ] || exit 0

exclude="$(git rev-parse --git-path info/exclude 2>/dev/null)" || exit 0
mkdir -p "$(dirname "$exclude")"
if ! grep -qxF '/site/*' "$exclude" 2>/dev/null; then
	printf '%s\n' \
		'# Template Codespace only (.devcontainer/hide-template-demo.sh): never commit a demo site.' \
		'/site/*' '!/site/README.md' >>"$exclude"
fi
