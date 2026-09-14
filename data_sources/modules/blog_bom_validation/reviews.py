"""Machine-review integration for BOM validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .. import machine_review
from ..blog_assembly_bom import BOM_SCHEMA_V1, BOM_SCHEMA_V2, BOM_SCHEMA_V3
from ..blog_assembly_contract import resolve_artifact, verify_artifact
from ..guard_common import Finding
from .artifacts import _verify_row, _is_workspace_file
from .common import _finding
from .dependencies import BomValidationDependencies
from . import review_validation as blog_assembly_bom_reviews
from . import snapshot_adapters as blog_assembly_bom_snapshot


def _check_machine_reviews(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
    *,
    proof_sidecar_path: str | Path | None,
    captured: Any = None,
    dependencies: BomValidationDependencies | None = None,
) -> list[Finding]:
    dependencies = dependencies or BomValidationDependencies()
    bound = dependencies.bind(
        BOM_SCHEMA_V1=BOM_SCHEMA_V1,
        BOM_SCHEMA_V2=BOM_SCHEMA_V2,
        BOM_SCHEMA_V3=BOM_SCHEMA_V3,
        _finding=_finding,
        _is_workspace_file=_is_workspace_file,
        _verify_row=_verify_row,
        blog_assembly_bom_snapshot=blog_assembly_bom_snapshot,
        machine_review=machine_review,
        resolve_artifact=resolve_artifact,
        verify_artifact=verify_artifact,
    )
    return blog_assembly_bom_reviews.check_machine_reviews(
        bound,
        bom,
        artifacts,
        root,
        proof_sidecar_path=proof_sidecar_path,
        captured=captured,
    )


__all__ = ["_check_machine_reviews"]
