"""Which agent client made a self-declared browser capture.

Browser captures (fact pages, AnswerSocrates and Google pages, SERP results) are read in the user's
main Chrome window by the running client's browser tools: Claude-in-Chrome in Claude Code, the Chrome
browser backend in Codex. Each recorder stores the client it ran under. The value is self-declared;
the one environmental check made is that a process inside Claude Code (``CLAUDECODE=1``) cannot
declare ``codex``; a Codex CLI launched from Claude Code's shell (``codex:codex-rescue``) inherits that
marker, so such a run cannot truthfully declare either client and leaves browser captures to the
parent session. Captures recorded before the field shipped (``CLIENT_FIELD_SINCE``) read as
``unrecorded``; a later record without a client is refused, so the field cannot be dropped to hide it.
"""

from __future__ import annotations

import datetime
import os
from collections.abc import Mapping
from typing import Any

CLIENTS = frozenset({"claude_code", "codex"})
UNRECORDED = "unrecorded"
# The instant the client field shipped (commit 2cd0a35). A record made at or after it must name its
# client; an earlier one reads as unrecorded. The cutoff is what makes "legacy" a fact, not a claim.
CLIENT_FIELD_SINCE = "2026-10-15T18:38:35Z"
_STAMP = "%Y-%m-%dT%H:%M:%SZ"
_SINCE = datetime.datetime.strptime(CLIENT_FIELD_SINCE, _STAMP)


def client_error(value: Any) -> str:
    """Return why ``value`` is not a known client, or an empty string."""
    if isinstance(value, str) and value in CLIENTS:
        return ""
    return f"client must be one of {sorted(CLIENTS)}, found: {value!r}"


def client_required(recorded_at: Any) -> bool:
    """True when a record made at ``recorded_at`` (RFC 3339 UTC Z) must name its client.

    Records from before the field shipped read as unrecorded; a record with no readable time fails closed.
    """
    try:
        return datetime.datetime.strptime(str(recorded_at), _STAMP) >= _SINCE
    except ValueError:
        return True


def fields_with_client_ok(payload: Mapping[str, Any], required: frozenset[str], *, recorded_at: Any = None) -> bool:
    """Every required field, no unknown field, and a known client when the record names one.

    The client may be absent only on a record made before the field shipped (``recorded_at`` decides;
    a caller that passes no time skips that check).
    """
    fields = set(payload)
    if not required <= fields <= required | {"client"}:
        return False
    if "client" not in payload:
        return recorded_at is None or not client_required(recorded_at)
    return not client_error(payload["client"])


def declared_client(value: Any, environ: Mapping[str, str] | None = None) -> str:
    """Return the client a recorder was told it runs under, refusing a value the environment contradicts."""
    error = client_error(value)
    if error:
        raise ValueError(error)
    env = os.environ if environ is None else environ
    if value == "codex" and env.get("CLAUDECODE") == "1":
        raise ValueError("client codex was declared, but this process runs inside Claude Code (CLAUDECODE=1)")
    return str(value)


__all__ = [
    "CLIENT_FIELD_SINCE",
    "CLIENTS",
    "UNRECORDED",
    "client_error",
    "client_required",
    "declared_client",
    "fields_with_client_ok",
]
