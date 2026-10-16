"""Canonical logical-input specification for readiness and release artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .artifact_io import resolve_input, resolve_workspace_root


_FIXED_WORKSPACE_INPUTS = (
    ("context_boundary_policy", "context/context-policy.json"),
    ("source_decision_registry", "context/source-classification-decisions.json"),
    ("customer_proof_usage_ledger", "config/customer-proof-usage-ledger.json"),
    ("url_verification_allowlist", "context/url-verification-allowlist.json"),
)


@dataclass(frozen=True, slots=True)
class ReadinessInputBinding:
    """One logical label bound to a canonical physical workspace file."""

    label: str
    path: Path


@dataclass(frozen=True, slots=True)
class ReadinessInputSpec:
    """Immutable input contract shared by capture, validation, and release."""

    workspace_root: Path
    bindings: tuple[ReadinessInputBinding, ...]

    @classmethod
    def from_mapping(
        cls,
        inputs: Mapping[str, str | Path | None],
        *,
        workspace_root: str | Path,
        include_workspace_defaults: bool = False,
    ) -> "ReadinessInputSpec":
        root = resolve_workspace_root(workspace_root)
        values = dict(inputs)
        if include_workspace_defaults:
            for label, relative_path in _FIXED_WORKSPACE_INPUTS:
                candidate = root / relative_path
                if candidate.is_file():
                    values.setdefault(label, candidate)
        bindings: list[ReadinessInputBinding] = []
        for label in sorted(values, key=str):
            value = values[label]
            if value is None:
                continue
            _validate_label(label)
            bindings.append(
                ReadinessInputBinding(label, resolve_input(value, workspace_root=root, field=label))
            )
        return cls(root, tuple(bindings))

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
        )

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(binding.label for binding in self.bindings)


def _validate_label(value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("readiness input labels must be non-empty strings")


__all__ = ["ReadinessInputBinding", "ReadinessInputSpec"]
