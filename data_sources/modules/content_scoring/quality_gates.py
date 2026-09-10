"""Quality Gates responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


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
        proof_sidecar_content = load_sidecar_content(source_path, proof_sidecar)
        resolved_sidecar = resolve_sidecar_path(source_path, proof_sidecar)
        proof_sidecar_path = (
            str(resolved_sidecar.resolve())
            if resolved_sidecar is not None and resolved_sidecar.is_file()
            else None
        )
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
        aeo_geo = rate_aeo_geo(content, metadata, **aeo_kwargs)
        faq_proof_check = aeo_geo.get('checks', {}).get('faq_proof', {})
        paa_provenance_check = aeo_geo.get('checks', {}).get('paa_provenance', {})
        metric_proof_pack_findings = trusted_readiness_findings(
            readiness_gate_context,
            "metric_proof_pack",
            article_content=content,
            proof_sidecar_content=proof_sidecar_content,
        )
        if metric_proof_pack_findings is None:
            metric_proof_pack_findings = check_metric_proof_pack(
                content,
                source_path=source_path,
                proof_content=proof_sidecar_content,
            )
        customer_proof_findings = trusted_readiness_findings(
            readiness_gate_context,
            "customer_proof_diversity",
            article_content=content,
            proof_sidecar_content=proof_sidecar_content,
        )
        if customer_proof_findings is None:
            customer_proof_findings = check_customer_proof_diversity(
                content,
                source_path=source_path,
                proof_content=proof_sidecar_content,
                proof_sidecar_path=proof_sidecar_path,
            )
        review_story_findings = trusted_readiness_findings(
            readiness_gate_context,
            "review_story_identity",
            article_content=content,
            proof_sidecar_content=proof_sidecar_content,
        )
        if review_story_findings is None:
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

        faq_proof_check = gate_context['faq_proof_check']
        if not gate_context['faq_proof_passed']:
            faq_findings = faq_proof_check.get('details', {}).get('findings', [])
            faq_questions = ", ".join(
                str(finding.get('question', 'unknown FAQ')) for finding in faq_findings[:3]
            )
            priority_fixes.insert(0, {
                'issue': 'FAQ proof blockers detected',
                'fix': (
                    'Resolve each finding according to its machine-assigned citation_mode. '
                    'For inline_required, use a natural descriptive anchor to an '
                    'authoritative owned or non-owned source in the first visible answer '
                    'paragraph, map it in the FAQ Proof Map, and do not use competitor-owned '
                    'FAQ sources. For lower-risk modes, satisfy the '
                    'assigned mode without quota-only links; a sidecar cannot replace '
                    f'inline evidence when inline_required applies: {faq_questions}'
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
