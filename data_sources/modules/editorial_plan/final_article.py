"""Validate FAQ policy and bind a plan to the final visible article."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
import re

from ..frontmatter import FrontmatterError
from ..publishable_markdown import metadata_path_tail
from ..publishable_markdown import resolve_slug_aliases
from .contracts import FAQ_POLICY_FIELDS
from .contracts import FAQ_SECTION_TYPE
from .contracts import PAA_POLICY_FIELDS
from .contracts import Finding
from .contracts import _finding
from .contracts import _invalid_field
from .contracts import _parse_iso_date
from .contracts import _require_nonempty_string
from .contracts import _unknown_fields
from .dependencies import EditorialPlanDependencies
from .dependencies import default_editorial_plan_dependencies
from .snapshot_adapters import final_article_content
from .text import _contains_entity
from .text import _normalize_visible_text
from .text import _visible_article_text
from .text import _visible_sections_by_heading
from .v2 import EDITORIAL_PLAN_SCHEMA_V2



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
            isinstance(section, Mapping) and section.get('type') == FAQ_SECTION_TYPE
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
    article_path: str | Path | None,
    *,
    assembly_date: str | None,
    article_content: str | None = None,
    dependencies: EditorialPlanDependencies | None = None,
) -> list[Finding]:
    dependencies = dependencies or default_editorial_plan_dependencies()
    article, load_error = final_article_content(
        article_path,
        article_content,
    )
    if load_error is not None:
        return [load_error]
    try:
        frontmatter, body, _ = dependencies.split_frontmatter(article)
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
    headings, section_text = _article_structure(body)
    if plan.get('schema') == EDITORIAL_PLAN_SCHEMA_V2:
        findings.extend(_check_v2_metadata_binding(plan, frontmatter, body))
    else:
        findings.extend(_contribution_findings(
            plan.get('original_contributions'),
            headings,
            section_text,
        ))
    findings.extend(_entity_findings(plan.get('entity_map'), body))
    findings.extend(_link_findings(plan.get('internal_link_plan'), body))
    return findings


def _check_v2_metadata_binding(
    plan: Mapping[str, Any],
    frontmatter: Mapping[str, Any],
    body: str,
) -> list[Finding]:
    meta = plan.get('meta')
    if not isinstance(meta, Mapping):
        return []
    findings: list[Finding] = []
    title_options = meta.get('title_options') if isinstance(meta.get('title_options'), list) else []
    h1_match = re.search(r'^#(?!#)\s+(.+?)\s*$', body, re.MULTILINE)
    article_title = frontmatter.get('title')
    h1 = h1_match.group(1).strip() if h1_match else ''
    for location, value in (('/title', article_title), ('/h1', h1)):
        if value not in title_options:
            findings.append(_metadata_mismatch(
                location,
                'Final title and H1 must each match one planned title option.',
            ))
    for key in ('meta_title', 'meta_description'):
        if frontmatter.get(key) != meta.get(key):
            findings.append(_metadata_mismatch(
                f'/{key}',
                f'Final {key} must exactly match the editorial plan.',
            ))
    for key in ('primary_keyword', 'secondary_keywords'):
        if _normalized_metadata(frontmatter.get(key)) != _normalized_metadata(meta.get(key)):
            findings.append(_metadata_mismatch(
                f'/{key}',
                f'Final {key} must match the editorial plan after normalization.',
            ))
    slug, conflicts = resolve_slug_aliases(frontmatter)
    if conflicts:
        findings.append(_finding(
            'editorial_plan_slug_alias_conflict',
            f'Final article contains conflicting slug aliases: {", ".join(conflicts)}.',
            '/url_slug',
            'Keep one canonical URL slug or make every legacy alias resolve to it.',
        ))
    planned_slug = metadata_path_tail(str(meta.get('url_slug') or '')).casefold()
    actual_slug = metadata_path_tail(slug).casefold()
    if not actual_slug or actual_slug != planned_slug:
        findings.append(_metadata_mismatch(
            '/url_slug',
            'Final URL slug must match the canonical planned url_slug.',
        ))
    return findings


def _normalized_metadata(value: Any) -> tuple[str, ...]:
    values = value if isinstance(value, list) else [value]
    return tuple(
        re.sub(r'\s+', ' ', str(item).strip()).casefold()
        for item in values
        if item is not None and str(item).strip()
    )


def _metadata_mismatch(location: str, message: str) -> Finding:
    return _finding(
        'editorial_plan_metadata_mismatch',
        message,
        location,
        'Regenerate the article from the frozen editorial plan.',
    )


def _article_structure(body: str) -> tuple[set[str], dict[str, str]]:
    headings = {
        match.group(1).strip().rstrip('#').strip().casefold()
        for match in re.finditer(r'^#{1,6}\s+(.+?)\s*$', body, re.MULTILINE)
    }
    return headings, _visible_sections_by_heading(body)


def _contribution_findings(
    contributions: Any,
    headings: set[str],
    section_text: Mapping[str, str],
) -> list[Finding]:
    if not isinstance(contributions, list):
        return []
    findings: list[Finding] = []
    for index, row in enumerate(contributions):
        if isinstance(row, Mapping):
            findings.extend(_contribution_row_findings(
                row,
                index,
                headings,
                section_text,
            ))
    return findings


def _contribution_row_findings(
    row: Mapping[str, Any],
    index: int,
    headings: set[str],
    section_text: Mapping[str, str],
) -> list[Finding]:
    section = row.get('final_section')
    if isinstance(section, str) and section.strip().casefold() not in headings:
        return [_finding(
            'editorial_plan_original_contribution_unmapped',
            'An original contribution is not mapped to a visible final heading.',
            f'/original_contributions/{index}/final_section',
            'Add the mapped section to the final article or update the plan.',
        )]
    evidence = row.get('visible_evidence')
    mapped_body = section_text.get(section.strip().casefold(), '') if isinstance(section, str) else ''
    if _valid_visible_evidence(evidence, mapped_body):
        return []
    return [_finding(
        'editorial_plan_original_contribution_evidence_missing',
        'The planned original contribution is not visibly present in its mapped final section.',
        f'/original_contributions/{index}/visible_evidence',
        'Bind a substantive exact excerpt from the visible contribution in the mapped section.',
    )]


def _valid_visible_evidence(evidence: Any, mapped_body: str) -> bool:
    return (
        isinstance(evidence, str)
        and len(evidence.split()) >= 4
        and _normalize_visible_text(evidence) in _normalize_visible_text(mapped_body)
    )


def _entity_findings(entity_map: Any, body: str) -> list[Finding]:
    findings: list[Finding] = []
    visible_body = _visible_article_text(body)
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
    return findings


def _link_findings(links: Any, body: str) -> list[Finding]:
    findings: list[Finding] = []
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
    if any(updated > expected for expected in expected_dates):
        return [_finding(
            'editorial_plan_article_date_mismatch',
            'Final article last_updated cannot be later than the editorial-plan or workflow assembly dates.',
            '/last_updated',
            'Update the article date only after a real CMS update date exists, then rebuild the plan in one assembly run.',
        )]
    return []


def _article_contains_link_target(article: str, target: str) -> bool:
    escaped = re.escape(target.strip())
    markdown = rf'\]\(\s*{escaped}(?:\s+["\'][^"\']*["\'])?\s*\)'
    html = rf'href\s*=\s*["\']{escaped}["\']'
    return bool(re.search(markdown, article) or re.search(html, article, re.IGNORECASE))
