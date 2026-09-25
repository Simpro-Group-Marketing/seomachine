"""Focused aeo metadata schema scoring."""

from __future__ import annotations

from .aeo_text import _normalize_key
from collections.abc import Mapping
from data_sources.modules import blog_assembly_contract
from data_sources.modules.frontmatter import FrontmatterError
from data_sources.modules.frontmatter import split_frontmatter
from data_sources.modules.schema_item_list import inspect_item_list_schema
from data_sources.modules.video_embed import inspect_video_embeds
from datetime import date
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
import re

CANONICAL_SCHEMA_ENTITIES = frozenset(
    {
        "BlogPosting",
        "BreadcrumbList",
        "FAQPage",
        "Question and Answer inside FAQPage",
        "ImageObject for the featured image or logo",
        "Organization as publisher reference only, not a separate full schema block",
        "Person as author",
        "VideoObject",
    }
)

def _extract_structured_frontmatter(content: str) -> Dict[str, Any]:
    try:
        metadata, _body, _line = split_frontmatter(content)
    except FrontmatterError:
        return {}
    return dict(metadata)

def _check_metadata_quality(
    metadata: Dict[str, Any],
    *,
    finalized_bom: Optional[Mapping[str, Any]],
    assembly_date: Optional[str],
) -> Dict[str, Any]:
    normalized = {_normalize_key(str(key)): value for key, value in metadata.items()}
    has_author = bool(str(normalized.get('author') or '').strip())
    author_policy_status = _validated_bom_author_policy(finalized_bom)
    raw_updated = str(
        normalized.get('last_updated')
        or normalized.get('updated')
        or normalized.get('date_updated')
        or ''
    ).strip()
    bound_assembly_date = str(
        assembly_date or normalized.get('assembly_date') or ''
    ).strip()
    parsed_updated = _parse_canonical_iso_date(raw_updated)
    parsed_assembly = (
        _parse_canonical_iso_date(bound_assembly_date)
        if bound_assembly_date
        else None
    )
    if not raw_updated:
        freshness_status = 'missing'
    elif parsed_updated is None:
        freshness_status = 'invalid'
    elif bound_assembly_date and parsed_assembly is None:
        freshness_status = 'assembly_date_invalid'
    elif (
        parsed_assembly is not None
        and parsed_assembly > blog_assembly_contract.current_utc_date()
    ):
        freshness_status = 'assembly_date_future'
    elif parsed_assembly is not None and parsed_updated > parsed_assembly:
        freshness_status = 'future'
    elif parsed_assembly is None and parsed_updated > date.today():
        freshness_status = 'future'
    else:
        freshness_status = 'valid'
    passed = freshness_status == 'valid'
    return {
        'passed': passed,
        'issue': 'The draft is missing valid freshness metadata.',
        'fix': (
            'Use a canonical YYYY-MM-DD last_updated value that is not later '
            'than the bound assembly date. Author metadata is optional for '
            'no-author blog workflows.'
        ),
        'severity': 'high',
        'details': {
            'has_author': has_author,
            'has_last_updated': bool(raw_updated),
            'last_updated': raw_updated,
            'assembly_date': bound_assembly_date,
            'freshness_status': freshness_status,
            'author_policy_status': author_policy_status,
        },
    }

def _parse_canonical_iso_date(value: str) -> Optional[date]:
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None

