'''Validate serialized Simpro blog editorial plans.'''

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from .article_planner import CTAType, EDITORIAL_PLAN_SCHEMA, FunnelStage, SectionType
    from .blog_assembly_contract import canonical_json_sha256
    from .execution_attestation import attest_mapping, verify_mapping_attestation
    from .frontmatter import FrontmatterError, split_frontmatter
except ImportError:  # pragma: no cover - supports direct script execution.
    from article_planner import CTAType, EDITORIAL_PLAN_SCHEMA, FunnelStage, SectionType
    from blog_assembly_contract import canonical_json_sha256
    from execution_attestation import attest_mapping, verify_mapping_attestation
    from frontmatter import FrontmatterError, split_frontmatter


Finding = dict[str, Any]

TOP_LEVEL_FIELDS = frozenset(
    {
        'schema',
        'topic',
        'date',
        'meta',
        'total_word_target',
        'sections',
        'engagement_map',
        'gap_mapping',
        'insight_mapping',
        'reader_contract',
        'serp_strategy',
        'original_contributions',
        'entity_map',
        'query_ownership',
        'internal_link_plan',
        'faq_policy',
        'paa_policy',
    }
)
META_FIELDS = frozenset(
    {
        'title_options',
        'meta_title',
        'meta_description',
        'url_slug',
        'primary_keyword',
        'secondary_keywords',
    }
)
READER_CONTRACT_FIELDS = frozenset(
    {
        'primary_reader',
        'sophistication_level',
        'trigger_problem',
        'existing_belief',
        'decision_task_helped',
        'distinctive_angle',
        'promised_payoff',
        'funnel_stage',
        'exclusions',
    }
)
SECTION_FIELDS = frozenset(
    {
        'section_number',
        'type',
        'heading',
        'word_target',
        'strategic_angle',
        'engagement_hook',
        'knowledge_gaps',
        'unique_data',
        'internal_links',
        'cta',
        'next_action',
        'mini_story',
        'featured_snippet',
    }
)
ENGAGEMENT_FIELDS = frozenset(
    {
        'mini_stories',
        'ctas',
        'featured_snippets',
        'next_actions',
        'cta_exception_reason',
    }
)
SERP_STRATEGY_FIELDS = frozenset(
    {
        'status',
        'content_type',
        'serp_features',
        'serp_structure',
        'competitor_gaps',
        'exception_reasons',
    }
)
ORIGINAL_CONTRIBUTION_FIELDS = frozenset(
    {'description', 'final_section', 'visible_evidence'}
)
ENTITY_MAP_FIELDS = frozenset({'primary', 'supporting'})
QUERY_OWNERSHIP_FIELDS = frozenset({'decision', 'rationale'})
INTERNAL_LINK_FIELDS = frozenset({'target', 'role', 'rationale'})
FAQ_POLICY_FIELDS = frozenset({'status', 'rationale'})
PAA_POLICY_FIELDS = frozenset({'source_kind', 'query', 'selected_questions'})
SERP_EVIDENCE_SCHEMA = 'simpro-serp-evidence/v1'
SERP_EVIDENCE_ATTESTATION_PURPOSE = 'simpro-serp-evidence/v1'
SERP_EVIDENCE_FIELDS = frozenset(
    {
        'schema',
        'status',
        'query',
        'collected_at',
        'collector',
        'run_id',
        'results',
        'observations',
        'execution_attestation',
        'evidence_hash',
    }
)
SERP_RESULT_FIELDS = frozenset({'position', 'url', 'title', 'result_type'})
SERP_OBSERVATION_FIELDS = frozenset(
    {'content_types', 'serp_features', 'must_have_sections', 'competitor_gaps'}
)
RFC3339_UTC_RE = re.compile(
    r'\A\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?Z\Z'
)
OWNED_INTERNAL_DOMAINS = frozenset(
    {
        'simprogroup.com',
        'simpro.ai',
        'clockshark.com',
        'bigchange.com',
    }
)


def build_serp_evidence(
    *,
    query: str,
    collected_at: str,
    collector_name: str,
    collector_version: str,
    run_id: str,
    results: list[dict[str, Any]],
    content_types: list[str],
    serp_features: list[str],
    must_have_sections: list[str],
    competitor_gaps: list[str],
) -> dict[str, Any]:
    '''Build one receipt-hashed SERP observation artifact.'''
    payload: dict[str, Any] = {
        'schema': SERP_EVIDENCE_SCHEMA,
        'status': 'verified',
        'query': query,
        'collected_at': collected_at,
        'collector': {'name': collector_name, 'version': collector_version},
        'run_id': run_id,
        'results': results,
        'observations': {
            'content_types': content_types,
            'serp_features': serp_features,
            'must_have_sections': must_have_sections,
            'competitor_gaps': competitor_gaps,
        },
    }
    payload['evidence_hash'] = canonical_json_sha256(payload)
    attested = attest_mapping(
        payload,
        purpose=SERP_EVIDENCE_ATTESTATION_PURPOSE,
    )
    findings = _check_serp_evidence_payload(
        attested,
        expected_query=query,
        assembly_date=(
            collected_at[:10]
            if isinstance(collected_at, str) and len(collected_at) >= 10
            else None
        ),
    )
    if findings:
        rules = ', '.join(sorted({str(row['rule_id']) for row in findings}))
        raise ValueError(f'invalid SERP evidence: {rules}')
    return attested


