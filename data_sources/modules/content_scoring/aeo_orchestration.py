"""Focused aeo orchestration scoring."""

from __future__ import annotations

import re

from .aeo_content import _check_capsule_coverage
from .aeo_content import _check_direct_answer
from .aeo_content import _check_external_source_diagnostic
from .aeo_content import _check_section_clarity
from .aeo_eeat import _check_eeat_proof
from .aeo_faq_paa import _check_bound_paa_provenance
from .aeo_faq_paa import _check_faq_answer_lengths
from .aeo_faq_paa import _check_faq_answer_quality
from .aeo_faq_paa import _check_faq_proof
from .aeo_faq_paa import _check_faq_questions
from .aeo_faq_paa import _check_faq_structure
from .aeo_metadata_schema import _check_author_voice
from .aeo_metadata_schema import _check_faq_policy
from .aeo_metadata_schema import _check_metadata_quality
from .aeo_metadata_schema import _check_schema
from .aeo_metadata_schema import _extract_structured_frontmatter
from .aeo_metadata_schema import _not_applicable_check
from .aeo_metadata_schema import _validated_non_connector_bom
from .aeo_text import _extract_frontmatter
from .aeo_text import _strip_frontmatter
from collections.abc import Mapping
from collections.abc import Sequence
from data_sources.modules.faq_structure import detect_faq_structure
from data_sources.modules.readiness_gate_context import trusted_readiness_findings
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

PASS_THRESHOLD = 90
NON_VISIBLE_HTML_BLOCK_RE = re.compile(
    r"<(?:script|style)\b[^>]*>.*?</(?:script|style)\s*>",
    re.IGNORECASE | re.DOTALL,
)

def _prevalidated_findings(
    readiness_gate_context: object,
    gate_name: str,
    *,
    article_content: str,
    proof_sidecar_content: Optional[str],
) -> Optional[List[Dict[str, Any]]]:
    """Read findings only from a sealed capability issued by readiness."""
    return trusted_readiness_findings(
        readiness_gate_context,
        gate_name,
        article_content=article_content,
        proof_sidecar_content=proof_sidecar_content,
    )

