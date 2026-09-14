from __future__ import annotations

from pathlib import Path

import pytest

from data_sources.modules.readiness.artifact_store import InstrumentedArtifactStore
from data_sources.modules.readiness.sealed_inventory import SealedInventory


def test_sealed_inventory_survives_session_boundary_and_rejects_mutation(
    tmp_path: Path,
) -> None:
    article = tmp_path / "article.md"
    article.write_bytes(b"# Article\n")
    store = InstrumentedArtifactStore.capture(
        {"article": article},
        workspace_root=tmp_path,
    )
    store.reseal()
    sealed = SealedInventory.issue(store)

    assert sealed.bytes("article") == b"# Article\n"
    assert sealed.release_inventory()["article"]["bytes"] == len(b"# Article\n")
    assert sealed.reseal() == sealed.release_inventory()

    article.write_text("# Changed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="changed during readiness"):
        sealed.reseal()


def test_sealed_inventory_tampering_is_rejected(tmp_path: Path) -> None:
    article = tmp_path / "article.md"
    article.write_bytes(b"# Article\n")
    store = InstrumentedArtifactStore.capture(
        {"article": article},
        workspace_root=tmp_path,
    )
    store.reseal()
    sealed = SealedInventory.issue(store)
    object.__setattr__(sealed, "_signature", "0" * 64)

    with pytest.raises(ValueError, match="capability is invalid"):
        sealed.release_inventory()


def test_sealed_inventory_wrong_workspace_and_forged_signature_fail(tmp_path: Path) -> None:
    article = tmp_path / "article.md"
    article.write_bytes(b"article")
    store = InstrumentedArtifactStore.capture({"article": article}, workspace_root=tmp_path)
    store.reseal()
    sealed = SealedInventory.issue(store)
    forged = SealedInventory(store, tmp_path / "other", sealed._signature)
    with pytest.raises(ValueError, match="capability is invalid"):
        forged.release_inventory()
