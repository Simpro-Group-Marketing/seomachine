"""Canonical hostname identity helpers for SEO data consumers."""

from __future__ import annotations

from urllib.parse import urlparse


def normalize_hostname(value: object) -> str:
    """Return a lowercase hostname with only a leading ``www.`` removed."""
    candidate = str(value or "").strip()
    if not candidate:
        return ""
    parsed = urlparse(candidate if "://" in candidate else f"//{candidate}")
    hostname = (parsed.hostname or "").lower().rstrip(".")
    return hostname[4:] if hostname.startswith("www.") else hostname


def hostnames_equal(left: object, right: object) -> bool:
    """Return whether two inputs resolve to the same exact normalized hostname."""
    left_hostname = normalize_hostname(left)
    right_hostname = normalize_hostname(right)
    return bool(left_hostname and left_hostname == right_hostname)
