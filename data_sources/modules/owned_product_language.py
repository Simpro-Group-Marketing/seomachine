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

try:
    from .proof_link_policy import (
        ANY_PUBLIC_NUMBER_RE,
        COMPARATIVE_RANKING_RE,
        MATERIAL_NUMBER_RE,
        STRICT_PUBLIC_RISK_RE,
        STRUCTURED_PRICING_ASSERTION_RE,
        STRUCTURED_QUOTE_RE,
        STRUCTURED_STATUS_RE,
        _proof_rows,
    )
    from .source_support.common import GENERAL_CLAIM_PATTERNS
except ImportError:  # pragma: no cover - supports direct script execution.
    from proof_link_policy import (
        ANY_PUBLIC_NUMBER_RE,
        COMPARATIVE_RANKING_RE,
        MATERIAL_NUMBER_RE,
        STRICT_PUBLIC_RISK_RE,
        STRUCTURED_PRICING_ASSERTION_RE,
        STRUCTURED_QUOTE_RE,
        STRUCTURED_STATUS_RE,
        _proof_rows,
    )
    from source_support.common import GENERAL_CLAIM_PATTERNS


PRODUCT_LANGUAGE_CLAIM_TYPES = frozenset({"product_claim", "feature_claim"})
SIMPRO_RE = re.compile(r"\bSimpro\b", re.IGNORECASE)
CAPABILITY_VERB_RE = re.compile(
    r"\b(?:enables?|allows?|lets|can|automates?)\b",
    re.IGNORECASE,
)
OUTCOME_VERB_RE = re.compile(
    r"\b(?:helps?|improves?|increases?|decreases?|reduces?|saves?|cuts?|"
    r"boosts?|streamlines?|optimi[sz]es?|delivers?|prevents?|drives?|"
    r"leads?\s+to|results?\s+in|causes?|because)\b",
    re.IGNORECASE,
)
_PATTERNS = dict(GENERAL_CLAIM_PATTERNS)
_DISQUALIFYING_CLAIM_TYPES = ("guarantee", "absolute", "commercial", "comparative", "recommendation")
_DISQUALIFIERS = (
    OUTCOME_VERB_RE,
    MATERIAL_NUMBER_RE,
    ANY_PUBLIC_NUMBER_RE,
    STRICT_PUBLIC_RISK_RE,
    STRUCTURED_STATUS_RE,
    STRUCTURED_PRICING_ASSERTION_RE,
    STRUCTURED_QUOTE_RE,
    COMPARATIVE_RANKING_RE,
    *(_PATTERNS[claim_type] for claim_type in _DISQUALIFYING_CLAIM_TYPES),
)


def product_language_kind(text: str) -> str | None:
    """Return the product-language shape of a Simpro sentence, or None."""
    sentence = str(text or "").strip()
    if not SIMPRO_RE.search(sentence):
        return None
    if any(pattern.search(sentence) for pattern in _DISQUALIFIERS):
        return None
    if _PATTERNS["definitional"].search(sentence):
        return "definitional"
    if _PATTERNS["process"].search(sentence):
        return "process"
    if CAPABILITY_VERB_RE.search(sentence):
        return "capability"
    return "factual"


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


def approved_product_language_claims(proof_content: str) -> tuple[str, ...]:
    """Return approved sidecar claims that the shared rule treats as product language."""
    return tuple(
        row.claim
        for row in _proof_rows(proof_content or "")
        if row.status.casefold() == "approved"
        and is_approved_product_language(
            row.claim, source_class=row.source_class, claim_type=row.claim_type
        )
    )
