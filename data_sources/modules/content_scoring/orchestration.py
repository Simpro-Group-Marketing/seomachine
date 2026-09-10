"""Orchestration responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


class ScoringOrchestrationMixin:
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
        finalized_bom: Optional[Mapping[str, Any]] = None,
        assembly_date: Optional[str] = None,
        paa_workflow_mode: Optional[str] = None,
        paa_content_brief: Optional[str] = None,
        paa_answersocrates_blocker: Optional[str] = None,
        paa_expected_query: Optional[str] = None,
        paa_expected_collection_date: Optional[str] = None,
        paa_expected_run_id: Optional[str] = None,
        paa_artifact: Optional[str] = None,
        prevalidated_gate_findings: Optional[
            Mapping[str, Sequence[Mapping[str, Any]]]
        ] = None,
        readiness_gate_context: object = None,
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
            finalized_bom: Guard-validated finalized assembly BOM used for
                author-policy decisions.
            assembly_date: Canonical assembly date that freshness metadata must
                match.
            paa_workflow_mode: Bound PAA workflow mode.
            paa_content_brief: Bound content brief path for PAA provenance.
            paa_answersocrates_blocker: Bound AnswerSocrates blocker, when any.
            paa_expected_query: Expected PAA collection query.
            paa_expected_collection_date: Expected PAA collection date.
            paa_artifact: Bound PAA artifact path.
            prevalidated_gate_findings: Deprecated compatibility input. Raw
                mappings are never trusted and standalone guards still run.
            readiness_gate_context: Opaque input-bound context issued only by
                publish readiness for same-run finding reuse.

        Returns:
            Dict with composite_score, passed, dimensions, and priority_fixes
        """
        metadata = metadata or {}

        _, visible_body, _ = split_frontmatter(content)

        # Reader-facing dimensions are based on visible Markdown body only.
        clean_content = self._clean_for_analysis(visible_body)

        # Score each dimension
        humanity = self._score_humanity(clean_content, lint_source=content)
        specificity = self._score_specificity(clean_content)
        structure = self._score_structure_balance(visible_body)
        seo = self._score_seo(content, metadata, proof_sidecar=proof_sidecar)
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
        seo_quality_passed = bool(seo.get('passed', True))
        gate_context = self._run_quality_gates(
            content,
            metadata,
            validate_urls=validate_urls,
            validate_source_support=validate_source_support,
            source_path=source_path,
            proof_sidecar=proof_sidecar,
            finalized_bom=finalized_bom,
            assembly_date=assembly_date,
            paa_workflow_mode=paa_workflow_mode,
            paa_content_brief=paa_content_brief,
            paa_answersocrates_blocker=paa_answersocrates_blocker,
            paa_expected_query=paa_expected_query,
            paa_expected_collection_date=paa_expected_collection_date,
            paa_expected_run_id=paa_expected_run_id,
            paa_artifact=paa_artifact,
            prevalidated_gate_findings=prevalidated_gate_findings,
            readiness_gate_context=readiness_gate_context,
        )

        # Determine if passed
        passed = self._quality_gates_passed(
            content_quality_passed,
            seo_quality_passed,
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
            seo_quality_passed,
            seo,
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
