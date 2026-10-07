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
    from . import sweep_checks, sweep_gates
    from .sweep_scoring import scorer_findings
    from .sweep_checks import arg
except ImportError:  # pragma: no cover - supports direct script execution.
    import context_binding_guard
    from blog_assembly.contracts import _visible_faq_questions
    from readiness.common import ARTICLE_GATES
    from readiness.gate_policy import skip_article_gate
    from readiness.pipeline_tail import _guard_kwargs
    import release_workflow.sweep_checks as sweep_checks
    import release_workflow.sweep_gates as sweep_gates
    from release_workflow.sweep_scoring import scorer_findings
    from release_workflow.sweep_checks import arg

SWEEP_SCHEMA = "simpro-blog-release-sweep/v1"
# ARTICLE_GATES entries the sweep never runs through check_file.
DEDICATED_GATES = {
    "editorial_plan": "dedicated check",
    "semrush_keyword_decision": "dedicated check",
    "paa_provenance": "dedicated check (faq_binding)",
    "blog_strategy": "dedicated check",
    "source_quality": "dedicated check",
}
SLOW_GATES = {"customer_proof_diversity": "slow; pass --include-slow"}
NETWORK_GATES = {"source_support": "offline"}
VAULT_GATES = {
    name: "needs vault connector"
    for name in (
        "named_feature_status", "competitive_shortlist", "fred_authority", "vault_brand_language"
    )
}
# Every dedicated release check, in run order (url_validator precedes its consumers).
RELEASE_CHECKS = (
    "pre_bom_report", "public_artifact", "ai_copy_linter", "url_validator",
    "public_research_links", "context_binding", "editorial_plan", "semrush_keyword_decision",
    "faq_binding", "blog_strategy", "source_quality", "customer_proof_no_fit", "content_scorer",
)
ARTICLE_TEXT_CHECKS = (
    "public_artifact", "ai_copy_linter", "url_validator", "public_research_links",
    "customer_proof_no_fit",
)
PLAN_CHECKS = ("blog_strategy", "source_quality")
RELEASE_ONLY = {
    "blog_assembly_bom": "release run only (needs the BOM)",
    "input_seal": "release run only (seals the BOM inputs)",
}

_pre_bom_rows = sweep_checks.pre_bom_rows
_plan_rows = sweep_checks.plan_rows
_keyword_rows = sweep_checks.keyword_rows
_faq_binding_rows = sweep_checks.faq_binding_rows
_strategy_rows = sweep_checks.strategy_rows
_source_quality_rows = sweep_checks.source_quality_rows
_public_artifact_rows = sweep_gates.public_artifact_rows
_ai_copy_rows = sweep_gates.ai_copy_rows
_url_validator_rows = sweep_gates.url_validator_rows
_research_link_rows = sweep_gates.research_link_rows
_context_binding_rows = sweep_gates.context_binding_rows
_no_fit_rows = sweep_gates.no_fit_rows


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


def _scorer_rows(
    args: Any, root: Path, runtime_policy: Mapping[str, Any], offline: bool = False
) -> list[dict[str, Any]]:
    return scorer_findings(sweep_checks.scorer_result(args, root, runtime_policy), offline=offline)


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


def _paa_artifact(args: Any, paa_policy: Mapping[str, Any] | None) -> Any:
    """Choose the PAA artifact by source kind, as ``_bom_runtime_policy`` does."""
    kind = (paa_policy or {}).get("source_kind")
    if kind == "brief_paa":
        return arg(args, "content_brief")
    if kind == "user_csv":
        return arg(args, "user_paa_csv")
    return arg(args, "paa_artifact")


