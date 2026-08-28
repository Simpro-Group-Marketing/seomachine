"""Validate Simpro trade-vertical industry cluster links."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

try:
    from .guard_common import Finding, make_finding, should_fail, summarize_findings
except ImportError:  # pragma: no cover - supports direct script execution.
    from guard_common import Finding, make_finding, should_fail, summarize_findings


INTRO_PLACEMENT = "intro_first_300_words"
MAX_INTRO_WORD_POSITION = 300
GENERIC_LINK_ANCHORS = {
    "click here",
    "here",
    "learn more",
    "read more",
    "this page",
    "this link",
}
RESOURCE_ID_RE = re.compile(r"^res-[0-9a-f]{32}$", re.IGNORECASE)
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)\s]+)(?:\s+['\"][^)]*['\"])?\)")
HTML_LINK_RE = re.compile(
    r"<a\b[^>]*\bhref\s*=\s*['\"](?P<url>[^'\"]+)['\"][^>]*>(?P<anchor>.*?)</a>",
    re.IGNORECASE | re.DOTALL,
)
FRONTMATTER_RE = re.compile(r"\A---\s*\r?\n(?P<frontmatter>.*?)\r?\n---\s*(?:\r?\n|\Z)", re.DOTALL)


@dataclass(frozen=True)
class IndustryPolicy:
    key: str
    context_topic: str
    target_url: str
    signals: tuple[str, ...]
    anchor_examples: tuple[str, ...]
    vault_vertical_query: str


POLICIES: dict[str, IndustryPolicy] = {
    "electrical": IndustryPolicy(
        key="electrical",
        context_topic="industry:electrical",
        target_url="https://www.simprogroup.com/industries/electrical-software",
        signals=(
            "electrical",
            "electrician",
            "electricians",
            "electrical contractor",
            "electrical contractors",
        ),
        anchor_examples=(
            "electrical contractor software",
            "electrical software",
            "field service software for electricians",
        ),
        vault_vertical_query=(
            "electrical contractor software industry page vertical profile "
            "Simpro industries electrical-software"
        ),
    ),
    "hvac": IndustryPolicy(
        key="hvac",
        context_topic="industry:hvac",
        target_url="https://www.simprogroup.com/industries/hvac-software",
        signals=("hvac", "heating", "cooling"),
        anchor_examples=(
            "HVAC software",
            "field service software for HVAC contractors",
            "HVAC contractor software",
        ),
        vault_vertical_query="HVAC software industry page vertical profile Simpro industries hvac-software",
    ),
    "plumbing": IndustryPolicy(
        key="plumbing",
        context_topic="industry:plumbing",
        target_url="https://www.simprogroup.com/industries/plumbing-software",
        signals=("plumbing", "plumber", "plumbers"),
        anchor_examples=(
            "plumbing software",
            "plumbing contractor software",
            "field service software for plumbers",
        ),
        vault_vertical_query=(
            "plumbing contractor software industry page vertical profile "
            "Simpro industries plumbing-software"
        ),
    ),
    "fire_protection": IndustryPolicy(
        key="fire_protection",
        context_topic="industry:fire_protection",
        target_url="https://www.simprogroup.com/industries/fire-protection-software",
        signals=("fire protection", "fire inspection", "fire inspections"),
        anchor_examples=(
            "fire protection software",
            "fire inspection software",
            "fire protection field service software",
        ),
        vault_vertical_query=(
            "fire protection software industry page vertical profile "
            "Simpro industries fire-protection-software"
        ),
    ),
    "security": IndustryPolicy(
        key="security",
        context_topic="industry:security",
        target_url="https://www.simprogroup.com/industries/security",
        signals=("security contractor", "security contractors", "low voltage"),
        anchor_examples=(
            "security business software",
            "low voltage contractor software",
            "software for security contractors",
        ),
        vault_vertical_query="security software industry page vertical profile Simpro industries security",
    ),
}
BRAND_DOMAINS = {"simprogroup.com"}
VERTICAL_RESOURCE_TERMS = {
    "industry",
    "industries",
    "solution",
    "solutions",
    "vertical",
    "verticals",
}


@dataclass(frozen=True)
class LinkMatch:
    anchor: str
    url: str
    normalized_path: str
    word_position: int


def check_content(
    content: str,
    *,
    plan: Mapping[str, Any] | None = None,
    context_request: Mapping[str, Any] | None = None,
    context_pack: Mapping[str, Any] | None = None,
    context_receipt: Mapping[str, Any] | None = None,
    fail_on: str = "error",
) -> list[Finding]:
    """Return findings for missing trade-vertical cluster links."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")
    policy = resolve_required_policy(content=content, plan=plan)
    if policy is None:
        return []
    findings = _article_findings(content, policy)
    if context_request is not None or context_pack is not None or context_receipt is not None:
        findings.extend(
            context_findings(
                content=content,
                request=context_request,
                pack=context_pack,
                receipt=context_receipt,
            )
        )
    return _sorted(findings)


