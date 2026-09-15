"""Serial editorial-plan orchestration over captured immutable inputs."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .contracts import Finding
from .contracts import _finding
from .contracts import _nested_string
from .contracts import _sorted_findings
from .dependencies import EditorialPlanDependencies
from .dependencies import default_editorial_plan_dependencies
from .final_article import _check_final_article_bindings
from .final_article import _check_plan_assembly_date
from .link_policy import _check_link_policy_override_binding
from .plan_validation import check_plan
from .serp_capture import _artifact_workspace_root
from .serp_validation import check_serp_evidence_payload


def check_file(
    path: str | Path,
    *,
    article_path: str | Path | None = None,
    serp_evidence_path: str | Path | None = None,
    assembly_date: str | None = None,
    expected_run_id: str | None = None,
    workspace_root: str | Path | None = None,
    dependencies: EditorialPlanDependencies | None = None,
) -> list[Finding]:
    """Return blocking findings for one editorial-plan JSON file."""
    dependencies = dependencies or default_editorial_plan_dependencies()
    source = Path(path)
    try:
        payload: Any = dependencies.load_json_object_snapshot(
            source,
            field="editorial plan",
        ).payload
    except ValueError as error:
        return [_finding(
            "editorial_plan_json_invalid",
            f"Editorial plan contains invalid JSON: {error}.",
            "/",
            "Write a valid simpro-blog-editorial-plan/v2 JSON object.",
        )]
    return _check_loaded_plan(
        payload,
        plan_path=source,
        article_path=article_path,
        serp_evidence_path=serp_evidence_path,
        assembly_date=assembly_date,
        expected_run_id=expected_run_id,
        workspace_root=workspace_root,
        dependencies=dependencies,
    )


def _check_loaded_plan(
    payload: Mapping[str, Any],
    *,
    plan_path: str | Path | None = None,
    article_path: str | Path | None,
    serp_evidence_path: str | Path | None,
    assembly_date: str | None,
    expected_run_id: str | None = None,
    article_content: str | None = None,
    serp_evidence_payload: Mapping[str, Any] | None = None,
    raw_capture_snapshot: Any = None,
    brief_content: str | None = None,
    brief_sha256: str | None = None,
    workspace_root: str | Path | None = None,
    dependencies: EditorialPlanDependencies | None = None,
) -> list[Finding]:
    """Validate one plan payload already parsed from immutable bytes."""
    dependencies = dependencies or default_editorial_plan_dependencies()
    findings = check_plan(payload, dependencies=dependencies)
    findings.extend(_check_plan_assembly_date(payload, assembly_date))
    if serp_evidence_path is not None or serp_evidence_payload is not None:
        findings.extend(_serp_findings(
            payload,
            plan_path=plan_path,
            serp_evidence_path=serp_evidence_path,
            serp_evidence_payload=serp_evidence_payload,
            raw_capture_snapshot=raw_capture_snapshot,
            assembly_date=assembly_date,
            expected_run_id=expected_run_id,
            workspace_root=workspace_root,
            dependencies=dependencies,
        ))
    if article_path is not None or article_content is not None:
        findings.extend(_check_final_article_bindings(
            payload,
            article_path,
            assembly_date=assembly_date,
            article_content=article_content,
            dependencies=dependencies,
        ))
        findings.extend(_check_link_policy_override_binding(
            payload,
            article_path=article_path,
            plan_path=plan_path,
            article_content=article_content,
            brief_content=brief_content,
            brief_sha256=brief_sha256,
            dependencies=dependencies,
        ))
    return _sorted_findings(findings)


def _serp_findings(
    payload: Mapping[str, Any],
    *,
    plan_path: str | Path | None,
    serp_evidence_path: str | Path | None,
    serp_evidence_payload: Mapping[str, Any] | None,
    raw_capture_snapshot: Any,
    assembly_date: str | None,
    expected_run_id: str | None,
    workspace_root: str | Path | None,
    dependencies: EditorialPlanDependencies,
) -> list[Finding]:
    expected_query = _nested_string(payload, "meta", "primary_keyword")
    serp_payload, findings = _resolve_serp_payload(
        serp_evidence_path,
        serp_evidence_payload,
        expected_query=expected_query,
        assembly_date=assembly_date,
        expected_run_id=expected_run_id,
        workspace_root=workspace_root,
        raw_capture_snapshot=raw_capture_snapshot,
        dependencies=dependencies,
    )
    is_v2 = payload.get("schema") == "simpro-blog-editorial-plan/v2"
    strategy = payload.get("search_strategy" if is_v2 else "serp_strategy")
    if isinstance(strategy, Mapping) and isinstance(serp_payload, Mapping):
        if is_v2:
            from .v2 import check_search_evidence_binding

            findings.extend(check_search_evidence_binding(strategy, serp_payload))
        else:
            from .field_validation import _check_serp_strategy_evidence_binding

            findings.extend(_check_serp_strategy_evidence_binding(strategy, serp_payload))
    if isinstance(strategy, Mapping) and str(strategy.get("status") or "").startswith(
        "unresolved"
    ):
        findings.append(_finding(
            "editorial_plan_serp_strategy_unresolved",
            "Editorial plan must record resolved intent and SERP decisions.",
            "/serp_strategy/status",
            "Regenerate the plan from the bound verified SERP evidence.",
        ))
    return findings


def _resolve_serp_payload(
    path: str | Path | None,
    payload: Mapping[str, Any] | None,
    *,
    expected_query: str,
    assembly_date: str | None,
    expected_run_id: str | None,
    workspace_root: str | Path | None,
    raw_capture_snapshot: Any,
    dependencies: EditorialPlanDependencies,
) -> tuple[Mapping[str, Any] | None, list[Finding]]:
    if payload is not None:
        root = workspace_root
    else:
        payload, root, load_findings = _load_serp_payload(
            path,
            workspace_root,
            dependencies,
        )
        if load_findings:
            return payload, load_findings
    findings = check_serp_evidence_payload(
        payload,
        expected_query=expected_query,
        assembly_date=assembly_date,
        expected_run_id=expected_run_id,
        workspace_root=root,
        raw_capture_snapshot=raw_capture_snapshot,
        dependencies=dependencies,
    )
    return payload, findings


def _load_serp_payload(
    path: str | Path | None,
    workspace_root: str | Path | None,
    dependencies: EditorialPlanDependencies,
) -> tuple[Mapping[str, Any] | None, Path | None, list[Finding]]:
    source = Path(str(path))
    root = _artifact_workspace_root(source, workspace_root)
    try:
        payload = dependencies.load_json_object_snapshot(
            source,
            field="SERP evidence",
        ).payload
    except ValueError as error:
        return None, root, [_finding(
            "serp_evidence_unreadable",
            f"SERP evidence cannot be read as UTF-8 JSON: {error}",
            "/",
            "Regenerate the verified SERP evidence artifact.",
        )]
    if not isinstance(payload, Mapping):
        return None, root, [_finding(
            "serp_evidence_root_invalid",
            "SERP evidence JSON must be an object.",
            "/",
            "Regenerate the verified SERP evidence artifact.",
        )]
    return payload, root, []


__all__ = ["_check_loaded_plan", "check_file"]
