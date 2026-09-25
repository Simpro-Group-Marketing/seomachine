"""Chrome-connector URL verification allowlist.

Some public authorities, dol.gov and bls.gov among them, refuse the URL
validator's request client with HTTP 403 while serving the same page to a real
browser. Treating that as an unresolved source would push otherwise correct
citations off primary authorities. Entries are only added after the page is
loaded through the Chrome connector and its title and an on-page snippet are
read back, so an entry asserts the stronger fact that a human-equivalent
browser saw the page serving.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

URL_VERIFICATION_ALLOWLIST_PATH = (
    Path(__file__).resolve().parents[2] / "context" / "url-verification-allowlist.json"
)

_CHROME_VERIFIED_CACHE: Optional[frozenset[str]] = None


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
        for entry in payload.get("entries", []):
            if (
                isinstance(entry, dict)
                and entry.get("verified_via") == "chrome_connector"
                and isinstance(entry.get("url"), str)
            ):
                urls.add(entry["url"].strip())
    except (OSError, ValueError):
        urls = set()
    _CHROME_VERIFIED_CACHE = frozenset(urls)
    return _CHROME_VERIFIED_CACHE


__all__ = ["URL_VERIFICATION_ALLOWLIST_PATH", "chrome_verified_urls"]
