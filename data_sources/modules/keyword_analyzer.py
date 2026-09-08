"""
Keyword Analyzer

Reports keyword density, analyzes distribution, detects stuffing risk, and performs
semantic clustering to identify terminology coverage and topic clusters.
"""

import argparse
from collections import Counter
import math
import re
import sys
from typing import Any, Dict, List, Optional


def _positive_finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return parsed

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
except ImportError:
    TfidfVectorizer = None
    KMeans = None


class KeywordAnalyzer:
    """Analyzes keyword density, distribution, and clustering in content"""

    def __init__(self):
        self.stop_words = set([
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'you', 'your', 'this', 'their', 'but',
            'or', 'not', 'can', 'have', 'all', 'when', 'there', 'been', 'if',
            'more', 'so', 'about', 'what', 'which', 'who', 'would', 'could'
        ])

    def analyze(
        self,
        content: str,
        primary_keyword: str,
        secondary_keywords: Optional[List[str]] = None,
        target_density: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive keyword analysis

        Args:
            content: Article content to analyze
            primary_keyword: Main target keyword
            secondary_keywords: List of secondary keywords
            target_density: Optional target keyword density percentage. When omitted,
                density is reported without low-density prompting.

        Returns:
            Dict with density metrics, distribution map, and recommendations
        """
        if not isinstance(content, str):
            raise ValueError("content must be a string")
        if not isinstance(primary_keyword, str) or not primary_keyword.strip():
            raise ValueError("primary_keyword must be a non-empty string")
        primary_keyword = primary_keyword.strip()
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
        if (
            target_density is not None
            and (
                isinstance(target_density, bool)
                or not isinstance(target_density, (int, float))
                or not math.isfinite(target_density)
                or target_density <= 0
            )
        ):
            raise ValueError("target_density must be a finite positive number or None")

        secondary_keywords = [
            keyword.strip() for keyword in (secondary_keywords or [])
        ]

        # Clean and prepare content
        word_count = len(content.split())
        sections = self._extract_sections(content)

        # Analyze primary keyword
        primary_analysis = self._analyze_keyword(
            content,
            primary_keyword,
            word_count,
            sections,
            target_density
        )

        # Analyze secondary keywords
        secondary_analysis = []
        for keyword in secondary_keywords:
            analysis = self._analyze_keyword(
                content,
                keyword,
                word_count,
                sections,
                target_density * 0.5 if target_density is not None else None
            )
            secondary_analysis.append(analysis)

        # Detect keyword stuffing
        stuffing_risk = self._detect_keyword_stuffing(
            content,
            primary_keyword,
            (
                primary_analysis['total_occurrences'] / word_count * 100
                if word_count
                else 0.0
            )
        )

        # Perform topic clustering
        clusters = self._perform_clustering(content, sections)

        # Distribution heatmap
        heatmap = self._create_distribution_heatmap(
            primary_keyword,
            sections
        )

        # Semantic terminology suggestions. Keep the lsi_keywords key for compatibility.
        lsi_keywords = self._find_lsi_keywords(content, primary_keyword)

        return {
            'word_count': word_count,
            'primary_keyword': {
                'keyword': primary_keyword,
                **primary_analysis
            },
            'secondary_keywords': secondary_analysis,
            'keyword_stuffing': stuffing_risk,
            'topic_clusters': clusters,
            'distribution_heatmap': heatmap,
            'lsi_keywords': lsi_keywords,
            'recommendations': self._generate_recommendations(
                primary_analysis,
                secondary_analysis,
                stuffing_risk,
                target_density
            )
        }

    def _analyze_keyword(
        self,
        content: str,
        keyword: str,
        word_count: int,
        sections: List[Dict],
        target_density: Optional[float]
    ) -> Dict[str, Any]:
        """Analyze a single keyword using bounded exact-phrase matches."""
        exact_count = self._count_keyword_matches(content, keyword)
        total_count = exact_count

        # Calculate density
        density = (total_count / word_count * 100) if word_count > 0 else 0

        # Find positions
        positions = self._find_keyword_positions(content, keyword)

        # Check critical placements
        critical_placements = self._check_critical_placements(
            content,
            sections,
            keyword
        )

        # Distribution across sections
        section_distribution = self._analyze_section_distribution(
            sections,
            keyword
        )

        return {
            'keyword': keyword,
            'exact_matches': exact_count,
            'total_occurrences': total_count,
            'density': round(density, 2),
            'target_density': target_density,
            'density_status': self._get_density_status(density, target_density),
            'positions': positions,
            'critical_placements': critical_placements,
            'section_distribution': section_distribution
        }

    @staticmethod
    def _keyword_pattern(keyword: str) -> re.Pattern[str]:
        """Compile a case-insensitive phrase pattern with word boundaries."""
        escaped_phrase = r'\s+'.join(
            re.escape(part)
            for part in keyword.strip().split()
        )
        return re.compile(
            rf'(?<!\w){escaped_phrase}(?!\w)',
            re.IGNORECASE,
        )

    def _count_keyword_matches(self, text: str, keyword: str) -> int:
        """Count bounded exact-phrase matches in text."""
        return sum(1 for _ in self._keyword_pattern(keyword).finditer(text))

    def _contains_keyword(self, text: str, keyword: str) -> bool:
        """Return whether text contains a bounded exact-phrase match."""
        return self._keyword_pattern(keyword).search(text) is not None

    def _extract_sections(self, content: str) -> List[Dict]:
        """Extract sections with headers from content"""
        sections = []

        # Split by headers (H1, H2, H3)
        lines = content.split('\n')
        current_section = {'type': 'intro', 'header': '', 'content': '', 'start_pos': 0}
        current_pos = 0

        for line in lines:
            # Check for markdown headers
            h1_match = re.match(r'^#\s+(.+)$', line)
            h2_match = re.match(r'^##\s+(.+)$', line)
            h3_match = re.match(r'^###\s+(.+)$', line)

            if h1_match or h2_match or h3_match:
                # Save previous section
                if current_section['content']:
                    current_section['end_pos'] = current_pos
                    sections.append(current_section.copy())

                # Start new section
                if h1_match:
                    header = h1_match.group(1)
                    header_type = 'h1'
                elif h2_match:
                    header = h2_match.group(1)
                    header_type = 'h2'
                else:
                    header = h3_match.group(1)
                    header_type = 'h3'

                current_section = {
                    'type': header_type,
                    'header': header,
                    'content': '',
                    'start_pos': current_pos
                }
            else:
                current_section['content'] += line + '\n'

            current_pos += len(line) + 1

        # Add last section
        if current_section['content']:
            current_section['end_pos'] = current_pos
            sections.append(current_section)

        return sections

    def _find_keyword_positions(self, content: str, keyword: str) -> List[int]:
        """Find all positions where keyword appears"""
        return [match.start() for match in self._keyword_pattern(keyword).finditer(content)]

    def _check_critical_placements(
        self,
        content: str,
        sections: List[Dict],
        keyword: str
    ) -> Dict[str, bool]:
        """Check if keyword appears in critical locations"""
        # First 100 words
        first_100 = ' '.join(content.split()[:100])
        in_first_100 = self._contains_keyword(first_100, keyword)

        # Last paragraph (conclusion)
        last_para = content.split('\n\n')[-1] if '\n\n' in content else content[-500:]
        in_conclusion = self._contains_keyword(last_para, keyword)

        # H1 (first heading)
        in_h1 = False
        h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if h1_match:
            in_h1 = self._contains_keyword(h1_match.group(1), keyword)

        # H2 headings
        h2_count = 0
        h2_with_keyword = 0
        for section in sections:
            if section['type'] == 'h2':
                h2_count += 1
                if self._contains_keyword(section['header'], keyword):
                    h2_with_keyword += 1

        return {
            'in_first_100_words': in_first_100,
            'in_conclusion': in_conclusion,
            'in_h1': in_h1,
            'in_h2_headings': f"{h2_with_keyword}/{h2_count}" if h2_count > 0 else "0/0",
            'h2_keyword_ratio': (h2_with_keyword / h2_count) if h2_count > 0 else 0
        }

    def _analyze_section_distribution(
        self,
        sections: List[Dict],
        keyword: str
    ) -> List[Dict]:
        """Analyze how keyword is distributed across sections"""
        distribution = []

        for i, section in enumerate(sections):
            section_text = section['header'] + ' ' + section['content']
            count = self._count_keyword_matches(section_text, keyword)
            word_count = len(section_text.split())

            distribution.append({
                'section_index': i,
                'section_type': section['type'],
                'header': section['header'][:50],  # Truncate long headers
                'keyword_count': count,
                'word_count': word_count,
                'density': round((count / word_count * 100) if word_count > 0 else 0, 2)
            })

        return distribution

    def _get_density_status(self, actual: float, target: Optional[float]) -> str:
        """Determine if density is appropriate"""
        if target is None:
            return "reported"
        if actual < target * 0.5:
            return "too_low"
        elif actual < target * 0.8:
            return "slightly_low"
        elif actual <= target * 1.2:
            return "optimal"
        elif actual <= target * 1.5:
            return "slightly_high"
        else:
            return "too_high"

    def _detect_keyword_stuffing(
        self,
        content: str,
        keyword: str,
        density: float
    ) -> Dict[str, Any]:
        """Detect potential keyword stuffing"""
        risk_level = "none"
        warnings = []

        # High density check
        if density > 3.0:
            risk_level = "high"
            warnings.append(
                f"Keyword density {density:.2f}% is very high (over 3%)"
            )
        elif density > 2.5:
            risk_level = "medium"
            warnings.append(
                f"Keyword density {density:.2f}% is high (over 2.5%)"
            )

        # Check for keyword clustering (multiple instances in same paragraph)
        paragraphs = content.split('\n\n')
        for i, para in enumerate(paragraphs):
            count = self._count_keyword_matches(para, keyword)
            words = len(para.split())
            if words > 0:
                para_density = (count / words * 100)
                if para_density > 5:
                    risk_level = "high"
                    warnings.append(f"Paragraph {i+1} has very high keyword density ({para_density:.1f}%)")

        # Check for unnatural repetition (keyword appears in consecutive sentences)
        sentences = re.split(r'[.!?]+', content)
        consecutive = 0
        max_consecutive = 0
        for sentence in sentences:
            if self._contains_keyword(sentence, keyword):
                consecutive += 1
                max_consecutive = max(max_consecutive, consecutive)
            else:
                consecutive = 0

        if max_consecutive >= 5:
            risk_level = "high"
            warnings.append(f"Keyword appears in {max_consecutive} consecutive sentences")
        elif max_consecutive >= 3:
            if risk_level == "none":
                risk_level = "low"
            warnings.append(f"Keyword appears in {max_consecutive} consecutive sentences")

        return {
            'risk_level': risk_level,
            'warnings': warnings,
            'safe': risk_level in ["none", "low"]
        }

    def _perform_clustering(self, content: str, sections: List[Dict]) -> Dict[str, Any]:
        """Perform topic clustering to identify content themes"""
        try:
            # Prepare section texts
            section_texts = []
            for section in sections:
                text = section['header'] + ' ' + section['content']
                if len(text.split()) > 10:  # Only include substantial sections
                    section_texts.append(text)

            if len(section_texts) < 3:
                return {
                    'clusters_found': 0,
                    'note': 'Insufficient sections for clustering'
                }

            if TfidfVectorizer is None or KMeans is None:
                return self._fallback_clustering(section_texts)

            # Use TF-IDF to vectorize
            vectorizer = TfidfVectorizer(
                max_features=100,
                stop_words='english',
                ngram_range=(1, 2)
            )
            tfidf_matrix = vectorizer.fit_transform(section_texts)

            # Determine optimal number of clusters (max 5 or len/2)
            n_clusters = min(5, max(2, len(section_texts) // 2))

            # Perform k-means clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(tfidf_matrix)

            # Get top terms per cluster
            feature_names = vectorizer.get_feature_names_out()
            clusters = []

            for i in range(n_clusters):
                cluster_center = kmeans.cluster_centers_[i]
                top_indices = cluster_center.argsort()[-5:][::-1]
                top_terms = [feature_names[idx] for idx in top_indices]

                sections_in_cluster = [j for j, label in enumerate(cluster_labels) if label == i]

                clusters.append({
                    'cluster_id': i,
                    'top_terms': top_terms,
                    'section_count': len(sections_in_cluster),
                    'sections': sections_in_cluster
                })

            return {
                'clusters_found': n_clusters,
                'clusters': clusters
            }
        except Exception as e:
            return {
                'clusters_found': 0,
                'error': str(e)
            }

    def _fallback_clustering(self, section_texts: List[str]) -> Dict[str, Any]:
        """Return useful topic terms when optional sklearn clustering is unavailable."""
        all_words = []
        for text in section_texts:
            words = re.findall(r'\b[a-z]{4,}\b', text.lower())
            all_words.extend(
                word
                for word in words
                if word not in self.stop_words
            )

        top_terms = [
            word
            for word, _ in Counter(all_words).most_common(10)
        ]

        return {
            'clusters_found': 1,
            'note': 'scikit-learn unavailable; returned frequency-based topic summary',
            'clusters': [
                {
                    'cluster_id': 0,
                    'top_terms': top_terms[:5],
                    'section_count': len(section_texts),
                    'sections': list(range(len(section_texts))),
                }
            ],
        }

    def _create_distribution_heatmap(
        self,
        keyword: str,
        sections: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Create a visual representation of keyword distribution"""
        heatmap = []

        for i, section in enumerate(sections):
            section_text = section['header'] + ' ' + section['content']
            count = self._count_keyword_matches(section_text, keyword)
            word_count = len(section_text.split())

            # Calculate heat level (0-5)
            density = (count / word_count * 100) if word_count > 0 else 0
            if density == 0:
                heat = 0
            elif density < 0.5:
                heat = 1
            elif density < 1.0:
                heat = 2
            elif density < 2.0:
                heat = 3
            elif density < 3.0:
                heat = 4
            else:
                heat = 5

            heatmap.append({
                'section': section['header'][:40] or f"Section {i+1}",
                'keyword_count': count,
                'heat_level': heat,
                'density': round(density, 2)
            })

        return heatmap

    def _find_lsi_keywords(self, content: str, primary_keyword: str) -> List[str]:
        """Find semantically related terms."""
        try:
            # Extract common phrases and terms
            words = re.findall(r'\b[a-z]{4,}\b', content.lower())
            word_freq = Counter(words)

            # Remove stop words
            filtered_words = {
                word: freq for word, freq in word_freq.items()
                if word not in self.stop_words and word not in primary_keyword.lower().split()
            }

            # Get top terms
            top_terms = sorted(filtered_words.items(), key=lambda x: x[1], reverse=True)[:20]

            # Extract bigrams and trigrams
            content_lower = content.lower()
            sentences = re.split(r'[.!?]+', content_lower)

            phrases = []
            for sentence in sentences:
                words = sentence.split()
                # Bigrams
                for i in range(len(words) - 1):
                    phrase = f"{words[i]} {words[i+1]}"
                    if len(phrase) > 8 and not any(sw in phrase.split() for sw in self.stop_words):
                        phrases.append(phrase)
                # Trigrams
                for i in range(len(words) - 2):
                    phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
                    if len(phrase) > 12 and not any(sw in phrase.split() for sw in self.stop_words):
                        phrases.append(phrase)

            phrase_freq = Counter(phrases)
            top_phrases = sorted(phrase_freq.items(), key=lambda x: x[1], reverse=True)[:10]

            # Combine and return
            lsi_keywords = []
            lsi_keywords.extend([word for word, _ in top_terms[:10]])
            lsi_keywords.extend([phrase for phrase, _ in top_phrases[:5]])

            return lsi_keywords[:15]

        except Exception:
            return []

    def _generate_recommendations(
        self,
        primary_analysis: Dict,
        secondary_analysis: List[Dict],
        stuffing_risk: Dict,
        target_density: Optional[float]
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Density is diagnostic at the low end and protective at the high end.
        # Do not recommend adding repetitions to meet a density target.
        status = primary_analysis['density_status']
        if target_density is None:
            recommendations.append(
                "INFO: Keyword density is reported for context only. Evaluate critical placement, "
                "semantic variations, and stuffing risk instead of chasing an exact-match target."
            )
        elif status == "too_low":
            recommendations.append(
                f"WARNING: Primary keyword density is too low ({primary_analysis['density']}%). "
                f"Target is {target_density}%. Add {primary_analysis['keyword']} naturally in more paragraphs."
            )
        elif status == "slightly_low":
            recommendations.append(
                f"INFO: Primary keyword density is slightly low ({primary_analysis['density']}%). "
                f"Consider adding a few more mentions of '{primary_analysis['keyword']}'."
            )
        elif status == "too_high":
            recommendations.append(
                f"WARNING: Primary keyword density is too high ({primary_analysis['density']}%). "
                f"This may trigger keyword stuffing penalties. Remove some instances or replace with variations."
            )
        elif status == "slightly_high":
            recommendations.append(
                f"INFO: Primary keyword density is slightly high ({primary_analysis['density']}%). "
                f"Consider using more keyword variations or synonyms."
            )

        # Critical placements
        placements = primary_analysis['critical_placements']
        if not placements['in_first_100_words']:
            recommendations.append("WARNING: Primary keyword missing from first 100 words - add it to the introduction")

        if not placements['in_h1']:
            recommendations.append("WARNING: Primary keyword missing from H1 headline - include it in the title")

        if (
            placements['in_h2_headings'] != "0/0"
            and placements['in_h2_headings'].startswith("0/")
        ):
            recommendations.append(
                "INFO: Primary keyword is missing from H2 headings. Add it to one "
                "relevant H2 where the exact phrase is natural, then use semantic variations."
            )

        # Keyword stuffing
        if not stuffing_risk['safe']:
            recommendations.append(
                f"WARNING: KEYWORD STUFFING RISK: {stuffing_risk['risk_level'].upper()} - "
                + '; '.join(stuffing_risk['warnings'])
            )

        # Secondary keywords
        for analysis in secondary_analysis:
            if analysis['total_occurrences'] == 0:
                recommendations.append(
                    f"INFO: Secondary keyword '{analysis['keyword']}' not found in content - consider adding it"
                )

        return recommendations


# Convenience function
def analyze_keywords(
    content: str,
    primary_keyword: str,
    secondary_keywords: Optional[List[str]] = None,
    target_density: Optional[float] = None
) -> Dict[str, Any]:
    """
    Analyze keyword usage in content

    Args:
        content: Article text
        primary_keyword: Main target keyword
        secondary_keywords: List of secondary keywords
        target_density: Optional target density percentage. When omitted, density is
            reported without low-density prompting.

    Returns:
        Comprehensive keyword analysis
    """
    analyzer = KeywordAnalyzer()
    return analyzer.analyze(content, primary_keyword, secondary_keywords, target_density)


def _sample_content() -> str:
    return """
# How to Start a Podcast: Complete Guide

Starting a podcast has never been easier. In this guide, you'll learn how to start a podcast from scratch.

## Choosing Your Podcast Topic

When you start a podcast, the first step is choosing your topic. Your podcast topic should be something you're passionate about.

## Getting Podcast Equipment

To start a podcast, you need basic equipment. A good microphone is essential for podcast recording.

## Podcast Hosting Platforms

Podcast hosting is crucial. Choose a reliable podcast hosting platform for your show.
    """


def _format_report(result: Dict[str, Any]) -> str:
    lines = [
        "=== Keyword Analysis ===",
        "",
        f"Word Count: {result['word_count']}",
        "",
        f"Primary Keyword: {result['primary_keyword']['keyword']}",
        f"Density: {result['primary_keyword']['density']}%",
        f"Status: {result['primary_keyword']['density_status']}",
        "",
        "Critical Placements:",
    ]

    for key, value in result['primary_keyword']['critical_placements'].items():
        lines.append(f"  {key}: {value}")

    lines.append("")
    lines.append(f"Keyword Stuffing Risk: {result['keyword_stuffing']['risk_level']}")
    if result['keyword_stuffing']['warnings']:
        lines.append("Warnings:")
        for warning in result['keyword_stuffing']['warnings']:
            lines.append(f"  - {warning}")

    topic_clusters = result.get("topic_clusters", {})
    if topic_clusters:
        lines.append("")
        lines.append(f"Topic Clusters: {topic_clusters.get('clusters_found', 0)}")
        if topic_clusters.get("note"):
            lines.append(f"  Note: {topic_clusters['note']}")
        if topic_clusters.get("error"):
            lines.append(f"  Error: {topic_clusters['error']}")

    lines.append("")
    lines.append("Recommendations:")
    if result['recommendations']:
        for rec in result['recommendations']:
            lines.append(f"  {rec}")
    else:
        lines.append("  No keyword recommendations.")

    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze keyword distribution, terminology coverage, and stuffing risk for markdown content.")
    parser.add_argument("path", nargs="?", help="Markdown file to analyze. If omitted, runs the built-in sample.")
    parser.add_argument("--primary-keyword", help="Primary keyword to analyze.")
    parser.add_argument("--secondary-keywords", help="Comma-separated secondary keywords.")
    parser.add_argument(
        "--target-density",
        type=_positive_finite_float,
        default=None,
        help="Optional primary keyword density percentage for legacy density-audit mode.",
    )

    args = parser.parse_args(argv)

    if args.path:
        try:
            with open(args.path, "r", encoding="utf-8") as file:
                content = file.read()
        except FileNotFoundError:
            print(f"Error: File not found: {args.path}", file=sys.stderr)
            return 1
    else:
        content = _sample_content()

    primary_keyword = args.primary_keyword
    if not primary_keyword:
        primary_keyword = "start a podcast" if not args.path else None

    if not primary_keyword:
        print("Error: --primary-keyword is required when analyzing a file.", file=sys.stderr)
        return 1

    secondary_keywords = None
    if args.secondary_keywords:
        secondary_keywords = [
            keyword.strip()
            for keyword in args.secondary_keywords.split(",")
            if keyword.strip()
        ]
    elif not args.path:
        secondary_keywords = ["podcast hosting", "podcast equipment", "podcast recording"]

    result = analyze_keywords(
        content,
        primary_keyword,
        secondary_keywords,
        target_density=args.target_density,
    )

    print(_format_report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
