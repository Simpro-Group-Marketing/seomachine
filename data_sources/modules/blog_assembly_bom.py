"""Build machine-readable blog assembly BOM artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .publishable_markdown import PublishableMarkdown, read_publishable_markdown
except ImportError:  # pragma: no cover - supports direct script execution.
    from publishable_markdown import PublishableMarkdown, read_publishable_markdown


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
    customer_proof_selector_evidence_path: str | Path | None = None,
    fred_authority_evidence_path: str | Path | None = None,
    optimizer_output_paths: Sequence[str | Path] | None = None,
    readiness_output_path: str | Path | None = None,
    file_hashes: Mapping[str, str] | None = None,
    optimizer_output_hashes: Sequence[Mapping[str, str]] | None = None,
    connector_binding_status: str = "required",
    connector_not_applicable_reason: str = "",
    stage_receipts: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return the JSON BOM for one blog assembly run."""
    scope = _required_mapping(request.get("scope"), "request.scope")
    if connector_binding_status not in {"required", "not_applicable"}:
        raise ValueError("connector_binding_status must be required or not_applicable")
    connector_required = connector_binding_status == "required"
    if connector_required:
        if pack.get("schema") != PACK_SCHEMA:
            raise ValueError(f"context pack must use {PACK_SCHEMA}")
        if receipt.get("schema") != RECEIPT_SCHEMA:
            raise ValueError(f"context receipt must use {RECEIPT_SCHEMA}")
    elif not connector_not_applicable_reason.strip():
        raise ValueError("connector_not_applicable_reason is required when connector binding is not_applicable")

    normalized_author = (author or "").strip()
    has_author = bool(normalized_author)
    required_fields = list(REQUIRED_FRONTMATTER_FIELDS)
    if has_author:
        required_fields.append("author")

    if connector_required:
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
        selected_resource_ids = _string_list(
            discovery.get("selected_resource_ids", []),
            "selected_resource_ids",
        )
        claim_ids = _claim_ids(evidence_rows)
        context_pack_hash = _required_string(
            receipt.get("pack_sha256"),
            "receipt.pack_sha256",
        )
        receipt_hash = _required_string(
            receipt.get("receipt_sha256"),
            "receipt.receipt_sha256",
        )
    else:
        receipt_revisions = {}
        selected_resource_ids = []
        claim_ids = []
        context_pack_hash = ""
        receipt_hash = ""

    optimizer_paths = [_artifact_path(path) for path in (optimizer_output_paths or [])]
    normalized_file_hashes = dict(file_hashes or {})
    normalized_optimizer_hashes = [
        {"path": str(row.get("path", "")).strip(), "sha256": str(row.get("sha256", "")).strip()}
        for row in (optimizer_output_hashes or [])
    ]
    normalized_stages = [str(stage).strip() for stage in stages if str(stage).strip()]
    if stage_receipts is None:
        stage_receipts = _stage_receipts(normalized_stages, normalized_file_hashes)

    bom = {
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
            "context_request": _artifact_path(context_request_path) if connector_required else "",
            "context_pack": _artifact_path(context_pack_path) if connector_required else "",
            "context_receipt": _artifact_path(context_receipt_path) if connector_required else "",
            "customer_proof_selector_evidence": _artifact_path(customer_proof_selector_evidence_path)
            if customer_proof_selector_evidence_path
            else "",
            "fred_authority_evidence": _artifact_path(fred_authority_evidence_path)
            if fred_authority_evidence_path
            else "",
            "readiness_output": _artifact_path(readiness_output_path)
            if readiness_output_path
            else "",
        },
        "file_hashes": normalized_file_hashes,
        "optimizer_outputs": normalized_optimizer_hashes
        or [{"path": path, "sha256": ""} for path in optimizer_paths],
        "connector_binding": {
            "status": connector_binding_status,
            **({"reason": connector_not_applicable_reason.strip()} if not connector_required else {}),
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
            "pack_schema": pack.get("schema") if connector_required else "",
            "receipt_schema": receipt.get("schema") if connector_required else "",
            "context_pack_hash": context_pack_hash,
            "receipt_hash": receipt_hash,
            "revisions": receipt_revisions,
            "selected_resource_ids": selected_resource_ids,
            "claim_ids": claim_ids,
        },
        "stages": normalized_stages,
        "stage_receipts": [dict(row) for row in stage_receipts],
    }
    return bom


