"""Validate editorial-plan sections and engagement assignments."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .contracts import CTA_TYPES
from .contracts import ENGAGEMENT_FIELDS
from .contracts import SECTION_FIELDS
from .contracts import SECTION_TYPES
from .contracts import Finding
from .contracts import _check_string_list
from .contracts import _finding
from .contracts import _invalid_field
from .contracts import _is_positive_int
from .contracts import _require_nonempty_string
from .contracts import _unknown_fields



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
    for index, row in enumerate(value):
        row_location = f'{location}/{index}'
        if not isinstance(row, Mapping):
            findings.append(_invalid_field(row_location, 'must be an object'))
            all_word_targets_valid = False
            continue
        rows.append(row)
        row_findings, number, word_target = _check_section_row(row, row_location)
        findings.extend(row_findings)
        if number is not None:
            numbers.append(number)
        if word_target is not None:
            word_total += word_target
        else:
            all_word_targets_valid = False
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


def _check_section_row(
    row: Mapping[str, Any],
    location: str,
) -> tuple[list[Finding], int | None, int | None]:
    findings = _unknown_fields(row, SECTION_FIELDS, location)
    number = row.get('section_number')
    if not _is_positive_int(number):
        findings.append(_invalid_field(
            f'{location}/section_number',
            'must be a positive integer',
        ))
        number = None
    word_target = row.get('word_target')
    if not _is_positive_int(word_target):
        findings.append(_invalid_field(
            f'{location}/word_target',
            'must be a positive integer',
        ))
        word_target = None
    findings.extend(_check_section_content(row, location))
    return findings, number, word_target


def _check_section_content(
    row: Mapping[str, Any],
    location: str,
) -> list[Finding]:
    findings: list[Finding] = []
    if row.get('type') not in SECTION_TYPES:
        findings.append(_invalid_field(f'{location}/type', 'uses an unsupported section type'))
    for key in ('heading', 'strategic_angle'):
        _require_nonempty_string(row, key, findings, f'{location}/{key}')
    hook = row.get('engagement_hook')
    if hook is not None and (not isinstance(hook, str) or not hook.strip()):
        findings.append(_invalid_field(f'{location}/engagement_hook', 'must be null or a non-empty string'))
    for key in ('knowledge_gaps', 'unique_data', 'internal_links'):
        findings.extend(_check_string_list(row.get(key), f'{location}/{key}'))
    for key in ('cta', 'next_action'):
        if row.get(key) is not None and row.get(key) not in CTA_TYPES:
            findings.append(_invalid_field(f'{location}/{key}', 'uses an unsupported action type'))
    for key in ('mini_story', 'featured_snippet'):
        if not isinstance(row.get(key), bool):
            findings.append(_invalid_field(f'{location}/{key}', 'must be a boolean'))
    return findings


def _check_engagement_map(
    value: Any,
    section_numbers: set[int],
    section_rows: list[Mapping[str, Any]],
) -> list[Finding]:
    location = '/engagement_map'
    if not isinstance(value, Mapping):
        return [_invalid_field(location, 'must be an object')]
    findings = _unknown_fields(value, ENGAGEMENT_FIELDS, location)
    list_values, list_findings = _engagement_lists(value, section_numbers)
    findings.extend(list_findings)
    mapping_values, mapping_findings = _engagement_mappings(value, section_numbers)
    findings.extend(mapping_findings)
    exception = value.get('cta_exception_reason')
    if exception is not None and (not isinstance(exception, str) or not exception.strip()):
        findings.append(_invalid_field(f'{location}/cta_exception_reason', 'must be null or a non-empty string'))

    expected = _expected_engagement(section_rows)
    actual = (
        sorted(list_values.get('mini_stories', [])),
        sorted(list_values.get('featured_snippets', [])),
        mapping_values.get('ctas', {}),
        mapping_values.get('next_actions', {}),
    )
    if actual != expected:
        findings.append(
            _finding(
                'editorial_plan_engagement_mismatch',
                'Engagement-map assignments must match their section-level fields.',
                location,
                'Regenerate the engagement map and section assignments together.',
            )
        )
    return findings


def _engagement_lists(
    value: Mapping[str, Any],
    section_numbers: set[int],
) -> tuple[dict[str, list[int]], list[Finding]]:
    resolved: dict[str, list[int]] = {}
    findings: list[Finding] = []
    for key in ('mini_stories', 'featured_snippets'):
        candidate = value.get(key)
        if not _valid_section_list(candidate):
            findings.append(_invalid_field(f'/engagement_map/{key}', 'must contain distinct positive section numbers'))
            resolved[key] = []
        else:
            resolved[key] = candidate
            if any(item not in section_numbers for item in candidate):
                findings.append(_invalid_field(f'/engagement_map/{key}', 'references a section outside the plan'))
    return resolved, findings


def _valid_section_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and all(_is_positive_int(item) for item in value)
        and len(value) == len(set(value))
    )


def _engagement_mappings(
    value: Mapping[str, Any],
    section_numbers: set[int],
) -> tuple[dict[str, dict[str, int]], list[Finding]]:
    resolved: dict[str, dict[str, int]] = {}
    findings: list[Finding] = []
    for key in ('ctas', 'next_actions'):
        candidate = value.get(key)
        if not _valid_action_mapping(candidate):
            findings.append(_invalid_field(f'/engagement_map/{key}', 'must map supported action types to positive section numbers'))
            resolved[key] = {}
            continue
        resolved[key] = dict(candidate)
        if len(set(candidate.values())) != len(candidate):
            findings.append(_invalid_field(f'/engagement_map/{key}', 'must use distinct section numbers'))
        if any(section not in section_numbers for section in candidate.values()):
            findings.append(_invalid_field(f'/engagement_map/{key}', 'references a section outside the plan'))
    return resolved, findings


def _valid_action_mapping(value: Any) -> bool:
    return isinstance(value, Mapping) and all(
        role in CTA_TYPES and _is_positive_int(section)
        for role, section in value.items()
    )


def _expected_engagement(
    section_rows: list[Mapping[str, Any]],
) -> tuple[list[int], list[int], dict[str, int], dict[str, int]]:
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
    return expected_mini, expected_featured, expected_ctas, expected_next_actions
