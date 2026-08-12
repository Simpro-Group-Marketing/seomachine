"""Publish readiness runner.

Runs the existing blog proof and quality gates in one deterministic order so
agents do not have to copy the full command stack by hand.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

try:
    from . import (
        ai_copy_linter,
        answer_withholding_guard,
        blog_assembly_bom_guard,
        blog_identity_guard,
        context_binding_guard,
        customer_proof_diversity_guard,
        early_artifact_guard,
        editorial_plan_guard,
        faq_answer_quality_guard,
        fred_authority_guard,
        faq_proof_guard,
        metric_proof_pack_guard,
        named_feature_status_guard,
        numeric_claim_source_guard,
        paa_provenance_guard,
        public_research_link_guard,
        public_artifact_guard,
        review_story_identity_guard,
        source_support_guard,
        vault_brand_language_guard,
    )
    from .content_scorer import ContentScorer
    from .blog_assembly_contract import (
        artifact_inventory_snapshots,
        atomic_write_json,
        canonical_artifact,
        canonical_article_run_id,
        canonical_json_bytes,
        expected_blog_gate_inventory,
        file_sha256,
        is_json_number,
        load_json_object_snapshot,
        order_blog_gate_results,
        resolve_artifact,
        validate_sha256,
        verify_artifact,
    )
    from .blog_assembly_stage_receipt import (
        build_stage_receipt,
        check_receipt_chain,
        write_stage_receipt,
    )
    from .landing_page_scorer import LandingPageScorer
    from .publishable_markdown import FrontmatterError, read_publishable_markdown
    from .readiness_gate_context import _issue_readiness_gate_context
    from .guard_common import should_fail, summarize_findings
    from .url_validator import UrlValidationSummary, validate_file_urls
except ImportError:  # pragma: no cover - supports direct script execution.
    import ai_copy_linter
    import answer_withholding_guard
    import blog_assembly_bom_guard
    import blog_identity_guard
    import context_binding_guard
    import customer_proof_diversity_guard
    import early_artifact_guard
    import editorial_plan_guard
    import faq_answer_quality_guard
    import fred_authority_guard
    import faq_proof_guard
    import metric_proof_pack_guard
    import named_feature_status_guard
    import numeric_claim_source_guard
    import paa_provenance_guard
    import public_research_link_guard
    import public_artifact_guard
    import review_story_identity_guard
    import source_support_guard
    import vault_brand_language_guard
    from content_scorer import ContentScorer
    from blog_assembly_contract import (
        artifact_inventory_snapshots,
        atomic_write_json,
        canonical_artifact,
        canonical_article_run_id,
        canonical_json_bytes,
        expected_blog_gate_inventory,
        file_sha256,
        is_json_number,
        load_json_object_snapshot,
        order_blog_gate_results,
        resolve_artifact,
        validate_sha256,
        verify_artifact,
    )
    from blog_assembly_stage_receipt import (
        build_stage_receipt,
        check_receipt_chain,
        write_stage_receipt,
    )
    from landing_page_scorer import LandingPageScorer
    from publishable_markdown import FrontmatterError, read_publishable_markdown
    from readiness_gate_context import _issue_readiness_gate_context
    from guard_common import should_fail, summarize_findings
    from url_validator import UrlValidationSummary, validate_file_urls


GateResult = Dict[str, Any]
ReadinessResult = Dict[str, Any]


_READINESS_EXECUTION_KEY = os.urandom(32)


class _ExecutedReadinessResult(dict[str, Any]):
    """Process-local proof that the result came from the complete gate runner."""

    __slots__ = ("_execution_signature", "_workspace_root")

    def __init__(self, value: Mapping[str, Any], *, workspace_root: Path) -> None:
        super().__init__(value)
        self._workspace_root = workspace_root.resolve()
        self._execution_signature = _sign_readiness_execution(self)


def _sign_readiness_execution(value: Mapping[str, Any]) -> str:
    return hmac.new(
        _READINESS_EXECUTION_KEY,
        canonical_json_bytes(value),
        hashlib.sha256,
    ).hexdigest()

READINESS_RESULT_SCHEMA = "simpro-publish-readiness-result/v1"
READINESS_TOOL = {"name": "publish_readiness", "version": "1.0.0"}
PASSED_RESULT_FIELDS = frozenset(
    {
        "schema",
        "tool",
        "phase",
        "verification_scope",
        "file",
        "proof_sidecar",
        "context_request",
        "context_pack",
        "context_receipt",
        "assembly_bom",
        "passed",
        "artifact_kind",
        "gates",
        "score",
        "score_threshold",
        "aeo_geo",
        "priority_fixes",
        "gate_inventory",
        "input_hashes",
        "input_seal",
        "run_id",
        "started_at",
        "completed_at",
    }
)
GATE_RESULT_FIELDS = frozenset(
    {"name", "label", "passed", "errors", "warnings", "findings", "blockers"}
)


ARTICLE_GATES = (
    (
        "metric_proof_pack",
        "Metric Proof Pack",
        metric_proof_pack_guard,
    ),
    (
        "numeric_claim_source",
        "Numeric Claim Source",
        numeric_claim_source_guard,
    ),
    (
        "faq_answer_quality",
        "FAQ Answer Quality",
        faq_answer_quality_guard,
    ),
    (
        "faq_proof",
        "FAQ Proof",
        faq_proof_guard,
    ),
    (
        "paa_provenance",
        "PAA Provenance",
        paa_provenance_guard,
    ),
    (
        "editorial_plan",
        "Editorial Plan",
        editorial_plan_guard,
    ),
    (
        "source_support",
        "Source Support",
        source_support_guard,
    ),
    (
        "customer_proof_diversity",
        "Customer Proof Diversity",
        customer_proof_diversity_guard,
    ),
    (
        "review_story_identity",
        "Review Story Identity",
        review_story_identity_guard,
    ),
    (
        "early_artifact",
        "Early Artifact",
        early_artifact_guard,
    ),
    (
        "answer_withholding",
        "Answer Withholding",
        answer_withholding_guard,
    ),
    (
        "vault_brand_language",
        "Vault Brand Language",
        vault_brand_language_guard,
    ),
    (
        "named_feature_status",
        "Named Feature Status",
        named_feature_status_guard,
    ),
    (
        "fred_authority",
        "Fred Voccola Authority",
        fred_authority_guard,
    ),
)


SIMPRO_CONTEXT_GATE_NAMES = frozenset({
    "vault_brand_language",
    "named_feature_status",
})


def run_publish_readiness(
    file_path: str | Path,
    *,
    proof_sidecar: str | Path | None = None,
    context_request: str | Path | None = None,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    assembly_bom: str | Path | None = None,
    vault_root: str | Path | None = None,
    ai_profile: str = "simpro-web",
    phase: str = "preflight",
    workspace_root: str | Path | None = None,
) -> ReadinessResult:
    """Run the complete gate stack inside one trusted workspace boundary."""
    if phase not in {"preflight", "final"}:
        raise ValueError("phase must be preflight or final")
    root = Path(workspace_root or Path.cwd()).resolve()
    article_path = _resolve_workspace_input(file_path, workspace_root=root, field="file")
    proof_path = _resolve_optional_workspace_input(
        proof_sidecar,
        workspace_root=root,
        field="proof_sidecar",
    )
    request_path = _resolve_optional_workspace_input(
        context_request,
        workspace_root=root,
        field="context_request",
    )
    pack_path = _resolve_optional_workspace_input(
        context_pack,
        workspace_root=root,
        field="context_pack",
    )
    receipt_path = _resolve_optional_workspace_input(
        context_receipt,
        workspace_root=root,
        field="context_receipt",
    )
    bom_path = _resolve_optional_workspace_input(
        assembly_bom,
        workspace_root=root,
        field="assembly_bom",
    )
    raw = _run_publish_readiness(
        article_path,
        proof_sidecar=proof_path,
        context_request=request_path,
        context_pack=pack_path,
        context_receipt=receipt_path,
        assembly_bom=bom_path,
        vault_root=vault_root,
        ai_profile=ai_profile,
        phase=phase,
        workspace_root=root,
    )
    return _ExecutedReadinessResult(raw, workspace_root=root)


def _run_publish_readiness(
    file_path: str | Path,
    *,
    proof_sidecar: str | Path | None = None,
    context_request: str | Path | None = None,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    assembly_bom: str | Path | None = None,
    vault_root: str | Path | None = None,
    ai_profile: str = "simpro-web",
    phase: str = "preflight",
    workspace_root: str | Path,
) -> ReadinessResult:
    """Run the full publish-readiness stack and return structured results."""
    if phase not in {"preflight", "final"}:
        raise ValueError("phase must be preflight or final")
    run_started_at = _utc_now()
    article_path = Path(file_path)
    proof_sidecar_path = str(proof_sidecar) if proof_sidecar is not None else None
    context_request_path = str(context_request) if context_request is not None else None
    context_pack_path = str(context_pack) if context_pack is not None else None
    context_receipt_path = str(context_receipt) if context_receipt is not None else None
    assembly_bom_path = str(assembly_bom) if assembly_bom is not None else None
    readiness_root = Path(workspace_root).resolve()
    try:
        article = read_publishable_markdown(article_path)
    except FrontmatterError as exc:
        gate = _gate_from_findings(
            "frontmatter_metadata",
            "Frontmatter Metadata",
            [{
                "rule_id": "frontmatter_invalid",
                "severity": "error",
                "line": 1,
                "column": 1,
                "message": str(exc),
                "suggestion": "Repair the YAML frontmatter before publishing.",
            }],
        )
        return {
            "schema": "simpro-publish-readiness-result/v1",
            "phase": phase,
            "verification_scope": "source_artifact",
            "file": str(article_path),
            "proof_sidecar": proof_sidecar_path,
            "context_request": context_request_path,
            "context_pack": context_pack_path,
            "context_receipt": context_receipt_path,
            "assembly_bom": assembly_bom_path,
            "passed": False,
            "artifact_kind": None,
            "gates": [gate],
            "score": None,
            "score_threshold": 85,
            "aeo_geo": {"score": None, "threshold": 90, "passed": False},
            "priority_fixes": [
                {"dimension": "frontmatter_metadata", "issue": str(exc)}
            ],
        }
    article_content = article.raw
    try:
        artifact_kind = context_binding_guard.require_artifact_kind(
            article_content,
            article_path=article_path,
        )
    except ValueError as error:
        message = str(error)
        normalized = message.casefold()
        if "unsupported" in normalized:
            rule_id = "artifact_kind_unsupported"
        elif "conflict" in normalized:
            rule_id = "artifact_kind_conflict"
        else:
            rule_id = "artifact_kind_missing"
        identity_gate = _gate_from_findings(
            "artifact_identity",
            "Artifact Identity",
            [{
                "rule_id": rule_id,
                "severity": "error",
                "line": 1,
                "column": 1,
                "message": message,
                "suggestion": "Declare one supported artifact_type in frontmatter.",
            }],
        )
        return {
            "schema": "simpro-publish-readiness-result/v1",
            "phase": phase,
            "file": str(article_path),
            "proof_sidecar": proof_sidecar_path,
            "context_request": context_request_path,
            "context_pack": context_pack_path,
            "context_receipt": context_receipt_path,
            "assembly_bom": assembly_bom_path,
            "verification_scope": "source_artifact",
            "passed": False,
            "artifact_kind": None,
            "gates": [identity_gate],
            "score": None,
            "score_threshold": 85,
            "aeo_geo": {"score": None, "threshold": 90, "passed": False},
            "priority_fixes": [
                {"dimension": "artifact_identity", "issue": message}
            ],
        }
    score_threshold = 75 if artifact_kind == "landing_page" else 85
    gates: List[GateResult] = []
    runtime_policy = _bom_runtime_policy(
        assembly_bom_path,
        workspace_root=readiness_root,
    )
    identity_gate = _gate_from_findings(
        "artifact_identity",
        "Artifact Identity",
        blog_identity_guard.check_article(
            article_content,
            assembly_date=runtime_policy.get("assembly_date") or None,
        ),
    )
    gates.append(identity_gate)
    if not identity_gate["passed"]:
        return {
            "schema": "simpro-publish-readiness-result/v1",
            "phase": phase,
            "file": str(article_path),
            "proof_sidecar": proof_sidecar_path,
            "context_request": context_request_path,
            "context_pack": context_pack_path,
            "context_receipt": context_receipt_path,
            "assembly_bom": assembly_bom_path,
            "verification_scope": "source_artifact",
            "passed": False,
            "artifact_kind": artifact_kind,
            "gates": gates,
            "score": None,
            "score_threshold": score_threshold,
            "aeo_geo": {"score": None, "threshold": 90, "passed": False},
            "priority_fixes": [
                {"dimension": "artifact_identity", "issue": blocker}
                for blocker in identity_gate.get("blockers", [])
            ],
        }

    context_result = context_binding_guard.validate_context_artifacts(
        str(article_path),
        fail_on="error",
        proof_sidecar=proof_sidecar_path,
        context_request=context_request_path,
        context_pack=context_pack_path,
        context_receipt=context_receipt_path,
        vault_root=vault_root,
    )
    context_gate = _gate_from_findings(
        "context_binding",
        "Context Binding",
        list(context_result.findings),
    )
    gates.append(context_gate)
    if not context_gate["passed"]:
        return {
            "schema": "simpro-publish-readiness-result/v1",
            "phase": phase,
            "verification_scope": "source_artifact",
            "file": str(article_path),
            "proof_sidecar": proof_sidecar_path,
            "context_request": context_request_path,
            "context_pack": context_pack_path,
            "context_receipt": context_receipt_path,
            "assembly_bom": assembly_bom_path,
            "passed": False,
            "artifact_kind": artifact_kind,
            "gates": gates,
            "score": None,
            "score_threshold": score_threshold,
            "aeo_geo": {"score": None, "threshold": 90, "passed": False},
            "priority_fixes": [
                {
                    "dimension": "context_binding",
                    "issue": blocker,
                }
                for blocker in context_gate.get("blockers", [])
            ],
        }

    bom_required = artifact_kind == "blog"
    sealed_input_hashes: Dict[str, Dict[str, str]] | None = None
    if bom_required and assembly_bom_path is None:
        bom_gate = _gate_from_findings(
            "blog_assembly_bom",
            "Blog Assembly BOM",
            [blog_assembly_bom_guard.missing_bom_finding()],
        )
        gates.append(bom_gate)
        return {
            "schema": "simpro-publish-readiness-result/v1",
            "phase": phase,
            "verification_scope": "source_artifact",
            "file": str(article_path),
            "proof_sidecar": proof_sidecar_path,
            "context_request": context_request_path,
            "context_pack": context_pack_path,
            "context_receipt": context_receipt_path,
            "assembly_bom": assembly_bom_path,
            "passed": False,
            "artifact_kind": artifact_kind,
            "gates": gates,
            "score": None,
            "score_threshold": score_threshold,
            "aeo_geo": {"score": None, "threshold": 90, "passed": False},
            "priority_fixes": [
                {
                    "dimension": "blog_assembly_bom",
                    "issue": blocker,
                }
                for blocker in bom_gate.get("blockers", [])
            ],
        }

    if assembly_bom_path is not None:
        bom_gate = _gate_from_findings(
            "blog_assembly_bom",
            "Blog Assembly BOM",
            blog_assembly_bom_guard.check_bom_file(
                assembly_bom_path,
                article_path=article_path,
                validation_sidecar_path=proof_sidecar_path or "",
                context_request_path=context_request_path,
                context_pack_path=context_pack_path,
                context_receipt_path=context_receipt_path,
                workspace_root=readiness_root,
                expected_lifecycle_state=(
                    "provisional" if phase == "preflight" else "final"
                ),
                context_result=context_result,
                vault_root=vault_root,
            ),
        )
        gates.append(bom_gate)
        if not bom_gate["passed"]:
            return {
                "schema": "simpro-publish-readiness-result/v1",
                "phase": phase,
                "verification_scope": "source_artifact",
                "file": str(article_path),
                "proof_sidecar": proof_sidecar_path,
                "context_request": context_request_path,
                "context_pack": context_pack_path,
                "context_receipt": context_receipt_path,
                "assembly_bom": assembly_bom_path,
                "passed": False,
                "artifact_kind": artifact_kind,
                "gates": gates,
                "score": None,
                "score_threshold": score_threshold,
                "aeo_geo": {"score": None, "threshold": 90, "passed": False},
                "priority_fixes": [
                    {
                        "dimension": "blog_assembly_bom",
                        "issue": blocker,
                    }
                    for blocker in bom_gate.get("blockers", [])
                ],
            }
        try:
            sealed_input_hashes = _complete_readiness_input_hashes(
                article=article_path,
                validation_sidecar=proof_sidecar_path,
                context_request=context_request_path,
                context_pack=context_pack_path,
                context_receipt=context_receipt_path,
                assembly_bom=assembly_bom_path,
                workspace_root=readiness_root,
            )
        except ValueError as error:
            seal_gate = _gate_from_findings(
                "input_seal",
                "Input Seal",
                [{
                    "rule_id": "readiness_input_snapshot_invalid",
                    "severity": "error",
                    "line": 1,
                    "column": 1,
                    "message": str(error),
                    "suggestion": "Regenerate the BOM from unchanged current artifacts.",
                }],
            )
            gates.append(seal_gate)
            return {
                "schema": "simpro-publish-readiness-result/v1",
                "phase": phase,
                "verification_scope": "source_artifact",
                "file": str(article_path),
                "proof_sidecar": proof_sidecar_path,
                "context_request": context_request_path,
                "context_pack": context_pack_path,
                "context_receipt": context_receipt_path,
                "assembly_bom": assembly_bom_path,
                "passed": False,
                "artifact_kind": artifact_kind,
                "gates": gates,
                "score": None,
                "score_threshold": score_threshold,
                "aeo_geo": {"score": None, "threshold": 90, "passed": False},
                "priority_fixes": [{
                    "dimension": "input_seal",
                    "issue": str(error),
                }],
            }

    gates.append(
        _gate_from_findings(
            "public_artifact",
            "Public Artifact",
            public_artifact_guard.check_file(str(article_path), fail_on="error"),
        )
    )

    ai_findings = ai_copy_linter.lint_file(
        str(article_path),
        profile=ai_profile,
        fail_on="error",
    )
    gates.append(
        _gate_from_findings(
            "ai_copy_linter",
            "AI Copy Linter",
            ai_findings,
        )
    )

    url_summary = validate_file_urls(article_path)
    gates.append(_gate_from_url_summary(url_summary))

    gates.append(
        _gate_from_findings(
            "public_research_links",
            "Public Research Links",
            public_research_link_guard.check_file(
                str(article_path),
                fail_on="error",
                proof_sidecar=proof_sidecar_path,
                url_summary=url_summary,
            ),
        )
    )

    simpro_context_required = context_binding_guard.requires_context(article_content)
    prevalidated_gate_findings: Dict[
        str,
        tuple[Mapping[str, Any], ...],
    ] = {}
    for name, label, guard_module in ARTICLE_GATES:
        if name in {"faq_answer_quality", "faq_proof"} and not runtime_policy["visible_faq"]:
            continue
        if name in SIMPRO_CONTEXT_GATE_NAMES and not simpro_context_required:
            continue
        if name == "fred_authority" and not simpro_context_required:
            continue
        guard_kwargs: Dict[str, Any] = {
            "fail_on": "error",
            "proof_sidecar": proof_sidecar_path,
        }
        if name in {
            "named_feature_status",
            "customer_proof_diversity",
            "fred_authority",
            "vault_brand_language",
        }:
            guard_kwargs.update(
                {
                    "context_pack": context_pack_path,
                    "context_receipt": context_receipt_path,
                }
            )
        if name == "named_feature_status":
            guard_kwargs["vault_root"] = vault_root
        if name == "fred_authority":
            guard_kwargs["vault_root"] = vault_root
        if name == "paa_provenance":
            guard_kwargs.update(runtime_policy["paa_kwargs"])
        if name == "editorial_plan":
            editorial_path = runtime_policy.get("editorial_plan")
            findings = (
                guard_module.check_file(
                    editorial_path,
                    article_path=article_path,
                    serp_evidence_path=runtime_policy.get("serp_evidence"),
                    assembly_date=runtime_policy.get("assembly_date"),
                    expected_run_id=runtime_policy.get("run_id"),
                )
                if editorial_path
                else [{
                    "rule_id": "editorial_plan_missing",
                    "severity": "error",
                    "line": 1,
                    "column": 1,
                    "message": "Blog readiness requires a bound editorial plan.",
                    "suggestion": "Regenerate the provisional BOM with --editorial-plan.",
                }]
            )
        else:
            findings = guard_module.check_file(str(article_path), **guard_kwargs)
        prevalidated_gate_findings[name] = tuple(
            dict(finding) for finding in findings
        )
        gates.append(_gate_from_findings(name, label, findings))

    proof_sidecar_content = (
        Path(proof_sidecar_path).read_text(encoding="utf-8")
        if proof_sidecar_path is not None
        else None
    )
    readiness_gate_context = _issue_readiness_gate_context(
        prevalidated_gate_findings,
        article_content=article_content,
        proof_sidecar_content=proof_sidecar_content,
        input_hashes=sealed_input_hashes or {},
        workspace_root=readiness_root,
    )

    scorer_result = _score_content(
        article_path,
        proof_sidecar_path,
        artifact_kind=artifact_kind or "blog",
        assembly_bom=assembly_bom_path,
        runtime_policy=runtime_policy,
        workspace_root=readiness_root,
        readiness_gate_context=readiness_gate_context,
    )
    gates.append(_gate_from_score(scorer_result))

    current_input_hashes: Dict[str, Dict[str, str]]
    try:
        current_input_hashes = _complete_readiness_input_hashes(
            article=article_path,
            validation_sidecar=proof_sidecar_path,
            context_request=context_request_path,
            context_pack=context_pack_path,
            context_receipt=context_receipt_path,
            assembly_bom=assembly_bom_path,
            workspace_root=readiness_root,
        )
        seal_findings = []
        if artifact_kind == "blog" and current_input_hashes != sealed_input_hashes:
            seal_findings = [{
                "rule_id": "readiness_inputs_changed_during_run",
                "severity": "error",
                "line": 1,
                "column": 1,
                "message": "One or more bound artifacts changed during readiness.",
                "suggestion": (
                    "Resume at the mutation receipt, then rerun scrub, Context Binding, "
                    "BOM build, and readiness."
                ),
            }]
    except ValueError as error:
        current_input_hashes = sealed_input_hashes or {}
        seal_findings = [{
            "rule_id": "readiness_inputs_changed_during_run",
            "severity": "error",
            "line": 1,
            "column": 1,
            "message": str(error),
            "suggestion": (
                "Resume at the mutation receipt, then rerun scrub, Context Binding, "
                "BOM build, and readiness."
            ),
        }]

    if artifact_kind == "blog":
        gates.append(
            _gate_from_findings(
                "input_seal",
                "Input Seal",
                seal_findings,
            )
        )
        try:
            gates = [
                dict(row)
                for row in order_blog_gate_results(
                    gates,
                    visible_faq=bool(runtime_policy["visible_faq"]),
                    connector_required=simpro_context_required,
                )
            ]
        except ValueError:
            gates.append(
                _gate_from_findings(
                    "readiness_contract",
                    "Readiness Contract",
                    [{
                        "rule_id": "readiness_gate_inventory_invalid",
                        "severity": "error",
                        "line": 1,
                        "column": 1,
                        "message": (
                            "Readiness gate order drifted from the closed blog contract."
                        ),
                        "suggestion": (
                            "Restore the expected conditional gate inventory before sealing."
                        ),
                    }],
                )
            )

    passed = all(gate["passed"] for gate in gates)
    result = {
        "schema": "simpro-publish-readiness-result/v1",
        "tool": {"name": "publish_readiness", "version": "1.0.0"},
        "phase": phase,
        "verification_scope": "source_artifact",
        "file": str(article_path),
        "proof_sidecar": proof_sidecar_path,
        "context_request": context_request_path,
        "context_pack": context_pack_path,
        "context_receipt": context_receipt_path,
        "assembly_bom": assembly_bom_path,
        "passed": passed,
        "artifact_kind": artifact_kind,
        "gates": gates,
        "score": _content_score(scorer_result),
        "score_threshold": scorer_result.get("threshold", 85),
        "aeo_geo": scorer_result.get("aeo_geo", {}),
        "priority_fixes": scorer_result.get("priority_fixes", []),
        "gate_inventory": [gate["name"] for gate in gates],
        "input_hashes": current_input_hashes,
        "input_seal": {
            "status": "verified" if not seal_findings else "failed",
        },
        "run_id": _readiness_run_id(assembly_bom_path, article.sha256),
        "started_at": run_started_at,
        "completed_at": _utc_now(),
    }
    if phase == "final" and assembly_bom_path:
        result["final_bom_sha256"] = file_sha256(assembly_bom_path)
    return result


def readiness_stage_receipt_path(output_path: str | Path) -> Path:
    """Return the deterministic detached receipt path for a readiness output."""
    output = Path(output_path)
    return output.with_name(f"{output.stem}-stage-receipt.json")


def write_readiness_result(
    output_path: str | Path,
    result: Mapping[str, Any],
    *,
    receipt_path: str | Path | None = None,
    workspace_root: str | Path | None = None,
) -> Path | None:
    """Write the result and, when passed, its non-circular stage receipt."""
    root = _result_workspace_root(result, workspace_root)
    output = _resolve_workspace_input(
        output_path,
        workspace_root=root,
        field="readiness output",
    )
    destination = (
        _resolve_workspace_input(
            receipt_path,
            workspace_root=root,
            field="readiness receipt",
        )
        if receipt_path is not None
        else readiness_stage_receipt_path(output)
    )
    _reject_output_input_collision(output, result, workspace_root=root)
    if result.get("passed") is not True:
        atomic_write_json(output, result)
        return None
    validate_passed_readiness_result(result, workspace_root=root)
    input_rows = result.get("input_hashes")
    input_hashes = {
        str(label): str(row.get("sha256"))
        for label, row in input_rows.items()
        if isinstance(row, Mapping) and isinstance(row.get("sha256"), str)
    }
    article_hash = input_hashes.get("article")
    if not article_hash:
        raise ValueError("passed readiness result requires the article input hash")
    bom_path = result.get("assembly_bom")
    previous_hash = ""
    optimized = False
    prior_receipts: list[Mapping[str, Any]] = []
    bom_assembly_date: str | None = None
    canonical_run_id: str | None = None
    if isinstance(bom_path, str) and bom_path:
        try:
            bom = load_json_object_snapshot(bom_path, field="assembly BOM").payload
        except ValueError as error:
            raise ValueError(f"readiness BOM is unavailable: {error}") from error
        workflow = bom.get("workflow") if isinstance(bom, Mapping) else None
        bom_assembly_date = (
            str(bom.get("assembly_date"))
            if isinstance(bom, Mapping) and isinstance(bom.get("assembly_date"), str)
            else None
        )
        if bom_assembly_date is None:
            raise ValueError("readiness BOM requires a canonical assembly_date")
        canonical_run_id = canonical_article_run_id(
            str(result.get("file") or ""),
            workspace_root=root,
            assembly_date=bom_assembly_date,
        )
        receipts = workflow.get("stage_receipts") if isinstance(workflow, Mapping) else None
        if isinstance(receipts, list) and receipts:
            if any(not isinstance(row, Mapping) for row in receipts):
                raise ValueError("readiness BOM contains an invalid stage receipt chain")
            prior_receipts = list(receipts)
            last = receipts[-1]
            if isinstance(last, Mapping):
                previous_hash = str(last.get("receipt_hash") or "")
            optimized = any(
                isinstance(row, Mapping) and row.get("stage") == "optimization"
                for row in receipts
            )
    if result.get("phase") == "final":
        stage = "final_readiness_attestation"
    elif optimized:
        stage = "final_preflight_readiness"
    else:
        stage = "preflight_readiness"
    if _same_path(destination, output):
        raise ValueError("readiness receipt cannot overwrite readiness output")
    _reject_output_input_collision(
        destination,
        result,
        output_label="readiness receipt",
        workspace_root=root,
    )
    output_digest = hashlib.sha256(canonical_json_bytes(result)).hexdigest()
    receipt = build_stage_receipt(
        run_id=str(result.get("run_id") or ""),
        stage=stage,
        tool_name="publish_readiness",
        tool_version="1.0.0",
        started_at=str(result.get("started_at") or ""),
        completed_at=str(result.get("completed_at") or ""),
        mutation=False,
        input_artifact_hashes=input_hashes,
        output_artifact_hashes={
            "article": article_hash,
            "readiness_output": output_digest,
        },
        evidence_hashes={
            label: digest
            for label, digest in input_hashes.items()
            if label not in {"article", "assembly_bom"}
        },
        previous_receipt_hash=previous_hash,
    )
    if prior_receipts:
        if canonical_run_id is None or bom_assembly_date is None:
            raise ValueError(
                "readiness stage receipt requires canonical workflow identity"
            )
        chain_findings = check_receipt_chain(
            [*prior_receipts, receipt],
            expected_run_id=canonical_run_id,
            assembly_date=bom_assembly_date,
        )
        if chain_findings:
            rules = ", ".join(
                sorted({str(finding["rule_id"]) for finding in chain_findings})
            )
            raise ValueError(f"readiness stage receipt chain is invalid: {rules}")
    _validate_actual_readiness_execution(result, workspace_root=root)
    output_existed = output.is_file()
    previous_output = output.read_bytes() if output_existed else None
    atomic_write_json(output, result)
    try:
        write_stage_receipt(destination, receipt)
    except Exception:
        _restore_file_after_failed_pair_write(
            output,
            existed=output_existed,
            previous_bytes=previous_output,
        )
        raise
    return destination


def _validate_actual_readiness_execution(
    result: Mapping[str, Any],
    *,
    workspace_root: Path,
) -> None:
    if not isinstance(result, _ExecutedReadinessResult):
        raise ValueError(
            "passed readiness output requires an actual publish-readiness execution"
        )
    if os.path.normcase(str(result._workspace_root)) != os.path.normcase(
        str(workspace_root.resolve())
    ):
        raise ValueError("readiness execution workspace_root changed before persistence")
    expected = _sign_readiness_execution(result)
    if not hmac.compare_digest(result._execution_signature, expected):
        raise ValueError(
            "passed readiness output changed after its actual publish-readiness execution"
        )


def validate_passed_readiness_result(
    result: Mapping[str, Any],
    *,
    workspace_root: str | Path | None = None,
) -> None:
    """Reject caller-invented pass payloads that do not match the closed contract."""
    phase = result.get("phase")
    expected_fields = set(PASSED_RESULT_FIELDS)
    if phase == "final":
        expected_fields.add("final_bom_sha256")
    if set(result) != expected_fields:
        raise ValueError("passed readiness result must use the exact result field set")
    if result.get("schema") != READINESS_RESULT_SCHEMA:
        raise ValueError(f"passed readiness result must use {READINESS_RESULT_SCHEMA}")
    if result.get("tool") != READINESS_TOOL:
        raise ValueError("passed readiness result uses the wrong readiness tool identity")
    if phase not in {"preflight", "final"}:
        raise ValueError("passed readiness result phase must be preflight or final")
    if result.get("verification_scope") != "source_artifact":
        raise ValueError("passed readiness result must declare source_artifact verification")
    if result.get("passed") is not True:
        raise ValueError("passed readiness result must declare passed true")
    root = _result_workspace_root(result, workspace_root)

    file_value = result.get("file")
    if not isinstance(file_value, str):
        raise ValueError("passed readiness result file must identify the current article")
    file_path = _resolve_workspace_input(
        file_value,
        workspace_root=root,
        field="readiness article",
    )
    if not file_path.is_file():
        raise ValueError("passed readiness result file must identify the current article")
    try:
        article = read_publishable_markdown(file_path)
        actual_kind = context_binding_guard.require_artifact_kind(
            article.raw,
            article_path=file_path,
        )
    except (FrontmatterError, ValueError) as error:
        raise ValueError(f"passed readiness result article identity is invalid: {error}") from error
    artifact_kind = result.get("artifact_kind")
    if artifact_kind != actual_kind:
        raise ValueError("passed readiness artifact_kind does not match the article")

    gates = result.get("gates")
    inventory = result.get("gate_inventory")
    if not isinstance(gates, list) or not gates:
        raise ValueError("passed readiness result is missing the expected gate inventory")
    if not isinstance(inventory, list) or not inventory:
        raise ValueError("passed readiness result is missing the expected gate inventory")
    names: list[str] = []
    for index, gate in enumerate(gates):
        if not isinstance(gate, Mapping) or set(gate) != GATE_RESULT_FIELDS:
            raise ValueError(f"passed readiness gate {index} has an invalid shape")
        name = gate.get("name")
        label = gate.get("label")
        if not isinstance(name, str) or not name or not isinstance(label, str) or not label:
            raise ValueError(f"passed readiness gate {index} requires a name and label")
        if (
            gate.get("passed") is not True
            or gate.get("errors") != 0
            or not isinstance(gate.get("warnings"), int)
            or isinstance(gate.get("warnings"), bool)
            or gate.get("warnings", -1) < 0
            or not isinstance(gate.get("findings"), list)
            or gate.get("blockers") != []
        ):
            raise ValueError(f"passed readiness gate {name} is not a completed pass")
        names.append(name)
    if len(names) != len(set(names)) or inventory != names:
        raise ValueError("passed readiness result has an invalid gate inventory")

    bom_path = result.get("assembly_bom")
    if artifact_kind == "blog":
        if not isinstance(bom_path, str):
            raise ValueError("passed blog readiness requires the bound assembly BOM")
        resolved_bom = _resolve_workspace_input(
            bom_path,
            workspace_root=root,
            field="readiness assembly_bom",
        )
        if not resolved_bom.is_file():
            raise ValueError("passed blog readiness requires the bound assembly BOM")
        try:
            bom = load_json_object_snapshot(
                resolved_bom, field="assembly BOM"
            ).payload
        except ValueError as error:
            raise ValueError(f"passed readiness BOM is unavailable: {error}") from error
        if not isinstance(bom, Mapping):
            raise ValueError("passed readiness BOM must be an object")
        expected_lifecycle = "provisional" if phase == "preflight" else "final"
        if bom.get("lifecycle_state") != expected_lifecycle:
            raise ValueError(
                f"{phase} readiness requires a {expected_lifecycle} assembly BOM"
            )
        schema_policy = bom.get("schema_policy")
        connector_binding = bom.get("connector_binding")
        visible_faq = bool(
            isinstance(schema_policy, Mapping)
            and schema_policy.get("visible_faq") is True
        )
        connector_required = bool(
            context_binding_guard.requires_context(article.raw)
            or (
                isinstance(connector_binding, Mapping)
                and connector_binding.get("status") == "required"
            )
        )
        expected_inventory = expected_blog_gate_inventory(
            visible_faq=visible_faq,
            connector_required=connector_required,
        )
        if names != expected_inventory:
            raise ValueError("passed readiness result does not contain the expected gate inventory")

    score_value = result.get("score")
    score_threshold = result.get("score_threshold")
    expected_threshold = 75 if artifact_kind == "landing_page" else 85
    if (
        not _is_number(score_value)
        or score_threshold != expected_threshold
        or float(score_value) < expected_threshold
    ):
        raise ValueError("passed readiness result does not meet its content score threshold")
    aeo_geo = result.get("aeo_geo")
    if not isinstance(aeo_geo, Mapping):
        raise ValueError("passed readiness result requires an AEO/GEO result")
    if artifact_kind == "blog":
        if (
            not _is_number(aeo_geo.get("score"))
            or aeo_geo.get("threshold") != 90
            or aeo_geo.get("passed") is not True
            or float(aeo_geo["score"]) < 90
        ):
            raise ValueError("passed blog readiness does not meet the AEO/GEO threshold")
    elif aeo_geo.get("passed") is not True:
        raise ValueError("passed readiness result contains a failed AEO/GEO result")
    if not isinstance(result.get("priority_fixes"), list):
        raise ValueError("passed readiness priority_fixes must be a list")
    if not isinstance(result.get("run_id"), str) or not str(result["run_id"]).strip():
        raise ValueError("passed readiness result requires a run_id")

    _verify_result_inputs_unchanged(result, workspace_root=root)
    _verify_result_path_bindings(result, workspace_root=root)
    expected_inputs = _complete_readiness_input_hashes(
        article=str(result["file"]),
        validation_sidecar=(
            result.get("proof_sidecar")
            if isinstance(result.get("proof_sidecar"), str)
            else None
        ),
        context_request=(
            result.get("context_request")
            if isinstance(result.get("context_request"), str)
            else None
        ),
        context_pack=(
            result.get("context_pack")
            if isinstance(result.get("context_pack"), str)
            else None
        ),
        context_receipt=(
            result.get("context_receipt")
            if isinstance(result.get("context_receipt"), str)
            else None
        ),
        assembly_bom=(
            result.get("assembly_bom")
            if isinstance(result.get("assembly_bom"), str)
            else None
        ),
        workspace_root=root,
    )
    if result.get("input_hashes") != expected_inputs:
        raise ValueError(
            "passed readiness result must bind the complete exact readiness input inventory"
        )


def _verify_result_path_bindings(
    result: Mapping[str, Any],
    *,
    workspace_root: str | Path,
) -> None:
    rows = result.get("input_hashes")
    if not isinstance(rows, Mapping):
        raise ValueError("passed readiness result requires input_hashes")
    root = Path(workspace_root).resolve()
    bindings = {
        "article": "file",
        "validation_sidecar": "proof_sidecar",
        "context_request": "context_request",
        "context_pack": "context_pack",
        "context_receipt": "context_receipt",
        "assembly_bom": "assembly_bom",
    }
    for label, field in bindings.items():
        declared = result.get(field)
        row = rows.get(label)
        if declared is None:
            if row is not None:
                raise ValueError(f"readiness input {label} is not bound to {field}")
            continue
        if not isinstance(declared, str) or not isinstance(row, Mapping):
            raise ValueError(f"readiness input {label} is missing its path binding")
        stored = row.get("path")
        if not isinstance(stored, str):
            raise ValueError(f"readiness input {label} has an invalid path binding")
        try:
            bound_path = _resolve_workspace_input(
                declared,
                workspace_root=root,
                field=field,
            )
            stored_path = resolve_artifact(stored, workspace_root=root)
        except ValueError as error:
            raise ValueError(f"readiness input {label} has an invalid path binding") from error
        if not _same_path(bound_path, stored_path):
            raise ValueError(f"readiness input {label} does not match its declared path")


def _is_number(value: Any) -> bool:
    return is_json_number(value)


def _same_path(left: str | Path, right: str | Path) -> bool:
    return os.path.normcase(str(Path(left).resolve())) == os.path.normcase(
        str(Path(right).resolve())
    )


def _restore_file_after_failed_pair_write(
    path: Path,
    *,
    existed: bool,
    previous_bytes: bytes | None,
) -> None:
    if not existed:
        path.unlink(missing_ok=True)
        return
    if previous_bytes is None:
        raise RuntimeError("readiness output rollback bytes are unavailable")
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".rollback.tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(previous_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _readiness_run_id(assembly_bom: str | None, article_hash: str) -> str:
    if assembly_bom:
        try:
            bom = load_json_object_snapshot(
                assembly_bom, field="assembly BOM"
            ).payload
        except ValueError:
            bom = None
        workflow = bom.get("workflow") if isinstance(bom, Mapping) else None
        receipts = workflow.get("stage_receipts") if isinstance(workflow, Mapping) else None
        if isinstance(receipts, list) and receipts and isinstance(receipts[0], Mapping):
            run_id = receipts[0].get("run_id")
            if isinstance(run_id, str) and run_id.strip():
                return run_id.strip()
    return f"readiness-{article_hash[:16]}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _resolve_workspace_input(
    value: str | Path,
    *,
    workspace_root: str | Path,
    field: str,
) -> Path:
    """Resolve one caller path without allowing a BOM to widen the trust root."""
    root = Path(workspace_root).resolve()
    raw = Path(value)
    candidate = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        common = Path(os.path.commonpath((str(root), str(candidate))))
    except ValueError as error:
        raise ValueError(f"{field} must remain inside workspace_root") from error
    if os.path.normcase(str(common)) != os.path.normcase(str(root)):
        raise ValueError(f"{field} must remain inside workspace_root")
    return candidate


def _resolve_optional_workspace_input(
    value: str | Path | None,
    *,
    workspace_root: str | Path,
    field: str,
) -> Path | None:
    if value is None:
        return None
    return _resolve_workspace_input(value, workspace_root=workspace_root, field=field)


def _result_workspace_root(
    result: Mapping[str, Any],
    workspace_root: str | Path | None,
) -> Path:
    if workspace_root is not None:
        root = Path(workspace_root).resolve()
    elif isinstance(result, _ExecutedReadinessResult):
        root = result._workspace_root
    else:
        root = Path.cwd().resolve()
    if (
        isinstance(result, _ExecutedReadinessResult)
        and os.path.normcase(str(root))
        != os.path.normcase(str(result._workspace_root))
    ):
        raise ValueError("readiness result workspace_root does not match its execution")
    return root


def _verify_result_inputs_unchanged(
    result: Mapping[str, Any],
    *,
    workspace_root: str | Path,
) -> None:
    """Reject persistence of a pass after any attested input changed."""
    if result.get("input_seal") != {"status": "verified"}:
        raise ValueError("passed readiness result requires a verified input seal")
    rows = result.get("input_hashes")
    if not isinstance(rows, Mapping) or not rows:
        raise ValueError("passed readiness result requires input_hashes")
    root = Path(workspace_root).resolve()
    for label, row in rows.items():
        if not isinstance(row, Mapping) or set(row) != {"path", "sha256"}:
            raise ValueError(f"readiness input {label} must contain only path and sha256")
        digest = validate_sha256(row.get("sha256"), field=f"input_hashes.{label}.sha256")
        stored = row.get("path")
        if not isinstance(stored, str) or not stored:
            raise ValueError(f"input_hashes.{label}.path must be a non-empty string")
        candidate = resolve_artifact(stored, workspace_root=root)
        if not candidate.is_file() or file_sha256(candidate) != digest:
            raise ValueError(f"readiness input {label} changed after gate execution")
    if result.get("phase") == "final":
        assembly_row = rows.get("assembly_bom")
        if (
            not isinstance(assembly_row, Mapping)
            or result.get("final_bom_sha256") != assembly_row.get("sha256")
        ):
            raise ValueError("final readiness must bind the exact final BOM hash")


def _reject_output_input_collision(
    output_path: str | Path,
    result: Mapping[str, Any],
    *,
    output_label: str = "readiness output",
    workspace_root: str | Path,
) -> None:
    root = Path(workspace_root).resolve()
    destination = os.path.normcase(str(Path(output_path).resolve()))
    direct_inputs = {
        "article": result.get("file"),
        "validation_sidecar": result.get("proof_sidecar"),
        "context_request": result.get("context_request"),
        "context_pack": result.get("context_pack"),
        "context_receipt": result.get("context_receipt"),
        "assembly_bom": result.get("assembly_bom"),
    }
    for label, value in direct_inputs.items():
        if isinstance(value, str) and value:
            resolved = _resolve_workspace_input(
                value,
                workspace_root=root,
                field=label,
            )
            if destination == os.path.normcase(str(resolved)):
                raise ValueError(f"{output_label} cannot overwrite input {label}")
    bom_value = result.get("assembly_bom")
    if isinstance(bom_value, str) and bom_value:
        try:
            bom = load_json_object_snapshot(
                bom_value, field="assembly BOM"
            ).payload
            artifacts = bom.get("artifacts") if isinstance(bom, Mapping) else None
            if not isinstance(artifacts, Mapping):
                raise ValueError("assembly BOM artifacts must be an object")
            nested_rows = artifact_inventory_snapshots(artifacts)
            nested_rows.update(_historical_preflight_input_snapshots(bom))
            for label, row in nested_rows.items():
                resolved = resolve_artifact(row["path"], workspace_root=root)
                if destination == os.path.normcase(str(resolved)):
                    raise ValueError(
                        f"{output_label} cannot overwrite input {label}"
                    )
        except ValueError as error:
            raise ValueError(
                f"{output_label} cannot safely inspect its bound assembly BOM: {error}"
            ) from error
    rows = result.get("input_hashes")
    if not isinstance(rows, Mapping):
        return
    for label, row in rows.items():
        if not isinstance(row, Mapping) or not isinstance(row.get("path"), str):
            continue
        stored = str(row["path"])
        try:
            resolved = resolve_artifact(stored, workspace_root=root)
        except ValueError:
            continue
        if destination == os.path.normcase(str(resolved)):
            raise ValueError(f"{output_label} cannot overwrite input {label}")


def _readiness_input_hashes(
    inputs: Dict[str, str | Path | None],
    *,
    workspace_root: str | Path,
) -> Dict[str, Dict[str, str]]:
    snapshots: Dict[str, Dict[str, str]] = {}
    for label, value in inputs.items():
        if value is None:
            continue
        path = _resolve_workspace_input(
            value,
            workspace_root=workspace_root,
            field=f"readiness input {label}",
        )
        if path.is_file():
            snapshots[label] = canonical_artifact(
                path,
                workspace_root=workspace_root,
            )
    return snapshots


def _complete_readiness_input_hashes(
    *,
    article: str | Path,
    validation_sidecar: str | Path | None,
    context_request: str | Path | None,
    context_pack: str | Path | None,
    context_receipt: str | Path | None,
    assembly_bom: str | Path | None,
    workspace_root: str | Path,
) -> Dict[str, Dict[str, str]]:
    snapshots = _readiness_input_hashes(
        {
            "article": article,
            "validation_sidecar": validation_sidecar,
            "context_request": context_request,
            "context_pack": context_pack,
            "context_receipt": context_receipt,
            "assembly_bom": assembly_bom,
        },
        workspace_root=workspace_root,
    )
    if assembly_bom is None:
        return snapshots
    bom_path = _resolve_workspace_input(
        assembly_bom,
        workspace_root=workspace_root,
        field="assembly_bom",
    )
    try:
        bom = load_json_object_snapshot(bom_path, field="assembly BOM").payload
    except ValueError as error:
        raise ValueError(f"assembly BOM changed or became unreadable: {error}") from error
    artifacts = bom.get("artifacts") if isinstance(bom, Mapping) else None
    if not isinstance(artifacts, Mapping):
        raise ValueError("assembly BOM artifacts inventory changed or became invalid")
    declared = artifact_inventory_snapshots(artifacts)
    for label, row in declared.items():
        verify_artifact(
            row,
            workspace_root=workspace_root,
            field=f"readiness.{label}",
        )
    snapshots.update(declared)
    historical = _historical_preflight_input_snapshots(bom)
    for label, row in historical.items():
        verify_artifact(
            row,
            workspace_root=workspace_root,
            field=f"readiness.{label}",
        )
    snapshots.update(historical)
    return snapshots


def _historical_preflight_input_snapshots(
    bom: Mapping[str, Any],
) -> Dict[str, Dict[str, str]]:
    """Return the immutable inputs sealed by a final BOM's preflight run."""
    record = bom.get("preflight")
    if record is None:
        return {}
    if not isinstance(record, Mapping):
        raise ValueError("assembly BOM preflight record must be an object")
    inputs = record.get("input_hashes")
    if not isinstance(inputs, Mapping) or not inputs:
        raise ValueError("assembly BOM preflight input_hashes must be an object")
    snapshots: Dict[str, Dict[str, str]] = {}
    for label, row in sorted(inputs.items(), key=lambda item: str(item[0])):
        if not isinstance(label, str) or not label:
            raise ValueError("assembly BOM preflight input labels must be non-empty strings")
        if not isinstance(row, Mapping) or set(row) != {"path", "sha256"}:
            raise ValueError(
                f"assembly BOM preflight input {label} must contain path and sha256"
            )
        path = row.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError(
                f"assembly BOM preflight input {label}.path must be a non-empty string"
            )
        digest = validate_sha256(
            row.get("sha256"),
            field=f"preflight.input_hashes.{label}.sha256",
        )
        snapshots[f"historical_preflight.{label}"] = {
            "path": path,
            "sha256": digest,
        }
    return snapshots