def _runtime_policy(
    args: Any, *, article_text: str | None, paa_policy: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Pre-release stand-in for ``_bom_runtime_policy``; no BOM exists yet."""
    assembly_date = arg(args, "assembly_date")
    run_id = arg(args, "run_id")
    paa_kwargs = {
        "workflow_mode": arg(args, "workflow_mode"),
        "paa_artifact": _paa_artifact(args, paa_policy),
        "content_brief": arg(args, "content_brief"),
        "answersocrates_blocker": arg(args, "answersocrates_blocker"),
        "expected_collection_date": assembly_date,
        "expected_run_id": run_id,
    }
    if paa_policy and paa_policy.get("query"):
        paa_kwargs["expected_query"] = str(paa_policy["query"])
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
    paths = any(arg(args, name) for name in ("context_request", "context_pack", "context_receipt"))
    if article_text is None:
        return paths
    return paths or context_binding_guard.requires_context(article_text)


def _gate_skips(
    gates: Sequence[tuple[str, str, Any]], *, offline: bool, include_slow: bool,
    visible_faq: bool, context_required: bool,
) -> dict[str, str]:
    skip: dict[str, str] = dict(DEDICATED_GATES)
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


def _check_skips(
    *, article_text: str | None, offline: bool, plan_available: bool, context_required: bool,
) -> dict[str, str]:
    """Reasons the dedicated release checks do not run."""
    skip: dict[str, str] = {}
    if article_text is None:
        skip.update({name: "article unreadable" for name in ARTICLE_TEXT_CHECKS})
    if offline:
        skip.update({name: "offline" for name in ("url_validator", "public_research_links")})
    if not context_required:
        skip["context_binding"] = "not applicable (no context artifacts or Simpro signal)"
    elif offline:
        skip["context_binding"] = "needs vault connector"
    if not plan_available:
        skip.update({name: "requires --editorial-plan" for name in PLAN_CHECKS})
    return skip


def _release_checks(
    args: Any, root: Path, policy: Mapping[str, Any], text: str | None,
    state: Any, derived: Any, offline: bool = False,
) -> dict[str, Callable[[], Any]]:
    sidecar = arg(args, "proof_sidecar")
    return {
        "pre_bom_report": lambda: _pre_bom_rows(args, root),
        "public_artifact": lambda: _public_artifact_rows(text),
        "ai_copy_linter": lambda: _ai_copy_rows(text),
        "url_validator": lambda: _url_validator_rows(state),
        "public_research_links": lambda: _research_link_rows(text, sidecar, state),
        "context_binding": lambda: _context_binding_rows(args, policy),
        "editorial_plan": lambda: _plan_rows(args, root),
        "semrush_keyword_decision": lambda: _keyword_rows(args),
        "faq_binding": lambda: _faq_binding_rows(args, root, derived),
        "blog_strategy": lambda: _strategy_rows(args, root, state.peek()),
        "source_quality": lambda: _source_quality_rows(args),
        "customer_proof_no_fit": lambda: _no_fit_rows(text, policy),
        "content_scorer": lambda: _scorer_rows(args, root, policy, offline),
    }


def run_release_sweep(
    args: argparse.Namespace, *, workspace_root: Path, offline: bool, include_slow: bool
) -> dict[str, Any]:
    started = time.monotonic()
    root = Path(workspace_root)
    text = _read_article(args.article)
    derived = sweep_checks.derive_paa_policy(args)
    policy = _runtime_policy(args, article_text=text, paa_policy=derived[0])
    sidecar = arg(args, "proof_sidecar")
    context_required = _context_required(args, text)

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

    check_skip = _check_skips(
        article_text=text, offline=offline, plan_available=bool(arg(args, "editorial_plan")),
        context_required=context_required,
    )
    checks = _release_checks(
        args, root, policy, text, sweep_gates.UrlState(text, sidecar, root), derived,
        offline,
    )
    ran = [name for name in RELEASE_CHECKS if name not in check_skip]
    findings: list[dict[str, Any]] = []
    for name in ran:
        findings += run_check(name, checks[name])
    gate_skip = _gate_skips(
        ARTICLE_GATES, offline=offline, include_slow=include_slow,
        visible_faq=policy["visible_faq"], context_required=context_required,
    )
    findings += sweep_article_gates(
        ARTICLE_GATES, article=str(args.article), kwargs={}, skip=gate_skip, kwargs_for=kwargs_for
    )
    gate_names = [name for name, _label, _module in ARTICLE_GATES]
    skipped = [
        {"check": name, "reason": gate_skip[name]}
        for name in gate_names if name in gate_skip and name not in RELEASE_CHECKS
    ]
    skipped += [{"check": name, "reason": check_skip[name]} for name in RELEASE_CHECKS if name in check_skip]
    skipped += [{"check": name, "reason": reason} for name, reason in RELEASE_ONLY.items()]
    return {
        "schema": SWEEP_SCHEMA,
        "passed": not any(row["severity"] == "error" for row in findings),
        "findings": findings,
        "skipped": skipped,
        "checks_run": [
            *ran,
            *(n for n in gate_names if n not in gate_skip and n not in RELEASE_CHECKS),
        ],
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