def check_file(
    path: str | Path,
    *,
    fail_on: str = "error",
    proof_sidecar: str | Path | None = None,
    editorial_plan: str | Path | Mapping[str, Any] | None = None,
    **_: Any,
) -> list[Finding]:
    """Read one Markdown artifact and return industry cluster findings."""
    try:
        content = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        return [
            _finding(
                "industry_cluster_link_article_unreadable",
                f"Article cannot be read for industry cluster link validation: {error}",
                suggestion="Regenerate the article artifact before publish readiness.",
            )
        ]
    return check_content(
        content,
        plan=_load_plan(editorial_plan),
        fail_on=fail_on,
    )


def context_findings(
    *,
    content: str,
    request: Mapping[str, Any] | None,
    pack: Mapping[str, Any] | None,
    receipt: Mapping[str, Any] | None,
    plan: Mapping[str, Any] | None = None,
) -> list[Finding]:
    """Validate the required vertical lane in context artifacts."""
    policy = resolve_required_policy(content=content, plan=plan)
    if policy is None:
        return []
    findings: list[Finding] = []
    scope = request.get("scope") if isinstance(request, Mapping) else None
    topics = scope.get("required_context_topics") if isinstance(scope, Mapping) else None
    if not isinstance(topics, list) or policy.context_topic not in {
        str(item).strip() for item in topics if isinstance(item, str)
    }:
        findings.append(
            _finding(
                "context_request_industry_topic_missing",
                (
                    "Context request must include the required vertical topic "
                    f"{policy.context_topic} for this single-trade Simpro article."
                ),
                suggestion=(
                    "Add scope.required_context_topics with the matching industry topic "
                    "before rebuilding the context pack and receipt."
                ),
            )
        )
    if not _has_matching_vertical_resource(pack, receipt, policy):
        findings.append(
            _finding(
                "context_pack_industry_resource_missing",
                (
                    "Context pack and receipt must select a vault resource whose metadata "
                    f"matches the {policy.key} vertical."
                ),
                suggestion=(
                    "Run vault_search for the industry page vertical profile, read the selected "
                    "resource, and rebuild the context pack and receipt with that resource ID."
                ),
            )
        )
    return _sorted(findings)


