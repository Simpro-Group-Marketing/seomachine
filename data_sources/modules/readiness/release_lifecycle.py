"""Shared artifact-kind rules for final readiness and authorization."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ArtifactReleasePolicy:
    artifact_kind: str
    requires_final_bom: bool


_POLICIES = {
    "blog": ArtifactReleasePolicy("blog", True),
    "landing_page": ArtifactReleasePolicy("landing_page", False),
}


def artifact_release_policy(artifact_kind: Any) -> ArtifactReleasePolicy:
    try:
        return _POLICIES[artifact_kind]
    except (KeyError, TypeError) as error:
        raise ValueError("final readiness artifact_kind is invalid") from error


def validate_final_bom_binding(
    result: Mapping[str, Any],
    inventory: Mapping[str, Any],
) -> None:
    """Enforce the one final-BOM contract for every release boundary."""
    policy = artifact_release_policy(result.get("artifact_kind"))
    bom_path = result.get("assembly_bom")
    bom_row = inventory.get("assembly_bom")
    bom_digest = result.get("final_bom_sha256")
    if policy.requires_final_bom:
        if not isinstance(bom_path, str) or not bom_path:
            raise ValueError("final blog readiness requires a final assembly BOM")
        if not isinstance(bom_row, Mapping):
            raise ValueError("final blog readiness requires a final assembly BOM input")
        if bom_digest != bom_row.get("sha256"):
            raise ValueError("final readiness must bind the exact final BOM hash")
        return
    if bom_path is not None or bom_row is not None or "final_bom_sha256" in result:
        raise ValueError("landing-page final readiness must not contain a blog assembly BOM")


__all__ = [
    "ArtifactReleasePolicy",
    "artifact_release_policy",
    "validate_final_bom_binding",
]
