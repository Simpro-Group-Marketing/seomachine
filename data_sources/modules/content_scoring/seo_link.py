"""Focused seo link scoring."""

from __future__ import annotations

from .seo_constants import BRAND_INTERNAL_DOMAINS
from .seo_constants import COMMERCIAL_PILLAR_INDEX_PATH
from .seo_constants import DOWN_FUNNEL_EXACT_PATHS
from .seo_constants import DOWN_FUNNEL_PATH_PREFIXES
from .seo_constants import FUNCTIONAL_DESTINATION_TERMS
from .seo_constants import GENERIC_LINK_ANCHORS
from .seo_constants import OWNED_INTERNAL_DOMAINS
from .seo_keyword import _contains_ordered_keyword_variant
from data_sources.modules.commercial_pillar_index import CommercialPillarIndexError
from data_sources.modules.commercial_pillar_index import load_index
from data_sources.modules.frontmatter import split_frontmatter
from data_sources.modules.proof_link_policy import canonicalize_link_identity
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from urllib.parse import urlparse
import re

def _count_markdown_links(
    content: str,
    *,
    brand: Optional[str] = None,
) -> Tuple[int, int]:
    """Count markdown links as internal or external for owned web content."""
    internal_count = 0
    distinct_external_urls = set()

    for _, url in _extract_markdown_links(content):
        url = url.strip()
        if not url:
            continue
        if url.startswith(("#", "mailto:", "tel:")):
            continue

        parsed = urlparse(url)
        if parsed.scheme in {"http", "https"}:
            hostname = (parsed.hostname or "").lower().rstrip(".")
            if _hostname_matches_brand(hostname, brand):
                internal_count += 1
            elif _hostname_is_group_owned(hostname):
                continue
            else:
                canonical = canonicalize_link_identity(url)
                if canonical:
                    distinct_external_urls.add(canonical)
        else:
            internal_count += 1

    return internal_count, len(distinct_external_urls)

def _extract_markdown_links(content: str) -> List[Tuple[str, str]]:
    """Extract non-image markdown links from article body."""
    _, body, _ = split_frontmatter(content)
    return [
        (anchor.strip(), url.strip())
        for anchor, url in re.findall(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)', body)
    ]

def _simpro_indexed_main_keywords(url: str) -> Optional[Tuple[str, ...]]:
    parsed = urlparse(url)
    if not parsed.scheme and not parsed.netloc and parsed.path.startswith("/"):
        return ()
    hostname = (parsed.hostname or "").casefold()
    if parsed.scheme not in {"http", "https"} or not (
        hostname == "simprogroup.com" or hostname.endswith(".simprogroup.com")
    ):
        return None
    return _verified_simpro_pillar_keywords_by_url().get(url.strip(), ())

def _verified_simpro_pillar_keywords_by_url() -> Dict[str, Tuple[str, ...]]:
    try:
        index = load_index(COMMERCIAL_PILLAR_INDEX_PATH)
    except CommercialPillarIndexError:
        return {}

    keywords: Dict[str, set[str]] = {}
    for record in index.records:
        if record.status != "verified" or record.brand.casefold() != "simpro":
            continue
        keywords.setdefault(record.canonical_url, set()).add(record.main_keyword)
    return {
        url: tuple(sorted(values, key=str.casefold))
        for url, values in keywords.items()
    }

def _anchor_contains_phrase(anchor: str, phrase: str) -> bool:
    normalized_anchor = _normalize_anchor(anchor)
    normalized_phrase = _normalize_anchor(phrase)
    if not normalized_anchor or not normalized_phrase:
        return False
    return (
        f" {normalized_phrase} " in f" {normalized_anchor} "
        or _contains_ordered_keyword_variant(normalized_anchor, normalized_phrase)
    )

