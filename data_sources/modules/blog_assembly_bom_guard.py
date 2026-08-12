"""Validate strict, evidence-backed blog assembly BOM artifacts."""

from __future__ import annotations

import copy
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from . import (
        blog_assembly_contract,
        blog_assembly_capabilities,
        blog_assembly_stage_receipt,
        blog_identity_guard,
        context_binding_guard,
        editorial_plan_guard,
    )
    from .blog_assembly_bom import (
        BOM_SCHEMA,
        EDITORIAL_PLAN_SCHEMA,
        LIFECYCLE_STATES,
        WORKFLOW_MODES,
        _editorial_plan_summary,
        _resolvable_receipt_evidence_hashes,
        _schema_policy,
        _visible_faq_questions,
        _validate_prior_preflight_readiness,
        validate_preflight_stage_receipt_binding,
    )
    from .blog_assembly_contract import (
        artifact_inventory_snapshots,
        canonical_artifact,
        canonical_article_run_id,
        canonical_json_sha256,
        expected_blog_gate_inventory,
        is_json_number,
        load_json_object_snapshot,
        normalized_text_sha256,
        NORMAL_FINAL_STAGES,
        NORMAL_PROVISIONAL_STAGES,
        OPTIMIZED_FINAL_STAGES,
        OPTIMIZED_PROVISIONAL_STAGES,
        resolve_artifact,
        sidecar_evidence_binding_errors,
        validate_sha256,
        verify_artifact,
    )
    from .guard_common import Finding, make_finding
    from .publishable_markdown import FrontmatterError, read_publishable_markdown
except ImportError:  # pragma: no cover - supports direct script execution.
    import blog_assembly_contract
    import blog_assembly_capabilities
    import blog_identity_guard
    import blog_assembly_stage_receipt
    import context_binding_guard
    import editorial_plan_guard
    from blog_assembly_bom import (
        BOM_SCHEMA,
        EDITORIAL_PLAN_SCHEMA,
        LIFECYCLE_STATES,
        WORKFLOW_MODES,
        _editorial_plan_summary,
        _resolvable_receipt_evidence_hashes,
        _schema_policy,
        _visible_faq_questions,
        _validate_prior_preflight_readiness,
        validate_preflight_stage_receipt_binding,
    )
    from blog_assembly_contract import (
        artifact_inventory_snapshots,
        canonical_artifact,
        canonical_article_run_id,
        canonical_json_sha256,
        expected_blog_gate_inventory,
        is_json_number,
        load_json_object_snapshot,
        normalized_text_sha256,
        NORMAL_FINAL_STAGES,
        NORMAL_PROVISIONAL_STAGES,
        OPTIMIZED_FINAL_STAGES,
        OPTIMIZED_PROVISIONAL_STAGES,
        resolve_artifact,
        sidecar_evidence_binding_errors,
        validate_sha256,
        verify_artifact,
    )
    from guard_common import Finding, make_finding
    from publishable_markdown import FrontmatterError, read_publishable_markdown


FORBIDDEN_TOPOLOGY_PATTERNS = (
    "/".join(("obsidian", "simpro brand context", "")),
    "".join(("wi", "ki", "/")),
    "_".join(("authority", "root")),
    "_".join(("simpro", "vault", "root")),
)
PATH_SHAPED_RE = re.compile(
    r"(?:^[A-Za-z]:[/\\]|^[/\\]{2}|^/|(?:^|[/\\])\.\.(?:[/\\]|$)|\$\{|%[A-Za-z_][A-Za-z0-9_]*%)"
)
REQUIRED_ARTIFACT_FIELDS = (
    "article",
    "validation_sidecar",
    "editorial_plan",
    "serp_evidence",
    "paa_artifact",
    "content_brief",
    "user_paa_csv",
    "answersocrates_blocker",
    "context_request",
    "context_pack",
    "context_receipt",
    "customer_proof_selector_evidence",
    "fred_authority_evidence",
    "execution_evidence",
    "optimizer_outputs",
    "stage_receipts",
    "stage_evidence",
    "prior_preflight_readiness",
    "preflight_readiness",
)
REQUIRED_TOP_LEVEL_FIELDS = frozenset({
    "schema",
    "lifecycle_state",
    "workflow_mode",
    "assembly_date",
    "identity",
    "artifacts",
    "connector_binding",
    "author_policy",
    "schema_policy",
    "faq_policy",
    "paa_policy",
    "editorial_plan_summary",
    "workflow",
    "preflight",
})


def missing_bom_finding() -> Finding:
    """Return the stable blocker for a blog without its execution record."""
    return _finding("bom_missing", "Blog artifacts require --assembly-bom.")


def check_bom_file(
    path: str | Path,
    *,
    article_path: str | Path,
    validation_sidecar_path: str | Path,
    context_request_path: str | Path | None = None,
    context_pack_path: str | Path | None = None,
    context_receipt_path: str | Path | None = None,
    workspace_root: str | Path | None = None,
    expected_lifecycle_state: str | None = None,
    context_result: context_binding_guard.ContextValidationResult | None = None,
    context_client: Any = None,
    vault_root: str | Path | None = None,
) -> list[Finding]:
    """Read and validate one strict BOM against current workflow files."""
    source = Path(path)
    root = Path(workspace_root).resolve() if workspace_root else source.resolve().parent.parent
    if workspace_root is not None:
        try:
            canonical_artifact(source, workspace_root=root)
        except ValueError as error:
            return [_finding("bom_path_invalid", f"Blog assembly BOM path is invalid: {error}")]
    try:
        payload = load_json_object_snapshot(source, field="blog assembly BOM").payload
    except ValueError as error:
        return [_finding("bom_invalid", f"Blog assembly BOM is invalid: {error}")]
    if not isinstance(payload, Mapping):
        return [_finding("bom_invalid", "Blog assembly BOM must be a JSON object.")]
    return check_bom(
        payload,
        article_path=article_path,
        validation_sidecar_path=validation_sidecar_path,
        context_request_path=context_request_path,
        context_pack_path=context_pack_path,
        context_receipt_path=context_receipt_path,
        workspace_root=root,
        expected_lifecycle_state=expected_lifecycle_state,
        context_result=context_result,
        context_client=context_client,
        vault_root=vault_root,
    )


