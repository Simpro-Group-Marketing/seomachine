"""Canonical content scorer assembled from focused serial mixins."""

from .humanity import HumanityScoringMixin
from .orchestration import ScoringOrchestrationMixin
from .quality_gates import QualityGatesMixin
from .readability import ReadabilityScoringMixin
from .reporting import ScoringReportingMixin
from .seo import SeoScoringMixin
from .specificity import SpecificityScoringMixin
from .structure import StructureScoringMixin

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

__all__ = ["ContentScorer"]
