"""Build and finalize strict, evidence-backed blog assembly BOM artifacts."""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from . import blog_identity_guard, context_binding_guard, editorial_plan_guard
    from .blog_assembly_contract import (
        artifact_inventory_snapshots,
        atomic_write_json,
        canonical_artifact,
        canonical_json_sha256,
        expected_blog_gate_inventory,
        file_sha256,
        normalized_text_sha256,
        resolve_artifact,
        sidecar_evidence_binding_errors,
        validate_current_assembly_date,
        validate_sha256,
        verify_artifact,
    )
    from .faq_structure import detect_faq_structure
    from .named_person import is_named_person
    from .publishable_markdown import PublishableMarkdown, read_publishable_markdown
    from .video_embed import inspect_video_embeds
except ImportError:  # pragma: no cover - supports direct script execution.
    import blog_identity_guard
    import context_binding_guard
    import editorial_plan_guard
    from blog_assembly_contract import (
        artifact_inventory_snapshots,
        atomic_write_json,
        canonical_artifact,
        canonical_json_sha256,
        expected_blog_gate_inventory,
        file_sha256,
        normalized_text_sha256,
        resolve_artifact,
        sidecar_evidence_binding_errors,
        validate_current_assembly_date,
        validate_sha256,
        verify_artifact,
    )
    from faq_structure import detect_faq_structure
    from named_person import is_named_person
    from publishable_markdown import PublishableMarkdown, read_publishable_markdown
    from video_embed import inspect_video_embeds


BOM_SCHEMA = "simpro-blog-assembly-bom/v1"
EDITORIAL_PLAN_SCHEMA = "simpro-blog-editorial-plan/v1"
READINESS_SCHEMA = "simpro-publish-readiness-result/v1"
PACK_SCHEMA = "simpro-product-context-pack/v2"
RECEIPT_SCHEMA = "simpro-context-receipt/v1"
WORKFLOW_MODES = frozenset({"new", "rewrite"})
LIFECYCLE_STATES = frozenset({"provisional", "final"})
PLACEHOLDER_VALUES = blog_identity_guard.PLACEHOLDER_VALUES
NON_CONNECTOR_REASON = (
    "Final article contains no Simpro brand, URL, or connector-sensitive language."
)