def _analyze_down_funnel_links(
    content: str,
    *,
    brand: Optional[str] = None,
) -> Dict[str, List[Tuple[str, str]]]:
    analysis = {
        "valid": [],
        "generic": [],
        "name_only": [],
        "weak_anchor": [],
        "unverified_destination": [],
        "indexed_keyword_missing": [],
    }

    for anchor, url in _extract_markdown_links(content):
        path = _internal_link_path(url, brand=brand)
        if not path or not _is_down_funnel_path(path, brand=brand):
            continue

        indexed_keywords = _simpro_indexed_main_keywords(url)
        if _is_generic_anchor(anchor):
            analysis["generic"].append((anchor, url))
        elif indexed_keywords == ():
            if _is_name_only_feature_or_solution_anchor(anchor, path):
                analysis["name_only"].append((anchor, url))
            else:
                analysis["unverified_destination"].append((anchor, url))
        elif indexed_keywords is not None:
            if any(
                _anchor_contains_phrase(anchor, keyword)
                for keyword in indexed_keywords
            ):
                analysis["valid"].append((anchor, url))
            else:
                analysis["indexed_keyword_missing"].append((anchor, url))
        elif _is_name_only_feature_or_solution_anchor(anchor, path):
            analysis["name_only"].append((anchor, url))
        elif _anchor_matches_down_funnel_target(anchor, path):
            analysis["valid"].append((anchor, url))
        else:
            analysis["weak_anchor"].append((anchor, url))

    return analysis

def _internal_link_path(url: str, *, brand: Optional[str] = None) -> Optional[str]:
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"}:
        hostname = (parsed.hostname or "").lower()
        if not _hostname_matches_brand(hostname, brand):
            return None
        return _normalize_path(parsed.path)

    if url.startswith("#") or url.startswith("mailto:") or url.startswith("tel:"):
        return None

    return _normalize_path(url)

def _resolve_article_brand(
    *,
    explicit_brand: Any,
    frontmatter_brand: Any,
    meta_title: Optional[str],
) -> Optional[str]:
    for candidate in (explicit_brand, frontmatter_brand):
        if candidate is not None:
            if not isinstance(candidate, str):
                return None
            normalized = candidate.strip().casefold()
            return normalized if normalized in BRAND_INTERNAL_DOMAINS else None

    if isinstance(meta_title, str):
        suffix = re.search(r"\|\s*([^|]+?)\s*$", meta_title)
        if suffix is not None:
            normalized = suffix.group(1).strip().casefold()
            if normalized in BRAND_INTERNAL_DOMAINS:
                return normalized
    return None

def _hostname_is_group_owned(hostname: str) -> bool:
    return any(
        hostname == domain or hostname.endswith(f".{domain}")
        for domain in OWNED_INTERNAL_DOMAINS
    )

def _hostname_matches_brand(hostname: str, brand: Optional[str]) -> bool:
    brand_key = brand.casefold() if isinstance(brand, str) else None
    domains = (
        BRAND_INTERNAL_DOMAINS.get(brand_key, frozenset())
        if brand_key is not None
        else frozenset(OWNED_INTERNAL_DOMAINS)
    )
    return any(
        hostname == domain or hostname.endswith(f".{domain}")
        for domain in domains
    )

def _normalize_path(path: str) -> str:
    cleaned = path.split("#", 1)[0].split("?", 1)[0].strip()
    if not cleaned.startswith("/"):
        cleaned = "/" + cleaned
    cleaned = re.sub(r"/+", "/", cleaned)
    return cleaned.rstrip("/") or "/"

def _is_down_funnel_path(path: str, *, brand: Optional[str] = None) -> bool:
    if brand and brand.casefold() == "clockshark" and path.startswith("/tour/"):
        return True
    return path in DOWN_FUNNEL_EXACT_PATHS or any(
        path.startswith(prefix) for prefix in DOWN_FUNNEL_PATH_PREFIXES
    )

def _is_generic_anchor(anchor: str) -> bool:
    normalized = _normalize_anchor(anchor)
    return normalized in GENERIC_LINK_ANCHORS

