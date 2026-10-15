"""Which agent client made a self-declared browser capture.

Browser captures (fact pages, AnswerSocrates and Google pages, SERP results) are read in the user's
main Chrome window by the running client's browser tools: Claude-in-Chrome in Claude Code, the Chrome
browser backend in Codex. Each recorder stores the client it ran under. The value is self-declared;
the one environmental check made is that a process inside Claude Code (``CLAUDECODE=1``) cannot
declare ``codex``. Captures recorded before the field existed read as ``unrecorded``.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

CLIENTS = frozenset({"claude_code", "codex"})
UNRECORDED = "unrecorded"


def client_error(value: Any) -> str:
    """Return why ``value`` is not a known client, or an empty string."""
    if isinstance(value, str) and value in CLIENTS:
        return ""
    return f"client must be one of {sorted(CLIENTS)}, found: {value!r}"


def fields_with_client_ok(payload: Mapping[str, Any], required: frozenset[str]) -> bool:
    """Every required field, no unknown field, and a known client when the record names one.

    The client is optional so that captures recorded before the field existed still validate.
    """
    fields = set(payload)
    if not required <= fields <= required | {"client"}:
        return False
    return "client" not in payload or not client_error(payload["client"])


def declared_client(value: Any, environ: Mapping[str, str] | None = None) -> str:
    """Return the client a recorder was told it runs under, refusing a value the environment contradicts."""
    error = client_error(value)
    if error:
        raise ValueError(error)
    env = os.environ if environ is None else environ
    if value == "codex" and env.get("CLAUDECODE") == "1":
        raise ValueError("client codex was declared, but this process runs inside Claude Code (CLAUDECODE=1)")
    return str(value)


__all__ = ["CLIENTS", "UNRECORDED", "client_error", "declared_client", "fields_with_client_ok"]