def build_blog_assembly_bom_from_files(
    *,
    article_path: str | Path,
    validation_sidecar_path: str | Path,
    editorial_plan_path: str | Path,
    serp_evidence_path: str | Path,
    stage_receipt_paths: Sequence[str | Path],
    workflow_mode: str,
    assembly_date: str,
    paa_artifact_path: str | Path | None = None,
    content_brief_path: str | Path | None = None,
    user_paa_csv_path: str | Path | None = None,
    answersocrates_blocker_path: str | Path | None = None,
    context_request_path: str | Path | None = None,
    context_pack_path: str | Path | None = None,
    context_receipt_path: str | Path | None = None,
    customer_proof_selector_evidence_path: str | Path | None = None,
    fred_authority_evidence_path: str | Path | None = None,
    optimizer_output_paths: Sequence[str | Path] | None = None,
    prior_preflight_readiness_path: str | Path | None = None,
    workspace_root: str | Path | None = None,
    context_client: Any = None,
    vault_root: str | Path | None = None,
) -> dict[str, Any]:
    """Build a deterministic provisional BOM from exact current files."""
    for field, value in (
        ("article_path", article_path),
        ("validation_sidecar_path", validation_sidecar_path),
        ("editorial_plan_path", editorial_plan_path),
        ("serp_evidence_path", serp_evidence_path),
    ):
        _validate_input_path(value, field=field)
    for field, value in (
        ("paa_artifact_path", paa_artifact_path),
        ("content_brief_path", content_brief_path),
        ("user_paa_csv_path", user_paa_csv_path),
        ("answersocrates_blocker_path", answersocrates_blocker_path),
        ("context_request_path", context_request_path),
        ("context_pack_path", context_pack_path),
        ("context_receipt_path", context_receipt_path),
        (
            "customer_proof_selector_evidence_path",
            customer_proof_selector_evidence_path,
        ),
        ("fred_authority_evidence_path", fred_authority_evidence_path),
        ("prior_preflight_readiness_path", prior_preflight_readiness_path),
    ):
        if value is not None:
            _validate_input_path(value, field=field)
    stage_receipt_paths = _validate_path_sequence(
        stage_receipt_paths,
        field="stage_receipt_paths",
    )
    optimizer_output_paths = _validate_path_sequence(
        optimizer_output_paths or (),
        field="optimizer_output_paths",
    )
    if workspace_root is not None:
        _validate_input_path(workspace_root, field="workspace_root")
    if vault_root is not None:
        _validate_input_path(vault_root, field="vault_root")
    root = Path(workspace_root or Path.cwd()).resolve()
    mode = _required_enum(workflow_mode, "workflow_mode", WORKFLOW_MODES)
    assembled = _iso_date(assembly_date, "assembly_date")
    article = read_publishable_markdown(article_path)
    _validate_article_identity(article, assembled)
    plan = _read_json_object(editorial_plan_path, "editorial_plan")
    plan_findings = editorial_plan_guard.check_file(
        editorial_plan_path,
        article_path=article_path,
        serp_evidence_path=serp_evidence_path,
        assembly_date=assembled.isoformat(),
    )
    if plan_findings:
        rule_ids = ", ".join(
            sorted({str(finding.get("rule_id") or "") for finding in plan_findings})
        )
        raise ValueError(f"editorial plan is invalid: {rule_ids}")

    connector_required = context_binding_guard.requires_context(article.raw)
    context_paths = (context_request_path, context_pack_path, context_receipt_path)
    if connector_required and not all(context_paths):
        raise ValueError(
            "connector-bound blog requires context_request_path, context_pack_path, "
            "and context_receipt_path"
        )
    if not connector_required and any(context_paths):
        raise ValueError(
            "non-connector blog cannot include a partial or caller-forced connector binding"
        )
    vault_evidence_paths = (
        customer_proof_selector_evidence_path,
        fred_authority_evidence_path,
    )
    if not connector_required and any(vault_evidence_paths):
        raise ValueError(
            "non-connector blog cannot include vault-dependent customer proof or "
            "Fred authority evidence"
        )

    context_result: context_binding_guard.ContextValidationResult | None = None
    if connector_required:
        context_result = context_binding_guard.validate_context_artifacts(
            article_path,
            proof_sidecar=validation_sidecar_path,
            context_request=context_request_path,
            context_pack=context_pack_path,
            context_receipt=context_receipt_path,
            vault_root=vault_root,
            client=context_client,
        )
        if not context_result.passed:
            rule_ids = ", ".join(
                str(finding.get("rule_id")) for finding in context_result.findings
            )
            raise ValueError(f"context binding is invalid: {rule_ids}")
        validate_sha256(
            context_result.pack_canonical_sha256,
            field="context.context_pack_hash",
        )
        validate_sha256(
            context_result.receipt_canonical_sha256,
            field="context.receipt_hash",
        )
        if not customer_proof_selector_evidence_path:
            raise ValueError(
                "connector-bound blog requires customer proof selector evidence"
            )
        if not fred_authority_evidence_path:
            raise ValueError("connector-bound blog requires Fred authority selection evidence")

    paa_policy = _derive_paa_policy(
        plan,
        workflow_mode=mode,
        paa_artifact_path=paa_artifact_path,
        content_brief_path=content_brief_path,
        user_paa_csv_path=user_paa_csv_path,
        answersocrates_blocker_path=answersocrates_blocker_path,
    )
    if paa_policy["selected_questions"] != _visible_faq_questions(article.raw):
        raise ValueError(
            "paa_policy.selected_questions must exactly match visible FAQ headings in order"
        )
    artifacts = {
        "article": canonical_artifact(article_path, workspace_root=root),
        "validation_sidecar": canonical_artifact(
            validation_sidecar_path,
            workspace_root=root,
        ),
        "editorial_plan": canonical_artifact(editorial_plan_path, workspace_root=root),
        "serp_evidence": canonical_artifact(serp_evidence_path, workspace_root=root),
        "paa_artifact": _optional_artifact(paa_artifact_path, root),
        "content_brief": _optional_artifact(content_brief_path, root),
        "user_paa_csv": _optional_artifact(user_paa_csv_path, root),
        "answersocrates_blocker": _optional_artifact(
            answersocrates_blocker_path,
            root,
        ),
        "context_request": _optional_artifact(context_request_path, root),
        "context_pack": _optional_artifact(context_pack_path, root),
        "context_receipt": _optional_artifact(context_receipt_path, root),
        "customer_proof_selector_evidence": _optional_artifact(
            customer_proof_selector_evidence_path,
            root,
        ),
        "fred_authority_evidence": _optional_artifact(
            fred_authority_evidence_path,
            root,
        ),
        "optimizer_outputs": [
            canonical_artifact(path, workspace_root=root)
            for path in (optimizer_output_paths or [])
        ],
        "stage_receipts": [
            canonical_artifact(path, workspace_root=root)
            for path in stage_receipt_paths
        ],
        "prior_preflight_readiness": _optional_artifact(
            prior_preflight_readiness_path,
            root,
        ),
        "preflight_readiness": None,
    }
    if connector_required:
        try:
            sidecar_content = Path(validation_sidecar_path).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise ValueError(f"validation sidecar is unreadable: {error}") from error
        evidence_errors = sidecar_evidence_binding_errors(
            sidecar_content,
            artifacts,
            workspace_root=root,
            required=True,
        )
        if evidence_errors:
            raise ValueError(
                "sidecar evidence bindings are invalid: "
                + ", ".join(code for code, _ in evidence_errors)
            )
    stage_receipts = [
        _read_json_object(path, f"stage_receipt[{index}]")
        for index, path in enumerate(stage_receipt_paths)
    ]
    if not stage_receipts:
        raise ValueError("stage_receipt_paths must contain real tool-emitted receipts")
    connector_reason = None if connector_required else NON_CONNECTOR_REASON
    _validate_provisional_stage_receipts(
        stage_receipts,
        article_sha256=artifacts["article"]["sha256"],
        optimizer_outputs=artifacts["optimizer_outputs"],
        artifacts=artifacts,
        connector_required=connector_required,
        connector_reason=connector_reason,
        prior_preflight_readiness_path=prior_preflight_readiness_path,
        visible_faq=bool(_visible_faq_questions(article.raw)),
        workspace_root=root,
    )

    bom = {
        "schema": BOM_SCHEMA,
        "lifecycle_state": "provisional",
        "workflow_mode": mode,
        "assembly_date": assembled.isoformat(),
        "identity": _identity_from_article(article),
        "artifacts": artifacts,
        "connector_binding": _connector_binding(
            context_result,
            not_applicable_reason=connector_reason,
        ),
        "author_policy": _author_policy(article),
        "schema_policy": _schema_policy(article),
        "faq_policy": _required_mapping(plan.get("faq_policy"), "editorial_plan.faq_policy"),
        "paa_policy": paa_policy,
        "editorial_plan_summary": _editorial_plan_summary(plan),
        "workflow": {
            "stage_receipts": stage_receipts,
        },
        "preflight": None,
    }
    return bom


def build_blog_assembly_bom(**kwargs: Any) -> dict[str, Any]:
    """Compatibility public name for the strict file-backed builder."""
    return build_blog_assembly_bom_from_files(**kwargs)


def finalize_blog_assembly_bom(
    *,
    bom_path: str | Path,
    preflight_readiness_path: str | Path,
    workspace_root: str | Path | None = None,
    vault_root: str | Path | None = None,
) -> dict[str, Any]:
    """Seal a passed preflight into a final BOM without self-reference."""
    root = Path(workspace_root or Path.cwd()).resolve()
    bom = _read_json_object(bom_path, "bom")
    if bom.get("schema") != BOM_SCHEMA:
        raise ValueError(f"bom.schema must be {BOM_SCHEMA}")
    if bom.get("lifecycle_state") != "provisional":
        raise ValueError("only a provisional BOM can be finalized")
    if file_sha256(bom_path) != canonical_json_sha256(bom):
        raise ValueError(
            "provisional BOM bytes are not the canonical deterministic serialization"
        )
    _validate_provisional_bom_guard(bom, workspace_root=root)
    readiness = _read_json_object(preflight_readiness_path, "preflight_readiness")
    _validate_passed_preflight(
        readiness,
        bom,
        bom_path=Path(bom_path),
        workspace_root=root,
    )
    _validate_persisted_readiness_contract(readiness, workspace_root=root)
    _verify_bom_artifacts_unchanged(bom, root)
    receipt_path = _readiness_receipt_path(preflight_readiness_path)
    preflight_receipt = _read_json_object(receipt_path, "preflight_stage_receipt")
    _validate_preflight_stage_receipt(
        preflight_receipt,
        bom=bom,
        readiness_path=Path(preflight_readiness_path),
    )
    _verify_preflight_execution(
        readiness,
        bom=bom,
        bom_path=Path(bom_path),
        workspace_root=root,
        vault_root=vault_root,
    )

    final_bom = copy.deepcopy(bom)
    readiness_artifact = canonical_artifact(
        preflight_readiness_path,
        workspace_root=root,
    )
    final_bom["lifecycle_state"] = "final"
    final_bom["artifacts"]["preflight_readiness"] = readiness_artifact
    final_bom["artifacts"]["stage_receipts"].append(
        canonical_artifact(receipt_path, workspace_root=root)
    )
    final_bom["workflow"]["stage_receipts"].append(preflight_receipt)
    final_bom["preflight"] = {
        "path": readiness_artifact["path"],
        "sha256": readiness_artifact["sha256"],
        "tool": copy.deepcopy(readiness["tool"]),
        "verification_scope": "source_artifact",
        "gate_inventory": list(readiness["gate_inventory"]),
        "input_hashes": copy.deepcopy(readiness["input_hashes"]),
    }
    _validate_final_bom_guard(final_bom, workspace_root=root)
    return final_bom


