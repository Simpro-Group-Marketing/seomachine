"""Validate post-write evidence that a final article fulfills a frozen plan."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import hashlib
import re
from typing import Any

from .contracts import Finding
from .contracts import _finding
from .contracts import _sorted_findings
from .text import _normalize_visible_text
from .text import _visible_article_text
from .text import _visible_sections_by_heading
from .v2 import EDITORIAL_PLAN_SCHEMA_V2


PLAN_FULFILLMENT_SCHEMA = "simpro-blog-plan-fulfillment/v1"
TOP_LEVEL_FIELDS = frozenset(
    {"schema", "editorial_plan_sha256", "article_sha256", "contributions"}
)
CONTRIBUTION_FIELDS = frozenset({"contribution_id", "actual_excerpt"})
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def check_fulfillment(
    value: Any,
    *,
    editorial_plan: Mapping[str, Any],
    editorial_plan_sha256: str,
    article_content: str,
) -> list[Finding]:
    """Return deterministic blockers without judging semantic writing quality."""
    if not isinstance(value, Mapping):
        return [_issue("plan_fulfillment_root_invalid", "/", "Fulfillment JSON must be an object.")]
    findings: list[Finding] = []
    findings.extend(_unknown_fields(value, TOP_LEVEL_FIELDS, ""))
    if value.get("schema") != PLAN_FULFILLMENT_SCHEMA:
        findings.append(_issue(
            "plan_fulfillment_schema_invalid",
            "/schema",
            f"Fulfillment must use {PLAN_FULFILLMENT_SCHEMA}.",
        ))
    if editorial_plan.get("schema") != EDITORIAL_PLAN_SCHEMA_V2:
        findings.append(_issue(
            "plan_fulfillment_editorial_plan_schema_invalid",
            "/editorial_plan_sha256",
            "Current fulfillment requires an editorial-plan v2 input.",
        ))
    findings.extend(_hash_findings(
        value,
        editorial_plan_sha256=editorial_plan_sha256,
        article_content=article_content,
    ))
    findings.extend(_contribution_findings(
        value.get("contributions"),
        editorial_plan=editorial_plan,
        article_content=article_content,
    ))
    return _sorted_findings(findings)


def _hash_findings(
    value: Mapping[str, Any],
    *,
    editorial_plan_sha256: str,
    article_content: str,
) -> list[Finding]:
    findings: list[Finding] = []
    plan_hash = value.get("editorial_plan_sha256")
    if not isinstance(plan_hash, str) or SHA256_RE.fullmatch(plan_hash) is None:
        findings.append(_issue("plan_fulfillment_plan_hash_invalid", "/editorial_plan_sha256", "Editorial-plan SHA-256 is invalid."))
    elif plan_hash != editorial_plan_sha256:
        findings.append(_issue("plan_fulfillment_plan_hash_mismatch", "/editorial_plan_sha256", "Fulfillment does not bind the supplied editorial plan."))
    article_hash = value.get("article_sha256")
    expected_article_hash = hashlib.sha256(article_content.encode("utf-8")).hexdigest()
    if not isinstance(article_hash, str) or SHA256_RE.fullmatch(article_hash) is None:
        findings.append(_issue("plan_fulfillment_article_hash_invalid", "/article_sha256", "Article SHA-256 is invalid."))
    elif article_hash != expected_article_hash:
        findings.append(_issue("plan_fulfillment_article_hash_mismatch", "/article_sha256", "Fulfillment is stale for the supplied article bytes."))
    return findings


def _contribution_findings(
    value: Any,
    *,
    editorial_plan: Mapping[str, Any],
    article_content: str,
) -> list[Finding]:
    rows = value if isinstance(value, list) else []
    findings: list[Finding] = []
    if not isinstance(value, list):
        findings.append(_issue("plan_fulfillment_contributions_invalid", "/contributions", "Contributions must be a JSON array."))
    plan_rows = {
        str(row.get("contribution_id")): row
        for row in editorial_plan.get("original_contributions", [])
        if isinstance(row, Mapping) and isinstance(row.get("contribution_id"), str)
    }
    findings.extend(_contribution_inventory_findings(rows, plan_rows))
    visible_content = _without_hidden_regions(article_content)
    visible_article = _visible_article_text(visible_content)
    sections = _visible_sections_by_heading(visible_content)
    for index, row in enumerate(rows):
        findings.extend(
            _contribution_row_findings(
                row,
                index=index,
                plan_rows=plan_rows,
                visible_article=visible_article,
                sections=sections,
            )
        )
    return findings


def _contribution_inventory_findings(
    rows: list[Any],
    plan_rows: Mapping[str, Mapping[str, Any]],
) -> list[Finding]:
    findings: list[Finding] = []
    ids = [
        str(row.get("contribution_id"))
        for row in rows
        if isinstance(row, Mapping) and isinstance(row.get("contribution_id"), str)
    ]
    counts = Counter(ids)
    for contribution_id in sorted(plan_rows):
        if counts[contribution_id] == 0:
            findings.append(_issue("plan_fulfillment_contribution_missing", "/contributions", f"Missing fulfillment for {contribution_id}."))
        elif counts[contribution_id] > 1:
            findings.append(_issue("plan_fulfillment_contribution_duplicate", "/contributions", f"Duplicate fulfillment for {contribution_id}."))
    for contribution_id in sorted(set(ids) - set(plan_rows)):
        findings.append(_issue("plan_fulfillment_contribution_extra", "/contributions", f"Unexpected fulfillment ID: {contribution_id}."))
    return findings


def _contribution_row_findings(
    row: Any,
    *,
    index: int,
    plan_rows: Mapping[str, Mapping[str, Any]],
    visible_article: str,
    sections: Mapping[str, str],
) -> list[Finding]:
    location = f"/contributions/{index}"
    if not isinstance(row, Mapping):
        return [_issue("plan_fulfillment_contribution_invalid", location, "Fulfillment row must be an object.")]
    findings = _unknown_fields(row, CONTRIBUTION_FIELDS, location)
    contribution_id = row.get("contribution_id")
    excerpt = row.get("actual_excerpt")
    if not isinstance(contribution_id, str) or not contribution_id.strip():
        findings.append(_issue("plan_fulfillment_contribution_invalid", f"{location}/contribution_id", "Contribution ID must be non-empty."))
        return findings
    if not isinstance(excerpt, str) or len(excerpt.split()) < 4:
        findings.append(_issue("plan_fulfillment_excerpt_not_substantive", f"{location}/actual_excerpt", "Actual excerpt must contain at least four words."))
        return findings
    normalized_excerpt = _normalize_visible_text(excerpt)
    if normalized_excerpt not in visible_article:
        findings.append(_issue("plan_fulfillment_excerpt_not_visible", f"{location}/actual_excerpt", "Actual excerpt is not visible in the final article."))
        return findings
    plan_row = plan_rows.get(contribution_id)
    target = str(plan_row.get("target_section") or "").strip().casefold() if plan_row else ""
    if target and normalized_excerpt not in sections.get(target, ""):
        findings.append(_issue("plan_fulfillment_excerpt_wrong_section", f"{location}/actual_excerpt", "Actual excerpt is outside its planned target section."))
    return findings


def _without_hidden_regions(content: str) -> str:
    visible = re.sub(r"<!--.*?-->", " ", content, flags=re.DOTALL)
    return re.sub(r"^(?:```|~~~).*?^(?:```|~~~)\s*$", " ", visible, flags=re.MULTILINE | re.DOTALL)


def _unknown_fields(value: Mapping[str, Any], allowed: frozenset[str], location: str) -> list[Finding]:
    return [
        _issue(
            "plan_fulfillment_unknown_field",
            f"{location}/{key}",
            f"Fulfillment contains unsupported field {key}.",
        )
        for key in sorted(set(value) - allowed)
    ]


def _issue(rule_id: str, location: str, message: str) -> Finding:
    return _finding(
        rule_id,
        message,
        location,
        "Regenerate fulfillment from the frozen plan and current visible article.",
    )


__all__ = ["PLAN_FULFILLMENT_SCHEMA", "check_fulfillment"]
