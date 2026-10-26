"""Exercise the prepared MCP processes with synthetic inputs, not attendee credentials."""

import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import import_module
from pathlib import Path
from threading import Thread

ROOT = Path(__file__).resolve().parents[1]


class SyntheticPage(BaseHTTPRequestHandler):
    """Provide a loopback-only browser target for the Linux tooling smoke check."""

    def do_GET(self) -> None:
        """Return one predictable page for a real browser navigation."""
        body = b"<!doctype html><html><body><h1>Synthetic browser check</h1></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        """Keep smoke output limited to the observed result."""


async def invoke(server: str, tool: str, arguments: dict, expected: str) -> None:
    """Use the installed official Python MCP client for a genuine stdio invocation."""
    mcp = import_module("mcp")
    stdio = import_module("mcp.client.stdio")
    parameters = mcp.StdioServerParameters(
        command="bash", args=[str(ROOT / ".devcontainer/mcp.sh"), server], cwd=str(ROOT),
    )
    async with asyncio.timeout(90):
        async with stdio.stdio_client(parameters) as (reader, writer):
            async with mcp.ClientSession(reader, writer) as session:
                await session.initialize()
                tools = await session.list_tools()
                required = {tool, "browser_evaluate"} if tool == "browser_navigate" else {tool}
                if not required.issubset({item.name for item in tools.tools}):
                    raise RuntimeError(f"{server} did not expose the required tool")
                result = await session.call_tool(tool, arguments)
                if tool == "browser_navigate" and not result.is_error:
                    result = await session.call_tool("browser_evaluate", {
                        "function": "() => document.querySelector('h1')?.textContent",
                    })
                text = "\n".join(getattr(item, "text", "") for item in result.content)
                if result.is_error or expected not in text:
                    raise RuntimeError(
                        f"{server} did not return the expected synthetic content "
                        f"(is_error={result.is_error}): {text[:2000]}"
                    )
    print(f"{server}: initialized, discovered {tool}, and verified synthetic content")


async def check() -> None:
    """Close all child processes and the local server when the bounded check ends."""
    await invoke("markitdown", "convert_to_markdown",
                 {"uri": "data:text/plain,Synthetic%20conversion%20check"}, "Synthetic conversion check")
    with ThreadingHTTPServer(("127.0.0.1", 0), SyntheticPage) as server:
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            await invoke("playwright", "browser_navigate",
                         {"url": f"http://127.0.0.1:{server.server_port}"}, "Synthetic browser check")
        finally:
            server.shutdown()
            worker.join()


if __name__ == "__main__":
    asyncio.run(check())