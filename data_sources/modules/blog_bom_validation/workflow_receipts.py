"""Receipt-specific workflow validation helpers."""

from __future__ import annotations

from typing import Any, Mapping

from .. import blog_assembly_capabilities
from ..blog_assembly_contract import normalized_text_sha256, validate_sha256
from ..guard_common import Finding
from .common import _finding

def _check_draft_receipt(
    by_stage: Mapping[str, Mapping[str, Any]],
    artifacts: Mapping[str, Any],
) -> list[Finding]:
    draft = by_stage.get("draft")
    if not isinstance(draft, Mapping):
        return []
    inputs = draft.get("input_artifact_hashes")
    evidence = draft.get("evidence_hashes")
    bindings = (
        (
            inputs,
            "editorial_plan",
            "bom_draft_plan_unbound",
            "Draft receipt must bind the editorial plan input.",
        ),
        (
            evidence,
            "serp_evidence",
            "bom_draft_serp_unbound",
            "Draft receipt must bind verified SERP evidence.",
        ),
        (
            evidence,
            "keyword_decision",
            "bom_draft_keyword_decision_unbound",
            "Draft receipt must bind Semrush keyword decision evidence.",
        ),
    )
    findings: list[Finding] = []
    for receipt_values, label, rule_id, message in bindings:
        row = artifacts.get(label)
        if (
            not isinstance(receipt_values, Mapping)
            or not isinstance(row, Mapping)
            or receipt_values.get(label) != row.get("sha256")
        ):
            findings.append(_finding(rule_id, message))
    return findings


def _check_scrub_receipts(
    by_stage: Mapping[str, Mapping[str, Any]],
) -> list[Finding]:
    findings: list[Finding] = []
    for stage_name in ("scrub", "post_optimization_scrub"):
        receipt = by_stage.get(stage_name)
        if not isinstance(receipt, Mapping):
            continue
        try:
            evidence = receipt.get("evidence_hashes")
            if not isinstance(evidence, Mapping):
                raise ValueError("missing evidence")
            validate_sha256(
                evidence.get("scrub_statistics"),
                field=f"{stage_name}.scrub_statistics",
            )
        except ValueError:
            findings.append(
                _finding(
                    "bom_scrub_statistics_missing",
                    f"{stage_name} receipt must bind scrub statistics.",
                )
            )
    return findings


def _check_context_receipts(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    by_stage: Mapping[str, Mapping[str, Any]],
    prior_readiness: Mapping[str, Any] | None,
) -> list[Finding]:
    connector = bom.get("connector_binding")
    required = isinstance(connector, Mapping) and connector.get("status") == "required"
    findings: list[Finding] = []
    for stage_name in ("context_binding", "post_optimization_context_binding"):
        receipt = by_stage.get(stage_name)
        if isinstance(receipt, Mapping):
            findings.extend(
                _check_context_receipt(
                    stage_name,
                    receipt,
                    artifacts,
                    connector,
                    required,
                    prior_readiness,
                )
            )
    return findings


def _check_context_receipt(
    stage_name: str,
    receipt: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    connector: Any,
    connector_required: bool,
    prior_readiness: Mapping[str, Any] | None,
) -> list[Finding]:
    inputs = receipt.get("input_artifact_hashes")
    outputs = receipt.get("output_artifact_hashes")
    evidence = receipt.get("evidence_hashes")
    expected_sidecar = _expected_sidecar_hash(
        stage_name, artifacts, prior_readiness,
    )
    findings: list[Finding] = []
    sidecar_hash = outputs.get("validation_sidecar") if isinstance(outputs, Mapping) else None
    if not isinstance(sidecar_hash, str) or sidecar_hash != expected_sidecar:
        findings.append(
            _finding(
                "bom_context_binding_sidecar_unbound",
                f"{stage_name} receipt must bind its validation sidecar output.",
            )
        )
    findings.extend(_check_context_evidence(stage_name, evidence))
    if connector_required:
        findings.extend(_check_context_inputs(stage_name, inputs, artifacts))
    else:
        findings.extend(
            _check_context_reason(stage_name, evidence, connector)
        )
    return findings


def _expected_sidecar_hash(
    stage_name: str,
    artifacts: Mapping[str, Any],
    prior_readiness: Mapping[str, Any] | None,
) -> Any:
    sidecar = artifacts.get("validation_sidecar")
    expected = sidecar.get("sha256") if isinstance(sidecar, Mapping) else None
    if stage_name != "context_binding" or prior_readiness is None:
        return expected
    inputs = prior_readiness.get("input_hashes")
    prior = inputs.get("validation_sidecar") if isinstance(inputs, Mapping) else None
    return prior.get("sha256") if isinstance(prior, Mapping) else None


