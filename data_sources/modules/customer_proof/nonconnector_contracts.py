"""Nonconnector customer-proof contracts and brand boundaries."""

from __future__ import annotations

SCHEMA = "simpro-nonvault-customer-proof-selector-evidence/v1"

SUPPORTED_BRAND_HOSTS = {
    "aroflo": "aroflo.com",
    "bigchange": "bigchange.com",
    "clockshark": "clockshark.com",
}

SUPPORTED_ROLES = ("metric", "quote", "theme", "experience_story")

SUPPORTED_SOURCE_TYPES = {"case_study", "customer_story", "reference"}

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
