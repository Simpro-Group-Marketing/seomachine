"""
AEO/GEO Rater

Scores blog drafts for answer engine optimization and generative engine
optimization readiness. The score is out of 100; drafts should score 90+
before they are treated as publish-ready for AEO/GEO.
"""

import json
import re
from collections.abc import Mapping, Sequence
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

try:
    from . import blog_assembly_contract
    from .customer_proof_evidence import verify_selector_evidence_roles
    from .faq_answer_quality_guard import check_content as check_faq_answer_quality
    from .faq_proof_guard import check_content as check_faq_proof
    from .faq_structure import detect_faq_structure, is_faq_h2
    from .frontmatter import FrontmatterError, split_frontmatter
    from .image_placeholder import is_production_image_placeholder_line
    from .paa_provenance_guard import check_content as check_paa_provenance_content
    from .readiness_gate_context import trusted_readiness_findings
    from .schema_item_list import inspect_item_list_schema
    from .video_embed import inspect_video_embeds
except ImportError:
    import blog_assembly_contract
    from customer_proof_evidence import verify_selector_evidence_roles
    from faq_answer_quality_guard import check_content as check_faq_answer_quality
    from faq_proof_guard import check_content as check_faq_proof
    from faq_structure import detect_faq_structure, is_faq_h2
    from frontmatter import FrontmatterError, split_frontmatter
    from image_placeholder import is_production_image_placeholder_line
    from paa_provenance_guard import check_content as check_paa_provenance_content
    from readiness_gate_context import trusted_readiness_findings
    from schema_item_list import inspect_item_list_schema
    from video_embed import inspect_video_embeds


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


