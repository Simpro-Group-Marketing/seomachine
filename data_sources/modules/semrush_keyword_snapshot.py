"""Captured editorial-plan and article bindings for Semrush decisions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


@dataclass(frozen=True)
class SemrushBindingDependencies:
    """Operations required to validate captured keyword bindings."""

    schema: str
    finding: Callable[..., dict[str, Any]]
    normalize: Callable[[str], str]
    split_frontmatter: Callable[..., Any]
    frontmatter_error: type[Exception]


def check_bindings(
    dependencies: SemrushBindingDependencies,
    payload: Mapping[str, Any],
    *,
    editorial_plan_path: str | Path | None,
    editorial_plan: Mapping[str, Any] | None,
    article_path: str | Path | None,
    article_content: str | None,
) -> list[dict[str, Any]]:
    """Validate optional plan and article bindings from captured payloads."""
    findings: list[dict[str, Any]] = []
    if editorial_plan_path is not None or editorial_plan is not None:
        findings.extend(check_editorial_plan_binding(
            dependencies,
            payload,
            editorial_plan_path,
            plan=editorial_plan,
        ))
    if article_path is not None or article_content is not None:
        findings.extend(check_article_binding(
            dependencies,
            payload,
            article_path,
            article_content=article_content,
        ))
    return findings


def check_editorial_plan_binding(
    dependencies: SemrushBindingDependencies,
    payload: Mapping[str, Any],
    editorial_plan_path: str | Path | None,
    *,
    plan: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    if plan is None:
        try:
            plan = json.loads(Path(str(editorial_plan_path)).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            return [dependencies.finding(
                "semrush_keyword_decision_plan_unreadable",
                f"Bound editorial plan cannot be read: {error}",
                "/",
                "Regenerate the BOM with a readable editorial plan.",
            )]
    if not isinstance(plan, Mapping):
        return [dependencies.finding(
            "semrush_keyword_decision_plan_invalid",
            "Bound editorial plan must be a JSON object.",
            "/",
            "Regenerate the editorial plan.",
        )]
    findings: list[dict[str, Any]] = []
    meta = plan.get("meta")
    keyword_decision = plan.get("keyword_decision")
    primary = str(payload.get("selected_primary_keyword") or "")
    secondary = list(payload.get("selected_secondary_keywords") or [])
    if isinstance(meta, Mapping):
        if dependencies.normalize(str(meta.get("primary_keyword") or "")) != dependencies.normalize(primary):
            findings.append(dependencies.finding(
                "semrush_keyword_decision_plan_primary_mismatch",
                "Editorial-plan primary keyword must match the Semrush-selected primary keyword.",
                "/selected_primary_keyword",
                "Regenerate the editorial plan from the current Semrush keyword decision.",
            ))
        if _normalized_list(meta.get("secondary_keywords"), dependencies.normalize) != _normalized_list(secondary, dependencies.normalize):
            findings.append(dependencies.finding(
                "semrush_keyword_decision_plan_secondary_mismatch",
                "Editorial-plan secondary keywords must match the Semrush-selected secondary keywords.",
                "/selected_secondary_keywords",
                "Regenerate the editorial plan from the current Semrush keyword decision.",
            ))
    if isinstance(keyword_decision, Mapping):
        if keyword_decision.get("artifact_schema") != dependencies.schema:
            findings.append(dependencies.finding(
                "semrush_keyword_decision_plan_schema_mismatch",
                "Editorial-plan keyword_decision must reference the current Semrush schema.",
                "/keyword_decision/artifact_schema",
                "Update the editorial-plan keyword_decision reference.",
            ))
        if dependencies.normalize(str(keyword_decision.get("selected_primary_keyword") or "")) != dependencies.normalize(primary):
            findings.append(dependencies.finding(
                "semrush_keyword_decision_plan_primary_mismatch",
                "Editorial-plan keyword_decision reference must match the Semrush artifact.",
                "/keyword_decision/selected_primary_keyword",
                "Regenerate the editorial plan from the current Semrush keyword decision.",
            ))
    else:
        findings.append(dependencies.finding(
            "semrush_keyword_decision_plan_reference_missing",
            "Editorial plan must include a keyword_decision reference.",
            "/keyword_decision",
            "Add the Semrush-backed keyword_decision object to the editorial plan.",
        ))
    return findings


def check_article_binding(
    dependencies: SemrushBindingDependencies,
    payload: Mapping[str, Any],
    article_path: str | Path | None,
    *,
    article_content: str | None,
) -> list[dict[str, Any]]:
    try:
        raw = article_content
        if raw is None:
            raw = Path(str(article_path)).read_text(encoding="utf-8")
        frontmatter, _, _ = dependencies.split_frontmatter(raw)
    except (OSError, UnicodeError, dependencies.frontmatter_error) as error:
        return [dependencies.finding(
            "semrush_keyword_decision_article_unreadable",
            f"Bound article cannot be read for keyword binding: {error}",
            "/",
            "Repair the article frontmatter before readiness.",
        )]
    primary = frontmatter.get("primary_keyword") or frontmatter.get("target_keyword")
    if isinstance(primary, str) and primary.strip():
        selected = str(payload.get("selected_primary_keyword") or "")
        if dependencies.normalize(primary) != dependencies.normalize(selected):
            return [dependencies.finding(
                "semrush_keyword_decision_article_primary_mismatch",
                "Article primary keyword metadata must match the Semrush-selected primary keyword.",
                "/primary_keyword",
                "Update article frontmatter or regenerate the Semrush keyword decision.",
            )]
    return []


def _normalized_list(value: Any, normalize: Callable[[str], str]) -> list[str]:
    if not isinstance(value, list):
        return []
    return [normalize(item) for item in value if isinstance(item, str)]


def sorted_findings(findings: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for finding in findings:
        key = tuple(
            str(finding.get(field) or "")
            for field in ("rule_id", "location", "message")
        )
        unique[key] = dict(finding)
    return sorted(unique.values(), key=lambda row: (row["location"], row["rule_id"], row["message"]))


__all__ = [
    "SemrushBindingDependencies",
    "sorted_findings",
    "check_article_binding",
    "check_bindings",
    "check_editorial_plan_binding",
]
