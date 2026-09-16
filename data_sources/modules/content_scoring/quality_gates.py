"""Quality Gates responsibilities."""

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Dict, List, Optional

from data_sources.modules.content_scoring.seo_constants import (
    PUBLISHING_THRESHOLD as SEO_PUBLISHING_THRESHOLD,
    SEO_TARGET_SCORE,
)


class QualityGatesMixin:
    def _run_quality_gates(
        self,
        content: str,
        metadata: Dict[str, Any],
        *,
        validate_urls: bool,
        validate_source_support: bool,
        source_path: Optional[str],
        proof_sidecar: Optional[str],
        proof_content: Optional[str] = None,
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
        """Run proof-aware quality gates and keep scorer orchestration local."""
        if proof_content is None:
            proof_sidecar_content = self.dependencies.load_sidecar_content(
                source_path, proof_sidecar
            )
            resolved_sidecar = self.dependencies.resolve_sidecar_path(
                source_path, proof_sidecar
            )
            proof_sidecar_path = (
                str(resolved_sidecar.resolve())
                if resolved_sidecar is not None and resolved_sidecar.is_file()
                else None
            )
        else:
            proof_sidecar_content = proof_content
            proof_sidecar_path = proof_sidecar
        minimum_visible_words = self._check_minimum_visible_words(content)
        aeo_kwargs: Dict[str, Any] = {
            "source_path": source_path,
            "proof_sidecar_content": proof_sidecar_content,
            "proof_sidecar_path": proof_sidecar_path,
            "finalized_bom": finalized_bom,
            "assembly_date": assembly_date,
            "paa_workflow_mode": paa_workflow_mode,
            "paa_content_brief": paa_content_brief,
            "paa_answersocrates_blocker": paa_answersocrates_blocker,
            "paa_expected_query": paa_expected_query,
            "paa_expected_collection_date": paa_expected_collection_date,
            "paa_expected_run_id": paa_expected_run_id,
            "paa_artifact": paa_artifact,
        }
        if readiness_gate_context is not None:
            aeo_kwargs["readiness_gate_context"] = readiness_gate_context
        aeo_geo = self.dependencies.rate_aeo_geo(content, metadata, **aeo_kwargs)
        faq_proof_check = aeo_geo.get('checks', {}).get('faq_proof', {})
        paa_provenance_check = aeo_geo.get('checks', {}).get('paa_provenance', {})
        metric_proof_pack_findings = self.dependencies.trusted_readiness_findings(
            readiness_gate_context,
            "metric_proof_pack",
            article_content=content,
            proof_sidecar_content=proof_sidecar_content,
        )
        if metric_proof_pack_findings is None:
            metric_proof_pack_findings = self.dependencies.check_metric_proof_pack(
                content,
                source_path=source_path,
                proof_content=proof_sidecar_content,
            )
        customer_proof_findings = self.dependencies.trusted_readiness_findings(
            readiness_gate_context,
            "customer_proof_diversity",
            article_content=content,
            proof_sidecar_content=proof_sidecar_content,
        )
        if customer_proof_findings is None:
            customer_proof_findings = self.dependencies.check_customer_proof_diversity(
                content,
                source_path=source_path,
                proof_content=proof_sidecar_content,
                proof_sidecar_path=proof_sidecar_path,
            )
        review_story_findings = self.dependencies.trusted_readiness_findings(
            readiness_gate_context,
            "review_story_identity",
            article_content=content,
            proof_sidecar_content=proof_sidecar_content,
        )
        if review_story_findings is None:
            review_story_findings = self.dependencies.check_review_story_identity(
                content,
                source_path=source_path,
                proof_content=proof_sidecar_content,
            )

        source_support_findings = []
        if validate_source_support:
            source_support_findings = self.dependencies.check_source_support(
                content,
                base_path=Path(source_path).parent if source_path else None,
                proof_content=proof_sidecar_content,
            )

        # Run source support before URL validation so proof fetches are not
        # starved by a burst of URL-resolution requests to the same domain.
        url_validation = None
        if validate_urls:
            url_validation = self.dependencies.validate_content_urls(content)

        return {
            'aeo_geo': aeo_geo,
            'aeo_geo_passed': bool(aeo_geo.get('passed', False)),
            'faq_proof_check': faq_proof_check,
            'faq_proof_passed': bool(faq_proof_check.get('passed', True)),
            'paa_provenance_check': paa_provenance_check,
            'paa_provenance_passed': bool(paa_provenance_check.get('passed', True)),
            'metric_proof_pack_findings': metric_proof_pack_findings,
            'metric_proof_pack_passed': not self._has_error_finding(
                metric_proof_pack_findings
            ),
            'customer_proof_findings': customer_proof_findings,
            'customer_proof_passed': not self._has_error_finding(customer_proof_findings),
            'review_story_findings': review_story_findings,
            'review_story_passed': not self._has_error_finding(review_story_findings),
            'url_validation': url_validation,
            'url_validation_passed': True if url_validation is None else url_validation.passed,
            'source_support_findings': source_support_findings,
            'source_support_passed': not source_support_findings,
            'minimum_visible_words': minimum_visible_words,
            'minimum_visible_words_passed': bool(minimum_visible_words['passed']),
        }
    def _quality_gates_passed(
        self,
        content_quality_passed: bool,
        seo_quality_passed: bool,
        gate_context: Dict[str, Any],
    ) -> bool:
        return (
            content_quality_passed
            and seo_quality_passed
            and gate_context['aeo_geo_passed']
            and gate_context['faq_proof_passed']
            and gate_context['paa_provenance_passed']
            and gate_context['metric_proof_pack_passed']
            and gate_context['customer_proof_passed']
            and gate_context['review_story_passed']
            and gate_context['url_validation_passed']
            and gate_context['source_support_passed']
            and gate_context['minimum_visible_words_passed']
        )
    def _build_quality_gates(
        self,
        composite: float,
        content_quality_passed: bool,
        seo_quality_passed: bool,
        seo: Dict[str, Any],
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
        minimum_visible_words = gate_context['minimum_visible_words']
        seo_score = seo.get('score', 0)
        seo_target_met = (
            isinstance(seo_score, (int, float))
            and not isinstance(seo_score, bool)
            and float(seo_score) >= float(SEO_TARGET_SCORE)
        )
        seo_target_status = seo.get('target_status')
        if seo_target_status not in {'met', 'below_target', 'failed_floor'}:
            if not seo_quality_passed:
                seo_target_status = 'failed_floor'
            elif seo_target_met:
                seo_target_status = 'met'
            else:
                seo_target_status = 'below_target'
        quality_gates = {
            'content_quality': {
                'score': composite,
                'threshold': self.PASS_THRESHOLD,
                'passed': content_quality_passed
            },
            'seo_quality': {
                'score': seo_score,
                'threshold': SEO_PUBLISHING_THRESHOLD,
                'target': SEO_TARGET_SCORE,
                'passed': seo_quality_passed,
                'target_met': bool(seo.get('target_met', seo_target_met)),
                'target_status': seo_target_status,
                'critical_issues': list(seo.get('critical_issues', [])),
                'critical_issue_count': len(seo.get('critical_issues', [])),
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
            },
            'minimum_visible_words': {
                'word_count': minimum_visible_words['word_count'],
                'threshold': minimum_visible_words['threshold'],
                'passed': gate_context['minimum_visible_words_passed'],
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
    def _has_error_finding(findings: Sequence[Mapping[str, Any]]) -> bool:
        return any(
            str(finding.get("severity", "error")).casefold() == "error"
            for finding in findings
        )

    def _check_minimum_visible_words(self, content: str) -> Dict[str, Any]:
        """Require a small release floor while keeping SEO word counts diagnostic."""
        _frontmatter, visible_body, _sidecar = self.dependencies.split_frontmatter(content)
        clean = self._clean_for_analysis(visible_body)
        word_count = len(re.findall(r"\b[\w'-]+\b", clean))
        threshold = 150
        return {
            'word_count': word_count,
            'threshold': threshold,
            'passed': word_count >= threshold,
        }
