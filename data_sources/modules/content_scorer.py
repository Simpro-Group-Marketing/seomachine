"""
Content Scorer

Multi-dimensional content quality scoring system that evaluates:
- Humanity/Voice (30%): Human tone, personality, conversational devices
- Specificity (25%): Concrete examples vs vague generalizations
- Structure Balance (20%): Prose-to-list ratio (target 50-75%)
- SEO Compliance (15%): Keyword placement, meta, structure
- Readability (10%): Flesch score, sentence rhythm, paragraph length

Readability now includes:
- Flesch Reading Ease score (target 60-70)
- Sentence rhythm scoring (penalizes monotonous sections)
- Paragraph length check (flags paragraphs >4 sentences)

Composite score must be >= 85 to pass the general content quality threshold.
SEO quality score must clear the 90 release floor with no critical issues to
pass the SEO gate. The honest optimization target is 95.
AEO/GEO score must be >= 90 to pass the generative-answer publishing gate.
"""

from collections.abc import Mapping, Sequence
from typing import Dict, List, Optional, Any

# Import existing modules
try:
    from .aeo_geo_rater import rate_aeo_geo
    from .ai_copy_linter import lint_content
    from .customer_proof_diversity_guard import check_content as check_customer_proof_diversity
    from .frontmatter import split_frontmatter
    from .metric_proof_pack_guard import check_content as check_metric_proof_pack
    from .proof_sidecar import load_sidecar_content, resolve_sidecar_path
    from .readability_scorer import ReadabilityScorer
    from .readiness_gate_context import trusted_readiness_findings
    from .review_story_identity_guard import check_content as check_review_story_identity
    from .seo_quality_rater import PUBLISHING_THRESHOLD as SEO_PUBLISHING_THRESHOLD
    from .seo_quality_rater import SEO_TARGET_SCORE
    from .seo_quality_rater import SEOQualityRater
    from .source_support_guard import check_content as check_source_support
    from .url_validator import validate_content_urls
except ImportError:
    # For standalone testing
    from aeo_geo_rater import rate_aeo_geo
    from ai_copy_linter import lint_content
    from customer_proof_diversity_guard import check_content as check_customer_proof_diversity
    from frontmatter import split_frontmatter
    from metric_proof_pack_guard import check_content as check_metric_proof_pack
    from proof_sidecar import load_sidecar_content, resolve_sidecar_path
    from readability_scorer import ReadabilityScorer
    from readiness_gate_context import trusted_readiness_findings
    from review_story_identity_guard import check_content as check_review_story_identity
    from seo_quality_rater import PUBLISHING_THRESHOLD as SEO_PUBLISHING_THRESHOLD
    from seo_quality_rater import SEO_TARGET_SCORE
    from seo_quality_rater import SEOQualityRater
    from source_support_guard import check_content as check_source_support
    from url_validator import validate_content_urls


def _copy_prevalidated_findings(
    findings_by_gate: Optional[Mapping[str, Sequence[Mapping[str, Any]]]],
    gate_name: str,
) -> Optional[List[Dict[str, Any]]]:
    """Return an isolated copy when readiness already ran a named gate."""
    if findings_by_gate is None or gate_name not in findings_by_gate:
        return None

    raw_findings = findings_by_gate[gate_name]
    if isinstance(raw_findings, (str, bytes)) or not isinstance(
        raw_findings,
        Sequence,
    ):
        raise TypeError(f"prevalidated findings for {gate_name!r} must be a sequence")

    copied: List[Dict[str, Any]] = []
    for index, finding in enumerate(raw_findings):
        if not isinstance(finding, Mapping):
            raise TypeError(
                f"prevalidated finding {gate_name}[{index}] must be a mapping"
            )
        copied.append(dict(finding))
    return copied


try:
    from .content_scoring.orchestration import ScoringOrchestrationMixin
    from .content_scoring.quality_gates import QualityGatesMixin
    from .content_scoring.humanity import HumanityScoringMixin
    from .content_scoring.specificity import SpecificityScoringMixin
    from .content_scoring.structure import StructureScoringMixin
    from .content_scoring.seo import SeoScoringMixin
    from .content_scoring.readability import ReadabilityScoringMixin
    from .content_scoring.reporting import ScoringReportingMixin
except ImportError:  # pragma: no cover - direct script compatibility.
    from content_scoring.orchestration import ScoringOrchestrationMixin
    from content_scoring.quality_gates import QualityGatesMixin
    from content_scoring.humanity import HumanityScoringMixin
    from content_scoring.specificity import SpecificityScoringMixin
    from content_scoring.structure import StructureScoringMixin
    from content_scoring.seo import SeoScoringMixin
    from content_scoring.readability import ReadabilityScoringMixin
    from content_scoring.reporting import ScoringReportingMixin

