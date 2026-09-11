"""Keyword-intent classification used by Search Console opportunity scoring."""

from __future__ import annotations


HIGH_INTENT_TERMS = (
    "pricing", "price", "cost", "buy", "purchase", "vs", "versus",
    "alternative", "alternatives", "best", "top", "review", "reviews",
    "comparison", "compare", "plan", "plans", "trial", "free trial",
    "discount", "coupon", "deal", "hosting", "service", "services",
    "platform", "software", "tool", "tools", "solution", "solutions",
    "provider", "providers",
)
MEDIUM_HIGH_INTENT_TERMS = (
    "how to", "guide", "tutorial", "tips", "strategies", "examples",
    "ideas", "ways to", "for business", "for companies", "professional",
    "analytics", "monetization", "monetize", "grow", "increase",
    "improve", "optimize", "setup", "set up",
)
MEDIUM_INTENT_TERMS = (
    "what is", "how does", "why", "benefits", "features",
    "podcast", "podcasting", "audio", "video", "rss", "marketing",
)
LOW_INTENT_TERMS = (
    "who is", "biography", "age", "net worth", "height", "wife",
    "husband", "dating", "married", "death", "died", "born",
    "pewdiepie", "youtube stars", "celebrity", "famous",
)


def commercial_intent_score(keyword: str) -> float:
    """Return the existing deterministic commercial-intent score."""
    normalized = keyword.lower()
    bands = (
        (LOW_INTENT_TERMS, 0.1),
        (HIGH_INTENT_TERMS, 3.0),
        (MEDIUM_HIGH_INTENT_TERMS, 2.0),
        (MEDIUM_INTENT_TERMS, 1.0),
    )
    for terms, score in bands:
        if any(term in normalized for term in terms):
            return score
    return 0.5


def intent_category(score: float) -> str:
    """Return the existing human-readable intent category."""
    if score >= 2.5:
        return "Transactional"
    if score >= 1.5:
        return "Commercial Investigation"
    if score >= 0.8:
        return "Informational (Relevant)"
    return "Informational (Low Value)"
