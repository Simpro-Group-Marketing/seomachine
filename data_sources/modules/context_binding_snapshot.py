"""Immutable-payload validation for Context Binding artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


@dataclass(frozen=True)
class ContextBindingDependencies:
    """Explicit operations and contracts required by snapshot validation."""

    binding_schema: str
    pack_schema: str
    receipt_schema: str
    required_revisions: frozenset[str]
    validate_repo_context: Callable[..., Any]
    validate_request_article: Callable[..., Any]
    validate_claim_map: Callable[..., Any]
    context_findings: Callable[..., Any]
    finding: Callable[..., Any]
    json_block: Callable[..., Any]
    client_factory: Callable[..., Any]
    vault_error: type[Exception]
    result_factory: Callable[..., Any]


def build_binding(
    *,
    dependencies: ContextBindingDependencies,
    article_name: str,
    article_sha256: str,
    request_name: str,
    request_sha256: str,
    pack_name: str,
    pack_sha256: str,
    pack: Mapping[str, Any],
    receipt_name: str,
    receipt_sha256: str,
    receipt: Mapping[str, Any],
    repo_context: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    """Build the deterministic binding from exact captured payloads."""
    sections = pack.get("sections", {})
    discovery = sections.get("Discovery Trace", {}) if isinstance(sections, Mapping) else {}
    constraints = sections.get("Constraints and Unresolved Gaps", {}) if isinstance(sections, Mapping) else {}
    task_scope = sections.get("Task and Scope", {}) if isinstance(sections, Mapping) else {}
    revisions = receipt.get("revisions")
    if not isinstance(revisions, Mapping):
        revisions = {}
    return {
        "schema": dependencies.binding_schema,
        "article": {"file": article_name, "sha256": article_sha256},
        "request": {"file": request_name, "sha256": request_sha256},
        "pack": {
            "file": pack_name,
            "schema": pack.get("schema"),
            "sha256": pack_sha256,
            "canonical_sha256": receipt.get("pack_sha256"),
        },
        "receipt": {
            "file": receipt_name,
            "schema": receipt.get("schema"),
            "sha256": receipt_sha256,
            "canonical_sha256": receipt.get("receipt_sha256"),
        },
        "revisions": revisions,
        "approval_policy_revision": revisions.get("approval_policy_revision"),
        "claim_registry_revision": revisions.get("claim_registry_revision")
        or receipt.get("claim_registry_revision"),
        "resource_ids": discovery.get("selected_resource_ids", []),
        "task_satisfaction": task_scope.get("task_satisfaction"),
        "unresolved_gaps": constraints.get("unresolved_gaps", []),
        "repo_context": dependencies.validate_repo_context(repo_context),
    }


def validate_payload_findings(
    *,
    dependencies: ContextBindingDependencies,
    article_content: str,
    article_path: Path,
    article_sha256: str,
    proof_content: str,
    request: Mapping[str, Any],
    request_path: Path,
    request_sha256: str,
    pack: Mapping[str, Any],
    pack_path: Path,
    pack_sha256: str,
    receipt: Mapping[str, Any],
    receipt_path: Path,
    receipt_sha256: str,
    editorial_plan: Mapping[str, Any] | None,
    vault_root: str | Path | None,
    client: Any,
) -> list[dict[str, Any]]:
    """Run Context Binding rules without reopening any captured artifact."""
    findings = dependencies.validate_request_article(
        request,
        article_content,
        article_path=article_path,
    )
    pack_revisions = pack.get("revisions")
    receipt_revisions = receipt.get("revisions")
    if (
        not isinstance(pack_revisions, Mapping)
        or not isinstance(receipt_revisions, Mapping)
        or set(pack_revisions) != dependencies.required_revisions
        or pack_revisions != receipt_revisions
        or any(
            not isinstance(pack_revisions.get(name), str)
            or not pack_revisions.get(name)
            for name in dependencies.required_revisions
        )
    ):
        findings.append(dependencies.finding(
            "context_revisions_invalid",
            "Context pack and receipt must bind the same complete current revision set.",
        ))
    if pack.get("schema") != dependencies.pack_schema:
        findings.append(dependencies.finding(
            "context_pack_schema_invalid",
            f"Context pack must use {dependencies.pack_schema}.",
        ))
    if receipt.get("schema") != dependencies.receipt_schema:
        findings.append(dependencies.finding(
            "context_receipt_schema_invalid",
            f"Context receipt must use {dependencies.receipt_schema}.",
        ))
    findings.extend(dependencies.context_findings(
        content=article_content,
        request=request,
        pack=pack,
        receipt=receipt,
        plan=editorial_plan,
    ))
    if findings:
        return findings
    connector_findings = _connector_findings(
        dependencies,
        request=request,
        pack=pack,
        receipt=receipt,
        vault_root=vault_root,
        client=client,
    )
    if connector_findings:
        return connector_findings
    try:
        binding = dependencies.json_block(proof_content, "Context Binding")
        claim_map = dependencies.json_block(proof_content, "Context Claim Use Map")
        expected = build_binding(
            dependencies=dependencies,
            article_name=article_path.name,
            article_sha256=article_sha256,
            request_name=request_path.name,
            request_sha256=request_sha256,
            pack_name=pack_path.name,
            pack_sha256=pack_sha256,
            pack=pack,
            receipt_name=receipt_path.name,
            receipt_sha256=receipt_sha256,
            receipt=receipt,
            repo_context=(
                binding.get("repo_context", []) if isinstance(binding, dict) else []
            ),
        )
    except ValueError as error:
        return [dependencies.finding("context_binding_invalid", str(error))]
    findings.extend(_binding_findings(
        dependencies,
        binding=binding,
        expected=expected,
        article_sha256=article_sha256,
    ))
    findings.extend(dependencies.validate_claim_map(article_content, pack, receipt, claim_map))
    return findings


def _connector_findings(
    dependencies: ContextBindingDependencies,
    *,
    request: Mapping[str, Any],
    pack: Mapping[str, Any],
    receipt: Mapping[str, Any],
    vault_root: str | Path | None,
    client: Any,
) -> list[dict[str, Any]]:
    try:
        validator = client or dependencies.client_factory(vault_root=vault_root)
        validation = validator.validate_context(request, pack, receipt)
    except dependencies.vault_error as error:
        rule = "context_pack_stale" if error.code == "pack_stale" else f"context_{error.code}"
        return [dependencies.finding(rule, str(error), connector_error_code=error.code)]
    except Exception as error:  # pragma: no cover - defensive fail-closed boundary.
        return [dependencies.finding(
            "context_validation_failed", f"Context validation failed: {error}"
        )]
    if not isinstance(validation, dict) or validation.get("valid") is not True or validation.get("errors"):
        return [dependencies.finding(
            "context_validation_failed",
            "The shared connector did not validate the context artifacts.",
        )]
    return []


def _binding_findings(
    dependencies: ContextBindingDependencies,
    *,
    binding: Any,
    expected: Mapping[str, Any],
    article_sha256: str,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not isinstance(binding, dict) or binding.get("schema") != dependencies.binding_schema:
        findings.append(dependencies.finding(
            "context_binding_schema_invalid",
            f"Context Binding must use {dependencies.binding_schema}.",
        ))
    elif binding != expected:
        article = binding.get("article")
        article_hash = article.get("sha256") if isinstance(article, Mapping) else None
        rule = (
            "context_article_hash_mismatch"
            if article_hash != article_sha256
            else "context_binding_hash_mismatch"
        )
        message = (
            "The article changed after Context Binding was generated."
            if rule == "context_article_hash_mismatch"
            else "Context Binding does not match the supplied artifacts."
        )
        findings.append(dependencies.finding(rule, message))
    if expected.get("task_satisfaction") != "satisfied" or expected.get("unresolved_gaps"):
        findings.append(dependencies.finding(
            "context_task_unsatisfied",
            "Context task satisfaction must be satisfied with no unresolved gaps.",
        ))
    return findings


def context_validation_result(
    *,
    dependencies: ContextBindingDependencies,
    required: bool,
    findings: Sequence[Mapping[str, Any]],
    pack: Mapping[str, Any] | None,
    receipt: Mapping[str, Any] | None,
) -> Any:
    """Build the connector-derived summary from already-validated payloads."""
    if findings or not required or pack is None or receipt is None:
        return dependencies.result_factory(required=required, findings=tuple(findings))
    sections = pack.get("sections")
    discovery = sections.get("Discovery Trace") if isinstance(sections, Mapping) else None
    raw_resources = discovery.get("selected_resource_ids") if isinstance(discovery, Mapping) else []
    resource_ids = tuple(dict.fromkeys(
        item.strip() for item in raw_resources
        if isinstance(item, str) and item.strip()
    ))
    decisions = receipt.get("claim_decisions")
    approved_claim_ids = tuple(dict.fromkeys(
        str(row.get("claim_id")).strip()
        for row in decisions if isinstance(row, Mapping)
        and row.get("approved") is True
        and isinstance(row.get("claim_id"), str)
        and str(row.get("claim_id")).strip()
    )) if isinstance(decisions, (list, tuple)) else ()
    revisions = receipt.get("revisions")
    revision_items = tuple(sorted(
        (str(key), str(value)) for key, value in revisions.items()
    )) if isinstance(revisions, Mapping) else ()
    return dependencies.result_factory(
        required=True,
        findings=(),
        resource_ids=resource_ids,
        approved_claim_ids=approved_claim_ids,
        pack_canonical_sha256=str(receipt.get("pack_sha256") or ""),
        receipt_canonical_sha256=str(receipt.get("receipt_sha256") or ""),
        revisions=revision_items,
    )


__all__ = ["build_binding", "context_validation_result", "validate_payload_findings"]
