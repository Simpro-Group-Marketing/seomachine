"""Strict orchestration for one loaded editorial-plan value."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .contracts import EDITORIAL_PLAN_SCHEMA
from .contracts import TOP_LEVEL_FIELDS
from .contracts import Finding
from .contracts import _finding
from .contracts import _invalid_field
from .contracts import _is_positive_int
from .contracts import _parse_iso_date
from .contracts import _require_nonempty_string
from .contracts import _sorted_findings
from .contracts import _unknown_fields
from .dependencies import EditorialPlanDependencies
from .dependencies import default_editorial_plan_dependencies
from .field_validation import _check_audience_language_research
from .field_validation import _check_entity_map
from .field_validation import _check_keyword_decision
from .field_validation import _check_meta
from .field_validation import _check_original_contributions
from .field_validation import _check_query_ownership
from .field_validation import _check_reader_contract
from .field_validation import _check_rewrite_decisions
from .field_validation import _check_section_mapping
from .field_validation import _check_serp_strategy
from .final_article import _check_faq_paa_policies
from .link_policy import _check_internal_link_plan
from .link_policy import _check_link_policy_override_shape_with_dependencies
from .link_policy import _has_syntactic_link_policy_override
from .link_policy import _resolve_plan_brand
from .sections import _check_engagement_map
from .sections import _check_sections



def check_plan(
    value: Any,
    *,
    dependencies: EditorialPlanDependencies | None = None,
) -> list[Finding]:
    '''Return deterministic findings for one loaded editorial-plan value.'''
    dependencies = dependencies or default_editorial_plan_dependencies()
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
    plan_brand = _resolve_plan_brand(value)
    if 'brand' in value and plan_brand is None:
        findings.append(_invalid_field(
            '/brand',
            'must be AroFlo, BigChange, ClockShark, or Simpro',
        ))
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
    findings.extend(_check_keyword_decision(value.get('keyword_decision'), value.get('meta')))
    findings.extend(_check_original_contributions(value.get('original_contributions')))
    findings.extend(_check_entity_map(value.get('entity_map')))
    findings.extend(_check_query_ownership(value.get('query_ownership')))
    findings.extend(_check_rewrite_decisions(value.get('rewrite_decisions')))
    findings.extend(
        _check_audience_language_research(value.get('audience_language_research'))
    )
    findings.extend(_check_link_policy_override_shape_with_dependencies(
        value.get('link_policy_override'),
        dependencies,
    ))
    link_override_active = _has_syntactic_link_policy_override(
        value.get('link_policy_override'),
        dependencies=dependencies,
    )
    industry_link_required = (
        dependencies.resolve_required_industry_policy(
            plan=value,
            brand=plan_brand,
        )
        is not None
    )
    findings.extend(
        _check_internal_link_plan(
            value.get('internal_link_plan'),
            brand=plan_brand,
            suppress_down_funnel=link_override_active and not industry_link_required,
        )
    )
    findings.extend(
        dependencies.editorial_plan_industry_findings(
            value,
            brand=plan_brand,
        )
    )
    findings.extend(
        _check_faq_paa_policies(
            value.get('faq_policy'),
            value.get('paa_policy'),
            value.get('sections'),
        )
    )
    return _sorted_findings(findings)