def check_file(
    path: str | Path,
    *,
    article_path: str | Path | None = None,
    serp_evidence_path: str | Path | None = None,
    assembly_date: str | None = None,
) -> list[Finding]:
    '''Return blocking findings for one editorial-plan JSON file.'''
    source = Path(path)
    try:
        raw = source.read_text(encoding='utf-8')
    except (OSError, UnicodeError) as error:
        return [
            _finding(
                'editorial_plan_unreadable',
                f'Editorial plan cannot be read as UTF-8 JSON: {error}',
                '/',
                'Regenerate the editorial plan from the current ArticlePlan.',
            )
        ]
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        return [
            _finding(
                'editorial_plan_json_invalid',
                f'Editorial plan contains invalid JSON: {error.msg}.',
                '/',
                'Serialize the plan with serialize_article_plan().',
            )
        ]
    findings = check_plan(payload)
    if isinstance(payload, Mapping):
        findings.extend(_check_plan_assembly_date(payload, assembly_date))
    if isinstance(payload, Mapping) and serp_evidence_path is not None:
        expected_query = _nested_string(payload, 'meta', 'primary_keyword')
        findings.extend(
            check_serp_evidence_file(
                serp_evidence_path,
                expected_query=expected_query,
                assembly_date=assembly_date,
            )
        )
        strategy = payload.get('serp_strategy')
        try:
            serp_payload = json.loads(Path(serp_evidence_path).read_text(encoding='utf-8'))
        except (OSError, UnicodeError, json.JSONDecodeError):
            serp_payload = None
        if isinstance(strategy, Mapping) and isinstance(serp_payload, Mapping):
            findings.extend(_check_serp_strategy_evidence_binding(strategy, serp_payload))
        if isinstance(strategy, Mapping) and str(strategy.get('status') or '').startswith(
            'unresolved'
        ):
            findings.append(
                _finding(
                    'editorial_plan_serp_strategy_unresolved',
                    'Editorial plan must record resolved intent and SERP decisions.',
                    '/serp_strategy/status',
                    'Regenerate the plan from the bound verified SERP evidence.',
                )
            )
    if isinstance(payload, Mapping) and article_path is not None:
        findings.extend(
            _check_final_article_bindings(
                payload,
                article_path,
                assembly_date=assembly_date,
            )
        )
    return _sorted_findings(findings)