def _findings_passed(findings: Sequence[Mapping[str, Any]]) -> bool:
    return not any(
        str(finding.get("severity", "error")).casefold() == "error"
        for finding in findings
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


CANONICAL_SCHEMA_ENTITIES = frozenset(
    {
        'BlogPosting',
        'BreadcrumbList',
        'FAQPage',
        'Question and Answer inside FAQPage',
        'ImageObject for the featured image or logo',
        'Organization as publisher reference only, not a separate full schema block',
        'Person as author',
        'VideoObject',
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
        and parsed_assembly != blog_assembly_contract.current_utc_date()
    ):
        freshness_status = 'assembly_date_not_current'
    elif parsed_assembly is not None and parsed_updated != parsed_assembly:
        freshness_status = 'assembly_date_mismatch'
    elif parsed_assembly is None and parsed_updated > date.today():
        freshness_status = 'future'
    else:
        freshness_status = 'valid'
    passed = freshness_status == 'valid'
    return {
        'passed': passed,
        'issue': 'The draft is missing valid freshness metadata.',
        'fix': (
            'Use a canonical YYYY-MM-DD last_updated value matching the bound '
            'assembly date when one is provided. Author metadata is optional '
            'for no-author blog workflows.'
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
    raw_entities = metadata.get('schema_notes')
    if isinstance(raw_entities, list):
        supplied = [str(value).strip() for value in raw_entities if str(value).strip()]
    elif isinstance(raw_entities, str) and raw_entities.strip():
        supplied = [
            value.strip()
            for value in raw_entities.split(';')
            if value.strip()
        ]
    else:
        supplied = []
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


def _check_bound_paa_provenance(
    content: str,
    source_path: Optional[str],
    proof_sidecar_content: Optional[str],
    *,
    workflow_mode: str,
    content_brief: Optional[str],
    answersocrates_blocker: Optional[str],
    expected_query: Optional[str],
    expected_collection_date: Optional[str],
    paa_artifact: Optional[str],
    prevalidated_findings: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    findings = (
        [dict(finding) for finding in prevalidated_findings]
        if prevalidated_findings is not None
        else check_paa_provenance_content(
            content,
            source_path=source_path,
            proof_content=proof_sidecar_content,
            workflow_mode=workflow_mode,
            content_brief=content_brief,
            answersocrates_blocker=answersocrates_blocker,
            expected_query=expected_query,
            expected_collection_date=expected_collection_date,
            paa_artifact=paa_artifact,
        )
    )
    return {
        'passed': _findings_passed(findings),
        'issue': 'PAA provenance does not match the bound workflow, query, or date.',
        'fix': (
            'Pass the BOM-bound workflow mode, exact query, assembly collection '
            'date, and primary PAA artifact into the AEO rater.'
        ),
        'severity': 'high',
        'details': {
            'finding_count': len(findings),
            'findings': findings,
            'prevalidated': prevalidated_findings is not None,
        },
    }


def _check_external_source_diagnostic(content: str) -> Dict[str, Any]:
    links = re.findall(r'\[[^\]]+\]\((https?://[^)]+)\)', content)
    return {
        'passed': True,
        'applicable': False,
        'status': 'not_applicable',
        'issue': (
            'External link totals are diagnostic in AEO scoring; release policy '
            'still uses a 2 distinct non-owned authority source baseline.'
        ),
        'fix': (
            'Use 2 distinct non-owned authority sources as the standard-post '
            'baseline. Add further claim-fit sources whenever evidence requires '
            'them, add no quota-only third source, and apply no maximum to '
            'required evidence.'
        ),
        'severity': 'info',
        'details': {
            'external_link_count': len(links),
            'external_links': links,
            'reason': (
                'AEO fixed source-count scoring is disabled; release link policy '
                'owns the baseline and claim-level proof gates own additions.'
            ),
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


def _extract_frontmatter(content: str) -> Dict[str, str]:
    match = re.match(r"\A---\s*\n(.*?)\n---\s*", content, re.DOTALL)
    if not match:
        return {}

    metadata = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[_normalize_key(key)] = value.strip().strip('"')
    return metadata


def _normalize_key(key: str) -> str:
    return key.strip().lower().replace(" ", "_").replace("-", "_")


def _strip_frontmatter(content: str) -> str:
    return re.sub(r"\A---\s*\n.*?\n---\s*", "", content, flags=re.DOTALL).strip()


def _plain_text(markdown: str) -> str:
    text = re.sub(r"```.*?```", "", markdown, flags=re.DOTALL)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_`>]", "", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    return text.strip()


def _extract_markdown_links(content: str) -> List[Tuple[str, str]]:
    return [
        (match.group(1).strip(), match.group(2).strip())
        for match in re.finditer(r"\[([^\]]+)\]\((https?://[^)]+)\)", content)
    ]


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def _sentences(text: str) -> List[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text.strip())
        if sentence.strip()
    ]


def _first_body_paragraph(body: str) -> str:
    lines = body.splitlines()
    paragraphs = []
    current = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if is_production_image_placeholder_line(stripped):
            continue
        if (
            stripped.startswith("#")
            or stripped.startswith(">")
            or stripped.startswith("- ")
        ):
            continue
        current.append(stripped)

    if current:
        paragraphs.append(" ".join(current))

    return paragraphs[0] if paragraphs else ""


def _check_direct_answer(body: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    paragraph = _first_body_paragraph(body)
    first_two = " ".join(_sentences(paragraph)[:2])
    text_lower = _plain_text(first_two).lower().strip()
    primary_keyword = str(metadata.get("primary_keyword", "")).lower().strip()
    main_question = str(metadata.get("main_question", "")).lower().strip()
    topic = str(metadata.get("topic", "")).lower().strip()
    targets = []
    declarative_targets = []
    for target in [primary_keyword, main_question, topic]:
        if not target:
            continue
        targets.append(target)
        definition_match = re.fullmatch(r"what\s+(is|are)\s+(.+?)\??", target)
        if definition_match:
            verb, subject = definition_match.groups()
            declarative_targets.append(f"{subject.strip()} {verb}")

    includes_target = any(
        _contains_ordered_target(text_lower, target)
        for target in targets
    ) or any(
        re.match(rf"^{re.escape(target)}\b", text_lower)
        for target in declarative_targets
    )
    concise = 12 <= _word_count(first_two) <= 90
    answer_like = bool(
        re.search(
            r"\b(is|are|helps|means|should|gives|reduces|connects|provides|allows|enables)\b",
            text_lower,
        )
    )

    passed = bool(first_two and includes_target and concise and answer_like)
    return {
        "passed": passed,
        "issue": "The article does not directly answer the target query in the first 1-2 sentences.",
        "fix": "Start with a concise answer that names the target query or primary keyword before the hook.",
        "severity": "high",
        "details": {
            "first_two_sentences": first_two,
            "word_count": _word_count(first_two),
            "includes_target": includes_target,
        },
    }


def _extract_h2_sections(body: str) -> List[Tuple[str, str]]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", body, re.MULTILINE))
    sections = []

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections.append((match.group(1).strip(), body[start:end].strip()))

    return sections


def _first_paragraph(section_body: str) -> str:
    lines = section_body.splitlines()
    current = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                break
            continue
        if (
            stripped.startswith("#")
            or stripped.startswith(">")
            or stripped.startswith("- ")
        ):
            continue
        current.append(stripped)

    return " ".join(current)


def _is_capsule(paragraph: str) -> bool:
    words = _word_count(_plain_text(paragraph))
    if words < 50 or words > 60:
        return False
    sentences = _sentences(_plain_text(paragraph))
    return 2 <= len(sentences) <= 4


def _check_capsule_coverage(body: str) -> Dict[str, Any]:
    sections = [
        (heading, section)
        for heading, section in _extract_h2_sections(body)
        if not is_faq_h2(f"## {heading}")
    ]
    h2_count = len(sections)
    capsule_count = sum(
        1 for _, section in sections if _is_capsule(_first_paragraph(section))
    )
    coverage = capsule_count / h2_count if h2_count else 0
    passed = h2_count > 0 and coverage >= 0.60

    return {
        "passed": passed,
        "issue": "Fewer than 60% of major H2 sections have 50-60 word direct-answer capsules.",
        "fix": "Add a 50-60 word direct-answer paragraph immediately below the H1 and at least 60% of major H2s.",
        "severity": "high",
        "details": {
            "h2_count": h2_count,
            "capsule_count": capsule_count,
            "coverage": round(coverage, 2),
        },
    }


def _extract_faq_questions(body: str) -> List[Tuple[str, str]]:
    return [
        (entry.question, entry.answer)
        for entry in detect_faq_structure(body).entries
    ]


def _check_faq_structure(body: str) -> Dict[str, Any]:
    structure = detect_faq_structure(body)
    passed = not structure.unsupported_lines
    return {
        "passed": passed,
        "issue": "FAQ-like question markup uses an unsupported structure.",
        "fix": "Use a recognized FAQ H2 followed by H3-H5 question headings.",
        "severity": "high",
        "details": {
            "heading_present": structure.heading_present,
            "unsupported_lines": list(structure.unsupported_lines),
        },
    }


def _check_faq_questions(body: str) -> Dict[str, Any]:
    questions = _extract_faq_questions(body)
    question_count = len(questions)
    passed = question_count > 0

    return {
        "passed": passed,
        "issue": "The selected FAQ/PAA section has no natural-language question headings.",
        "fix": "Use the useful complete questions selected by the bound PAA policy, without a fixed count.",
        "severity": "high",
        "details": {
            "question_count": question_count,
            "questions": [question for question, _ in questions],
        },
    }


def _check_faq_answer_lengths(body: str) -> Dict[str, Any]:
    questions = _extract_faq_questions(body)
    lengths = []
    failing = []

    for question, answer_body in questions:
        paragraph = _first_paragraph(answer_body)
        words = _word_count(_plain_text(paragraph))
        lengths.append({"question": question, "words": words})
        if words < 40 or words > 60:
            failing.append({"question": question, "words": words})

    passed = bool(questions) and not failing
    return {
        "passed": passed,
        "issue": "One or more FAQ answers is outside the 40-60 word AEO snippet range.",
        "fix": "Rewrite each FAQ answer as a 40-60 word direct answer, then add context after it if needed.",
        "severity": "medium",
        "details": {
            "answer_lengths": lengths,
            "failing_answers": failing,
        },
    }


def _check_faq_answer_quality(
    content: str,
    *,
    prevalidated_findings: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    findings = (
        [dict(finding) for finding in prevalidated_findings]
        if prevalidated_findings is not None
        else check_faq_answer_quality(content)
    )
    passed = _findings_passed(findings)

    return {
        "passed": passed,
        "issue": "One or more FAQ answers opens with a generic non-answer.",
        "fix": (
            "Lead with a supported number or range, named recommendation, "
            "definition, concrete action, or explained yes/no answer. Move "
            "limitations after the direct answer."
        ),
        "severity": "high",
        "details": {
            "finding_count": len(findings),
            "findings": findings,
            "prevalidated": prevalidated_findings is not None,
        },
    }


def _check_faq_proof(
    content: str,
    proof_sidecar_content: Optional[str],
    *,
    prevalidated_findings: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    findings = (
        [dict(finding) for finding in prevalidated_findings]
        if prevalidated_findings is not None
        else check_faq_proof(content, proof_content=proof_sidecar_content or None)
    )
    passed = _findings_passed(findings)

    return {
        "passed": passed,
        "issue": (
            "One or more FAQ answers does not satisfy its machine-assigned "
            "citation mode."
        ),
        "fix": (
            "Resolve each finding according to its machine-assigned citation_mode. "
            "For inline_required, add a natural descriptive anchor to an "
            "authoritative non-owned source in the first visible answer paragraph "
            "and map it in the FAQ Proof Map. For section_source_allowed, "
            "sidecar_only, or proof_not_required, satisfy the assigned mode without "
            "quota-only links; a sidecar cannot replace inline evidence when "
            "inline_required applies."
        ),
        "severity": "high",
        "details": {
            "finding_count": len(findings),
            "findings": findings,
            "prevalidated": prevalidated_findings is not None,
        },
    }


def _check_paa_provenance(
    content: str,
    source_path: Optional[str],
    proof_sidecar_content: Optional[str],
    *,
    workflow_mode: str = "new",
    content_brief: Optional[str] = None,
    answersocrates_blocker: Optional[str] = None,
    expected_query: Optional[str] = None,
    expected_collection_date: Optional[str] = None,
    paa_artifact: Optional[str] = None,
) -> Dict[str, Any]:
    return _check_bound_paa_provenance(
        content,
        source_path,
        proof_sidecar_content,
        workflow_mode=workflow_mode,
        content_brief=content_brief,
        answersocrates_blocker=answersocrates_blocker,
        expected_query=expected_query,
        expected_collection_date=expected_collection_date,
        paa_artifact=paa_artifact,
    )


def _check_external_sources(content: str) -> Dict[str, Any]:
    return _check_external_source_diagnostic(content)


def _check_metadata(
    metadata: Dict[str, Any],
    *,
    finalized_bom: Optional[Mapping[str, Any]] = None,
    assembly_date: Optional[str] = None,
) -> Dict[str, Any]:
    return _check_metadata_quality(
        metadata,
        finalized_bom=finalized_bom,
        assembly_date=assembly_date,
    )


def _check_eeat_proof(
    content: str,
    body: str,
    metadata: Dict[str, Any],
    proof_sidecar_content: Optional[str] = None,
    proof_sidecar_path: Optional[str] = None,
) -> Dict[str, Any]:
    links = _extract_markdown_links(content)
    normalized = {_normalize_key(str(key)): value for key, value in metadata.items()}

    case_study_links = [url for _, url in links if _is_case_study_link(url)]
    review_site_links = [url for _, url in links if _is_review_site_link(url)]
    simpro_product_links = [
        url for _, url in links if _is_simpro_product_or_workflow_link(url)
    ]
    clockshark_workflow_links = [
        url for _, url in links if _is_clockshark_product_or_workflow_link(url)
    ]

    experience_signals = []
    validated_customer_experience = _validated_customer_experience_binding(
        content,
        proof_sidecar_content,
        proof_sidecar_path,
    )
    if validated_customer_experience:
        experience_signals.append("validated_customer_experience")
    has_documented_no_fit_boundary = _has_documented_no_fit_experience_boundary(
        proof_sidecar_content,
        proof_sidecar_path=proof_sidecar_path,
    )
    if has_documented_no_fit_boundary:
        experience_signals.append("documented_no_fit_experience_boundary")

    expertise_signals = []
    if normalized.get("author"):
        expertise_signals.append("author_metadata")
    if _has_expert_quote(body):
        expertise_signals.append("expert_quote")
    if _has_valid_fred_authority_expertise(body, proof_sidecar_content):
        expertise_signals.append("fred_authority")

    has_experience = bool(experience_signals)
    has_expertise = bool(expertise_signals)
    passed = has_experience

    return {
        "passed": passed,
        "issue": "The draft is missing required first-hand experience proof.",
        "fix": (
            "Use a hash-verified customer-proof selector experience_story binding, "
            "an approved Selected Customer Proof Mining record, and the selected "
            "identity and public URL in the same visible article paragraph. A bare "
            "case-study link or self-asserted proof label does not establish Experience. "
            "If no story fits, document a substantive "
            "First-hand evidence decision with Selected: [none] in the E-E-A-T "
            "Proof Map and a matching experience_story slate row with rejected-"
            "candidate reasons. Generic review-site experience evidence "
            "and VoC themes are research inputs, not E-E-A-T story proof. Named "
            "authors and receipt-approved Fred authority are optional positive "
            "expertise signals, not required AEO pass conditions. A bare owned "
            "product link does not establish Expertise."
        ),
        "severity": "high",
        "details": {
            "case_study_links": case_study_links,
            "review_site_links": review_site_links,
            "simpro_product_links": simpro_product_links,
            "clockshark_workflow_links": clockshark_workflow_links,
            "experience_signals": experience_signals,
            "expertise_signals": expertise_signals,
            "has_experience": has_experience,
            "has_expertise": has_expertise,
            "has_review_story_selection": False,
            "validated_customer_experience": validated_customer_experience,
            "has_documented_no_fit_boundary": has_documented_no_fit_boundary,
        },
    }


def _contains_ordered_target(text: str, target: str, *, max_gap_words: int = 2) -> bool:
    text_tokens = re.findall(r"[a-z0-9]+", text.casefold())
    target_tokens = re.findall(r"[a-z0-9]+", target.casefold())
    if not target_tokens:
        return False

    for start, token in enumerate(text_tokens):
        if token != target_tokens[0]:
            continue
        position = start
        inserted = 0
        for expected in target_tokens[1:]:
            position += 1
            while position < len(text_tokens) and text_tokens[position] != expected:
                inserted += 1
                if inserted > max_gap_words:
                    break
                position += 1
            if inserted > max_gap_words or position >= len(text_tokens):
                break
        else:
            return True
    return False


def _validated_non_connector_bom(finalized_bom: Optional[Mapping[str, Any]]) -> bool:
    if not isinstance(finalized_bom, Mapping):
        return False
    if finalized_bom.get("schema") not in {
        "simpro-blog-assembly-bom/v1",
        "simpro-blog-assembly-bom/v2",
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


def _is_review_site_link(url: str) -> bool:
    lower = url.lower()
    review_domains = (
        "g2.com",
        "capterra.com",
        "softwareadvice.com",
        "getapp.com",
        "trustradius.com",
        "gartner.com",
        "gartnerdigitalmarkets.com",
        "trustpilot.com",
        "apps.apple.com",
        "play.google.com",
    )
    return any(domain in lower for domain in review_domains)


def _is_case_study_link(url: str) -> bool:
    lower = url.lower()
    return bool(
        re.search(r"/case-stud(?:y|ies)/", lower) or "/resources/case-study-" in lower
    )


def _is_simpro_product_or_workflow_link(url: str) -> bool:
    lower = url.lower()
    if "simprogroup.com" not in lower:
        return False

    product_paths = (
        "/features/",
        "/solutions/",
        "/industries/",
        "/product/",
        "/products/",
        "/tour/",
    )
    return any(path in lower for path in product_paths)


def _is_clockshark_product_or_workflow_link(url: str) -> bool:
    lower = url.lower()
    if "clockshark.com" not in lower:
        return False

    workflow_paths = (
        "/industries/",
        "/tour/",
        "/blog/",
    )
    return any(path in lower for path in workflow_paths)


def _has_sidecar_experience_proof(proof_sidecar_content: Optional[str]) -> bool:
    if not proof_sidecar_content:
        return False

    in_block = False
    for line in proof_sidecar_content.splitlines():
        stripped = line.strip()
        if re.match(r"^(?:#{1,6}\s+)?E-E-A-T Proof Map:?\s*$", stripped, re.IGNORECASE):
            in_block = True
            continue
        if not in_block:
            continue
        if stripped.startswith("```"):
            continue
        if re.match(
            r"^(?:#{1,6}\s+)?(?:PAA/FAQ Provenance|Metric Proof Pack|Source Map|"
            r"Customer Proof Pack|FAQ Proof Map|Structured data plan|Review Story Selection|"
            r"Review Site Theme Selection|Fred Voccola Authority Selection)\s*$",
            stripped,
            re.IGNORECASE,
        ):
            break

        match = re.match(r"^[-*+]\s*Experience proof:\s*(.+)$", stripped, re.IGNORECASE)
        if (
            match
            and re.search(r"https?://", match.group(1))
            and _has_approved_experience_proof_status(match.group(1))
        ):
            proof_description = match.group(1)
            if _is_explicit_first_hand_evidence(proof_description):
                return True

    return False


def _is_explicit_first_hand_evidence(proof_description: str) -> bool:
    proof_type_match = re.search(
        r"(?:^|\|)\s*Proof type:\s*([^|]+)",
        proof_description,
        re.IGNORECASE,
    )
    evidence_match = re.search(
        r"(?:^|\|)\s*Evidence:\s*([^|]+)",
        proof_description,
        re.IGNORECASE,
    )
    if proof_type_match and evidence_match and evidence_match.group(1).strip():
        proof_type = _normalize_text(proof_type_match.group(1))
        return proof_type in {
            "first hand experience",
            "first hand evidence",
            "identity backed experience",
            "identity backed story",
            "identity backed account",
            "identity backed review",
            "identity backed evidence",
            "first party workflow experience",
            "first party workflow evidence",
        }

    return (
        re.search(
            r"\bThe rewrite uses first[- ]party ClockShark workflow evidence from\s+"
            r"https?://(?:www\.)?clockshark\.com/(?:blog|tour|industries)/",
            proof_description,
            re.IGNORECASE,
        )
        is not None
    )


def _has_approved_experience_proof_status(proof_description: str) -> bool:
    status_match = re.search(
        r"(?:^|\|)\s*Status:\s*([^|]+)",
        proof_description,
        re.IGNORECASE,
    )
    if not status_match:
        return False

    status = _normalize_text(status_match.group(1))
    return status in {
        "approved",
        "approved for public use",
        "verified",
        "verified for public use",
    }


def _verified_selector_roles(
    proof_sidecar_content: str,
    proof_sidecar_path: Optional[str],
) -> Optional[Dict[str, Dict[str, Any]]]:
    return verify_selector_evidence_roles(
        proof_sidecar_content,
        proof_sidecar_path,
    )


def _validated_customer_experience_binding(
    content: str,
    proof_sidecar_content: Optional[str],
    proof_sidecar_path: Optional[str],
) -> Optional[Dict[str, str]]:
    if not proof_sidecar_content or not proof_sidecar_path:
        return None
    verified_roles = _verified_selector_roles(
        proof_sidecar_content,
        proof_sidecar_path,
    )
    if not verified_roles:
        return None
    experience_role = verified_roles.get("experience_story")
    if not isinstance(experience_role, Mapping):
        return None
    selected = experience_role.get("selected_candidate")
    if not isinstance(selected, Mapping):
        return None
    selected_id = str(selected.get("proof_id", "")).strip()
    claim_id = str(selected.get("claim_id", "")).strip()
    identity = str(selected.get("identity", "")).strip()
    public_url = str(selected.get("public_url", "")).strip()
    story = str(selected.get("story", "")).strip()
    if not all((selected_id, claim_id, identity, public_url, story)):
        return None

    mining = _extract_selected_customer_proof_mining(proof_sidecar_content)
    if mining is None:
        return None
    proof = _parse_mined_proof(str(mining.get("proof", "")))
    if str(proof.get("proof_id", "")).strip() != selected_id:
        return None
    if _normalize_url(str(proof.get("url", ""))) != _normalize_url(public_url):
        return None
    if str(mining.get("status", "")).strip().casefold() != "approved":
        return None
    usable_story = str(mining.get("usable_pov/story_found", "")).strip()
    final_use = str(mining.get("final_use_in_copy", "")).strip()
    if not _is_substantive_experience_text(usable_story):
        return None
    if not _is_substantive_experience_text(final_use) or not re.search(
        r"\b(?:experience|pov|story)\b",
        final_use,
        re.IGNORECASE,
    ):
        return None
    if not _visible_story_mapping(content, public_url, identity, story):
        return None
    return {
        "proof_id": selected_id,
        "claim_id": claim_id,
        "identity": identity,
        "public_url": public_url,
    }


def _extract_selected_customer_proof_mining(
    proof_sidecar_content: str,
) -> Optional[Dict[str, str]]:
    in_block = False
    fields: Dict[str, str] = {}
    for line in proof_sidecar_content.splitlines():
        stripped = line.strip()
        if re.match(
            r"^(?:#{1,6}\s+)?Selected Customer Proof Mining:?\s*$",
            stripped,
            re.IGNORECASE,
        ):
            in_block = True
            continue
        if not in_block:
            continue
        if stripped.startswith("```") or re.match(r"^#{1,6}\s+", stripped):
            break
        match = re.match(r"^[-*+]\s*([^:]+):\s*(.+?)\s*$", stripped)
        if match:
            fields[_normalize_key(match.group(1))] = match.group(2).strip()
    return fields or None


def _parse_mined_proof(value: str) -> Dict[str, str]:
    parts = [part.strip() for part in value.split("|")]
    parsed = {"proof_id": parts[0] if parts else ""}
    for part in parts[1:]:
        if ":" not in part:
            continue
        key, item_value = part.split(":", 1)
        parsed[_normalize_key(key)] = item_value.strip()
    return parsed


def _is_substantive_experience_text(value: str) -> bool:
    normalized = _normalize_text(value)
    if not normalized or normalized in {
        "none",
        "none found",
        "not used",
        "not applicable",
        "n a",
    }:
        return False
    return len(re.findall(r"[a-z0-9]+", normalized)) >= 4


def _visible_story_mapping(
    content: str,
    public_url: str,
    identity: str,
    story: str,
) -> bool:
    normalized_url = _normalize_url(public_url)
    normalized_identity = _normalize_text(identity)
    story_tokens = _story_tokens(story)
    if not normalized_url or not normalized_identity or len(story_tokens) < 2:
        return False
    for paragraph in re.split(r"\n\s*\n", content):
        if normalized_url not in _normalize_url(paragraph):
            continue
        if normalized_identity not in _normalize_text(paragraph):
            continue
        if len(story_tokens.intersection(_story_tokens(paragraph))) >= 2:
            return True
    return False


def _story_tokens(value: str) -> set[str]:
    stopwords = {
        "and",
        "describes",
        "from",
        "into",
        "owner",
        "that",
        "the",
        "their",
        "using",
        "with",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if len(token) >= 3 and token not in stopwords
    }


def _has_documented_no_fit_experience_boundary(
    proof_sidecar_content: Optional[str],
    *,
    proof_sidecar_path: Optional[str] = None,
) -> bool:
    if not proof_sidecar_content:
        return False
    verified_roles = _verified_selector_roles(
        proof_sidecar_content,
        proof_sidecar_path,
    )
    if not verified_roles or "experience_story" not in verified_roles:
        return False
    verified_story = verified_roles["experience_story"]
    if str(verified_story.get("selected_id", "")).casefold() != "none":
        return False
    expected_candidates = [
        str(candidate).casefold()
        for candidate in verified_story.get("candidate_ids", [])
    ]
    expected_rejections = {
        str(candidate).casefold(): str(reason)
        for candidate, reason in verified_story.get("rejected_overrides", {}).items()
    }

    has_substantive_decision = False
    has_verified_rejections = False
    in_eeat_map = False
    in_customer_slate = False

    for line in proof_sidecar_content.splitlines():
        stripped = line.strip()
        if re.match(
            r"^(?:#{1,6}\s+)?E-E-A-T Proof Map:?\s*$",
            stripped,
            re.IGNORECASE,
        ):
            in_eeat_map = True
            in_customer_slate = False
            continue
        if re.match(
            r"^(?:#{1,6}\s+)?Customer Proof Slate:?\s*$",
            stripped,
            re.IGNORECASE,
        ):
            in_eeat_map = False
            in_customer_slate = True
            continue
        if stripped.startswith(chr(96) * 3) or re.match(r"^#{1,6}\s+", stripped):
            in_eeat_map = False
            in_customer_slate = False
            continue

        if in_eeat_map:
            decision = re.match(
                r"^[-*+]\s*First-hand evidence decision:\s*"
                r"Selected:\s*\[none\]\s*(.*)$",
                stripped,
                re.IGNORECASE,
            )
            if decision:
                reason = decision.group(1).lstrip(" .:|-\t")
                normalized_reason = _normalize_text(reason)
                reason_signals = (
                    "because",
                    "does not",
                    "did not",
                    "cannot",
                    "no approved",
                    "no relevant",
                    "not relevant",
                    "objective",
                    "article",
                    "section",
                    "omitted",
                    "excluded",
                    "substantiat",
                    "rather than",
                )
                has_substantive_decision = _word_count(reason) >= 8 and any(
                    signal in normalized_reason for signal in reason_signals
                )
            continue

        if not in_customer_slate or not re.match(
            r"^[-*+]\s*Role:\s*experience_story\b",
            stripped,
            re.IGNORECASE,
        ):
            continue
        if not re.search(r"\|\s*Selected:\s*\[none\]", stripped, re.IGNORECASE):
            continue
        top_candidates_match = re.search(
            r"\|\s*Top candidates:\s*\[([^\]]*)\]",
            stripped,
            re.IGNORECASE,
        )
        rejected_match = re.search(
            r"\|\s*Rejected stronger candidates:\s*\[([^\]]*)\]",
            stripped,
            re.IGNORECASE,
        )
        if not top_candidates_match or not rejected_match:
            continue
        raw_candidates = [
            candidate.strip().strip("\"'").casefold()
            for candidate in top_candidates_match.group(1).split(",")
            if candidate.strip()
        ]
        sidecar_candidates = [] if raw_candidates == ["none"] else raw_candidates
        if sidecar_candidates != expected_candidates:
            continue

        sidecar_rejections: Dict[str, str] = {}
        malformed_rejection = False
        for raw_rejection in rejected_match.group(1).split(","):
            candidate, separator, reason = raw_rejection.partition(":")
            candidate_key = candidate.strip().strip("\"'").casefold()
            reason = reason.strip()
            if not separator or not candidate_key or not reason:
                malformed_rejection = True
                break
            sidecar_rejections[candidate_key] = reason
        if malformed_rejection or sidecar_rejections != expected_rejections:
            continue
        if expected_candidates:
            has_verified_rejections = set(sidecar_rejections) == set(
                expected_candidates
            ) and all(
                _has_section_specific_story_rejection_reason(reason)
                for reason in sidecar_rejections.values()
            )
        else:
            empty_reason = sidecar_rejections.get("none", "")
            has_verified_rejections = (
                set(sidecar_rejections) == {"none"}
                and "no eligible candidate exists" in _normalize_text(empty_reason)
                and _has_section_specific_story_rejection_reason(empty_reason)
            )

    if not expected_candidates and not expected_rejections:
        no_fit_reason = str(verified_story.get("no_fit_reason", ""))
        normalized_no_fit = _normalize_text(no_fit_reason)
        has_verified_rejections = (
            _word_count(no_fit_reason) >= 8
            and "no customer proof selected" in normalized_no_fit
            and "public copy must omit" in normalized_no_fit
        )

    return has_substantive_decision and has_verified_rejections


@lru_cache(maxsize=1)
def _customer_proof_ids() -> FrozenSet[str]:
    """Load approved, public, story-eligible proof IDs; fail closed on error."""
    index_path = (
        Path(__file__).resolve().parents[2] / "context" / "customer-proof-index.json"
    )
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return frozenset()

    proof_rows = payload.get("proof")
    if not isinstance(proof_rows, list):
        return frozenset()
    eligible_ids = set()
    for row in proof_rows:
        if not isinstance(row, dict):
            continue
        review_story = row.get("review_story")
        if not isinstance(review_story, dict):
            continue
        proof_id = str(row.get("proof_id", "")).strip().lower()
        if (
            proof_id
            and str(row.get("approval_status", "")).strip().lower() == "approved"
            and row.get("public_copy_allowed") is True
            and review_story.get("story_allowed") is True
        ):
            eligible_ids.add(proof_id)
    return frozenset(eligible_ids)


def _has_section_specific_story_rejection_reason(reason: str) -> bool:
    normalized = re.sub(r"\s+", " ", reason.strip().lower())
    if not normalized or normalized in {"none", "n/a", "na"}:
        return False
    reason_signals = (
        "because",
        "section",
        "article",
        "objective",
        "omitted",
        "not used",
        "instead",
        "while",
    )
    return len(normalized.split()) >= 8 and any(
        signal in normalized for signal in reason_signals
    )


def _has_review_site_theme(body: str) -> bool:
    text = _plain_text(body).lower()
    review_surfaces = (
        "g2",
        "capterra",
        "software advice",
        "getapp",
        "trustradius",
        "gartner",
        "trustpilot",
        "app store",
        "google reviews",
    )
    review_terms = (
        "review",
        "reviews",
        "review-site",
        "review site",
        "customer feedback",
        "customer themes",
        "voc",
    )
    return any(surface in text for surface in review_surfaces) and any(
        term in text for term in review_terms
    )


def _has_valid_review_story_selection(
    content: str, proof_sidecar_content: Optional[str]
) -> bool:
    if not proof_sidecar_content:
        return False
    selected = _extract_review_story_selected_line(proof_sidecar_content)
    if not selected:
        return False
    identity = selected.get("identity", "")
    url = selected.get("url", "")
    status = selected.get("status", "").lower()
    use = selected.get("use", "").lower()
    if not identity or not url.startswith(("http://", "https://")):
        return False
    if status != "approved":
        return False
    if "e-e-a-t experience story" not in use:
        return False
    return _paragraph_has_url_and_identity(content, url, identity)


def _extract_review_story_selected_line(content: str) -> Dict[str, str]:
    in_block = False
    for line in content.splitlines():
        stripped = line.strip()
        if re.match(
            r"^(?:#{1,6}\s+)?Review Story Selection:?\s*$", stripped, re.IGNORECASE
        ):
            in_block = True
            continue
        if not in_block:
            continue
        if stripped.startswith("```"):
            break
        if re.match(
            r"^(?:#{1,6}\s+)?(?:PAA/FAQ Provenance|Metric Proof Pack|Source Map|"
            r"Customer Proof Pack|E-E-A-T Proof Map|FAQ Proof Map|Structured data plan|Fred Voccola Authority Selection)\s*$",
            stripped,
            re.IGNORECASE,
        ):
            break
        match = re.match(
            r"^\s*[-*+]\s*Selected story:\s*(.+?)\s*$", line, re.IGNORECASE
        )
        if not match:
            continue
        parts = [part.strip() for part in match.group(1).split("|")]
        selected = {"proof_id": parts[0] if parts else ""}
        for part in parts[1:]:
            if ":" not in part:
                continue
            key, value = part.split(":", 1)
            selected[_normalize_key(key).replace(" ", "_")] = value.strip()
        return selected
    return {}


def _paragraph_has_url_and_identity(content: str, url: str, identity: str) -> bool:
    normalized_url = _normalize_url(url)
    normalized_identity = _normalize_text(identity)
    for paragraph in re.split(r"\n\s*\n", content):
        if normalized_url not in _normalize_url(paragraph):
            continue
        if normalized_identity and normalized_identity in _normalize_text(paragraph):
            return True
    return False


def _normalize_url(value: str) -> str:
    url_match = re.search(r"https?://[^\s),]+", value, re.IGNORECASE)
    if url_match:
        value = url_match.group(0)
    return value.strip().rstrip(".,)").lower()


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _has_expert_quote(body: str) -> bool:
    quote_pattern = (
        r'"[^"]{20,240}"\s*(?:,?\s*(?:said|says|according to|explained|wrote)\b)'
    )
    attribution_pattern = (
        r'(?:said|says|according to|explained|wrote)\s+[^.]{3,80}:\s*"[^"]{20,240}"'
    )
    return bool(
        re.search(quote_pattern, body, re.IGNORECASE)
        or re.search(attribution_pattern, body, re.IGNORECASE)
    )


def _has_valid_fred_authority_expertise(
    body: str,
    proof_sidecar_content: Optional[str],
) -> bool:
    if not proof_sidecar_content:
        return False
    fields = _extract_fred_authority_selection_fields(proof_sidecar_content)
    if not fields:
        return False
    if fields.get("evaluation_status", "").strip().casefold() != "completed":
        return False
    selected = _unwrap_bracketed_value(fields.get("selected", ""))
    if not selected or selected.casefold() == "none":
        return False
    intended_use = fields.get("intended_use", "").strip().casefold()
    if not intended_use or intended_use == "none":
        return False
    evidence_status = fields.get("evidence_status", "").strip().casefold()
    if evidence_status != "receipt_approved":
        return False
    public_url = fields.get("public_url", "").strip()
    if not public_url.startswith(("http://", "https://")):
        return False
    expected = _normalize_url(public_url)
    return any(
        _normalize_url(url) == expected
        for _, url in _extract_markdown_links(body)
    )


def _extract_fred_authority_selection_fields(
    proof_sidecar_content: str,
) -> Dict[str, str]:
    in_block = False
    fields: Dict[str, str] = {}
    for line in proof_sidecar_content.splitlines():
        stripped = line.strip()
        if re.match(
            r"^(?:#{1,6}\s+)?Fred Voccola Authority Selection:?\s*$",
            stripped,
            re.IGNORECASE,
        ):
            in_block = True
            continue
        if not in_block:
            continue
        if stripped.startswith("```") or re.match(r"^#{1,6}\s+", stripped):
            break
        match = re.match(r"^[-*+]\s*([^:]+):\s*(.+?)\s*$", stripped)
        if match:
            fields[_normalize_key(match.group(1))] = match.group(2).strip()
    return fields


def _unwrap_bracketed_value(value: str) -> str:
    cleaned = value.strip()
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    return cleaned.strip()


def _check_section_clarity(body: str) -> Dict[str, Any]:
    sections = _extract_h2_sections(body)
    unclear_sections = []

    for heading, section in sections:
        plain = _plain_text(section)
        word_count = _word_count(plain)
        h3_count = len(re.findall(r"^###\s+", section, re.MULTILINE))
        if word_count > 450 and h3_count == 0:
            unclear_sections.append({"heading": heading, "words": word_count})

    passed = not unclear_sections
    return {
        "passed": passed,
        "issue": "One or more major sections appears to cover too much without H3 structure.",
        "fix": "Keep one clear idea per major section, or split broad sections with focused H3s.",
        "severity": "low",
        "details": {
            "unclear_sections": unclear_sections,
        },
    }
