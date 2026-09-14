"""Process-local authority over one final readiness input snapshot."""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from ..blog_assembly_contract import canonical_json_bytes
from .artifact_store import InstrumentedArtifactStore


_SEALED_INVENTORY_KEY = os.urandom(32)


@dataclass(frozen=True, slots=True)
class SealedInventory:
    """A capability issued only after a final session has resealed its store."""

    _store: InstrumentedArtifactStore
    _workspace_root: Path
    _signature: str

    @classmethod
    def issue(cls, store: InstrumentedArtifactStore) -> "SealedInventory":
        root = store.workspace_root.resolve()
        inventory = store.release_inventory()
        return cls(store, root, _sign(root, inventory))

    @property
    def workspace_root(self) -> Path:
        self._authenticate()
        return self._workspace_root

    def hash_inventory(self) -> dict[str, dict[str, str]]:
        self._authenticate()
        return self._store.hash_inventory()

    def release_inventory(self) -> dict[str, dict[str, str | int]]:
        self._authenticate()
        return self._store.release_inventory()

    def bytes(self, label: str) -> bytes:
        self._authenticate()
        return self._store.bytes(label)

    def reseal(self) -> dict[str, dict[str, str | int]]:
        """Verify the original snapshot against current files without recapturing."""
        self._authenticate()
        current = self._store.reseal()
        if _sign(self._workspace_root, current) != self._signature:
            raise ValueError("sealed readiness inventory changed after finalization")
        return current

    def _authenticate(self) -> None:
        expected = _sign(self._workspace_root, self._store.release_inventory())
        if not hmac.compare_digest(self._signature, expected):
            raise ValueError("sealed readiness inventory capability is invalid")


def _sign(
    workspace_root: Path,
    inventory: Mapping[str, Mapping[str, str | int]],
) -> str:
    payload = {
        "workspace_root": str(workspace_root.resolve()),
        "inventory": inventory,
    }
    return hmac.new(
        _SEALED_INVENTORY_KEY,
        canonical_json_bytes(payload),
        hashlib.sha256,
    ).hexdigest()


__all__ = ["SealedInventory"]
