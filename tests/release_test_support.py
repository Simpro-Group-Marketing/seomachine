"""Shared release test doubles kept outside size-budgeted test modules."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

import pytest


def mock_final_authorization(
    monkeypatch: pytest.MonkeyPatch,
    release_module: ModuleType,
) -> None:
    def prepare(result, *, release_manifest_path, **_kwargs):
        path = Path(release_manifest_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"schema":"simpro-release-manifest/v1"}\n', encoding="utf-8")
        return {
            **result,
            "schema": "simpro-publish-readiness-result/v2",
            "release_manifest": str(release_manifest_path),
            "release_manifest_sha256": "b" * 64,
        }

    monkeypatch.setattr(
        release_module.release_authorization,
        "prepare_final_release_result",
        prepare,
    )
    monkeypatch.setattr(
        release_module.release_authorization,
        "load_publish_authorization",
        lambda **_kwargs: object(),
    )
