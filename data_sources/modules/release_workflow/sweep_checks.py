"""Dedicated checks for the one-pass release sweep.

Each function mirrors a call the real release path makes, but returns finding
rows instead of raising, so the sweep can report every blocker together.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Mapping

try:
    from ..blog_assembly.contracts import _visible_faq_questions
    from ..blog_assembly.policy import _derive_paa_policy
    from ..blog_creation_preflight import build_preflight_report
    from ..blog_strategy_plan_guard import check_content as check_strategy_content
    from ..commercial_pillar_index import load_index
    from ..editorial_plan.orchestration import check_file as check_editorial_plan_file
    from ..faq_structure import faq_questions_match
    from ..paa_provenance.results import check_file as check_paa_provenance_file
    from ..readiness.adapters import _score_content
    from ..readiness.runtime_policy import _runtime_scoring_metadata
    from ..semrush_keyword_decision_guard import check_file as check_keyword_file
    from ..source_quality_plan_guard import check_content as check_source_quality_content
    from .precheck import _release_stage_receipts
except ImportError:  # pragma: no cover - supports direct script execution.
    from blog_assembly.contracts import _visible_faq_questions
    from blog_assembly.policy import _derive_paa_policy
    from blog_creation_preflight import build_preflight_report
    from blog_strategy_plan_guard import check_content as check_strategy_content
    from commercial_pillar_index import load_index
    from editorial_plan.orchestration import check_file as check_editorial_plan_file
    from faq_structure import faq_questions_match
    from paa_provenance.results import check_file as check_paa_provenance_file
    from readiness.adapters import _score_content
    from readiness.runtime_policy import _runtime_scoring_metadata
    from semrush_keyword_decision_guard import check_file as check_keyword_file
    from source_quality_plan_guard import check_content as check_source_quality_content
    from release_workflow.precheck import _release_stage_receipts

Rows = list[Mapping[str, Any]]


def arg(args: Any, name: str) -> Any:
    return getattr(args, name, None)


def _text(path: Any) -> str | None:
    return None if path is None else str(path)


def _assembly_date(args: Any) -> date:
    raw = arg(args, "assembly_date")
    return date.fromisoformat(str(raw)) if raw else date.today()


def _json_object(path: Any) -> Mapping[str, Any] | None:
    if not path:
        return None
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    return value if isinstance(value, Mapping) else None


def _finding(rule_id: str, message: str) -> dict[str, str]:
    return {"rule_id": rule_id, "severity": "error", "message": message}


def plan_faq_policy_status(args: Any) -> str:
    """Read ``faq_policy.status`` from the editorial plan, as the BOM does; "" when absent."""
    try:
        plan = _json_object(arg(args, "editorial_plan"))
    except (OSError, UnicodeError, ValueError):
        return ""
    faq_policy = plan.get("faq_policy") if plan else None
    return str(faq_policy.get("status") or "") if isinstance(faq_policy, Mapping) else ""


def pre_bom_rows(args: Any, root: Path) -> Rows:
    """Mirror ``precheck.run_blog_release_precheck``'s pre-BOM call; keep every blocker."""
    stage_receipts = _release_stage_receipts(
        arg(args, "stage_receipts") or (), arg(args, "scrub_receipt") or ""
    )
    report = build_preflight_report(
        args.article,
        proof_sidecar=args.proof_sidecar,
        context_request=arg(args, "context_request"),
        context_pack=arg(args, "context_pack"),
        context_receipt=arg(args, "context_receipt"),
        keyword_decision=arg(args, "keyword_decision"),
        assembly_date=arg(args, "assembly_date"),
        output=None,
        scrub_receipt=arg(args, "scrub_receipt"),
        customer_proof_evidence=arg(args, "customer_proof_evidence"),
        fred_authority_evidence=arg(args, "fred_authority_evidence"),
        editorial_plan=arg(args, "editorial_plan"),
        serp_evidence=arg(args, "serp_evidence"),
        stage_receipts=stage_receipts,
        paa_artifact=arg(args, "paa_artifact"),
        content_brief=arg(args, "content_brief"),
        user_paa_csv=arg(args, "user_paa_csv"),
        answersocrates_blocker=arg(args, "answersocrates_blocker"),
        workspace_root=root,
    )
    return list(report.get("blockers") or [])


def plan_rows(args: Any, root: Path) -> Rows:
    """Mirror ``construction_support.validate_plan_inputs`` (editorial plan check)."""
    return check_editorial_plan_file(
        args.editorial_plan,
        article_path=args.article,
        serp_evidence_path=arg(args, "serp_evidence"),
        assembly_date=arg(args, "assembly_date"),
        expected_run_id=arg(args, "run_id"),
        workspace_root=root,
    )