def _check_context_evidence(stage_name: str, evidence: Any) -> list[Finding]:
    try:
        if not isinstance(evidence, Mapping):
            raise ValueError("missing evidence")
        validate_sha256(
            evidence.get("context_binding"),
            field=f"{stage_name}.context_binding",
        )
        return []
    except ValueError:
        return [
            _finding(
                "bom_context_binding_evidence_missing",
                f"{stage_name} receipt must bind generated Context Binding evidence.",
            )
        ]


def _check_context_inputs(
    stage_name: str,
    inputs: Any,
    artifacts: Mapping[str, Any],
) -> list[Finding]:
    findings: list[Finding] = []
    for label in ("context_request", "context_pack", "context_receipt"):
        row = artifacts.get(label)
        if (
            not isinstance(inputs, Mapping)
            or not isinstance(row, Mapping)
            or inputs.get(label) != row.get("sha256")
        ):
            findings.append(
                _finding(
                    "bom_context_binding_input_unbound",
                    f"{stage_name} receipt must bind {label}.",
                )
            )
    return findings


def _check_context_reason(
    stage_name: str,
    evidence: Any,
    connector: Any,
) -> list[Finding]:
    try:
        expected = normalized_text_sha256(
            connector.get("reason") if isinstance(connector, Mapping) else None,
            field="connector_binding.reason",
        )
    except ValueError:
        expected = None
    if (
        expected is not None
        and isinstance(evidence, Mapping)
        and evidence.get("not_applicable_reason") == expected
    ):
        return []
    return [
        _finding(
            "bom_context_not_applicable_reason_unbound",
            f"{stage_name} receipt must bind the BOM connector not-applicable reason.",
        )
    ]


def _check_optimization_receipt(
    by_stage: Mapping[str, Mapping[str, Any]],
    artifacts: Mapping[str, Any],
    loaded: list[Mapping[str, Any]],
) -> list[Finding]:
    receipt = by_stage.get("optimization")
    if not isinstance(receipt, Mapping):
        return []
    try:
        _validate_optimization_evidence(receipt, artifacts, loaded)
        return []
    except (KeyError, blog_assembly_capabilities.CapabilityRegistryError) as error:
        return [
            _finding(
                "bom_optimizer_evidence_unbound",
                f"Optimization capability evidence is invalid: {error}",
            )
        ]


def _validate_optimization_evidence(
    receipt: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    loaded: list[Mapping[str, Any]],
) -> None:
    execution = artifacts.get("execution_evidence")
    if not isinstance(execution, Mapping):
        raise blog_assembly_capabilities.CapabilityRegistryError(
            "execution evidence is unavailable"
        )
    expected = blog_assembly_capabilities.receipt_definition_hashes(
        loaded, stage="optimization", execution_evidence=execution,
    )
    expected_rows = [
        execution[f"agent_output.{agent_id}"]
        for agent_id in blog_assembly_capabilities.expected_agent_ids(loaded)
    ]
    if artifacts.get("optimizer_outputs") != expected_rows:
        raise blog_assembly_capabilities.CapabilityRegistryError(
            "optimizer outputs do not exactly match distinct agent outputs"
        )
    evidence = receipt.get("evidence_hashes")
    if not isinstance(evidence, Mapping) or any(
        evidence.get(label) != digest for label, digest in expected.items()
    ):
        raise blog_assembly_capabilities.CapabilityRegistryError(
            "optimization receipt does not bind definitions and agent outputs"
        )


def _check_final_article_binding(
    loaded: list[Mapping[str, Any]],
    artifacts: Mapping[str, Any],
) -> list[Finding]:
    article = artifacts.get("article")
    if not loaded or not isinstance(article, Mapping):
        return []
    outputs = loaded[-1].get("output_artifact_hashes")
    if isinstance(outputs, Mapping) and outputs.get("article") == article.get("sha256"):
        return []
    return [
        _finding(
            "bom_final_stage_article_hash_mismatch",
            "Last stage receipt must bind the final article hash.",
        )
    ]


__all__ = [
    "_check_context_receipts",
    "_check_draft_receipt",
    "_check_final_article_binding",
    "_check_optimization_receipt",
    "_check_scrub_receipts",
]
