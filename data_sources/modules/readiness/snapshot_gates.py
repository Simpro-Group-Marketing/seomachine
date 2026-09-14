"""Special readiness gates backed by one immutable artifact snapshot."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Mapping

from .gates import ContentGateInputs, _json


Finding = dict[str, Any]


def run_editorial_plan_gate(
    guard_module: Any,
    *,
    article_path: Path,
    runtime_policy: Mapping[str, Any],
    content_gate_inputs: ContentGateInputs | None,
    telemetry: Any,
    timed_call: Callable[..., Any],
    missing_finding: Callable[[str, str, str], list[Finding]],
) -> list[Finding]:
    """Validate the plan from captured payloads when a session is available."""
    editorial_path = runtime_policy.get("editorial_plan")
    if not editorial_path:
        return missing_finding(
            "editorial_plan_missing",
            "Blog readiness requires a bound editorial plan.",
            "Regenerate the provisional BOM with --editorial-plan.",
        )
    if content_gate_inputs is None:
        return timed_call(
            telemetry,
            "gate.editorial_plan",
            guard_module.check_file,
            editorial_path,
            article_path=article_path,
            serp_evidence_path=runtime_policy.get("serp_evidence"),
            assembly_date=runtime_policy.get("assembly_date"),
            expected_run_id=runtime_policy.get("run_id"),
        )
    captured = content_gate_inputs.captured
    raw_snapshot = captured.optional_snapshot("serp_raw_capture")
    brief_snapshot = captured.optional_snapshot("content_brief")
    return timed_call(
        telemetry,
        "gate.editorial_plan",
        guard_module._check_loaded_plan,
        _json(captured, "editorial_plan"),
        plan_path=editorial_path,
        article_path=article_path,
        serp_evidence_path=runtime_policy.get("serp_evidence"),
        assembly_date=runtime_policy.get("assembly_date"),
        expected_run_id=runtime_policy.get("run_id"),
        article_content=content_gate_inputs.article_content,
        serp_evidence_payload=_json(captured, "serp_evidence"),
        raw_capture_snapshot=_raw_capture_view(captured, raw_snapshot),
        brief_content=(
            captured.bytes("content_brief").decode("utf-8")
            if brief_snapshot is not None
            else None
        ),
        brief_sha256=brief_snapshot.sha256 if brief_snapshot is not None else None,
        workspace_root=captured.workspace_root,
    )


def run_keyword_gate(
    guard_module: Any,
    *,
    article_path: Path,
    runtime_policy: Mapping[str, Any],
    content_gate_inputs: ContentGateInputs | None,
    telemetry: Any,
    timed_call: Callable[..., Any],
    missing_finding: Callable[[str, str, str], list[Finding]],
) -> list[Finding]:
    """Validate the keyword decision from captured payloads when available."""
    keyword_path = runtime_policy.get("keyword_decision")
    editorial_path = runtime_policy.get("editorial_plan")
    if not keyword_path or not editorial_path:
        return missing_finding(
            "semrush_keyword_decision_missing",
            "Blog readiness requires a bound Semrush keyword decision.",
            "Regenerate the provisional BOM with --keyword-decision.",
        )
    if content_gate_inputs is None:
        return timed_call(
            telemetry,
            "gate.semrush_keyword_decision",
            guard_module.check_file,
            keyword_path,
            article_path=article_path,
            editorial_plan_path=editorial_path,
            assembly_date=runtime_policy.get("assembly_date"),
        )
    return timed_call(
        telemetry,
        "gate.semrush_keyword_decision",
        guard_module.check_decision,
        _json(content_gate_inputs.captured, "keyword_decision"),
        article_path=article_path,
        article_content=content_gate_inputs.article_content,
        editorial_plan_path=editorial_path,
        editorial_plan=_json(content_gate_inputs.captured, "editorial_plan"),
        assembly_date=runtime_policy.get("assembly_date"),
    )


def _raw_capture_view(captured: Any, snapshot: Any) -> Any:
    if snapshot is None:
        return None
    return SimpleNamespace(
        path=snapshot.path,
        sha256=snapshot.sha256,
        payload=_json(captured, "serp_raw_capture"),
    )


def source_registry_state(session: Any, captured: Any) -> Any:
    """Return a lazy session cache lookup over exact captured registry bytes."""
    snapshot = captured.optional_snapshot("source_decision_registry")
    if session is None or snapshot is None:
        return None
    source = SimpleNamespace(
        path=snapshot.path,
        data=captured.bytes("source_decision_registry"),
        sha256=snapshot.sha256,
        payload=_json(captured, "source_decision_registry"),
    )
    return lambda: session.git_registry_state(snapshot.path, lambda: source)


__all__ = [
    "run_editorial_plan_gate",
    "run_keyword_gate",
    "source_registry_state",
]