def _validate_persisted_readiness_contract(
    readiness: Mapping[str, Any],
    *,
    workspace_root: Path,
) -> None:
    try:
        from . import publish_readiness
    except ImportError:  # pragma: no cover - supports direct script execution.
        import publish_readiness
    publish_readiness.validate_passed_readiness_result(
        readiness,
        workspace_root=workspace_root,
    )


def _verify_preflight_execution(
    readiness: Mapping[str, Any],
    *,
    bom: Mapping[str, Any],
    bom_path: Path,
    workspace_root: Path,
    vault_root: str | Path | None,
) -> None:
    rerun = _rerun_preflight_readiness(
        bom=bom,
        bom_path=bom_path,
        workspace_root=workspace_root,
        vault_root=vault_root,
    )
    if rerun.get("passed") is not True:
        raise ValueError("preflight verification rerun did not pass")
    stable_fields = (
        "schema",
        "tool",
        "phase",
        "verification_scope",
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
    )
    persisted_stable = {field: readiness.get(field) for field in stable_fields}
    rerun_stable = {field: rerun.get(field) for field in stable_fields}
    if rerun_stable != persisted_stable:
        raise ValueError(
            "persisted preflight does not match the live verification rerun"
        )


def _rerun_preflight_readiness(
    *,
    bom: Mapping[str, Any],
    bom_path: Path,
    workspace_root: Path,
    vault_root: str | Path | None,
) -> Mapping[str, Any]:
    try:
        from . import publish_readiness
    except ImportError:  # pragma: no cover - supports direct script execution.
        import publish_readiness
    artifacts = _required_mapping(bom.get("artifacts"), "bom.artifacts")

    def bound_path(label: str, *, required: bool = False) -> Path | None:
        row = artifacts.get(label)
        if row is None and not required:
            return None
        mapping = _required_mapping(row, f"bom.artifacts.{label}")
        return resolve_artifact(mapping.get("path"), workspace_root=workspace_root)

    return publish_readiness.run_publish_readiness(
        bound_path("article", required=True),
        proof_sidecar=bound_path("validation_sidecar", required=True),
        context_request=bound_path("context_request"),
        context_pack=bound_path("context_pack"),
        context_receipt=bound_path("context_receipt"),
        assembly_bom=bom_path,
        vault_root=vault_root,
        phase="preflight",
        workspace_root=workspace_root,
    )


def _validate_provisional_bom_guard(
    bom: Mapping[str, Any],
    *,
    workspace_root: Path,
) -> None:
    """Run the same complete BOM guard used by preflight before sealing."""
    try:
        from . import blog_assembly_bom_guard
    except ImportError:  # pragma: no cover - supports direct script execution.
        import blog_assembly_bom_guard

    artifacts = _required_mapping(bom.get("artifacts"), "bom.artifacts")

    def bound_path(label: str, *, required: bool = False) -> Path | None:
        row = artifacts.get(label)
        if row is None and not required:
            return None
        mapping = _required_mapping(row, f"bom.artifacts.{label}")
        return resolve_artifact(mapping.get("path"), workspace_root=workspace_root)

    findings = blog_assembly_bom_guard.check_bom(
        bom,
        article_path=bound_path("article", required=True),
        validation_sidecar_path=bound_path("validation_sidecar", required=True),
        context_request_path=bound_path("context_request"),
        context_pack_path=bound_path("context_pack"),
        context_receipt_path=bound_path("context_receipt"),
        workspace_root=workspace_root,
        expected_lifecycle_state="provisional",
    )
    if findings:
        rules = ", ".join(
            sorted({str(finding.get("rule_id")) for finding in findings})
        )
        raise ValueError(f"provisional BOM is invalid: {rules}")


def _validate_final_bom_guard(
    bom: Mapping[str, Any],
    *,
    workspace_root: Path,
) -> None:
    """Reject a final object that would fail the same guard after persistence."""
    try:
        from . import blog_assembly_bom_guard
    except ImportError:  # pragma: no cover - supports direct script execution.
        import blog_assembly_bom_guard

    artifacts = _required_mapping(bom.get("artifacts"), "bom.artifacts")

    def bound_path(label: str, *, required: bool = False) -> Path | None:
        row = artifacts.get(label)
        if row is None and not required:
            return None
        mapping = _required_mapping(row, f"bom.artifacts.{label}")
        return resolve_artifact(mapping.get("path"), workspace_root=workspace_root)

    findings = blog_assembly_bom_guard.check_bom(
        bom,
        article_path=bound_path("article", required=True),
        validation_sidecar_path=bound_path("validation_sidecar", required=True),
        context_request_path=bound_path("context_request"),
        context_pack_path=bound_path("context_pack"),
        context_receipt_path=bound_path("context_receipt"),
        workspace_root=workspace_root,
        expected_lifecycle_state="final",
    )
    if findings:
        rules = ", ".join(
            sorted({str(finding.get("rule_id")) for finding in findings})
        )
        raise ValueError(f"constructed final BOM is invalid: {rules}")


def _readiness_receipt_path(readiness_path: str | Path) -> Path:
    source = Path(readiness_path)
    return source.with_name(f"{source.stem}-stage-receipt.json")