def rate_aeo_geo(
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    source_path: Optional[str] = None,
    proof_sidecar_content: Optional[str] = None,
    proof_sidecar_path: Optional[str] = None,
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
    Rate content against AEO/GEO publishing requirements.

    Args:
        content: Full markdown article content.
        metadata: Optional metadata such as primary_keyword, main_question, author.
        source_path: Optional draft path used to resolve relative PAA/FAQ
            provenance artifact paths.

    Returns:
        Dict with score, passed, checks, issues, and details.
    """
    metadata = metadata or {}
    if proof_sidecar_content is None and proof_sidecar_path:
        try:
            proof_sidecar_content = Path(proof_sidecar_path).read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            proof_sidecar_content = None
    frontmatter = _extract_frontmatter(content)
    frontmatter.update(_extract_structured_frontmatter(content))
    merged_metadata = {**frontmatter, **metadata}
    body = NON_VISIBLE_HTML_BLOCK_RE.sub("", _strip_frontmatter(content))
    faq_policy_status = str(
        merged_metadata.get('faq_policy_status') or ''
    ).strip().casefold()
    faq_structure = detect_faq_structure(body)
    visible_faq = faq_structure.visible

    faq_answer_findings = _prevalidated_findings(
        readiness_gate_context,
        "faq_answer_quality",
        article_content=content,
        proof_sidecar_content=proof_sidecar_content,
    )
    faq_proof_findings = _prevalidated_findings(
        readiness_gate_context,
        "faq_proof",
        article_content=content,
        proof_sidecar_content=proof_sidecar_content,
    )
    paa_findings = _prevalidated_findings(
        readiness_gate_context,
        "paa_provenance",
        article_content=content,
        proof_sidecar_content=proof_sidecar_content,
    )

    checks = {
        "direct_answer": _check_direct_answer(body, merged_metadata),
        "capsule_coverage": _check_capsule_coverage(body),
        "faq_questions": _check_faq_questions(body),
        "faq_answer_length": _check_faq_answer_lengths(body),
        "faq_answer_quality": _check_faq_answer_quality(
            content,
            prevalidated_findings=faq_answer_findings,
        ),
        "external_sources": _check_external_source_diagnostic(content),
        "metadata": _check_metadata_quality(
            merged_metadata,
            finalized_bom=finalized_bom,
            assembly_date=assembly_date,
        ),
        "eeat_proof": _check_eeat_proof(
            content,
            body,
            merged_metadata,
            proof_sidecar_content,
            proof_sidecar_path,
        ),
        "faq_proof": _check_faq_proof(
            content,
            proof_sidecar_content,
            prevalidated_findings=faq_proof_findings,
        ),
        "faq_structure": _check_faq_structure(body),
    }
    if _validated_non_connector_bom(finalized_bom):
        checks["eeat_proof"] = _not_applicable_check(
            checks["eeat_proof"],
            "Selector-backed Simpro E-E-A-T proof is not applicable to a guard-validated nonconnector article.",
        )
    checks['author_voice'] = _check_author_voice(
        body,
        merged_metadata,
        finalized_bom=finalized_bom,
    )
    checks['schema'] = _check_schema(
        content,
        merged_metadata,
        visible_faq=visible_faq,
        finalized_bom=finalized_bom,
    )
    checks['faq_policy'] = _check_faq_policy(
        faq_policy_status,
        visible_faq=visible_faq,
    )
    checks['paa_provenance'] = _check_bound_paa_provenance(
        content,
        source_path,
        proof_sidecar_content,
        workflow_mode=(
            paa_workflow_mode
            or str(merged_metadata.get('paa_workflow_mode') or '').strip()
            or 'new'
        ),
        content_brief=(
            paa_content_brief
            or str(merged_metadata.get('paa_content_brief') or '').strip()
            or None
        ),
        answersocrates_blocker=(
            paa_answersocrates_blocker
            or str(merged_metadata.get('paa_answersocrates_blocker') or '').strip()
            or None
        ),
        expected_query=(
            paa_expected_query
            or str(merged_metadata.get('paa_expected_query') or '').strip()
            or None
        ),
        expected_collection_date=(
            paa_expected_collection_date
            or str(merged_metadata.get('paa_expected_collection_date') or '').strip()
            or None
        ),
        expected_run_id=(
            paa_expected_run_id
            or str(merged_metadata.get('paa_expected_run_id') or '').strip()
            or None
        ),
        paa_artifact=(
            paa_artifact
            or str(merged_metadata.get('paa_artifact') or '').strip()
            or None
        ),
        prevalidated_findings=paa_findings,
    )
    if not visible_faq:
        for check_name in (
            'faq_questions',
            'faq_answer_length',
            'faq_answer_quality',
            'faq_proof',
        ):
            checks[check_name] = _not_applicable_check(
                checks[check_name],
                'No visible FAQ exists, so FAQ-only scoring is not applicable.',
            )
    for check in checks.values():
        check.setdefault('applicable', True)
        check.setdefault('status', 'passed' if check.get('passed') else 'failed')
    section_clarity = _check_section_clarity(body)

    weights = {
        'direct_answer': 18,
        'capsule_coverage': 18,
        'faq_questions': 8,
        'faq_answer_length': 8,
        'faq_answer_quality': 8,
        'metadata': 8,
        'author_voice': 4,
        'schema': 8,
        'eeat_proof': 10,
        'faq_proof': 5,
        'paa_provenance': 5,
    }
    possible_weight = sum(
        weight
        for name, weight in weights.items()
        if checks[name].get('applicable', True)
    )
    earned_weight = sum(
        weight
        for name, weight in weights.items()
        if checks[name].get('applicable', True) and checks[name].get('passed')
    )
    score = round(100 * earned_weight / possible_weight) if possible_weight else 0
    hard_gate_passed = all(
        not check.get('applicable', True) or bool(check.get('passed'))
        for check in checks.values()
    )
    issues = []
    for name, check in checks.items():
        if not check["passed"]:
            issues.append(
                {
                    "check": name,
                    "issue": check["issue"],
                    "fix": check["fix"],
                    "severity": check["severity"],
                }
            )

    return {
        "score": score,
        "passed": (
            hard_gate_passed
            and score >= PASS_THRESHOLD
            and checks["faq_questions"]["passed"]
            and checks["faq_answer_length"]["passed"]
            and checks["faq_answer_quality"]["passed"]
            and checks["metadata"]["passed"]
            and checks["eeat_proof"]["passed"]
            and checks["faq_proof"]["passed"]
            and checks["paa_provenance"]["passed"]
        ),
        "threshold": PASS_THRESHOLD,
        "checks": checks,
        "issues": issues,
        "details": {
            "h2_count": checks["capsule_coverage"]["details"]["h2_count"],
            "capsule_count": checks["capsule_coverage"]["details"]["capsule_count"],
            "faq_question_count": checks["faq_questions"]["details"]["question_count"],
            "faq_answer_quality_findings": checks["faq_answer_quality"]["details"][
                "findings"
            ],
            "external_link_count": checks["external_sources"]["details"][
                "external_link_count"
            ],
            "case_study_links": checks["eeat_proof"]["details"]["case_study_links"],
            "review_site_links": checks["eeat_proof"]["details"]["review_site_links"],
            "experience_signals": checks["eeat_proof"]["details"]["experience_signals"],
            "expertise_signals": checks["eeat_proof"]["details"]["expertise_signals"],
            "faq_proof_findings": checks["faq_proof"]["details"]["findings"],
            "paa_provenance_findings": checks["paa_provenance"]["details"]["findings"],
            "section_clarity": section_clarity,
        },
    }


__all__ = [
    "_prevalidated_findings",
    "rate_aeo_geo",
]