def _validated_bom_author_policy(
    finalized_bom: Optional[Mapping[str, Any]],
) -> str:
    """Return the exact author state from a guard-validated strict BOM.

    Publish readiness calls this only after the BOM guard succeeds. Both
    provisional and final lifecycle states are accepted because preflight must
    score an optional-author article before the BOM can be finalized.
    """
    if not isinstance(finalized_bom, Mapping):
        return ''
    if finalized_bom.get('schema') not in {
        'simpro-blog-assembly-bom/v1',
        'simpro-blog-assembly-bom/v2',
        'simpro-blog-assembly-bom/v3',
    }:
        return ''
    if finalized_bom.get('lifecycle_state') not in {'provisional', 'final'}:
        return ''
    policy = finalized_bom.get('author_policy')
    if not isinstance(policy, Mapping):
        return ''
    required_keys = {
        'status',
        'name',
        'frontmatter_author_required',
        'schema_person_required',
        'named_author_voice_allowed',
    }
    if set(policy) != required_keys:
        return ''
    status = policy.get('status')
    if status not in {'named_author', 'no_author', 'not_provided'}:
        return ''
    named_author = status == 'named_author'
    name = str(policy.get('name') or '').strip()
    if named_author != bool(name):
        return ''
    for key in (
        'frontmatter_author_required',
        'schema_person_required',
        'named_author_voice_allowed',
    ):
        if policy.get(key) is not named_author:
            return ''
    return str(status)

