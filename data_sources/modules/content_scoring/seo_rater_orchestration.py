"""Focused seo rater orchestration scoring."""

from __future__ import annotations

from .seo_constants import NON_VISIBLE_HTML_BLOCK_RE
from .seo_constants import PUBLISHING_THRESHOLD
from .seo_constants import SEO_TARGET_SCORE
from .seo_link import _resolve_article_brand
from .seo_metadata import seo_target_status
from data_sources.modules.frontmatter import split_frontmatter
from data_sources.modules.url_validator import validate_content_urls
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
import math
from .seo_config import SeoConfigMixin
from .seo_keyword import SeoKeywordMixin
from .seo_link_scoring import SeoLinkMixin
from .seo_structure_quality import SeoStructureQualityMixin

class SeoRaterOrchestrationMixin:
    def rate(
            self,
            content: str,
            meta_title: Optional[str] = None,
            meta_description: Optional[str] = None,
            primary_keyword: Optional[str] = None,
            secondary_keywords: Optional[List[str]] = None,
            keyword_density: Optional[float] = None,
            internal_link_count: Optional[int] = None,
            external_link_count: Optional[int] = None,
            validate_urls: bool = False,
            brand: Optional[str] = None,
        ) -> Dict[str, Any]:
            """
            Rate content against SEO best practices

            Args:
                content: Article content
                meta_title: Meta title tag
                meta_description: Meta description tag
                primary_keyword: Target primary keyword
                secondary_keywords: Target secondary keywords
                keyword_density: Deprecated diagnostic input. It is validated for
                    compatibility but never changes the quality score.
                internal_link_count: Number of internal links
                external_link_count: Number of external links
                validate_urls: Resolve URLs and block publishing readiness on
                    unresolved/manual-review links. With URL validation enabled,
                    the external-link requirement means resolved non-owned public
                    research links; owned Simpro and ClockShark links do not count.

            Returns:
                Dict with overall score, category scores, and recommendations
            """
            _validate_rate_inputs(
                content=content,
                meta_title=meta_title,
                meta_description=meta_description,
                primary_keyword=primary_keyword,
                secondary_keywords=secondary_keywords,
                keyword_density=keyword_density,
                internal_link_count=internal_link_count,
                external_link_count=external_link_count,
                validate_urls=validate_urls,
            )

            frontmatter, visible_body, _ = split_frontmatter(content)
            analysis_body = NON_VISIBLE_HTML_BLOCK_RE.sub("", visible_body)
            article_brand = _resolve_article_brand(
                explicit_brand=brand,
                frontmatter_brand=frontmatter.get("brand"),
                meta_title=meta_title,
            )

            # Extract structure from reader-visible copy only. Frontmatter remains
            # available to metadata resolution, but it is never article prose.
            # Structured data and CSS are also excluded because browsers do not
            # render their text as article copy.
            primary_aeo_topic = frontmatter.get("primary_aeo_topic")
            title_keyword = (
                primary_aeo_topic.strip()
                if isinstance(primary_aeo_topic, str) and primary_aeo_topic.strip()
                else primary_keyword
            )
            structure = self._analyze_structure(
                analysis_body,
                primary_keyword,
                h1_keyword=title_keyword,
            )

            # Score each category
            content_score = self._score_content(analysis_body, structure)
            keyword_score = self._score_keyword_optimization(
                analysis_body,
                structure,
                primary_keyword,
                secondary_keywords,
                keyword_density=keyword_density,
                h1_keyword=title_keyword,
            )
            meta_score = self._score_meta_elements(
                meta_title,
                meta_description,
                title_keyword
            )
            structure_score = self._score_structure(structure)
            link_score = self._score_links(
                analysis_body,
                internal_link_count,
                external_link_count,
                brand=article_brand,
            )
            readability_score = self._score_readability(analysis_body, structure)

            # Calculate overall score (weighted average)
            weights = {
                'content': 0.20,
                'keywords': 0.25,
                'meta': 0.15,
                'structure': 0.15,
                'links': 0.15,
                'readability': 0.10
            }

            overall_score = (
                content_score['score'] * weights['content'] +
                keyword_score['score'] * weights['keywords'] +
                meta_score['score'] * weights['meta'] +
                structure_score['score'] * weights['structure'] +
                link_score['score'] * weights['links'] +
                readability_score['score'] * weights['readability']
            )

            # Compile all issues
            critical_issues = []
            warnings = []
            suggestions = []

            for category in [content_score, keyword_score, meta_score, structure_score, link_score, readability_score]:
                critical_issues.extend(category.get('critical', []))
                warnings.extend(category.get('warnings', []))
                suggestions.extend(category.get('suggestions', []))

            url_validation = None
            if validate_urls:
                url_validation = validate_content_urls(visible_body)
                for result in url_validation.blockers:
                    location = f" on line {result.line}" if result.line else ""
                    code = f"HTTP {result.status_code}" if result.status_code is not None else result.reason
                    if result.status == "manual_review":
                        critical_issues.append(
                            "Unresolved URL manual review blocker"
                            f"{location}: {result.url} ({code}). Replace this source "
                            "with an equivalent resolved public source or remove the "
                            "supported claim. Do not remove the citation without replacing "
                            "it with a resolved source supporting the same claim."
                        )
                    else:
                        critical_issues.append(
                            f"Unresolved URL{location}: {result.url} ({code})"
                        )

            details = {
                'word_count': structure['word_count'],
                'keyword_density': keyword_density,
                'h2_count': structure['h2_count'],
                'has_h1': structure['has_h1'],
                'keyword_in_h1': structure.get('keyword_in_h1', False),
                'keyword_in_first_100': structure.get('keyword_in_first_100', False),
                'h1_keyword': title_keyword,
            }
            if url_validation is not None:
                details['url_validation'] = {
                    'total': url_validation.total,
                    'resolved': url_validation.resolved_count,
                    'unresolved': url_validation.unresolved_count,
                    'manual_review': url_validation.manual_review_count,
                    'passed': url_validation.passed
                }

            publishing_ready = (
                overall_score >= PUBLISHING_THRESHOLD
                and len(critical_issues) == 0
            )
            rounded_score = round(overall_score, 1)

            return {
                'overall_score': rounded_score,
                'grade': self._get_grade(overall_score),
                'threshold': PUBLISHING_THRESHOLD,
                'target': SEO_TARGET_SCORE,
                'passed': publishing_ready,
                'target_met': overall_score >= SEO_TARGET_SCORE,
                'target_status': seo_target_status(
                    score=overall_score,
                    publishing_ready=publishing_ready,
                ),
                'category_scores': {
                    'content': content_score['score'],
                    'keyword_optimization': keyword_score['score'],
                    'meta_elements': meta_score['score'],
                    'structure': structure_score['score'],
                    'links': link_score['score'],
                    'readability': readability_score['score']
                },
                'critical_issues': critical_issues,
                'warnings': warnings,
                'suggestions': suggestions,
                'publishing_ready': publishing_ready,
                'details': details
            }


