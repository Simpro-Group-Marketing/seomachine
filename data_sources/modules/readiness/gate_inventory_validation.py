"""Validate persisted readiness gate inventory against its bound BOM."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .common import (
    context_binding_guard,
    expected_blog_gate_inventory,
    load_json_object_snapshot,
)


def validate_blog_gate_inventory(
    result: Mapping[str, Any],
    *,
    article: Any,
    artifact_kind: str,
    phase: str,
    names: Sequence[str],
    workspace_root: Path,
    resolve_workspace_input: Callable[..., Path],
) -> None:
    if artifact_kind != "blog":
        return
    bom_path = result.get("assembly_bom")
    if not isinstance(bom_path, str):
        raise ValueError("passed blog readiness requires the bound assembly BOM")
    resolved = resolve_workspace_input(
        bom_path,
        workspace_root=workspace_root,
        field="readiness assembly_bom",
    )
    if not resolved.is_file():
        raise ValueError("passed blog readiness requires the bound assembly BOM")
    try:
        bom = load_json_object_snapshot(resolved, field="assembly BOM").payload
    except ValueError as error:
        raise ValueError(f"passed readiness BOM is unavailable: {error}") from error
    if not isinstance(bom, Mapping):
        raise ValueError("passed readiness BOM must be an object")
    expected_lifecycle = "provisional" if phase == "preflight" else "final"
    if bom.get("lifecycle_state") != expected_lifecycle:
        raise ValueError(f"{phase} readiness requires a {expected_lifecycle} assembly BOM")
    schema_policy = bom.get("schema_policy")
    connector_binding = bom.get("connector_binding")
    expected = expected_blog_gate_inventory(
        visible_faq=bool(
            isinstance(schema_policy, Mapping)
            and schema_policy.get("visible_faq") is True
        ),
        connector_required=bool(
            context_binding_guard.requires_context(article.raw)
            or (
                isinstance(connector_binding, Mapping)
                and connector_binding.get("status") == "required"
            )
        ),
        current_strategy=(bom.get("schema") == "simpro-blog-assembly-bom/v4"),
    )
    if list(names) != expected:
        raise ValueError(
            "passed readiness result does not contain the expected gate inventory"
        )
