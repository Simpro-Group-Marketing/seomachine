"""Check that a fact's verified quote actually supports the claim written for it.

The live-page check proves only that the quote exists on the page. These rules
stop a short or unrelated quote from certifying a stronger claim.
"""

from __future__ import annotations

import re

MIN_QUOTE_WORDS = 6
MIN_OVERLAP = 0.5
SUPPORT_RULE = "quote_overlap"
POLARITY_WORDS = frozenset(
    "more fewer less over under above below most least only not no never up at all every none".split()
)
STOPWORDS = frozenset(
    "a an the is are was were be been being am to of for in on and or but if as by from with than "
    "that this these those it its it's they them their we our you your he she his her i can could "
    "will would should may might do does did has have had any some such so into onto out about "
    "which who whom what when where how also just very".split()
)
_TOKEN = re.compile(r"[a-z0-9]+")
_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(_THOUSANDS.sub("", text.casefold()))


def _stem(token: str) -> str:
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _content(tokens: list[str]) -> set[str]:
    return {_stem(token) for token in tokens if token not in STOPWORDS and token not in POLARITY_WORDS}


def claim_support_errors(fact_id: str, claim: str, quote: str) -> list[str]:
    """Return one line per rule the quote fails for this claim; empty means supported."""
    claim_tokens, quote_tokens = _tokens(claim), _tokens(quote)
    errors = []
    if len(quote_tokens) < MIN_QUOTE_WORDS:
        errors.append(
            f"fact {fact_id} rule quote_min_words: quote has {len(quote_tokens)} words, "
            f"needs at least {MIN_QUOTE_WORDS}"
        )
    wanted = _content(claim_tokens)
    shared = wanted & _content(quote_tokens)
    if not wanted or len(shared) / len(wanted) < MIN_OVERLAP:
        errors.append(
            f"fact {fact_id} rule {SUPPORT_RULE}: fewer than half of the claim's content words "
            f"appear in the quote ({len(shared)} of {len(wanted)})"
        )
    mismatch = sorted(POLARITY_WORDS.intersection(claim_tokens) ^ POLARITY_WORDS.intersection(quote_tokens))
    if mismatch:
        errors.append(
            f"fact {fact_id} rule polarity: comparator or negation words differ between claim and quote: "
            + ", ".join(mismatch)
        )
    return errors