def check_bom(
    bom: Mapping[str, Any],
    *,
    article_path: str | Path,
    validation_sidecar_path: str | Path,
    context_request_path: str | Path | None = None,
    context_pack_path: str | Path | None = None,
    context_receipt_path: str | Path | None = None,
    workspace_root: str | Path | None = None,
    expected_lifecycle_state: str | None = None,
    context_result: context_binding_guard.ContextValidationResult | None = None,
    context_client: Any = None,
    vault_root: str | Path | None = None,
) -> list[Finding]:
    """Return deterministic blocking findings for one BOM object."""
    root = Path(workspace_root or Path.cwd()).resolve()
    findings: list[Finding] = []
    missing_fields = REQUIRED_TOP_LEVEL_FIELDS - set(bom)
    unknown_fields = set(bom) - REQUIRED_TOP_LEVEL_FIELDS
    if missing_fields:
        findings.append(
            _finding(
                "bom_shape_missing_fields",
                "BOM is missing strict top-level fields: "
                + ", ".join(sorted(missing_fields)),
            )
        )
    if unknown_fields:
        findings.append(
            _finding(
                "bom_shape_unknown_fields",
                "BOM contains unsupported top-level fields: "
                + ", ".join(sorted(unknown_fields)),
            )
        )
    if bom.get("schema") != BOM_SCHEMA:
        findings.append(_finding("bom_schema_invalid", f"BOM must use {BOM_SCHEMA}."))
    lifecycle = bom.get("lifecycle_state")
    if lifecycle not in LIFECYCLE_STATES:
        findings.append(_finding("bom_lifecycle_state_invalid", "BOM lifecycle_state is invalid."))
    if expected_lifecycle_state and lifecycle != expected_lifecycle_state:
        findings.append(
            _finding(
                "bom_lifecycle_state_mismatch",
                f"Readiness requires a {expected_lifecycle_state} BOM.",
            )
        )
    if bom.get("workflow_mode") not in WORKFLOW_MODES:
        findings.append(_finding("bom_workflow_mode_invalid", "BOM workflow_mode is invalid."))
    assembly_date = _parse_date(bom.get("assembly_date"))
    if assembly_date is None:
        findings.append(_finding("bom_assembly_date_invalid", "BOM assembly_date must be an ISO date."))
    elif assembly_date != blog_assembly_contract.current_utc_date():
        findings.append(
            _finding(
                "bom_assembly_date_not_current",
                "BOM assembly_date must equal the current UTC date.",
            )
        )

    findings.extend(_check_topology(bom))
    artifacts = bom.get("artifacts")
    if not isinstance(artifacts, Mapping):
        findings.append(_finding("bom_artifacts_missing", "BOM requires a strict artifacts inventory."))
        return _sorted(findings)
    for field in REQUIRED_ARTIFACT_FIELDS:
        if field not in artifacts:
            findings.append(_finding(f"bom_{field}_missing", f"BOM artifacts.{field} is missing."))
    unknown_artifact_fields = set(artifacts) - set(REQUIRED_ARTIFACT_FIELDS)
    if unknown_artifact_fields:
        findings.append(
            _finding(
                "bom_artifacts_unknown_fields",
                "BOM artifacts contains unsupported fields: "
                + ", ".join(sorted(str(field) for field in unknown_artifact_fields)),
            )
        )

    article = None
    sidecar_content = ""
    findings.extend(_check_artifact_inventory(bom, artifacts, root))
    article_path_findings = _check_supplied_path(
        artifacts,
        "article",
        article_path,
        root,
    )
    sidecar_path_findings = _check_supplied_path(
        artifacts,
        "validation_sidecar",
        validation_sidecar_path,
        root,
    )
    findings.extend(article_path_findings)
    findings.extend(sidecar_path_findings)
    article_input_safe = _is_workspace_file(article_path, root)
    sidecar_input_safe = _is_workspace_file(validation_sidecar_path, root)
    if article_input_safe:
        try:
            article = read_publishable_markdown(article_path)
        except (OSError, UnicodeError, FrontmatterError) as error:
            findings.append(_finding("bom_article_unreadable", f"Article cannot be read: {error}"))
    if sidecar_input_safe:
        try:
            sidecar_content = Path(validation_sidecar_path).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            findings.append(_finding("bom_sidecar_unreadable", f"Sidecar cannot be read: {error}"))

    safe_context_inputs: dict[str, str | Path | None] = {}
    for label, supplied in (
        ("context_request", context_request_path),
        ("context_pack", context_pack_path),
        ("context_receipt", context_receipt_path),
    ):
        if supplied is not None:
            findings.extend(_check_supplied_path(artifacts, label, supplied, root))
            safe_context_inputs[label] = supplied if _is_workspace_file(supplied, root) else None
        else:
            safe_context_inputs[label] = None

    if article is not None:
        findings.extend(_check_identity(bom, article, assembly_date))
        findings.extend(_check_author(bom, article, sidecar_content))
        findings.extend(_check_schema_and_faq(bom, article))
        findings.extend(_check_paa_policy(bom, article))
        findings.extend(
            _check_connector(
                bom,
                article,
                validation_sidecar_path=(
                    validation_sidecar_path if sidecar_input_safe else None
                ),
                context_request_path=safe_context_inputs["context_request"],
                context_pack_path=safe_context_inputs["context_pack"],
                context_receipt_path=safe_context_inputs["context_receipt"],
                context_result=context_result,
                context_client=context_client,
                vault_root=vault_root,
            )
        )
    connector = bom.get("connector_binding")
    for rule_id, message in sidecar_evidence_binding_errors(
        sidecar_content,
        artifacts,
        workspace_root=root,
        required=(
            isinstance(connector, Mapping)
            and connector.get("status") == "required"
        ),
    ):
        findings.append(_finding(rule_id, message))
    findings.extend(_check_editorial_plan(bom, artifacts, root))
    findings.extend(_check_workflow(bom, artifacts, root))
    findings.extend(_check_preflight(bom, artifacts, root))
    return _sorted(findings)


