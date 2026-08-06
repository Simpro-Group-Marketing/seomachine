"""
Content Length Comparator

Fetches top SERP results for a keyword and reports their observed content
length as context. Article targets remain caller supplied.
"""

import re
import requests
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
import statistics


class ContentLengthComparator:
    """Compares content length against top SERP competitors"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def analyze(
        self,
        keyword: str,
        observed_word_count: Optional[int] = None,
        serp_results: Optional[List[Dict[str, str]]] = None,
        fetch_content: bool = True,
        word_target: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Analyze content length compared to SERP competitors

        Args:
            keyword: Search keyword to analyze
            observed_word_count: Observed content word count
            serp_results: SERP results from DataForSEO (list of {'url', 'title', 'domain'})
            fetch_content: Whether to fetch and analyze competitor content
            word_target: Optional caller-supplied intent/evidence-complete target

        Returns:
            Dict with observed length context and statistics
        """
        if not isinstance(keyword, str) or not keyword.strip():
            raise ValueError("keyword must be a non-empty string")
        if (
            observed_word_count is not None
            and (
                not isinstance(observed_word_count, int)
                or isinstance(observed_word_count, bool)
                or observed_word_count < 0
            )
        ):
            raise ValueError("observed_word_count must be a non-negative integer or None")
        if (
            word_target is not None
            and (
                not isinstance(word_target, int)
                or isinstance(word_target, bool)
                or word_target <= 0
            )
        ):
            raise ValueError("word_target must be a positive integer or None")
        if not isinstance(fetch_content, bool):
            raise ValueError("fetch_content must be a boolean")
        if serp_results is not None:
            if not isinstance(serp_results, list):
                raise ValueError("serp_results must be a list of result dictionaries or None")
            for result in serp_results:
                if not isinstance(result, dict):
                    raise ValueError("serp_results must contain result dictionaries")
                url = result.get('url')
                if not isinstance(url, str) or not url.strip():
                    raise ValueError("serp_results must contain result dictionaries with non-empty url values")
                for optional_key in ('title', 'domain'):
                    value = result.get(optional_key)
                    if value is not None and not isinstance(value, str):
                        raise ValueError(
                            f"serp_results {optional_key} values must be strings or None"
                        )

        if not serp_results:
            return self._build_result(
                keyword=keyword,
                observed_word_count=observed_word_count,
                word_target=word_target,
                competitor_lengths=[],
                unavailable_reason='No SERP results provided',
            )

        # Analyze competitor content lengths
        competitor_lengths = []

        if fetch_content:
            for i, result in enumerate(serp_results[:10]):  # Top 10 only
                url = result.get('url')
                if url:
                    word_count = self.fetch_word_count(url)
                    if word_count:
                        competitor_lengths.append({
                            'position': i + 1,
                            'url': url,
                            'domain': result.get('domain') or '',
                            'title': (result.get('title') or '')[:100],
                            'word_count': word_count
                        })
        else:
            return self._build_result(
                keyword=keyword,
                observed_word_count=observed_word_count,
                word_target=word_target,
                competitor_lengths=[],
                unavailable_reason='Competitor content was not fetched',
            )

        if not competitor_lengths:
            return self._build_result(
                keyword=keyword,
                observed_word_count=observed_word_count,
                word_target=word_target,
                competitor_lengths=[],
                unavailable_reason='Could not fetch competitor content',
            )

        return self._build_result(
            keyword=keyword,
            observed_word_count=observed_word_count,
            word_target=word_target,
            competitor_lengths=competitor_lengths,
        )

    def _build_result(
        self,
        keyword: str,
        observed_word_count: Optional[int],
        word_target: Optional[int],
        competitor_lengths: List[Dict[str, Any]],
        unavailable_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build the clean context-only result shape for all outcomes."""
        counts = [comp['word_count'] for comp in competitor_lengths]
        stats = self._calculate_statistics(counts)

        length_context = self._build_length_context(
            stats,
            observed_word_count,
            word_target,
            unavailable_reason,
        )

        your_position = self._get_position_in_range(
            observed_word_count,
            competitor_lengths
        ) if observed_word_count is not None and competitor_lengths else None

        return {
            'keyword': keyword,
            'competitors_analyzed': len(competitor_lengths),
            'observed_word_count': observed_word_count,
            'word_target': word_target,
            'statistics': stats,
            'competitor_lengths': competitor_lengths,
            'observed_position': your_position,
            'length_context': length_context,
            'competitive_analysis': self._analyze_competition(
                observed_word_count,
                competitor_lengths,
            )
        }

    def fetch_word_count(self, url: str) -> Optional[int]:
        """Fetch and count words from a URL."""
        return self.fetch_content_context(url).get('word_count')

    def fetch_content_context(self, url: str) -> Dict[str, Any]:
        """Fetch observed word count and H2 headings from one page request."""
        context: Dict[str, Any] = {
            'word_count': None,
            'h2_headings': [],
        }
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove script, style, nav, footer, header elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                element.decompose()

            # Try to find main content area
            main_content = None
            for selector in ['article', 'main', '[role="main"]', '.content', '#content', '.post', '.entry-content']:
                main_content = soup.select_one(selector)
                if main_content:
                    break

            # If no main content found, use body
            if not main_content:
                main_content = soup.find('body')

            if main_content:
                text = main_content.get_text(separator=' ', strip=True)
                words = re.findall(r'\b[a-zA-Z]{2,}\b', text)
                headings = []
                for heading in main_content.find_all('h2'):
                    heading_text = re.sub(
                        r'\s+',
                        ' ',
                        heading.get_text(separator=' ', strip=True),
                    ).strip()
                    if heading_text and heading_text not in headings:
                        headings.append(heading_text)
                context['word_count'] = len(words)
                context['h2_headings'] = headings

        except Exception:
            pass

        return context

    def _calculate_statistics(self, counts: List[int]) -> Dict[str, Any]:
        """Calculate statistical measures"""
        if not counts:
            return {}

        return {
            'min': min(counts),
            'max': max(counts),
            'mean': round(statistics.mean(counts)),
            'median': round(statistics.median(counts)),
            'mode': round(statistics.mode(counts)) if len(counts) > 1 else counts[0],
            'std_dev': round(statistics.stdev(counts)) if len(counts) > 1 else 0,
            'percentile_25': round(statistics.quantiles(counts, n=4)[0]) if len(counts) > 3 else min(counts),
            'percentile_75': round(statistics.quantiles(counts, n=4)[2]) if len(counts) > 3 else max(counts)
        }

    def _build_length_context(
        self,
        stats: Dict[str, Any],
        observed_word_count: Optional[int],
        word_target: Optional[int],
        unavailable_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Describe observed length without deriving a target from competitors."""
        difference = None
        if observed_word_count is not None and word_target is not None:
            difference = observed_word_count - word_target

        if word_target is None:
            target_source = "unresolved"
            if unavailable_reason:
                message = (
                    f"{unavailable_reason}. Word target is unresolved until Reader Contract "
                    "planning identifies the intent, payoff, and required evidence."
                )
            else:
                message = (
                    "Competitor word counts are context only. Word target is unresolved until "
                    "Reader Contract planning identifies the intent, payoff, and required evidence."
                )
        else:
            target_source = "caller_supplied"
            if unavailable_reason:
                message = (
                    f"{unavailable_reason}. Evaluate completeness against the caller-supplied "
                    "target, Reader Contract, and available evidence without padding."
                )
            else:
                message = (
                    "Competitor word counts are context only. Evaluate completeness against the "
                    "caller-supplied target, Reader Contract, and available evidence without padding."
                )

        return {
            'status': 'reported',
            'target_source': target_source,
            'difference_from_target': difference,
            'message': message,
        }

    def _get_position_in_range(
        self,
        observed_word_count: int,
        competitors: List[Dict[str, Any]]
    ) -> str:
        """Determine where your content falls in the competitor range"""
        counts = [c['word_count'] for c in competitors]
        counts.sort()

        if observed_word_count < counts[0]:
            return f"Below all competitors (shortest is {counts[0]})"
        elif observed_word_count > counts[-1]:
            return f"Above all competitors (longest is {counts[-1]})"
        else:
            # Find position
            for i, count in enumerate(counts, 1):
                if observed_word_count <= count:
                    if i == 1:
                        return f"At shortest competitor length ({count})"
                    return f"Between position {i - 1} and {i} competitors"

        return "Within competitive range"

    def _analyze_competition(
        self,
        observed_word_count: Optional[int],
        competitors: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Provide competitive analysis"""
        analysis = {
            'total_competitors': len(competitors),
            'length_distribution': self._categorize_lengths(competitors),
            'comparison': None,
        }

        if observed_word_count is not None and competitors:
            # How many competitors you're longer than
            shorter_than_you = len([
                c for c in competitors
                if c['word_count'] < observed_word_count
            ])
            longer_than_you = len([
                c for c in competitors
                if c['word_count'] > observed_word_count
            ])

            analysis['comparison'] = {
                'shorter_than_you': shorter_than_you,
                'longer_than_you': longer_than_you,
                'percentile': round((shorter_than_you / len(competitors)) * 100)
            }

        return analysis

    def _categorize_lengths(self, competitors: List[Dict[str, Any]]) -> Dict[str, int]:
        """Categorize competitor content by length ranges"""
        categories = {
            'under_1000': 0,
            '1000_1500': 0,
            '1500_2000': 0,
            '2000_2500': 0,
            '2500_3000': 0,
            '3000_plus': 0
        }

        for comp in competitors:
            count = comp['word_count']
            if count < 1000:
                categories['under_1000'] += 1
            elif count < 1500:
                categories['1000_1500'] += 1
            elif count < 2000:
                categories['1500_2000'] += 1
            elif count < 2500:
                categories['2000_2500'] += 1
            elif count < 3000:
                categories['2500_3000'] += 1
            else:
                categories['3000_plus'] += 1

        return categories


# Convenience function
def compare_content_length(
    keyword: str,
    observed_word_count: Optional[int] = None,
    serp_results: Optional[List[Dict[str, str]]] = None,
    fetch_content: bool = True,
    word_target: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Compare content length against SERP competitors

    Args:
        keyword: Target keyword
        observed_word_count: Observed content word count
        serp_results: SERP results from DataForSEO
        fetch_content: Whether to fetch competitor content
        word_target: Optional caller-supplied intent/evidence-complete target

    Returns:
        Observed content length comparison and caller-target context
    """
    comparator = ContentLengthComparator()
    return comparator.analyze(
        keyword,
        observed_word_count,
        serp_results,
        fetch_content,
        word_target,
    )
