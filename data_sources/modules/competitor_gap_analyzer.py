"""
Competitor Gap Analyzer

Analyzes competitor content to identify knowledge gaps, thin sections,
unsupported claims, missing perspectives, and outdated information.
Builds a context blueprint for Reader Contract planning.

Used by the /article command during SERP analysis phase.
"""

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, replace
from enum import Enum
from datetime import datetime


class GapType(Enum):
    """Types of content gaps found in competitor articles."""
    THIN_SECTION = "thin_section"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    MISSING_PERSPECTIVE = "missing_perspective"
    OUTDATED_INFO = "outdated_info"
    STRUCTURAL_GAP = "structural_gap"


class GapPriority(Enum):
    """Priority levels for addressing gaps."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ContentGap:
    """Represents a single gap found in competitor content."""
    gap_type: GapType
    description: str
    location: str  # H2 heading or section name where gap was found
    competitor_url: str
    priority: GapPriority
    opportunity: str  # How your content can address this gap
    reader_critical: bool = False
    evidence_available: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.gap_type, GapType):
            raise ValueError("gap_type must be a GapType value")
        if not isinstance(self.priority, GapPriority):
            raise ValueError("priority must be a GapPriority value")
        for field_name in (
            "description",
            "location",
            "competitor_url",
            "opportunity",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        for field_name in ("reader_critical", "evidence_available"):
            if not isinstance(getattr(self, field_name), bool):
                raise ValueError(f"{field_name} must be a boolean")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.gap_type.value,
            "description": self.description,
            "location": self.location,
            "url": self.competitor_url,
            "priority": self.priority.value,
            "opportunity": self.opportunity,
            "reader_critical": self.reader_critical,
            "evidence_available": self.evidence_available,
        }


@dataclass
class CompetitorAnalysis:
    """Analysis results for a single competitor article."""
    url: str
    title: str
    word_count: int
    structure: List[str]  # H2 headings
    strengths: List[str]
    gaps: List[ContentGap]
    outdated_items: List[str]

    def __post_init__(self) -> None:
        if not isinstance(self.url, str) or not self.url.strip():
            raise ValueError("url must be a non-empty string")
        if not isinstance(self.title, str):
            raise ValueError("title must be a string")
        if (
            isinstance(self.word_count, bool)
            or not isinstance(self.word_count, int)
            or self.word_count < 0
        ):
            raise ValueError("word_count must be a non-negative integer")
        for field_name in ("structure", "strengths", "outdated_items"):
            values = getattr(self, field_name)
            if not isinstance(values, list) or any(
                not isinstance(item, str) or not item.strip() for item in values
            ):
                raise ValueError(f"{field_name} must be a list of non-empty strings")
        if not isinstance(self.gaps, list) or any(
            not isinstance(gap, ContentGap) for gap in self.gaps
        ):
            raise ValueError("gaps must be a list of ContentGap values")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "word_count": self.word_count,
            "structure": self.structure,
            "strengths": self.strengths,
            "gaps": [g.to_dict() for g in self.gaps],
            "outdated_items": self.outdated_items
        }


@dataclass
class GapBlueprint:
    """Observed competitor context for Reader Contract planning."""
    must_fill_gaps: List[ContentGap]  # Compatibility field: qualified must-fill gaps
    differentiation_opportunities: List[str]  # Unique angles
    data_needed: List[str]  # Specific data to gather
    outdated_to_update: List[str]  # Old information to evaluate for sourced replacement
    structure_to_match: List[str]  # Compatibility field: recurring H2s to evaluate
    qualification_required_gaps: List[ContentGap] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "must_fill_gaps": [g.to_dict() for g in self.must_fill_gaps],
            "differentiation_opportunities": self.differentiation_opportunities,
            "data_needed": self.data_needed,
            "outdated_to_update": self.outdated_to_update,
            "structure_to_match": self.structure_to_match,
            "qualification_required_gaps": [
                gap.to_dict() for gap in self.qualification_required_gaps
            ],
        }


class CompetitorGapAnalyzer:
    """
    Analyzes competitor content to identify knowledge gaps.

    This class provides structure and patterns for the /article command
    to use when analyzing competitor content. The actual analysis is
    performed by the AI during command execution.
    """

    # Patterns indicating vague/unsupported claims
    UNSUPPORTED_PATTERNS = [
        r'\bmany\s+(?:podcasters?|people|users|creators?)\b',
        r'\bmost\s+(?:podcasters?|people|experts?|creators?)\b',
        r'\bstudies\s+show\b(?!\s*[\[\(])',  # No citation following
        r'\bresearch\s+(?:indicates?|shows?|suggests?)\b(?!\s*[\[\(])',
        r'\bsignificant(?:ly)?\s+(?:increase|improvement|growth|impact)\b',
        r'\bsubstantial\s+(?:results?|benefits?|returns?|improvement)\b',
        r'\bexperts?\s+(?:say|agree|recommend)\b(?!\s*[\[\(])',
        r'\baccording\s+to\s+(?:experts?|studies)\b(?!\s*[\[\(])',
    ]

    # Year patterns identify references that may require a freshness review.
    YEAR_PATTERN = r'\b(19\d{2}|20\d{2})\b'

    def analyze_content(
        self,
        content: str,
        url: str,
        title: str = ""
    ) -> CompetitorAnalysis:
        """
        Analyze a single competitor's content for gaps.

        Args:
            content: The full text content of the competitor article
            url: URL of the competitor article
            title: Title of the article (optional)

        Returns:
            CompetitorAnalysis with identified gaps and structure
        """
        if not isinstance(content, str):
            raise ValueError("content must be a string")
        if not isinstance(url, str) or not url.strip():
            raise ValueError("url must be a non-empty string")
        if not isinstance(title, str):
            raise ValueError("title must be a string")
        sections = self._extract_sections(content)
        gaps = []
        outdated = []

        # Analyze each section
        for section in sections:
            # Check for thin sections
            thin_gaps = self._find_thin_sections(section, url)
            gaps.extend(thin_gaps)

            # Check for unsupported claims
            claim_gaps = self._find_unsupported_claims(section, url)
            gaps.extend(claim_gaps)

            # Check for outdated info
            outdated_items = self._find_outdated_info(section['content'])
            outdated.extend(outdated_items)

        return CompetitorAnalysis(
            url=url,
            title=title,
            word_count=len(content.split()),
            structure=[s['header'] for s in sections if s['level'] == 2],
            strengths=self._identify_strengths(sections),
            gaps=gaps,
            outdated_items=outdated
        )

    def create_blueprint(
        self,
        analyses: List[CompetitorAnalysis],
        reader_critical_gaps: Optional[List[str]] = None,
        evidence_supported_gaps: Optional[List[str]] = None,
    ) -> GapBlueprint:
        """
        Create a context blueprint from multiple competitor analyses.

        Args:
            analyses: List of CompetitorAnalysis from analyzing competitors

        Returns:
            GapBlueprint with prioritized opportunities
        """
        if not isinstance(analyses, list) or any(
            not isinstance(analysis, CompetitorAnalysis) for analysis in analyses
        ):
            raise ValueError("analyses must be a list of CompetitorAnalysis values")

        for name, values in (
            ("reader_critical_gaps", reader_critical_gaps),
            ("evidence_supported_gaps", evidence_supported_gaps),
        ):
            if values is not None and (
                not isinstance(values, list)
                or any(not isinstance(item, str) or not item.strip() for item in values)
            ):
                raise ValueError(f"{name} must be a list of non-empty strings")

        reader_critical = {
            item.strip().casefold() for item in (reader_critical_gaps or [])
        }
        evidence_supported = {
            item.strip().casefold() for item in (evidence_supported_gaps or [])
        }

        # Count recurrence across distinct competitor analyses, not duplicate rows.
        gap_counts: Dict[str, Dict[str, Any]] = {}
        for analysis in analyses:
            for gap in analysis.gaps:
                key = f"{gap.gap_type.value}:{gap.description.strip().casefold()}"
                if key not in gap_counts:
                    gap_counts[key] = {"gaps": [], "competitor_urls": set()}
                gap_counts[key]["gaps"].append(gap)
                gap_counts[key]["competitor_urls"].add(analysis.url)

        known_gap_descriptions = {
            group["gaps"][0].description.strip().casefold()
            for group in gap_counts.values()
        }
        for name, supplied in (
            ("reader_critical_gaps", reader_critical),
            ("evidence_supported_gaps", evidence_supported),
        ):
            unknown = supplied - known_gap_descriptions
            if unknown:
                raise ValueError(
                    f"{name} contains an unknown gap description: {sorted(unknown)[0]}"
                )

        # A gap is must-fill only when recurrence, reader value, and evidence align.
        must_fill = []
        unqualified_recurring_gaps = []
        for group in gap_counts.values():
            representative = group["gaps"][0]
            description_key = representative.description.strip().casefold()
            is_recurring = len(group["competitor_urls"]) >= 3
            reader_qualification_known = (
                reader_critical_gaps is not None
                or any(gap.reader_critical for gap in group["gaps"])
            )
            evidence_qualification_known = (
                evidence_supported_gaps is not None
                or any(gap.evidence_available for gap in group["gaps"])
            )
            if (
                is_recurring
                and (not reader_qualification_known or not evidence_qualification_known)
            ):
                unqualified_recurring_gaps.append(representative)
                continue
            is_reader_critical = (
                any(gap.reader_critical for gap in group["gaps"])
                or description_key in reader_critical
            )
            has_evidence = (
                any(gap.evidence_available for gap in group["gaps"])
                or description_key in evidence_supported
            )
            if (
                is_recurring
                and is_reader_critical
                and has_evidence
            ):
                must_fill.append(
                    replace(
                        representative,
                        reader_critical=True,
                        evidence_available=True,
                    )
                )

        # Collect all outdated items
        all_outdated = []
        for analysis in analyses:
            all_outdated.extend(analysis.outdated_items)

        # Find common structure (appears in 3+ competitors)
        structure_urls: Dict[str, set] = {}
        structure_labels: Dict[str, str] = {}
        for analysis in analyses:
            for heading in analysis.structure:
                normalized = heading.lower().strip()
                if not normalized:
                    continue
                structure_urls.setdefault(normalized, set()).add(analysis.url)
                structure_labels.setdefault(normalized, heading.strip())

        common_structure = sorted(
            [
                structure_labels[heading]
                for heading, urls in structure_urls.items()
                if len(urls) >= 3
            ],
            key=str.casefold,
        )

        return GapBlueprint(
            must_fill_gaps=must_fill,
            differentiation_opportunities=[],  # Filled during analysis
            data_needed=[],  # Filled during analysis
            outdated_to_update=sorted(set(all_outdated)),
            structure_to_match=common_structure,
            qualification_required_gaps=unqualified_recurring_gaps,
        )

    def _extract_sections(self, content: str) -> List[Dict]:
        """Extract H2/H3 sections with their content."""
        sections = []
        lines = content.split('\n')
        current_section = {'header': 'Introduction', 'content': '', 'level': 1}

        for line in lines:
            h2_match = re.match(r'^##\s+(.+)$', line)
            h3_match = re.match(r'^###\s+(.+)$', line)

            if h2_match or h3_match:
                # Save previous section
                if current_section['content'].strip():
                    sections.append(current_section.copy())

                header = h2_match.group(1) if h2_match else h3_match.group(1)
                level = 2 if h2_match else 3
                current_section = {'header': header, 'content': '', 'level': level}
            else:
                current_section['content'] += line + '\n'

        # Save final section
        if current_section['content'].strip():
            sections.append(current_section)

        return sections

    def _find_thin_sections(
        self,
        section: Dict,
        url: str
    ) -> List[ContentGap]:
        """Identify sections that lack a reader-payoff, evidence, or task gap."""
        gaps = []
        content = section['content'].strip().lower()

        if section['level'] == 2 and re.search(r'\b(todo|placeholder|tbd)\b', content):
            gaps.append(ContentGap(
                gap_type=GapType.THIN_SECTION,
                description=f"Section '{section['header']}' has unresolved placeholder content",
                location=section['header'],
                competitor_url=url,
                priority=GapPriority.HIGH,
                opportunity=(
                    f"Replace placeholder content in '{section['header']}' with the "
                    "specific reader payoff, required evidence, or task guidance this "
                    "section must provide"
                )
            ))

        return gaps

    def _find_unsupported_claims(
        self,
        section: Dict,
        url: str
    ) -> List[ContentGap]:
        """Find claims without data or citations."""
        gaps = []
        content = section['content']

        for pattern in self.UNSUPPORTED_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                # Only add one gap per pattern per section
                gaps.append(ContentGap(
                    gap_type=GapType.UNSUPPORTED_CLAIM,
                    description=f"Vague claim without data in '{section['header']}'",
                    location=section['header'],
                    competitor_url=url,
                    priority=GapPriority.MEDIUM,
                    opportunity=(
                        "Replace vague claims with approved proof or concrete workflow "
                        "detail; do not invent percentages, dollar amounts, statistics, "
                        "names, quotes, or outcomes"
                    )
                ))
                break  # One gap per section is enough

        return gaps

    def _find_outdated_info(self, content: str) -> List[str]:
        """Identify date-sensitive references that require a freshness review."""
        review_candidates = []
        current_year = datetime.now().year

        # A year is an observation, not proof that the surrounding claim is outdated.
        old_years = re.findall(self.YEAR_PATTERN, content)
        for year in set(old_years):
            if int(year) < current_year - 1:  # More than 1 year old
                review_candidates.append(
                    f"Reference to {year} - evaluate whether current evidence is needed"
                )

        return review_candidates

    def _identify_strengths(self, sections: List[Dict]) -> List[str]:
        """Identify what the competitor does well."""
        strengths = []

        for section in sections:
            # Check for specific data patterns
            if re.search(
                r'\$\d+|\b\d+(?:\.\d+)?\s*(?:%|hours?|days?|users?|jobs?|teams?|businesses?)\b',
                section['content'],
                re.IGNORECASE,
            ):
                strengths.append(f"Contains numeric detail in '{section['header']}'")

        return sorted(set(strengths))[:5]  # Limit to top 5


def format_gap_report(
    keyword: str,
    analyses: List[CompetitorAnalysis],
    blueprint: GapBlueprint
) -> str:
    """
    Format the analysis results as a markdown report.

    This is used to generate the serp-analysis-[topic]-[date].md file.
    """
    date = datetime.now().strftime("%Y-%m-%d")

    report = f"""# SERP Analysis: {keyword}

