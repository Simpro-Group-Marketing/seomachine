"""Focused seo structure quality scoring."""

from __future__ import annotations

from .seo_keyword import _contains_ordered_keyword_variant
from typing import Any
from typing import Dict
from typing import Optional
import re

class SeoStructureQualityMixin:
    def _analyze_structure(
            self,
            content: str,
            primary_keyword: Optional[str],
            h1_keyword: Optional[str] = None,
        ) -> Dict[str, Any]:
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

            title_target = h1_keyword or primary_keyword
            if title_target:
                keyword_in_h1 = _contains_ordered_keyword_variant(
                    h1_text,
                    title_target.lower(),
                )

            if primary_keyword:
                keyword_lower = primary_keyword.lower()
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


__all__ = [
    "SeoStructureQualityMixin",
]
