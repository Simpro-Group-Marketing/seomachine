"""Focused seo config scoring."""

from __future__ import annotations

from typing import Any
from typing import Dict
from typing import Optional
import math

class SeoConfigMixin:
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


__all__ = [
    "SeoConfigMixin",
]