def editorial_plan_findings(plan: Mapping[str, Any], *, brand: str | None) -> list[Finding]:
    """Validate an editorial plan's industry-cluster policy block."""
    policy = resolve_required_policy(plan=plan, brand=brand)
    declared = plan.get("industry_cluster_link_policy")
    if policy is None:
        if declared is None:
            return []
        if not isinstance(declared, Mapping):
            return [
                _plan_finding(
                    "editorial_plan_industry_cluster_policy_invalid",
                    "/industry_cluster_link_policy",
                    "industry_cluster_link_policy must be an object when present.",
                )
            ]
        if link_policy_override_prohibits_industry_link(plan):
            return _suppressed_industry_policy_findings(plan, declared)
        if declared.get("status") != "not_applicable":
            return [
                _plan_finding(
                    "editorial_plan_industry_cluster_policy_invalid",
                    "/industry_cluster_link_policy/status",
                    "Non-single-trade plans must mark industry_cluster_link_policy not_applicable.",
                )
            ]
        if not str(declared.get("rationale") or declared.get("reason") or "").strip():
            return [
                _plan_finding(
                    "editorial_plan_industry_cluster_policy_invalid",
                    "/industry_cluster_link_policy/rationale",
                    "Not-applicable industry cluster policies need a rationale.",
                )
            ]
        return []
    if not isinstance(declared, Mapping):
        return [
            _plan_finding(
                "editorial_plan_industry_cluster_link_missing",
                "/industry_cluster_link_policy",
                "Single-trade Simpro plans require an industry_cluster_link_policy object.",
            )
        ]
    findings: list[Finding] = []
    if link_policy_override_prohibits_industry_link(plan):
        expected_suppressed_fields = {
            "status",
            "industry",
            "target",
            "anchor",
            "placement",
            "vault_vertical_query",
            "required_resource_ids",
            "rationale",
        }
        unknown_suppressed = set(declared) - expected_suppressed_fields
        if unknown_suppressed:
            findings.append(
                _plan_finding(
                    "editorial_plan_industry_cluster_policy_invalid",
                    "/industry_cluster_link_policy",
                    "industry_cluster_link_policy contains unsupported fields: "
                    + ", ".join(sorted(str(field) for field in unknown_suppressed)),
                )
            )
        if declared.get("status") != "suppressed_by_exact_brief_override":
            findings.append(
                _plan_finding(
                    "editorial_plan_industry_cluster_policy_invalid",
                    "/industry_cluster_link_policy/status",
                    "industry_cluster_link_policy.status must be suppressed_by_exact_brief_override.",
                )
            )
        if declared.get("industry") != policy.key:
            findings.append(
                _plan_finding(
                    "editorial_plan_industry_cluster_policy_invalid",
                    "/industry_cluster_link_policy/industry",
                    f"industry_cluster_link_policy.industry must be {policy.key}.",
                )
            )
        query = str(declared.get("vault_vertical_query") or "").strip()
        normalized_query = _normalize_text(query)
        if policy.key not in normalized_query.split() or not any(
            term in normalized_query.split() for term in ("industry", "industries", "vertical")
        ):
            findings.append(
                _plan_finding(
                    "editorial_plan_industry_cluster_policy_invalid",
                    "/industry_cluster_link_policy/vault_vertical_query",
                    "vault_vertical_query must explicitly request the matching industry or vertical context.",
                )
            )
        resources = declared.get("required_resource_ids")
        if not isinstance(resources, list) or not resources or any(
            not isinstance(resource_id, str) or RESOURCE_ID_RE.fullmatch(resource_id) is None
            for resource_id in resources
        ):
            findings.append(
                _plan_finding(
                    "editorial_plan_industry_cluster_policy_invalid",
                    "/industry_cluster_link_policy/required_resource_ids",
                    "required_resource_ids must list at least one connector-shaped vault resource ID.",
                )
            )
        rationale = str(declared.get("rationale") or "").casefold()
        if "brief" not in rationale or "override" not in rationale:
            findings.append(
                _plan_finding(
                    "editorial_plan_industry_cluster_policy_invalid",
                    "/industry_cluster_link_policy/rationale",
                    "Suppressed industry cluster policies must cite the brief override rationale.",
                )
            )
        return _sorted(findings)
    expected_fields = {
        "status",
        "industry",
        "target",
        "anchor",
        "placement",
        "vault_vertical_query",
        "required_resource_ids",
        "rationale",
    }
    unknown = set(declared) - expected_fields
    if unknown:
        findings.append(
            _plan_finding(
                "editorial_plan_industry_cluster_policy_invalid",
                "/industry_cluster_link_policy",
                "industry_cluster_link_policy contains unsupported fields: "
                + ", ".join(sorted(str(field) for field in unknown)),
            )
        )
    checks = {
        "status": "required",
        "industry": policy.key,
        "target": policy.target_url,
        "placement": INTRO_PLACEMENT,
    }
    for key, expected in checks.items():
        if declared.get(key) != expected:
            findings.append(
                _plan_finding(
                    "editorial_plan_industry_cluster_policy_invalid",
                    f"/industry_cluster_link_policy/{key}",
                    f"industry_cluster_link_policy.{key} must be {expected}.",
                )
            )
    anchor = str(declared.get("anchor") or "").strip()
    if _normalize_anchor(anchor) not in _normalized_anchor_examples(policy):
        findings.append(
            _plan_finding(
                "editorial_plan_industry_cluster_policy_invalid",
                "/industry_cluster_link_policy/anchor",
                "industry_cluster_link_policy.anchor must match an approved industry-page anchor.",
            )
        )
    query = str(declared.get("vault_vertical_query") or "").strip()
    normalized_query = _normalize_text(query)
    if policy.key not in normalized_query.split() or not any(
        term in normalized_query.split() for term in ("industry", "industries", "vertical")
    ):
        findings.append(
            _plan_finding(
                "editorial_plan_industry_cluster_policy_invalid",
                "/industry_cluster_link_policy/vault_vertical_query",
                "vault_vertical_query must explicitly request the matching industry or vertical context.",
            )
        )
    resources = declared.get("required_resource_ids")
    if not isinstance(resources, list) or not resources or any(
        not isinstance(resource_id, str) or RESOURCE_ID_RE.fullmatch(resource_id) is None
        for resource_id in resources
    ):
        findings.append(
            _plan_finding(
                "editorial_plan_industry_cluster_policy_invalid",
                "/industry_cluster_link_policy/required_resource_ids",
                "required_resource_ids must list at least one connector-shaped vault resource ID.",
            )
        )
    links = plan.get("internal_link_plan")
    if not isinstance(links, list) or not any(
        isinstance(row, Mapping) and _same_target(str(row.get("target") or ""), policy.target_url)
        for row in links
    ):
        findings.append(
            _plan_finding(
                "editorial_plan_industry_cluster_link_missing",
                "/internal_link_plan",
                "Single-trade Simpro plans must include the required industry page in internal_link_plan.",
            )
        )
    return _sorted(findings)