def _validate_rate_inputs(
    *,
    content: object,
    meta_title: object,
    meta_description: object,
    primary_keyword: object,
    secondary_keywords: object,
    keyword_density: object,
    internal_link_count: object,
    external_link_count: object,
    validate_urls: object,
) -> None:
    if not isinstance(content, str):
        raise ValueError("content must be a string")
    _validate_optional_strings(
        meta_title=meta_title,
        meta_description=meta_description,
        primary_keyword=primary_keyword,
    )
    if secondary_keywords is not None and (
        not isinstance(secondary_keywords, list)
        or any(
            not isinstance(keyword, str) or not keyword.strip()
            for keyword in secondary_keywords
        )
    ):
        raise ValueError("secondary_keywords must be a list of non-empty strings or None")
    _validate_optional_counts(
        internal_link_count=internal_link_count,
        external_link_count=external_link_count,
    )
    if not isinstance(validate_urls, bool):
        raise ValueError("validate_urls must be a boolean")
    if keyword_density is not None and (
        isinstance(keyword_density, bool)
        or not isinstance(keyword_density, (int, float))
        or not math.isfinite(keyword_density)
        or keyword_density < 0
    ):
        raise ValueError("keyword_density must be a finite non-negative number or None")


def _validate_optional_strings(**values: object) -> None:
    for field_name, value in values.items():
        if value is not None and not isinstance(value, str):
            raise ValueError(f"{field_name} must be a string or None")


def _validate_optional_counts(**values: object) -> None:
    for field_name, value in values.items():
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or value < 0
        ):
            raise ValueError(f"{field_name} must be a non-negative integer or None")


class SEOQualityRater(
    SeoConfigMixin,
    SeoRaterOrchestrationMixin,
    SeoStructureQualityMixin,
    SeoKeywordMixin,
    SeoLinkMixin,
):
    """Rate content against SEO best practices."""


def rate_seo_quality(
    content: str,
    meta_title: Optional[str] = None,
    meta_description: Optional[str] = None,
    primary_keyword: Optional[str] = None,
    secondary_keywords: Optional[List[str]] = None,
    keyword_density: Optional[float] = None,
    internal_link_count: Optional[int] = None,
    external_link_count: Optional[int] = None,
    custom_guidelines: Optional[Dict[str, Any]] = None,
    validate_urls: bool = False,
    brand: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Rate SEO quality of content

    Args:
        content: Article content
        meta_title: Meta title
        meta_description: Meta description
        primary_keyword: Target keyword
        secondary_keywords: Secondary keywords
        keyword_density: Deprecated diagnostic input retained for compatibility
        internal_link_count: Number of internal links
        external_link_count: Number of external links
        custom_guidelines: Custom SEO guidelines
        validate_urls: Resolve URLs and block publishing readiness on failures.
            With URL validation enabled, external links are expected to be
            resolved non-owned public research links; owned Simpro and
            ClockShark links do not count as external research.

    Returns:
        SEO quality rating with score and recommendations
    """
    rater = SEOQualityRater(custom_guidelines)
    return rater.rate(
        content,
        meta_title,
        meta_description,
        primary_keyword,
        secondary_keywords,
        keyword_density,
        internal_link_count,
        external_link_count,
        validate_urls,
        brand,
    )

__all__ = [
    "SeoRaterOrchestrationMixin",
    "SEOQualityRater",
    "rate_seo_quality",
]