def _check_artifact_inventory(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
) -> list[Finding]:
    findings: list[Finding] = []
    singleton_fields = set(REQUIRED_ARTIFACT_FIELDS) - {
        "execution_evidence",
        "optimizer_outputs",
        "stage_receipts",
        "stage_evidence",
    }
    for field in singleton_fields:
        row = artifacts.get(field)
        if row is None:
            continue
        findings.extend(_verify_row(row, field, root))
    for field in ("optimizer_outputs", "stage_receipts", "stage_evidence"):
        rows = artifacts.get(field)
        if not isinstance(rows, list):
            findings.append(_finding(f"bom_{field}_invalid", f"artifacts.{field} must be a list."))
            continue
        for index, row in enumerate(rows):
            findings.extend(_verify_row(row, f"{field}_{index}", root))
    execution_evidence = artifacts.get("execution_evidence")
    workflow = bom.get("workflow")
    receipts = workflow.get("stage_receipts") if isinstance(workflow, Mapping) else []
    for rule_id, message in blog_assembly_capabilities.validate_execution_evidence(
        execution_evidence,
        receipts=receipts if isinstance(receipts, list) else [],
        workspace_root=root,
    ):
        findings.append(_finding(rule_id, message))

    for field in ("article", "validation_sidecar", "editorial_plan", "serp_evidence"):
        if artifacts.get(field) is None:
            findings.append(_finding(f"bom_{field}_missing", f"artifacts.{field} is required."))
    paa = bom.get("paa_policy")
    source_kind = paa.get("source_kind") if isinstance(paa, Mapping) else None
    required_paa_artifact = {
        "answersocrates": "paa_artifact",
        "brief_paa": "content_brief",
        "user_csv": "user_paa_csv",
    }.get(source_kind)
    if required_paa_artifact and artifacts.get(required_paa_artifact) is None:
        findings.append(
            _finding(
                f"bom_{required_paa_artifact}_missing",
                f"PAA source {source_kind} requires artifacts.{required_paa_artifact}.",
            )
        )
    if source_kind == "user_csv" and artifacts.get("answersocrates_blocker") is None:
        findings.append(
            _finding(
                "bom_answersocrates_blocker_missing",
                "User CSV PAA requires a bound AnswerSocrates blocker artifact.",
            )
        )
    connector = bom.get("connector_binding")
    connector_required = isinstance(connector, Mapping) and connector.get("status") == "required"
    if connector_required:
        for field in (
            "context_request",
            "context_pack",
            "context_receipt",
            "customer_proof_selector_evidence",
            "fred_authority_evidence",
        ):
            if artifacts.get(field) is None:
                findings.append(_finding(f"bom_{field}_missing", f"Connector-bound BOM requires artifacts.{field}."))
    lifecycle = bom.get("lifecycle_state")
    workflow = bom.get("workflow")
    embedded_receipts = (
        workflow.get("stage_receipts") if isinstance(workflow, Mapping) else None
    )
    optimized = isinstance(embedded_receipts, list) and any(
        isinstance(receipt, Mapping) and receipt.get("stage") == "optimization"
        for receipt in embedded_receipts
    )
    if optimized and artifacts.get("prior_preflight_readiness") is None:
        findings.append(
            _finding(
                "bom_prior_preflight_readiness_missing",
                "Optimized BOM requires the earlier passed preflight readiness artifact.",
            )
        )
    if not optimized and artifacts.get("prior_preflight_readiness") is not None:
        findings.append(
            _finding(
                "bom_prior_preflight_readiness_unexpected",
                "Prior preflight readiness is allowed only for an optimized workflow.",
            )
        )
    if lifecycle == "final" and artifacts.get("preflight_readiness") is None:
        findings.append(_finding("bom_preflight_readiness_missing", "Final BOM requires passed preflight readiness evidence."))
    if lifecycle == "provisional" and artifacts.get("preflight_readiness") is not None:
        findings.append(_finding("bom_provisional_readiness_present", "Provisional BOM cannot bind preflight output before it runs."))
    return findings


def _load_bound_json_object(
    row: Any,
    *,
    workspace_root: Path,
    field: str,
) -> tuple[Path, dict[str, Any]]:
    """Hash and parse one bound JSON object from the same immutable bytes."""
    if not isinstance(row, Mapping):
        raise ValueError(f"{field} must be a path/hash object")
    expected = validate_sha256(row.get("sha256"), field=f"{field}.sha256")
    path = resolve_artifact(row.get("path"), workspace_root=workspace_root)
    snapshot = load_json_object_snapshot(path, field=field)
    if snapshot.sha256 != expected:
        raise ValueError(f"{field}.sha256 does not match current file contents")
    return path, snapshot.payload


def _verify_row(row: Any, field: str, root: Path) -> list[Finding]:
    if not isinstance(row, Mapping) or set(row) != {"path", "sha256"}:
        return [
            _finding(
                f"bom_{field}_invalid",
                f"artifacts.{field} must contain only path and sha256.",
            )
        ]
    try:
        verify_artifact(row, workspace_root=root, field=f"artifacts.{field}")
    except ValueError as error:
        message = str(error)
        if "sha256 does not match" in message:
            suffix = "hash_mismatch"
        elif "unavailable" in message:
            suffix = "unavailable"
        elif "path" in message:
            suffix = "path_invalid"
        else:
            suffix = "invalid"
        return [_finding(f"bom_{field}_{suffix}", message)]
    return []


def _check_supplied_path(
    artifacts: Mapping[str, Any],
    field: str,
    supplied: str | Path,
    root: Path,
) -> list[Finding]:
    row = artifacts.get(field)
    if not isinstance(row, Mapping):
        return []
    try:
        expected = canonical_artifact(supplied, workspace_root=root)
    except ValueError as error:
        return [_finding(f"bom_{field}_input_invalid", str(error))]
    if row.get("path") != expected["path"]:
        return [_finding(f"bom_{field}_path_mismatch", f"BOM {field} path does not match readiness input.")]
    if row.get("sha256") != expected["sha256"]:
        return [_finding(f"bom_{field}_hash_mismatch", f"BOM {field} hash does not match readiness input.")]
    return []


def _is_workspace_file(path: str | Path, root: Path) -> bool:
    try:
        canonical_artifact(path, workspace_root=root)
    except ValueError:
        return False
    return True


def _check_identity(bom: Mapping[str, Any], article: Any, assembled: date | None) -> list[Finding]:
    identity = bom.get("identity")
    if not isinstance(identity, Mapping):
        return [_finding("bom_identity_missing", "BOM requires identity.")]
    identity_fields = {
        "artifact_type",
        "brand",
        "title",
        "objective",
        "audience",
        "region",
        "last_updated",
    }
    findings = list(
        blog_identity_guard.check_article(article.raw, assembly_date=assembled)
    )
    if set(identity) != identity_fields:
        findings.append(
            _finding(
                "bom_identity_shape_invalid",
                "BOM identity must contain only the exact v1 identity fields.",
            )
        )
    expected = {
        key: article.scalar(key)
        for key in identity_fields
    }
    result: list[Finding] = findings
    for field, value in expected.items():
        if identity.get(field) != value:
            result.append(_finding(f"bom_identity_{field}_mismatch", f"BOM identity.{field} does not match the final article."))
    return result


