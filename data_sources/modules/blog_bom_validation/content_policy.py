"""Focused blog assembly BOM validation routines."""

from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from .. import blog_identity_guard, context_binding_guard
from ..blog_assembly.contracts import _visible_faq_questions
from ..blog_assembly.policy import _schema_policy
from ..guard_common import Finding
from .common import _finding
from .dependencies import BomValidationDependencies

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
        "status": "named_author" if named else "no_author",
        "name": author if named else "",
        "frontmatter_author_required": named,
        "schema_person_required": named,
        "named_author_voice_allowed": named,
    }
    findings = []
    legacy_expected = dict(expected)
    if not named:
        legacy_expected["status"] = "not_provided"
    if dict(policy) not in (expected, legacy_expected):
        findings.append(_finding("bom_author_policy_mismatch", "BOM author_policy does not match final article frontmatter."))
    normalized = sidecar_content.casefold()
    token = f"author policy: {policy.get('status')}"
    if token not in normalized:
        findings.append(_finding("bom_author_policy_sidecar_missing", "Validation sidecar must record the exact author policy."))
    return findings


def _check_schema_and_faq(bom: Mapping[str, Any], article: Any) -> list[Finding]:
    try:
        expected = _schema_policy(article)
    except ValueError as exc:
        normalized_error = str(exc).casefold()
        if "itemlist schema metadata" in normalized_error:
            rule_id = "bom_item_list_schema_invalid"
        elif "video embed" in normalized_error:
            rule_id = "bom_video_embed_invalid"
        else:
            rule_id = "bom_faq_structure_unsupported"
        return [_finding(rule_id, str(exc))]
    policy = bom.get("schema_policy")
    findings: list[Finding] = []
    if not isinstance(policy, Mapping):
        return [_finding("bom_schema_policy_missing", "BOM requires schema_policy.")]
    if dict(policy) != expected:
        findings.append(_finding("bom_schema_policy_mismatch", "BOM schema_policy does not match the final article."))
    item_list_active = any(
        str(entity).startswith("ItemList for the ")
        for entity in expected["required_entities"]
    )
    entities_match = (
        Counter(expected["declared_entities"])
        == Counter(expected["required_entities"])
        if item_list_active
        else expected["declared_entities"] == expected["required_entities"]
    )
    if not entities_match:
        findings.append(_finding("bom_schema_entities_mismatch", "Article schema_notes must exactly match visible author, FAQ, and video state."))
    findings.extend(_check_faq_policy(bom.get("faq_policy"), expected["visible_faq"]))
    return findings


def _check_faq_policy(faq_policy: Any, visible: bool) -> list[Finding]:
    findings: list[Finding] = []
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
    editorial_plan: Mapping[str, Any] | None,
    vault_root: str | Path | None,
    dependencies: BomValidationDependencies | None = None,
) -> list[Finding]:
    dependencies = dependencies or BomValidationDependencies()
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
        context_result = dependencies.validate_context_artifacts(
            article.path,
            proof_sidecar=validation_sidecar_path,
            context_request=context_request_path,
            context_pack=context_pack_path,
            context_receipt=context_receipt_path,
            editorial_plan=editorial_plan,
            client=context_client,
            vault_root=vault_root,
        )
    if context_result is None or not context_result.passed:
        findings.append(_finding("bom_context_validation_missing", "Connector-bound BOM requires one passed structured Context Binding result."))
        return findings
    if binding.get("context") != context_result.context_summary():
        findings.append(_finding("bom_context_summary_mismatch", "BOM connector summary does not exactly match validated connector artifacts."))
    return findings
