"""Explicit external dependency contract for readiness orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..simpro_vault_client import SimproVaultClient
from ..vault_claim_receipts import load_validated_claim_set


@dataclass(frozen=True)
class ReadinessDependencies:
    """Connector operations injected at the readiness ownership boundary."""

    connector_factory: Callable[..., Any] = SimproVaultClient
    claim_set_loader: Callable[..., Any] = load_validated_claim_set


DEFAULT_READINESS_DEPENDENCIES = ReadinessDependencies()


__all__ = ["DEFAULT_READINESS_DEPENDENCIES", "ReadinessDependencies"]