def _suppressed_industry_policy_findings(
    plan: Mapping[str, Any],
    declared: Mapping[str, Any],
) -> list[Finding]:
    """Validate an industry policy intentionally suppressed by an exact brief override."""
    findings: list[Finding] = []
    expected_fields = {
        "status",
        "industry",
        "target",
        "anchor",
        "placement",
        "vault_vertical_query",
        "required_resource_ids",
        "rationale",
    }
    unknown = set(declared) - expected_fields
    if unknown:
        findings.append(
            _plan_finding(
                "editorial_plan_industry_cluster_policy_invalid",
                "/industry_cluster_link_policy",
                "industry_cluster_link_policy contains unsupported fields: "
                + ", ".join(sorted(str(field) for field in unknown)),
            )
        )
    if declared.get("status") != "suppressed_by_exact_brief_override":
        findings.append(
            _plan_finding(
                "editorial_plan_industry_cluster_policy_invalid",
                "/industry_cluster_link_policy/status",
                "industry_cluster_link_policy.status must be suppressed_by_exact_brief_override.",
            )
        )
    industry = str(declared.get("industry") or "").strip()
    detected = _detected_policy_keys(plan=plan)
    expected_industry = detected[0] if len(detected) == 1 else industry
    if industry != expected_industry or industry not in POLICIES:
        findings.append(
            _plan_finding(
                "editorial_plan_industry_cluster_policy_invalid",
                "/industry_cluster_link_policy/industry",
                "industry_cluster_link_policy.industry must match the suppressed single-trade policy.",
            )
        )
    query = str(declared.get("vault_vertical_query") or "").strip()
    normalized_query = _normalize_text(query)
    if industry and (
        industry not in normalized_query.split()
        or not any(term in normalized_query.split() for term in ("industry", "industries", "vertical"))
    ):
        findings.append(
            _plan_finding(
                "editorial_plan_industry_cluster_policy_invalid",
                "/industry_cluster_link_policy/vault_vertical_query",
                "vault_vertical_query must explicitly request the matching industry or vertical context.",
            )
        )
    resources = declared.get("required_resource_ids")
    if not isinstance(resources, list) or not resources or any(
        not isinstance(resource_id, str) or RESOURCE_ID_RE.fullmatch(resource_id) is None
        for resource_id in resources
    ):
        findings.append(
            _plan_finding(
                "editorial_plan_industry_cluster_policy_invalid",
                "/industry_cluster_link_policy/required_resource_ids",
                "required_resource_ids must list at least one connector-shaped vault resource ID.",
            )
        )
    rationale = str(declared.get("rationale") or "").casefold()
    if "brief" not in rationale or "override" not in rationale:
        findings.append(
            _plan_finding(
                "editorial_plan_industry_cluster_policy_invalid",
                "/industry_cluster_link_policy/rationale",
                "Suppressed industry cluster policies must cite the brief override rationale.",
            )
        )
    return _sorted(findings)