def _check_author(
    bom: Mapping[str, Any],
    article: Any,
    sidecar_content: str,
) -> list[Finding]:
    policy = bom.get("author_policy")
    if not isinstance(policy, Mapping):
        return [_finding("bom_author_policy_missing", "BOM requires author_policy.")]
    author = article.scalar("author")
    named = bool(author)
    expected = {
        "status": "named_author" if named else "not_provided",
        "name": author if named else "",
        "frontmatter_author_required": named,
        "schema_person_required": named,
        "named_author_voice_allowed": named,
    }
    findings = []
    if dict(policy) != expected:
        findings.append(_finding("bom_author_policy_mismatch", "BOM author_policy does not match final article frontmatter."))
    normalized = sidecar_content.casefold()
    token = "author policy: named_author" if named else "author policy: not_provided"
    if token not in normalized:
        findings.append(_finding("bom_author_policy_sidecar_missing", "Validation sidecar must record the exact author policy."))
    return findings


def _check_schema_and_faq(bom: Mapping[str, Any], article: Any) -> list[Finding]:
    try:
        expected = _schema_policy(article)
    except ValueError as exc:
        rule_id = (
            "bom_video_embed_invalid"
            if "video embed" in str(exc).casefold()
            else "bom_faq_structure_unsupported"
        )
        return [_finding(rule_id, str(exc))]
    policy = bom.get("schema_policy")
    findings: list[Finding] = []
    if not isinstance(policy, Mapping):
        return [_finding("bom_schema_policy_missing", "BOM requires schema_policy.")]
    if dict(policy) != expected:
        findings.append(_finding("bom_schema_policy_mismatch", "BOM schema_policy does not match the final article."))
    if expected["declared_entities"] != expected["required_entities"]:
        findings.append(_finding("bom_schema_entities_mismatch", "Article schema_notes must exactly match visible author, FAQ, and video state."))
    faq_policy = bom.get("faq_policy")
    if not isinstance(faq_policy, Mapping):
        findings.append(_finding("bom_faq_policy_missing", "BOM requires faq_policy."))
    else:
        if set(faq_policy) != {"status", "rationale"}:
            findings.append(
                _finding(
                    "bom_faq_policy_shape_invalid",
                    "BOM faq_policy must contain only status and rationale.",
                )
            )
        status = faq_policy.get("status")
        visible = expected["visible_faq"]
        if visible and status != "required":
            findings.append(_finding("bom_faq_policy_required", "Visible FAQ content requires faq_policy.status required."))
        if not visible and status != "not_applicable":
            findings.append(_finding("bom_faq_policy_not_applicable", "A blog without visible FAQs requires a reasoned not_applicable policy."))
        if status == "not_applicable" and not str(faq_policy.get("rationale") or "").strip():
            findings.append(_finding("bom_faq_policy_rationale_missing", "FAQ not_applicable requires a rationale."))
    return findings


def _check_paa_policy(bom: Mapping[str, Any], article: Any) -> list[Finding]:
    policy = bom.get("paa_policy")
    if not isinstance(policy, Mapping):
        return [_finding("bom_paa_policy_missing", "BOM requires paa_policy.")]
    findings: list[Finding] = []
    if set(policy) != {"source_kind", "query", "selected_questions"}:
        findings.append(
            _finding(
                "bom_paa_policy_shape_invalid",
                "paa_policy must contain only source_kind, query, and selected_questions.",
            )
        )
    source_kind = policy.get("source_kind")
    if source_kind not in {"answersocrates", "brief_paa", "user_csv"}:
        findings.append(
            _finding(
                "bom_paa_source_kind_invalid",
                "PAA source_kind must be answersocrates, brief_paa, or user_csv.",
            )
        )
    if bom.get("workflow_mode") == "new" and source_kind == "brief_paa":
        findings.append(
            _finding(
                "bom_paa_source_kind_invalid",
                "New blogs cannot use rewrite-only brief_paa provenance.",
            )
        )
    query = policy.get("query")
    if not isinstance(query, str) or not query.strip():
        findings.append(_finding("bom_paa_query_missing", "PAA policy requires its exact query."))
    selected = policy.get("selected_questions")
    if not isinstance(selected, list) or any(
        not isinstance(question, str) or not question.strip()
        for question in selected
    ):
        findings.append(
            _finding(
                "bom_paa_questions_invalid",
                "PAA selected_questions must be a list of non-empty strings.",
            )
        )
    else:
        try:
            visible = _visible_faq_questions(article.body)
        except ValueError as exc:
            findings.append(_finding("bom_faq_structure_unsupported", str(exc)))
            return findings
        if selected != visible:
            findings.append(
                _finding(
                    "bom_paa_questions_mismatch",
                    "PAA selected_questions must exactly match visible FAQ headings in order.",
                )
            )
    return findings


def _check_connector(
    bom: Mapping[str, Any],
    article: Any,
    *,
    validation_sidecar_path: str | Path | None,
    context_request_path: str | Path | None,
    context_pack_path: str | Path | None,
    context_receipt_path: str | Path | None,
    context_result: context_binding_guard.ContextValidationResult | None,
    context_client: Any,
    vault_root: str | Path | None,
) -> list[Finding]:
    required = context_binding_guard.requires_context(article.raw)
    binding = bom.get("connector_binding")
    if not isinstance(binding, Mapping):
        return [_finding("bom_connector_binding_missing", "BOM requires connector_binding.")]
    status = binding.get("status")
    expected_fields = (
        {"status", "context"}
        if status == "required"
        else {"status", "reason", "context"}
        if status == "not_applicable"
        else set()
    )
    findings: list[Finding] = []
    if not expected_fields or set(binding) != expected_fields:
        findings.append(
            _finding(
                "bom_connector_binding_shape_invalid",
                "BOM connector_binding must use the exact fields for its status.",
            )
        )
    expected_status = "required" if required else "not_applicable"
    if status != expected_status:
        findings.append(_finding("bom_connector_status_mismatch", "Connector applicability must be derived from the final article."))
        return findings
    if not required:
        if not str(binding.get("reason") or "").strip():
            findings.append(_finding("bom_connector_reason_missing", "Non-connector BOM requires a reason."))
        expected_context = context_binding_guard.ContextValidationResult(
            required=False,
            findings=(),
        ).context_summary()
        if binding.get("context") != expected_context:
            findings.append(
                _finding(
                    "bom_context_summary_mismatch",
                    "Non-connector BOM context must be the exact empty validated summary.",
                )
            )
        return findings
    if context_result is None and all((context_request_path, context_pack_path, context_receipt_path)):
        context_result = context_binding_guard.validate_context_artifacts(
            article.path,
            proof_sidecar=validation_sidecar_path,
            context_request=context_request_path,
            context_pack=context_pack_path,
            context_receipt=context_receipt_path,
            client=context_client,
            vault_root=vault_root,
        )
    if context_result is None or not context_result.passed:
        findings.append(_finding("bom_context_validation_missing", "Connector-bound BOM requires one passed structured Context Binding result."))
        return findings
    if binding.get("context") != context_result.context_summary():
        findings.append(_finding("bom_context_summary_mismatch", "BOM connector summary does not exactly match validated connector artifacts."))
    return findings