def _bom_runtime_policy(
    assembly_bom: str | None,
    *,
    workspace_root: str | Path,
) -> Dict[str, Any]:
    default = {
        "visible_faq": True,
        "editorial_plan": None,
        "serp_evidence": None,
        "assembly_date": None,
        "run_id": None,
        "assembly_bom": None,
        "faq_policy_status": "",
        "scoring_metadata": {},
        "paa_kwargs": {},
    }
    if not assembly_bom:
        return default
    try:
        source = _resolve_workspace_input(
            assembly_bom,
            workspace_root=workspace_root,
            field="assembly_bom",
        )
    except ValueError:
        return default
    try:
        bom = load_json_object_snapshot(source, field="assembly BOM").payload
    except ValueError:
        return default
    if not isinstance(bom, Mapping):
        return default
    artifacts = bom.get("artifacts")
    paa_policy = bom.get("paa_policy")
    faq_policy = bom.get("faq_policy")
    schema_policy = bom.get("schema_policy")
    if (
        not isinstance(artifacts, Mapping)
        or not isinstance(paa_policy, Mapping)
        or not isinstance(faq_policy, Mapping)
    ):
        return default
    root = Path(workspace_root).resolve()

    def artifact_path(label: str) -> str | None:
        row = artifacts.get(label)
        if not isinstance(row, Mapping) or not isinstance(row.get("path"), str):
            return None
        try:
            return str(resolve_artifact(row["path"], workspace_root=root))
        except ValueError:
            return None

    source_kind = paa_policy.get("source_kind")
    if source_kind == "brief_paa":
        paa_artifact = artifact_path("content_brief")
    elif source_kind == "user_csv":
        paa_artifact = artifact_path("user_paa_csv")
    else:
        paa_artifact = artifact_path("paa_artifact")
    editorial_plan_path = artifact_path("editorial_plan")
    scoring_metadata: Dict[str, Any] = {}
    if editorial_plan_path:
        try:
            plan = load_json_object_snapshot(
                editorial_plan_path, field="editorial plan"
            ).payload
        except ValueError:
            plan = None
        meta = plan.get("meta") if isinstance(plan, Mapping) else None
        if isinstance(meta, Mapping):
            for key in (
                "meta_title",
                "meta_description",
                "primary_keyword",
                "secondary_keywords",
            ):
                scoring_metadata[key] = meta.get(key)
    return {
        "visible_faq": bool(
            isinstance(schema_policy, Mapping) and schema_policy.get("visible_faq") is True
        ),
        "editorial_plan": editorial_plan_path,
        "serp_evidence": artifact_path("serp_evidence"),
        "assembly_date": str(bom.get("assembly_date") or ""),
        "run_id": _canonical_bom_run_id(bom),
        "assembly_bom": bom,
        "faq_policy_status": str(faq_policy.get("status") or ""),
        "scoring_metadata": scoring_metadata,
        "paa_kwargs": {
            "workflow_mode": str(bom.get("workflow_mode") or ""),
            "paa_artifact": paa_artifact,
            "content_brief": artifact_path("content_brief"),
            "answersocrates_blocker": artifact_path("answersocrates_blocker"),
            "expected_query": str(paa_policy.get("query") or ""),
            "expected_collection_date": str(bom.get("assembly_date") or ""),
            "expected_run_id": _canonical_bom_run_id(bom),
        },
    }