def summarize_policy(
    content: str,
    *,
    plan: Mapping[str, Any] | None = None,
    context_resource_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """Return the deterministic BOM summary for the industry-cluster decision."""
    if link_policy_override_prohibits_industry_link(plan):
        return {
            "status": "not_applicable",
            "reason": "Valid exact internal-link override explicitly prohibits the industry cluster link.",
        }
    policy = resolve_required_policy(content=content, plan=plan)
    if policy is None:
        return {
            "status": "not_applicable",
            "reason": "No single-trade Simpro industry cluster link is required.",
        }
    link = _find_policy_link(content, policy)
    if link is None:
        anchor = ""
        position = None
        passed = False
    else:
        anchor = link.anchor
        position = link.word_position
        passed = (
            position <= MAX_INTRO_WORD_POSITION
            and _normalize_anchor(anchor) in _normalized_anchor_examples(policy)
        )
    required_resource_ids = _policy_required_resource_ids(plan, context_resource_ids)
    return {
        "status": "required",
        "industry": policy.key,
        "target": policy.target_url,
        "anchor": anchor,
        "placement": INTRO_PLACEMENT,
        "first_visible_word_position": position,
        "required_resource_ids": required_resource_ids,
        "passed": passed,
    }


def resolve_required_policy(
    *,
    content: str = "",
    plan: Mapping[str, Any] | None = None,
    brand: str | None = None,
) -> IndustryPolicy | None:
    """Return the required single-trade policy, or None if not applicable."""
    if link_policy_override_prohibits_industry_link(plan):
        return None
    resolved_brand = brand or _brand_from_plan(plan) or _brand_from_content(content)
    if resolved_brand != "simpro":
        return None
    detected = _detected_policy_keys(content=content, plan=plan)
    if len(detected) != 1:
        return None
    return POLICIES[detected[0]]


def resource_matches_policy(resource: Mapping[str, Any], policy: IndustryPolicy) -> bool:
    """Return whether connector resource metadata satisfies a vertical policy."""
    semantic_text = _resource_semantic_text(resource)
    if not semantic_text:
        return False
    tokens = set(semantic_text.split())
    if policy.key == "fire_protection":
        industry_match = "fire" in tokens and "protection" in tokens
    else:
        industry_match = policy.key in tokens
    vertical_match = bool(tokens & VERTICAL_RESOURCE_TERMS)
    return industry_match and vertical_match


def _article_findings(content: str, policy: IndustryPolicy) -> list[Finding]:
    link = _find_policy_link(content, policy)
    if link is None:
        return [
            _finding(
                "industry_cluster_link_missing",
                (
                    "Single-trade Simpro articles must link to the matching industry page "
                    "in the first 300 visible body words."
                ),
                suggestion=f"Add an intro link to {policy.target_url} with a destination-matched anchor.",
            )
        ]
    findings: list[Finding] = []
    normalized_anchor = _normalize_anchor(link.anchor)
    if normalized_anchor in GENERIC_LINK_ANCHORS or normalized_anchor not in _normalized_anchor_examples(policy):
        findings.append(
            _finding(
                "industry_cluster_link_anchor_invalid",
                "Industry cluster link anchor must match the destination keyword.",
                match=link.anchor,
                suggestion="Use one of the approved industry-page anchor examples.",
            )
        )
    if link.word_position > MAX_INTRO_WORD_POSITION:
        findings.append(
            _finding(
                "industry_cluster_link_late",
                (
                    "Industry cluster link appears after the first 300 visible body words "
                    f"at word position {link.word_position}."
                ),
                match=link.url,
                suggestion="Move the industry page link into the introduction after the direct answer.",
            )
        )
    return findings


def _find_policy_link(content: str, policy: IndustryPolicy) -> LinkMatch | None:
    body = _body(content)
    matches: list[LinkMatch] = []
    for match in MARKDOWN_LINK_RE.finditer(_blank_fenced_code(body)):
        anchor = match.group(1)
        url = match.group(2)
        normalized_path = _normalized_internal_path(url)
        if _same_path(normalized_path, _normalized_internal_path(policy.target_url)):
            matches.append(
                LinkMatch(
                    anchor=_visible_text(anchor),
                    url=url,
                    normalized_path=normalized_path,
                    word_position=_word_position(body[: match.start()]),
                )
            )
    for match in HTML_LINK_RE.finditer(_blank_fenced_code(body)):
        anchor = _visible_text(match.group("anchor"))
        url = match.group("url")
        normalized_path = _normalized_internal_path(url)
        if _same_path(normalized_path, _normalized_internal_path(policy.target_url)):
            matches.append(
                LinkMatch(
                    anchor=anchor,
                    url=url,
                    normalized_path=normalized_path,
                    word_position=_word_position(body[: match.start()]),
                )
            )
    return sorted(matches, key=lambda item: item.word_position)[0] if matches else None


def _has_matching_vertical_resource(
    pack: Mapping[str, Any] | None,
    receipt: Mapping[str, Any] | None,
    policy: IndustryPolicy,
) -> bool:
    for resource in _selected_resources(pack, receipt):
        if resource_matches_policy(resource, policy):
            return True
    return False


def _selected_resources(
    pack: Mapping[str, Any] | None,
    receipt: Mapping[str, Any] | None,
) -> list[Mapping[str, Any]]:
    selected_ids: set[str] = set()
    resources: list[Mapping[str, Any]] = []
    sections = pack.get("sections") if isinstance(pack, Mapping) else None
    if isinstance(sections, Mapping):
        discovery = sections.get("Discovery Trace")
        if isinstance(discovery, Mapping):
            for value in discovery.get("selected_resource_ids", []):
                if isinstance(value, str) and value:
                    selected_ids.add(value)
        for section_name in ("Selected Resource Inventory", "Retrieved Guidance"):
            rows = sections.get(section_name)
            if isinstance(rows, list):
                for row in rows:
                    if isinstance(row, Mapping):
                        resources.append(row)
    if isinstance(receipt, Mapping):
        rows = receipt.get("resources")
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, Mapping):
                    resources.append(row)
    if not selected_ids:
        return resources
    return [
        row
        for row in resources
        if isinstance(row.get("resource_id"), str) and row["resource_id"] in selected_ids
    ]