**Date**: {date}
**Keyword**: {keyword}
**Competitors Analyzed**: {len(analyses)}

---

## Top Ranking Articles

"""

    for i, analysis in enumerate(analyses, 1):
        report += f"""### {i}. {analysis.title}
- **URL**: {analysis.url}
- **Word Count**: ~{analysis.word_count}
- **Structure**: {', '.join(analysis.structure[:5])}
- **Strengths**: {', '.join(analysis.strengths[:3]) if analysis.strengths else 'None identified'}
- **Gaps Found**: {len(analysis.gaps)}
- **Outdated Items**: {len(analysis.outdated_items)}

"""

    report += """---

## SERP Structure Context

Common ranking sections to evaluate against the Reader Contract:
"""
    for heading in blueprint.structure_to_match:
        report += f"- {heading}\n"

    report += """
---

## Competitor Gap Blueprint

### MUST-FILL GAPS

These gaps are recurring, reader-critical, and evidence-supported. Include each
one by default or document a Reader Contract exception.
"""
    if blueprint.must_fill_gaps:
        for gap in blueprint.must_fill_gaps:
            report += f"- **{gap.description}**\n  - Opportunity: {gap.opportunity}\n"
    else:
        report += "- No qualified must-fill gaps identified\n"

    report += """
### QUALIFICATION REQUIRED

These recurring gap candidates are not must-fill until reader importance and evidence
availability are resolved. Qualify each against the Reader Contract before inclusion.
"""
    if blueprint.qualification_required_gaps:
        for gap in blueprint.qualification_required_gaps:
            report += f"- **{gap.description}**\n  - Decision: {gap.opportunity}\n"
    else:
        report += "- No recurring gap candidates awaiting qualification\n"

    report += """
### DATE-SENSITIVE REFERENCES TO EVALUATE
"""
    if blueprint.outdated_to_update:
        for item in blueprint.outdated_to_update:
            report += f"- {item}\n"
    else:
        report += "- No date-sensitive references identified\n"

    return report


if __name__ == "__main__":
    # Example usage
    print("Competitor Gap Analyzer")
    print("=" * 50)
    print("This module is used by the /article command")
    print("to analyze competitor content and identify gaps.")
    print()
    print("Gap Types:")
    for gap_type in GapType:
        print(f"  - {gap_type.value}")