def _canonical_bom_run_id(bom: Mapping[str, Any]) -> str:
    workflow = bom.get("workflow")
    receipts = workflow.get("stage_receipts") if isinstance(workflow, Mapping) else None
    if isinstance(receipts, list) and receipts and isinstance(receipts[0], Mapping):
        run_id = receipts[0].get("run_id")
        if isinstance(run_id, str) and run_id.strip():
            return run_id.strip()
    return ""


def format_text_report(result: ReadinessResult) -> str:
    """Return a human-readable publish-readiness report."""
    lines = [
        "PUBLISH READINESS",
        "=" * 50,
        f"File: {result['file']}",
        f"Proof sidecar: {result.get('proof_sidecar') or 'auto/default'}",
        f"Context request: {result.get('context_request') or 'not required/provided'}",
        f"Context pack: {result.get('context_pack') or 'not required/provided'}",
        f"Context receipt: {result.get('context_receipt') or 'not required/provided'}",
        f"Assembly BOM: {result.get('assembly_bom') or 'not required/provided'}",
        f"Overall: {'PASS' if result['passed'] else 'FAIL'}",
        "",
        "Gates:",
    ]

    for gate in result["gates"]:
        status = "PASS" if gate["passed"] else "FAIL"
        lines.append(
            f"  {status:4} {gate['label']:<28} "
            f"errors={gate['errors']} warnings={gate['warnings']}"
        )
        for blocker in gate.get("blockers", [])[:3]:
            lines.append(f"       - {blocker}")

    content_score = result.get("score")
    content_threshold = result.get("score_threshold", 85)
    content_passed = bool(
        content_score is not None and content_score >= content_threshold
    )
    aeo_geo = result.get("aeo_geo", {})
    aeo_geo_score = aeo_geo.get("score")
    aeo_geo_threshold = aeo_geo.get("threshold", 90)
    aeo_geo_passed = bool(aeo_geo.get("passed", False))

    lines.extend(
        [
            "",
            _score_report_line(
                "Content score",
                content_score,
                content_threshold,
                content_passed,
            ),
            _score_report_line(
                "AEO/GEO score",
                aeo_geo_score,
                aeo_geo_threshold,
                aeo_geo_passed,
            ),
        ]
    )

    priority_fixes = result.get("priority_fixes", [])
    if priority_fixes:
        lines.append("")
        lines.append("Priority fixes:")
        for index, fix in enumerate(priority_fixes[:5], start=1):
            issue = fix.get("issue", "Unknown issue")
            dimension = fix.get("dimension", "unknown")
            lines.append(f"  {index}. [{dimension}] {issue}")

    lines.append("=" * 50)
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the publish-readiness gate stack.")
    parser.add_argument("file_path", help="Path to the draft or rewrite markdown file.")
    parser.add_argument(
        "--proof-sidecar",
        help="Validation sidecar containing proof maps and proof packs.",
    )
    parser.add_argument(
        "--profile",
        default="simpro-web",
        help="AI copy linter profile. Defaults to simpro-web.",
    )
    parser.add_argument("--context-request", help="Current Simpro context request JSON.")
    parser.add_argument("--context-pack", help="Current Simpro v2 context pack JSON.")
    parser.add_argument("--context-receipt", help="Current Simpro context receipt JSON.")
    parser.add_argument("--assembly-bom", help="Current blog assembly BOM JSON.")
    parser.add_argument(
        "--phase",
        choices=("preflight", "final"),
        default="preflight",
        help="Validate a provisional BOM for preflight or a final BOM for attestation.",
    )
    parser.add_argument(
        "--output",
        help="Atomically persist the machine-readable readiness result JSON.",
    )
    parser.add_argument(
        "--stage-receipt-output",
        help="Optional receipt path; defaults beside --output for passed runs.",
    )
    parser.add_argument("--vault-root", help="Configured Simpro vault root override.")
    parser.add_argument(
        "--workspace-root",
        default=str(Path.cwd()),
        help="Trusted repository root used to resolve and contain all readiness artifacts.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of the text report.",
    )
    args = parser.parse_args(argv)
    if args.stage_receipt_output and not args.output:
        parser.error("--stage-receipt-output requires --output")
    if args.assembly_bom and not args.output:
        parser.error("--output is required when --assembly-bom is supplied")
    if args.phase == "preflight" and args.stage_receipt_output:
        parser.error(
            "preflight receipts use the deterministic --output companion path; "
            "--stage-receipt-output is allowed only for final attestation"
        )

    result = run_publish_readiness(
        args.file_path,
        proof_sidecar=args.proof_sidecar,
        context_request=args.context_request,
        context_pack=args.context_pack,
        context_receipt=args.context_receipt,
        assembly_bom=args.assembly_bom,
        vault_root=args.vault_root,
        ai_profile=args.profile,
        phase=args.phase,
        workspace_root=args.workspace_root,
    )
    if args.output:
        try:
            write_readiness_result(
                args.output,
                result,
                receipt_path=args.stage_receipt_output,
                workspace_root=args.workspace_root,
            )
        except (OSError, UnicodeError, ValueError) as error:
            parser.error(str(error))
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_text_report(result))
    return 0 if result["passed"] else 1


