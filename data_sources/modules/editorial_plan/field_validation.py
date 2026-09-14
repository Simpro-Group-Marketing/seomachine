"""Strict validation for editorial-plan metadata and policy fields."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import re

from .contracts import AUDIENCE_LANGUAGE_RESEARCH_FIELDS
from .contracts import ENTITY_MAP_FIELDS
from .contracts import FUNNEL_STAGES
from .contracts import KEYWORD_DECISION_FIELDS
from .contracts import KEYWORD_DECISION_SCHEMA
from .contracts import META_FIELDS
from .contracts import ORIGINAL_CONTRIBUTION_FIELDS
from .contracts import QUERY_OWNERSHIP_FIELDS
from .contracts import READER_CONTRACT_FIELDS
from .contracts import REWRITE_DECISIONS_FIELDS
from .contracts import SERP_STRATEGY_FIELDS
from .contracts import Finding
from .contracts import _check_string_list
from .contracts import _finding
from .contracts import _invalid_field
from .contracts import _is_positive_int
from .contracts import _require_nonempty_string
from .contracts import _unknown_fields



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
    if value.get('funnel_stage') not in FUNNEL_STAGES:
        findings.append(_invalid_field(f'{location}/funnel_stage', 'uses an unsupported funnel stage'))
    findings.extend(_check_string_list(value.get('exclusions'), f'{location}/exclusions'))
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


def _check_keyword_decision(value: Any, meta: Any) -> list[Finding]:
    location = '/keyword_decision'
    if not isinstance(value, Mapping):
        return [_invalid_field(location, 'must be an object')]
    findings = _unknown_fields(value, KEYWORD_DECISION_FIELDS, location)
    for key in (
        'status',
        'artifact_schema',
        'source',
        'database',
        'selected_primary_keyword',
        'selection_rationale',
    ):
        _require_nonempty_string(value, key, findings, f'{location}/{key}')
    if value.get('status') != 'resolved':
        findings.append(_invalid_field(f'{location}/status', 'must be resolved'))
    if value.get('artifact_schema') != KEYWORD_DECISION_SCHEMA:
        findings.append(_invalid_field(
            f'{location}/artifact_schema',
            f'must be {KEYWORD_DECISION_SCHEMA}',
        ))
    if value.get('source') != 'semrush_connector':
        findings.append(_invalid_field(f'{location}/source', 'must be semrush_connector'))
    selected_secondary_findings = _check_string_list(
        value.get('selected_secondary_keywords'),
        f'{location}/selected_secondary_keywords',
    )
    findings.extend(selected_secondary_findings)
    if isinstance(meta, Mapping):
        meta_primary = meta.get('primary_keyword')
        selected_primary = value.get('selected_primary_keyword')
        if (
            isinstance(meta_primary, str)
            and isinstance(selected_primary, str)
            and _normalize_keyword(meta_primary) != _normalize_keyword(selected_primary)
        ):
            findings.append(_finding(
                'editorial_plan_keyword_decision_mismatch',
                'Editorial plan primary keyword must match the Semrush keyword decision.',
                f'{location}/selected_primary_keyword',
                'Regenerate the editorial plan from the current keyword decision artifact.',
            ))
        meta_secondary = meta.get('secondary_keywords')
        selected_secondary = value.get('selected_secondary_keywords')
        if (
            isinstance(meta_secondary, list)
            and isinstance(selected_secondary, list)
            and [_normalize_keyword(item) for item in meta_secondary if isinstance(item, str)]
            != [_normalize_keyword(item) for item in selected_secondary if isinstance(item, str)]
        ):
            findings.append(_finding(
                'editorial_plan_keyword_decision_mismatch',
                'Editorial plan secondary keywords must match the Semrush keyword decision.',
                f'{location}/selected_secondary_keywords',
                'Regenerate the editorial plan from the current keyword decision artifact.',
            ))
    return findings


def _normalize_keyword(value: str) -> str:
    return re.sub(r'\s+', ' ', value.strip()).casefold()


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





def _check_rewrite_decisions(value: Any) -> list[Finding]:
    if value is None:
        return []
    location = '/rewrite_decisions'
    if not isinstance(value, Mapping):
        return [_invalid_field(location, 'must be an object when present')]
    findings = _unknown_fields(value, REWRITE_DECISIONS_FIELDS, location)
    for key in REWRITE_DECISIONS_FIELDS:
        candidate = value.get(key)
        if not isinstance(candidate, list) or any(
            not isinstance(item, Mapping) or not str(item.get('decision') or item.get('item') or '').strip()
            for item in candidate
        ):
            findings.append(_invalid_field(f'{location}/{key}', 'must be a list of decision objects'))
    return findings


def _check_audience_language_research(value: Any) -> list[Finding]:
    if value is None:
        return []
    location = '/audience_language_research'
    if not isinstance(value, Mapping):
        return [_invalid_field(location, 'must be an object when present')]
    findings = _unknown_fields(value, AUDIENCE_LANGUAGE_RESEARCH_FIELDS, location)
    status = value.get('status')
    if status not in {'required', 'not_applicable'}:
        findings.append(_invalid_field(f'{location}/status', 'must be required or not_applicable'))
    _require_nonempty_string(value, 'rationale', findings, f'{location}/rationale')
    for key in ('source_urls', 'observations', 'intended_section_use'):
        candidate = value.get(key)
        if not isinstance(candidate, list) or any(
            not isinstance(item, str) or not item.strip() for item in candidate
        ):
            findings.append(_invalid_field(f'{location}/{key}', 'must be a list of non-empty strings'))
    return findings