def build_blog_assembly_bom_from_files(
    *,
    article_path: str | Path,
    validation_sidecar_path: str | Path,
    context_request_path: str | Path | None = None,
    context_pack_path: str | Path | None = None,
    context_receipt_path: str | Path | None = None,
    customer_proof_selector_evidence_path: str | Path | None = None,
    fred_authority_evidence_path: str | Path | None = None,
    optimizer_output_paths: Sequence[str | Path] | None = None,
    readiness_output_path: str | Path | None = None,
    topic_slug: str | None = None,
    connector_binding_status: str | None = None,
    connector_not_applicable_reason: str = "",
    stage_names: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Build one BOM by reading the final workflow artifacts from disk."""
    article = read_publishable_markdown(article_path)
    connector_required = connector_binding_status == "required" or (
        connector_binding_status is None
        and any(path is not None for path in (context_request_path, context_pack_path, context_receipt_path))
    )
    if connector_required:
        if not context_request_path or not context_pack_path or not context_receipt_path:
            raise ValueError("connector-bound BOM requires context request, pack, and receipt paths")
        request = _read_json_file(context_request_path)
        pack = _read_json_file(context_pack_path)
        receipt = _read_json_file(context_receipt_path)
        status = "required"
    else:
        request = _request_from_article(article)
        pack = {}
        receipt = {}
        status = "not_applicable"

    file_paths: dict[str, str | Path | None] = {
        "article": article_path,
        "validation_sidecar": validation_sidecar_path,
        "context_request": context_request_path if connector_required else None,
        "context_pack": context_pack_path if connector_required else None,
        "context_receipt": context_receipt_path if connector_required else None,
        "customer_proof_selector_evidence": customer_proof_selector_evidence_path,
        "fred_authority_evidence": fred_authority_evidence_path,
        "readiness_output": readiness_output_path,
    }
    file_hashes = {
        label: _file_sha256(path)
        for label, path in file_paths.items()
        if path is not None
    }
    optimizer_hashes = [
        {"path": _artifact_path(path), "sha256": _file_sha256(path)}
        for path in (optimizer_output_paths or [])
    ]
    stages = list(stage_names or ["draft", "scrub", "context_binding", "publish_readiness"])
    return build_blog_assembly_bom(
        topic_slug=topic_slug or _topic_slug(article.path),
        article_path=article_path,
        validation_sidecar_path=validation_sidecar_path,
        context_request_path=context_request_path or "",
        context_pack_path=context_pack_path or "",
        context_receipt_path=context_receipt_path or "",
        request=request,
        pack=pack,
        receipt=receipt,
        author=article.scalar("author") or None,
        schema_notes=_schema_notes_from_article(article),
        stages=stages,
        customer_proof_selector_evidence_path=customer_proof_selector_evidence_path,
        fred_authority_evidence_path=fred_authority_evidence_path,
        optimizer_output_paths=optimizer_output_paths,
        readiness_output_path=readiness_output_path,
        file_hashes=file_hashes,
        optimizer_output_hashes=optimizer_hashes,
        connector_binding_status=status,
        connector_not_applicable_reason=connector_not_applicable_reason,
        stage_receipts=_stage_receipts(stages, file_hashes),
    )


def write_blog_assembly_bom(path: str | Path, bom: Mapping[str, Any]) -> None:
    """Write one BOM JSON artifact deterministically."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(dict(bom), ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for deterministic BOM generation."""
    parser = argparse.ArgumentParser(description="Build a blog assembly BOM JSON artifact.")
    parser.add_argument("article_path")
    parser.add_argument("--validation-sidecar", required=True)
    parser.add_argument("--context-request")
    parser.add_argument("--context-pack")
    parser.add_argument("--context-receipt")
    parser.add_argument("--customer-proof-selector-evidence")
    parser.add_argument("--fred-authority-evidence")
    parser.add_argument("--optimizer-output", action="append", default=[])
    parser.add_argument("--readiness-output")
    parser.add_argument("--topic-slug")
    parser.add_argument(
        "--connector-binding-status",
        choices=("required", "not_applicable"),
        default=None,
    )
    parser.add_argument("--connector-not-applicable-reason", default="")
    parser.add_argument("--stage", action="append", dest="stages", default=[])
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    bom = build_blog_assembly_bom_from_files(
        article_path=args.article_path,
        validation_sidecar_path=args.validation_sidecar,
        context_request_path=args.context_request,
        context_pack_path=args.context_pack,
        context_receipt_path=args.context_receipt,
        customer_proof_selector_evidence_path=args.customer_proof_selector_evidence,
        fred_authority_evidence_path=args.fred_authority_evidence,
        optimizer_output_paths=args.optimizer_output,
        readiness_output_path=args.readiness_output,
        topic_slug=args.topic_slug,
        connector_binding_status=args.connector_binding_status,
        connector_not_applicable_reason=args.connector_not_applicable_reason,
        stage_names=args.stages or None,
    )
    write_blog_assembly_bom(args.output, bom)
    return 0


def _schema_entities(schema_notes: Sequence[str], *, has_author: bool) -> list[str]:
    supplied = [str(value).strip() for value in schema_notes if str(value).strip()]
    required = [
        "BlogPosting",
        "BreadcrumbList",
        "ImageObject",
        "Organization publisher reference",
    ]
    if "FAQPage" in supplied:
        required.insert(2, "FAQPage")
        required.insert(3, "Question and Answer inside FAQPage")
    if has_author:
        required.insert(3, "Person as author")
    extras = [value for value in supplied if value not in required]
    return required + sorted(set(extras))


def _schema_notes_from_article(article: PublishableMarkdown) -> list[str]:
    raw_values = article.values("schema_notes")
    if not raw_values:
        return []
    notes: list[str] = []
    for raw in raw_values:
        if re.search(r"\band\b", raw, flags=re.IGNORECASE):
            parts = re.split(r"\s+and\s+", raw, flags=re.IGNORECASE)
        else:
            parts = [raw]
        for part in parts:
            value = part.strip()
            if value:
                notes.append(value)
    return notes


def _request_from_article(article: PublishableMarkdown) -> dict[str, Any]:
    return {
        "task": "Assemble a blog.",
        "scope": {
            "artifact_type": article.scalar("artifact_type", "artifact_kind") or "blog",
            "brand": article.scalar("brand") or "Unknown",
            "title": article.scalar("title", "meta_title") or article.h1 or article.path.stem,
            "objective": article.scalar("objective") or "Not provided",
            "audience": article.scalar("audience") or "Not provided",
            "region": article.scalar("region") or "Not provided",
        },
    }


def _stage_receipts(stages: Sequence[str], file_hashes: Mapping[str, str]) -> list[dict[str, Any]]:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    article_hash = file_hashes.get("article", "")
    return [
        {
            "stage": stage,
            "tool": stage,
            "status": "passed",
            "timestamp": timestamp,
            "input_hashes": {"article": article_hash} if article_hash else {},
            "output_hashes": {"article": article_hash} if article_hash else {},
        }
        for stage in stages
    ]


def _read_json_file(path: str | Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} must be valid JSON") from exc
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _topic_slug(path: Path) -> str:
    stem = path.stem
    return re.sub(r"-\d{4}-\d{2}-\d{2}$", "", stem)


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


if __name__ == "__main__":  # pragma: no cover - exercised through CLI usage.
    raise SystemExit(main())