def _check_editorial_plan(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
) -> list[Finding]:
    row = artifacts.get("editorial_plan")
    if not isinstance(row, Mapping) or not isinstance(row.get("path"), str):
        return []
    try:
        path, plan = _load_bound_json_object(
            row,
            workspace_root=root,
            field="artifacts.editorial_plan",
        )
    except ValueError as error:
        return [_finding("bom_editorial_plan_invalid", f"Editorial plan is invalid: {error}")]
    if not isinstance(plan, Mapping) or plan.get("schema") != EDITORIAL_PLAN_SCHEMA:
        return [_finding("bom_editorial_plan_schema_invalid", f"Editorial plan must use {EDITORIAL_PLAN_SCHEMA}.")]
    article_row = artifacts.get("article")
    serp_row = artifacts.get("serp_evidence")
    try:
        article_path = verify_artifact(
            article_row,
            workspace_root=root,
            field="artifacts.article",
        )
        serp_path = verify_artifact(
            serp_row,
            workspace_root=root,
            field="artifacts.serp_evidence",
        )
    except ValueError:
        return []
    plan_findings = editorial_plan_guard._check_loaded_plan(
        plan,
        article_path=article_path,
        serp_evidence_path=serp_path,
        assembly_date=(
            str(bom.get("assembly_date"))
            if isinstance(bom.get("assembly_date"), str)
            else None
        ),
    )
    if plan_findings:
        return [
            _finding(
                f"bom_{finding.get('rule_id')}",
                str(finding.get("message") or "Editorial plan is invalid."),
            )
            for finding in plan_findings
        ]
    try:
        expected = _editorial_plan_summary(plan)
    except (KeyError, TypeError) as error:
        return [_finding("bom_editorial_plan_incomplete", f"Editorial plan is incomplete: {error}")]
    findings: list[Finding] = []
    if bom.get("editorial_plan_summary") != expected:
        findings.append(_finding("bom_editorial_plan_summary_mismatch", "BOM editorial plan summary does not match the bound plan."))
    if bom.get("faq_policy") != plan.get("faq_policy"):
        findings.append(
            _finding(
                "bom_faq_policy_mismatch",
                "BOM faq_policy must exactly match the bound editorial plan.",
            )
        )
    ownership = plan.get("query_ownership")
    if isinstance(ownership, Mapping) and ownership.get("decision") == "blocked":
        findings.append(_finding("bom_query_ownership_blocked", "Blocked query ownership prevents readiness."))
    return findings


