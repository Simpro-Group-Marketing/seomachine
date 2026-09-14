"""Validate editorial-plan internal links and brief-bound count overrides."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import re

from ..frontmatter import FrontmatterError
from .contracts import BRAND_INTERNAL_DOMAINS
from .contracts import INTERNAL_LINK_FIELDS
from .contracts import LINK_POLICY_OVERRIDE_FIELDS
from .contracts import OWNED_INTERNAL_DOMAINS
from .contracts import Finding
from .contracts import _finding
from .contracts import _invalid_field
from .contracts import _require_nonempty_string
from .contracts import _sorted_findings
from .contracts import _unknown_fields
from .dependencies import EditorialPlanDependencies
from .dependencies import default_editorial_plan_dependencies
from .snapshot_adapters import link_policy_article
from .snapshot_adapters import link_policy_brief
from .text import _normalize_visible_text



def _check_internal_link_plan(
    value: Any,
    *,
    brand: str | None,
    suppress_down_funnel: bool = False,
) -> list[Finding]:
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
        if (
            isinstance(target, str)
            and target.strip()
            and not _is_internal_link_target(target, brand=brand)
        ):
            findings.append(_finding(
                'editorial_plan_internal_link_external',
                'Editorial-plan internal-link targets must resolve to an owned site.',
                f'{row_location}/target',
                'Use a root-relative URL or an absolute URL owned by the article brand.',
            ))
        has_down_funnel = has_down_funnel or role == 'down_funnel'
    if not has_down_funnel and not suppress_down_funnel:
        findings.append(_finding(
            'editorial_plan_down_funnel_link_missing',
            'Editorial plan requires an intent-appropriate down-funnel internal link.',
            location,
            'Map a relevant product, solution, feature, or industry next step.',
        ))
    return findings




def _check_link_policy_override_shape(value: Any) -> list[Finding]:
    return _check_link_policy_override_shape_with_dependencies(
        value,
        default_editorial_plan_dependencies(),
    )


def _check_link_policy_override_shape_with_dependencies(
    value: Any,
    dependencies: EditorialPlanDependencies,
) -> list[Finding]:
    if value is None:
        return []
    location = '/link_policy_override'
    if not isinstance(value, Mapping):
        return [_invalid_field(location, 'must be an object when present')]
    findings = _unknown_fields(value, LINK_POLICY_OVERRIDE_FIELDS, location)
    for key in ('brief_path', 'brief_sha256', 'source_sentence', 'scope'):
        _require_nonempty_string(value, key, findings, f'{location}/{key}')
    try:
        validate_sha = value.get('brief_sha256')
        if not isinstance(validate_sha, str) or re.fullmatch(r'[0-9a-f]{64}', validate_sha) is None:
            raise ValueError
    except FrontmatterError:
        findings.append(_invalid_field(f'{location}/brief_sha256', 'must be a lowercase SHA-256 digest'))
    exact_count = value.get('exact_count')
    if (
        not isinstance(exact_count, int)
        or isinstance(exact_count, bool)
        or exact_count <= 0
        or exact_count > 7
    ):
        findings.append(
            _invalid_field(
                f'{location}/exact_count',
                'must be a positive integer no greater than 7',
            )
        )
    elif isinstance(value.get('source_sentence'), str) and not (
        dependencies.link_policy_override_count_supported(
            str(value.get('source_sentence')),
            exact_count,
        )
    ):
        findings.append(
            _invalid_field(
                f'{location}/exact_count',
                'must be explicitly permitted by source_sentence',
            )
        )
    if value.get('scope') != 'pre_faq_body':
        findings.append(_invalid_field(f'{location}/scope', 'must be pre_faq_body'))
    return findings


def _has_syntactic_link_policy_override(
    value: Any,
    *,
    dependencies: EditorialPlanDependencies | None = None,
) -> bool:
    dependencies = dependencies or default_editorial_plan_dependencies()
    return value is not None and not _check_link_policy_override_shape_with_dependencies(
        value,
        dependencies,
    )


def internal_link_guidelines_from_plan(
    plan: Mapping[str, Any],
    *,
    dependencies: EditorialPlanDependencies | None = None,
) -> dict[str, Any]:
    """Return SEO link-count guidelines resolved from an editorial plan."""
    dependencies = dependencies or default_editorial_plan_dependencies()
    override = plan.get('link_policy_override') if isinstance(plan, Mapping) else None
    if not _has_syntactic_link_policy_override(override, dependencies=dependencies):
        return {}
    exact_count = int(override['exact_count'])
    industry_policy = dependencies.resolve_required_industry_policy(
        plan=plan,
        brand=_resolve_plan_brand(plan),
    )
    resolved_count = exact_count + (1 if industry_policy is not None else 0)
    return {
        'min_internal_links': resolved_count,
        'optimal_internal_links': resolved_count,
        'max_internal_links': resolved_count,
        'require_down_funnel_link': industry_policy is not None,
    }


def _check_link_policy_override_binding(
    plan: Mapping[str, Any],
    *,
    article_path: str | Path | None,
    plan_path: str | Path | None,
    article_content: str | None = None,
    brief_content: str | None = None,
    brief_sha256: str | None = None,
    dependencies: EditorialPlanDependencies | None = None,
) -> list[Finding]:
    dependencies = dependencies or default_editorial_plan_dependencies()
    override = plan.get('link_policy_override')
    if override is None:
        return []
    findings = _check_link_policy_override_shape_with_dependencies(
        override,
        dependencies,
    )
    if findings:
        return findings
    brief_bytes, actual_hash, load_error = link_policy_brief(
        override,
        plan_path=plan_path,
        brief_content=brief_content,
        brief_sha256=brief_sha256,
    )
    if load_error is not None:
        return [load_error]
    findings.extend(_brief_binding_findings(override, brief_bytes, actual_hash))
    article, load_error = link_policy_article(article_path, article_content)
    if load_error is not None:
        return [*_sorted_findings(findings), load_error]
    findings.extend(_article_link_binding_findings(
        plan,
        override,
        article,
        dependencies,
    ))
    return _sorted_findings(findings)


def _brief_binding_findings(
    override: Mapping[str, Any],
    brief_bytes: bytes,
    actual_hash: str,
) -> list[Finding]:
    findings: list[Finding] = []
    if actual_hash != override['brief_sha256']:
        findings.append(_finding(
            'editorial_plan_link_policy_override_brief_hash_mismatch',
            'Link policy override brief hash does not match the bound brief snapshot.',
            '/link_policy_override/brief_sha256',
            'Bind the exact current brief snapshot hash.',
        ))
    try:
        brief_text = brief_bytes.decode('utf-8')
    except UnicodeDecodeError:
        brief_text = ''
    if _normalize_visible_text(str(override['source_sentence'])) not in _normalize_visible_text(brief_text):
        findings.append(_finding(
            'editorial_plan_link_policy_override_source_sentence_missing',
            'Link policy override source sentence is not present in the bound brief.',
            '/link_policy_override/source_sentence',
            'Use an exact sentence from the bound brief snapshot.',
        ))
    return findings


def _article_link_binding_findings(
    plan: Mapping[str, Any],
    override: Mapping[str, Any],
    article: str,
    dependencies: EditorialPlanDependencies,
) -> list[Finding]:
    findings: list[Finding] = []
    links = _pre_faq_internal_links(
        article,
        brand=_resolve_plan_brand(plan),
        dependencies=dependencies,
    )
    exact_count = int(override['exact_count'])
    industry_policy = dependencies.resolve_required_industry_policy(
        plan=plan,
        brand=_resolve_plan_brand(plan),
    )
    expected_count = exact_count + (1 if industry_policy is not None else 0)
    if len(links) != expected_count:
        count_description = (
            f'{exact_count} brief-selected links plus the required industry link'
            if industry_policy is not None
            else f'{exact_count} pre-FAQ internal body links'
        )
        findings.append(_finding(
            'editorial_plan_link_policy_override_count_mismatch',
            f'Link policy override requires exactly {count_description}.',
            '/link_policy_override/exact_count',
            'Match the resolved brief-bound internal-link count.',
        ))
    if len({target for _anchor, target in links}) != len(links):
        findings.append(_finding(
            'editorial_plan_link_policy_override_duplicate_target',
            'Link policy override rejects duplicate internal-link targets.',
            '/link_policy_override',
            'Use each planned target once.',
        ))
    planned_targets = {
        _normalize_link_target(str(row.get('target') or ''))
        for row in plan.get('internal_link_plan', [])
        if isinstance(row, Mapping)
    }
    actual_targets = {_normalize_link_target(target) for _anchor, target in links}
    if actual_targets != planned_targets:
        findings.append(_finding(
            'editorial_plan_link_policy_override_target_set_mismatch',
            'Link policy override requires final internal-link targets to match internal_link_plan exactly.',
            '/internal_link_plan',
            'Add the brief-selected targets and any required single-trade industry target only.',
        ))
    return findings




def _resolve_plan_brand(plan: Mapping[str, Any]) -> str | None:
    raw_brand = plan.get('brand')
    if raw_brand is not None:
        if not isinstance(raw_brand, str):
            return None
        normalized = raw_brand.strip().casefold()
        return normalized if normalized in BRAND_INTERNAL_DOMAINS else None

    meta = plan.get('meta')
    meta_title = meta.get('meta_title') if isinstance(meta, Mapping) else None
    if not isinstance(meta_title, str):
        return None
    suffix = re.search(r'\|\s*([^|]+?)\s*$', meta_title)
    if suffix is None:
        return None
    normalized = suffix.group(1).strip().casefold()
    return normalized if normalized in BRAND_INTERNAL_DOMAINS else None


def _is_internal_link_target(target: str, *, brand: str | None = None) -> bool:
    candidate = target.strip()
    parsed = urlparse(candidate)
    if parsed.scheme in {'http', 'https'}:
        hostname = (parsed.hostname or '').casefold().rstrip('.')
        allowed_domains = (
            BRAND_INTERNAL_DOMAINS.get(brand, frozenset())
            if brand is not None
            else OWNED_INTERNAL_DOMAINS
        )
        return any(
            hostname == domain or hostname.endswith(f'.{domain}')
            for domain in allowed_domains
        )
    if parsed.scheme or parsed.netloc:
        return False
    return candidate.startswith('/') and not candidate.startswith('//')


def _article_contains_link_target(article: str, target: str) -> bool:
    escaped = re.escape(target.strip())
    return bool(re.search(rf'\]\(\s*{escaped}(?:\s+["\'][^"\']*["\'])?\s*\)', article) or re.search(rf'href\s*=\s*["\']{escaped}["\']', article, re.IGNORECASE))


def _resolve_brief_path(raw_path: str, *, plan_path: Path) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    cwd_candidate = Path.cwd() / candidate
    if cwd_candidate.exists():
        return cwd_candidate
    parent_candidate = plan_path.parent / candidate
    if parent_candidate.exists():
        return parent_candidate
    return cwd_candidate


def _pre_faq_internal_links(
    article: str,
    *,
    brand: str | None,
    dependencies: EditorialPlanDependencies | None = None,
) -> list[tuple[str, str]]:
    dependencies = dependencies or default_editorial_plan_dependencies()
    try:
        _frontmatter, body, _line = dependencies.split_frontmatter(article)
    except ValueError:
        body = article
    pre_faq = re.split(
        r'(?im)^##\s+(?:frequently asked questions|faqs?)\s*$',
        body,
        maxsplit=1,
    )[0]
    pre_faq = _blank_non_visible_link_context(pre_faq)
    links: list[tuple[str, str]] = []
    for anchor, target in re.findall(
        r'(?<!!)\[([^\]]+)\]\(([^)\s]+)(?:\s+["\'][^)]*["\'])?\)',
        pre_faq,
    ):
        if _is_internal_link_target(target, brand=brand):
            links.append((_visible_anchor(anchor), target.strip()))
    for match in re.finditer(
        r'<a\b[^>]*\bhref\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        pre_faq,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        target = match.group(1).strip()
        if _is_internal_link_target(target, brand=brand):
            links.append((_visible_anchor(match.group(2)), target))
    return links


def _blank_non_visible_link_context(value: str) -> str:
    value = re.sub(
        r'^(?:```|~~~).*?^(?:```|~~~)\s*$',
        ' ',
        value,
        flags=re.MULTILINE | re.DOTALL,
    )
    value = re.sub(r'<!--.*?-->', ' ', value, flags=re.DOTALL)
    return value


def _visible_anchor(value: str) -> str:
    value = re.sub(r'<[^>]+>', ' ', value)
    value = re.sub(r'[*_`]', '', value)
    return re.sub(r'\s+', ' ', value).strip()


def _normalize_link_target(target: str) -> str:
    candidate = target.strip()
    parsed = urlparse(candidate)
    if parsed.scheme in {'http', 'https'}:
        scheme = parsed.scheme.casefold()
        host = (parsed.hostname or '').casefold().rstrip('.')
        path = re.sub(r'/+', '/', parsed.path or '/')
        return f'{scheme}://{host}{path.rstrip("/") or "/"}'
    cleaned = candidate.split('#', 1)[0].split('?', 1)[0]
    return re.sub(r'/+', '/', cleaned).rstrip('/') or '/'
