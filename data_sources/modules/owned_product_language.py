"""One shared rule for approved, low-risk Simpro product language.

A Simpro sentence that describes what the product is, how it works, or what it
lets a user do is product language. Owned product pages support it, and the
policy engine maps an approved owned row for it to ``sidecar_only``. Outcome,
numeric, pricing, status, comparative, guarantee, quote, advice, and
regulated-topic wording is never product language and keeps its stricter
citation mode.

Approval itself is not decided here. Source support verifies the owned row's
classification and source-visible Evidence, and source quality requires the
vault read path and Vault Brand Language Alignment for ``product_claim`` and
``feature_claim`` rows.
"""

from __future__ import annotations

import re
import unicodedata

try:
    from .claim_patterns import (
        ANY_PUBLIC_NUMBER_RE,
        COMPARATIVE_RANKING_RE,
        GENERAL_CLAIM_PATTERNS,
        INFERRED_HIGH_RISK_RE,
        LEGAL_OR_TIME_SENSITIVE_RE,
        MATERIAL_NUMBER_RE,
        STRICT_PUBLIC_RISK_RE,
        STRUCTURED_PRICING_ASSERTION_RE,
        STRUCTURED_QUOTE_RE,
        STRUCTURED_STATUS_RE,
    )
except ImportError:  # pragma: no cover - supports direct script execution.
    from claim_patterns import (
        ANY_PUBLIC_NUMBER_RE,
        COMPARATIVE_RANKING_RE,
        GENERAL_CLAIM_PATTERNS,
        INFERRED_HIGH_RISK_RE,
        LEGAL_OR_TIME_SENSITIVE_RE,
        MATERIAL_NUMBER_RE,
        STRICT_PUBLIC_RISK_RE,
        STRUCTURED_PRICING_ASSERTION_RE,
        STRUCTURED_QUOTE_RE,
        STRUCTURED_STATUS_RE,
    )


PRODUCT_LANGUAGE_CLAIM_TYPES = frozenset({"product_claim", "feature_claim"})
SIMPRO_RE = re.compile(r"\bSimpro\b", re.IGNORECASE)
CAPABILITY_VERB_RE = re.compile(
    r"\b(?:enables?|allows?|lets|can|automates?)\b",
    re.IGNORECASE,
)
OUTCOME_VERB_RE = re.compile(
    r"\b(?:helps?|improves?|increases?|decreases?|reduces?|saves?|cuts?|"
    r"boosts?|streamlines?|optimi[sz]es?|delivers?|prevents?|drives?|"
    r"grow(?:s|th)?|earns?|leads?\s+to|results?\s+in|causes?|because|therefore|"
    r"contributes?\s+to)\b",
    re.IGNORECASE,
)
MONEY_RE = re.compile(r"\b(?:revenue|profits?|profitab\w*|costs?|cash\s+flow|margins?|roi)\b", re.IGNORECASE)
REGULATED_RE = re.compile(r"\b(?:complian\w*|certifi\w*|accredit\w*)\b", re.IGNORECASE)
QUANTITY_WORD_RE = re.compile(
    r"\b(?:hundreds?|thousands?|millions?|billions?|dozens?|twice|double|triple|half|percent)\b",
    re.IGNORECASE,
)
ABSOLUTE_WORD_RE = re.compile(
    r"\b(?:without\s+(?:any\s+)?(?:errors?|mistakes?|delays?|downtime|fail\w*)|"
    r"error[- ]free|entire(?:ly)?|completely|fully|only|unique|first|leading|best|"
    r"everything|anything|everyone|all[- ]in[- ]one|complete)\b",
    re.IGNORECASE,
)
COMPARATIVE_WORD_RE = re.compile(
    r"\b(?:faster|quicker|sooner|easier|simpler|better|smarter|cheaper|fewer|less|more|"
    r"lower|higher|greater)\b",
    re.IGNORECASE,
)
PRODUCT_FACT_RE = re.compile(
    r"^(?:The|A|An|Its|Each|Simpro(?:['’]s)?|[A-Z][A-Za-z0-9&.+-]*)\s+"
    r"(?:[A-Za-z0-9&'’.+-]+\s+){0,5}"
    r"(?:shows?|displays?|lists?|lets|keeps?|stores?|records?|tracks?|offers?|provides?|"
    r"includes?|supports?|connects?|sends?|manages?|contains?|groups?|links?|assigns?|"
    r"creates?|updates?|syncs?|holds?|captures?|generates?|schedules?|routes?)\b"
)
_SUBJECT_WORDS = frozenset({"simpro", "simpro's", "simpro’s"})
_PATTERNS = dict(GENERAL_CLAIM_PATTERNS)
_DISQUALIFYING_CLAIM_TYPES = ("guarantee", "absolute", "commercial", "comparative", "recommendation")
_DISQUALIFIERS = (
    OUTCOME_VERB_RE,
    MONEY_RE,
    REGULATED_RE,
    QUANTITY_WORD_RE,
    ABSOLUTE_WORD_RE,
    COMPARATIVE_WORD_RE,
    MATERIAL_NUMBER_RE,
    ANY_PUBLIC_NUMBER_RE,
    STRICT_PUBLIC_RISK_RE,
    INFERRED_HIGH_RISK_RE,
    STRUCTURED_STATUS_RE,
    STRUCTURED_PRICING_ASSERTION_RE,
    STRUCTURED_QUOTE_RE,
    COMPARATIVE_RANKING_RE,
    *(_PATTERNS[claim_type] for claim_type in _DISQUALIFYING_CLAIM_TYPES),
)


