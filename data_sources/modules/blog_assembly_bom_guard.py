"""Validate machine-readable blog assembly BOM artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

try:
    from .blog_assembly_bom import BOM_SCHEMA
except ImportError:  # pragma: no cover - supports direct script execution.
    from blog_assembly_bom import BOM_SCHEMA


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
        )
    )
    findings.extend(_check_author_policy(bom))
    findings.extend(_check_stages(bom.get("stages")))
    return findings


def _check_files(value: Any, expected: Mapping[str, str | Path]) -> list[Finding]:
    if not isinstance(value, Mapping):
        return [_finding("bom_files_missing", "Blog assembly BOM requires files.")]
    findings: list[Finding] = []
    for field, expected_path in expected.items():
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


def _check_author_policy(bom: Mapping[str, Any]) -> list[Finding]:
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

    entities = _schema_entities(bom)
    has_person = "Person as author" in entities
    if status == "named_author" and not has_person:
        return [
            _finding(
                "bom_person_author_missing",
                "Named-author BOM requires Person as author schema notes.",
            )
        ]
    if status == "not_provided" and has_person:
        return [
            _finding(
                "bom_person_author_without_author",
                "BOM cannot require Person as author when no named author exists.",
            )
        ]
    return []


def _check_stages(value: Any) -> list[Finding]:
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


def _finding(rule_id: str, message: str) -> Finding:
    return {
        "severity": "error",
        "rule_id": rule_id,
        "message": message,
        "suggestion": "Regenerate the blog assembly BOM from current workflow artifacts.",
    }
