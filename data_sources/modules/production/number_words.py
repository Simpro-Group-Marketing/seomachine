"""Spelled-out numbers: cardinals, fractions of a whole, and word ratios.

"seventy percent" reads as 70, "twenty-four thousand" as 24000, "nine out of ten" as 9 and 10.
A fraction counts only before "of": "half of" is 50, "a quarter of" 25, "three quarters of" 75,
"a third of" 33.33 and "two thirds of" 66.67 (thirds are rounded to two decimals, so a source
must say "a third" or "33.33%" to support "a third of"). Bare "one" is a pronoun far more often
than a count ("one of the best", "no one"), so it is a number only in a compound, before a
percent or "times", or in a ratio. Ordinals ("first", "third party") are never numbers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_UNITS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine")
_TEENS = (
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
)
_TENS = ("twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")
_SCALES = {"thousand": 1_000, "million": 1_000_000, "billion": 1_000_000_000}
_VALUES = {
    **{word: value for value, word in enumerate(_UNITS)},
    **{word: value + 10 for value, word in enumerate(_TEENS)},
    **{word: (value + 2) * 10 for value, word in enumerate(_TENS)},
    "a": 1,
}
_FRACTIONS = {"half": "50", "third": "33.33", "thirds": "66.67", "quarter": "25", "quarters": "75"}
# "the second half of the year" is a period of time, not 50%.
_NOT_A_HALF = frozenset({"the", "first", "second", "back", "front", "latter", "former", "last", "next", "this", "that"})


def _word(*words: str) -> str:
    return r"(?<![A-Za-z])(?:" + "|".join(sorted(words, key=len, reverse=True)) + r")(?![A-Za-z])"


_N99 = rf"(?:{_word(*_TENS)}(?:(?:-|\s+){_word(*_UNITS[1:])})?|{_word(*_TEENS)}|{_word(*_UNITS)})"
_N999 = rf"(?:(?:{_N99}|{_word('a')})\s+{_word('hundred')}(?:\s+(?:and\s+)?{_N99})?|{_N99})"
_SCALED = rf"(?:{_N999}|{_word('a')})\s+{_word(*_SCALES)}"
_CARDINAL = rf"(?:{_SCALED},?\s+(?:and\s+)?)*(?:{_SCALED}|{_N999})"
_SIDE = rf"(?:{_CARDINAL}|(?<![\d.,])\d{{1,3}}(?![\d.,]))"
_PATTERN = re.compile(
    rf"(?P<fraction>(?:{_word('half')}|(?:{_word('a', 'one')})[- ]{_word('third', 'quarter')}"
    rf"|{_word('two')}[- ]{_word('thirds')}|{_word('three')}[- ]{_word('quarters')})\s+of(?![A-Za-z]))"
    rf"|(?P<ratio>(?P<left>{_SIDE})\s+(?:out\s+of|in)\s+(?P<right>{_SIDE}))"
    rf"|(?P<cardinal>{_CARDINAL})(?P<suffix>\s*%|\s+per\s?cent(?![A-Za-z])|\s+times(?![A-Za-z]))?",
    re.IGNORECASE,
)
_PARTS = re.compile(r"[A-Za-z]+")


@dataclass(frozen=True)
class SpelledNumber:
    start: int
    end: int
    text: str
    values: tuple[str, ...]  # canonical decimal strings
    attached: bool  # a percent, a multiplier, a fraction of a whole, or a ratio


def cardinal_value(text: str) -> int:
    """Return the value of a spelled cardinal such as "two hundred and fifty" or "a thousand"."""
    total = current = 0
    for part in _PARTS.findall(text.casefold()):
        if part in _SCALES:
            total += max(current, 1) * _SCALES[part]
            current = 0
        elif part == "hundred":
            current = max(current, 1) * 100
        elif part != "and":
            current += _VALUES[part]
    return total + current


def _side_value(text: str) -> str:
    return str(int(text)) if text.isdigit() else str(cardinal_value(text))


def _is_half_of_a_period(match: re.Match[str], text: str) -> bool:
    if not match.group("fraction").casefold().startswith("half"):
        return False
    before = _PARTS.findall(text[: match.start()][-20:])
    return bool(before) and before[-1].casefold() in _NOT_A_HALF


def _spelled(match: re.Match[str], text: str) -> SpelledNumber | None:
    found = match.group(0)
    if match.group("fraction"):
        if _is_half_of_a_period(match, text):
            return None
        last = _PARTS.findall(found)[-2].casefold()
        return SpelledNumber(match.start(), match.end(), found, (_FRACTIONS[last],), True)
    if match.group("ratio"):
        if match.group("left").isdigit() and match.group("right").isdigit():
            return None
        values = (_side_value(match.group("left")), _side_value(match.group("right")))
        return SpelledNumber(match.start(), match.end(), found, values, True)
    suffix = bool(match.group("suffix"))
    if not suffix and match.group("cardinal").casefold() == "one":
        return None
    return SpelledNumber(match.start(), match.end(), found, (str(cardinal_value(match.group("cardinal"))),), suffix)


def spelled_numbers(text: str) -> list[SpelledNumber]:
    """Return every spelled-out number in ``text`` with its canonical values."""
    found = (_spelled(match, text) for match in _PATTERN.finditer(text))
    return [item for item in found if item is not None]


__all__ = ["SpelledNumber", "cardinal_value", "spelled_numbers"]