def _policy_required_resource_ids(
    plan: Mapping[str, Any] | None,
    context_resource_ids: Sequence[str],
) -> list[str]:
    declared = plan.get("industry_cluster_link_policy") if isinstance(plan, Mapping) else None
    if isinstance(declared, Mapping):
        resources = declared.get("required_resource_ids")
        if isinstance(resources, list):
            return [
                resource_id
                for resource_id in dict.fromkeys(
                    str(item).strip()
                    for item in resources
                    if isinstance(item, str) and item.strip()
                )
                if RESOURCE_ID_RE.fullmatch(resource_id)
            ]
    return [
        resource_id
        for resource_id in dict.fromkeys(str(item).strip() for item in context_resource_ids)
        if RESOURCE_ID_RE.fullmatch(resource_id)
    ]


def _resource_semantic_text(resource: Mapping[str, Any]) -> str:
    values: list[str] = []
    for field in ("title", "aliases", "headings", "topics", "semantic_roles"):
        value = resource.get(field)
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, list):
            values.extend(str(item) for item in value if isinstance(item, str))
    return _normalize_text(" ".join(values))


def _detected_policy_keys(
    *,
    content: str = "",
    plan: Mapping[str, Any] | None = None,
) -> list[str]:
    text = _normalize_text(" ".join((_content_signal_text(content), _plan_signal_text(plan))))
    keys: list[str] = []
    for key, policy in POLICIES.items():
        if any(_contains_phrase(text, signal) for signal in policy.signals):
            keys.append(key)
    return keys


def _content_signal_text(content: str) -> str:
    frontmatter, body = _frontmatter_and_body(content)
    return " ".join(
        value
        for value in (
            frontmatter.get("title", ""),
            frontmatter.get("objective", ""),
            frontmatter.get("audience", ""),
            body,
        )
        if value
    )