class ContentScorer(
        ScoringOrchestrationMixin,
        QualityGatesMixin,
        HumanityScoringMixin,
        SpecificityScoringMixin,
        StructureScoringMixin,
        SeoScoringMixin,
        ReadabilityScoringMixin,
        ScoringReportingMixin,
):
    """Multi-dimensional content quality scorer"""

    # Dimension weights (must sum to 1.0)
    WEIGHTS = {
        'humanity': 0.30,
        'specificity': 0.25,
        'structure_balance': 0.20,
        'seo': 0.15,
        'readability': 0.10
    }

    # Threshold for passing the general content quality gate.
    PASS_THRESHOLD = 85

    # Vague words that reduce specificity
    VAGUE_WORDS = [
        r'\bmany\b',
        r'\bsome\b',
        r'\bvarious\b',
        r'\bnumerous\b',
        r'\bseveral\b',
        r'\boften\b',
        r'\bsometimes\b',
        r'\busually\b',
        r'\bgenerally\b',
        r'\btypically\b',
        r'\bsignificant(?:ly)?\b',
        r'\bsubstantial(?:ly)?\b',
        r'\bconsiderable\b',
        r'\bgreat(?:ly)?\b',
        r'\bvery\b',
        r'\breally\b',
        r'\bquite\b',
        r'\brather\b',
        r'\brelatively\b',
        r'\brecently\b',
        r'\bcurrently\b',
        r'\beffective(?:ly)?\b',
        r'\bimportant\b',
        r'\bessential\b',
        r'\bcritical\b',
        r'\bkey\b',
        r'\bcrucial\b',
    ]

    # Proof-sensitive specifics. These are reported as needing proof context;
    # they do not automatically improve the score.
    PROOF_SENSITIVE_SPECIFICITY_PATTERNS = [
        r'(?<!\w)\d+(?:\.\d+)?%(?!\w)',  # Percentages
        r'\$[\d,]+(?:\.\d{2})?\b',  # Dollar amounts
        r'\b\d{4}\b',  # Years
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}',  # Dates
        r'\b\d+(?:,\d{3})*\s*(?:downloads?|listeners?|subscribers?|episodes?|users?|customers?|businesses|companies|teams?|contractors?|trades?)\b',  # Counts
        r'(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:said|says|explained|noted|mentioned)',  # Quotes with names
        r'\"[^\"]{10,}\"',  # Quoted text
        r'\b[A-Z][a-z]+\s+at\s+[A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*){0,3}\b',  # Named person at business
        r'\b[A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*){1,3}\s+(?:Inc|LLC|Ltd|Group|Mechanical|Electrical|Plumbing|Services|Contractors|Construction)\b',  # Named business
        r'\b(?:saved|increased|reduced|improved|helped|avoided|prevented|cut|grew|won|switched|delivered)\b[^.]{0,120}\b(?:time|money|costs?|revenue|profit|invoices?|customers?|businesses|outcomes?)\b',  # Outcome claims
    ]

    # Concrete workflow detail that can improve usefulness without inventing
    # claims, metrics, names, or quotes.
    WORKFLOW_SPECIFICITY_PATTERNS = [
        r'\b(?:dispatcher|dispatchers|technician|technicians|manager|managers|office teams?|field teams?|customer|customers)\b',
        r'\b(?:workflow|handoff|job card|invoice|invoicing|quote|quoting|schedule|scheduling|parts|inventory|customer access|job status)\b',
        r'\b(?:assign|prioritize|route|update|approve|review|rekey|sync|close|escalate|track|handoff)\w*\b',
        r'\b(?:before|after|when|if)\s+(?:the|a|an|teams?|dispatchers?|technicians?|customers?)\b',
    ]

    # Conversational devices (boost humanity score)
    CONVERSATIONAL_PATTERNS = [
        r'\([^)]{5,50}\)',  # Parenthetical asides
        r'\?(?:\s|$)',  # Questions
        r'\bdon\'t\b',  # Contractions
        r'\bcan\'t\b',
        r'\bwon\'t\b',
        r'\byou\'re\b',
        r'\byou\'ve\b',
        r'\bit\'s\b',
        r'\bthat\'s\b',
        r'\bhere\'s\b',
        r'\blet\'s\b',
        r'\bI\'ve\b',
        r'\bI\'m\b',
        r'\bwe\'ve\b',
        r'\bwe\'re\b',
        r'(?:^|\.\s+)(?:Look|Here\'s the thing|The truth is|Sound familiar|Trust me)',  # Casual openers
    ]


__all__ = [
    "ContentScorer",
    "ReadabilityScorer",
    "SEOQualityRater",
    "SEO_PUBLISHING_THRESHOLD",
    "SEO_TARGET_SCORE",
    "rate_aeo_geo",
    "lint_content",
    "check_customer_proof_diversity",
    "split_frontmatter",
    "check_metric_proof_pack",
    "load_sidecar_content",
    "resolve_sidecar_path",
    "trusted_readiness_findings",
    "check_review_story_identity",
    "check_source_support",
    "validate_content_urls",
    "main",
]


def main():
    """CLI entry point for testing"""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Score markdown content quality.")
    parser.add_argument("file_path", help="Path to the draft or rewrite markdown file.")
    parser.add_argument(
        "--validate-urls",
        action="store_true",
        help="Resolve article URLs and fail the gate on unresolved/manual-review links.",
    )
    parser.add_argument(
        "--validate-source-support",
        action="store_true",
        help="Verify approved evidence snippets support high-risk claims.",
    )
    parser.add_argument(
        "--proof-sidecar",
        help="Optional validation sidecar containing proof maps and proof packs.",
    )
    args = parser.parse_args()

    try:
        with open(args.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {args.file_path}")
        sys.exit(1)

    scorer = ContentScorer()
    result = scorer.score(
        content,
        validate_urls=args.validate_urls,
        validate_source_support=args.validate_source_support,
        source_path=args.file_path,
        proof_sidecar=args.proof_sidecar,
    )

    print(scorer.format_report(result))
    sys.exit(0 if result["passed"] else 1)


if __name__ == '__main__':
    main()
