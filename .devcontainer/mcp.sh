#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
case "${1:-}" in
  playwright)
    BROWSER="$(node -p "require('./.devcontainer/browser/node_modules/playwright').chromium.executablePath()")"
    test -x "$BROWSER"
    mkdir -p research/browser
    exec node .devcontainer/browser/node_modules/@playwright/mcp/cli.js \
      --headless --isolated --executable-path "$BROWSER" --output-dir "$ROOT/research/browser"
    ;;
  markitdown)
    exec .venv-research/bin/markitdown-mcp
    ;;
  check-research)
    .venv-research/bin/python -c 'from importlib.metadata import version; from markitdown import MarkItDown; print("MarkItDown", version("markitdown"), "MCP", version("markitdown-mcp"))'
    ;;
  check-browser)
    node .devcontainer/browser/node_modules/@playwright/mcp/cli.js --version
    node -e 'const { chromium } = require("./.devcontainer/browser/node_modules/playwright"); (async () => { const browser = await chromium.launch({headless: true, chromiumSandbox: true, executablePath: chromium.executablePath()}); const page = await browser.newPage(); await page.setContent("<h1>Synthetic browser check</h1>"); if (await page.locator("h1").innerText() !== "Synthetic browser check") throw new Error("Browser check failed"); await browser.close(); console.log("Sandboxed headless Chromium launched and read the synthetic page"); })().catch(error => { console.error(error.message); process.exitCode = 1; });'
    ;;
  check)
    bash "$ROOT/.devcontainer/mcp.sh" check-browser
    bash "$ROOT/.devcontainer/mcp.sh" check-research
    ;;
  *)
    printf 'Usage: bash .devcontainer/mcp.sh playwright|markitdown|check-browser|check-research|check\n' >&2
    exit 2
    ;;
esac