def _gate_from_findings(
    name: str,
    label: str,
    findings: List[Dict[str, Any]],
) -> GateResult:
    summary = summarize_findings(findings)
    passed = not should_fail(findings, fail_on="error")
    return {
        "name": name,
        "label": label,
        "passed": passed,
        "errors": summary["error"],
        "warnings": summary["warning"],
        "findings": findings,
        "blockers": _finding_lines(findings) if not passed else [],
    }


def _gate_from_url_summary(summary: UrlValidationSummary) -> GateResult:
    blockers = summary.blockers
    return {
        "name": "url_validator",
        "label": "URL Validator",
        "passed": summary.passed,
        "errors": len(blockers),
        "warnings": 0,
        "findings": [
            {
                "rule_id": "url_unresolved",
                "severity": "error",
                "line": result.line,
                "url": result.url,
                "status": result.status,
                "status_code": result.status_code,
                "reason": result.reason,
                "anchor": result.anchor,
            }
            for result in blockers
        ],
        "blockers": [
            _url_blocker_line(result)
            for result in blockers[:3]
        ],
    }


def _gate_from_score(score_result: Dict[str, Any]) -> GateResult:
    passed = bool(score_result.get("passed", False))
    priority_fixes = score_result.get("priority_fixes", [])
    return {
        "name": score_result.get("gate_name", "content_scorer"),
        "label": score_result.get("gate_label", "Content Scorer"),
        "passed": passed,
        "errors": 0 if passed else 1,
        "warnings": len(priority_fixes) if passed else 0,
        "findings": [],
        "blockers": _priority_fix_lines(priority_fixes) if not passed else [],
    }


