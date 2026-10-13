"""Check that a fact's verified quote actually supports the claim written for it.

The live-page check proves only that the quote exists on the page. These rules
stop a short or unrelated quote from certifying a stronger claim.

Polarity is one-directional. A comparator, quantifier, or negation the claim leans
on must be in the quote. Extra words in the quote count against the claim only when
they narrow or reverse its meaning; neutral context ("every month", "at the office")
does not.
"""

from __future__ import annotations

import re

MIN_QUOTE_WORDS = 6
MIN_OVERLAP = 0.5
SUPPORT_RULE = "quote_overlap"
# Fused tokens for the phrases "at least", "at most" and "up to".
_PHRASES = {"atleast": "at least", "atmost": "at most", "upto": "up to"}
_NEGATORS = frozenset("not no never none without nor neither few rarely seldom hardly".split())
# Claim side: any of these in the claim must also be in the quote.
CLAIM_POLARITY = _NEGATORS | frozenset(
    "more fewer less over under above below most least only all every".split()
) | frozenset(_PHRASES)
# Quote side: a word only in the quote refuses only when it narrows or reverses meaning.
QUOTE_POLARITY = _NEGATORS | frozenset("fewer less under below least only".split()) | frozenset(_PHRASES)
STOPWORDS = frozenset(
    "a an the is are was were be been being am to of for in on at and or but if as by from with than "
    "that this these those it its they them their we our you your he she his her i can could "
    "will would should may might do does did has have had any some such so into onto out about "
    "which who whom what when where how also just very".split()
)
_TOKEN = re.compile(r"[a-z0-9]+")
_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")
_CONTRACTIONS = (
    (re.compile(r"\bwon['’]t\b"), "will not"),
    (re.compile(r"\bcan['’]?not\b|\bcan['’]t\b"), "can not"),
    (re.compile(r"n['’]t\b"), " not"),
)
_PHRASE_PATTERNS = tuple(
    (re.compile(r"\b" + r"\s+".join(phrase.split()) + r"\b"), token) for token, phrase in _PHRASES.items()
)


def _tokens(text: str) -> list[str]:
    folded = _THOUSANDS.sub("", text.casefold())
    for pattern, replacement in _CONTRACTIONS:
        folded = pattern.sub(replacement, folded)
    for pattern, token in _PHRASE_PATTERNS:
        folded = pattern.sub(token, folded)
    return _TOKEN.findall(folded)


def _stem(token: str) -> str:
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _content(tokens: list[str]) -> set[str]:
    skip = STOPWORDS | CLAIM_POLARITY | QUOTE_POLARITY
    return {_stem(token) for token in tokens if token not in skip}


def _polarity_mismatch(claim_tokens: list[str], quote_tokens: list[str]) -> list[str]:
    claim_set, quote_set = set(claim_tokens), set(quote_tokens)
    lost = CLAIM_POLARITY & claim_set - quote_set
    added = QUOTE_POLARITY & quote_set - claim_set
    return sorted(lost | added)


def _display(token: str) -> str:
    return _PHRASES.get(token, token)


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
    mismatch = _polarity_mismatch(claim_tokens, quote_tokens)
    if mismatch:
        errors.append(
            f"fact {fact_id} rule polarity: comparator, quantifier, or negation differs between claim "
            f"and quote: {', '.join(_display(token) for token in mismatch)}; "
            "trim the quote to the span that supports the claim"
        )
    return errors
