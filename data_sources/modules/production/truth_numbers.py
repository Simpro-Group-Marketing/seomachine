"""Number checks for the truth layer: the global public-copy gate and per-claim number support."""

from __future__ import annotations

import re
from collections.abc import Sequence
from decimal import Decimal

from data_sources.modules.production.bom_text import strip_label_numbers
from data_sources.modules.production.numbers import extract_numbers
from data_sources.modules.production.truth_text import Finding

_ISO_DATE = re.compile(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)")
_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_])(?<!\d\.)"
    r"(?P<number>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+)(?!\d)"
    r"(?P<suffix>\s*%|\s+per\s?cent\b|\s+(?:thousand|million|billion)\b|\s*bn\b|[km](?![A-Za-z]))?",
    re.IGNORECASE,
)
_CURRENCY_BEFORE = re.compile(r"(?:[$£€]|\b(?:USD|AUD|GBP|EUR|NZD|CAD))\s*$", re.IGNORECASE)
_SMALL_INTEGER = 10


def _is_exempt(match: re.Match[str], line: str) -> bool:
    """A bare integer from 0 to 10 with no percent, currency, or multiplier attached."""
    number = match.group("number")
    if match.group("suffix") or not number.isdigit() or int(number) > _SMALL_INTEGER:
        return False
    return _CURRENCY_BEFORE.search(line[: match.start()]) is None


def _line_offenders(line: str, allowed: frozenset[str]) -> dict[str, str]:
    """Map canonical number to the text as written, for numbers the BOM does not supply."""
    scrubbed = _ISO_DATE.sub(" ", strip_label_numbers(line))
    found: dict[str, str] = {}
    for match in _TOKEN.finditer(scrubbed):
        if _is_exempt(match, scrubbed):
            continue
        for canonical in extract_numbers(match.group(0)) - allowed:
            found.setdefault(canonical, match.group(0).strip())
    return found


def number_gate(lines: Sequence[str], allowed: frozenset[str]) -> list[Finding]:
    """Block every public number that is not a BOM-supplied, label, or small bare number."""
    findings = []
    for index, line in enumerate(lines, start=1):
        for written in _line_offenders(line, allowed).values():
            findings.append(Finding(
                "number_gate", "block",
                f"number {written!r} is not in any production BOM fact quote or approved proof", index,
            ))
    return findings


def missing_claim_numbers(claim: str, allowed: frozenset[str]) -> list[str]:
    """Return the claim's numbers (canonical, ascending) that the cited sources do not supply.

    Uses the same exemptions as the global gate: list numbering, 24/7, and bare integers 0 to 10.
    """
    return sorted(_line_offenders(claim, allowed), key=Decimal)
