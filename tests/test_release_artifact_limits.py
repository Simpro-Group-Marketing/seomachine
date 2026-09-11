from __future__ import annotations

from pathlib import Path

import pytest

from data_sources.modules import blog_release
from data_sources.modules.artifact_runtime.limits import ARTICLE_MAX_BYTES
from tests.test_blog_release import _inputs


def test_blog_release_rejects_oversized_article_before_creating_output(
    tmp_path: Path,
) -> None:
    inputs = _inputs(tmp_path)
    Path(inputs["article"]).write_bytes(b"a" * (ARTICLE_MAX_BYTES + 1))
    destination = tmp_path / "research" / "releases" / "run"

    with pytest.raises(blog_release.ReleaseInvocationError, match="article exceeds"):
        blog_release.run_blog_release(
            run_id="run-1",
            workflow_mode="rewrite",
            assembly_date="2026-08-26",
            output_dir=destination,
            workspace_root=tmp_path,
            **inputs,
        )

    assert not destination.exists()
