"""Canonical logical-input specification for readiness and release artifacts."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any

from .artifact_io import resolve_input, resolve_workspace_root


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_FIXED_WORKSPACE_INPUTS = (
    ("source_decision_registry", "context/source-classification-decisions.json"),
    ("customer_proof_index", "context/customer-proof-index.json"),
    ("customer_proof_usage_ledger", "context/customer-proof-usage-ledger.json"),
)


@dataclass(frozen=True, slots=True)
class ReadinessInputBinding:
    """One logical label bound to a canonical physical workspace file."""

    label: str
    path: Path
    expected_sha256: str | None = None
    expected_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class ReadinessInputSpec:
    """Immutable input contract shared by capture, validation, and release."""

    workspace_root: Path
    bindings: tuple[ReadinessInputBinding, ...]
    expand_bom_inventory: bool = True

    @classmethod
    def from_mapping(
        cls,
        inputs: Mapping[str, str | Path | None],
        *,
        workspace_root: str | Path,
        include_workspace_defaults: bool = False,
        expand_bom_inventory: bool = True,
    ) -> "ReadinessInputSpec":
        root = resolve_workspace_root(workspace_root)
        values = dict(inputs)
        if include_workspace_defaults:
            for label, relative_path in _FIXED_WORKSPACE_INPUTS:
                candidate = root / relative_path
                if candidate.is_file():
                    values.setdefault(label, candidate)
        rows = {
            label: {"path": value}
            for label, value in values.items()
            if value is not None
        }
        return cls._from_rows(
            rows,
            workspace_root=root,
            expand_bom_inventory=expand_bom_inventory,
        )

    @classmethod
    def for_readiness(
        cls,
        inputs: Mapping[str, str | Path | None],
        *,
        workspace_root: str | Path,
    ) -> "ReadinessInputSpec":
        return cls.from_mapping(
            inputs,
            workspace_root=workspace_root,
            include_workspace_defaults=True,
            expand_bom_inventory=True,
        )

    @classmethod
    def for_final_attestation(
        cls,
        preflight_inventory: Mapping[str, Any],
        direct_inputs: Mapping[str, str | Path | None],
        *,
        workspace_root: str | Path,
    ) -> "ReadinessInputSpec":
        """Bind authenticated preflight inputs plus the replacement final BOM."""
        root = resolve_workspace_root(workspace_root)
        rows: dict[str, Mapping[str, Any]] = {}
        for label, row in preflight_inventory.items():
            if label == "assembly_bom":
                continue
            _validate_label(label)
            if not isinstance(row, Mapping):
                raise ValueError(f"readiness input {label} must be an object")
            rows[label] = row
        for label, value in direct_inputs.items():
            if value is None:
                continue
            existing = rows.get(label)
            if existing is not None:
                existing_path = resolve_input(
                    existing.get("path"), workspace_root=root, field=label
                )
                direct_path = resolve_input(value, workspace_root=root, field=label)
                if existing_path != direct_path:
                    raise ValueError(
                        f"final readiness input differs from authenticated preflight: {label}"
                    )
                continue
            rows[label] = {"path": value}
        for label, relative_path in _FIXED_WORKSPACE_INPUTS:
            candidate = root / relative_path
            if candidate.is_file():
                rows.setdefault(label, {"path": candidate})
        return cls._from_rows(
            rows,
            workspace_root=root,
            expand_bom_inventory=True,
        )

    @classmethod
    def from_hash_inventory(
        cls,
        rows: Mapping[str, Any],
        *,
        workspace_root: str | Path,
        expand_bom_inventory: bool = False,
    ) -> "ReadinessInputSpec":
        return cls._from_rows(
            rows,
            workspace_root=resolve_workspace_root(workspace_root),
            require_sha256=True,
            expand_bom_inventory=expand_bom_inventory,
        )

    @classmethod
    def from_release_inventory(
        cls,
        rows: Mapping[str, Any],
        *,
        workspace_root: str | Path,
    ) -> "ReadinessInputSpec":
        return cls._from_rows(
            rows,
            workspace_root=resolve_workspace_root(workspace_root),
            require_sha256=True,
            require_bytes=True,
            require_portable_paths=True,
            expand_bom_inventory=False,
        )

    @classmethod
    def _from_rows(
        cls,
        rows: Mapping[str, Any],
        *,
        workspace_root: Path,
        require_sha256: bool = False,
        require_bytes: bool = False,
        require_portable_paths: bool = False,
        expand_bom_inventory: bool,
    ) -> "ReadinessInputSpec":
        if not isinstance(rows, Mapping):
            raise ValueError("readiness input inventory must be an object")
        bindings: list[ReadinessInputBinding] = []
        physical: dict[Path, tuple[str | None, int | None]] = {}
        for label in sorted(rows, key=str):
            row = rows[label]
            _validate_label(label)
            if not isinstance(row, Mapping):
                raise ValueError(f"readiness input {label} must be an object")
            allowed = {"path", "sha256", "bytes"}
            if set(row) - allowed:
                raise ValueError(f"readiness input {label} has unknown fields")
            if require_sha256 and "sha256" not in row:
                raise ValueError(f"readiness input {label} requires sha256")
            if require_bytes and "bytes" not in row:
                raise ValueError(f"readiness input {label} requires bytes")
            if require_portable_paths:
                _validate_portable_path(row.get("path"), label=label)
            path = resolve_input(row.get("path"), workspace_root=workspace_root, field=label)
            digest = _optional_sha256(row.get("sha256"), label=label)
            byte_count = _optional_byte_count(row.get("bytes"), label=label)
            previous = physical.get(path)
            if previous is not None:
                _validate_alias_contract(label, digest, byte_count, previous)
                digest = digest or previous[0]
                byte_count = byte_count if byte_count is not None else previous[1]
            physical[path] = (digest, byte_count)
            bindings.append(ReadinessInputBinding(label, path, digest, byte_count))
        return cls(workspace_root, tuple(bindings), expand_bom_inventory)

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(binding.label for binding in self.bindings)


def _validate_label(value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("readiness input labels must be non-empty strings")


def _optional_sha256(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"readiness input {label} sha256 is invalid")
    return value


def _optional_byte_count(value: Any, *, label: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"readiness input {label} byte count is invalid")
    return value


def _validate_alias_contract(
    label: str,
    digest: str | None,
    byte_count: int | None,
    previous: tuple[str | None, int | None],
) -> None:
    previous_digest, previous_bytes = previous
    if digest is not None and previous_digest is not None and digest != previous_digest:
        raise ValueError(f"readiness input alias {label} has a conflicting sha256")
    if byte_count is not None and previous_bytes is not None and byte_count != previous_bytes:
        raise ValueError(f"readiness input alias {label} has a conflicting byte count")


def _validate_portable_path(value: Any, *, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"readiness input {label} path is invalid")
    pure = PurePosixPath(value)
    if pure.is_absolute() or "\\" in value or any(
        part in {"", ".", ".."} for part in pure.parts
    ):
        raise ValueError(f"readiness input {label} path is invalid")


__all__ = ["ReadinessInputBinding", "ReadinessInputSpec"]