def keyword_rows(args: Any) -> Rows:
    """Mirror ``construction_support.validate_plan_inputs`` (keyword decision check)."""
    return check_keyword_file(
        args.keyword_decision,
        article_path=args.article,
        editorial_plan_path=arg(args, "editorial_plan"),
        assembly_date=arg(args, "assembly_date"),
    )


def derive_paa_policy(args: Any) -> tuple[Mapping[str, Any] | None, str | None]:
    """Derive the PAA policy once; return ``(policy, None)`` or ``(None, error text)``."""
    try:
        policy = _derive_paa_policy(
            _json_object(arg(args, "editorial_plan")) or {},
            workflow_mode=arg(args, "workflow_mode"),
            paa_artifact_path=arg(args, "paa_artifact"),
            content_brief_path=arg(args, "content_brief"),
            user_paa_csv_path=arg(args, "user_paa_csv"),
            answersocrates_blocker_path=arg(args, "answersocrates_blocker"),
        )
    except (OSError, UnicodeError, ValueError) as error:
        return None, str(error)
    return policy, None


def faq_binding_rows(
    args: Any, root: Path, derived: tuple[Mapping[str, Any] | None, str | None]
) -> Rows:
    """Mirror ``construction_support.derive_and_validate_paa`` without stopping at the first miss."""
    policy, error_text = derived
    if policy is None:
        return [_finding("paa_policy_invalid", error_text or "PAA policy is unavailable")]
    article_text = Path(args.article).read_text(encoding="utf-8")
    workflow_mode = arg(args, "workflow_mode")
    rows: list[Mapping[str, Any]] = []
    try:
        matches = faq_questions_match(
            policy["selected_questions"],
            _visible_faq_questions(article_text),
            source_kind=str(policy["source_kind"]),
        )
    except ValueError as error:
        rows.append(_finding("faq_structure_unsupported", str(error)))
    else:
        if not matches:
            rows.append(_finding(
                "paa_policy_questions_mismatch",
                "paa_policy.selected_questions must match visible FAQ headings in order "
                "(case and punctuation are ignored except for brief_paa)",
            ))
    bound = {
        "brief_paa": arg(args, "content_brief"),
        "user_csv": arg(args, "user_paa_csv"),
    }.get(policy["source_kind"], arg(args, "paa_artifact"))
    rows.extend(check_paa_provenance_file(
        str(args.article),
        proof_sidecar=_text(args.proof_sidecar),
        workflow_mode=workflow_mode,
        content_brief=_text(arg(args, "content_brief")),
        answersocrates_blocker=_text(arg(args, "answersocrates_blocker")),
        expected_query=str(policy["query"]),
        expected_collection_date=arg(args, "assembly_date"),
        expected_run_id=arg(args, "run_id"),
        paa_artifact=_text(bound),
    ))
    return rows


def strategy_rows(args: Any, root: Path, url_summary: Any = None) -> Rows:
    """Mirror the ``blog_strategy`` content gate; ``url_summary`` is None when offline."""
    return check_strategy_content(
        Path(args.article).read_text(encoding="utf-8"),
        editorial_plan=_json_object(args.editorial_plan),
        index=load_index(args.commercial_pillar_index),
        today=_assembly_date(args),
        url_summary=url_summary,
        context_request=_json_object(arg(args, "context_request")),
        article_path=Path(args.article),
        artifact_root=root,
    )


def source_quality_rows(args: Any) -> Rows:
    """Mirror the ``source_quality`` content gate for current (v2 plan) strategy."""
    return check_source_quality_content(
        Path(args.article).read_text(encoding="utf-8"),
        proof_content=Path(args.proof_sidecar).read_text(encoding="utf-8"),
        editorial_plan=_json_object(args.editorial_plan),
        today=_assembly_date(args),
    )


def scorer_result(args: Any, root: Path, runtime_policy: Mapping[str, Any]) -> Mapping[str, Any]:
    """Mirror the readiness ``_score_content`` call with a pre-BOM runtime policy."""
    policy = dict(runtime_policy)
    policy["scoring_metadata"] = _runtime_scoring_metadata(_text(arg(args, "editorial_plan")))
    return _score_content(
        Path(args.article),
        _text(args.proof_sidecar),
        artifact_kind="blog",
        runtime_policy=policy,
        workspace_root=root,
    )