def _check_workflow(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
) -> list[Finding]:
    workflow = bom.get("workflow")
    if not isinstance(workflow, Mapping):
        return [_finding("bom_workflow_missing", "BOM requires workflow stage receipts.")]
    findings: list[Finding] = []
    if set(workflow) != {"stage_receipts"}:
        findings.append(
            _finding(
                "bom_workflow_shape_invalid",
                "BOM workflow must contain only stage_receipts.",
            )
        )
    embedded = workflow.get("stage_receipts")
    rows = artifacts.get("stage_receipts")
    if not isinstance(embedded, list) or not isinstance(rows, list):
        findings.append(_finding("bom_stage_receipts_invalid", "BOM stage receipts must be strict lists."))
        return findings
    loaded: list[Mapping[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping) or not isinstance(row.get("path"), str):
            continue
        try:
            receipt_path = verify_artifact(
                row,
                workspace_root=root,
                field=f"artifacts.stage_receipts[{index}]",
            )
            receipt_snapshot = load_json_object_snapshot(
                receipt_path,
                field=f"stage receipt {index}",
            )
            if receipt_snapshot.sha256 != row.get("sha256"):
                raise ValueError("stage receipt changed during validation")
            receipt = receipt_snapshot.payload
        except ValueError:
            continue
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            findings.append(_finding("bom_stage_receipt_invalid", f"Stage receipt {index} is invalid: {error}"))
            continue
        if not isinstance(receipt, Mapping):
            findings.append(_finding("bom_stage_receipt_invalid", f"Stage receipt {index} must be an object."))
            continue
        loaded.append(receipt)
    if loaded != embedded:
        findings.append(_finding("bom_stage_receipts_mismatch", "Embedded stage receipts must exactly match bound receipt artifacts."))
    stages = tuple(str(receipt.get("stage") or "") for receipt in loaded)
    optimized = "optimization" in stages
    lifecycle = bom.get("lifecycle_state")
    expected = (
        OPTIMIZED_FINAL_STAGES if optimized and lifecycle == "final"
        else OPTIMIZED_PROVISIONAL_STAGES if optimized
        else NORMAL_FINAL_STAGES if lifecycle == "final"
        else NORMAL_PROVISIONAL_STAGES
    )
    if stages != expected:
        findings.append(_finding("bom_stage_order_invalid", f"BOM stage sequence must be exactly: {' -> '.join(expected)}."))
    if optimized and not artifacts.get("optimizer_outputs"):
        findings.append(_finding("bom_optimizer_evidence_missing", "Optimization stage requires optimizer output evidence."))
    if not optimized and artifacts.get("optimizer_outputs"):
        findings.append(_finding("bom_optimizer_evidence_unexpected", "Optimizer evidence is allowed only when an optimization stage exists."))
    article_row = artifacts.get("article")
    try:
        expected_run_id = canonical_article_run_id(
            resolve_artifact(
                article_row.get("path") if isinstance(article_row, Mapping) else None,
                workspace_root=root,
            ),
            workspace_root=root,
            assembly_date=str(bom.get("assembly_date") or ""),
        )
    except ValueError as error:
        findings.append(
            _finding(
                "bom_stage_canonical_identity_invalid",
                f"Workflow receipt chain lacks canonical article/date identity: {error}",
            )
        )
        expected_run_id = None
    try:
        resolvable_evidence = _resolvable_receipt_evidence_hashes(
            loaded,
            artifacts=artifacts,
            workspace_root=root,
        )
    except ValueError as error:
        findings.append(
            _finding(
                "bom_stage_evidence_invalid",
                f"Stage evidence resolution failed: {error}",
            )
        )
        resolvable_evidence = set()
    findings.extend(
        blog_assembly_stage_receipt.check_receipt_chain(
            loaded,
            expected_run_id=expected_run_id,
            assembly_date=(
                str(bom.get("assembly_date"))
                if isinstance(bom.get("assembly_date"), str)
                else None
            ),
            now=datetime.now(timezone.utc),
            resolvable_evidence_hashes=resolvable_evidence,
        )
    )
    by_stage = {
        str(receipt.get("stage") or ""): receipt
        for receipt in loaded
    }
    prior_readiness: Mapping[str, Any] | None = None
    if optimized:
        prior_row = artifacts.get("prior_preflight_readiness")
        prior_receipt = by_stage.get("preflight_readiness")
        try:
            prior_path = verify_artifact(
                prior_row,
                workspace_root=root,
                field="artifacts.prior_preflight_readiness",
            )
            if not isinstance(prior_receipt, Mapping):
                raise ValueError("missing preflight stage receipt")
            schema_policy = bom.get("schema_policy")
            connector_policy = bom.get("connector_binding")
            prior_readiness = _validate_prior_preflight_readiness(
                prior_path,
                receipt=prior_receipt,
                visible_faq=(
                    isinstance(schema_policy, Mapping)
                    and schema_policy.get("visible_faq") is True
                ),
                connector_required=(
                    isinstance(connector_policy, Mapping)
                    and connector_policy.get("status") == "required"
                ),
                workspace_root=root,
            )
        except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as error:
            findings.append(
                _finding(
                    "bom_prior_preflight_invalid",
                    f"Optimized workflow prior preflight is invalid: {error}",
                )
            )
    draft = by_stage.get("draft")
    if isinstance(draft, Mapping):
        draft_inputs = draft.get("input_artifact_hashes")
        draft_evidence = draft.get("evidence_hashes")
        plan_row = artifacts.get("editorial_plan")
        serp_row = artifacts.get("serp_evidence")
        if (
            not isinstance(draft_inputs, Mapping)
            or not isinstance(plan_row, Mapping)
            or draft_inputs.get("editorial_plan") != plan_row.get("sha256")
        ):
            findings.append(_finding("bom_draft_plan_unbound", "Draft receipt must bind the editorial plan input."))
        if (
            not isinstance(draft_evidence, Mapping)
            or not isinstance(serp_row, Mapping)
            or draft_evidence.get("serp_evidence") != serp_row.get("sha256")
        ):
            findings.append(_finding("bom_draft_serp_unbound", "Draft receipt must bind verified SERP evidence."))
        try:
            if not isinstance(execution_evidence := artifacts.get("execution_evidence"), Mapping):
                raise blog_assembly_capabilities.CapabilityRegistryError(
                    "execution evidence is unavailable"
                )
            expected_draft_evidence = (
                blog_assembly_capabilities.receipt_definition_hashes(
                    loaded,
                    stage="draft",
                    execution_evidence=execution_evidence,
                )
            )
            if not isinstance(draft_evidence, Mapping) or any(
                draft_evidence.get(label) != digest
                for label, digest in expected_draft_evidence.items()
            ):
                raise blog_assembly_capabilities.CapabilityRegistryError(
                    "draft receipt does not bind current route definitions"
                )
        except blog_assembly_capabilities.CapabilityRegistryError as error:
            findings.append(
                _finding(
                    "bom_draft_capability_evidence_unbound",
                    f"Draft capability evidence is invalid: {error}",
                )
            )
    for stage_name in ("scrub", "post_optimization_scrub"):
        stage_receipt = by_stage.get(stage_name)
        if not isinstance(stage_receipt, Mapping):
            continue
        evidence = stage_receipt.get("evidence_hashes")
        try:
            if not isinstance(evidence, Mapping):
                raise ValueError("missing evidence")
            validate_sha256(
                evidence.get("scrub_statistics"),
                field=f"{stage_name}.scrub_statistics",
            )
        except ValueError:
            findings.append(_finding("bom_scrub_statistics_missing", f"{stage_name} receipt must bind scrub statistics."))
    connector = bom.get("connector_binding")
    connector_required = isinstance(connector, Mapping) and connector.get("status") == "required"
    for stage_name in ("context_binding", "post_optimization_context_binding"):
        stage_receipt = by_stage.get(stage_name)
        if not isinstance(stage_receipt, Mapping):
            continue
        stage_inputs = stage_receipt.get("input_artifact_hashes")
        stage_outputs = stage_receipt.get("output_artifact_hashes")
        stage_evidence = stage_receipt.get("evidence_hashes")
        sidecar_row = artifacts.get("validation_sidecar")
        sidecar_hash = stage_outputs.get("validation_sidecar") if isinstance(stage_outputs, Mapping) else None
        expected_sidecar_hash = (
            sidecar_row.get("sha256") if isinstance(sidecar_row, Mapping) else None
        )
        if stage_name == "context_binding" and prior_readiness is not None:
            prior_inputs = prior_readiness.get("input_hashes")
            prior_sidecar = (
                prior_inputs.get("validation_sidecar")
                if isinstance(prior_inputs, Mapping)
                else None
            )
            expected_sidecar_hash = (
                prior_sidecar.get("sha256")
                if isinstance(prior_sidecar, Mapping)
                else None
            )
        if (
            not isinstance(sidecar_hash, str)
            or sidecar_hash != expected_sidecar_hash
        ):
            findings.append(_finding("bom_context_binding_sidecar_unbound", f"{stage_name} receipt must bind its validation sidecar output."))
        try:
            if not isinstance(stage_evidence, Mapping):
                raise ValueError("missing evidence")
            validate_sha256(
                stage_evidence.get("context_binding"),
                field=f"{stage_name}.context_binding",
            )
        except ValueError:
            findings.append(_finding("bom_context_binding_evidence_missing", f"{stage_name} receipt must bind generated Context Binding evidence."))
        if connector_required:
            for label in ("context_request", "context_pack", "context_receipt"):
                artifact_row = artifacts.get(label)
                if (
                    not isinstance(stage_inputs, Mapping)
                    or not isinstance(artifact_row, Mapping)
                    or stage_inputs.get(label) != artifact_row.get("sha256")
                ):
                    findings.append(_finding("bom_context_binding_input_unbound", f"{stage_name} receipt must bind {label}."))
        else:
            try:
                expected_reason_hash = normalized_text_sha256(
                    connector.get("reason") if isinstance(connector, Mapping) else None,
                    field="connector_binding.reason",
                )
            except ValueError:
                expected_reason_hash = None
            if (
                expected_reason_hash is None
                or not isinstance(stage_evidence, Mapping)
                or stage_evidence.get("not_applicable_reason")
                != expected_reason_hash
            ):
                findings.append(
                    _finding(
                        "bom_context_not_applicable_reason_unbound",
                        f"{stage_name} receipt must bind the BOM connector "
                        "not-applicable reason.",
                    )
                )
    optimization_receipt = by_stage.get("optimization")
    if isinstance(optimization_receipt, Mapping):
        optimization_evidence = optimization_receipt.get("evidence_hashes")
        optimizer_rows = artifacts.get("optimizer_outputs")
        try:
            execution_evidence = artifacts.get("execution_evidence")
            if not isinstance(execution_evidence, Mapping):
                raise blog_assembly_capabilities.CapabilityRegistryError(
                    "execution evidence is unavailable"
                )
            expected_evidence = blog_assembly_capabilities.receipt_definition_hashes(
                loaded,
                stage="optimization",
                execution_evidence=execution_evidence,
            )
            expected_optimizer_rows = [
                execution_evidence[f"agent_output.{agent_id}"]
                for agent_id in blog_assembly_capabilities.expected_agent_ids(loaded)
            ]
            if optimizer_rows != expected_optimizer_rows:
                raise blog_assembly_capabilities.CapabilityRegistryError(
                    "optimizer outputs do not exactly match distinct agent outputs"
                )
            if not isinstance(optimization_evidence, Mapping) or any(
                optimization_evidence.get(label) != digest
                for label, digest in expected_evidence.items()
            ):
                raise blog_assembly_capabilities.CapabilityRegistryError(
                    "optimization receipt does not bind definitions and agent outputs"
                )
        except (KeyError, blog_assembly_capabilities.CapabilityRegistryError) as error:
            findings.append(
                _finding(
                    "bom_optimizer_evidence_unbound",
                    f"Optimization capability evidence is invalid: {error}",
                )
            )
    article_row = artifacts.get("article")
    if loaded and isinstance(article_row, Mapping):
        outputs = loaded[-1].get("output_artifact_hashes")
        if not isinstance(outputs, Mapping) or outputs.get("article") != article_row.get("sha256"):
            findings.append(_finding("bom_final_stage_article_hash_mismatch", "Last stage receipt must bind the final article hash."))
    return findings


def _check_preflight(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
) -> list[Finding]:
    lifecycle = bom.get("lifecycle_state")
    record = bom.get("preflight")
    if lifecycle == "provisional":
        if record is not None:
            return [
                _finding(
                    "bom_provisional_preflight_present",
                    "A provisional BOM cannot contain a preflight seal.",
                )
            ]
        return []
    if lifecycle != "final":
        return []
    readiness_row = artifacts.get("preflight_readiness")
    if not isinstance(readiness_row, Mapping):
        return []
    try:
        readiness_path, readiness = _load_bound_json_object(
            readiness_row,
            workspace_root=root,
            field="artifacts.preflight_readiness",
        )
    except ValueError as error:
        return [
            _finding(
                "bom_preflight_invalid",
                f"Bound preflight readiness is invalid: {error}",
            )
        ]
    if not isinstance(readiness, Mapping):
        return [_finding("bom_preflight_invalid", "Bound preflight readiness must be an object.")]
    expected_record = {
        "path": readiness_row.get("path"),
        "sha256": readiness_row.get("sha256"),
        "tool": readiness.get("tool"),
        "verification_scope": readiness.get("verification_scope"),
        "gate_inventory": readiness.get("gate_inventory"),
        "input_hashes": readiness.get("input_hashes"),
    }
    findings: list[Finding] = []
    if record != expected_record:
        findings.append(
            _finding(
                "bom_preflight_record_mismatch",
                "Final BOM preflight seal must exactly match its bound readiness output.",
            )
        )
    if (
        readiness.get("schema") != "simpro-publish-readiness-result/v1"
        or readiness.get("phase") != "preflight"
        or readiness.get("passed") is not True
        or readiness.get("artifact_kind") != "blog"
        or readiness.get("verification_scope") != "source_artifact"
        or readiness.get("input_seal") != {"status": "verified"}
        or readiness.get("tool")
        != {"name": "publish_readiness", "version": "1.0.0"}
    ):
        findings.append(
            _finding(
                "bom_preflight_invalid",
                "Final BOM requires a passed source-artifact preflight result from publish_readiness 1.0.0.",
            )
        )
        return findings
    schema_policy = bom.get("schema_policy")
    connector_binding = bom.get("connector_binding")
    expected_inventory = expected_blog_gate_inventory(
        visible_faq=(
            isinstance(schema_policy, Mapping)
            and schema_policy.get("visible_faq") is True
        ),
        connector_required=(
            isinstance(connector_binding, Mapping)
            and connector_binding.get("status") == "required"
        ),
    )
    if readiness.get("gate_inventory") != expected_inventory:
        findings.append(
            _finding(
                "bom_preflight_gate_inventory_invalid",
                "Preflight readiness gate inventory is not the exact expected inventory.",
            )
        )
    gates = readiness.get("gates")
    if (
        not isinstance(gates, list)
        or [
            gate.get("name") if isinstance(gate, Mapping) else None
            for gate in gates
        ]
        != expected_inventory
        or any(
            not isinstance(gate, Mapping)
            or gate.get("passed") is not True
            or gate.get("errors") != 0
            or gate.get("blockers") not in ([], ())
            for gate in gates
        )
    ):
        findings.append(
            _finding(
                "bom_preflight_gate_results_invalid",
                "Every exact preflight gate must have a passed, blocker-free tool result.",
            )
        )
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
        or aeo_geo.get("score") < 90
    ):
        findings.append(
            _finding(
                "bom_preflight_scores_invalid",
                "Preflight requires content >=85 and AEO/GEO >=90.",
            )
        )
    inputs = readiness.get("input_hashes")
    if not isinstance(inputs, Mapping):
        findings.append(_finding("bom_preflight_inputs_invalid", "Preflight input_hashes must be an object."))
        return findings
    provisional_artifacts = dict(artifacts)
    provisional_artifacts["preflight_readiness"] = None
    stage_rows = provisional_artifacts.get("stage_receipts")
    if isinstance(stage_rows, list) and stage_rows:
        provisional_artifacts["stage_receipts"] = stage_rows[:-1]
    try:
        expected_inputs = artifact_inventory_snapshots(provisional_artifacts)
    except ValueError as error:
        findings.append(_finding("bom_preflight_inputs_invalid", str(error)))
        return findings
    actual_bound = {
        key: value
        for key, value in inputs.items()
        if key != "assembly_bom"
    }
    if actual_bound != expected_inputs:
        findings.append(
            _finding(
                "bom_preflight_inputs_mismatch",
                "Preflight must bind every provisional BOM artifact exactly.",
            )
        )
    assembly_input = inputs.get("assembly_bom")
    historical_provisional: Mapping[str, Any] | None = None
    try:
        if not isinstance(assembly_input, Mapping):
            raise ValueError("input_hashes.assembly_bom must be an object")
        expected_provisional_hash = validate_sha256(
            assembly_input.get("sha256"),
            field="input_hashes.assembly_bom.sha256",
        )
        _, historical_provisional = _load_bound_json_object(
            assembly_input,
            workspace_root=root,
            field="preflight.input_hashes.assembly_bom",
        )
    except ValueError as error:
        findings.append(
            _finding(
                "bom_preflight_bom_artifact_invalid",
                f"Historical provisional BOM is unavailable or changed: {error}",
            )
        )
    else:
        try:
            provisional = copy.deepcopy(dict(bom))
            provisional["lifecycle_state"] = "provisional"
            provisional["preflight"] = None
            provisional_artifact_inventory = provisional.get("artifacts")
            provisional_workflow = provisional.get("workflow")
            if not isinstance(provisional_artifact_inventory, dict):
                raise ValueError("artifacts must be an object")
            if not isinstance(provisional_workflow, dict):
                raise ValueError("workflow must be an object")
            provisional_artifact_inventory["preflight_readiness"] = None
            receipt_artifacts = provisional_artifact_inventory.get("stage_receipts")
            embedded_receipts = provisional_workflow.get("stage_receipts")
            if not isinstance(receipt_artifacts, list) or not receipt_artifacts:
                raise ValueError("final BOM must contain its preflight receipt artifact")
            if not isinstance(embedded_receipts, list) or not embedded_receipts:
                raise ValueError("final BOM must contain its embedded preflight receipt")
            provisional_artifact_inventory["stage_receipts"] = receipt_artifacts[:-1]
            provisional_workflow["stage_receipts"] = embedded_receipts[:-1]
            actual_provisional_hash = canonical_json_sha256(provisional)
        except (TypeError, ValueError) as error:
            findings.append(_finding("bom_preflight_inputs_invalid", str(error)))
        else:
            if actual_provisional_hash != expected_provisional_hash:
                findings.append(
                    _finding(
                        "bom_preflight_bom_hash_mismatch",
                        "Final BOM base fields do not reconstruct the exact provisional BOM sealed by preflight.",
                    )
                )
            elif historical_provisional != provisional:
                findings.append(
                    _finding(
                        "bom_preflight_bom_hash_mismatch",
                        "Historical provisional BOM content does not match the final BOM base fields.",
                    )
                )

    workflow = bom.get("workflow")
    embedded_receipts = (
        workflow.get("stage_receipts")
        if isinstance(workflow, Mapping)
        else None
    )
    article_row = artifacts.get("article")
    try:
        if not isinstance(embedded_receipts, list) or not embedded_receipts:
            raise ValueError("final BOM must contain an embedded preflight receipt")
        if not isinstance(article_row, Mapping):
            raise ValueError("final BOM article artifact must be an object")
        validate_preflight_stage_receipt_binding(
            embedded_receipts[-1],
            prior_receipts=embedded_receipts[:-1],
            readiness_path=readiness_path,
            article_sha256=article_row.get("sha256"),
            article_path=resolve_artifact(
                article_row.get("path"),
                workspace_root=root,
            ),
            workspace_root=root,
            assembly_date=str(bom.get("assembly_date") or ""),
        )
    except (OSError, UnicodeError, ValueError) as error:
        findings.append(
            _finding(
                "bom_preflight_stage_receipt_invalid",
                f"Final BOM preflight stage receipt is invalid: {error}",
            )
        )
    return findings