def _plan_signal_text(plan: Mapping[str, Any] | None) -> str:
    if not isinstance(plan, Mapping):
        return ""
    meta = plan.get("meta")
    reader = plan.get("reader_contract")
    values = [
        str(plan.get("topic") or ""),
        str(meta.get("meta_title") or "") if isinstance(meta, Mapping) else "",
        str(meta.get("primary_keyword") or "") if isinstance(meta, Mapping) else "",
        str(reader.get("primary_reader") or "") if isinstance(reader, Mapping) else "",
        str(reader.get("decision_task_helped") or "") if isinstance(reader, Mapping) else "",
    ]
    return " ".join(value for value in values if value)


def _frontmatter_and_body(content: str) -> tuple[dict[str, str], str]:
    match = FRONTMATTER_RE.match(content)
    if match is None:
        return {}, content
    frontmatter: dict[str, str] = {}
    for line in match.group("frontmatter").splitlines():
        if ":" not in line or line.startswith((" ", "\t", "-")):
            continue
        key, value = line.split(":", 1)
        frontmatter[key.strip().casefold()] = value.strip().strip("'\"")
    return frontmatter, content[match.end() :]


def _body(content: str) -> str:
    return _frontmatter_and_body(content)[1]


def _brand_from_content(content: str) -> str | None:
    frontmatter, _ = _frontmatter_and_body(content)
    brand = frontmatter.get("brand", "").strip().casefold()
    return brand or None


def _brand_from_plan(plan: Mapping[str, Any] | None) -> str | None:
    if not isinstance(plan, Mapping):
        return None
    raw = plan.get("brand")
    if isinstance(raw, str) and raw.strip():
        return raw.strip().casefold()
    meta = plan.get("meta")
    meta_title = meta.get("meta_title") if isinstance(meta, Mapping) else None
    if not isinstance(meta_title, str):
        return None
    match = re.search(r"\|\s*([^|]+?)\s*$", meta_title)
    return match.group(1).strip().casefold() if match else None


