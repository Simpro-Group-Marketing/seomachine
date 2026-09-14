"""Focused seo keyword scoring."""

from __future__ import annotations

from .seo_constants import FENCED_CODE_BLOCK_RE
from .seo_constants import GEO_KEYWORD_TAIL_TOKENS
from .seo_constants import HTML_COMMENT_RE
from .seo_constants import MARKDOWN_IMAGE_RE
from .seo_metadata import _has_meta_title_brand_suffix
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
import re

class SeoKeywordMixin:
    def _score_keyword_optimization(
            self,
            content: str,
            structure: Dict,
            primary_keyword: Optional[str],
            secondary_keywords: Optional[List[str]],
            keyword_density: Optional[float] = None,
            h1_keyword: Optional[str] = None,
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
                heading_target = h1_keyword or primary_keyword
                critical.append(f"Primary topic '{heading_target}' missing from H1 heading")

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
            if keyword_density is not None and keyword_density > 3.0:
                score -= 20
                critical.append(
                    f"Keyword density is too high ({keyword_density:.1f}%). "
                    "Reduce exact-match repetition and use natural related terms."
                )
            missing_keywords = _missing_secondary_keywords(content, secondary_keywords)
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


def _missing_secondary_keywords(
    content: str,
    secondary_keywords: Optional[List[str]],
) -> List[str]:
    if not secondary_keywords:
        return []
    content_lower = content.lower()
    return [keyword for keyword in secondary_keywords if keyword.lower() not in content_lower]

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


__all__ = [
    "SeoKeywordMixin",
    "_contains_ordered_keyword_variant",
    "_contains_token_sequence_variant",
    "_contains_locale_fronted_keyword_variant",
]
