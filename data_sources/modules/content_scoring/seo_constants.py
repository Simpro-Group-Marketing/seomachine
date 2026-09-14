"""SEO scoring constants."""

from __future__ import annotations

from pathlib import Path
import re

DOWN_FUNNEL_PATH_PREFIXES = (
    "/features/",
    "/industries/",
    "/solutions/",
)

DOWN_FUNNEL_EXACT_PATHS = {
    "/",
    "/features",
    "/industries",
}

COMMERCIAL_PILLAR_INDEX_PATH = (
    Path(__file__).resolve().parents[3] / "context" / "commercial-pillar-index.json"
)

GENERIC_LINK_ANCHORS = {
    "click here",
    "here",
    "learn more",
    "more",
    "read more",
    "this page",
    "this article",
    "this link",
    "this resource",
    "check it out",
}

HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)

MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")

FENCED_CODE_BLOCK_RE = re.compile(
    r"^[ \t]*(?P<fence>`{3,}|~{3,})[^\r\n]*(?:\r?\n|\Z)"
    r".*?^[ \t]*(?P=fence)[ \t]*(?:\r?\n|\Z)",
    re.DOTALL | re.MULTILINE,
)

NON_VISIBLE_HTML_BLOCK_RE = re.compile(
    r"<(?:script|style)\b[^>]*>.*?</(?:script|style)\s*>",
    re.IGNORECASE | re.DOTALL,
)

FUNCTIONAL_DESTINATION_TERMS = {
    "accounts receivable",
    "asset maintenance",
    "cash collection",
    "construction",
    "crm",
    "data feed",
    "digital forms",
    "dispatch",
    "estimating",
    "field service",
    "inventory",
    "invoice",
    "invoicing",
    "job management",
    "maintenance",
    "management",
    "mobile app",
    "payment options",
    "payments",
    "project management",
    "reporting",
    "scheduling",
    "service management",
    "sms messaging",
    "software",
    "work order",
}

OWNED_INTERNAL_DOMAINS = {
    "aroflo.com",
    "www.aroflo.com",
    "simprogroup.com",
    "www.simprogroup.com",
    "simpro.ai",
    "www.simpro.ai",
    "clockshark.com",
    "www.clockshark.com",
    "bigchange.com",
    "www.bigchange.com",
}

BRAND_INTERNAL_DOMAINS = {
    "aroflo": frozenset({"aroflo.com"}),
    "bigchange": frozenset({"bigchange.com"}),
    "clockshark": frozenset({"clockshark.com"}),
    "simpro": frozenset({"simprogroup.com", "simpro.ai"}),
}

GEO_KEYWORD_TAIL_TOKENS = frozenset(
    {
        "alabama",
        "alaska",
        "arizona",
        "arkansas",
        "australia",
        "california",
        "canada",
        "colorado",
        "connecticut",
        "delaware",
        "florida",
        "georgia",
        "hawaii",
        "idaho",
        "illinois",
        "indiana",
        "iowa",
        "kansas",
        "kentucky",
        "louisiana",
        "maine",
        "maryland",
        "massachusetts",
        "michigan",
        "minnesota",
        "mississippi",
        "missouri",
        "montana",
        "nebraska",
        "nevada",
        "ohio",
        "oklahoma",
        "oregon",
        "pennsylvania",
        "queensland",
        "tennessee",
        "texas",
        "uk",
        "utah",
        "vermont",
        "virginia",
        "washington",
        "wisconsin",
        "wyoming",
    }
)

META_TITLE_BRAND_SUFFIX_RE = re.compile(r"\|\s*[A-Za-z][A-Za-z0-9 .&-]{1,40}$")

PUBLISHING_THRESHOLD = 90

SEO_TARGET_SCORE = 95


__all__ = [
    "BRAND_INTERNAL_DOMAINS",
    "COMMERCIAL_PILLAR_INDEX_PATH",
    "DOWN_FUNNEL_EXACT_PATHS",
    "DOWN_FUNNEL_PATH_PREFIXES",
    "FENCED_CODE_BLOCK_RE",
    "FUNCTIONAL_DESTINATION_TERMS",
    "GENERIC_LINK_ANCHORS",
    "GEO_KEYWORD_TAIL_TOKENS",
    "HTML_COMMENT_RE",
    "MARKDOWN_IMAGE_RE",
    "META_TITLE_BRAND_SUFFIX_RE",
    "NON_VISIBLE_HTML_BLOCK_RE",
    "OWNED_INTERNAL_DOMAINS",
    "PUBLISHING_THRESHOLD",
    "SEO_TARGET_SCORE",
]