def _normalized_internal_path(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme in {"http", "https"}:
        hostname = (parsed.hostname or "").casefold().rstrip(".")
        if hostname not in BRAND_DOMAINS and not any(hostname.endswith(f".{domain}") for domain in BRAND_DOMAINS):
            return ""
        path = parsed.path
    elif parsed.scheme or parsed.netloc:
        return ""
    else:
        path = url
    cleaned = path.split("#", 1)[0].split("?", 1)[0].strip()
    if not cleaned.startswith("/"):
        cleaned = "/" + cleaned
    return re.sub(r"/+", "/", cleaned).rstrip("/") or "/"


def _same_target(left: str, right: str) -> bool:
    return _same_path(_normalized_internal_path(left), _normalized_internal_path(right))


def _same_path(left: str, right: str) -> bool:
    return bool(left and right and left == right)


def _blank_fenced_code(value: str) -> str:
    return re.sub(
        r"^(?:```|~~~).*?^(?:```|~~~)\s*$",
        " ",
        value,
        flags=re.MULTILINE | re.DOTALL,
    )


def _visible_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    text = re.sub(r"[*_`]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _word_position(prefix: str) -> int:
    visible = _visible_text(
        re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", prefix))
    )
    return len(re.findall(r"[A-Za-z0-9]+", visible)) + 1


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _normalize_anchor(value: str) -> str:
    return _normalize_text(_visible_text(value))


def _normalized_anchor_examples(policy: IndustryPolicy) -> set[str]:
    return {_normalize_anchor(anchor) for anchor in policy.anchor_examples}


def _contains_phrase(text: str, phrase: str) -> bool:
    normalized = _normalize_text(phrase)
    return bool(normalized and re.search(rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])", text))


def _load_plan(value: str | Path | Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return value
    if value is None:
        return None
    try:
        loaded = json.loads(Path(value).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, Mapping) else None


def _has_valid_link_policy_override(plan: Mapping[str, Any] | None) -> bool:
    if not isinstance(plan, Mapping):
        return False
    override = plan.get("link_policy_override")
    if not isinstance(override, Mapping):
        return False
    expected_fields = {
        "brief_path",
        "brief_sha256",
        "source_sentence",
        "exact_count",
        "scope",
    }
    if set(override) != expected_fields:
        return False
    shape_valid = (
        isinstance(override.get("brief_path"), str)
        and bool(str(override.get("brief_path")).strip())
        and isinstance(override.get("brief_sha256"), str)
        and re.fullmatch(r"[0-9a-f]{64}", str(override.get("brief_sha256"))) is not None
        and isinstance(override.get("source_sentence"), str)
        and bool(str(override.get("source_sentence")).strip())
        and isinstance(override.get("exact_count"), int)
        and not isinstance(override.get("exact_count"), bool)
        and 0 < int(override.get("exact_count")) <= 7
        and override.get("scope") == "pre_faq_body"
    )
    if not shape_valid or not link_policy_override_count_supported(
        str(override.get("source_sentence")),
        int(override.get("exact_count")),
    ):
        return False
    brief_path = Path(str(override.get("brief_path")))
    if not brief_path.is_absolute():
        brief_path = Path.cwd() / brief_path
    try:
        brief_bytes = brief_path.read_bytes()
        brief_text = brief_bytes.decode("utf-8")
    except (OSError, UnicodeError):
        return False
    if hashlib.sha256(brief_bytes).hexdigest() != override.get("brief_sha256"):
        return False
    return _normalize_policy_sentence(str(override.get("source_sentence"))) in _normalize_policy_sentence(
        brief_text
    )


def link_policy_override_count_supported(source_sentence: str, exact_count: int) -> bool:
    """Return whether an explicit brief sentence permits the selected exact count."""
    if not isinstance(exact_count, int) or isinstance(exact_count, bool):
        return False
    if exact_count <= 0 or exact_count > 7:
        return False
    normalized = _normalize_policy_sentence(source_sentence)
    if "link" not in normalized:
        return False
    token_pattern = r"(?:[1-7]|one|two|three|four|five|six|seven)"
    exact_match = re.search(rf"\bexactly\s+({token_pattern})\b", normalized)
    if exact_match:
        return _policy_number(exact_match.group(1)) == exact_count
    only_match = re.search(
        rf"\bonly\s+(?:these\s+)?({token_pattern})\b.*\binternal\s+links?\b",
        normalized,
    )
    if only_match:
        return _policy_number(only_match.group(1)) == exact_count
    range_match = re.search(
        rf"\b({token_pattern})\s*(?:-|to|through)\s*({token_pattern})\b",
        normalized,
    )
    if range_match:
        lower = _policy_number(range_match.group(1))
        upper = _policy_number(range_match.group(2))
        return lower is not None and upper is not None and lower <= exact_count <= upper
    upper_match = re.search(rf"\bup to\s+({token_pattern})\b", normalized)
    if upper_match:
        upper = _policy_number(upper_match.group(1))
        return upper is not None and exact_count <= upper
    return False


def link_policy_override_prohibits_industry_link(plan: Mapping[str, Any] | None) -> bool:
    """Return whether a valid override explicitly opts out of the industry link."""
    if not _has_valid_link_policy_override(plan):
        return False
    override = plan.get("link_policy_override") if isinstance(plan, Mapping) else None
    sentence = _normalize_policy_sentence(str(override.get("source_sentence") or ""))
    explicit_prohibitions = (
        "do not include the industry page",
        "do not include an industry page",
        "do not link to the industry page",
        "do not link to an industry page",
        "exclude the industry page",
        "exclude an industry page",
        "omit the industry page",
        "omit an industry page",
        "no industry page link",
        "no industry link",
    )
    if any(phrase in sentence for phrase in explicit_prohibitions):
        return True
    return False


def _policy_number(value: str) -> int | None:
    words = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
    }
    return int(value) if value.isdigit() else words.get(value)


def _normalize_policy_sentence(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold().replace("–", "-").replace("—", "-")).strip()


def _finding(
    rule_id: str,
    message: str,
    *,
    suggestion: str,
    match: str = "",
) -> Finding:
    return make_finding(
        rule_id,
        "error",
        1,
        match=match,
        message=message,
        suggestion=suggestion,
    )


def _plan_finding(rule_id: str, location: str, message: str) -> Finding:
    return {
        "severity": "error",
        "rule_id": rule_id,
        "message": message,
        "suggestion": "Regenerate the editorial plan with the required industry cluster link policy.",
        "location": location,
    }


def _sorted(findings: Sequence[Finding]) -> list[Finding]:
    return sorted(
        (dict(finding) for finding in findings),
        key=lambda finding: (
            str(finding.get("line") or ""),
            str(finding.get("location") or ""),
            str(finding.get("rule_id") or ""),
            str(finding.get("message") or ""),
        ),
    )
