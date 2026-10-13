"""Canonical number comparison for claim-to-quote number checks."""

from __future__ import annotations

import re
from decimal import Decimal

_ISO_DATE = re.compile(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)")
_NUMBER = re.compile(
    r"(?<![A-Za-z0-9_])(?<!\d\.)"
    r"(?P<number>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+)(?!\d)"
    r"(?:(?:\s+(?P<word>thousand|million|billion)|\s*(?P<spaced>bn)|(?P<short>k|m))(?![A-Za-z]))?",
    re.IGNORECASE,
)
_MULTIPLIERS = {
    "thousand": 1_000,
    "k": 1_000,
    "million": 1_000_000,
    "m": 1_000_000,
    "billion": 1_000_000_000,
    "bn": 1_000_000_000,
}


def _canonical(number: str, suffix: str | None) -> str:
    value = Decimal(number.replace(",", ""))
    if suffix:
        value *= _MULTIPLIERS[suffix.lower()]
    text = format(value.normalize(), "f")
    return text[:-1] if text.endswith(".") else text


def _suffix(match: re.Match[str]) -> str | None:
    return match.group("word") or match.group("spaced") or match.group("short")


def extract_numbers(text: str) -> frozenset[str]:
    """Return canonical decimal strings for every number in ``text``."""
    scrubbed = _ISO_DATE.sub(" ", text)
    return frozenset(
        _canonical(match.group("number"), _suffix(match))
        for match in _NUMBER.finditer(scrubbed)
    )


def numbers_supported(claim: str, quote: str) -> tuple[bool, frozenset[str]]:
    """Return whether every claim number appears in the quote, plus the missing numbers."""
    missing = extract_numbers(claim) - extract_numbers(quote)
    return (not missing, frozenset(missing))