def _validate_preflight_stage_receipt(
    receipt: Mapping[str, Any],
    *,
    bom: Mapping[str, Any],
    readiness_path: Path,
) -> None:
    workflow = _required_mapping(bom.get("workflow"), "bom.workflow")
    prior = workflow.get("stage_receipts")
    if not isinstance(prior, list):
        raise ValueError("bom.workflow.stage_receipts must be a list")
    artifacts = _required_mapping(bom.get("artifacts"), "bom.artifacts")
    article = _required_mapping(artifacts.get("article"), "bom.artifacts.article")
    validate_preflight_stage_receipt_binding(
        receipt,
        prior_receipts=prior,
        readiness_path=readiness_path,
        article_sha256=article.get("sha256"),
    )


def validate_preflight_stage_receipt_binding(
    receipt: Mapping[str, Any],
    *,
    prior_receipts: Sequence[Mapping[str, Any]],
    readiness_path: str | Path,
    article_sha256: Any,
) -> None:
    """Validate one readiness receipt against its exact run, inputs, and outputs."""
    try:
        from .blog_assembly_stage_receipt import check_receipt_chain, check_stage_receipt
    except ImportError:  # pragma: no cover - supports direct script execution.
        from blog_assembly_stage_receipt import check_receipt_chain, check_stage_receipt
    if not isinstance(prior_receipts, (list, tuple)) or any(
        not isinstance(row, Mapping) for row in prior_receipts
    ):
        raise ValueError("prior_receipts must be a list of receipt objects")
    final_article_sha256 = validate_sha256(
        article_sha256,
        field="article_sha256",
    )
    optimized = any(
        isinstance(row, Mapping) and row.get("stage") == "optimization"
        for row in prior_receipts
    )
    expected_stage = "final_preflight_readiness" if optimized else "preflight_readiness"
    findings = check_stage_receipt(
        receipt,
        expected_stage=expected_stage,
        expected_tool_name="publish_readiness",
        expected_tool_version="1.0.0",
    )
    findings.extend(check_receipt_chain([*prior_receipts, receipt]))
    if findings:
        raise ValueError(
            "preflight stage receipt is invalid: "
            + ", ".join(sorted({str(finding["rule_id"]) for finding in findings}))
        )
    outputs = receipt.get("output_artifact_hashes")
    readiness_file = Path(readiness_path)
    if not isinstance(outputs, Mapping) or outputs.get("readiness_output") != file_sha256(readiness_file):
        raise ValueError("preflight stage receipt does not bind the readiness output")
    readiness = _read_json_object(readiness_file, "preflight_readiness")
    readiness_inputs = _required_mapping(
        readiness.get("input_hashes"),
        "preflight_readiness.input_hashes",
    )
    expected_input_hashes: dict[str, str] = {}
    for label, row in readiness_inputs.items():
        if not isinstance(label, str) or not label.strip():
            raise ValueError("preflight readiness input labels must be non-empty strings")
        input_row = _required_mapping(
            row,
            f"preflight_readiness.input_hashes.{label}",
        )
        expected_input_hashes[label] = validate_sha256(
            input_row.get("sha256"),
            field=f"preflight_readiness.input_hashes.{label}.sha256",
        )
    if receipt.get("input_artifact_hashes") != expected_input_hashes:
        raise ValueError("preflight stage receipt input hashes do not match readiness")
    if (
        receipt.get("run_id") != readiness.get("run_id")
        or receipt.get("started_at") != readiness.get("started_at")
        or receipt.get("completed_at") != readiness.get("completed_at")
    ):
        raise ValueError("preflight stage receipt run identity does not match readiness")
    if outputs.get("article") != final_article_sha256:
        raise ValueError("preflight stage receipt does not bind the final article")


