from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_sources.modules import blog_release
from tests.test_blog_release import _run, _touch


def test_blog_release_forwards_hindsight_strategy_evidence_to_bom(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    evidence = _touch(
        tmp_path / "research" / "hindsight-strategy-evidence.json",
        '{"pack":{},"receipt":{},"sidecar":{}}\n',
    )
    observed = {}

    monkeypatch.setattr(
        blog_release.blog_creation_preflight,
        "build_preflight_report",
        lambda *args, **kwargs: {
            "schema": "simpro-blog-creation-preflight/v1",
            "ready_for_bom": True,
            "blockers": [],
        },
    )

    def provisional(**kwargs):
        observed["hindsight_strategy_evidence_path"] = kwargs[
            "hindsight_strategy_evidence_path"
        ]
        return {
            "schema": "simpro-blog-assembly-bom/v2",
            "lifecycle_state": "provisional",
            "artifacts": {},
            "workflow": {"stage_receipts": []},
        }

    monkeypatch.setattr(
        blog_release.blog_assembly_bom,
        "build_blog_assembly_bom_from_files",
        provisional,
    )
    monkeypatch.setattr(
        blog_release.publish_readiness,
        "run_publish_readiness",
        lambda *args, **kwargs: {
            "schema": "simpro-publish-readiness-result/v1",
            "passed": False,
            "phase": kwargs["phase"],
        },
    )
    monkeypatch.setattr(
        blog_release.publish_readiness,
        "write_readiness_result",
        lambda output, result, **kwargs: (
            _touch(Path(output), json.dumps(result)),
            None,
        )[1],
    )

    result = _run(tmp_path, hindsight_strategy_evidence=evidence)

    assert result.exit_code == 0
    assert result.phase == "optimization_started"
    assert observed == {"hindsight_strategy_evidence_path": evidence}
