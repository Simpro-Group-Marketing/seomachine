"""Adapters from immutable readiness content to existing content-level guards."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import partial
from pathlib import Path
from typing import Any, Callable, Mapping

from ..vault_claim_receipts import ValidatedClaimSet
from .artifact_views import thaw_value
from .inputs import ReadinessInputs


@dataclass(frozen=True, slots=True)
class ContentGateInputs:
    article_content: str
    proof_content: str | None
    article_path: Path
    proof_sidecar_path: str | None
    context_pack_path: str | None
    context_receipt_path: str | None
    vault_root: str | Path | None
    captured: ReadinessInputs
    validated_claim_set: ValidatedClaimSet | None
    transport: Any | None
    normalize_source: Callable[[str, Callable[[], Any]], Any] | None = None
    registry_state: object | None = None


def run_content_gate(
    name: str,
    guard_module: Any,
    inputs: ContentGateInputs,
) -> list[dict[str, Any]]:
    """Run one article gate through its content adapter."""
    return _ADAPTERS[name](guard_module, inputs)


def _metric(module: Any, value: ContentGateInputs) -> list[dict[str, Any]]:
    return module.check_content(
        value.article_content,
        source_path=str(value.article_path),
        proof_content=value.proof_content,
        fetcher=(
            lambda url: module.fetch_source_text(url, transport=value.transport)
        )
        if value.transport is not None
        else None,
    )


def _numeric(module: Any, value: ContentGateInputs) -> list[dict[str, Any]]:
    return module.check_content(value.article_content, proof_content=value.proof_content)


def _faq_answer(module: Any, value: ContentGateInputs) -> list[dict[str, Any]]:
    return module.check_content(value.article_content)


def _faq_proof(module: Any, value: ContentGateInputs) -> list[dict[str, Any]]:
    return module.check_content(
        value.article_content,
        proof_content=value.proof_content,
        base_path=value.article_path.parent,
        registry_state=value.registry_state,
    )


def _competitive(module: Any, value: ContentGateInputs) -> list[dict[str, Any]]:
    return module.check_content(
        value.article_content,
        proof_content=value.proof_content,
        context_pack=_json(value.captured, "context_pack"),
        context_receipt=_json(value.captured, "context_receipt"),
        vault_root=value.vault_root,
        validated_claim_set=value.validated_claim_set,
    )


def _proof_only(module: Any, value: ContentGateInputs) -> list[dict[str, Any]]:
    return module.check_content(value.article_content, proof_content=value.proof_content)


def _source_support(module: Any, value: ContentGateInputs) -> list[dict[str, Any]]:
    fetch_many = (
        partial(
            module.fetch_source_text_many,
            transport=value.transport,
            normalize=value.normalize_source,
        )
        if value.transport is not None
        and callable(getattr(value.transport, "request_many", None))
        else None
    )
    return module.check_content(
        value.article_content,
        base_path=value.article_path,
        proof_content=value.proof_content,
        registry_state=value.registry_state,
        fetcher=(
            lambda url: module.fetch_source_text(url, transport=value.transport)
        )
        if value.transport is not None
        else None,
        fetch_many=fetch_many,
    )


def _source_quality(module: Any, value: ContentGateInputs) -> list[dict[str, Any]]:
    return module.check_content(
        value.article_content,
        proof_content=value.proof_content or "",
        today=date.today(),
    )


def _customer_proof(module: Any, value: ContentGateInputs) -> list[dict[str, Any]]:
    return module.check_content(
        value.article_content,
        proof_content=value.proof_content,
        proof_sidecar_path=value.proof_sidecar_path,
        source_path=value.article_path,
        context_pack=value.context_pack_path,
        context_receipt=value.context_receipt_path,
        ledger_payload=_json(value.captured, "customer_proof_usage_ledger"),
        validated_claim_set=value.validated_claim_set,
    )


def _review_story(module: Any, value: ContentGateInputs) -> list[dict[str, Any]]:
    return module.check_content(
        value.article_content,
        proof_content=value.proof_content,
        proof_sidecar_path=value.proof_sidecar_path,
        source_path=value.article_path,
    )


def _context_boundary(module: Any, value: ContentGateInputs) -> list[dict[str, Any]]:
    return module.check_content(
        value.article_content,
        proof_content=value.proof_content,
        source_path=value.article_path,
        workspace_root=value.captured.workspace_root,
    )


def _eeat_strength(module: Any, value: ContentGateInputs) -> list[dict[str, Any]]:
    return module.check_content(
        value.article_content,
        proof_content=value.proof_content,
        # Landing pages bind no editorial plan, selector evidence, or Fred evidence.
        editorial_plan=None,
        customer_proof_evidence=None,
        fred_authority_content=None,
    )


def _vault_language(module: Any, value: ContentGateInputs) -> list[dict[str, Any]]:
    return module.check_content(
        value.article_content,
        proof_content=value.proof_content,
        context_pack=_json(value.captured, "context_pack"),
        context_receipt=_json(value.captured, "context_receipt"),
    )


def _named_feature(module: Any, value: ContentGateInputs) -> list[dict[str, Any]]:
    return module.check_content(
        value.article_content,
        proof_content=value.proof_content,
        vault_root=value.vault_root,
        context_pack=_json(value.captured, "context_pack"),
        context_receipt=value.context_receipt_path,
        validated_claim_set=value.validated_claim_set,
    )


def _fred(module: Any, value: ContentGateInputs) -> list[dict[str, Any]]:
    return module.check_content(
        value.article_content,
        proof_content=value.proof_content,
        vault_root=value.vault_root,
        context_pack=value.context_pack_path,
        context_receipt=value.context_receipt_path,
        validated_claim_set=value.validated_claim_set,
    )


def _json(inputs: ReadinessInputs, label: str) -> Mapping[str, Any] | None:
    snapshot = inputs.optional_snapshot(label)
    value = None if snapshot is None else thaw_value(inputs.json_object(label))
    return value if isinstance(value, Mapping) else None


_ADAPTERS: dict[str, Callable[[Any, ContentGateInputs], list[dict[str, Any]]]] = {
    "context_boundary": _context_boundary,
    "metric_proof_pack": _metric,
    "numeric_claim_source": _numeric,
    "faq_answer_quality": _faq_answer,
    "faq_proof": _faq_proof,
    "competitive_shortlist": _competitive,
    "hindsight_boundary": _proof_only,
    "source_support": _source_support,
    "source_quality": _source_quality,
    "customer_proof_diversity": _customer_proof,
    "review_story_identity": _review_story,
    "eeat_strength": _eeat_strength,
    "early_artifact": _proof_only,
    "answer_withholding": _proof_only,
    "vault_brand_language": _vault_language,
    "named_feature_status": _named_feature,
    "fred_authority": _fred,
}

CONTENT_GATE_NAMES = frozenset(_ADAPTERS)
