"""Strict optimizer evidence parsing and current-release authorization."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .blog_assembly_contract import (
        file_sha256,
        load_json_object_snapshot,
        resolve_artifact,
        validate_sha256,
    )
except ImportError:  # pragma: no cover - supports direct script execution.
    from blog_assembly_contract import (
        file_sha256,
        load_json_object_snapshot,
        resolve_artifact,
        validate_sha256,
    )


V1_SCHEMA = "simpro-optimizer-output/v1"
V2_SCHEMA = "simpro-optimizer-output/v2"
REQUIRED_BINDINGS = (
    "article",
    "editorial_plan",
    "proof_sidecar",
    "scorecard",
    "prior_preflight_readiness",
)


class OptimizerEvidenceError(RuntimeError):
    """A stable, machine-readable optimizer authorization failure."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True, slots=True)
class OptimizerOutput:
    """One history-readable optimizer output artifact."""

    path: Path
    schema: str
    payload: dict[str, Any]


def read_optimizer_output(path: str | Path) -> OptimizerOutput:
    """Parse a V1 or V2 optimizer artifact without authorizing its use."""
    try:
        snapshot = load_json_object_snapshot(path, field="optimizer_output")
    except ValueError as error:
        raise OptimizerEvidenceError("optimizer_output_invalid", str(error)) from error
    schema = snapshot.payload.get("schema")
    if schema not in {V1_SCHEMA, V2_SCHEMA}:
        raise OptimizerEvidenceError(
            "optimizer_output_invalid",
            f"schema must be {V1_SCHEMA} or {V2_SCHEMA}; observed {schema!r}",
        )
    return OptimizerOutput(snapshot.path, schema, snapshot.payload)


def validate_optimizer_outputs(
    optimizer_outputs: Sequence[str | Path],
    *,
    article: str | Path,
    editorial_plan: str | Path,
    proof_sidecar: str | Path,
    prior_preflight_readiness: str | Path,
    workspace_root: str | Path,
) -> None:
    """Require every optimizer output to bind the current release inputs."""
    root = Path(workspace_root).resolve()
    current = {
        "article": _current_artifact(article, root=root, label="article"),
        "editorial_plan": _current_artifact(
            editorial_plan,
            root=root,
            label="editorial_plan",
        ),
        "proof_sidecar": _current_artifact(
            proof_sidecar,
            root=root,
            label="proof_sidecar",
        ),
        "prior_preflight_readiness": _current_artifact(
            prior_preflight_readiness,
            root=root,
            label="prior_preflight_readiness",
        ),
    }
    for index, path in enumerate(optimizer_outputs):
        output = read_optimizer_output(path)
        if output.schema == V1_SCHEMA:
            raise OptimizerEvidenceError(
                "optimizer_output_stale",
                f"optimizer_outputs[{index}] cannot authorize a current release; "
                f"expected schema {V2_SCHEMA}, observed schema {V1_SCHEMA}",
            )
        bindings = _bindings(output.payload, index=index)
        scorecard = _declared_artifact(
            bindings["scorecard"],
            root=root,
            field=f"optimizer_outputs[{index}].input_bindings.scorecard",
        )
        _require_fresh_binding(
            bindings["scorecard"],
            scorecard,
            label="scorecard",
            index=index,
        )
        for label, observed in current.items():
            _require_fresh_binding(
                bindings[label],
                observed,
                label=label,
                index=index,
            )


def _bindings(payload: Mapping[str, Any], *, index: int) -> dict[str, Mapping[str, Any]]:
    if payload.get("status") != "completed":
        raise OptimizerEvidenceError(
            "optimizer_output_invalid",
            f"optimizer_outputs[{index}].status must be completed",
        )
    value = payload.get("input_bindings")
    if not isinstance(value, Mapping) or set(value) != set(REQUIRED_BINDINGS):
        names = ", ".join(REQUIRED_BINDINGS)
        raise OptimizerEvidenceError(
            "optimizer_output_invalid",
            f"optimizer_outputs[{index}].input_bindings must contain exactly: {names}",
        )
    result: dict[str, Mapping[str, Any]] = {}
    for label in REQUIRED_BINDINGS:
        row = value[label]
        if not isinstance(row, Mapping) or set(row) != {"path", "sha256"}:
            raise OptimizerEvidenceError(
                "optimizer_output_invalid",
                f"optimizer_outputs[{index}].input_bindings.{label} "
                "must contain only path and sha256",
            )
        try:
            validate_sha256(
                row.get("sha256"),
                field=f"optimizer_outputs[{index}].input_bindings.{label}.sha256",
            )
        except ValueError as error:
            raise OptimizerEvidenceError("optimizer_output_invalid", str(error)) from error
        result[label] = row
    return result


def _current_artifact(
    path: str | Path,
    *,
    root: Path,
    label: str,
) -> dict[str, str]:
    candidate = Path(path).resolve()
    try:
        relative = candidate.relative_to(root).as_posix()
        canonical = resolve_artifact(relative, workspace_root=root)
    except (OSError, ValueError) as error:
        raise OptimizerEvidenceError(
            "optimizer_output_invalid",
            f"current {label} is unavailable or outside workspace: {path}",
        ) from error
    if not canonical.is_file():
        raise OptimizerEvidenceError(
            "optimizer_output_invalid",
            f"current {label} is unavailable: {path}",
        )
    return {"path": relative, "sha256": file_sha256(canonical)}


def _declared_artifact(
    row: Mapping[str, Any],
    *,
    root: Path,
    field: str,
) -> dict[str, str]:
    try:
        path = resolve_artifact(row.get("path"), workspace_root=root)
    except ValueError as error:
        raise OptimizerEvidenceError("optimizer_output_invalid", f"{field}.path: {error}") from error
    if not path.is_file():
        raise OptimizerEvidenceError(
            "optimizer_output_invalid",
            f"{field}.path is unavailable",
        )
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": file_sha256(path),
    }


def _require_fresh_binding(
    row: Mapping[str, Any],
    observed: Mapping[str, str],
    *,
    label: str,
    index: int,
) -> None:
    expected_path = row.get("path")
    expected_hash = row.get("sha256")
    observed_path = observed["path"]
    observed_hash = observed["sha256"]
    if expected_path == observed_path and expected_hash == observed_hash:
        return
    raise OptimizerEvidenceError(
        "optimizer_output_stale",
        f"optimizer_outputs[{index}] {label} binding does not match current bytes; "
        f"expected_path={expected_path!r} observed_path={observed_path!r} "
        f"expected_sha256={expected_hash} observed_sha256={observed_hash}",
    )


__all__ = [
    "OptimizerEvidenceError",
    "OptimizerOutput",
    "V1_SCHEMA",
    "V2_SCHEMA",
    "read_optimizer_output",
    "validate_optimizer_outputs",
]
