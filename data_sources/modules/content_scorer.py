"""
Content Scorer

Multi-dimensional content quality scoring system that evaluates:
- Humanity/Voice (30%): Human tone, personality, conversational devices
- Specificity (25%): Concrete examples vs vague generalizations
- Structure Balance (20%): Prose-to-list ratio (target 50-75%)
- SEO Compliance (15%): Keyword density, meta, structure
- Readability (10%): Flesch score, sentence rhythm, paragraph length

Readability now includes:
- Flesch Reading Ease score (target 60-70)
- Sentence rhythm scoring (penalizes monotonous sections)
- Paragraph length check (flags paragraphs >4 sentences)

Composite score must be >= 85 to pass the general content quality threshold.
AEO/GEO score must be >= 90 to pass the generative-answer publishing gate.
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# Import existing modules
try:
    from .aeo_geo_rater import rate_aeo_geo
    from .ai_copy_linter import lint_content
    from .customer_proof_diversity_guard import check_content as check_customer_proof_diversity
    from .metric_proof_pack_guard import check_content as check_metric_proof_pack
    from .proof_sidecar import load_sidecar_content
    from .readability_scorer import ReadabilityScorer
    from .review_story_identity_guard import check_content as check_review_story_identity
    from .seo_quality_rater import SEOQualityRater
    from .source_support_guard import check_content as check_source_support
    from .url_validator import validate_content_urls
except ImportError:
    # For standalone testing
    from aeo_geo_rater import rate_aeo_geo
    from ai_copy_linter import lint_content
    from customer_proof_diversity_guard import check_content as check_customer_proof_diversity
    from metric_proof_pack_guard import check_content as check_metric_proof_pack
    from proof_sidecar import load_sidecar_content
    from readability_scorer import ReadabilityScorer
    from review_story_identity_guard import check_content as check_review_story_identity
    from seo_quality_rater import SEOQualityRater
    from source_support_guard import check_content as check_source_support
    from url_validator import validate_content_urls


class ContentScorer:
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

    # Specificity indicators (boost specificity score)
    SPECIFICITY_PATTERNS = [
        r'\b\d{1,3}%\b',  # Percentages
        r'\$[\d,]+(?:\.\d{2})?\b',  # Dollar amounts
        r'\b\d{4}\b',  # Years
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}',  # Dates
        r'\b\d+(?:,\d{3})*\s*(?:downloads?|listeners?|subscribers?|episodes?|users?|customers?)\b',  # Counts
        r'(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:said|says|explained|noted|mentioned)',  # Quotes with names
        r'\"[^\"]{10,}\"',  # Quoted text
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

    def __init__(self):
        self.readability_scorer = ReadabilityScorer()
        self.seo_rater = SEOQualityRater()

    def score(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        validate_urls: bool = False,
        validate_source_support: bool = False,
        source_path: Optional[str] = None,
        proof_sidecar: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Score content across all dimensions

        Args:
            content: Full article content (markdown)
            metadata: Optional dict with meta_title, meta_description,
                     primary_keyword, secondary_keywords
            validate_urls: Resolve URLs and block the quality gate on failures
            validate_source_support: Verify approved evidence snippets support
                high-risk claims and block the quality gate on failures
            source_path: Optional draft path used to resolve relative PAA/FAQ
                provenance artifact paths

        Returns:
            Dict with composite_score, passed, dimensions, and priority_fixes
        """
        metadata = metadata or {}

        # Clean content for analysis
        clean_content = self._clean_for_analysis(content)

        # Score each dimension
        humanity = self._score_humanity(clean_content, lint_source=content)
        specificity = self._score_specificity(clean_content)
        structure = self._score_structure_balance(content)
        seo = self._score_seo(content, metadata)
        readability = self._score_readability(clean_content)

        # Calculate composite score
        composite = (
            humanity['score'] * self.WEIGHTS['humanity'] +
            specificity['score'] * self.WEIGHTS['specificity'] +
            structure['score'] * self.WEIGHTS['structure_balance'] +
            seo['score'] * self.WEIGHTS['seo'] +
            readability['score'] * self.WEIGHTS['readability']
        )
        composite = round(composite, 1)

        content_quality_passed = composite >= self.PASS_THRESHOLD
        gate_context = self._run_quality_gates(
            content,
            metadata,
            validate_urls=validate_urls,
            validate_source_support=validate_source_support,
            source_path=source_path,
            proof_sidecar=proof_sidecar,
        )

        # Determine if passed
        passed = self._quality_gates_passed(
            content_quality_passed,
            gate_context,
        )

        # Collect all issues and prioritize
        priority_fixes = self._build_priority_fixes(
            [
                ('humanity', humanity),
                ('specificity', specificity),
                ('structure_balance', structure),
                ('seo', seo),
                ('readability', readability)
            ],
            gate_context,
        )
        quality_gates = self._build_quality_gates(
            composite,
            content_quality_passed,
            gate_context,
            include_source_support=validate_source_support,
        )

        return {
            'composite_score': composite,
            'content_quality_score': composite,
            'passed': passed,
            'threshold': self.PASS_THRESHOLD,
            'aeo_geo': gate_context['aeo_geo'],
            'quality_gates': quality_gates,
            'dimensions': {
                'humanity': {
                    'score': humanity['score'],
                    'weight': self.WEIGHTS['humanity'],
                    'issues': humanity.get('issues', []),
                    'details': humanity.get('details', {})
                },
                'specificity': {
                    'score': specificity['score'],
                    'weight': self.WEIGHTS['specificity'],
                    'issues': specificity.get('issues', []),
                    'details': specificity.get('details', {})
                },
                'structure_balance': {
                    'score': structure['score'],
                    'weight': self.WEIGHTS['structure_balance'],
                    'prose_ratio': structure.get('prose_ratio', 0),
                    'issues': structure.get('issues', []),
                    'details': structure.get('details', {})
                },
                'seo': {
                    'score': seo['score'],
                    'weight': self.WEIGHTS['seo'],
                    'issues': seo.get('issues', []),
                    'details': seo.get('details', {})
                },
                'readability': {
                    'score': readability['score'],
                    'weight': self.WEIGHTS['readability'],
                    'flesch': readability.get('flesch', 0),
                    'issues': readability.get('issues', []),
                    'details': readability.get('details', {})
                }
            },
            'priority_fixes': priority_fixes
        }

    def _run_quality_gates(
        self,
        content: str,
        metadata: Dict[str, Any],
        *,
        validate_urls: bool,
        validate_source_support: bool,
        source_path: Optional[str],
        proof_sidecar: Optional[str],
    ) -> Dict[str, Any]:
        """Run proof-aware quality gates and keep scorer orchestration local."""
        proof_sidecar_content = load_sidecar_content(source_path, proof_sidecar)
        aeo_geo = rate_aeo_geo(
            content,
            metadata,
            source_path=source_path,
            proof_sidecar_content=proof_sidecar_content,
        )
        faq_proof_check = aeo_geo.get('checks', {}).get('faq_proof', {})
        paa_provenance_check = aeo_geo.get('checks', {}).get('paa_provenance', {})
        metric_proof_pack_findings = check_metric_proof_pack(
            content,
            source_path=source_path,
            proof_content=proof_sidecar_content,
        )
        customer_proof_findings = check_customer_proof_diversity(
            content,
            source_path=source_path,
            proof_content=proof_sidecar_content,
        )
        review_story_findings = check_review_story_identity(
            content,
            source_path=source_path,
            proof_content=proof_sidecar_content,
        )

        source_support_findings = []
        if validate_source_support:
            source_support_findings = check_source_support(
                content,
                base_path=Path(source_path).parent if source_path else None,
                proof_content=proof_sidecar_content,
            )

        # Run source support before URL validation so proof fetches are not
        # starved by a burst of URL-resolution requests to the same domain.
        url_validation = None
        if validate_urls:
            url_validation = validate_content_urls(content)

        return {
            'aeo_geo': aeo_geo,
            'aeo_geo_passed': bool(aeo_geo.get('passed', False)),
            'faq_proof_check': faq_proof_check,
            'faq_proof_passed': bool(faq_proof_check.get('passed', True)),
            'paa_provenance_check': paa_provenance_check,
            'paa_provenance_passed': bool(paa_provenance_check.get('passed', True)),
            'metric_proof_pack_findings': metric_proof_pack_findings,
            'metric_proof_pack_passed': not metric_proof_pack_findings,
            'customer_proof_findings': customer_proof_findings,
            'customer_proof_passed': not self._has_error_finding(customer_proof_findings),
            'review_story_findings': review_story_findings,
            'review_story_passed': not self._has_error_finding(review_story_findings),
            'url_validation': url_validation,
            'url_validation_passed': True if url_validation is None else url_validation.passed,
            'source_support_findings': source_support_findings,
            'source_support_passed': not source_support_findings,
        }

    def _quality_gates_passed(
        self,
        content_quality_passed: bool,
        gate_context: Dict[str, Any],
    ) -> bool:
        return (
            content_quality_passed
            and gate_context['aeo_geo_passed']
            and gate_context['faq_proof_passed']
            and gate_context['paa_provenance_passed']
            and gate_context['metric_proof_pack_passed']
            and gate_context['customer_proof_passed']
            and gate_context['review_story_passed']
            and gate_context['url_validation_passed']
            and gate_context['source_support_passed']
        )

    def _build_priority_fixes(
        self,
        dimensions: List[Tuple[str, Dict[str, Any]]],
        gate_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        all_issues = []
        for dim_name, dim_data in dimensions:
            for issue in dim_data.get('issues', []):
                issue['dimension'] = dim_name
                issue['dimension_score'] = dim_data['score']
                all_issues.append(issue)

        # Sort by impact (dimension weight * score deficit)
        for issue in all_issues:
            weight = self.WEIGHTS[issue['dimension']]
            deficit = 100 - issue['dimension_score']
            issue['impact'] = weight * deficit

        priority_fixes = sorted(all_issues, key=lambda x: -x['impact'])[:5]
        return self._add_gate_priority_fixes(priority_fixes, gate_context)

    def _add_gate_priority_fixes(
        self,
        priority_fixes: List[Dict[str, Any]],
        gate_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        faq_proof_check = gate_context['faq_proof_check']
        if not gate_context['faq_proof_passed']:
            faq_findings = faq_proof_check.get('details', {}).get('findings', [])
            faq_questions = ", ".join(
                str(finding.get('question', 'unknown FAQ')) for finding in faq_findings[:3]
            )
            priority_fixes.insert(0, {
                'issue': 'FAQ proof blockers detected',
                'fix': (
                    'Add public proof links inside unsupported FAQ answers or add '
                    f'question-specific Source Map / FAQ Proof Map entries: {faq_questions}'
                ),
                'severity': 'high',
                'dimension': 'faq_proof',
                'dimension_score': 0,
                'impact': 100
            })
            priority_fixes = priority_fixes[:5]

        paa_provenance_check = gate_context['paa_provenance_check']
        if not gate_context['paa_provenance_passed']:
            paa_findings = paa_provenance_check.get('details', {}).get('findings', [])
            paa_questions = ", ".join(
                str(finding.get('question') or finding.get('match') or 'unknown FAQ')
                for finding in paa_findings[:3]
            )
            priority_fixes.insert(0, {
                'issue': 'PAA provenance blockers detected',
                'fix': (
                    'Add a PAA/FAQ Provenance block with an allowed source label, '
                    f'a real artifact path, and exact selected questions: {paa_questions}'
                ),
                'severity': 'high',
                'dimension': 'paa_provenance',
                'dimension_score': 0,
                'impact': 100
            })
            priority_fixes = priority_fixes[:5]

        metric_proof_pack_findings = gate_context['metric_proof_pack_findings']
        if not gate_context['metric_proof_pack_passed']:
            metric_lines = ", ".join(
                f"line {finding.get('line', '?')}"
                for finding in metric_proof_pack_findings[:3]
            )
            priority_fixes.insert(0, {
                'issue': 'Metric Proof Pack blockers detected',
                'fix': (
                    'Add a Metric Proof Pack with a search log and approved metrics '
                    f'with source-visible Evidence, or document not applicable: {metric_lines}'
                ),
                'severity': 'high',
                'dimension': 'metric_proof_pack',
                'dimension_score': 0,
                'impact': 100
            })
            priority_fixes = priority_fixes[:5]

        customer_proof_findings = gate_context['customer_proof_findings']
        if not gate_context['customer_proof_passed']:
            customer_lines = ", ".join(
                f"line {finding.get('line', '?')}"
                for finding in customer_proof_findings[:3]
            )
            priority_fixes.insert(0, {
                'issue': 'Customer proof diversity blockers detected',
                'fix': (
                    'Add Quote Matrix, Reference, Customer Story, or review-site search evidence, '
                    f'or document a Reuse reason for repeated customer proof: {customer_lines}'
                ),
                'severity': 'high',
                'dimension': 'customer_proof_diversity',
                'dimension_score': 0,
                'impact': 100
            })
            priority_fixes = priority_fixes[:5]

        review_story_findings = gate_context['review_story_findings']
        if not gate_context['review_story_passed']:
            review_story_lines = ", ".join(
                f"line {finding.get('line', '?')}"
                for finding in review_story_findings[:3]
            )
            priority_fixes.insert(0, {
                'issue': 'Review story identity blockers detected',
                'fix': (
                    'Add a Review Story Selection with a real person or business identity, '
                    'public review URL, and same-paragraph article link; or remove review-derived copy: '
                    f'{review_story_lines}'
                ),
                'severity': 'high',
                'dimension': 'review_story_identity',
                'dimension_score': 0,
                'impact': 100
            })
            priority_fixes = priority_fixes[:5]

        url_validation = gate_context['url_validation']
        if url_validation is not None and not url_validation.passed:
            blocker_urls = ", ".join(
                result.url for result in url_validation.blockers[:3]
            )
            priority_fixes.insert(0, {
                'issue': 'URL validation blockers detected',
                'fix': f'Replace or verify unresolved/manual-review URLs before optimize or publish: {blocker_urls}',
                'severity': 'high',
                'dimension': 'url_validation',
                'dimension_score': 0,
                'impact': 100
            })
            priority_fixes = priority_fixes[:5]

        source_support_findings = gate_context['source_support_findings']
        if not gate_context['source_support_passed']:
            blocker_lines = ", ".join(
                f"line {finding.get('line', '?')}" for finding in source_support_findings[:3]
            )
            priority_fixes.insert(0, {
                'issue': 'Source support blockers detected',
                'fix': (
                    'Add approved proof rows with source-visible Evidence snippets, '
                    f'or remove unsupported claims: {blocker_lines}'
                ),
                'severity': 'high',
                'dimension': 'source_support',
                'dimension_score': 0,
                'impact': 100
            })
            priority_fixes = priority_fixes[:5]

        return priority_fixes

    def _build_quality_gates(
        self,
        composite: float,
        content_quality_passed: bool,
        gate_context: Dict[str, Any],
        *,
        include_source_support: bool,
    ) -> Dict[str, Any]:
        aeo_geo = gate_context['aeo_geo']
        faq_proof_check = gate_context['faq_proof_check']
        paa_provenance_check = gate_context['paa_provenance_check']
        metric_proof_pack_findings = gate_context['metric_proof_pack_findings']
        customer_proof_findings = gate_context['customer_proof_findings']
        review_story_findings = gate_context['review_story_findings']
        quality_gates = {
            'content_quality': {
                'score': composite,
                'threshold': self.PASS_THRESHOLD,
                'passed': content_quality_passed
            },
            'aeo_geo': {
                'score': aeo_geo.get('score', 0),
                'threshold': aeo_geo.get('threshold', 90),
                'passed': gate_context['aeo_geo_passed']
            },
            'faq_proof': {
                'finding_count': faq_proof_check.get('details', {}).get('finding_count', 0),
                'passed': gate_context['faq_proof_passed']
            },
            'paa_provenance': {
                'finding_count': paa_provenance_check.get('details', {}).get('finding_count', 0),
                'passed': gate_context['paa_provenance_passed']
            },
            'metric_proof_pack': {
                'finding_count': len(metric_proof_pack_findings),
                'passed': gate_context['metric_proof_pack_passed'],
                'findings': metric_proof_pack_findings
            },
            'customer_proof_diversity': {
                'finding_count': len(customer_proof_findings),
                'passed': gate_context['customer_proof_passed'],
                'findings': customer_proof_findings
            },
            'review_story_identity': {
                'finding_count': len(review_story_findings),
                'passed': gate_context['review_story_passed'],
                'findings': review_story_findings
            }
        }
        url_validation = gate_context['url_validation']
        if url_validation is not None:
            quality_gates['url_validation'] = {
                'total': url_validation.total,
                'resolved': url_validation.resolved_count,
                'unresolved': url_validation.unresolved_count,
                'manual_review': url_validation.manual_review_count,
                'passed': gate_context['url_validation_passed']
            }
        if include_source_support:
            source_support_findings = gate_context['source_support_findings']
            quality_gates['source_support'] = {
                'finding_count': len(source_support_findings),
                'passed': gate_context['source_support_passed'],
                'findings': source_support_findings
            }
        return quality_gates

    @staticmethod
    def _has_error_finding(findings: List[Dict[str, Any]]) -> bool:
        return any(finding.get("severity") == "error" for finding in findings)

    def _clean_for_analysis(self, content: str) -> str:
        """Remove markdown formatting for text analysis"""
        text = content

        # Remove frontmatter/metadata block
        text = re.sub(r'^\*\*[^*]+\*\*:\s*.+$', '', text, flags=re.MULTILINE)

        # Remove horizontal rules
        text = re.sub(r'^---+\s*$', '', text, flags=re.MULTILINE)

        # Remove code blocks
        text = re.sub(r'```[^`]*```', '', text)

        # Remove links but keep text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

        # Remove bold/italic markers
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)

        # Remove headers but keep text
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)

        return text.strip()

    def _score_humanity(self, content: str, lint_source: Optional[str] = None) -> Dict[str, Any]:
        """Score content for human voice and personality"""
        issues = []
        details = {}

        word_count = len(content.split())

        # Use the shared deterministic AI copy linter so scoring and lint gates
        # do not drift into separate phrase lists.
        copy_lint_findings = lint_content(lint_source or content)
        copy_lint_errors = [
            finding for finding in copy_lint_findings
            if finding["severity"] == "error"
        ]
        copy_lint_warnings = [
            finding for finding in copy_lint_findings
            if finding["severity"] == "warning"
        ]
        passive_findings = [
            finding for finding in copy_lint_findings
            if finding["rule_id"] == "passive_voice"
        ]

        ai_density = (len(copy_lint_errors) / max(word_count, 1)) * 1000
        warning_density = (len(copy_lint_warnings) / max(word_count, 1)) * 1000
        passive_ratio = len(passive_findings) / max(word_count / 100, 1)

        details['ai_phrases_per_1000'] = round(ai_density, 1)
        details['ai_phrases_found'] = [
            str(finding["match"]) for finding in copy_lint_errors[:5]
        ]
        details['ai_copy_lint_errors'] = len(copy_lint_errors)
        details['ai_copy_lint_warnings'] = len(copy_lint_warnings)
        details['ai_copy_lint_findings'] = [
            {
                "rule_id": finding["rule_id"],
                "severity": finding["severity"],
                "line": finding["line"],
                "match": finding["match"],
            }
            for finding in copy_lint_findings[:10]
        ]

        # Count conversational devices
        conversational_count = 0
        for pattern in self.CONVERSATIONAL_PATTERNS:
            conversational_count += len(re.findall(pattern, content, re.IGNORECASE))

        conv_density = (conversational_count / max(word_count, 1)) * 1000
        details['conversational_per_1000'] = round(conv_density, 1)

        details['passive_voice_ratio'] = round(passive_ratio, 2)

        # Count contractions
        contractions = len(re.findall(r"'(?:t|s|re|ve|ll|d|m)\b", content))
        contraction_density = (contractions / max(word_count, 1)) * 100
        details['contractions_per_100'] = round(contraction_density, 1)

        # Calculate score
        score = 100

        # Penalize blocking AI copy lint errors (up to -35)
        if copy_lint_errors:
            penalty = min(35, max(10, ai_density * 3))
            score -= penalty
            issues.append({
                'issue': f'AI copy lint errors detected ({len(copy_lint_errors)} instances)',
                'fix': 'Remove or rephrase: ' + ", ".join(
                    str(finding["match"]) for finding in copy_lint_errors[:3]
                ),
                'severity': 'high'
            })

        # Penalize warning clusters (up to -15)
        if warning_density > 8:
            penalty = min(15, (warning_density - 8) * 1.5)
            score -= penalty
            issues.append({
                'issue': f'AI copy lint warnings detected ({len(copy_lint_warnings)} instances)',
                'fix': 'Review linter warnings for passive voice, filler, vague language, and modal verbs',
                'severity': 'medium'
            })

        # Penalize high passive voice (up to -15)
        if passive_ratio > 2:
            penalty = min(15, (passive_ratio - 2) * 5)
            score -= penalty
            issues.append({
                'issue': 'High passive voice usage',
                'fix': 'Convert passive sentences to active voice',
                'severity': 'medium'
            })

        # Reward conversational devices (up to +15)
        if conv_density > 3:
            bonus = min(15, (conv_density - 3) * 2)
            score = min(100, score + bonus)

        # Penalize lack of contractions (up to -10)
        if contraction_density < 1:
            score -= 10
            issues.append({
                'issue': 'Lacks contractions (sounds formal)',
                'fix': "Use contractions like don't, can't, you're, it's",
                'severity': 'low'
            })

        return {
            'score': max(0, min(100, round(score))),
            'issues': issues,
            'details': details
        }

    def _score_specificity(self, content: str) -> Dict[str, Any]:
        """Score content for concrete examples vs vague generalizations"""
        issues = []
        details = {}

        content_lower = content.lower()
        word_count = len(content.split())

        # Count vague words
        vague_count = 0
        vague_found = []
        for pattern in self.VAGUE_WORDS:
            matches = re.findall(pattern, content_lower)
            vague_count += len(matches)
            if matches and len(vague_found) < 5:
                vague_found.extend(matches[:2])

        vague_density = (vague_count / max(word_count, 1)) * 1000
        details['vague_words_per_1000'] = round(vague_density, 1)
        details['vague_words_found'] = list(set(vague_found))[:5]

        # Count specificity indicators
        specific_count = 0
        for pattern in self.SPECIFICITY_PATTERNS:
            specific_count += len(re.findall(pattern, content))

        specific_density = (specific_count / max(word_count, 1)) * 1000
        details['specifics_per_1000'] = round(specific_density, 1)

        # Count numbers and data points
        numbers = re.findall(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', content)
        number_density = (len(numbers) / max(word_count, 1)) * 1000
        details['numbers_per_1000'] = round(number_density, 1)

        # Calculate score
        score = 70  # Start at baseline

        # Penalize vague words (up to -25)
        if vague_density > 15:
            penalty = min(25, (vague_density - 15) * 1.5)
            score -= penalty
            issues.append({
                'issue': f'Too many vague words ({vague_count} instances)',
                'fix': f'Replace vague words with specifics: {", ".join(vague_found[:3])}',
                'severity': 'high' if vague_density > 25 else 'medium'
            })

        # Reward specificity indicators (up to +30)
        if specific_density > 2:
            bonus = min(30, specific_density * 5)
            score += bonus

        # Penalize lack of numbers/data (up to -15)
        if number_density < 3:
            penalty = min(15, (3 - number_density) * 5)
            score -= penalty
            issues.append({
                'issue': 'Lacks specific numbers and data',
                'fix': 'Add percentages, dollar amounts, dates, or counts',
                'severity': 'medium'
            })

        return {
            'score': max(0, min(100, round(score))),
            'issues': issues,
            'details': details
        }

    def _score_structure_balance(self, content: str) -> Dict[str, Any]:
        """Score content for prose-to-structure ratio"""
        issues = []
        details = {}

        # Remove metadata block
        content = re.sub(r'^\*\*[^*]+\*\*:\s*.+$', '', content, flags=re.MULTILINE)
        content = re.sub(r'^---+\s*$', '', content, flags=re.MULTILINE)

        lines = content.split('\n')

        list_chars = 0
        table_chars = 0
        header_chars = 0
        total_chars = 0

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            char_count = len(line_stripped)
            total_chars += char_count

            # List items
            if re.match(r'^[-*+]\s', line_stripped) or re.match(r'^\d+\.\s', line_stripped):
                list_chars += char_count
            # Table rows
            elif '|' in line_stripped:
                table_chars += char_count
            # Headers
            elif re.match(r'^#+\s', line_stripped):
                header_chars += char_count

        structured_chars = list_chars + table_chars
        prose_chars = total_chars - structured_chars - header_chars

        prose_ratio = prose_chars / max(total_chars - header_chars, 1)
        list_ratio = list_chars / max(total_chars, 1)
        table_ratio = table_chars / max(total_chars, 1)

        details['prose_ratio'] = round(prose_ratio, 2)
        details['list_ratio'] = round(list_ratio, 2)
        details['table_ratio'] = round(table_ratio, 2)
        details['prose_chars'] = prose_chars
        details['list_chars'] = list_chars
        details['table_chars'] = table_chars

        # Calculate score
        # Target: 50-75% prose (sweet spot for readable, scannable content)
        if 0.50 <= prose_ratio <= 0.75:
            score = 100
        elif prose_ratio < 0.50:
            # Too structured - needs more narrative
            deficit = 0.50 - prose_ratio
            score = max(0, 100 - (deficit * 150))
            issues.append({
                'issue': f'Too much structure ({round(prose_ratio * 100)}% prose, target 50-75%)',
                'fix': 'Convert some bullet lists or tables to prose paragraphs',
                'severity': 'high' if prose_ratio < 0.35 else 'medium'
            })
        else:
            # Too prose-heavy - needs more structure for scannability
            excess = prose_ratio - 0.75
            score = max(0, 100 - (excess * 100))
            issues.append({
                'issue': f'Too much prose ({round(prose_ratio * 100)}% prose, target 50-75%)',
                'fix': 'Add tables for comparisons, lists for features, or visual breaks',
                'severity': 'medium' if prose_ratio < 0.90 else 'high'
            })

        return {
            'score': round(score),
            'prose_ratio': round(prose_ratio, 2),
            'issues': issues,
            'details': details
        }

    def _score_seo(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Score content for SEO compliance"""
        issues = []
        details = {}
        frontmatter = self._extract_frontmatter_metadata(content)

        meta_title = metadata.get('meta_title', '') or frontmatter.get('meta_title', '') or frontmatter.get('title', '')
        meta_description = metadata.get('meta_description', '') or frontmatter.get('meta_description', '') or frontmatter.get('description', '')
        primary_keyword = metadata.get('primary_keyword', '') or frontmatter.get('primary_keyword', '') or frontmatter.get('target_keyword', '')

        # Extract from content if not provided
        if not meta_title:
            match = re.search(r'\*\*Meta Title\*\*:\s*(.+)', content)
            if match:
                meta_title = match.group(1).strip()
            else:
                match = re.search(r'^\s*Meta Title:\s*(.+)', content, re.MULTILINE)
                if match:
                    meta_title = match.group(1).strip()

        if not meta_description:
            match = re.search(r'\*\*Meta Description\*\*:\s*(.+)', content)
            if match:
                meta_description = match.group(1).strip()
            else:
                match = re.search(r'^\s*Meta Description:\s*(.+)', content, re.MULTILINE)
                if match:
                    meta_description = match.group(1).strip()

        if not primary_keyword:
            match = re.search(r'\*\*(?:Target|Primary) Keyword\*\*:\s*(.+)', content)
            if match:
                primary_keyword = match.group(1).strip()
            else:
                match = re.search(r'^\s*Primary Keyword:\s*(.+)', content, re.MULTILINE)
                if match:
                    primary_keyword = match.group(1).strip()

        details['meta_title'] = meta_title
        details['meta_title_length'] = len(meta_title)
        details['meta_description'] = meta_description[:100] + '...' if len(meta_description) > 100 else meta_description
        details['meta_description_length'] = len(meta_description)
        details['primary_keyword'] = primary_keyword

        score = 100

        # Check meta title length (50-60)
        if not meta_title:
            score -= 15
            issues.append({
                'issue': 'Missing meta title',
                'fix': 'Add a meta title (50-60 characters)',
                'severity': 'high'
            })
        elif len(meta_title) < 50:
            score -= 5
            issues.append({
                'issue': f'Meta title too short ({len(meta_title)} chars)',
                'fix': 'Expand meta title to 50-60 characters',
                'severity': 'low'
            })
        elif len(meta_title) > 60:
            score -= 5
            issues.append({
                'issue': f'Meta title too long ({len(meta_title)} chars)',
                'fix': 'Shorten meta title to 50-60 characters',
                'severity': 'low'
            })

        # Check meta description length (150-160)
        if not meta_description:
            score -= 15
            issues.append({
                'issue': 'Missing meta description',
                'fix': 'Add a meta description (150-160 characters)',
                'severity': 'high'
            })
        elif len(meta_description) < 150:
            score -= 5
        elif len(meta_description) > 160:
            score -= 5

        # Check keyword in H1
        h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if h1_match:
            h1 = h1_match.group(1).lower()
            details['h1'] = h1_match.group(1)
            if primary_keyword and primary_keyword.lower() not in h1:
                score -= 10
                issues.append({
                    'issue': 'Primary keyword not in H1',
                    'fix': f'Include "{primary_keyword}" in the H1 headline',
                    'severity': 'medium'
                })
        else:
            score -= 10
            issues.append({
                'issue': 'Missing H1 headline',
                'fix': 'Add an H1 headline with primary keyword',
                'severity': 'high'
            })

        # Check keyword in first 100 words
        clean_content = self._clean_for_analysis(content)
        first_100 = ' '.join(clean_content.split()[:100]).lower()
        if primary_keyword and primary_keyword.lower() not in first_100:
            score -= 10
            issues.append({
                'issue': 'Primary keyword not in first 100 words',
                'fix': f'Include "{primary_keyword}" in the introduction',
                'severity': 'medium'
            })

        # Word count
        word_count = len(clean_content.split())
        details['word_count'] = word_count
        if word_count < 2000:
            score -= 15
            issues.append({
                'issue': f'Content too short ({word_count} words)',
                'fix': 'Expand to at least 2,000 words',
                'severity': 'high'
            })

        return {
            'score': max(0, min(100, round(score))),
            'issues': issues,
            'details': details
        }

    def _extract_frontmatter_metadata(self, content: str) -> Dict[str, str]:
        """Extract simple scalar metadata from YAML-style frontmatter."""
        match = re.match(r'\A---\s*\n(.*?)\n---\s*', content, re.DOTALL)
        if not match:
            return {}

        values: Dict[str, str] = {}
        for line in match.group(1).splitlines():
            if ':' not in line:
                continue
            key, value = line.split(':', 1)
            normalized_key = key.strip().lower().replace('-', '_').replace(' ', '_')
            values[normalized_key] = value.strip().strip('"').strip("'")
        return values

    def _score_readability(self, content: str) -> Dict[str, Any]:
        """Score content for readability, rhythm, and paragraph length"""
        issues = []
        details = {}

        # Use existing readability scorer
        try:
            analysis = self.readability_scorer.analyze(content)
            flesch = analysis.get('readability_metrics', {}).get('flesch_reading_ease', 50)
            grade = analysis.get('reading_level', 12)
        except Exception:
            # Fallback if module fails
            flesch = 60
            grade = 10

        details['flesch_reading_ease'] = flesch
        details['grade_level'] = grade

        # Target: Flesch 60-70 (fairly easy), Grade 8-10
        score = 100

        if flesch < 50:
            penalty = min(30, (50 - flesch) * 1.5)
            score -= penalty
            issues.append({
                'issue': f'Content too difficult (Flesch: {flesch})',
                'fix': 'Simplify sentences, use shorter words',
                'severity': 'high' if flesch < 40 else 'medium'
            })
        elif flesch < 60:
            score -= 10
            issues.append({
                'issue': f'Content slightly difficult (Flesch: {flesch})',
                'fix': 'Simplify some complex sentences',
                'severity': 'low'
            })
        elif flesch > 80:
            # Too simple (not heavily penalized)
            score -= 5

        if grade > 12:
            score -= 10
            issues.append({
                'issue': f'Reading level too high (Grade {grade})',
                'fix': 'Target 8th-10th grade reading level',
                'severity': 'medium'
            })

        # NEW: Check paragraph length (max 4 sentences)
        paragraph_issues = self._check_paragraph_length(content)
        details['long_paragraphs'] = paragraph_issues['count']
        details['longest_paragraph_sentences'] = paragraph_issues['longest']

        if paragraph_issues['count'] > 0:
            penalty = min(15, paragraph_issues['count'] * 3)
            score -= penalty
            issues.append({
                'issue': f'{paragraph_issues["count"]} paragraphs exceed 4 sentences (longest: {paragraph_issues["longest"]})',
                'fix': 'Break long paragraphs into smaller chunks (2-4 sentences max)',
                'severity': 'medium' if paragraph_issues['count'] < 5 else 'high'
            })

        # NEW: Check sentence rhythm (variety in length)
        rhythm_issues = self._check_sentence_rhythm(content)
        details['rhythm_score'] = rhythm_issues['rhythm_score']
        details['monotonous_sections'] = rhythm_issues['monotonous_count']

        if rhythm_issues['rhythm_score'] < 60:
            penalty = min(10, (60 - rhythm_issues['rhythm_score']) / 4)
            score -= penalty
            issues.append({
                'issue': f'Monotonous sentence rhythm ({rhythm_issues["monotonous_count"]} uniform sections)',
                'fix': 'Vary sentence length: mix short punchy (5-10 words) with longer flowing (15-25 words)',
                'severity': 'medium' if rhythm_issues['rhythm_score'] > 40 else 'high'
            })

        return {
            'score': max(0, min(100, round(score))),
            'flesch': flesch,
            'issues': issues,
            'details': details
        }

    def _check_paragraph_length(self, content: str) -> Dict[str, Any]:
        """Check for paragraphs that exceed 4 sentences"""
        # Split into paragraphs (double newline or blank line)
        paragraphs = re.split(r'\n\s*\n', content)

        long_paragraphs = 0
        longest = 0

        for para in paragraphs:
            para = para.strip()
            # Skip headers, lists, tables, metadata
            if not para or para.startswith('#') or para.startswith('-') or para.startswith('*') or para.startswith('|') or para.startswith('**Meta'):
                continue

            # Count sentences (rough: split by . ! ? followed by space or end)
            sentences = re.split(r'[.!?]+(?:\s|$)', para)
            sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]

            sentence_count = len(sentences)
            if sentence_count > 4:
                long_paragraphs += 1
                longest = max(longest, sentence_count)

        return {
            'count': long_paragraphs,
            'longest': longest
        }

    def _check_sentence_rhythm(self, content: str) -> Dict[str, Any]:
        """Check for sentence length variety (rhythm)"""
        # Extract sentences
        sentences = re.split(r'[.!?]+(?:\s|$)', content)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]

        if len(sentences) < 10:
            return {'rhythm_score': 70, 'monotonous_count': 0}  # Not enough to evaluate

        # Calculate word counts for each sentence
        word_counts = [len(s.split()) for s in sentences]

        # Check rhythm in sliding windows of 5 sentences
        monotonous_sections = 0
        window_size = 5

        for i in range(len(word_counts) - window_size + 1):
            window = word_counts[i:i + window_size]
            avg = sum(window) / len(window)

            # Check if all sentences in window are within 5 words of average (monotonous)
            all_similar = all(abs(wc - avg) <= 5 for wc in window)
            if all_similar:
                monotonous_sections += 1

        # Calculate rhythm score
        # More variety = higher score
        if len(word_counts) > 0:
            std_dev = (sum((wc - sum(word_counts)/len(word_counts))**2 for wc in word_counts) / len(word_counts)) ** 0.5
        else:
            std_dev = 0

        # Target std_dev around 8-15 (good variety)
        if std_dev < 5:
            rhythm_score = 40 + (std_dev * 6)  # Too uniform
        elif std_dev <= 15:
            rhythm_score = 100 - abs(10 - std_dev) * 2  # Sweet spot
        else:
            rhythm_score = 80  # High variety is fine

        # Penalize for monotonous sections
        rhythm_score -= monotonous_sections * 3
        rhythm_score = max(0, min(100, rhythm_score))

        return {
            'rhythm_score': round(rhythm_score),
            'monotonous_count': monotonous_sections,
            'std_dev': round(std_dev, 1)
        }

    def format_report(self, result: Dict[str, Any]) -> str:
        """Format scoring result as readable report"""
        lines = []
        lines.append("=" * 50)
        lines.append("CONTENT QUALITY SCORE")
        lines.append("=" * 50)
        lines.append("")

        status = "PASSED" if result['passed'] else "BELOW THRESHOLD"
        lines.append(f"Composite Score: {result['composite_score']}/100 ({status})")
        lines.append(f"Content Quality Threshold: {result['threshold']}")
        aeo_geo = result.get('aeo_geo', {})
        if aeo_geo:
            lines.append(
                f"AEO/GEO Score: {aeo_geo.get('score', 0)}/100 "
                f"(threshold: {aeo_geo.get('threshold', 90)})"
            )
        lines.append("")

        lines.append("Dimensions:")
        for dim_name, dim_data in result['dimensions'].items():
            score = dim_data['score']
            weight = dim_data['weight']
            check = "OK" if score >= 70 else "NEEDS WORK"
            extra = ""
            if dim_name == 'structure_balance':
                extra = f" ({round(dim_data.get('prose_ratio', 0) * 100)}% prose)"
            elif dim_name == 'readability':
                flesch = dim_data.get('flesch', 0)
                details = dim_data.get('details', {})
                rhythm = details.get('rhythm_score', 'N/A')
                long_paras = details.get('long_paragraphs', 0)
                extra = f" (Flesch: {flesch}, Rhythm: {rhythm}, Long¶: {long_paras})"

            lines.append(f"  {dim_name:20} {score:3}/100 (weight: {int(weight*100)}%) [{check}]{extra}")

        lines.append("")

        if result['priority_fixes']:
            lines.append("Priority Fixes:")
            for i, fix in enumerate(result['priority_fixes'][:5], 1):
                dim = fix.get('dimension', 'unknown')
                issue = fix.get('issue', 'Unknown issue')
                suggestion = fix.get('fix', 'No suggestion')
                lines.append(f"  {i}. [{dim}] {issue}")
                lines.append(f"     Fix: {suggestion}")

        lines.append("")
        lines.append("=" * 50)

        return "\n".join(lines)


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
