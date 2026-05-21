"""Codex-friendly stdio wrapper for the Google Analytics MCP server.

The upstream analytics-mcp package prints startup/debug messages with
``print()``, which writes to stdout. MCP stdio clients reserve stdout for JSON
RPC frames, so route ordinary print output to stderr before starting the
server.
"""

from __future__ import annotations

import builtins
import sys

from analytics_mcp.server import run_server


_original_print = builtins.print


def _print_to_stderr(*args, **kwargs):
    kwargs.setdefault("file", sys.stderr)
    return _original_print(*args, **kwargs)


builtins.print = _print_to_stderr


if __name__ == "__main__":
    run_server()