def write_blog_assembly_bom(path: str | Path, bom: Mapping[str, Any]) -> None:
    """Persist a deterministic BOM atomically."""
    atomic_write_json(path, bom)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI for strict provisional build and passed-preflight finalization."""
    parser = argparse.ArgumentParser(description="Build or finalize a blog assembly BOM.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build", help="Build a provisional BOM.")
    build.add_argument("article_path")
    build.add_argument("--validation-sidecar", required=True)
    build.add_argument("--editorial-plan", required=True)
    build.add_argument("--serp-evidence", required=True)
    build.add_argument("--paa-artifact")
    build.add_argument("--content-brief")
    build.add_argument("--user-paa-csv")
    build.add_argument("--answersocrates-blocker")
    build.add_argument("--context-request")
    build.add_argument("--context-pack")
    build.add_argument("--context-receipt")
    build.add_argument("--customer-proof-selector-evidence")
    build.add_argument("--fred-authority-evidence")
    build.add_argument("--optimizer-output", action="append", default=[])
    build.add_argument("--prior-preflight-readiness")
    build.add_argument("--stage-receipt", action="append", required=True)
    build.add_argument("--workflow-mode", choices=sorted(WORKFLOW_MODES), required=True)
    build.add_argument("--assembly-date", required=True)
    build.add_argument("--workspace-root", default=str(Path.cwd()))
    build.add_argument("--vault-root")
    build.add_argument("--output", required=True)

    finalize = subparsers.add_parser("finalize", help="Seal a passed preflight.")
    finalize.add_argument("--bom", required=True)
    finalize.add_argument("--preflight-readiness", required=True)
    finalize.add_argument("--workspace-root", default=str(Path.cwd()))
    finalize.add_argument("--vault-root")
    finalize.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    try:
        if args.command == "build":
            bom = build_blog_assembly_bom_from_files(
                article_path=args.article_path,
                validation_sidecar_path=args.validation_sidecar,
                editorial_plan_path=args.editorial_plan,
                serp_evidence_path=args.serp_evidence,
                paa_artifact_path=args.paa_artifact,
                content_brief_path=args.content_brief,
                user_paa_csv_path=args.user_paa_csv,
                answersocrates_blocker_path=args.answersocrates_blocker,
                context_request_path=args.context_request,
                context_pack_path=args.context_pack,
                context_receipt_path=args.context_receipt,
                customer_proof_selector_evidence_path=args.customer_proof_selector_evidence,
                fred_authority_evidence_path=args.fred_authority_evidence,
                optimizer_output_paths=args.optimizer_output,
                prior_preflight_readiness_path=args.prior_preflight_readiness,
                stage_receipt_paths=args.stage_receipt,
                workflow_mode=args.workflow_mode,
                assembly_date=args.assembly_date,
                workspace_root=args.workspace_root,
                vault_root=args.vault_root,
            )
        else:
            bom = finalize_blog_assembly_bom(
                bom_path=args.bom,
                preflight_readiness_path=args.preflight_readiness,
                workspace_root=args.workspace_root,
                vault_root=args.vault_root,
            )
        _reject_bom_output_collision(
            args.output,
            bom,
            workspace_root=args.workspace_root,
        )
        write_blog_assembly_bom(args.output, bom)
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))
    return 0


def _reject_bom_output_collision(
    output_path: str | Path,
    bom: Mapping[str, Any],
    *,
    workspace_root: str | Path,
) -> None:
    """Prevent a BOM write from destroying any artifact it attests."""
    root = Path(workspace_root).resolve()

    def output_identity(path: str | Path) -> str:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = root / candidate
        resolved = candidate.resolve(strict=False)
        root_identity = os.path.normcase(str(root))
        resolved_identity = os.path.normcase(str(resolved))
        try:
            common = os.path.commonpath((root_identity, resolved_identity))
        except ValueError as error:
            raise ValueError("BOM output must stay inside the workspace") from error
        if common != root_identity:
            raise ValueError("BOM output must stay inside the workspace")
        return resolved_identity

    destination = output_identity(output_path)
    artifacts = _required_mapping(bom.get("artifacts"), "bom.artifacts")
    for label, row in artifact_inventory_snapshots(artifacts).items():
        candidate = resolve_artifact(row["path"], workspace_root=workspace_root)
        if destination == os.path.normcase(str(candidate)):
            raise ValueError(f"BOM output cannot overwrite artifact {label}")
    for readiness_label in ("prior_preflight_readiness", "preflight_readiness"):
        readiness_row = artifacts.get(readiness_label)
        if not isinstance(readiness_row, Mapping):
            continue
        readiness_path = verify_artifact(
            readiness_row,
            workspace_root=workspace_root,
            field=f"artifacts.{readiness_label}",
        )
        readiness = _read_json_object(readiness_path, readiness_label)
        inputs = _required_mapping(
            readiness.get("input_hashes"),
            f"{readiness_label}.input_hashes",
        )
        for label, row in inputs.items():
            input_row = _required_mapping(
                row,
                f"{readiness_label}.input_hashes.{label}",
            )
            candidate = resolve_artifact(
                input_row.get("path"),
                workspace_root=workspace_root,
            )
            candidate_identity = os.path.normcase(str(candidate))
            if destination != candidate_identity:
                continue
            raise ValueError(
                f"BOM output cannot overwrite {readiness_label} input {label}"
            )


def _validate_article_identity(article: PublishableMarkdown, assembled: date) -> None:
    kind = context_binding_guard.require_artifact_kind(
        article.raw,
        article_path=article.path,
    )
    if kind != "blog":
        raise ValueError("blog assembly BOM can only bind artifact_type blog")
    findings = blog_identity_guard.check_article(article.raw, assembly_date=assembled)
    if findings:
        raise ValueError(
            "blog identity is invalid: "
            + ", ".join(str(finding["rule_id"]) for finding in findings)
        )


def _identity_from_article(article: PublishableMarkdown) -> dict[str, str]:
    return {
        field: _required_article_scalar(article, field)
        for field in (
            "artifact_type",
            "brand",
            "title",
            "objective",
            "audience",
            "region",
            "last_updated",
        )
    }


def _author_policy(article: PublishableMarkdown) -> dict[str, Any]:
    author = article.scalar("author")
    named = bool(author)
    if named and not is_named_person(author):
        raise ValueError(
            "article.author must identify a named person, not an organization, team, or role byline"
        )
    return {
        "status": "named_author" if named else "not_provided",
        "name": author if named else "",
        "frontmatter_author_required": named,
        "schema_person_required": named,
        "named_author_voice_allowed": named,
    }


def _schema_policy(article: PublishableMarkdown) -> dict[str, Any]:
    declared = article.values("schema_notes")
    faq = detect_faq_structure(article.raw)
    if faq.unsupported_lines:
        raise ValueError(
            "FAQ-like details or bold-question markup is unsupported; use a recognized FAQ H2 with question headings"
        )
    questions = [entry.question for entry in faq.entries]
    video_inspection = inspect_video_embeds(article.raw)
    if video_inspection.errors:
        raise ValueError("invalid video embed: " + "; ".join(video_inspection.errors))
    video = video_inspection.has_supported_embed
    author = is_named_person(article.scalar("author"))
    required = [
        "BlogPosting",
        "BreadcrumbList",
        "ImageObject for the featured image or logo",
        "Organization as publisher reference only, not a separate full schema block",
    ]
    if faq.heading_present:
        required.extend(("FAQPage", "Question and Answer inside FAQPage"))
    if author:
        required.append("Person as author")
    if video:
        required.append("VideoObject")
    return {
        "declared_entities": declared,
        "required_entities": required,
        "visible_faq": faq.heading_present,
        "faq_questions": questions,
        "video_embed": video,
    }


def _derive_paa_policy(
    plan: Mapping[str, Any],
    *,
    workflow_mode: str,
    paa_artifact_path: str | Path | None,
    content_brief_path: str | Path | None,
    user_paa_csv_path: str | Path | None,
    answersocrates_blocker_path: str | Path | None,
) -> dict[str, Any]:
    declared = _required_mapping(plan.get("paa_policy"), "editorial_plan.paa_policy")
    source_kind = _required_string(declared.get("source_kind"), "paa_policy.source_kind")
    if source_kind not in {"answersocrates", "brief_paa", "user_csv"}:
        raise ValueError(
            "paa_policy.source_kind must be answersocrates, brief_paa, or user_csv"
        )
    selected = _string_list(declared.get("selected_questions"), "paa_policy.selected_questions")
    query = _required_string(declared.get("query"), "paa_policy.query")
    if workflow_mode == "new" and source_kind not in {"answersocrates", "user_csv"}:
        raise ValueError("new blog PAA policy must bind AnswerSocrates or a blocked-state user CSV")
    if workflow_mode == "rewrite" and source_kind == "brief_paa" and not content_brief_path:
        raise ValueError("rewrite brief_paa policy requires content_brief_path")
    if source_kind == "answersocrates" and not paa_artifact_path:
        raise ValueError("answersocrates PAA policy requires paa_artifact_path")
    if source_kind == "user_csv" and (
        not user_paa_csv_path or not answersocrates_blocker_path
    ):
        raise ValueError(
            "user_csv PAA policy requires both user_paa_csv_path and "
            "answersocrates_blocker_path"
        )
    return {
        "source_kind": source_kind,
        "query": query,
        "selected_questions": selected,
    }


def _connector_binding(
    result: context_binding_guard.ContextValidationResult | None,
    *,
    not_applicable_reason: str | None,
) -> dict[str, Any]:
    if result is None:
        return {
            "status": "not_applicable",
            "reason": not_applicable_reason,
            "context": context_binding_guard.ContextValidationResult(
                required=False,
                findings=(),
            ).context_summary(),
        }
    return {
        "status": "required",
        "context": result.context_summary(),
    }


def _editorial_plan_summary(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": plan["schema"],
        "reader_contract": copy.deepcopy(plan["reader_contract"]),
        "serp_strategy": copy.deepcopy(plan["serp_strategy"]),
        "original_contributions": copy.deepcopy(plan["original_contributions"]),
        "entity_map": copy.deepcopy(plan["entity_map"]),
        "query_ownership": copy.deepcopy(plan["query_ownership"]),
        "internal_link_plan": copy.deepcopy(plan["internal_link_plan"]),
    }


def _validate_editorial_plan(plan: Mapping[str, Any]) -> None:
    findings = editorial_plan_guard.check_plan(plan)
    if findings:
        rule_ids = ", ".join(
            sorted({str(finding.get("rule_id") or "") for finding in findings})
        )
        raise ValueError(f"editorial plan is invalid: {rule_ids}")


def _validate_provisional_stage_receipts(
    receipts: list[Mapping[str, Any]],
    *,
    article_sha256: str,
    optimizer_outputs: list[dict[str, str]],
    artifacts: Mapping[str, Any],
    connector_required: bool,
    connector_reason: str | None,
    prior_preflight_readiness_path: str | Path | None,
    visible_faq: bool,
    workspace_root: Path,
) -> None:
    try:
        from .blog_assembly_stage_receipt import check_receipt_chain
    except ImportError:  # pragma: no cover - supports direct script execution.
        from blog_assembly_stage_receipt import check_receipt_chain

    findings = check_receipt_chain(receipts)
    if findings:
        rules = ", ".join(
            sorted({str(finding.get("rule_id")) for finding in findings})
        )
        raise ValueError(f"stage receipt chain is invalid: {rules}")
    stages = tuple(str(receipt.get("stage") or "") for receipt in receipts)
    optimized = "optimization" in stages
    expected = (
        (
            "draft",
            "scrub",
            "context_binding",
            "preflight_readiness",
            "optimization",
            "post_optimization_scrub",
            "post_optimization_context_binding",
        )
        if optimized
        else ("draft", "scrub", "context_binding")
    )
    if stages != expected:
        raise ValueError(
            "provisional stage receipt sequence must be exactly: "
            + " -> ".join(expected)
        )
    if optimized != bool(optimizer_outputs):
        raise ValueError(
            "optimizer output evidence must be present if and only if the "
            "optimization stage is present"
        )
    if optimized != bool(prior_preflight_readiness_path):
        raise ValueError(
            "prior preflight readiness evidence must be present if and only if "
            "the optimization stage is present"
        )
    outputs = receipts[-1].get("output_artifact_hashes")
    if not isinstance(outputs, Mapping) or outputs.get("article") != article_sha256:
        raise ValueError("last provisional stage receipt must bind the final article hash")

    by_stage = {
        str(receipt.get("stage") or ""): receipt
        for receipt in receipts
    }
    prior_readiness: Mapping[str, Any] | None = None
    if optimized:
        prior_readiness = _validate_prior_preflight_readiness(
            prior_preflight_readiness_path,
            receipt=by_stage["preflight_readiness"],
            visible_faq=visible_faq,
            connector_required=connector_required,
            workspace_root=workspace_root,
        )
    draft = by_stage["draft"]
    draft_inputs = _required_mapping(
        draft.get("input_artifact_hashes"),
        "draft.input_artifact_hashes",
    )
    if draft_inputs.get("editorial_plan") != artifacts["editorial_plan"]["sha256"]:
        raise ValueError("draft stage receipt must bind the editorial plan input")
    draft_evidence = _required_mapping(
        draft.get("evidence_hashes"),
        "draft.evidence_hashes",
    )
    if draft_evidence.get("serp_evidence") != artifacts["serp_evidence"]["sha256"]:
        raise ValueError("draft stage receipt must bind verified SERP evidence")

    for stage_name in ("scrub", "post_optimization_scrub"):
        receipt = by_stage.get(stage_name)
        if receipt is None:
            continue
        evidence = _required_mapping(
            receipt.get("evidence_hashes"),
            f"{stage_name}.evidence_hashes",
        )
        try:
            validate_sha256(
                evidence.get("scrub_statistics"),
                field=f"{stage_name}.evidence_hashes.scrub_statistics",
            )
        except ValueError as error:
            raise ValueError(
                f"{stage_name} stage receipt must bind scrub statistics"
            ) from error

    for stage_name in ("context_binding", "post_optimization_context_binding"):
        receipt = by_stage.get(stage_name)
        if receipt is None:
            continue
        receipt_outputs = _required_mapping(
            receipt.get("output_artifact_hashes"),
            f"{stage_name}.output_artifact_hashes",
        )
        expected_sidecar_hash = artifacts["validation_sidecar"]["sha256"]
        if stage_name == "context_binding" and prior_readiness is not None:
            prior_inputs = _required_mapping(
                prior_readiness.get("input_hashes"),
                "prior_preflight_readiness.input_hashes",
            )
            prior_sidecar = _required_mapping(
                prior_inputs.get("validation_sidecar"),
                "prior_preflight_readiness.input_hashes.validation_sidecar",
            )
            expected_sidecar_hash = prior_sidecar.get("sha256")
        if receipt_outputs.get("validation_sidecar") != expected_sidecar_hash:
            raise ValueError(
                f"{stage_name} stage receipt must bind the validation sidecar output"
            )
        evidence = _required_mapping(
            receipt.get("evidence_hashes"),
            f"{stage_name}.evidence_hashes",
        )
        try:
            validate_sha256(
                evidence.get("context_binding"),
                field=f"{stage_name}.evidence_hashes.context_binding",
            )
        except ValueError as error:
            raise ValueError(
                f"{stage_name} stage receipt must bind generated Context Binding evidence"
            ) from error
        if connector_required:
            receipt_inputs = _required_mapping(
                receipt.get("input_artifact_hashes"),
                f"{stage_name}.input_artifact_hashes",
            )
            for label in ("context_request", "context_pack", "context_receipt"):
                row = _required_mapping(
                    artifacts.get(label),
                    f"artifacts.{label}",
                )
                if receipt_inputs.get(label) != row.get("sha256"):
                    raise ValueError(
                        f"{stage_name} stage receipt must bind {label} input"
                    )
        else:
            expected_reason_hash = normalized_text_sha256(
                connector_reason,
                field="connector_binding.reason",
            )
            if evidence.get("not_applicable_reason") != expected_reason_hash:
                raise ValueError(
                    f"{stage_name} stage receipt must bind the BOM "
                    "connector not-applicable reason"
                )

    optimization = by_stage.get("optimization")
    if optimization is not None:
        evidence = _required_mapping(
            optimization.get("evidence_hashes"),
            "optimization.evidence_hashes",
        )
        expected_optimizer_hashes = {
            str(row["sha256"]) for row in optimizer_outputs
        }
        if not expected_optimizer_hashes.issubset(set(evidence.values())):
            raise ValueError(
                "optimization stage receipt must bind every optimizer output artifact"
            )


def _validate_prior_preflight_readiness(
    path: str | Path | None,
    *,
    receipt: Mapping[str, Any],
    visible_faq: bool,
    connector_required: bool,
    workspace_root: Path,
) -> Mapping[str, Any]:
    if path is None:
        raise ValueError("optimized workflow requires prior preflight readiness evidence")
    readiness = _read_json_object(path, "prior_preflight_readiness")
    inputs = _required_mapping(
        readiness.get("input_hashes"),
        "prior_preflight_readiness.input_hashes",
    )
    prior_bom_row = _required_mapping(
        inputs.get("assembly_bom"),
        "prior_preflight_readiness.input_hashes.assembly_bom",
    )
    try:
        prior_bom_path = verify_artifact(
            prior_bom_row,
            workspace_root=workspace_root,
            field="prior_preflight_readiness.input_hashes.assembly_bom",
        )
    except ValueError as error:
        raise ValueError("prior preflight BOM artifact is invalid") from error
    prior_bom = _read_json_object(prior_bom_path, "prior_preflight_bom")
    if (
        prior_bom.get("schema") != BOM_SCHEMA
        or prior_bom.get("lifecycle_state") != "provisional"
    ):
        raise ValueError("prior preflight must bind a provisional blog assembly BOM")
    prior_schema = _required_mapping(
        prior_bom.get("schema_policy"),
        "prior_preflight_bom.schema_policy",
    )
    prior_connector = _required_mapping(
        prior_bom.get("connector_binding"),
        "prior_preflight_bom.connector_binding",
    )
    expected_inventory = expected_blog_gate_inventory(
        visible_faq=prior_schema.get("visible_faq") is True,
        connector_required=prior_connector.get("status") == "required",
    )
    if (
        readiness.get("schema") != READINESS_SCHEMA
        or readiness.get("tool")
        != {"name": "publish_readiness", "version": "1.0.0"}
        or readiness.get("phase") != "preflight"
        or readiness.get("passed") is not True
        or readiness.get("artifact_kind") != "blog"
        or readiness.get("verification_scope") != "source_artifact"
        or readiness.get("input_seal") != {"status": "verified"}
        or readiness.get("gate_inventory") != expected_inventory
    ):
        raise ValueError("prior preflight readiness result is not a passed tool result")
    gates = readiness.get("gates")
    if not isinstance(gates, list) or [
        row.get("name") if isinstance(row, Mapping) else None for row in gates
    ] != expected_inventory or any(
        not isinstance(row, Mapping)
        or row.get("passed") is not True
        or row.get("errors") != 0
        or row.get("blockers") not in ([], ())
        for row in gates
    ):
        raise ValueError("prior preflight readiness gate results are invalid")
    score = readiness.get("score")
    aeo_geo = readiness.get("aeo_geo")
    if (
        readiness.get("score_threshold") != 85
        or not _is_number(score)
        or score < 85
        or not isinstance(aeo_geo, Mapping)
        or aeo_geo.get("threshold") != 90
        or aeo_geo.get("passed") is not True
        or not _is_number(aeo_geo.get("score"))
        or aeo_geo["score"] < 90
    ):
        raise ValueError("prior preflight readiness scores are below the hard thresholds")
    prior_artifacts = _required_mapping(
        prior_bom.get("artifacts"),
        "prior_preflight_bom.artifacts",
    )
    expected_inputs = artifact_inventory_snapshots(prior_artifacts)
    actual_prior_inputs = {
        str(label): dict(row)
        for label, row in inputs.items()
        if label != "assembly_bom" and isinstance(row, Mapping)
    }
    if actual_prior_inputs != expected_inputs:
        raise ValueError("prior preflight inputs do not match its bound provisional BOM")
    input_hashes = {
        str(label): str(row.get("sha256"))
        for label, row in inputs.items()
        if isinstance(row, Mapping) and isinstance(row.get("sha256"), str)
    }
    if len(input_hashes) != len(inputs):
        raise ValueError("prior preflight readiness input hashes are invalid")
    outputs = _required_mapping(
        receipt.get("output_artifact_hashes"),
        "preflight_readiness.output_artifact_hashes",
    )
    article_input = _required_mapping(
        inputs.get("article"),
        "prior_preflight_readiness.input_hashes.article",
    )
    if (
        receipt.get("input_artifact_hashes") != input_hashes
        or outputs.get("readiness_output") != file_sha256(path)
        or outputs.get("article") != article_input.get("sha256")
        or receipt.get("run_id") != readiness.get("run_id")
        or receipt.get("started_at") != readiness.get("started_at")
        or receipt.get("completed_at") != readiness.get("completed_at")
    ):
        raise ValueError("preflight readiness stage receipt does not bind its prior result")
    return readiness


def _validate_passed_preflight(
    readiness: Mapping[str, Any],
    bom: Mapping[str, Any],
    *,
    bom_path: Path,
    workspace_root: Path,
) -> None:
    if readiness.get("schema") != READINESS_SCHEMA:
        raise ValueError(f"preflight readiness must use {READINESS_SCHEMA}")
    if readiness.get("phase") != "preflight":
        raise ValueError("preflight readiness phase must be preflight")
    if readiness.get("passed") is not True:
        raise ValueError("failed preflight cannot finalize a BOM")
    if readiness.get("verification_scope") != "source_artifact":
        raise ValueError("preflight verification_scope must be source_artifact")
    if readiness.get("input_seal") != {"status": "verified"}:
        raise ValueError("preflight readiness input seal is not verified")
    tool = _required_mapping(readiness.get("tool"), "preflight_readiness.tool")
    if tool != {"name": "publish_readiness", "version": "1.0.0"}:
        raise ValueError("preflight readiness tool/version is invalid")
    if readiness.get("artifact_kind") != "blog":
        raise ValueError("preflight readiness artifact_kind must be blog")
    schema_policy = _required_mapping(
        bom.get("schema_policy"),
        "bom.schema_policy",
    )
    connector_binding = _required_mapping(
        bom.get("connector_binding"),
        "bom.connector_binding",
    )
    expected_inventory = expected_blog_gate_inventory(
        visible_faq=schema_policy.get("visible_faq") is True,
        connector_required=connector_binding.get("status") == "required",
    )
    inventory = readiness.get("gate_inventory")
    if inventory != expected_inventory:
        raise ValueError("preflight readiness gate inventory is not the exact expected inventory")
    gates = readiness.get("gates")
    if not isinstance(gates, list) or len(gates) != len(expected_inventory):
        raise ValueError("preflight readiness gate results are incomplete")
    for index, (gate, expected_name) in enumerate(zip(gates, expected_inventory)):
        if not isinstance(gate, Mapping):
            raise ValueError(f"preflight readiness gate result {index} must be an object")
        if gate.get("name") != expected_name or gate.get("passed") is not True:
            raise ValueError(
                f"preflight readiness gate result {expected_name} is not a passed tool result"
            )
        if gate.get("errors") != 0 or gate.get("blockers") not in ([], ()):
            raise ValueError(
                f"preflight readiness gate result {expected_name} contains blockers"
            )
    score = readiness.get("score")
    threshold = readiness.get("score_threshold")
    if (
        not _is_number(score)
        or threshold != 85
        or score < threshold
    ):
        raise ValueError("preflight readiness content score did not pass 85")
    aeo_geo = _required_mapping(readiness.get("aeo_geo"), "preflight_readiness.aeo_geo")
    if (
        aeo_geo.get("passed") is not True
        or aeo_geo.get("threshold") != 90
        or not _is_number(aeo_geo.get("score"))
        or aeo_geo["score"] < 90
    ):
        raise ValueError("preflight readiness AEO/GEO score did not pass 90")
    inputs = _required_mapping(readiness.get("input_hashes"), "preflight_readiness.input_hashes")
    bom_input = _required_mapping(inputs.get("assembly_bom"), "input_hashes.assembly_bom")
    expected_bom_input = canonical_artifact(
        bom_path,
        workspace_root=workspace_root,
    )
    if dict(bom_input) != expected_bom_input:
        raise ValueError("preflight input hash mismatch: assembly_bom")
    readiness_bom_path = readiness.get("assembly_bom")
    if not isinstance(readiness_bom_path, str) or not readiness_bom_path:
        raise ValueError("preflight readiness assembly_bom path is missing")
    try:
        readiness_bom_candidate = Path(readiness_bom_path)
        if not readiness_bom_candidate.is_absolute():
            readiness_bom_candidate = resolve_artifact(
                readiness_bom_path,
                workspace_root=workspace_root,
            )
        readiness_bom_identity = canonical_artifact(
            readiness_bom_candidate,
            workspace_root=workspace_root,
        )
    except ValueError as error:
        raise ValueError("preflight readiness assembly_bom path is invalid") from error
    if readiness_bom_identity != expected_bom_input:
        raise ValueError("preflight readiness binds a different assembly BOM path")
    artifacts = _required_mapping(bom.get("artifacts"), "bom.artifacts")
    for input_label, expected in artifact_inventory_snapshots(artifacts).items():
        row = _required_mapping(
            inputs.get(input_label),
            f"input_hashes.{input_label}",
        )
        if dict(row) != expected:
            raise ValueError(f"preflight input hash mismatch: {input_label}")


def _verify_bom_artifacts_unchanged(bom: Mapping[str, Any], root: Path) -> None:
    artifacts = _required_mapping(bom.get("artifacts"), "bom.artifacts")
    for label, row in artifacts.items():
        if row is None:
            continue
        if isinstance(row, list):
            for index, item in enumerate(row):
                verify_artifact(item, workspace_root=root, field=f"artifacts.{label}[{index}]")
        else:
            verify_artifact(row, workspace_root=root, field=f"artifacts.{label}")


def _optional_artifact(path: str | Path | None, root: Path) -> dict[str, str] | None:
    return canonical_artifact(path, workspace_root=root) if path is not None else None


def _read_json_object(path: str | Path, field: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{field} must be a readable JSON object: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{field} must be a JSON object")
    return payload


def _required_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    if value.strip().casefold() in PLACEHOLDER_VALUES:
        raise ValueError(f"{field} cannot be a placeholder")
    return value.strip()


def _validate_input_path(value: Any, *, field: str) -> str | Path:
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise ValueError(f"{field} must be a path")
    return value


def _validate_path_sequence(value: Any, *, field: str) -> tuple[str | Path, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{field} must be a sequence of paths")
    normalized: list[str | Path] = []
    for index, item in enumerate(value):
        try:
            normalized.append(_validate_input_path(item, field=f"{field}[{index}]"))
        except ValueError as error:
            raise ValueError(f"{field} must be a sequence of paths: {error}") from error
    return tuple(normalized)


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ValueError(f"{field} must be a list of non-empty strings")
    return [item.strip() for item in value]


def _required_enum(value: Any, field: str, allowed: frozenset[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{field} must be one of: {', '.join(sorted(allowed))}")
    return value


def _iso_date(value: Any, field: str) -> date:
    return validate_current_assembly_date(value, field=field)


def _required_article_scalar(article: PublishableMarkdown, field: str) -> str:
    return _required_string(article.scalar(field), f"article.{field}")


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _visible_faq_questions(content: str) -> list[str]:
    structure = detect_faq_structure(content)
    if structure.unsupported_lines:
        raise ValueError(
            "FAQ-like details or bold-question markup is unsupported; use a recognized FAQ H2 with question headings"
        )
    return [entry.question for entry in structure.entries]


def _has_video_embed(content: str) -> bool:
    return inspect_video_embeds(content).has_supported_embed


if __name__ == "__main__":  # pragma: no cover - exercised through CLI usage.
    raise SystemExit(main())
