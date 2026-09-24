"""Nonconnector customer-proof contracts and brand boundaries."""

from __future__ import annotations

SCHEMA = "simpro-nonvault-customer-proof-selector-evidence/v1"

SUPPORTED_BRAND_HOSTS = {
    "aroflo": "aroflo.com",
    "bigchange": "bigchange.com",
    "clockshark": "clockshark.com",
}

SUPPORTED_ROLES = ("metric", "quote", "theme", "experience_story")

SUPPORTED_SOURCE_TYPES = {"case_study", "customer_story", "reference", "review_site"}

# Brand -> exact Capterra product-page prefixes eligible for a public,
# review-derived experience story or theme. Only these pages qualify; any
# other Capterra page, or any other review platform, is out of scope.
SUPPORTED_REVIEW_PAGES = {
    "bigchange": (
        "www.capterra.co.uk/software/149479/jobwatch-powered-by-bigchange",
        "www.capterra.ca/software/149479/jobwatch-powered-by-bigchange",
    ),
    "aroflo": (
        "www.capterra.com/p/166811/aroflo",
    ),
    "clockshark": (
        "www.capterra.com/p/155467/clockshark",
    ),
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "from",
    "in",
    "of",
    "on",
    "the",
    "to",
    "with",
}

class NonVaultProofDataError(RuntimeError):
    """Raised when non-vault proof inputs do not satisfy the contract."""
