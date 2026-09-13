"""MCP stdio server for AndroGuard.

Implements the MCP 2024-11-05 line-framed JSON-RPC transport over stdin/stdout.
Each request is one JSON line; each response is one JSON line.

Usage (stdio transport, as configured in Claude Desktop / Claude Code)::

    androguard-mcp                    # standalone entry point
    androguard-skills mcp             # subcommand form

Claude Desktop config (~/.config/claude/claude_desktop_config.json)::

    {
      "mcpServers": {
        "androguard": {
          "command": "androguard-mcp"
        }
      }
    }
"""

from __future__ import annotations

import json
import sys

from androguard.agent.headless import HeadlessAPI


def run_stdio(include_ui: bool = False) -> None:
    """Read JSON-RPC requests from stdin, write responses to stdout (line-framed)."""
    api = HeadlessAPI(include_ui=include_ui)

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            request = json.loads(raw)
        except json.JSONDecodeError as exc:
            _write({
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
                "id": None,
            })
            continue

        # JSON-RPC 2.0 batch request
        if isinstance(request, list):
            responses = []
            for item in request:
                resp = api.handle(item)
                if resp is not None:
                    responses.append(resp)
            if responses:
                _write(responses)
            continue

        resp = api.handle(request)
        if resp is not None:
            _write(resp)


def _write(obj: object) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main() -> None:
    """Entry point for the ``androguard-mcp`` script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the AndroGuard MCP stdio server.",
    )
    parser.add_argument(
        "--with-ui",
        action="store_true",
        default=False,
        help="Also expose UI control tools (ui.snapshot, ui.action, etc.)",
    )
    args = parser.parse_args()
    run_stdio(include_ui=args.with_ui)


if __name__ == "__main__":
    main()
