"""One-pass release sweep: run every release check and collect all findings."""

from __future__ import annotations

import argparse
import inspect
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

try:
    from .. import context_binding_guard
    from ..blog_assembly.contracts import _visible_faq_questions
    from ..readiness.common import ARTICLE_GATES
    from ..readiness.gate_policy import skip_article_gate
    from ..readiness.pipeline_tail import _guard_kwargs
    from . import sweep_checks
    from .sweep_checks import arg
except ImportError:  # pragma: no cover - supports direct script execution.
    import context_binding_guard
    from blog_assembly.contracts import _visible_faq_questions
    from readiness.common import ARTICLE_GATES
    from readiness.gate_policy import skip_article_gate
    from readiness.pipeline_tail import _guard_kwargs
    import release_workflow.sweep_checks as sweep_checks
    from release_workflow.sweep_checks import arg

SWEEP_SCHEMA = "simpro-blog-release-sweep/v1"
DEDICATED_GATES = {
    "editorial_plan": "dedicated check",
    "semrush_keyword_decision": "dedicated check",
    "paa_provenance": "dedicated check (FAQ binding)",
    "blog_strategy": "dedicated check",
    "source_quality": "dedicated check",
}
SLOW_GATES = {"customer_proof_diversity": "slow; pass --include-slow"}
NETWORK_GATES = {
    "url_validator": "offline",
    "source_support": "offline",
    "public_research_links": "offline",
}
VAULT_GATES = {
    name: "needs vault connector"
    for name in (
        "named_feature_status", "competitive_shortlist", "fred_authority", "vault_brand_language"
    )
}
DEDICATED_CHECKS = (
    "pre_bom_report", "editorial_plan", "semrush_keyword_decision", "faq_binding",
    "content_scorer",
)
PLAN_CHECKS = ("blog_strategy", "source_quality")

_pre_bom_rows = sweep_checks.pre_bom_rows
_plan_rows = sweep_checks.plan_rows
_keyword_rows = sweep_checks.keyword_rows
_faq_binding_rows = sweep_checks.faq_binding_rows
_strategy_rows = sweep_checks.strategy_rows
_source_quality_rows = sweep_checks.source_quality_rows


def _row(check: str, raw: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "check": check,
        "rule_id": str(raw.get("rule_id") or raw.get("code") or "finding"),
        "severity": str(raw.get("severity") or "error"),
        "line": raw.get("line"),
        "message": str(raw.get("message") or raw.get("issue") or ""),
    }


def run_check(
    name: str, check: Callable[[], Iterable[Mapping[str, Any]] | None]
) -> list[dict[str, Any]]:
    try:
        return [_row(name, raw) for raw in (check() or [])]
    except Exception as error:  # noqa: BLE001 - the sweep must survive any guard failure.
        return [{
            "check": name, "rule_id": "sweep_check_crashed", "severity": "error",
            "line": None, "message": f"{type(error).__name__}: {error}",
        }]


def _supported_kwargs(function: Callable[..., Any], kwargs: Mapping[str, Any]) -> dict[str, Any]:
    parameters = inspect.signature(function).parameters
    return {name: value for name, value in kwargs.items() if name in parameters}


