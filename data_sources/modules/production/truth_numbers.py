"""Number checks for the truth layer: tokenizing public text, the global gate, and material numbers."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from data_sources.modules.production.bom_text import strip_label_numbers
from data_sources.modules.production.numbers import extract_numbers
from data_sources.modules.production.truth_text import Finding

_ISO_DATE = re.compile(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)")
_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_])(?<!\d\.)"
    r"(?P<number>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+)(?!\d)"
    r"(?P<suffix>\s*%|\s+per\s?cent\b|\s+(?:thousand|million|billion)\b|\s*bn\b|[km](?![A-Za-z])"
    r"|\s*[x×](?![A-Za-z])|\s+times\b)?",
    re.IGNORECASE,
)
_RATIO = re.compile(r"\b(\d+)\s+(?:out\s+of|in)\s+(\d+)\b", re.IGNORECASE)
_CURRENCY_BEFORE = re.compile(r"(?:[$£€]|\b(?:USD|AUD|GBP|EUR|NZD|CAD))\s*$", re.IGNORECASE)
_SMALL_INTEGER = 10
_MATERIAL_FLOOR = 11

_CODE_BODY = r"\s?\d+(?:[.:/-]\d+)*[A-Za-z]?(?!\s*%)"
_EXEMPT_SPANS = (
    # Standards, codes, and product versions: the digits name something, they do not measure it.
    re.compile(r"(?<![A-Za-z0-9_])(?:ISO|AS/NZS|AS|BS|EN|NFPA|OSHA|NEC|COVID-|R-|iOS)" + _CODE_BODY),
    re.compile(
        r"(?<![A-Za-z0-9_])(?:Title|Section|Chapter|Article|Part|Rule|Class|Tier|Level|Version|Android|Windows)"
        + _CODE_BODY,
        re.IGNORECASE,
    ),
    re.compile(r"(?<![A-Za-z0-9_])[vV]\d+(?:\.\d+)*"),
    re.compile(r"\b401\(k\)", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z0-9_])\d+(?:st|nd|rd|th)\b", re.IGNORECASE),
    re.compile(
        r"(?<![\d:.])(?:(?:1[0-2]|0?[1-9])(?::[0-5]\d)?\s*[ap]\.?m\.?|(?:[01]?\d|2[0-3]):[0-5]\d)(?!\d)",
        re.IGNORECASE,
    ),
)
_PHONE = re.compile(r"(?<![\d.,$£€])\+?\d{1,4}(?:[ -]\d{1,4}){2,}(?![\d,.]|\s*%)")
_PHONE_DIGITS = 8


@dataclass(frozen=True)
class NumberToken:
    text: str  # as written
    canonical: str
    material: bool  # carries %, currency, a multiplier, a ratio, or is 11 or more


def _blank_span(match: re.Match[str]) -> str:
    return " " * len(match.group(0))


def _blank_phone(match: re.Match[str]) -> str:
    digits = sum(char.isdigit() for char in match.group(0))
    return _blank_span(match) if digits >= _PHONE_DIGITS else match.group(0)


def _scrub(line: str) -> str:
    text = _ISO_DATE.sub(" ", strip_label_numbers(line))
    for pattern in _EXEMPT_SPANS:
        text = pattern.sub(_blank_span, text)
    return _PHONE.sub(_blank_phone, text)


def _ratio_starts(text: str) -> frozenset[int]:
    return frozenset(start for match in _RATIO.finditer(text) for start in (match.start(1), match.start(2)))


def _classify(match: re.Match[str], text: str, ratios: frozenset[int]) -> tuple[bool, bool]:
    """Return (exempt, material) for one number token."""
    number = match.group("number")
    attached = bool(match.group("suffix")) or _CURRENCY_BEFORE.search(text[: match.start()]) is not None
    ratio = match.start("number") in ratios
    small = number.isdigit() and int(number) <= _SMALL_INTEGER
    if small and not (attached or ratio):
        return True, False
    large = Decimal(number.replace(",", "")) >= _MATERIAL_FLOOR
    return False, attached or ratio or large


def number_tokens(line: str, year: str = "") -> list[NumberToken]:
    """Return the checkable numbers in one line of public text (exempt forms are dropped)."""
    text = _scrub(line)
    ratios = _ratio_starts(text)
    tokens = []
    for match in _TOKEN.finditer(text):
        exempt, material = _classify(match, text, ratios)
        if exempt:
            continue
        for canonical in extract_numbers(match.group(0)):
            tokens.append(NumberToken(match.group(0).strip(), canonical, material and canonical != year))
    return tokens


def number_gate(lines: Sequence[str], allowed: frozenset[str]) -> list[Finding]:
    """Block every public number that no BOM fact quote or approved proof supplies."""
    findings = []
    for index, line in enumerate(lines, start=1):
        seen: set[str] = set()
        for token in number_tokens(line):
            if token.canonical in allowed or token.canonical in seen:
                continue
            seen.add(token.canonical)
            findings.append(Finding(
                "number_gate", "block",
                f"number {token.text!r} is not in any production BOM fact quote or approved proof", index,
            ))
    return findings


def material_numbers(lines: Sequence[str], year: str) -> dict[str, str]:
    """Map canonical number to its written form for every material number in a unit's lines."""
    found: dict[str, str] = {}
    for line in lines:
        for token in number_tokens(line, year):
            if token.material:
                found.setdefault(token.canonical, token.text)
    return found
