"""Number checks for the truth layer: tokenizing public text, the global gate, and material numbers."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from data_sources.modules.production.numbers import extract_numbers
from data_sources.modules.production.truth_text import Finding

_ISO_DATE = re.compile(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)")
_TOKEN = re.compile(
    # A letter may touch the number ("v47%", "USD40") only after a currency code or before a unit.
    r"(?<![0-9_])(?<!\d\.)(?:(?<![A-Za-z])|(?<=USD)|(?<=AUD)|(?<=NZD)|(?<=GBP)|(?<=EUR)|(?<=CAD)"
    r"|(?=[\d,.]+(?:\s*%|\s+per\s?cent\b|\s*[x×](?![A-Za-z])|\s+times\b|[km](?![A-Za-z]))))"
    r"(?P<number>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+)(?!\d)"
    r"(?P<suffix>\s*%|\s+per\s?cent\b|\s+(?:thousand|million|billion)\b|\s*bn\b|[km](?![A-Za-z])"
    r"|\s*[x×](?![A-Za-z])|\s+times\b)?",
    re.IGNORECASE,
)
_RATIO = re.compile(r"\b(\d+)\s+(?:out\s+of|in)\s+(\d+)\b", re.IGNORECASE)
_CURRENCY_BEFORE = re.compile(r"(?:[$£€]|\b(?:USD|AUD|GBP|EUR|NZD|CAD))\s*$", re.IGNORECASE)
_PLURAL_AFTER = re.compile(r"(?:-[A-Za-z]+\b|\s+(?:[A-Za-z-]+\s+){0,4}[A-Za-z-]{2,}s\b)")
_THOUSANDS = re.compile(r"(?<![\d,.])\d{1,3}(?:[  ]\d{3})+(?!\d)")
_SMALL_INTEGER = 10
_MATERIAL_FLOOR = 11

# No exemption may swallow a number that carries a percent, multiplier, or magnitude word.
_ATTACHED = (
    r"(?!\s*%|\s+per\s?cent\b|\s*[x×](?![A-Za-z])|\s+times\b|[km](?![A-Za-z])|\s*bn\b"
    r"|\s+(?:thousand|million|billion)\b)"
)
_CODE_BODY = r"\s?\d+(?:[.:/-]\d+)*(?!\d)" + _ATTACHED
_LABEL = re.compile(
    r"\b(?:step|part|phase|stage|tip|form)\s*\d+(?!\d)" + _ATTACHED
    + r"|#\s*\d+(?!\d)" + _ATTACHED + r"|(?<![\d/])24/7(?![\d/])",
    re.IGNORECASE,
)
_EXEMPT_SPANS = (
    # Standards, codes, and product versions: the digits name something, they do not measure it.
    re.compile(r"(?<![A-Za-z0-9_])(?:ISO|AS/NZS|AS|BS|EN|NFPA|OSHA|NEC|COVID-|R-|iOS)" + _CODE_BODY),
    re.compile(
        r"(?<![A-Za-z0-9_])(?:Title|Section|Chapter|Article|Part|Rule|Class|Tier|Level|Version|Android|Windows)"
        + _CODE_BODY,
        re.IGNORECASE,
    ),
    re.compile(r"(?<![A-Za-z0-9_])[vV]\d+(?:\.\d+)*(?!\d)" + _ATTACHED),
    re.compile(r"\b401\(k\)" + _ATTACHED, re.IGNORECASE),
    re.compile(r"(?<![A-Za-z0-9_])\d+(?:st|nd|rd|th)\b" + _ATTACHED, re.IGNORECASE),
    re.compile(
        r"(?<![\d:.])(?:(?:1[0-2]|0?[1-9])(?::[0-5]\d)?\s*[ap]\.?m\.?|(?:[01]?\d|2[0-3]):[0-5]\d)(?!\d)" + _ATTACHED,
        re.IGNORECASE,
    ),
)
_PHONE = re.compile(r"(?<![\d.,])\+?\(?\d{1,4}\)?(?:[ -]\d{1,4}){1,}(?!\d)" + _ATTACHED)
_PHONE_PREFIX = re.compile(r"\+|\(0|1300|1800|13 |0800|0")
_PHONE_CUE = re.compile(r"\b(?:call|phone|tel|ph|mobile|contact)\b", re.IGNORECASE)
_SENTENCE_BREAK = re.compile(r"[.!?]\s")
_PHONE_DIGITS = 8
_CUED_PHONE_DIGITS = 7
_PHONE_LONG_GROUPS = 2
_LONG_GROUP = 3


@dataclass(frozen=True)
class NumberToken:
    text: str  # as written
    canonical: str
    material: bool  # carries %, currency, a multiplier, a ratio, or is 11 or more


@dataclass(frozen=True)
class ListicleScope:
    """Where a list-size number ("12 Ways") may be exempt: titles, meta, headings, link anchors."""

    count: int = 0  # the article's H3 count
    lines: frozenset[int] = frozenset()  # title, meta, and heading line numbers
    anchors: Mapping[int, tuple[str, ...]] = field(default_factory=dict)  # link anchor text per line

    def count_at(self, number: int, line: str, position: int) -> int:
        """The list size that applies to a number at ``position`` of line ``number`` (0 when none)."""
        if number in self.lines or _in_anchor(line, self.anchors.get(number, ()), position):
            return self.count
        return 0


def _in_anchor(line: str, anchors: Sequence[str], position: int) -> bool:
    cursor = 0
    for anchor in anchors:
        start = line.find(anchor, cursor) if anchor else -1
        if start < 0:
            continue
        cursor = start + len(anchor)
        if start <= position < cursor:
            return True
    return False


def _blank_span(match: re.Match[str]) -> str:
    return " " * len(match.group(0))


def _blank_phone(match: re.Match[str], text: str) -> str:
    """Blank a phone-shaped span, but only with a phone prefix or a call/phone cue before it."""
    before = text[: match.start()]
    span = match.group(0)
    if _CURRENCY_BEFORE.search(before):
        return span
    cued = _PHONE_CUE.search(_SENTENCE_BREAK.split(before)[-1]) is not None
    if not (cued or _PHONE_PREFIX.match(span)):
        return span
    groups = re.findall(r"\d+", span)
    long_groups = sum(len(group) >= _LONG_GROUP for group in groups)
    floor = _CUED_PHONE_DIGITS if cued else _PHONE_DIGITS
    return _blank_span(match) if sum(map(len, groups)) >= floor and long_groups >= _PHONE_LONG_GROUPS else span


def _scrub(line: str) -> str:
    """Blank exempt forms and join space-separated thousands; the result keeps the line's length."""
    text = _ISO_DATE.sub(_blank_span, _LABEL.sub(_blank_span, line))
    for pattern in _EXEMPT_SPANS:
        text = pattern.sub(_blank_span, text)
    text = _PHONE.sub(lambda match: _blank_phone(match, text), text)
    return _THOUSANDS.sub(lambda match: re.sub(r"[  ]", ",", match.group(0)), text)


