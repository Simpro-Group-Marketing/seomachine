"""Compatibility imports for the standalone Simpro vault connector package.

The canonical engine, Python client, CLI, and MCP adapters live in the
``simpro-vault-connector`` distribution. Seomachine keeps this module so
existing workflow imports continue to resolve without consumer-specific
connector discovery.
"""

from __future__ import annotations

from simpro_vault import (
    OPERATIONS,
    RECOVERY_HINTS,
    VaultClient,
    VaultClientError,
    VaultOperationResult,
)


SimproVaultClient = VaultClient


__all__ = [
    "OPERATIONS",
    "RECOVERY_HINTS",
    "SimproVaultClient",
    "VaultClientError",
    "VaultOperationResult",
]