def _score_content(
    article_path: Path,
    proof_sidecar: Optional[str],
    *,
    artifact_kind: str = "blog",
    assembly_bom: Optional[str] = None,
    runtime_policy: Mapping[str, Any] | None = None,
    workspace_root: str | Path,
    readiness_gate_context: object = None,
) -> Dict[str, Any]:
    content = article_path.read_text(encoding="utf-8")
    if artifact_kind == "landing_page":
        artifact = read_publishable_markdown(article_path)
        page_type = artifact.scalar("page_type").casefold()
        conversion_goal = artifact.scalar("conversion_goal").casefold()
        if page_type not in {"seo", "ppc"} or conversion_goal not in {
            "trial",
            "demo",
            "lead",
        }:
            return {
                "passed": False,
                "content_quality_score": None,
                "threshold": 75,
                "aeo_geo": {
                    "score": None,
                    "threshold": None,
                    "passed": True,
                    "not_applicable": True,
                },
                "priority_fixes": [
                    {
                        "dimension": "landing_page_metadata",
                        "issue": "Landing pages require page_type seo|ppc and conversion_goal trial|demo|lead.",
                    }
                ],
                "gate_name": "landing_page_scorer",
                "gate_label": "Landing Page Scorer",
            }
        result = LandingPageScorer(page_type, conversion_goal).score(
            content,
            meta_title=artifact.scalar("meta_title", "title"),
            meta_description=artifact.scalar("meta_description"),
            primary_keyword=artifact.scalar("primary_keyword", "target_keyword"),
        )
        issues = [
            {"dimension": "landing_page", "issue": str(issue)}
            for issue in result.get("critical_issues", [])
        ]
        if not issues and not result.get("publishing_ready"):
            issues = [
                {"dimension": "landing_page", "issue": str(issue)}
                for issue in result.get("suggestions", [])[:5]
            ]
        return {
            "passed": bool(result.get("publishing_ready")),
            "content_quality_score": result.get("overall_score"),
            "threshold": 75,
            "aeo_geo": {
                "score": None,
                "threshold": None,
                "passed": True,
                "not_applicable": True,
            },
            "priority_fixes": issues,
            "gate_name": "landing_page_scorer",
            "gate_label": "Landing Page Scorer",
            "landing_page": result,
        }
    scorer = ContentScorer()
    policy = dict(runtime_policy or {})
    if assembly_bom and not policy:
        policy = _bom_runtime_policy(
            assembly_bom,
            workspace_root=workspace_root,
        )
    raw_metadata = policy.get("scoring_metadata")
    metadata = dict(raw_metadata) if isinstance(raw_metadata, Mapping) else {}
    metadata["faq_policy_status"] = str(policy.get("faq_policy_status") or "")
    raw_paa = policy.get("paa_kwargs")
    paa = dict(raw_paa) if isinstance(raw_paa, Mapping) else {}
    return scorer.score(
        content,
        metadata=metadata,
        validate_urls=False,
        validate_source_support=False,
        source_path=str(article_path),
        proof_sidecar=proof_sidecar,
        finalized_bom=(
            policy.get("assembly_bom")
            if isinstance(policy.get("assembly_bom"), Mapping)
            else None
        ),
        assembly_date=str(policy.get("assembly_date") or "") or None,
        paa_workflow_mode=str(paa.get("workflow_mode") or "") or None,
        paa_content_brief=str(paa.get("content_brief") or "") or None,
        paa_answersocrates_blocker=(
            str(paa.get("answersocrates_blocker") or "") or None
        ),
        paa_expected_query=str(paa.get("expected_query") or "") or None,
        paa_expected_collection_date=(
            str(paa.get("expected_collection_date") or "") or None
        ),
        paa_expected_run_id=str(paa.get("expected_run_id") or "") or None,
        paa_artifact=str(paa.get("paa_artifact") or "") or None,
        readiness_gate_context=readiness_gate_context,
    )


