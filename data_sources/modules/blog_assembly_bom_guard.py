"""Validate machine-readable blog assembly BOM artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

try:
    from .blog_assembly_bom import BOM_SCHEMA
    from .publishable_markdown import FrontmatterError, read_publishable_markdown
except ImportError:  # pragma: no cover - supports direct script execution.
    from blog_assembly_bom import BOM_SCHEMA
    from publishable_markdown import FrontmatterError, read_publishable_markdown


Finding = dict[str, Any]
REQUIRED_STAGE_ORDER = (
    "draft",
    "scrub",
    "context_binding",
    "publish_readiness",
)
OPTIMIZATION_STAGES = frozenset(
    {
        "optimization",
        "optimize",
        "content_analyzer",
        "seo_optimizer",
        "meta_creator",
        "internal_linker",
        "keyword_mapper",
    }
)
POST_OPTIMIZATION_REQUIRED = (
    "post_optimization_scrub",
    "post_optimization_context_binding",
    "final_publish_readiness",
)
FORBIDDEN_TOPOLOGY_PATTERNS = (
    "obsidian/simpro brand context/",
    "wi" + "ki/",
    "authority_root",
    "simpro_vault_root",
)


def check_bom_file(
    path: str | Path,
    *,
    article_path: str | Path,
    validation_sidecar_path: str | Path,
    context_request_path: str | Path,
    context_pack_path: str | Path,
    context_receipt_path: str | Path,
) -> list[Finding]:
    """Read and validate one blog assembly BOM JSON file."""
    try:
        bom = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [_finding("bom_invalid", f"Blog assembly BOM is invalid: {error}")]
    if not isinstance(bom, Mapping):
        return [_finding("bom_invalid", "Blog assembly BOM must be a JSON object.")]
    return check_bom(
        bom,
        article_path=article_path,
        validation_sidecar_path=validation_sidecar_path,
        context_request_path=context_request_path,
        context_pack_path=context_pack_path,
        context_receipt_path=context_receipt_path,
    )


def missing_bom_finding() -> Finding:
    """Return the stable blocking finding for a required missing BOM."""
    return _finding("bom_missing", "Blog artifacts require --assembly-bom.")


def check_bom(
    bom: Mapping[str, Any],
    *,
    article_path: str | Path,
    validation_sidecar_path: str | Path,
    context_request_path: str | Path,
    context_pack_path: str | Path,
    context_receipt_path: str | Path,
) -> list[Finding]:
    """Return blocking findings for one blog assembly BOM object."""
    findings: list[Finding] = []
    if bom.get("schema") != BOM_SCHEMA:
        findings.append(
            _finding(
                "bom_schema_invalid",
                f"Blog assembly BOM must use {BOM_SCHEMA}.",
            )
        )

    findings.extend(_check_topology(bom))
    findings.extend(
        _check_files(
            bom.get("files"),
            {
                "article": article_path,
                "validation_sidecar": validation_sidecar_path,
                "context_request": context_request_path,
                "context_pack": context_pack_path,
                "context_receipt": context_receipt_path,
            },
            connector_required=_connector_required(bom),
        )
    )
    findings.extend(_check_file_hashes(bom))
    findings.extend(_check_optimizer_outputs(bom))
    findings.extend(_check_connector_binding(bom))
    article_content = ""
    article_metadata: Mapping[str, Any] = {}
    sidecar_content = ""
    try:
        article = read_publishable_markdown(article_path)
        article_content = article.raw
        article_metadata = article.metadata
    except (OSError, UnicodeError, FrontmatterError) as error:
        findings.append(_finding("bom_article_unreadable", f"Blog article cannot be read for BOM validation: {error}"))
    try:
        sidecar_content = Path(validation_sidecar_path).read_text(encoding="utf-8") if str(validation_sidecar_path) else ""
    except (OSError, UnicodeError) as error:
        findings.append(_finding("bom_sidecar_unreadable", f"Validation sidecar cannot be read for BOM validation: {error}"))
    findings.extend(
        _check_author_policy(
            bom,
            article_metadata=article_metadata,
            sidecar_content=sidecar_content,
        )
    )
    findings.extend(_check_schema_policy(bom, article_content))
    findings.extend(_check_stages(bom.get("stages"), bom.get("stage_receipts"), bom))
    return findings


def _check_files(
    value: Any,
    expected: Mapping[str, str | Path],
    *,
    connector_required: bool,
) -> list[Finding]:
    if not isinstance(value, Mapping):
        return [_finding("bom_files_missing", "Blog assembly BOM requires files.")]
    findings: list[Finding] = []
    for field, expected_path in expected.items():
        if field in {"context_request", "context_pack", "context_receipt"} and not connector_required:
            continue
        actual = value.get(field)
        if not isinstance(actual, str) or not actual.strip():
            findings.append(
                _finding(
                    f"bom_{field}_missing",
                    f"Blog assembly BOM is missing files.{field}.",
                )
            )
            continue
        if _normalize_path(actual) != _normalize_path(expected_path):
            findings.append(
                _finding(
                    f"bom_{field}_mismatch",
                    f"Blog assembly BOM files.{field} does not match workflow input.",
                )
            )
    return findings


def _check_file_hashes(bom: Mapping[str, Any]) -> list[Finding]:
    files = bom.get("files")
    hashes = bom.get("file_hashes")
    if not isinstance(files, Mapping):
        return []
    if not isinstance(hashes, Mapping):
        return [_finding("bom_file_hashes_missing", "Blog assembly BOM requires file_hashes.")]
    findings: list[Finding] = []
    for field, actual_path in files.items():
        if field in {"context_request", "context_pack", "context_receipt"} and not _connector_required(bom):
            continue
        if not isinstance(actual_path, str) or not actual_path.strip():
            continue
        expected_hash = hashes.get(field)
        if not isinstance(expected_hash, str) or not expected_hash.strip():
            findings.append(_finding(f"bom_{field}_hash_missing", f"Blog assembly BOM is missing file_hashes.{field}."))
            continue
        try:
            current_hash = _file_sha256(actual_path)
        except OSError:
            findings.append(_finding(f"bom_{field}_unavailable", f"Blog assembly BOM file is unavailable: files.{field}."))
            continue
        if current_hash != expected_hash:
            findings.append(_finding(f"bom_{field}_hash_mismatch", f"Blog assembly BOM hash for files.{field} does not match current file contents."))
    return findings


def _check_optimizer_outputs(bom: Mapping[str, Any]) -> list[Finding]:
    outputs = bom.get("optimizer_outputs", [])
    if outputs in (None, []):
        return []
    if not isinstance(outputs, list) or not all(isinstance(row, Mapping) for row in outputs):
        return [_finding("bom_optimizer_outputs_invalid", "Blog assembly BOM optimizer_outputs must be a list of path/hash objects.")]
    findings: list[Finding] = []
    for index, row in enumerate(outputs):
        path = row.get("path")
        expected_hash = row.get("sha256")
        if not isinstance(path, str) or not path.strip():
            findings.append(_finding("bom_optimizer_output_path_missing", f"Optimizer output {index} is missing a path."))
            continue
        if not isinstance(expected_hash, str) or not expected_hash.strip():
            findings.append(_finding("bom_optimizer_output_hash_missing", f"Optimizer output {path} is missing a SHA-256 hash."))
            continue
        try:
            current_hash = _file_sha256(path)
        except OSError:
            findings.append(_finding("bom_optimizer_output_unavailable", f"Optimizer output is unavailable: {path}."))
            continue
        if current_hash != expected_hash:
            findings.append(_finding("bom_optimizer_output_hash_mismatch", f"Optimizer output hash does not match current file contents: {path}."))
    return findings


def _check_connector_binding(bom: Mapping[str, Any]) -> list[Finding]:
    binding = bom.get("connector_binding")
    if not isinstance(binding, Mapping):
        return [_finding("bom_connector_binding_missing", "Blog assembly BOM requires connector_binding.")]
    status = binding.get("status")
    if status not in {"required", "not_applicable"}:
        return [_finding("bom_connector_binding_invalid", "connector_binding.status must be required or not_applicable.")]
    if status == "not_applicable" and not str(binding.get("reason") or "").strip():
        return [_finding("bom_connector_not_applicable_reason_missing", "Non-connector blog BOMs require connector_binding.reason.")]
    if status == "required":
        context = bom.get("context")
        if not isinstance(context, Mapping):
            return [_finding("bom_context_missing", "Connector-bound BOM requires context.")]
        findings: list[Finding] = []
        if context.get("pack_schema") != "simpro-product-context-pack/v2":
            findings.append(_finding("bom_context_pack_schema_invalid", "Connector-bound BOM requires simpro-product-context-pack/v2."))
        if context.get("receipt_schema") != "simpro-context-receipt/v1":
            findings.append(_finding("bom_context_receipt_schema_invalid", "Connector-bound BOM requires simpro-context-receipt/v1."))
        if not isinstance(context.get("context_pack_hash"), str) or not context.get("context_pack_hash"):
            findings.append(_finding("bom_context_pack_hash_missing", "Connector-bound BOM requires context.context_pack_hash."))
        if not isinstance(context.get("receipt_hash"), str) or not context.get("receipt_hash"):
            findings.append(_finding("bom_context_receipt_hash_missing", "Connector-bound BOM requires context.receipt_hash."))
        return findings
    return []


def _check_author_policy(
    bom: Mapping[str, Any],
    *,
    article_metadata: Mapping[str, Any],
    sidecar_content: str,
) -> list[Finding]:
    author_policy = bom.get("author_policy")
    if not isinstance(author_policy, Mapping):
        return [
            _finding(
                "bom_author_policy_missing",
                "Blog assembly BOM requires author_policy.",
            )
        ]

    status = author_policy.get("status")
    if status not in {"named_author", "not_provided"}:
        return [
            _finding(
                "bom_author_policy_invalid",
                "Blog assembly BOM author_policy.status must be named_author or not_provided.",
            )
        ]
    expected_contract = {
        "frontmatter_author_required": status == "named_author",
        "schema_person_required": status == "named_author",
        "named_author_voice_allowed": status == "named_author",
    }
    findings: list[Finding] = []
    for key, expected in expected_contract.items():
        if author_policy.get(key) is not expected:
            findings.append(
                _finding(
                    f"bom_author_policy_{key}_invalid",
                    f"Blog assembly BOM author_policy.{key} must be {expected}.",
                )
            )

    entities = _schema_entities(bom)
    has_person = "Person as author" in entities
    if status == "named_author" and not has_person:
        findings.append(
            _finding(
                "bom_person_author_missing",
                "Named-author BOM requires Person as author schema notes.",
            )
        )
    if status == "not_provided" and has_person:
        findings.append(
            _finding(
                "bom_person_author_without_author",
                "BOM cannot require Person as author when no named author exists.",
            )
        )
    article_author = _metadata_scalar(article_metadata, "author")
    policy_name = str(author_policy.get("name") or "").strip()
    if status == "named_author":
        if not article_author:
            findings.append(_finding("bom_named_author_frontmatter_missing", "Named-author BOM requires author in article frontmatter."))
        elif policy_name and article_author != policy_name:
            findings.append(_finding("bom_named_author_frontmatter_mismatch", "Named-author BOM author_policy.name must match article frontmatter author."))
        sidecar_normalized = sidecar_content.casefold()
        if "author policy: named_author" not in sidecar_normalized and (not policy_name or policy_name.casefold() not in sidecar_normalized):
            findings.append(_finding("bom_named_author_sidecar_missing", "Named-author decision must be recorded in the validation sidecar."))
    else:
        if article_author:
            findings.append(_finding("bom_unexpected_author_frontmatter", "No-author BOM must omit author from article frontmatter."))
        sidecar_normalized = sidecar_content.casefold()
        if not any(token in sidecar_normalized for token in ("author policy: not_provided", "no named author", "no-author")):
            findings.append(_finding("bom_no_author_sidecar_missing", "No-author decision must be recorded in the validation sidecar."))
    return findings


def _check_schema_policy(bom: Mapping[str, Any], article_content: str) -> list[Finding]:
    entities = _schema_entities(bom)
    findings: list[Finding] = []
    has_visible_faq = _has_visible_faq(article_content)
    has_faqpage = "FAQPage" in entities
    if has_visible_faq and not has_faqpage:
        findings.append(_finding("bom_faqpage_missing", "Visible FAQ content requires FAQPage in schema notes."))
    if not has_visible_faq and has_faqpage:
        findings.append(_finding("bom_faqpage_without_visible_faq", "FAQPage must be omitted when no visible FAQ exists."))
    if has_faqpage and "Question and Answer inside FAQPage" not in entities:
        findings.append(_finding("bom_faq_question_answer_missing", "FAQPage requires Question and Answer inside FAQPage."))
    has_video_embed = _has_video_embed(article_content)
    has_video_object = "VideoObject" in entities
    if has_video_embed and not has_video_object:
        findings.append(_finding("bom_video_object_missing", "Embedded video requires VideoObject in schema notes."))
    if not has_video_embed and has_video_object:
        findings.append(_finding("bom_video_object_without_embed", "VideoObject must be omitted when no video is embedded."))
    return findings


def _check_stages(value: Any, receipts: Any, bom: Mapping[str, Any]) -> list[Finding]:
    if not isinstance(value, list) or not all(isinstance(stage, str) for stage in value):
        return [
            _finding(
                "bom_stages_invalid",
                "Blog assembly BOM requires a string stage list.",
            )
        ]
    stages = [stage for stage in value if stage]
    findings: list[Finding] = []
    if not _contains_ordered(stages, REQUIRED_STAGE_ORDER):
        findings.append(
            _finding(
                "bom_stage_order_invalid",
                "Blog assembly BOM must record draft, scrub, context_binding, and publish_readiness in order.",
            )
        )
    if OPTIMIZATION_STAGES.intersection(stages) and not _contains_ordered(
        stages,
        POST_OPTIMIZATION_REQUIRED,
    ):
        findings.append(
            _finding(
                "bom_post_optimization_revalidation_missing",
                "Optimization mutations require post_optimization_scrub, post_optimization_context_binding, and final_publish_readiness stages.",
            )
        )
    if not isinstance(receipts, list) or not all(isinstance(row, Mapping) for row in receipts):
        findings.append(_finding("bom_stage_receipts_missing", "Blog assembly BOM requires machine-readable stage_receipts."))
        return findings
    receipt_stages = [str(row.get("stage") or "").strip() for row in receipts]
    if receipt_stages != stages:
        findings.append(_finding("bom_stage_receipts_mismatch", "BOM stage_receipts must match stages exactly."))
    timestamps = [str(row.get("timestamp") or "").strip() for row in receipts]
    if any(not timestamp for timestamp in timestamps) or timestamps != sorted(timestamps):
        findings.append(_finding("bom_stage_receipts_not_monotonic", "BOM stage_receipts timestamps must be present and monotonic."))
    article_hash = ""
    hashes = bom.get("file_hashes")
    if isinstance(hashes, Mapping) and isinstance(hashes.get("article"), str):
        article_hash = hashes["article"]
    for row in receipts:
        if row.get("stage") in {"final_publish_readiness", "publish_readiness"}:
            output_hashes = row.get("output_hashes")
            if not isinstance(output_hashes, Mapping) or output_hashes.get("article") != article_hash:
                findings.append(_finding("bom_readiness_stage_article_hash_missing", "Readiness stage receipts must record the final article hash."))
    return findings


def _check_topology(value: Any) -> list[Finding]:
    for text in _iter_strings(value):
        normalized = text.replace("\\", "/").casefold()
        if any(pattern in normalized for pattern in FORBIDDEN_TOPOLOGY_PATTERNS):
            return [
                _finding(
                    "bom_hard_coded_vault_topology",
                    "Blog assembly BOM must use connector IDs and workflow artifact paths, not hard-coded vault topology.",
                )
            ]
    return []


def _schema_entities(bom: Mapping[str, Any]) -> set[str]:
    schema_notes = bom.get("schema_notes")
    if not isinstance(schema_notes, Mapping):
        return set()
    entities = schema_notes.get("required_entities")
    if not isinstance(entities, list):
        return set()
    return {entity for entity in entities if isinstance(entity, str)}


def _iter_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for key, item in value.items():
            yield from _iter_strings(key)
            yield from _iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)


def _contains_ordered(values: list[str], required: tuple[str, ...]) -> bool:
    cursor = 0
    for value in values:
        if cursor < len(required) and value == required[cursor]:
            cursor += 1
    return cursor == len(required)


def _normalize_path(value: str | Path) -> str:
    return str(value).replace("\\", "/").strip().rstrip("/")


def _connector_required(bom: Mapping[str, Any]) -> bool:
    binding = bom.get("connector_binding")
    return isinstance(binding, Mapping) and binding.get("status") == "required"


def _metadata_scalar(metadata: Mapping[str, Any], key: str) -> str:
    value = metadata.get(key)
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def _file_sha256(path: str | Path) -> str:
    import hashlib

    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _has_visible_faq(content: str) -> bool:
    return bool(
        re.search(r"^#{2,4}\s+(?:frequently asked questions|faqs?)\b", content, re.IGNORECASE | re.MULTILINE)
        or re.search(r"^#{3,5}\s+[^?\n]+\?\s*$", content, re.MULTILINE)
    )


def _has_video_embed(content: str) -> bool:
    return bool(re.search(r"<iframe[^>]+(?:youtube(?:-nocookie)?\.com/embed|vimeo\.com/video)", content, re.IGNORECASE))


def _finding(rule_id: str, message: str) -> Finding:
    return {
        "severity": "error",
        "rule_id": rule_id,
        "message": message,
        "suggestion": "Regenerate the blog assembly BOM from current workflow artifacts.",
    }
