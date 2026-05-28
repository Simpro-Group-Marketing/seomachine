"""
SEO Quality Rater

Rates content quality against SEO best practices and guidelines.
Provides scoring (0-100) and specific recommendations for improvement.
"""

import argparse
from functools import lru_cache
import re
import sys
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, List, Optional, Any, Tuple


DOWN_FUNNEL_PATH_PREFIXES = (
    "/features/",
    "/industries/",
    "/solutions/",
)
DOWN_FUNNEL_EXACT_PATHS = {
    "/industries",
}
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
    "simprogroup.com",
    "www.simprogroup.com",
    "simpro.ai",
    "www.simpro.ai",
}


class SEOQualityRater:
    """Rates content against SEO best practices"""

    def __init__(self, guidelines: Optional[Dict[str, Any]] = None):
        """
        Initialize SEO Quality Rater

        Args:
            guidelines: Custom SEO guidelines (defaults to standard best practices)
        """
        self.guidelines = guidelines or self._default_guidelines()

    def _default_guidelines(self) -> Dict[str, Any]:
        """Default SEO guidelines based on industry standards"""
        return {
            'min_word_count': 2000,
            'optimal_word_count': 2500,
            'max_word_count': 3000,
            'primary_keyword_density_min': 1.0,
            'primary_keyword_density_max': 2.0,
            'secondary_keyword_density': 0.5,
            'min_internal_links': 3,
            'optimal_internal_links': 5,
            'min_external_links': 2,
            'optimal_external_links': 3,
            'meta_title_length_min': 50,
            'meta_title_length_max': 60,
            'meta_description_length_min': 150,
            'meta_description_length_max': 160,
            'min_h2_sections': 4,
            'optimal_h2_sections': 6,
            'h2_with_keyword_ratio': 0.33,  # At least 1/3 of H2s should have keyword
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
        external_link_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Rate content against SEO best practices

        Args:
            content: Article content
            meta_title: Meta title tag
            meta_description: Meta description tag
            primary_keyword: Target primary keyword
            secondary_keywords: Target secondary keywords
            keyword_density: Pre-calculated keyword density
            internal_link_count: Number of internal links
            external_link_count: Number of external links

        Returns:
            Dict with overall score, category scores, and recommendations
        """
        # Extract structure
        structure = self._analyze_structure(content, primary_keyword)

        # Score each category
        content_score = self._score_content(content, structure)
        keyword_score = self._score_keyword_optimization(
            content,
            structure,
            primary_keyword,
            secondary_keywords,
            keyword_density
        )
        meta_score = self._score_meta_elements(
            meta_title,
            meta_description,
            primary_keyword
        )
        structure_score = self._score_structure(structure)
        link_score = self._score_links(
            content,
            internal_link_count,
            external_link_count
        )
        readability_score = self._score_readability(content, structure)

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

        return {
            'overall_score': round(overall_score, 1),
            'grade': self._get_grade(overall_score),
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
            'publishing_ready': overall_score >= 80 and len(critical_issues) == 0,
            'details': {
                'word_count': structure['word_count'],
                'h2_count': structure['h2_count'],
                'has_h1': structure['has_h1'],
                'keyword_in_h1': structure.get('keyword_in_h1', False),
                'keyword_in_first_100': structure.get('keyword_in_first_100', False)
            }
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
            keyword_in_h1 = keyword_lower in h1_text.lower()
            first_100_words = ' '.join(content.split()[:100]).lower()
            keyword_in_first_100 = keyword_lower in first_100_words

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

        # Word count scoring
        if word_count < min_words:
            score -= 30
            critical.append(f"Content is too short ({word_count} words). Minimum is {min_words} words.")
        elif word_count < optimal_words:
            score -= 10
            warnings.append(f"Content could be longer ({word_count} words). Optimal is {optimal_words}+ words.")
        elif word_count > max_words:
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
        keyword_density: Optional[float]
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
            ratio = h2_with_kw / h2_count
            target_ratio = self.guidelines['h2_with_keyword_ratio']
            if ratio < target_ratio:
                score -= 10
                warnings.append(
                    f"Keyword appears in only {h2_with_kw}/{h2_count} H2 headings. "
                    f"Target is at least {int(target_ratio * 100)}% (2-3 H2s)"
                )

        # Keyword density
        if keyword_density is not None:
            min_density = self.guidelines['primary_keyword_density_min']
            max_density = self.guidelines['primary_keyword_density_max']

            if keyword_density < min_density:
                score -= 15
                warnings.append(
                    f"Keyword density is too low ({keyword_density}%). "
                    f"Target is {min_density}-{max_density}%"
                )
            elif keyword_density > max_density * 1.5:
                score -= 20
                critical.append(
                    f"Keyword density is too high ({keyword_density}%). "
                    f"Risk of keyword stuffing. Target is {min_density}-{max_density}%"
                )
            elif keyword_density > max_density:
                score -= 10
                warnings.append(
                    f"Keyword density is slightly high ({keyword_density}%). "
                    f"Target is {min_density}-{max_density}%"
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

        if h2_count < min_h2:
            score -= 15
            warnings.append(f"Too few H2 sections ({h2_count}). Add more main sections (target: {optimal_h2}).")
        elif h2_count < optimal_h2:
            score -= 5
            suggestions.append(f"Could use more H2 sections ({h2_count}). Optimal is {optimal_h2} sections.")

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
        external_count: Optional[int]
    ) -> Dict[str, Any]:
        """Score internal and external linking"""
        score = 100
        critical = []
        warnings = []
        suggestions = []

        # Count links if not provided
        if internal_count is None:
            internal_count, inferred_external_count = _count_markdown_links(content)
            if external_count is None:
                external_count = inferred_external_count

        if external_count is None:
            _, external_count = _count_markdown_links(content)

        # Internal links
        min_internal = self.guidelines['min_internal_links']
        optimal_internal = self.guidelines['optimal_internal_links']

        if internal_count < min_internal:
            score -= 20
            warnings.append(
                f"Too few internal links ({internal_count}). "
                f"Add {min_internal - internal_count} more (target: {optimal_internal})."
            )
        elif internal_count < optimal_internal:
            score -= 5
            suggestions.append(f"Could add more internal links ({internal_count}). Optimal is {optimal_internal}.")

        down_funnel = _analyze_down_funnel_links(content)
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
        optimal_external = self.guidelines['optimal_external_links']

        if external_count < min_external:
            score -= 15
            warnings.append(
                f"Too few external links ({external_count}). "
                f"Add authoritative sources (target: {optimal_external})."
            )
        elif external_count < optimal_external:
            score -= 5
            suggestions.append(f"Could add more external links ({external_count}). Optimal is {optimal_external}.")

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
    custom_guidelines: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Rate SEO quality of content

    Args:
        content: Article content
        meta_title: Meta title
        meta_description: Meta description
        primary_keyword: Target keyword
        secondary_keywords: Secondary keywords
        keyword_density: Pre-calculated density
        internal_link_count: Number of internal links
        external_link_count: Number of external links
        custom_guidelines: Custom SEO guidelines

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
        external_link_count
    )


def _count_markdown_links(content: str) -> Tuple[int, int]:
    """Count markdown links as internal or external for Simpro content."""
    internal_count = 0
    external_count = 0

    for _, url in _extract_markdown_links(content):
        url = url.strip()
        if not url:
            continue

        parsed = urlparse(url)
        if parsed.scheme in {"http", "https"}:
            hostname = (parsed.hostname or "").lower()
            if (
                hostname in OWNED_INTERNAL_DOMAINS
                or hostname.endswith(".simprogroup.com")
                or hostname.endswith(".simpro.ai")
            ):
                internal_count += 1
            else:
                external_count += 1
        else:
            internal_count += 1

    return internal_count, external_count


def _extract_markdown_links(content: str) -> List[Tuple[str, str]]:
    """Extract non-image markdown links from article body."""
    body = re.sub(r"\A---\s*\n.*?\n---\s*", "", content, flags=re.DOTALL)
    return [
        (anchor.strip(), url.strip())
        for anchor, url in re.findall(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)', body)
    ]


def _analyze_down_funnel_links(content: str) -> Dict[str, List[Tuple[str, str]]]:
    analysis = {
        "valid": [],
        "generic": [],
        "name_only": [],
        "weak_anchor": [],
    }

    for anchor, url in _extract_markdown_links(content):
        path = _internal_link_path(url)
        if not path or not _is_down_funnel_path(path):
            continue

        if _is_generic_anchor(anchor):
            analysis["generic"].append((anchor, url))
        elif _is_name_only_feature_or_solution_anchor(anchor, path):
            analysis["name_only"].append((anchor, url))
        elif _anchor_matches_down_funnel_target(anchor, path):
            analysis["valid"].append((anchor, url))
        else:
            analysis["weak_anchor"].append((anchor, url))

    return analysis


def _internal_link_path(url: str) -> Optional[str]:
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"}:
        hostname = (parsed.hostname or "").lower()
        if not (
            hostname in OWNED_INTERNAL_DOMAINS
            or hostname.endswith(".simprogroup.com")
            or hostname.endswith(".simpro.ai")
        ):
            return None
        return _normalize_path(parsed.path)

    if url.startswith("#") or url.startswith("mailto:") or url.startswith("tel:"):
        return None

    return _normalize_path(url)


def _normalize_path(path: str) -> str:
    cleaned = path.split("#", 1)[0].split("?", 1)[0].strip()
    if not cleaned.startswith("/"):
        cleaned = "/" + cleaned
    cleaned = re.sub(r"/+", "/", cleaned)
    return cleaned.rstrip("/") or "/"


def _is_down_funnel_path(path: str) -> bool:
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
    match = re.match(r"\A---\s*\n(.*?)\n---\s*", content, re.DOTALL)
    if not match:
        return {}

    metadata = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized_key = key.strip().lower().replace("-", "_").replace(" ", "_")
        metadata[normalized_key] = value.strip().strip('"')

    return metadata


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
    inline = _extract_inline_metadata(content)

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
    parser.add_argument("--keyword-density", type=float, help="Pre-calculated primary keyword density percentage.")

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

    internal_links, external_links = _count_markdown_links(content)
    result = rate_seo_quality(
        content=content,
        meta_title=meta_title,
        meta_description=meta_description,
        primary_keyword=primary_keyword,
        secondary_keywords=secondary_keywords,
        keyword_density=args.keyword_density,
        internal_link_count=internal_links,
        external_link_count=external_links,
    )

    print(_format_report(result))
    return 0 if result["publishing_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