def _content_score(score_result: Dict[str, Any]) -> Any:
    return score_result.get("content_quality_score", score_result.get("composite_score"))


def _score_report_line(
    label: str,
    score: Any,
    threshold: Any,
    passed: bool,
) -> str:
    if score is None:
        return f"{label}: n/a"
    status = "PASS" if passed else "FAIL"
    return f"{label}: {score}/100 (threshold: {threshold}, {status})"


def _finding_lines(findings: List[Dict[str, Any]]) -> List[str]:
    blockers = [
        finding
        for finding in findings
        if finding.get("severity") == "error"
    ]
    if not blockers:
        blockers = findings
    lines = []
    for finding in blockers[:3]:
        line = finding.get("line", "?")
        rule = finding.get("rule_id", "finding")
        message = finding.get("message", "")
        lines.append(f"line {line}: {rule} - {message}".rstrip(" -"))
    return lines


def _url_blocker_line(result: Any) -> str:
    location = f"line {result.line}: " if result.line else ""
    anchor = f" [{result.anchor}]" if result.anchor else ""
    code = f"HTTP {result.status_code}" if result.status_code is not None else result.reason
    line = f"{location}{result.url}{anchor} ({result.status}: {code})"
    if result.status == "manual_review":
        line += (
            " Replace this source with an equivalent resolved public source "
            "or remove the supported claim. Do not remove the citation without "
            "replacing it with a resolved source supporting the same claim."
        )
    return line


def _priority_fix_lines(priority_fixes: List[Dict[str, Any]]) -> List[str]:
    lines = []
    for fix in priority_fixes[:3]:
        dimension = fix.get("dimension", "unknown")
        issue = fix.get("issue", "Unknown issue")
        lines.append(f"{dimension}: {issue}")
    return lines


if __name__ == "__main__":
    sys.exit(main())