def _is_name_only_feature_or_solution_anchor(anchor: str, path: str) -> bool:
    if not (path.startswith("/features/") or path.startswith("/solutions/")):
        return False

    normalized_anchor = _normalize_anchor(anchor)
    destination_phrase = _normalize_anchor(path.rsplit("/", 1)[-1].replace("-", " "))
    title = _internal_link_titles().get(path, "")

    name_variants = {destination_phrase}
    if title:
        name_variants.add(title)

    for name in list(name_variants):
        if name and not name.startswith("simpro "):
            name_variants.add(f"simpro {name}")

    if normalized_anchor not in name_variants:
        return False

    if normalized_anchor.startswith("simpro "):
        return True

    if path.startswith("/features/") and len(normalized_anchor.split()) <= 1:
        return True

    return not _has_functional_anchor_context(normalized_anchor)

def _has_functional_anchor_context(normalized_anchor: str) -> bool:
    return any(term in normalized_anchor for term in FUNCTIONAL_DESTINATION_TERMS)

def _anchor_matches_down_funnel_target(anchor: str, path: str) -> bool:
    normalized_anchor = _normalize_anchor(anchor)
    approved_examples = _internal_link_anchor_examples().get(path, set())
    if normalized_anchor in approved_examples:
        return True

    if path == "/industries":
        return any(
            term in normalized_anchor
            for term in ("industry", "industries", "trade", "trades")
        )

    if path == "/features":
        return (
            len(normalized_anchor.split()) >= 2
            and _has_functional_anchor_context(normalized_anchor)
        )

    destination_phrase = path.rsplit("/", 1)[-1].replace("-", " ")
    if destination_phrase and destination_phrase in normalized_anchor:
        return True

    destination_terms = [
        term
        for term in destination_phrase.split()
        if term not in {"software", "for", "and", "the", "simpro"}
    ]
    return bool(destination_terms) and any(term in normalized_anchor for term in destination_terms)

def _normalize_anchor(anchor: str) -> str:
    text = re.sub(r"<[^>]+>", " ", anchor)
    text = re.sub(r"[*_`]", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()

def _internal_link_titles() -> Dict[str, str]:
    link_map_path = Path(__file__).resolve().parents[2] / "context" / "internal-links-map.md"
    titles: Dict[str, str] = {}

    if not link_map_path.exists():
        return titles

    current_title = ""
    for line in link_map_path.read_text(encoding="utf-8").splitlines():
        title_match = re.match(r"^###\s+(.+)", line)
        if title_match:
            current_title = _normalize_anchor(title_match.group(1))
            continue

        url_match = re.match(r"- \*\*URL\*\*:\s*(\S+)", line)
        if url_match and current_title:
            current_path = _internal_link_path(url_match.group(1))
            if current_path:
                titles[current_path] = current_title

    return titles

def _internal_link_anchor_examples() -> Dict[str, set]:
    link_map_path = Path(__file__).resolve().parents[2] / "context" / "internal-links-map.md"
    examples: Dict[str, set] = {}

    if not link_map_path.exists():
        return examples

    current_path = None
    for line in link_map_path.read_text(encoding="utf-8").splitlines():
        url_match = re.match(r"- \*\*URL\*\*:\s*(\S+)", line)
        if url_match:
            current_path = _internal_link_path(url_match.group(1))
            continue

        if current_path is None:
            continue

        anchor_match = re.match(r"- \*\*Anchor Text Examples\*\*:\s*(.+)", line)
        if not anchor_match:
            continue

        examples[current_path] = {
            _normalize_anchor(example)
            for example in anchor_match.group(1).split(",")
            if example.strip()
        }

    return examples


__all__ = [
    "_count_markdown_links",
    "_extract_markdown_links",
    "_simpro_indexed_main_keywords",
    "_verified_simpro_pillar_keywords_by_url",
    "_anchor_contains_phrase",
    "_analyze_down_funnel_links",
    "_internal_link_path",
    "_resolve_article_brand",
    "_hostname_is_group_owned",
    "_hostname_matches_brand",
    "_normalize_path",
    "_is_down_funnel_path",
    "_is_generic_anchor",
    "_is_name_only_feature_or_solution_anchor",
    "_has_functional_anchor_context",
    "_anchor_matches_down_funnel_target",
    "_normalize_anchor",
    "_internal_link_titles",
    "_internal_link_anchor_examples",
]