def is_low_risk_owned_language(text: str) -> bool:
    """Return true when a sentence carries none of the stricter-proof signals.

    Capability verbs are not causal claims, and "availability" alone (as in a
    technician's availability) is not a regulated access claim.
    """
    sentence = str(text or "").strip()
    if not sentence or any(pattern.search(sentence) for pattern in _DISQUALIFIERS):
        return False
    if LEGAL_OR_TIME_SENSITIVE_RE.search(re.sub(r"\bavailability\b", " ", sentence, flags=re.IGNORECASE)):
        return False
    if _PATTERNS["causal"].search(CAPABILITY_VERB_RE.sub(" ", sentence)):
        return False
    return not _names_other_entity(sentence)


def product_language_kind(text: str) -> str | None:
    """Return the product-language shape of a low-risk Simpro sentence, or None."""
    sentence = str(text or "").strip()
    if not SIMPRO_RE.search(sentence) or not is_low_risk_owned_language(sentence):
        return None
    if _PATTERNS["definitional"].search(sentence):
        return "definitional"
    if _PATTERNS["process"].search(sentence):
        return "process"
    if CAPABILITY_VERB_RE.search(sentence):
        return "capability"
    if PRODUCT_FACT_RE.search(sentence) or _PATTERNS["factual"].search(sentence):
        return "factual"
    return None


def is_approved_product_language(
    claim: str,
    *,
    source_class: str,
    claim_type: str,
) -> bool:
    """Return true for an owned product row whose claim is product language."""
    return (
        str(source_class or "").strip().casefold() == "owned_product"
        and str(claim_type or "").strip().casefold() in PRODUCT_LANGUAGE_CLAIM_TYPES
        and product_language_kind(claim) is not None
    )


def has_outcome_language(text: str) -> bool:
    """Return true when text states an outcome or money result, with or without a subject."""
    return bool(OUTCOME_VERB_RE.search(text) or MONEY_RE.search(text))


def normalize_claim_text(text: str) -> str:
    """One normalization for comparing a mapped claim with a public sentence."""
    folded = unicodedata.normalize("NFKC", str(text or ""))
    folded = folded.translate({0x2018: "'", 0x2019: "'", 0x201C: '"', 0x201D: '"'})
    return re.sub(r"\s+", " ", folded).strip().casefold().rstrip(".")


def split_sentences(text: str) -> list[str]:
    """Split visible text into sentences on terminal punctuation."""
    return [part for part in re.split(r"(?<=[.!?])\s+", str(text or "").strip()) if part]


def _names_other_entity(sentence: str) -> bool:
    words = re.findall(r"[A-Za-z][A-Za-z0-9&'’.-]*", sentence)
    return any(
        len(word) > 1 and word[0].isupper() and word.casefold().rstrip(".") not in _SUBJECT_WORDS
        for word in words[1:]
    )