def _check_author_voice(
    body: str,
    metadata: Dict[str, Any],
    *,
    finalized_bom: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    normalized = {_normalize_key(str(key)): value for key, value in metadata.items()}
    has_author = bool(str(normalized.get('author') or '').strip())
    policy_status = _validated_bom_author_policy(finalized_bom)
    searchable = re.sub(r'```.*?```', ' ', body, flags=re.DOTALL)
    visible_lines: List[str] = []
    for line in searchable.splitlines():
        stripped = line.lstrip()
        if stripped.startswith('>'):
            continue
        if stripped.startswith('#'):
            heading = re.sub(r'^#{1,6}\s*', '', stripped).strip()
            if heading.endswith('?'):
                continue
            visible_lines.append(heading)
            continue
        visible_lines.append(line)
    searchable = '\n'.join(visible_lines)
    searchable = re.sub(r'<blockquote\b.*?</blockquote>', ' ', searchable, flags=re.DOTALL | re.IGNORECASE)
    searchable = re.sub(r'\x22[^\x22]*\x22', ' ', searchable)
    searchable = re.sub(r'“[^”]*”|‘[^’]*’', ' ', searchable, flags=re.DOTALL)
    searchable = re.sub(r'https?://[^\s)>]+', ' ', searchable, flags=re.IGNORECASE)
    term_pattern = re.compile(
        r'\b(?:I|(?i:me|my|mine|myself))\b|\bI(?:\x27m|\x27ve|\x27d|\x27ll)\b',
    )
    first_person_terms = list(dict.fromkeys(term_pattern.findall(searchable)))
    passed = has_author or not first_person_terms
    return {
        'passed': passed,
        'issue': 'First-person singular author judgment appears without a named author.',
        'fix': (
            'Add a source-bound named author or rewrite first-person singular '
            'judgment in an attributed or neutral channel voice. Quoted source '
            'language may remain quoted.'
        ),
        'severity': 'high',
        'details': {
            'has_author': has_author,
            'author_policy_status': policy_status,
            'first_person_terms': first_person_terms,
        },
    }

def _check_schema(
    content: str,
    metadata: Dict[str, Any],
    *,
    visible_faq: bool,
    finalized_bom: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    supplied = _schema_entities(metadata.get("schema_notes"))
    entities = set(supplied)
    item_list = inspect_item_list_schema(supplied, metadata)
    required = {
        'BlogPosting',
        'BreadcrumbList',
        'ImageObject for the featured image or logo',
        'Organization as publisher reference only, not a separate full schema block',
    }
    unexpected: set[str] = set()
    normalized = {_normalize_key(str(key)): value for key, value in metadata.items()}
    has_author = bool(str(normalized.get('author') or '').strip())
    if has_author:
        required.add('Person as author')
    elif 'Person as author' in entities:
        unexpected.add('Person as author')
    if visible_faq:
        required.update({'FAQPage', 'Question and Answer inside FAQPage'})
    else:
        unexpected.update(entities.intersection({'FAQPage', 'Question and Answer inside FAQPage'}))
    video_inspection = inspect_video_embeds(content)
    has_supported_video_embed = video_inspection.has_supported_embed
    if has_supported_video_embed:
        required.add('VideoObject')
    elif 'VideoObject' in entities:
        unexpected.add('VideoObject')
    if item_list.note:
        required.add(item_list.note)
    missing = sorted(required - entities)
    allowed_entities = set(CANONICAL_SCHEMA_ENTITIES)
    if item_list.note:
        allowed_entities.add(item_list.note)
    unknown = sorted(entities - allowed_entities)
    passed = (
        not missing
        and not unexpected
        and not unknown
        and not item_list.errors
        and not video_inspection.errors
    )
    result = {
        'passed': passed,
        'issue': 'Schema notes do not match the exact conditional blog entity contract.',
        'fix': (
            'Use exact canonical schema entity names. Include FAQPage and its '
            'Question and Answer entity only with a visible FAQ, Person only '
            'with a named author, and VideoObject only with a supported embed.'
        ),
        'severity': 'high',
        'details': {
            'entities': sorted(entities),
            'missing_entities': missing,
            'unexpected_entities': sorted(unexpected),
            'unknown_entities': unknown,
            'has_supported_video_embed': has_supported_video_embed,
            'video_embed_errors': list(video_inspection.errors),
            'author_policy_status': _validated_bom_author_policy(finalized_bom),
        },
    }
    if item_list.active:
        result['details'].update(
            {
                'item_list_entry_count': len(item_list.entries),
                'item_list_errors': list(item_list.errors),
            }
        )
    return result


def _schema_entities(raw_entities: object) -> List[str]:
    if isinstance(raw_entities, list):
        return [str(value).strip() for value in raw_entities if str(value).strip()]
    if isinstance(raw_entities, str) and raw_entities.strip():
        return [value.strip() for value in raw_entities.split(";") if value.strip()]
    return []

def _has_supported_video_embed(content: str) -> bool:
    return inspect_video_embeds(content).has_supported_embed

def _check_faq_policy(status: str, *, visible_faq: bool) -> Dict[str, Any]:
    if status == 'not_applicable':
        passed = not visible_faq
        effective_status = status
    elif status == 'required':
        passed = visible_faq
        effective_status = status
    elif not status and visible_faq:
        passed = True
        effective_status = 'inferred_required'
    else:
        passed = False
        effective_status = status or 'missing'
    return {
        'passed': passed,
        'issue': 'The bound FAQ policy does not match visible FAQ content.',
        'fix': (
            'Use required when a visible FAQ is planned. Use not_applicable '
            'with a rationale only when the final article has no visible FAQ.'
        ),
        'severity': 'high',
        'details': {
            'policy_status': effective_status,
            'visible_faq': visible_faq,
        },
    }

def _not_applicable_check(check: Dict[str, Any], reason: str) -> Dict[str, Any]:
    result = dict(check)
    details = dict(result.get('details') or {})
    details['not_applicable_reason'] = reason
    result.update(
        {
            'passed': True,
            'applicable': False,
            'status': 'not_applicable',
            'details': details,
        }
    )
    return result

def _validated_non_connector_bom(finalized_bom: Optional[Mapping[str, Any]]) -> bool:
    if not isinstance(finalized_bom, Mapping):
        return False
    if finalized_bom.get("schema") not in {
        "simpro-blog-assembly-bom/v1",
        "simpro-blog-assembly-bom/v2",
        "simpro-blog-assembly-bom/v3",
    }:
        return False
    if finalized_bom.get("lifecycle_state") not in {"provisional", "final"}:
        return False
    binding = finalized_bom.get("connector_binding")
    return bool(
        isinstance(binding, Mapping)
        and binding.get("status") == "not_applicable"
        and binding.get("reason")
        == "Final article contains no Simpro brand, URL, or connector-sensitive language."
    )


__all__ = [
    "_extract_structured_frontmatter",
    "_check_metadata_quality",
    "_parse_canonical_iso_date",
    "_validated_bom_author_policy",
    "_check_author_voice",
    "_check_schema",
    "_has_supported_video_embed",
    "_check_faq_policy",
    "_not_applicable_check",
    "_validated_non_connector_bom",
]