def _check_topology(value: Any) -> list[Finding]:
    findings: list[Finding] = []

    def inspect_text(item: str, field_path: tuple[str, ...]) -> None:
        normalized = item.replace("\\", "/").casefold()
        if any(pattern in normalized for pattern in FORBIDDEN_TOPOLOGY_PATTERNS):
            findings.append(_finding("bom_hard_coded_vault_topology", "BOM must not expose fixed vault topology."))
            return
        if _is_declared_artifact_path(field_path):
            return
        if PATH_SHAPED_RE.search(item):
            findings.append(_finding("bom_path_leakage", "Path-shaped strings are allowed only in declared artifact path fields."))

    def visit(item: Any, field_path: tuple[str, ...]) -> None:
        if isinstance(item, Mapping):
            for key, child in item.items():
                inspect_text(str(key), field_path + ("<key>",))
                visit(child, field_path + (str(key),))
            return
        if isinstance(item, list):
            for index, child in enumerate(item):
                visit(child, field_path + (str(index),))
            return
        if not isinstance(item, str):
            return
        inspect_text(item, field_path)

    visit(value, ())
    unique = {str(finding["rule_id"]): finding for finding in findings}
    return list(unique.values())


def _is_declared_artifact_path(field_path: tuple[str, ...]) -> bool:
    singleton_fields = set(REQUIRED_ARTIFACT_FIELDS) - {
        "execution_evidence",
        "optimizer_outputs",
        "stage_receipts",
    }
    if (
        len(field_path) == 3
        and field_path[0] == "artifacts"
        and field_path[1] in singleton_fields
        and field_path[2] == "path"
    ):
        return True
    if (
        len(field_path) == 4
        and field_path[:2] == ("artifacts", "execution_evidence")
        and field_path[3] == "path"
    ):
        return True
    if (
        len(field_path) == 4
        and field_path[0] == "artifacts"
        and field_path[1] in {"optimizer_outputs", "stage_receipts"}
        and field_path[2].isdigit()
        and field_path[3] == "path"
    ):
        return True
    if field_path == ("preflight", "path"):
        return True
    if (
        len(field_path) == 4
        and field_path[:2] == ("preflight", "input_hashes")
        and field_path[3] == "path"
    ):
        label = field_path[2]
        return label == "assembly_bom" or _is_artifact_snapshot_label(label)
    return False


def _is_artifact_snapshot_label(label: str) -> bool:
    if label.startswith(blog_assembly_capabilities.EXECUTION_EVIDENCE_PREFIXES):
        return True
    if label in set(REQUIRED_ARTIFACT_FIELDS) - {
        "execution_evidence",
        "optimizer_outputs",
        "stage_receipts",
    }:
        return True
    return re.fullmatch(r"(?:optimizer_outputs|stage_receipts)\[\d+\]", label) is not None


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _sorted(findings: Sequence[Finding]) -> list[Finding]:
    return sorted(
        findings,
        key=lambda finding: (
            str(finding.get("rule_id", "")),
            str(finding.get("message", "")),
        ),
    )


def _is_number(value: Any) -> bool:
    return is_json_number(value)


def _finding(rule_id: str, message: str) -> Finding:
    return make_finding(
        rule_id,
        "error",
        1,
        message=message,
        suggestion="Regenerate the BOM from current workflow artifacts.",
    )
