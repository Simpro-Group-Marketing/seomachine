"""Build machine-readable blog assembly BOM artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence


BOM_SCHEMA = "simpro-blog-assembly-bom/v1"
PACK_SCHEMA = "simpro-product-context-pack/v2"
RECEIPT_SCHEMA = "simpro-context-receipt/v1"
REQUIRED_FRONTMATTER_FIELDS = (
    "artifact_type",
    "brand",
    "title",
    "objective",
    "audience",
    "region",
    "schema_notes",
)


def build_blog_assembly_bom(
    *,
    topic_slug: str,
    article_path: str | Path,
    validation_sidecar_path: str | Path,
    context_request_path: str | Path,
    context_pack_path: str | Path,
    context_receipt_path: str | Path,
    request: Mapping[str, Any],
    pack: Mapping[str, Any],
    receipt: Mapping[str, Any],
    author: str | None,
    schema_notes: Sequence[str],
    stages: Sequence[str],
) -> dict[str, Any]:
    """Return the JSON BOM for one blog assembly run."""
    scope = _required_mapping(request.get("scope"), "request.scope")
    if pack.get("schema") != PACK_SCHEMA:
        raise ValueError(f"context pack must use {PACK_SCHEMA}")
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise ValueError(f"context receipt must use {RECEIPT_SCHEMA}")

    normalized_author = (author or "").strip()
    has_author = bool(normalized_author)
    required_fields = list(REQUIRED_FRONTMATTER_FIELDS)
    if has_author:
        required_fields.append("author")

    sections = _required_mapping(pack.get("sections"), "pack.sections")
    discovery = _required_mapping(
        sections.get("Discovery Trace"),
        "pack.sections.Discovery Trace",
    )
    evidence_rows = _list_of_mappings(
        sections.get("Approved Claim Evidence", []),
        "pack.sections.Approved Claim Evidence",
    )
    pack_revisions = dict(_required_mapping(pack.get("revisions"), "pack.revisions"))
    receipt_revisions = dict(
        _required_mapping(receipt.get("revisions"), "receipt.revisions")
    )
    if pack_revisions != receipt_revisions:
        raise ValueError("context pack and receipt revisions must match")

    return {
        "schema": BOM_SCHEMA,
        "identity": {
            "topic_slug": _required_string(topic_slug, "topic_slug"),
            "artifact_type": _required_string(
                scope.get("artifact_type"),
                "request.scope.artifact_type",
            ),
            "brand": _required_string(scope.get("brand"), "request.scope.brand"),
            "title": _required_string(scope.get("title"), "request.scope.title"),
            "objective": _required_string(
                scope.get("objective"),
                "request.scope.objective",
            ),
            "audience": _required_string(
                scope.get("audience"),
                "request.scope.audience",
            ),
            "region": _required_string(scope.get("region"), "request.scope.region"),
        },
        "files": {
            "article": _artifact_path(article_path),
            "validation_sidecar": _artifact_path(validation_sidecar_path),
            "context_request": _artifact_path(context_request_path),
            "context_pack": _artifact_path(context_pack_path),
            "context_receipt": _artifact_path(context_receipt_path),
        },
        "frontmatter": {
            "required_fields": required_fields,
            "optional_fields": [] if has_author else ["author"],
        },
        "author_policy": {
            "status": "named_author" if has_author else "not_provided",
            "name": normalized_author if has_author else "",
            "frontmatter_author_required": has_author,
            "schema_person_required": has_author,
            "named_author_voice_allowed": has_author,
        },
        "schema_notes": {
            "required_entities": _schema_entities(
                schema_notes,
                has_author=has_author,
            ),
            "video_object_required": _contains_token(schema_notes, "VideoObject"),
        },
        "context": {
            "pack_schema": pack.get("schema"),
            "receipt_schema": receipt.get("schema"),
            "context_pack_hash": _required_string(
                receipt.get("pack_sha256"),
                "receipt.pack_sha256",
            ),
            "receipt_hash": _required_string(
                receipt.get("receipt_sha256"),
                "receipt.receipt_sha256",
            ),
            "revisions": receipt_revisions,
            "selected_resource_ids": _string_list(
                discovery.get("selected_resource_ids", []),
                "selected_resource_ids",
            ),
            "claim_ids": _claim_ids(evidence_rows),
        },
        "stages": [str(stage).strip() for stage in stages if str(stage).strip()],
    }


def write_blog_assembly_bom(path: str | Path, bom: Mapping[str, Any]) -> None:
    """Write one BOM JSON artifact deterministically."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(dict(bom), ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _schema_entities(schema_notes: Sequence[str], *, has_author: bool) -> list[str]:
    supplied = [str(value).strip() for value in schema_notes if str(value).strip()]
    required = [
        "BlogPosting",
        "BreadcrumbList",
        "FAQPage",
        "ImageObject",
        "Organization publisher reference",
    ]
    if has_author:
        required.insert(3, "Person as author")
    extras = [value for value in supplied if value not in required]
    return required + sorted(set(extras))


def _claim_ids(evidence_rows: Sequence[Mapping[str, Any]]) -> list[str]:
    claim_ids: list[str] = []
    for row in evidence_rows:
        claim_id = row.get("claim_id")
        if isinstance(claim_id, str):
            normalized = claim_id.strip()
            if normalized and normalized not in claim_ids:
                claim_ids.append(normalized)
    return claim_ids


def _artifact_path(value: str | Path) -> str:
    return Path(value).as_posix()


def _required_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _list_of_mappings(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(row, Mapping) for row in value):
        raise ValueError(f"{label} must be a list of objects")
    return value


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{label} must be a list of strings")
    return [item.strip() for item in value if item.strip()]


def _required_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _contains_token(values: Sequence[str], token: str) -> bool:
    return any(str(value).strip().casefold() == token.casefold() for value in values)