def check_serp_evidence_file(
    path: str | Path,
    *,
    expected_query: str,
    assembly_date: str | None,
) -> list[Finding]:
    '''Validate the exact SERP evidence metadata bound to an editorial plan.'''
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding='utf-8'))
    except (OSError, UnicodeError) as error:
        return [_finding(
            'serp_evidence_unreadable',
            f'SERP evidence cannot be read as UTF-8 JSON: {error}',
            '/',
            'Regenerate the verified SERP evidence artifact.',
        )]
    except json.JSONDecodeError as error:
        return [_finding(
            'serp_evidence_json_invalid',
            f'SERP evidence contains invalid JSON: {error.msg}.',
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
    )


def _check_serp_evidence_payload(
    payload: Mapping[str, Any],
    *,
    expected_query: str,
    assembly_date: str | None,
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
    if not verify_mapping_attestation(
        payload,
        purpose=SERP_EVIDENCE_ATTESTATION_PURPOSE,
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
    collector = payload.get('collector')
    if (
        not isinstance(collector, Mapping)
        or set(collector) != {'name', 'version'}
        or not isinstance(collector.get('name'), str)
        or not str(collector.get('name')).strip()
        or not isinstance(collector.get('version'), str)
        or not str(collector.get('version')).strip()
    ):
        findings.append(_invalid_serp_field(
            '/collector',
            'must identify the collection tool and version',
        ))
    if not isinstance(payload.get('run_id'), str) or not str(payload.get('run_id')).strip():
        findings.append(_invalid_serp_field('/run_id', 'must be a non-empty string'))
    results = payload.get('results')
    if not isinstance(results, list) or not results:
        findings.append(_invalid_serp_field('/results', 'must contain collected SERP results'))
    else:
        positions: set[int] = set()
        for index, row in enumerate(results):
            location = f'/results/{index}'
            if not isinstance(row, Mapping) or set(row) != SERP_RESULT_FIELDS:
                findings.append(_invalid_serp_field(location, 'must use the exact result shape'))
                continue
            position = row.get('position')
            parsed_url = urlparse(str(row.get('url') or ''))
            if (
                not isinstance(position, int)
                or isinstance(position, bool)
                or position <= 0
                or position in positions
                or parsed_url.scheme not in {'http', 'https'}
                or not parsed_url.netloc
                or not isinstance(row.get('title'), str)
                or not str(row.get('title')).strip()
                or row.get('result_type')
                not in {'organic', 'featured_snippet', 'people_also_ask', 'video', 'other'}
            ):
                findings.append(_invalid_serp_field(location, 'contains invalid collected result metadata'))
            if isinstance(position, int) and not isinstance(position, bool):
                positions.add(position)
    observations = payload.get('observations')
    if not isinstance(observations, Mapping) or set(observations) != SERP_OBSERVATION_FIELDS:
        findings.append(_invalid_serp_field(
            '/observations',
            'must use the exact observed strategy fields',
        ))
    else:
        for key in SERP_OBSERVATION_FIELDS:
            value = observations.get(key)
            if (
                not isinstance(value, list)
                or any(not isinstance(item, str) or not item.strip() for item in value)
                or len({item.strip().casefold() for item in value if isinstance(item, str)})
                != len(value)
            ):
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
    stored_hash = payload.get('evidence_hash')
    unsigned = dict(payload)
    unsigned.pop('evidence_hash', None)
    unsigned.pop('execution_attestation', None)
    if (
        not isinstance(stored_hash, str)
        or re.fullmatch(r'[0-9a-f]{64}', stored_hash) is None
        or stored_hash != canonical_json_sha256(unsigned)
    ):
        findings.append(_finding(
            'serp_evidence_hash_invalid',
            'SERP evidence canonical hash does not match its collected observations.',
            '/evidence_hash',
            'Regenerate the immutable SERP evidence artifact.',
        ))
    return _sorted_findings(findings)


def check_plan(value: Any) -> list[Finding]:
    '''Return deterministic findings for one loaded editorial-plan value.'''
    if not isinstance(value, Mapping):
        return [
            _finding(
                'editorial_plan_root_invalid',
                'Editorial plan JSON must be an object.',
                '/',
                'Serialize an ArticlePlan object instead of a scalar or list.',
            )
        ]

    findings: list[Finding] = []
    if value.get('schema') != EDITORIAL_PLAN_SCHEMA:
        findings.append(
            _finding(
                'editorial_plan_schema_invalid',
                f'Editorial plan must use {EDITORIAL_PLAN_SCHEMA}.',
                '/schema',
                'Regenerate the plan with the current article planner.',
            )
        )
    findings.extend(_unknown_fields(value, TOP_LEVEL_FIELDS, ''))
    _require_nonempty_string(value, 'topic', findings, '/topic')
    _require_nonempty_string(value, 'date', findings, '/date')
    raw_plan_date = value.get('date')
    if isinstance(raw_plan_date, str) and raw_plan_date.strip() and _parse_iso_date(raw_plan_date) is None:
        findings.append(_finding(
            'editorial_plan_date_invalid',
            'Editorial plan date must be a canonical ISO date in YYYY-MM-DD form.',
            '/date',
            'Regenerate the plan for the current assembly date.',
        ))
    total_word_target = value.get('total_word_target')
    if not _is_positive_int(total_word_target):
        findings.append(_invalid_field('/total_word_target', 'must be a positive integer'))

    findings.extend(_check_meta(value.get('meta')))
    findings.extend(_check_reader_contract(value.get('reader_contract')))
    section_findings, section_numbers, section_word_total, section_rows = _check_sections(
        value.get('sections')
    )
    findings.extend(section_findings)
    if _is_positive_int(total_word_target) and section_word_total is not None:
        if total_word_target != section_word_total:
            findings.append(
                _finding(
                    'editorial_plan_word_total_mismatch',
                    'total_word_target must equal the sum of section word targets.',
                    '/total_word_target',
                    'Reconcile the article total with every section word target.',
                )
            )
    findings.extend(
        _check_engagement_map(
            value.get('engagement_map'),
            section_numbers,
            section_rows,
        )
    )
    for field_name in ('gap_mapping', 'insight_mapping'):
        findings.extend(
            _check_section_mapping(
                value.get(field_name),
                section_numbers,
                f'/{field_name}',
            )
        )
    findings.extend(_check_serp_strategy(value.get('serp_strategy')))
    findings.extend(_check_original_contributions(value.get('original_contributions')))
    findings.extend(_check_entity_map(value.get('entity_map')))
    findings.extend(_check_query_ownership(value.get('query_ownership')))
    findings.extend(_check_internal_link_plan(value.get('internal_link_plan')))
    findings.extend(
        _check_faq_paa_policies(
            value.get('faq_policy'),
            value.get('paa_policy'),
            value.get('sections'),
        )
    )
    return _sorted_findings(findings)


def _check_meta(value: Any) -> list[Finding]:
    location = '/meta'
    if not isinstance(value, Mapping):
        return [_invalid_field(location, 'must be an object')]
    findings = _unknown_fields(value, META_FIELDS, location)
    for key in ('meta_title', 'meta_description', 'url_slug', 'primary_keyword'):
        _require_nonempty_string(value, key, findings, f'{location}/{key}')
    findings.extend(_check_string_list(value.get('title_options'), f'{location}/title_options', required=True))
    findings.extend(_check_string_list(value.get('secondary_keywords'), f'{location}/secondary_keywords'))
    return findings


def _check_reader_contract(value: Any) -> list[Finding]:
    location = '/reader_contract'
    if not isinstance(value, Mapping):
        return [_invalid_field(location, 'must be an object')]
    findings = _unknown_fields(value, READER_CONTRACT_FIELDS, location)
    for key in (
        'primary_reader',
        'sophistication_level',
        'trigger_problem',
        'existing_belief',
        'decision_task_helped',
        'distinctive_angle',
        'promised_payoff',
    ):
        _require_nonempty_string(value, key, findings, f'{location}/{key}')
    if value.get('funnel_stage') not in {stage.value for stage in FunnelStage}:
        findings.append(_invalid_field(f'{location}/funnel_stage', 'uses an unsupported funnel stage'))
    findings.extend(_check_string_list(value.get('exclusions'), f'{location}/exclusions'))
    return findings


def _check_sections(
    value: Any,
) -> tuple[list[Finding], set[int], int | None, list[Mapping[str, Any]]]:
    location = '/sections'
    if not isinstance(value, list) or not value:
        return [_invalid_field(location, 'must be a non-empty list')], set(), None, []
    findings: list[Finding] = []
    rows: list[Mapping[str, Any]] = []
    numbers: list[int] = []
    word_total = 0
    all_word_targets_valid = True
    section_types = {item.value for item in SectionType}
    action_types = {item.value for item in CTAType}
    for index, row in enumerate(value):
        row_location = f'{location}/{index}'
        if not isinstance(row, Mapping):
            findings.append(_invalid_field(row_location, 'must be an object'))
            all_word_targets_valid = False
            continue
        rows.append(row)
        findings.extend(_unknown_fields(row, SECTION_FIELDS, row_location))
        number = row.get('section_number')
        if _is_positive_int(number):
            numbers.append(number)
        else:
            findings.append(_invalid_field(f'{row_location}/section_number', 'must be a positive integer'))
        word_target = row.get('word_target')
        if _is_positive_int(word_target):
            word_total += word_target
        else:
            all_word_targets_valid = False
            findings.append(_invalid_field(f'{row_location}/word_target', 'must be a positive integer'))
        if row.get('type') not in section_types:
            findings.append(_invalid_field(f'{row_location}/type', 'uses an unsupported section type'))
        for key in ('heading', 'strategic_angle'):
            _require_nonempty_string(row, key, findings, f'{row_location}/{key}')
        hook = row.get('engagement_hook')
        if hook is not None and (not isinstance(hook, str) or not hook.strip()):
            findings.append(_invalid_field(f'{row_location}/engagement_hook', 'must be null or a non-empty string'))
        for key in ('knowledge_gaps', 'unique_data', 'internal_links'):
            findings.extend(_check_string_list(row.get(key), f'{row_location}/{key}'))
        for key in ('cta', 'next_action'):
            if row.get(key) is not None and row.get(key) not in action_types:
                findings.append(_invalid_field(f'{row_location}/{key}', 'uses an unsupported action type'))
        for key in ('mini_story', 'featured_snippet'):
            if not isinstance(row.get(key), bool):
                findings.append(_invalid_field(f'{row_location}/{key}', 'must be a boolean'))
    if numbers != list(range(1, len(value) + 1)):
        findings.append(
            _finding(
                'editorial_plan_section_sequence_invalid',
                'Sections must use contiguous numbers starting at 1.',
                location,
                'Renumber sections in article order and update all references.',
            )
        )
    return findings, set(numbers), word_total if all_word_targets_valid else None, rows


def _check_engagement_map(
    value: Any,
    section_numbers: set[int],
    section_rows: list[Mapping[str, Any]],
) -> list[Finding]:
    location = '/engagement_map'
    if not isinstance(value, Mapping):
        return [_invalid_field(location, 'must be an object')]
    findings = _unknown_fields(value, ENGAGEMENT_FIELDS, location)
    list_values: dict[str, list[int]] = {}
    for key in ('mini_stories', 'featured_snippets'):
        candidate = value.get(key)
        if not isinstance(candidate, list) or any(
            not _is_positive_int(item) for item in candidate
        ) or len(candidate) != len(set(candidate or [])):
            findings.append(_invalid_field(f'{location}/{key}', 'must contain distinct positive section numbers'))
            list_values[key] = []
        else:
            list_values[key] = candidate
            if any(item not in section_numbers for item in candidate):
                findings.append(_invalid_field(f'{location}/{key}', 'references a section outside the plan'))
    mapping_values: dict[str, dict[str, int]] = {}
    action_types = {item.value for item in CTAType}
    for key in ('ctas', 'next_actions'):
        candidate = value.get(key)
        if not isinstance(candidate, Mapping) or any(
            role not in action_types or not _is_positive_int(section)
            for role, section in candidate.items()
        ):
            findings.append(_invalid_field(f'{location}/{key}', 'must map supported action types to positive section numbers'))
            mapping_values[key] = {}
        else:
            mapping_values[key] = dict(candidate)
            if len(set(candidate.values())) != len(candidate):
                findings.append(_invalid_field(f'{location}/{key}', 'must use distinct section numbers'))
            if any(section not in section_numbers for section in candidate.values()):
                findings.append(_invalid_field(f'{location}/{key}', 'references a section outside the plan'))
    exception = value.get('cta_exception_reason')
    if exception is not None and (not isinstance(exception, str) or not exception.strip()):
        findings.append(_invalid_field(f'{location}/cta_exception_reason', 'must be null or a non-empty string'))

    expected_mini = sorted(
        row.get('section_number')
        for row in section_rows
        if row.get('mini_story') is True and _is_positive_int(row.get('section_number'))
    )
    expected_featured = sorted(
        row.get('section_number')
        for row in section_rows
        if row.get('featured_snippet') is True and _is_positive_int(row.get('section_number'))
    )
    expected_ctas = {
        str(row.get('cta')): row.get('section_number')
        for row in section_rows
        if row.get('cta') is not None and _is_positive_int(row.get('section_number'))
    }
    expected_next_actions = {
        str(row.get('next_action')): row.get('section_number')
        for row in section_rows
        if row.get('next_action') is not None and _is_positive_int(row.get('section_number'))
    }
    if (
        sorted(list_values.get('mini_stories', [])) != expected_mini
        or sorted(list_values.get('featured_snippets', [])) != expected_featured
        or mapping_values.get('ctas', {}) != expected_ctas
        or mapping_values.get('next_actions', {}) != expected_next_actions
    ):
        findings.append(
            _finding(
                'editorial_plan_engagement_mismatch',
                'Engagement-map assignments must match their section-level fields.',
                location,
                'Regenerate the engagement map and section assignments together.',
            )
        )
    return findings


def _check_section_mapping(
    value: Any,
    section_numbers: set[int],
    location: str,
) -> list[Finding]:
    if not isinstance(value, Mapping) or any(
        not isinstance(label, str)
        or not label.strip()
        or not _is_positive_int(section)
        or section not in section_numbers
        for label, section in value.items()
    ):
        return [_invalid_field(location, 'must map non-empty labels to valid section numbers')]
    return []


def _check_serp_strategy(value: Any) -> list[Finding]:
    location = '/serp_strategy'
    if not isinstance(value, Mapping):
        return [_invalid_field(location, 'must be an object')]
    findings = _unknown_fields(value, SERP_STRATEGY_FIELDS, location)
    for key in SERP_STRATEGY_FIELDS:
        if key not in value:
            findings.append(_invalid_field(f'{location}/{key}', 'is required'))
    if not isinstance(value.get('status'), str) or not str(value.get('status')).strip():
        findings.append(_invalid_field(f'{location}/status', 'must be a non-empty string'))
    for key in ('content_type', 'serp_features', 'serp_structure', 'competitor_gaps', 'exception_reasons'):
        if not isinstance(value.get(key), Mapping):
            findings.append(_invalid_field(f'{location}/{key}', 'must be an object'))
    decision_maps = [
        value.get(key)
        for key in ('serp_features', 'serp_structure', 'competitor_gaps')
    ]
    if value.get('status') == 'resolved' and not any(
        isinstance(row, Mapping) and bool(row) for row in decision_maps
    ):
        findings.append(_finding(
            'editorial_plan_serp_strategy_empty',
            'A resolved SERP strategy must contain at least one observed feature, structure, or gap decision.',
            location,
            'Map concrete decisions from the bound SERP evidence observations.',
        ))
    return findings


def _check_serp_strategy_evidence_binding(
    strategy: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> list[Finding]:
    observations = evidence.get('observations')
    if not isinstance(observations, Mapping):
        return []
    findings: list[Finding] = []
    content_type = strategy.get('content_type')
    observed_type = content_type.get('observed') if isinstance(content_type, Mapping) else None
    evidence_types = _casefolded_strings(observations.get('content_types'))
    if not isinstance(observed_type, str) or observed_type.casefold() not in evidence_types:
        findings.append(_finding(
            'editorial_plan_serp_decision_unbound',
            'The planned observed content type is not present in the bound SERP evidence.',
            '/serp_strategy/content_type/observed',
            'Regenerate the plan from the current SERP evidence.',
        ))
    mappings = (
        ('serp_features', 'serp_features'),
        ('serp_structure', 'must_have_sections'),
        ('competitor_gaps', 'competitor_gaps'),
    )
    for strategy_key, evidence_key in mappings:
        decisions = strategy.get(strategy_key)
        observed = _casefolded_strings(observations.get(evidence_key))
        if not isinstance(decisions, Mapping):
            continue
        for decision in decisions:
            if not isinstance(decision, str) or decision.casefold() not in observed:
                findings.append(_finding(
                    'editorial_plan_serp_decision_unbound',
                    f'SERP strategy decision is not traceable to evidence: {decision}.',
                    f'/serp_strategy/{strategy_key}',
                    'Use only decisions observed in the bound SERP artifact.',
                ))
    return findings


def _casefolded_strings(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {
        item.strip().casefold()
        for item in value
        if isinstance(item, str) and item.strip()
    }


def _check_original_contributions(value: Any) -> list[Finding]:
    location = '/original_contributions'
    if not isinstance(value, list) or not value:
        return [_invalid_field(location, 'must be a non-empty list')]
    findings: list[Finding] = []
    for index, row in enumerate(value):
        row_location = f'{location}/{index}'
        if not isinstance(row, Mapping):
            findings.append(_invalid_field(row_location, 'must be an object'))
            continue
        findings.extend(_unknown_fields(row, ORIGINAL_CONTRIBUTION_FIELDS, row_location))
        for key in ORIGINAL_CONTRIBUTION_FIELDS:
            _require_nonempty_string(row, key, findings, f'{row_location}/{key}')
    return findings


def _check_entity_map(value: Any) -> list[Finding]:
    location = '/entity_map'
    if not isinstance(value, Mapping):
        return [_invalid_field(location, 'must be an object')]
    findings = _unknown_fields(value, ENTITY_MAP_FIELDS, location)
    for role in ENTITY_MAP_FIELDS:
        findings.extend(_check_string_list(value.get(role), f'{location}/{role}', required=True))
    return findings


def _check_query_ownership(value: Any) -> list[Finding]:
    location = '/query_ownership'
    if not isinstance(value, Mapping):
        return [_invalid_field(location, 'must be an object')]
    findings = _unknown_fields(value, QUERY_OWNERSHIP_FIELDS, location)
    decision = value.get('decision')
    if decision not in {'clear', 'differentiated', 'blocked'}:
        findings.append(_invalid_field(f'{location}/decision', 'must be clear, differentiated, or blocked'))
    elif decision == 'blocked':
        findings.append(_finding(
            'editorial_plan_query_ownership_blocked',
            'A blocked query-ownership decision prevents readiness.',
            f'{location}/decision',
            'Differentiate the intent or choose a query the article can own.',
        ))
    _require_nonempty_string(value, 'rationale', findings, f'{location}/rationale')
    return findings


def _check_internal_link_plan(value: Any) -> list[Finding]:
    location = '/internal_link_plan'
    if not isinstance(value, list) or not value:
        return [_invalid_field(location, 'must be a non-empty list')]
    findings: list[Finding] = []
    has_down_funnel = False
    for index, row in enumerate(value):
        row_location = f'{location}/{index}'
        if not isinstance(row, Mapping):
            findings.append(_invalid_field(row_location, 'must be an object'))
            continue
        findings.extend(_unknown_fields(row, INTERNAL_LINK_FIELDS, row_location))
        for key in ('target', 'rationale'):
            _require_nonempty_string(row, key, findings, f'{row_location}/{key}')
        role = row.get('role')
        if role not in {'supporting', 'down_funnel'}:
            findings.append(_invalid_field(f'{row_location}/role', 'must be supporting or down_funnel'))
        target = row.get('target')
        if isinstance(target, str) and target.strip() and not _is_internal_link_target(target):
            findings.append(_finding(
                'editorial_plan_internal_link_external',
                'Editorial-plan internal-link targets must resolve to an owned site.',
                f'{row_location}/target',
                'Use a root-relative URL or an owned Simpro, ClockShark, or BigChange URL.',
            ))
        has_down_funnel = has_down_funnel or role == 'down_funnel'
    if not has_down_funnel:
        findings.append(_finding(
            'editorial_plan_down_funnel_link_missing',
            'Editorial plan requires an intent-appropriate down-funnel internal link.',
            location,
            'Map a relevant product, solution, feature, or industry next step.',
        ))
    return findings


def _check_faq_paa_policies(
    faq_value: Any,
    paa_value: Any,
    sections_value: Any,
) -> list[Finding]:
    findings: list[Finding] = []
    if not isinstance(faq_value, Mapping):
        findings.append(_invalid_field('/faq_policy', 'must be an object'))
        faq_value = {}
    else:
        findings.extend(_unknown_fields(faq_value, FAQ_POLICY_FIELDS, '/faq_policy'))
    status = faq_value.get('status')
    if status not in {'required', 'not_applicable'}:
        findings.append(_invalid_field('/faq_policy/status', 'must be required or not_applicable'))
    _require_nonempty_string(faq_value, 'rationale', findings, '/faq_policy/rationale')

    if not isinstance(paa_value, Mapping):
        findings.append(_invalid_field('/paa_policy', 'must be an object'))
        paa_value = {}
    else:
        findings.extend(_unknown_fields(paa_value, PAA_POLICY_FIELDS, '/paa_policy'))
    if paa_value.get('source_kind') not in {'answersocrates', 'brief_paa', 'user_csv'}:
        findings.append(_invalid_field('/paa_policy/source_kind', 'uses an unsupported source kind'))
    _require_nonempty_string(paa_value, 'query', findings, '/paa_policy/query')
    selected = paa_value.get('selected_questions')
    if not isinstance(selected, list) or any(
        not isinstance(question, str)
        or not question.strip()
        or not question.strip().endswith('?')
        for question in selected or []
    ):
        findings.append(_invalid_field('/paa_policy/selected_questions', 'must be a list of complete questions'))
        selected = []
    if (status == 'required' and not selected) or (status == 'not_applicable' and selected):
        findings.append(_finding(
            'editorial_plan_faq_paa_mismatch',
            'FAQ policy and selected PAA questions must agree.',
            '/faq_policy/status',
            'Select questions for a required FAQ or clear them when FAQ is not applicable.',
        ))
    faq_section_planned = bool(
        isinstance(sections_value, list)
        and any(
            isinstance(section, Mapping) and section.get('type') == SectionType.FAQ.value
            for section in sections_value
        )
    )
    if faq_section_planned != (status == 'required'):
        findings.append(_finding(
            'editorial_plan_faq_section_mismatch',
            'FAQ policy must match the presence of a planned FAQ section.',
            '/faq_policy/status',
            'Add the selected FAQ section or mark the FAQ not applicable.',
        ))
    return findings


def _check_final_article_bindings(
    plan: Mapping[str, Any],
    article_path: str | Path,
    *,
    assembly_date: str | None,
) -> list[Finding]:
    try:
        article = Path(article_path).read_text(encoding='utf-8')
    except (OSError, UnicodeError) as error:
        return [_finding(
            'editorial_plan_article_unreadable',
            f'Final article cannot be read for editorial-plan validation: {error}',
            '/',
            'Bind the current final article and rebuild the plan.',
        )]
    try:
        frontmatter, body, _ = split_frontmatter(article)
    except FrontmatterError as error:
        return [_finding(
            'editorial_plan_article_frontmatter_invalid',
            f'Final article frontmatter is invalid: {error}',
            '/last_updated',
            'Repair the article frontmatter before binding the editorial plan.',
        )]
    findings = _check_article_date_binding(
        plan,
        frontmatter,
        assembly_date=assembly_date,
    )
    headings = {
        match.group(1).strip().rstrip('#').strip().casefold()
        for match in re.finditer(r'^#{1,6}\s+(.+?)\s*$', body, re.MULTILINE)
    }
    section_text = _visible_sections_by_heading(body)
    contributions = plan.get('original_contributions')
    if isinstance(contributions, list):
        for index, row in enumerate(contributions):
            if isinstance(row, Mapping):
                section = row.get('final_section')
                if isinstance(section, str) and section.strip().casefold() not in headings:
                    findings.append(_finding(
                        'editorial_plan_original_contribution_unmapped',
                        'An original contribution is not mapped to a visible final heading.',
                        f'/original_contributions/{index}/final_section',
                        'Add the mapped section to the final article or update the plan.',
                    ))
                    continue
                evidence = row.get('visible_evidence')
                mapped_body = (
                    section_text.get(section.strip().casefold(), '')
                    if isinstance(section, str)
                    else ''
                )
                if (
                    not isinstance(evidence, str)
                    or len(evidence.split()) < 4
                    or _normalize_visible_text(evidence)
                    not in _normalize_visible_text(mapped_body)
                ):
                    findings.append(_finding(
                        'editorial_plan_original_contribution_evidence_missing',
                        'The planned original contribution is not visibly present in its mapped final section.',
                        f'/original_contributions/{index}/visible_evidence',
                        'Bind a substantive exact excerpt from the visible contribution in the mapped section.',
                    ))
    visible_body = _visible_article_text(body)
    entity_map = plan.get('entity_map')
    if isinstance(entity_map, Mapping):
        for role in ('primary', 'supporting'):
            entities = entity_map.get(role)
            if not isinstance(entities, list):
                continue
            for index, entity in enumerate(entities):
                if isinstance(entity, str) and not _contains_entity(visible_body, entity):
                    findings.append(_finding(
                        'editorial_plan_entity_missing',
                        f'Planned {role} entity is absent from the final article: {entity}.',
                        f'/entity_map/{role}/{index}',
                        'Cover the entity naturally or remove it from the final plan.',
                    ))
    links = plan.get('internal_link_plan')
    if isinstance(links, list):
        for index, row in enumerate(links):
            target = row.get('target') if isinstance(row, Mapping) else None
            if isinstance(target, str) and not _article_contains_link_target(body, target):
                findings.append(_finding(
                    'editorial_plan_internal_link_missing',
                    f'Planned internal link is absent from the final article: {target}.',
                    f'/internal_link_plan/{index}/target',
                    'Add the planned contextual link or update the final plan.',
                ))
    return findings


def _check_plan_assembly_date(
    plan: Mapping[str, Any],
    assembly_date: str | None,
) -> list[Finding]:
    if assembly_date is None:
        return []
    expected = _parse_iso_date(assembly_date)
    if expected is None:
        return [_finding(
            'editorial_plan_assembly_date_invalid',
            'Workflow assembly date must be a canonical ISO date in YYYY-MM-DD form.',
            '/assembly_date',
            'Pass the exact current assembly date to the editorial-plan guard.',
        )]
    planned = _parse_iso_date(plan.get('date'))
    if planned is not None and planned != expected:
        return [_finding(
            'editorial_plan_assembly_date_mismatch',
            'Editorial plan date must match the current workflow assembly date.',
            '/date',
            'Regenerate the editorial plan for the current assembly run.',
        )]
    return []


def _check_article_date_binding(
    plan: Mapping[str, Any],
    frontmatter: Mapping[str, Any],
    *,
    assembly_date: str | None,
) -> list[Finding]:
    raw_updated = frontmatter.get('last_updated')
    updated = _parse_iso_date(raw_updated)
    if updated is None:
        return [_finding(
            'editorial_plan_article_last_updated_invalid',
            'Final article last_updated must be a canonical ISO date in YYYY-MM-DD form.',
            '/last_updated',
            'Set last_updated to the current assembly date.',
        )]
    expected_dates = {
        candidate
        for candidate in (
            _parse_iso_date(plan.get('date')),
            _parse_iso_date(assembly_date),
        )
        if candidate is not None
    }
    if any(updated != expected for expected in expected_dates):
        return [_finding(
            'editorial_plan_article_date_mismatch',
            'Final article last_updated must match the editorial-plan and workflow assembly dates.',
            '/last_updated',
            'Update the article and rebuild the plan in one assembly run.',
        )]
    return []


def _visible_article_text(body: str) -> str:
    visible = re.sub(r'!\[[^\]]*\]\([^)]*\)', ' ', body)
    visible = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', visible)
    visible = re.sub(r'^\s*\[[^\]]+\]:\s*\S+.*$', ' ', visible, flags=re.MULTILINE)
    visible = re.sub(r'<(?:https?://|mailto:)[^>]+>', ' ', visible, flags=re.IGNORECASE)
    visible = re.sub(r'https?://\S+', ' ', visible, flags=re.IGNORECASE)
    visible = re.sub(r'<[^>]+>', ' ', visible)
    return re.sub(r'\s+', ' ', visible).casefold()


def _visible_sections_by_heading(body: str) -> dict[str, str]:
    lines = body.splitlines()
    headings: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        match = re.match(r'^(#{1,6})\s+(.+?)\s*$', line)
        if match:
            headings.append((index, len(match.group(1)), match.group(2).rstrip('#').strip()))
    sections: dict[str, str] = {}
    for heading_index, (line_index, level, heading) in enumerate(headings):
        end = len(lines)
        for next_line, next_level, _ in headings[heading_index + 1:]:
            if next_level <= level:
                end = next_line
                break
        key = heading.casefold()
        visible = _visible_article_text('\n'.join(lines[line_index + 1:end]))
        sections[key] = f"{sections.get(key, '')} {visible}".strip()
    return sections


def _normalize_visible_text(value: str) -> str:
    return _visible_article_text(value)


def _contains_entity(visible_body: str, entity: str) -> bool:
    normalized = re.sub(r'\s+', ' ', entity.strip()).casefold()
    if not normalized:
        return False
    pattern = re.escape(normalized).replace(r'\ ', r'\s+')
    return bool(re.search(rf'(?<!\w){pattern}(?!\w)', visible_body))


def _is_internal_link_target(target: str) -> bool:
    candidate = target.strip()
    parsed = urlparse(candidate)
    if parsed.scheme in {'http', 'https'}:
        hostname = (parsed.hostname or '').casefold().rstrip('.')
        return any(
            hostname == domain or hostname.endswith(f'.{domain}')
            for domain in OWNED_INTERNAL_DOMAINS
        )
    if parsed.scheme or parsed.netloc:
        return False
    return candidate.startswith('/') and not candidate.startswith('//')


def _article_contains_link_target(article: str, target: str) -> bool:
    escaped = re.escape(target.strip())
    return bool(re.search(rf'\]\(\s*{escaped}(?:\s+["\'][^"\']*["\'])?\s*\)', article) or re.search(rf'href\s*=\s*["\']{escaped}["\']', article, re.IGNORECASE))


def _nested_string(value: Mapping[str, Any], parent: str, key: str) -> str:
    row = value.get(parent)
    if not isinstance(row, Mapping):
        return ''
    candidate = row.get(key)
    return candidate.strip() if isinstance(candidate, str) else ''


def _rfc3339_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or RFC3339_UTC_RE.fullmatch(value) is None:
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + '+00:00')
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        return None
    return parsed


def _parse_iso_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _invalid_serp_field(location: str, requirement: str) -> Finding:
    return _finding(
        'serp_evidence_field_invalid',
        f'SERP evidence field {location} {requirement}.',
        location,
        'Regenerate the verified SERP evidence artifact.',
    )


def _check_string_list(value: Any, location: str, *, required: bool = False) -> list[Finding]:
    if not isinstance(value, list) or (required and not value) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        qualifier = 'non-empty ' if required else ''
        return [_invalid_field(location, f'must be a {qualifier}list of non-empty strings')]
    return []


def _unknown_fields(
    value: Mapping[str, Any],
    allowed: frozenset[str],
    parent_location: str,
) -> list[Finding]:
    return [
        _finding(
            'editorial_plan_unknown_field',
            f'Editorial plan contains unsupported field {key}.',
            f'{parent_location}/{key}',
            'Remove the field or update the editorial-plan schema deliberately.',
        )
        for key in sorted(set(value) - allowed)
    ]


def _require_nonempty_string(
    value: Mapping[str, Any],
    key: str,
    findings: list[Finding],
    location: str,
) -> None:
    candidate = value.get(key)
    if not isinstance(candidate, str) or not candidate.strip():
        findings.append(_invalid_field(location, 'must be a non-empty string'))


def _is_positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _invalid_field(location: str, requirement: str) -> Finding:
    return _finding(
        'editorial_plan_field_invalid',
        f'Editorial plan field {location} {requirement}.',
        location,
        'Regenerate the editorial plan from validated planner inputs.',
    )


def _finding(
    rule_id: str,
    message: str,
    location: str,
    suggestion: str,
) -> Finding:
    return {
        'severity': 'error',
        'rule_id': rule_id,
        'message': message,
        'suggestion': suggestion,
        'location': location,
    }


def _deduplicate(findings: list[Finding]) -> list[Finding]:
    unique: dict[tuple[str, str, str], Finding] = {}
    for finding in findings:
        key = (
            str(finding.get('rule_id') or ''),
            str(finding.get('location') or ''),
            str(finding.get('message') or ''),
        )
        unique[key] = finding
    return list(unique.values())


def _sorted_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(
        _deduplicate(findings),
        key=lambda finding: (
            str(finding.get('location') or ''),
            str(finding.get('rule_id') or ''),
            str(finding.get('message') or ''),
        ),
    )
