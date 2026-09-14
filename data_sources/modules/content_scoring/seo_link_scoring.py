"""SEO link score orchestration with focused policy helpers."""

from __future__ import annotations

from typing import Any
from typing import Dict
from typing import List
from typing import Mapping
from typing import Optional
from typing import Tuple

from .seo_link import _analyze_down_funnel_links
from .seo_link import _count_markdown_links
from .seo_link import _simpro_indexed_main_keywords
from .seo_metadata import _count_visible_words


FindingBundle = Tuple[int, List[str], List[str], List[str]]


class SeoLinkMixin:
    """Score article link counts and down-funnel link quality."""

    def _score_links(
        self,
        content: str,
        internal_count: Optional[int],
        external_count: Optional[int],
        *,
        brand: Optional[str] = None,
    ) -> Dict[str, Any]:
        internal_count, external_count = _resolve_link_counts(
            content,
            internal_count,
            external_count,
            brand=brand,
        )
        bundles = (
            _internal_minimum_findings(self.guidelines, internal_count),
            _internal_maximum_findings(self.guidelines, content, internal_count),
            _down_funnel_findings(self.guidelines, content, brand=brand),
            _external_findings(self.guidelines, external_count),
        )
        penalty, critical, warnings, suggestions = _combine_findings(bundles)
        return {
            "score": max(0, 100 - penalty),
            "critical": critical,
            "warnings": warnings,
            "suggestions": suggestions,
        }


def _resolve_link_counts(
    content: str,
    internal_count: Optional[int],
    external_count: Optional[int],
    *,
    brand: Optional[str],
) -> Tuple[int, int]:
    inferred_internal, inferred_external = _count_markdown_links(content, brand=brand)
    return (
        inferred_internal if internal_count is None else internal_count,
        inferred_external if external_count is None else external_count,
    )


def _internal_minimum_findings(
    guidelines: Mapping[str, Any],
    internal_count: int,
) -> FindingBundle:
    minimum = guidelines["min_internal_links"]
    optimal = guidelines["optimal_internal_links"]
    if minimum is not None and internal_count < minimum:
        target = optimal if optimal is not None else minimum
        warning = (
            f"Too few internal links ({internal_count}). "
            f"Add {minimum - internal_count} more (target: {target})."
        )
        return 20, [], [warning], []
    if optimal is not None and internal_count < optimal:
        suggestion = (
            f"Could add more internal links ({internal_count}). Optimal is {optimal}."
        )
        return 5, [], [], [suggestion]
    return 0, [], [], []


def _internal_maximum_findings(
    guidelines: Mapping[str, Any],
    content: str,
    internal_count: int,
) -> FindingBundle:
    maximum = guidelines["max_internal_links"]
    exemption = guidelines["long_form_internal_link_exemption_word_count"]
    if maximum is None or internal_count <= maximum:
        return 0, [], [], []
    if exemption is not None and _count_visible_words(content) >= exemption:
        return 0, [], [], []
    warning = _maximum_link_warning(internal_count, maximum, exemption)
    return 5, [], [warning], []


def _maximum_link_warning(
    internal_count: int,
    maximum: int,
    exemption: Optional[int],
) -> str:
    if exemption is None:
        return (
            f"Too many internal links ({internal_count}). "
            f"Keep standard posts to {maximum} or fewer."
        )
    return (
        f"Too many internal links ({internal_count}) for a standard blog. "
        f"Keep standard posts to {maximum} or fewer unless the article "
        f"is {exemption}+ words."
    )


def _down_funnel_findings(
    guidelines: Mapping[str, Any],
    content: str,
    *,
    brand: Optional[str],
) -> FindingBundle:
    if not guidelines["require_down_funnel_link"]:
        return 0, [], [], []
    analysis = _analyze_down_funnel_links(content, brand=brand)
    issue = _down_funnel_issue(analysis)
    if issue is None:
        return 0, [], [], []
    return 20, [issue], [], []


def _down_funnel_issue(analysis: Mapping[str, List[Tuple[str, str]]]) -> Optional[str]:
    if analysis["generic"]:
        anchor, url = analysis["generic"][0]
        return (
            "A down-funnel internal link uses generic anchor text. "
            f"Replace '{anchor}' for {url} with destination-matched anchor text."
        )
    if analysis["name_only"]:
        anchor, url = analysis["name_only"][0]
        return (
            "A feature or solution link uses name-only anchor text. "
            f"Replace '{anchor}' for {url} with functional anchor text that describes "
            "the workflow, category, or outcome."
        )
    if analysis["valid"]:
        return None
    return _invalid_down_funnel_issue(analysis)


def _invalid_down_funnel_issue(
    analysis: Mapping[str, List[Tuple[str, str]]],
) -> str:
    if analysis["unverified_destination"]:
        anchor, url = analysis["unverified_destination"][0]
        return (
            "A Simpro down-funnel link must match a verified commercial pillar index "
            "destination with an exact absolute canonical URL. "
            f"Check '{anchor}' for {url} against context/commercial-pillar-index.json."
        )
    if analysis["indexed_keyword_missing"]:
        return _indexed_keyword_issue(analysis["indexed_keyword_missing"][0])
    if analysis["weak_anchor"]:
        anchor, url = analysis["weak_anchor"][0]
        return (
            "A down-funnel internal link anchor text must match the destination keyword. "
            f"Replace '{anchor}' for {url} with a product, solution, feature, or industry keyword."
        )
    return (
        "Missing down-funnel internal link to /, /industries, /industries/..., "
        "/solutions/..., or /features/... with matched anchor text."
    )


def _indexed_keyword_issue(link: Tuple[str, str]) -> str:
    anchor, url = link
    indexed_keywords = _simpro_indexed_main_keywords(url) or ()
    return (
        "A down-funnel internal link anchor text must include an indexed main keyword. "
        f"Replace '{anchor}' for {url} with one of: {', '.join(indexed_keywords)}."
    )


def _external_findings(
    guidelines: Mapping[str, Any],
    external_count: int,
) -> FindingBundle:
    minimum = guidelines["min_external_links"]
    if minimum is None or external_count >= minimum:
        return 0, [], [], []
    warning = (
        f"Too few non-owned public research links ({external_count}). "
        f"Add authoritative resolved sources (baseline: {minimum})."
    )
    return 15, [], [warning], []


def _combine_findings(
    bundles: Tuple[FindingBundle, ...],
) -> FindingBundle:
    penalty = sum(bundle[0] for bundle in bundles)
    critical = [item for bundle in bundles for item in bundle[1]]
    warnings = [item for bundle in bundles for item in bundle[2]]
    suggestions = [item for bundle in bundles for item in bundle[3]]
    return penalty, critical, warnings, suggestions


__all__ = ["SeoLinkMixin"]