def _ratio_starts(text: str) -> frozenset[int]:
    return frozenset(start for match in _RATIO.finditer(text) for start in (match.start(1), match.start(2)))


def _classify(match: re.Match[str], text: str, ratios: frozenset[int], listicle: int) -> tuple[bool, bool]:
    """Return (exempt, material) for one number token."""
    number = match.group("number")
    attached = bool(match.group("suffix")) or _CURRENCY_BEFORE.search(text[: match.start()]) is not None
    ratio = match.start("number") in ratios
    if number.isdigit() and int(number) <= _SMALL_INTEGER and not (attached or ratio):
        return True, False
    large = Decimal(number.replace(",", "")) >= _MATERIAL_FLOOR
    is_list_size = listicle and number.isdigit() and int(number) == listicle and not (attached or ratio)
    if is_list_size and large and _PLURAL_AFTER.match(text, match.end()):
        return True, False
    return False, attached or ratio or large


def number_tokens(
    line: str, year: str = "", scope: ListicleScope | None = None, line_no: int = 0
) -> list[NumberToken]:
    """Return the checkable numbers in one line of public text (exempt forms are dropped).

    ``scope`` carries the article's H3 count: an equal number of 11 or more followed by a plural
    noun ("12 Ways") is a list size, not a claim, but only in a title, meta field, heading, or anchor.
    """
    text = _scrub(line)
    ratios = _ratio_starts(text)
    tokens = []
    for match in _TOKEN.finditer(text):
        listicle = scope.count_at(line_no, line, match.start()) if scope else 0
        exempt, material = _classify(match, text, ratios, listicle)
        if exempt:
            continue
        for canonical in extract_numbers(match.group(0)):
            tokens.append(NumberToken(match.group(0).strip(), canonical, material and canonical != year))
    return tokens


def number_gate(lines: Sequence[str], allowed: frozenset[str], scope: ListicleScope | None = None) -> list[Finding]:
    """Block every public number that no BOM fact quote or approved proof supplies."""
    findings = []
    for index, line in enumerate(lines, start=1):
        seen: set[str] = set()
        for token in number_tokens(line, scope=scope, line_no=index):
            if token.canonical in allowed or token.canonical in seen:
                continue
            seen.add(token.canonical)
            findings.append(Finding(
                "number_gate", "block",
                f"number {token.text!r} is not in any production BOM fact quote or approved proof", index,
            ))
    return findings


def material_numbers(
    lines: Sequence[str], year: str, scope: ListicleScope | None = None, first_line: int = 0
) -> dict[str, str]:
    """Map canonical number to its written form for every material number in a unit's lines."""
    found: dict[str, str] = {}
    for offset, line in enumerate(lines):
        for token in number_tokens(line, year, scope, first_line + offset):
            if token.material:
                found.setdefault(token.canonical, token.text)
    return found
