"""
SEO Quality Rater

Rates content quality against SEO best practices and guidelines.
Provides scoring (0-100) and specific recommendations for improvement.
"""

import argparse
from datetime import date
from functools import lru_cache
import math
import re
import sys
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, List, Optional, Any, Tuple

try:
    from .frontmatter import split_frontmatter
    from .proof_link_policy import canonicalize_link_identity
    from .url_validator import validate_content_urls
except ImportError:
    from frontmatter import split_frontmatter
    from proof_link_policy import canonicalize_link_identity
    from url_validator import validate_content_urls


DOWN_FUNNEL_PATH_PREFIXES = (
    "/features/",
    "/industries/",
    "/solutions/",
)
DOWN_FUNNEL_EXACT_PATHS = {
    "/features",
    "/industries",
}
COMMERCIAL_PILLAR_INDEX_PATH = (
    Path(__file__).resolve().parents[2] / "context" / "commercial-pillar-index.json"
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


def seo_target_status(
    *,
    score: float,
    publishing_ready: bool,
    target: int = SEO_TARGET_SCORE,
) -> str:
    """Classify SEO target status without changing release readiness."""
    if not publishing_ready:
        return "failed_floor"
    if score >= target:
        return "met"
    return "below_target"


def _non_negative_finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0:
        raise argparse.ArgumentTypeError("must be a finite non-negative number")
    return parsed


def _has_meta_title_brand_suffix(meta_title: str) -> bool:
    return bool(META_TITLE_BRAND_SUFFIX_RE.search(meta_title.strip()))


class SEOQualityRater:
    """Rates content against SEO best practices"""

    def __init__(self, guidelines: Optional[Dict[str, Any]] = None):
        """
        Initialize SEO Quality Rater

        Args:
            guidelines: Custom SEO guidelines (defaults to standard best practices)
        """
        supplied_guidelines = dict(guidelines or {})
        self.guidelines = {
            **self._default_guidelines(),
            **supplied_guidelines,
        }
        self._validate_word_count_guidelines()
        self._validate_h2_guidelines()
        self._validate_link_guidelines()

    def _validate_word_count_guidelines(self) -> None:
        word_count_keys = (
            'min_word_count',
            'optimal_word_count',
            'max_word_count',
        )
        for key in word_count_keys:
            value = self.guidelines.get(key)
            if value is None:
                continue
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value <= 0
            ):
                raise ValueError(f"{key} must be a positive integer or None")

        minimum = self.guidelines.get('min_word_count')
        optimal = self.guidelines.get('optimal_word_count')
        maximum = self.guidelines.get('max_word_count')
        if minimum is not None and optimal is not None and minimum > optimal:
            raise ValueError(
                "word_count rules require min_word_count <= optimal_word_count"
            )
        if optimal is not None and maximum is not None and optimal > maximum:
            raise ValueError(
                "word_count rules require optimal_word_count <= max_word_count"
            )
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError(
                "word_count rules require min_word_count <= max_word_count"
            )

    def _validate_h2_guidelines(self) -> None:
        for key in ("min_h2_sections", "optimal_h2_sections"):
            value = self.guidelines.get(key)
            if value is None:
                continue
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value <= 0
            ):
                raise ValueError(f"{key} must be a positive integer or None")

        min_h2 = self.guidelines.get("min_h2_sections")
        optimal_h2 = self.guidelines.get("optimal_h2_sections")
        if min_h2 is not None and optimal_h2 is not None and min_h2 > optimal_h2:
            raise ValueError(
                "min_h2_sections must be less than or equal to optimal_h2_sections"
            )

        ratio = self.guidelines.get("h2_with_keyword_ratio")
        if ratio is not None and (
            isinstance(ratio, bool)
            or not isinstance(ratio, (int, float))
            or not math.isfinite(ratio)
            or ratio <= 0
            or ratio > 1
        ):
            raise ValueError(
                "h2_with_keyword_ratio must be a finite number from 0 to 1 or None"
            )

    def _validate_link_guidelines(self) -> None:
        for key in (
            'min_internal_links',
            'optimal_internal_links',
            'max_internal_links',
            'min_external_links',
            'optimal_external_links',
        ):
            value = self.guidelines.get(key)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{key} must be a non-negative integer or None")

        for minimum_key, optimal_key in (
            ('min_internal_links', 'optimal_internal_links'),
            ('min_external_links', 'optimal_external_links'),
        ):
            minimum = self.guidelines.get(minimum_key)
            optimal = self.guidelines.get(optimal_key)
            if minimum is not None and optimal is not None and minimum > optimal:
                raise ValueError(
                    f"{minimum_key} must be less than or equal to {optimal_key}"
                )

        max_internal = self.guidelines.get('max_internal_links')
        for key in ('min_internal_links', 'optimal_internal_links'):
            value = self.guidelines.get(key)
            if value is not None and max_internal is not None and value > max_internal:
                raise ValueError(f"{key} must be less than or equal to max_internal_links")

        long_form_exemption = self.guidelines.get(
            'long_form_internal_link_exemption_word_count'
        )
        if long_form_exemption is not None and (
            isinstance(long_form_exemption, bool)
            or not isinstance(long_form_exemption, int)
            or long_form_exemption <= 0
        ):
            raise ValueError(
                "long_form_internal_link_exemption_word_count must be a positive integer or None"
            )
        require_down_funnel = self.guidelines.get('require_down_funnel_link')
        if not isinstance(require_down_funnel, bool):
            raise ValueError("require_down_funnel_link must be a boolean")

    def _default_guidelines(self) -> Dict[str, Any]:
        """Default SEO guidelines for proof-sensitive, intent-led blog quality."""
        return {
            'min_word_count': None,
            'optimal_word_count': None,
            'max_word_count': None,
            'min_internal_links': 3,
            'optimal_internal_links': 5,
            'max_internal_links': 7,
            'long_form_internal_link_exemption_word_count': 3000,
            'min_external_links': 2,
            'optimal_external_links': 2,
            'require_down_funnel_link': True,
            'meta_title_length_min': 50,
            'meta_title_length_max': 60,
            'meta_description_length_min': 150,
            'meta_description_length_max': 160,
            'min_h2_sections': None,
            'optimal_h2_sections': None,
            'h2_with_keyword_ratio': None,
            'max_sentence_length': 25,
            'target_reading_level_min': 8,
            'target_reading_level_max': 10,
            'paragraph_sentence_min': 2,
            'paragraph_sentence_max': 4,
        }

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
        if not isinstance(content, str):
            raise ValueError("content must be a string")
        for field_name, value in (
            ("meta_title", meta_title),
            ("meta_description", meta_description),
            ("primary_keyword", primary_keyword),
        ):
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{field_name} must be a string or None")
        if secondary_keywords is not None and (
            not isinstance(secondary_keywords, list)
            or any(
                not isinstance(keyword, str) or not keyword.strip()
                for keyword in secondary_keywords
            )
        ):
            raise ValueError(
                "secondary_keywords must be a list of non-empty strings or None"
            )
        for field_name, value in (
            ("internal_link_count", internal_link_count),
            ("external_link_count", external_link_count),
        ):
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer or None"
                )
        if not isinstance(validate_urls, bool):
            raise ValueError("validate_urls must be a boolean")
        if keyword_density is not None and (
            isinstance(keyword_density, bool)
            or not isinstance(keyword_density, (int, float))
            or not math.isfinite(keyword_density)
            or keyword_density < 0
        ):
            raise ValueError(
                "keyword_density must be a finite non-negative number or None"
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
        structure = self._analyze_structure(analysis_body, primary_keyword)

        # Score each category
        content_score = self._score_content(analysis_body, structure)
        keyword_score = self._score_keyword_optimization(
            analysis_body,
            structure,
            primary_keyword,
            secondary_keywords,
        )
        meta_score = self._score_meta_elements(
            meta_title,
            meta_description,
            primary_keyword
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
            'keyword_in_first_100': structure.get('keyword_in_first_100', False)
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

    def _analyze_structure(self, content: str, primary_keyword: Optional[str]) -> Dict[str, Any]:
        """Analyze content structure"""
        lines = content.split('\n')

        # Extract headings
        h1_count = 0
        h2_count = 0
        h3_count = 0
        h1_text = ""
        h2_texts = []
        h3_texts = []

        for line in lines:
            h1_match = re.match(r'^#\s+(.+)$', line)
            h2_match = re.match(r'^##\s+(.+)$', line)
            h3_match = re.match(r'^###\s+(.+)$', line)

            if h1_match:
                h1_count += 1
                if not h1_text:  # First H1
                    h1_text = h1_match.group(1)
            elif h2_match:
                h2_count += 1
                h2_texts.append(h2_match.group(1))
            elif h3_match:
                h3_count += 1
                h3_texts.append(h3_match.group(1))

        # Word count
        word_count = len(content.split())

        # Paragraph analysis
        paragraphs = [p for p in content.split('\n\n') if p.strip() and not p.strip().startswith('#')]
        avg_paragraph_length = sum(len(p.split()) for p in paragraphs) / len(paragraphs) if paragraphs else 0

        # Keyword checks
        keyword_in_h1 = False
        keyword_in_first_100 = False
        h2_with_keyword = 0

        if primary_keyword:
            keyword_lower = primary_keyword.lower()
            keyword_in_h1 = _contains_ordered_keyword_variant(h1_text, keyword_lower)
            first_100_words = ' '.join(content.split()[:100]).lower()
            keyword_in_first_100 = _contains_ordered_keyword_variant(
                first_100_words,
                keyword_lower,
            )

            for h2 in h2_texts:
                if keyword_lower in h2.lower():
                    h2_with_keyword += 1

        return {
            'word_count': word_count,
            'has_h1': h1_count > 0,
            'h1_count': h1_count,
            'h1_text': h1_text,
            'h2_count': h2_count,
            'h2_texts': h2_texts,
            'h3_count': h3_count,
            'paragraph_count': len(paragraphs),
            'avg_paragraph_length': avg_paragraph_length,
            'keyword_in_h1': keyword_in_h1,
            'keyword_in_first_100': keyword_in_first_100,
            'h2_with_keyword': h2_with_keyword
        }

    def _score_content(self, content: str, structure: Dict) -> Dict[str, Any]:
        """Score content length and quality"""
        score = 100
        critical = []
        warnings = []
        suggestions = []

        word_count = structure['word_count']
        min_words = self.guidelines['min_word_count']
        optimal_words = self.guidelines['optimal_word_count']
        max_words = self.guidelines['max_word_count']

        # Word count is context, not a default quality proxy. Custom guidelines
        # can still opt into explicit length targets when a workflow needs them.
        if min_words is not None and word_count < min_words:
            score -= 30
            critical.append(f"Content is too short ({word_count} words). Minimum is {min_words} words.")
        elif optimal_words is not None and word_count < optimal_words:
            score -= 10
            warnings.append(f"Content could be longer ({word_count} words). Optimal is {optimal_words}+ words.")
        elif max_words is not None and word_count > max_words:
            score -= 5
            suggestions.append(f"Content is quite long ({word_count} words). Consider breaking into multiple articles if over {max_words} words.")

        # Paragraph length
        avg_para = structure['avg_paragraph_length']
        if avg_para > 150:
            score -= 10
            warnings.append(f"Paragraphs are too long (avg {avg_para:.0f} words). Break into 2-4 sentence paragraphs.")
        elif avg_para < 30:
            score -= 5
            suggestions.append(f"Paragraphs are very short (avg {avg_para:.0f} words). Add more detail where appropriate.")

        return {
            'score': max(0, score),
            'critical': critical,
            'warnings': warnings,
            'suggestions': suggestions
        }

    def _score_keyword_optimization(
        self,
        content: str,
        structure: Dict,
        primary_keyword: Optional[str],
        secondary_keywords: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Score keyword optimization"""
        score = 100
        critical = []
        warnings = []
        suggestions = []

        if not primary_keyword:
            return {
                'score': 50,
                'critical': ['No primary keyword specified'],
                'warnings': [],
                'suggestions': []
            }

        # Keyword in H1
        if not structure['keyword_in_h1']:
            score -= 20
            critical.append(f"Primary keyword '{primary_keyword}' missing from H1 heading")

        # Keyword in first 100 words
        if not structure['keyword_in_first_100']:
            score -= 15
            critical.append(f"Primary keyword '{primary_keyword}' missing from first 100 words")

        # Keyword in H2 headings
        h2_count = structure['h2_count']
        h2_with_kw = structure['h2_with_keyword']
        if h2_count > 0:
            target_ratio = self.guidelines['h2_with_keyword_ratio']
            if target_ratio is None and h2_with_kw == 0:
                score -= 10
                warnings.append(
                    "Primary keyword is missing from H2 headings. Add it to one "
                    "relevant H2 where the wording is natural."
                )
            elif target_ratio is not None and h2_with_kw / h2_count < target_ratio:
                score -= 10
                warnings.append(
                    f"Keyword appears in only {h2_with_kw}/{h2_count} H2 headings. "
                    f"The caller-supplied target is at least {int(target_ratio * 100)}%."
                )

        repetition = self._contextual_keyword_repetition(content, primary_keyword)
        if repetition:
            score -= 20
            critical.append(
                "Contextual keyword stuffing detected: "
                f"{repetition}. Remove forced exact-phrase repetition and use "
                "natural terminology where it helps the reader."
            )
        # Secondary keywords
        if secondary_keywords:
            content_lower = content.lower()
            missing_keywords = [kw for kw in secondary_keywords if kw.lower() not in content_lower]
            if missing_keywords:
                score -= 5
                suggestions.append(f"Secondary keywords not found: {', '.join(missing_keywords)}")

        return {
            'score': max(0, score),
            'critical': critical,
            'warnings': warnings,
            'suggestions': suggestions
        }

    @staticmethod
    def _contextual_keyword_repetition(
        content: str,
        primary_keyword: str,
    ) -> Optional[str]:
        """Describe forced exact-phrase repetition in reader-visible prose."""
        escaped = r"\s+".join(
            re.escape(part)
            for part in primary_keyword.strip().split()
        )
        keyword_pattern = re.compile(
            rf"(?<!\w){escaped}(?!\w)",
            re.IGNORECASE,
        )
        reader_visible = HTML_COMMENT_RE.sub("", content)
        reader_visible = FENCED_CODE_BLOCK_RE.sub("", reader_visible)
        reader_visible = MARKDOWN_IMAGE_RE.sub("", reader_visible)
        prose = "\n".join(
            line
            for line in reader_visible.splitlines()
            if not re.match(r"^\s*#", line)
        )
        sentences = [
            sentence.strip()
            for sentence in re.split(r"[.!?]+(?:\s|$)", prose)
            if sentence.strip()
        ]

        consecutive = 0
        longest_run = 0
        for sentence in sentences:
            occurrences = len(keyword_pattern.findall(sentence))
            if occurrences >= 2:
                return "the exact primary keyword appears more than once in one sentence"
            if occurrences == 1:
                consecutive += 1
                longest_run = max(longest_run, consecutive)
            else:
                consecutive = 0

        if longest_run >= 3:
            return (
                "the exact primary keyword appears in "
                f"{longest_run} consecutive sentences"
            )
        return None

    def _score_meta_elements(
        self,
        meta_title: Optional[str],
        meta_description: Optional[str],
        primary_keyword: Optional[str]
    ) -> Dict[str, Any]:
        """Score meta title and description"""
        score = 100
        critical = []
        warnings = []
        suggestions = []

        # Meta title
        if not meta_title:
            score -= 40
            critical.append("Meta title is missing")
        else:
            title_len = len(meta_title)
            min_len = self.guidelines['meta_title_length_min']
            max_len = self.guidelines['meta_title_length_max']

            if title_len < min_len:
                score -= 15
                warnings.append(f"Meta title too short ({title_len} chars). Target is {min_len}-{max_len} chars.")
            elif title_len > max_len + 10:
                score -= 10
                warnings.append(f"Meta title too long ({title_len} chars). Target is {min_len}-{max_len} chars.")

            if primary_keyword and primary_keyword.lower() not in meta_title.lower():
                score -= 15
                warnings.append(f"Primary keyword '{primary_keyword}' not in meta title")

            if not _has_meta_title_brand_suffix(meta_title):
                score -= 10
                warnings.append('Meta title must end with a brand suffix like " | Simpro" or " | ClockShark".')

        # Meta description
        if not meta_description:
            score -= 40
            critical.append("Meta description is missing")
        else:
            desc_len = len(meta_description)
            min_len = self.guidelines['meta_description_length_min']
            max_len = self.guidelines['meta_description_length_max']

            if desc_len < min_len:
                score -= 15
                warnings.append(f"Meta description too short ({desc_len} chars). Target is {min_len}-{max_len} chars.")
            elif desc_len > max_len + 10:
                score -= 10
                warnings.append(f"Meta description too long ({desc_len} chars). Target is {min_len}-{max_len} chars.")

            if primary_keyword and primary_keyword.lower() not in meta_description.lower():
                score -= 10
                suggestions.append(f"Primary keyword '{primary_keyword}' not in meta description")

        return {
            'score': max(0, score),
            'critical': critical,
            'warnings': warnings,
            'suggestions': suggestions
        }

    def _score_structure(self, structure: Dict) -> Dict[str, Any]:
        """Score content structure"""
        score = 100
        critical = []
        warnings = []
        suggestions = []

        # H1 check
        if not structure['has_h1']:
            score -= 30
            critical.append("Missing H1 heading")
        elif structure['h1_count'] > 1:
            score -= 20
            critical.append(f"Multiple H1 headings found ({structure['h1_count']}). Should only have one.")

        # H2 count
        h2_count = structure['h2_count']
        min_h2 = self.guidelines['min_h2_sections']
        optimal_h2 = self.guidelines['optimal_h2_sections']

        if min_h2 is not None and h2_count < min_h2:
            score -= 15
            target = optimal_h2 if optimal_h2 is not None else min_h2
            warnings.append(
                f"Too few H2 sections ({h2_count}) for the caller-supplied rule "
                f"(target: {target})."
            )
        elif optimal_h2 is not None and h2_count < optimal_h2:
            score -= 5
            suggestions.append(
                f"H2 count ({h2_count}) is below the caller-supplied optimal "
                f"of {optimal_h2} sections."
            )

        return {
            'score': max(0, score),
            'critical': critical,
            'warnings': warnings,
            'suggestions': suggestions
        }

    def _score_links(
        self,
        content: str,
        internal_count: Optional[int],
        external_count: Optional[int],
        *,
        brand: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Score internal and external linking"""
        score = 100
        critical = []
        warnings = []
        suggestions = []

        # Count links if not provided
        if internal_count is None:
            internal_count, inferred_external_count = _count_markdown_links(
                content,
                brand=brand,
            )
            if external_count is None:
                external_count = inferred_external_count

        if external_count is None:
            _, external_count = _count_markdown_links(content, brand=brand)

        # Internal links
        min_internal = self.guidelines['min_internal_links']
        optimal_internal = self.guidelines['optimal_internal_links']

        if min_internal is not None and internal_count < min_internal:
            score -= 20
            target = optimal_internal if optimal_internal is not None else min_internal
            warnings.append(
                f"Too few internal links ({internal_count}). "
                f"Add {min_internal - internal_count} more (target: {target})."
            )
        elif optimal_internal is not None and internal_count < optimal_internal:
            score -= 5
            suggestions.append(f"Could add more internal links ({internal_count}). Optimal is {optimal_internal}.")

        max_internal = self.guidelines['max_internal_links']
        long_form_exemption = self.guidelines[
            'long_form_internal_link_exemption_word_count'
        ]
        if max_internal is not None and internal_count > max_internal:
            article_word_count = _count_visible_words(content)
            if (
                long_form_exemption is None
                or article_word_count < long_form_exemption
            ):
                score -= 5
                if long_form_exemption is None:
                    warnings.append(
                        f"Too many internal links ({internal_count}). "
                        f"Keep standard posts to {max_internal} or fewer."
                    )
                else:
                    warnings.append(
                        f"Too many internal links ({internal_count}) for a standard blog. "
                        f"Keep standard posts to {max_internal} or fewer unless the article "
                        f"is {long_form_exemption}+ words."
                    )

        if self.guidelines['require_down_funnel_link']:
            down_funnel = _analyze_down_funnel_links(content, brand=brand)
            if down_funnel["generic"]:
                score -= 20
                anchor, url = down_funnel["generic"][0]
                critical.append(
                    "A down-funnel internal link uses generic anchor text. "
                    f"Replace '{anchor}' for {url} with destination-matched anchor text."
                )
            elif down_funnel["name_only"]:
                score -= 20
                anchor, url = down_funnel["name_only"][0]
                critical.append(
                    "A feature or solution link uses name-only anchor text. "
                    f"Replace '{anchor}' for {url} with functional anchor text that describes "
                    "the workflow, category, or outcome."
                )
            elif not down_funnel["valid"]:
                score -= 20
                if down_funnel["weak_anchor"]:
                    anchor, url = down_funnel["weak_anchor"][0]
                    critical.append(
                        "A down-funnel internal link anchor text must match the destination keyword. "
                        f"Replace '{anchor}' for {url} with a product, solution, feature, or industry keyword."
                    )
                else:
                    critical.append(
                        "Missing down-funnel internal link to /industries, /industries/..., "
                        "/solutions/..., or /features/... with matched anchor text."
                    )

        # External links
        min_external = self.guidelines['min_external_links']

        if min_external is not None and external_count < min_external:
            score -= 15
            warnings.append(
                f"Too few non-owned public research links ({external_count}). "
                f"Add authoritative resolved sources (baseline: {min_external})."
            )

        return {
            'score': max(0, score),
            'critical': critical,
            'warnings': warnings,
            'suggestions': suggestions
        }

    def _score_readability(self, content: str, structure: Dict) -> Dict[str, Any]:
        """Score readability factors"""
        score = 100
        critical = []
        warnings = []
        suggestions = []

        # Sentence length analysis
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]

        sentence_lengths = [len(s.split()) for s in sentences]
        avg_sentence_length = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0

        max_sentence = self.guidelines['max_sentence_length']
        if avg_sentence_length > max_sentence:
            score -= 10
            warnings.append(
                f"Average sentence length is {avg_sentence_length:.1f} words. "
                f"Target is under {max_sentence} words for better readability."
            )

        # Very long sentences
        long_sentences = [s for s in sentence_lengths if s > max_sentence * 1.5]
        if len(long_sentences) > len(sentences) * 0.2:  # More than 20% are too long
            score -= 10
            warnings.append(
                f"{len(long_sentences)} sentences are very long (>{max_sentence * 1.5} words). "
                "Break them into shorter sentences."
            )

        # Lists and formatting
        bullet_lists = len(re.findall(r'^\s*[-*+]\s', content, re.MULTILINE))
        numbered_lists = len(re.findall(r'^\s*\d+\.\s', content, re.MULTILINE))

        if bullet_lists + numbered_lists == 0:
            score -= 5
            suggestions.append("No lists found. Use bullet points or numbered lists to improve scannability.")

        return {
            'score': max(0, score),
            'critical': critical,
            'warnings': warnings,
            'suggestions': suggestions
        }

    def _get_grade(self, score: float) -> str:
        """Convert score to letter grade"""
        if score >= 90:
            return "A (Excellent)"
        elif score >= 80:
            return "B (Good)"
        elif score >= 70:
            return "C (Average)"
        elif score >= 60:
            return "D (Needs Work)"
        else:
            return "F (Poor)"


# Convenience function
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


def _count_visible_words(content: str) -> int:
    """Count reader-visible words in an article body for link-density policy."""
    _, body, _ = split_frontmatter(content)
    body = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", body)
    body = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", body)
    return len(re.findall(r"[A-Za-z0-9]+", body))


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


def _contains_ordered_keyword_variant(text: str, keyword: str, *, max_gap_words: int = 2) -> bool:
    """Match a keyword exactly or with a short natural-language token gap.

    Australian titles commonly place a noun or preposition before a location,
    as in ``construction estimating software options in Australia``. The
    ordered-token fallback accepts no more than two total inserted words while
    preserving every keyword token in order.
    """
    text_tokens = re.findall(r"[a-z0-9]+", text.casefold())
    keyword_tokens = re.findall(r"[a-z0-9]+", keyword.casefold())
    if not keyword_tokens:
        return False

    if _contains_token_sequence_variant(
        text_tokens,
        keyword_tokens,
        max_gap_words=max_gap_words,
    ):
        return True
    return _contains_locale_fronted_keyword_variant(
        text_tokens,
        keyword_tokens,
        max_gap_words=max_gap_words,
    )


def _contains_token_sequence_variant(
    text_tokens: List[str],
    keyword_tokens: List[str],
    *,
    max_gap_words: int,
) -> bool:
    for start, token in enumerate(text_tokens):
        if token != keyword_tokens[0]:
            continue
        position = start
        inserted = 0
        for expected in keyword_tokens[1:]:
            position += 1
            while position < len(text_tokens) and text_tokens[position] != expected:
                inserted += 1
                if inserted > max_gap_words:
                    break
                position += 1
            if inserted > max_gap_words or position >= len(text_tokens):
                break
        else:
            return True
    return False


def _contains_locale_fronted_keyword_variant(
    text_tokens: List[str],
    keyword_tokens: List[str],
    *,
    max_gap_words: int,
) -> bool:
    """Accept natural title variants where a trailing locale moves first."""
    if len(keyword_tokens) < 2 or keyword_tokens[-1] not in GEO_KEYWORD_TAIL_TOKENS:
        return False
    fronted_tokens = [keyword_tokens[-1], *keyword_tokens[:-1]]
    return _contains_token_sequence_variant(
        text_tokens,
        fronted_tokens,
        max_gap_words=max_gap_words,
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


@lru_cache(maxsize=1)
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


@lru_cache(maxsize=1)
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


def _extract_frontmatter(content: str) -> Dict[str, str]:
    metadata, _, _ = split_frontmatter(content)
    return {
        key: value
        for key, value in metadata.items()
        if isinstance(value, str)
    }


def _extract_inline_metadata(content: str) -> Dict[str, str]:
    patterns = {
        "meta_title": r"^\s*(?:\*\*)?Meta Title(?:\*\*)?:\s*(.+)$",
        "meta_description": r"^\s*(?:\*\*)?Meta Description(?:\*\*)?:\s*(.+)$",
        "primary_keyword": r"^\s*(?:\*\*)?(?:Primary|Target) Keyword(?:\*\*)?:\s*(.+)$",
    }
    metadata = {}

    for key, pattern in patterns.items():
        match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
        if match:
            metadata[key] = match.group(1).strip()

    return metadata


def _resolve_metadata(
    content: str,
    meta_title: Optional[str],
    meta_description: Optional[str],
    primary_keyword: Optional[str],
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    frontmatter = _extract_frontmatter(content)
    _, body, _ = split_frontmatter(content)
    inline = _extract_inline_metadata(body)

    resolved_title = (
        meta_title
        or inline.get("meta_title")
        or frontmatter.get("meta_title")
        or frontmatter.get("title")
    )
    resolved_description = (
        meta_description
        or inline.get("meta_description")
        or frontmatter.get("meta_description")
        or frontmatter.get("description")
    )
    resolved_keyword = (
        primary_keyword
        or inline.get("primary_keyword")
        or frontmatter.get("primary_keyword")
        or frontmatter.get("target_keyword")
    )

    return resolved_title, resolved_description, resolved_keyword


def _format_report(result: Dict[str, Any]) -> str:
    lines = [
        "=== SEO Quality Report ===",
        "",
        f"Overall Score: {result['overall_score']}/100",
        f"Grade: {result['grade']}",
        f"Publishing Ready: {result['publishing_ready']}",
        f"Release Floor: {result.get('threshold', PUBLISHING_THRESHOLD)}",
        f"Optimization Target: {result.get('target', SEO_TARGET_SCORE)}",
        f"Target Status: {result.get('target_status', 'unknown')}",
        "",
        "Category Scores:",
    ]

    for category, score in result["category_scores"].items():
        lines.append(f"  {category}: {score}/100")

    if result["critical_issues"]:
        lines.append("")
        lines.append("Critical Issues:")
        for issue in result["critical_issues"]:
            lines.append(f"  ERROR: {issue}")

    if result["warnings"]:
        lines.append("")
        lines.append("Warnings:")
        for warning in result["warnings"]:
            lines.append(f"  WARNING: {warning}")

    if result["suggestions"]:
        lines.append("")
        lines.append("Suggestions:")
        for suggestion in result["suggestions"][:5]:
            lines.append(f"  SUGGESTION: {suggestion}")

    details = result.get("details", {})
    if details:
        lines.append("")
        lines.append("Details:")
        for key, value in details.items():
            lines.append(f"  {key}: {value}")

    return "\n".join(lines)


def _sample_content() -> str:
    return """
# How to Start a Podcast

Starting a podcast is easier than you think. This complete guide shows you how to start a podcast from scratch.

## Choose Your Topic

Pick a topic you're passionate about. Your podcast topic should resonate with your target audience.

## Get Equipment

You'll need a microphone, headphones, and recording software.

## Record Your First Episode

Start recording! Don't worry about perfection on your first try.

## Publish Your Podcast

Upload to a podcast hosting platform and distribute to directories.

Ready to start your podcast? Begin today with these simple steps.
    """


def _run_sample() -> Dict[str, Any]:
    return rate_seo_quality(
        content=_sample_content(),
        meta_title="How to Start a Podcast: Complete Guide for 2024",
        meta_description="Learn how to start a podcast from scratch with this step-by-step guide. Everything you need to know about podcast equipment, recording, and publishing.",
        primary_keyword="start a podcast",
        secondary_keywords=["podcast hosting", "recording software"],
        keyword_density=1.8,
        internal_link_count=4,
        external_link_count=2,
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Rate markdown content against SEO quality rules.")
    parser.add_argument("path", nargs="?", help="Markdown file to rate. If omitted, runs the built-in sample.")
    parser.add_argument("--meta-title", help="Override or provide meta title.")
    parser.add_argument("--meta-description", help="Override or provide meta description.")
    parser.add_argument("--primary-keyword", help="Override or provide primary keyword.")
    parser.add_argument("--secondary-keywords", help="Comma-separated secondary keywords.")
    parser.add_argument(
        "--keyword-density",
        type=_non_negative_finite_float,
        help=(
            "Deprecated diagnostic percentage retained for compatibility; "
            "it does not change the quality score."
        ),
    )
    parser.add_argument(
        "--validate-urls",
        action="store_true",
        help=(
            "Resolve article URLs and fail readiness on unresolved/manual-review links. "
            "Standard posts use 2+ distinct non-owned authority sources as the baseline. "
            "Add no quota-only third source, and apply no maximum to claim-required "
            "evidence."
        ),
    )

    args = parser.parse_args(argv)

    if not args.path:
        result = _run_sample()
        print(_format_report(result))
        return 0

    file_path = Path(args.path)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        return 1

    content = file_path.read_text(encoding="utf-8")
    meta_title, meta_description, primary_keyword = _resolve_metadata(
        content,
        args.meta_title,
        args.meta_description,
        args.primary_keyword,
    )
    secondary_keywords = None
    if args.secondary_keywords:
        secondary_keywords = [
            keyword.strip()
            for keyword in args.secondary_keywords.split(",")
            if keyword.strip()
        ]

    frontmatter = _extract_frontmatter(content)
    article_brand = _resolve_article_brand(
        explicit_brand=None,
        frontmatter_brand=frontmatter.get("brand"),
        meta_title=meta_title,
    )
    internal_links, external_links = _count_markdown_links(
        content,
        brand=article_brand,
    )
    result = rate_seo_quality(
        content=content,
        meta_title=meta_title,
        meta_description=meta_description,
        primary_keyword=primary_keyword,
        secondary_keywords=secondary_keywords,
        keyword_density=args.keyword_density,
        internal_link_count=internal_links,
        external_link_count=external_links,
        validate_urls=args.validate_urls,
        brand=article_brand,
    )

    print(_format_report(result))
    return 0 if result["publishing_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
