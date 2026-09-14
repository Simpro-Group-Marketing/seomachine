"""Validate normalized SERP evidence and its raw-capture binding."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import re

from .contracts import Finding
from .contracts import SERP_APPROVED_COLLECTORS
from .contracts import SERP_EVIDENCE_ATTESTATION_PURPOSE
from .contracts import SERP_EVIDENCE_FIELDS
from .contracts import SERP_EVIDENCE_SCHEMA
from .contracts import SERP_OBSERVATION_FIELDS
from .contracts import SERP_RESULT_FIELDS
from .contracts import _finding
from .contracts import _invalid_serp_field
from .contracts import _parse_iso_date
from .contracts import _rfc3339_utc
from .contracts import _sorted_findings
from .dependencies import EditorialPlanDependencies
from .dependencies import default_editorial_plan_dependencies
from .serp_raw import _artifact_workspace_root
from .serp_raw import _serp_content_type
from .serp_raw import _unique_strings
from .serp_raw import _validate_serp_raw_snapshot



def _check_serp_raw_binding(
    payload: Mapping[str, Any],
    *,
    workspace_root: str | Path | None,
    raw_capture_snapshot: Any = None,
    dependencies: EditorialPlanDependencies,
) -> list[Finding]:
    binding = payload.get('raw_capture')
    if not isinstance(binding, Mapping) or set(binding) != {'path', 'sha256'}:
        return [_finding(
            'serp_raw_capture_binding_missing',
            'SERP evidence must bind the exact raw collector capture.',
            '/raw_capture',
            'Regenerate evidence through scripts/research_serp_analysis.py.',
        )]
    if workspace_root is None:
        return [_finding(
            'serp_raw_capture_workspace_missing',
            'SERP raw capture validation requires the workspace root.',
            '/raw_capture/path',
            'Validate through the repository workflow.',
        )]
    if raw_capture_snapshot is None:
        try:
            path = dependencies.resolve_artifact(
                binding.get('path'),
                workspace_root=workspace_root,
            )
            snapshot = dependencies.load_json_object_snapshot(
                path,
                field='SERP raw capture',
            )
        except ValueError as error:
            return [_finding(
                'serp_raw_capture_invalid',
                f'SERP raw capture is invalid: {error}.',
                '/raw_capture',
                'Rerun the approved SERP collector.',
            )]
    else:
        snapshot = raw_capture_snapshot
    if snapshot.sha256 != binding.get('sha256'):
        return [_finding(
            'serp_raw_capture_hash_mismatch',
            'SERP raw capture bytes changed after evidence emission.',
            '/raw_capture/sha256',
            'Rerun SERP research from the unchanged raw response.',
        )]
    try:
        capture, normalized = _validate_serp_raw_snapshot(
            snapshot,
            workspace_root=workspace_root,
            dependencies=dependencies,
        )
    except ValueError as error:
        return [_finding(
            'serp_raw_capture_invalid',
            f'SERP raw capture is invalid: {error}.',
            '/raw_capture',
            'Rerun the approved SERP collector.',
        )]
    if any((
        capture.get('query') != payload.get('query'),
        capture.get('run_id') != payload.get('run_id'),
        capture.get('collected_at') != payload.get('collected_at'),
        capture.get('collector') != payload.get('collector'),
    )):
        return [_finding(
            'serp_raw_capture_metadata_mismatch',
            'SERP evidence metadata diverges from its raw capture.',
            '/raw_capture',
            'Regenerate evidence for the exact query and agency run.',
        )]
    organic = normalized.get('organic_results')
    if normalized.get('blocker') or normalized.get('fallback_blocker') or not organic:
        return [_finding(
            'serp_raw_capture_blocked_or_empty',
            'Blocked or empty raw SERP output cannot support verified evidence.',
            '/raw_capture',
            'Collect at least one visible organic result.',
        )]
    expected_results = [
        {
            'position': position,
            'url': str(row.get('url') or '').strip(),
            'title': str(row.get('title') or '').strip(),
            'result_type': 'organic',
        }
        for position, row in enumerate(organic[:10], start=1)
    ]
    observations = payload.get('observations')
    expected_types = _unique_strings([_serp_content_type(row['title']) for row in expected_results])
    expected_features = _unique_strings(normalized.get('features', []))
    if (
        payload.get('results') != expected_results
        or not isinstance(observations, Mapping)
        or observations.get('content_types') != expected_types
        or observations.get('serp_features') != expected_features
    ):
        return [_finding(
            'serp_evidence_raw_divergence',
            'SERP evidence rows or directly obtainable observations diverge from raw output.',
            '/results',
            'Regenerate normalized evidence from the bound raw capture.',
        )]
    return []




def check_serp_evidence_file(
    path: str | Path,
    *,
    expected_query: str,
    assembly_date: str | None,
    expected_run_id: str | None = None,
    workspace_root: str | Path | None = None,
    dependencies: EditorialPlanDependencies | None = None,
) -> list[Finding]:
    '''Validate the exact SERP evidence metadata bound to an editorial plan.'''
    dependencies = dependencies or default_editorial_plan_dependencies()
    source = Path(path)
    root = _artifact_workspace_root(source, workspace_root)
    try:
        payload = dependencies.load_json_object_snapshot(
            source,
            field='SERP evidence',
        ).payload
    except ValueError as error:
        return [_finding(
            'serp_evidence_unreadable',
            f'SERP evidence cannot be read as UTF-8 JSON: {error}',
            '/',
            'Regenerate the verified SERP evidence artifact.',
        )]
    if not isinstance(payload, Mapping):
        return [_finding(
            'serp_evidence_root_invalid',
            'SERP evidence JSON must be an object.',
            '/',
            'Regenerate the verified SERP evidence artifact.',
        )]
    return _check_serp_evidence_payload(
        payload,
        expected_query=expected_query,
        assembly_date=assembly_date,
        expected_run_id=expected_run_id,
        workspace_root=root,
        dependencies=dependencies,
    )


def check_serp_evidence_payload(
    payload: Mapping[str, Any],
    *,
    expected_query: str,
    assembly_date: str | None,
    expected_run_id: str | None,
    workspace_root: str | Path | None = None,
    raw_capture_snapshot: Any = None,
    dependencies: EditorialPlanDependencies | None = None,
) -> list[Finding]:
    dependencies = dependencies or default_editorial_plan_dependencies()
    findings = _shape_findings(payload, workspace_root, dependencies)
    findings.extend(_query_and_time_findings(payload, expected_query, assembly_date))
    findings.extend(_collector_and_run_findings(payload, expected_run_id))
    findings.extend(_result_findings(payload.get('results')))
    findings.extend(_observation_findings(payload.get('observations')))
    findings.extend(_evidence_hash_findings(payload, dependencies))
    findings.extend(_check_serp_raw_binding(
        payload,
        workspace_root=workspace_root,
        raw_capture_snapshot=raw_capture_snapshot,
        dependencies=dependencies,
    ))
    return _sorted_findings(findings)


def _shape_findings(
    payload: Mapping[str, Any],
    workspace_root: str | Path | None,
    dependencies: EditorialPlanDependencies,
) -> list[Finding]:
    findings: list[Finding] = []
    if set(payload) != SERP_EVIDENCE_FIELDS:
        findings.append(_finding(
            'serp_evidence_shape_invalid',
            'SERP evidence must use the exact observation and collection-receipt fields.',
            '/',
            'Regenerate the artifact with build_serp_evidence().',
        ))
    if payload.get('schema') != SERP_EVIDENCE_SCHEMA:
        findings.append(_finding(
            'serp_evidence_schema_invalid',
            f'SERP evidence must use {SERP_EVIDENCE_SCHEMA}.',
            '/schema',
            'Regenerate the evidence with the current SERP research workflow.',
        ))
    if not dependencies.verify_mapping_attestation(
        payload,
        purpose=SERP_EVIDENCE_ATTESTATION_PURPOSE,
        workspace_root=workspace_root,
    ):
        findings.append(_finding(
            'serp_evidence_execution_attestation_invalid',
            'SERP evidence lacks a valid collector execution attestation.',
            '/execution_attestation',
            'Regenerate the artifact through the live SERP research command.',
        ))
    if payload.get('status') != 'verified':
        findings.append(_finding(
            'serp_evidence_status_invalid',
            'SERP evidence status must be verified.',
            '/status',
            'Complete live SERP verification before planning the article.',
        ))
    return findings


def _query_and_time_findings(
    payload: Mapping[str, Any],
    expected_query: str,
    assembly_date: str | None,
) -> list[Finding]:
    findings: list[Finding] = []
    query = payload.get('query')
    if not isinstance(query, str) or not query.strip():
        findings.append(_invalid_serp_field('/query', 'must be a non-empty string'))
    elif not isinstance(expected_query, str) or query.strip().casefold() != expected_query.strip().casefold():
        findings.append(_finding(
            'serp_evidence_query_mismatch',
            'SERP evidence query must exactly match the editorial-plan primary keyword.',
            '/query',
            'Regenerate the evidence for the planned query.',
        ))
    collected_at = payload.get('collected_at')
    timestamp = _rfc3339_utc(collected_at)
    if timestamp is None:
        findings.append(_invalid_serp_field(
            '/collected_at',
            'must be an RFC 3339 UTC timestamp ending in Z',
        ))
    expected_date = _parse_iso_date(assembly_date)
    if expected_date is None:
        findings.append(_invalid_serp_field(
            '/assembly_date',
            'requires a valid ISO assembly date from the workflow',
        ))
    elif timestamp is not None and timestamp.date() != expected_date:
        findings.append(_finding(
            'serp_evidence_stale',
            'SERP evidence must be verified on the current assembly date.',
            '/collected_at',
            'Rerun verified SERP research for this assembly run.',
        ))
    if timestamp is not None and timestamp > datetime.now(timezone.utc):
        findings.append(_finding(
            'serp_evidence_future',
            'SERP evidence collection time cannot be in the future.',
            '/collected_at',
            'Rerun SERP research with the current UTC workflow clock.',
        ))
    return findings


def _collector_and_run_findings(
    payload: Mapping[str, Any],
    expected_run_id: str | None,
) -> list[Finding]:
    findings: list[Finding] = []
    collector = payload.get('collector')
    if (
        not isinstance(collector, Mapping)
        or set(collector) != {'name', 'version'}
        or (collector.get('name'), collector.get('version'))
        not in SERP_APPROVED_COLLECTORS
    ):
        findings.append(_invalid_serp_field(
            '/collector',
            'must identify the collection tool and version',
        ))
    run_id = payload.get('run_id')
    if not isinstance(run_id, str) or not run_id.strip():
        findings.append(_invalid_serp_field('/run_id', 'must be a non-empty string'))
    if not isinstance(expected_run_id, str) or not expected_run_id.strip():
        findings.append(_finding(
            'serp_evidence_run_expectation_missing',
            'SERP evidence validation requires the canonical article run ID.',
            '/run_id',
            'Pass the canonical BOM run ID into editorial-plan validation.',
        ))
    elif isinstance(run_id, str) and run_id != expected_run_id:
        findings.append(_finding(
            'serp_evidence_run_mismatch',
            'SERP evidence run ID must equal the canonical article run ID.',
            '/run_id',
            'Rerun SERP research within the current article assembly run.',
        ))
    return findings


def _result_findings(results: Any) -> list[Finding]:
    if not isinstance(results, list) or not results:
        return [_invalid_serp_field('/results', 'must contain collected SERP results')]
    findings: list[Finding] = []
    positions: set[int] = set()
    for index, row in enumerate(results):
        location = f'/results/{index}'
        if not isinstance(row, Mapping) or set(row) != SERP_RESULT_FIELDS:
            findings.append(_invalid_serp_field(location, 'must use the exact result shape'))
            continue
        position = row.get('position')
        if not _valid_result_row(row, positions):
            findings.append(_invalid_serp_field(location, 'contains invalid collected result metadata'))
        if isinstance(position, int) and not isinstance(position, bool):
            positions.add(position)
    return findings


def _valid_result_row(row: Mapping[str, Any], positions: set[int]) -> bool:
    position = row.get('position')
    parsed_url = urlparse(str(row.get('url') or ''))
    return (
        isinstance(position, int)
        and not isinstance(position, bool)
        and position > 0
        and position not in positions
        and parsed_url.scheme in {'http', 'https'}
        and bool(parsed_url.netloc)
        and isinstance(row.get('title'), str)
        and bool(str(row.get('title')).strip())
        and row.get('result_type')
        in {'organic', 'featured_snippet', 'people_also_ask', 'video', 'other'}
    )


def _observation_findings(observations: Any) -> list[Finding]:
    if not isinstance(observations, Mapping) or set(observations) != SERP_OBSERVATION_FIELDS:
        return [_invalid_serp_field(
            '/observations',
            'must use the exact observed strategy fields',
        )]
    findings: list[Finding] = []
    for key in SERP_OBSERVATION_FIELDS:
        if not _valid_observation_list(observations.get(key)):
            findings.append(_invalid_serp_field(
                f'/observations/{key}',
                'must be a unique list of non-empty strings',
            ))
    content_types = observations.get('content_types')
    if isinstance(content_types, list) and not content_types:
        findings.append(_invalid_serp_field(
            '/observations/content_types',
            'must contain at least one observed content type',
        ))
    return findings


def _valid_observation_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(item, str) and bool(item.strip()) for item in value)
        and len({item.strip().casefold() for item in value}) == len(value)
    )


def _evidence_hash_findings(
    payload: Mapping[str, Any],
    dependencies: EditorialPlanDependencies,
) -> list[Finding]:
    stored_hash = payload.get('evidence_hash')
    unsigned = dict(payload)
    unsigned.pop('evidence_hash', None)
    unsigned.pop('execution_attestation', None)
    if (
        not isinstance(stored_hash, str)
        or re.fullmatch(r'[0-9a-f]{64}', stored_hash) is None
        or stored_hash != dependencies.canonical_json_sha256(unsigned)
    ):
        return [_finding(
            'serp_evidence_hash_invalid',
            'SERP evidence canonical hash does not match its collected observations.',
            '/evidence_hash',
            'Regenerate the immutable SERP evidence artifact.',
        )]
    return []


_check_serp_evidence_payload = check_serp_evidence_payload
