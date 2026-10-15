"""Chrome-connector URL verification allowlist.

Some public authorities, dol.gov and bls.gov among them, refuse the URL
validator's request client with HTTP 403 while serving the same page to a real
browser. Treating that as an unresolved source would push otherwise correct
citations off primary authorities. Entries are only added after the page is
loaded in the user's main Chrome window by the running client's live-browser
tools and its title and an on-page snippet are read back, so an entry asserts
the stronger fact that a human-equivalent browser saw the page serving. An
entry names that client (``claude_code`` or ``codex``); an entry verified before
the field shipped may carry none, and a later entry without one, or any entry
naming an unknown client, is ignored.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

try:
    from .capture_client import client_error, client_required
except ImportError:  # pragma: no cover - supports direct script execution.
    from capture_client import client_error, client_required

URL_VERIFICATION_ALLOWLIST_PATH = (
    Path(__file__).resolve().parents[2] / "context" / "url-verification-allowlist.json"
)

_CHROME_VERIFIED_CACHE: Optional[frozenset[str]] = None


def _client_ok(entry: dict) -> bool:
    """A known client, or none on an entry verified before the client field shipped."""
    if "client" in entry:
        return not client_error(entry["client"])
    return not client_required(entry.get("verified_at"))


def chrome_verified_urls() -> frozenset[str]:
    """Return URLs a Chrome connector run observed serving normally."""
    global _CHROME_VERIFIED_CACHE
    if _CHROME_VERIFIED_CACHE is not None:
        return _CHROME_VERIFIED_CACHE
    urls: set[str] = set()
    try:
        payload = json.loads(
            URL_VERIFICATION_ALLOWLIST_PATH.read_text(encoding="utf-8")
        )
        if not isinstance(payload, dict):
            # A non-object file is as unusable as an unreadable one; do not cache it.
            return frozenset()
        for entry in payload.get("entries", []):
            if (
                isinstance(entry, dict)
                and entry.get("verified_via") == "chrome_connector"
                and isinstance(entry.get("url"), str)
                and _client_ok(entry)
            ):
                urls.add(entry["url"].strip())
    except (OSError, ValueError):
        # A read error must not be cached for the life of the process.
        return frozenset()
    _CHROME_VERIFIED_CACHE = frozenset(urls)
    return _CHROME_VERIFIED_CACHE


__all__ = ["URL_VERIFICATION_ALLOWLIST_PATH", "chrome_verified_urls"]