def sweep_article_gates(
    gates: Sequence[tuple[str, str, Any]], *, article: str,
    kwargs: Mapping[str, Any], skip: Mapping[str, str],
    kwargs_for: Callable[[str], Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, _label, module in gates:
        check_file = getattr(module, "check_file", None)
        if name in skip or check_file is None:
            continue
        gate_kwargs = kwargs_for(name) if kwargs_for is not None else kwargs
        rows += run_check(
            name, lambda f=check_file, k=gate_kwargs: f(article, **_supported_kwargs(f, k))
        )
    return rows


def scorer_findings(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    checks = (result.get("aeo_geo") or {}).get("checks") or {}
    return [
        {"rule_id": f"aeo_geo.{name}", "severity": "error", "line": None,
         "message": str(check.get("issue") or check.get("fix") or "check failed")}
        for name, check in checks.items()
        if isinstance(check, Mapping) and check.get("passed") is False
    ]


def _scorer_rows(args: Any, root: Path, runtime_policy: Mapping[str, Any]) -> list[dict[str, Any]]:
    return scorer_findings(sweep_checks.scorer_result(args, root, runtime_policy))


def _read_article(path: Any) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError, TypeError):
        return None


def _has_visible_faq(article_text: str | None) -> bool:
    if article_text is None:
        return True
    try:
        return bool(_visible_faq_questions(article_text))
    except ValueError:
        return True


def _runtime_policy(args: Any, *, article_text: str | None) -> dict[str, Any]:
    """Pre-release stand-in for ``_bom_runtime_policy``; no BOM exists yet."""
    assembly_date = arg(args, "assembly_date")
    run_id = arg(args, "run_id")
    paa_kwargs = {
        "workflow_mode": arg(args, "workflow_mode"),
        "paa_artifact": arg(args, "paa_artifact"),
        "content_brief": arg(args, "content_brief"),
        "answersocrates_blocker": arg(args, "answersocrates_blocker"),
        "expected_collection_date": assembly_date,
        "expected_run_id": run_id,
    }
    return {
        "visible_faq": _has_visible_faq(article_text),
        "editorial_plan": arg(args, "editorial_plan"),
        "keyword_decision": arg(args, "keyword_decision"),
        "serp_evidence": arg(args, "serp_evidence"),
        "commercial_pillar_index": arg(args, "commercial_pillar_index"),
        "current_strategy": True,
        "assembly_date": assembly_date,
        "run_id": run_id,
        "customer_proof_selector_evidence": arg(args, "customer_proof_evidence"),
        "fred_authority_evidence": arg(args, "fred_authority_evidence"),
        "faq_policy_status": "",
        "scoring_metadata": {},
        "paa_kwargs": paa_kwargs,
    }


def _context_required(args: Any, article_text: str | None) -> bool:
    if article_text is not None:
        return context_binding_guard.requires_context(article_text)
    return any(arg(args, name) for name in ("context_request", "context_pack", "context_receipt"))


def _skip_map(
    gates: Sequence[tuple[str, str, Any]], *, offline: bool, include_slow: bool,
    visible_faq: bool, context_required: bool, plan_available: bool,
) -> dict[str, str]:
    skip: dict[str, str] = dict(DEDICATED_GATES)
    if not plan_available:
        skip.update({name: "requires --editorial-plan" for name in PLAN_CHECKS})
    for name, _label, module in gates:
        if skip_article_gate(
            name, artifact_kind="blog", visible_faq=visible_faq,
            simpro_context_required=context_required,
        ):
            skip.setdefault(name, "not applicable")
        if not hasattr(module, "check_file"):
            skip.setdefault(name, "no file entry point")
    if not include_slow:
        for name, reason in SLOW_GATES.items():
            skip.setdefault(name, reason)
    if offline:
        for name, reason in {**NETWORK_GATES, **VAULT_GATES}.items():
            skip.setdefault(name, reason)
    return skip


def run_release_sweep(
    args: argparse.Namespace, *, workspace_root: Path, offline: bool, include_slow: bool
) -> dict[str, Any]:
    started = time.monotonic()
    root = Path(workspace_root)
    article_text = _read_article(args.article)
    policy = _runtime_policy(args, article_text=article_text)
    sidecar = arg(args, "proof_sidecar")

    def kwargs_for(name: str) -> Mapping[str, Any]:
        return _guard_kwargs(
            name,
            proof_sidecar_path=None if sidecar is None else str(sidecar),
            context_pack_path=arg(args, "context_pack"),
            context_receipt_path=arg(args, "context_receipt"),
            vault_root=None,
            validated_claim_set=None,
            runtime_policy=policy,
        )

    checks: dict[str, Callable[[], Any]] = {
        "pre_bom_report": lambda: _pre_bom_rows(args, root),
        "editorial_plan": lambda: _plan_rows(args, root),
        "semrush_keyword_decision": lambda: _keyword_rows(args),
        "faq_binding": lambda: _faq_binding_rows(args, root),
        "blog_strategy": lambda: _strategy_rows(args, root),
        "source_quality": lambda: _source_quality_rows(args),
        "content_scorer": lambda: _scorer_rows(args, root, policy),
    }
    plan_available = bool(arg(args, "editorial_plan"))
    dedicated = [*DEDICATED_CHECKS, *(PLAN_CHECKS if plan_available else ())]
    findings: list[dict[str, Any]] = []
    for name in dedicated:
        findings += run_check(name, checks[name])
    skip = _skip_map(
        ARTICLE_GATES, offline=offline, include_slow=include_slow,
        visible_faq=policy["visible_faq"],
        context_required=_context_required(args, article_text),
        plan_available=plan_available,
    )
    findings += sweep_article_gates(
        ARTICLE_GATES, article=str(args.article), kwargs={}, skip=skip, kwargs_for=kwargs_for
    )
    gate_names = [name for name, _label, _module in ARTICLE_GATES]
    return {
        "schema": SWEEP_SCHEMA,
        "passed": not any(row["severity"] == "error" for row in findings),
        "findings": findings,
        "skipped": [
            {"check": name, "reason": skip[name]} for name in gate_names if name in skip
        ],
        "checks_run": [*dedicated, *(n for n in gate_names if n not in skip)],
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
