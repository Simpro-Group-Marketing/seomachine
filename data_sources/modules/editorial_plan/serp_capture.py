"""Normalize and bind attested raw SERP captures."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .contracts import SERP_EVIDENCE_ATTESTATION_PURPOSE
from .contracts import SERP_EVIDENCE_SCHEMA
from .dependencies import EditorialPlanDependencies
from .dependencies import default_editorial_plan_dependencies
from .serp_raw import _artifact_workspace_root
from .serp_raw import _dataforseo_request_valid
from .serp_raw import _decode_playwright_response
from .serp_raw import _load_valid_serp_raw_capture
from .serp_raw import _normalize_dataforseo_items
from .serp_raw import _normalize_dataforseo_response
from .serp_raw import _normalize_serp_raw_response
from .serp_raw import _playwright_request_valid
from .serp_raw import _semrush_request_valid
from .serp_raw import _serp_content_type
from .serp_raw import _unique_strings
from .serp_raw import _validate_capture_identity
from .serp_raw import _validate_capture_request
from .serp_raw import _validate_normalized_response
from .serp_raw import _validate_serp_raw_snapshot
from .serp_raw import _validated_capture_payload
from .serp_raw import load_json_text
from .serp_raw import load_normalized_serp_raw_capture


def build_serp_evidence(
    *,
    raw_capture_path: str | Path,
    workspace_root: str | Path,
    must_have_sections: list[str],
    competitor_gaps: list[str],
    dependencies: EditorialPlanDependencies | None = None,
) -> dict[str, Any]:
    '''Build one evidence artifact solely from a bound attested raw capture.'''
    dependencies = dependencies or default_editorial_plan_dependencies()
    root = Path(workspace_root).resolve()
    snapshot, capture, normalized = _load_valid_serp_raw_capture(
        raw_capture_path,
        workspace_root=root,
        dependencies=dependencies,
    )
    organic = normalized.get('organic_results')
    blocker = normalized.get('blocker') or normalized.get('fallback_blocker')
    if blocker or not isinstance(organic, list) or not organic:
        raise ValueError('blocked or empty SERP raw capture cannot mint verified evidence')
    results = [
        {
            'position': position,
            'url': str(row.get('url') or '').strip(),
            'title': str(row.get('title') or '').strip(),
            'result_type': 'organic',
        }
        for position, row in enumerate(organic[:10], start=1)
    ]
    content_types = _unique_strings([
        _serp_content_type(row['title']) for row in results
    ])
    serp_features = _unique_strings(normalized.get('features', []))
    payload: dict[str, Any] = {
        'schema': SERP_EVIDENCE_SCHEMA,
        'status': 'verified',
        'query': capture['query'],
        'collected_at': capture['collected_at'],
        'collector': capture['collector'],
        'run_id': capture['run_id'],
        'results': results,
        'observations': {
            'content_types': content_types,
            'serp_features': serp_features,
            'must_have_sections': must_have_sections,
            'competitor_gaps': competitor_gaps,
        },
        'raw_capture': dependencies.canonical_snapshot_artifact(
            snapshot,
            workspace_root=root,
        ),
    }
    payload['evidence_hash'] = dependencies.canonical_json_sha256(payload)
    attested = dependencies.attest_mapping(
        payload,
        purpose=SERP_EVIDENCE_ATTESTATION_PURPOSE,
        workspace_root=root,
    )
    from .serp_validation import check_serp_evidence_payload

    findings = check_serp_evidence_payload(
        attested,
        expected_query=str(capture['query']),
        expected_run_id=str(capture['run_id']),
        assembly_date=(
            capture['collected_at'][:10]
            if isinstance(capture['collected_at'], str) and len(capture['collected_at']) >= 10
            else None
        ),
        workspace_root=root,
        dependencies=dependencies,
    )
    if findings:
        rules = ', '.join(sorted({str(row['rule_id']) for row in findings}))
        raise ValueError(f'invalid SERP evidence: {rules}')
    return attested
