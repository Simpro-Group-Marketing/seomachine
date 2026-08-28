from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_sources.modules import blog_release


def _touch(path: Path, payload: str = "{}\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(payload, encoding="utf-8"); return path


def _inputs(tmp_path: Path) -> dict[str, object]:
    return {
        "article": _touch(tmp_path / "rewrites" / "article.md", "---\nartifact_type: blog\n---\n# Article\n"),
        "proof_sidecar": _touch(tmp_path / "research" / "sidecar.md"),
        "editorial_plan": _touch(tmp_path / "research" / "plan.json"),
        "plan_review": _touch(tmp_path / "research" / "plan-review.json"),
        "article_review": _touch(tmp_path / "research" / "article-review.json"),
        "keyword_decision": _touch(tmp_path / "research" / "keyword.json"),
        "scrub_receipt": _touch(tmp_path / "research" / "scrub.json"),
        "serp_evidence": _touch(tmp_path / "research" / "serp.json"),
        "stage_receipts": [_touch(tmp_path / "research" / "stage.json")],
    }


def _run(tmp_path: Path, **kwargs):
    return blog_release.run_blog_release(run_id="run-1", workflow_mode="rewrite", assembly_date="2026-08-26", output_dir=tmp_path / "research" / "releases" / "run", workspace_root=tmp_path, **_inputs(tmp_path), **kwargs)


def test_blog_release_rejects_reused_output_directory(tmp_path: Path):
    (tmp_path / "research" / "releases" / "run").mkdir(parents=True)
    with pytest.raises(blog_release.ReleaseInvocationError):
        _run(tmp_path)


def test_blog_release_writes_fixed_artifacts_for_blocker_and_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(blog_release.blog_creation_preflight, "build_preflight_report", lambda *a, **k: {"schema": "simpro-blog-creation-preflight/v1", "ready_for_bom": False, "blockers": [{"rule_id": "blocked"}]})
    blocked = _run(tmp_path)
    assert blocked.exit_code == 1 and (blocked.output_dir / "pre-bom-report.json").is_file()
    assert not (blocked.output_dir / "provisional-bom.json").exists()

    tmp2 = tmp_path / "success"; monkeypatch.setattr(blog_release.blog_creation_preflight, "build_preflight_report", lambda *a, **k: {"schema": "simpro-blog-creation-preflight/v1", "ready_for_bom": True, "blockers": []})
    monkeypatch.setattr(blog_release.blog_assembly_bom, "build_blog_assembly_bom_from_files", lambda **k: {"schema": "simpro-blog-assembly-bom/v2", "lifecycle_state": "provisional", "artifacts": {}, "workflow": {"stage_receipts": []}})
    monkeypatch.setattr(blog_release.blog_assembly_bom, "finalize_blog_assembly_bom", lambda **k: {"schema": "simpro-blog-assembly-bom/v2", "lifecycle_state": "final", "artifacts": {}, "workflow": {"stage_receipts": []}})
    monkeypatch.setattr(blog_release.publish_readiness, "run_publish_readiness", lambda *a, **k: {"schema": "simpro-publish-readiness-result/v1", "passed": True, "phase": k["phase"]})
    monkeypatch.setattr(blog_release.publish_readiness, "write_readiness_result", lambda output, result, **k: (_touch(Path(output), json.dumps(result)), _touch(Path(k["receipt_path"]), '{"receipt": true}\n')))
    passed = _run(tmp2)
    assert passed.exit_code == 0
    assert sorted(p.name for p in passed.output_dir.iterdir()) == ["final-bom.json", "final-readiness-stage-receipt.json", "final-readiness.json", "pre-bom-report.json", "preflight-readiness-stage-receipt.json", "preflight-readiness.json", "provisional-bom.json"]


def test_blog_release_cli_exit_codes_distinguish_policy_from_operational_failure(monkeypatch: pytest.MonkeyPatch):
    args = ["rewrites/article.md", "--run-id", "run-1", "--proof-sidecar", "research/sidecar.md", "--editorial-plan", "research/plan.json", "--plan-review", "research/plan-review.json", "--article-review", "research/article-review.json", "--keyword-decision", "research/keyword.json", "--scrub-receipt", "research/scrub.json", "--serp-evidence", "research/serp.json", "--stage-receipt", "research/stage.json", "--workflow-mode", "rewrite", "--assembly-date", "2026-08-26", "--output-dir", "research/releases/run"]
    monkeypatch.setattr(blog_release, "run_blog_release", lambda **k: (_ for _ in ()).throw(ValueError("policy blocker")))
    assert blog_release.main(args) == 1
    monkeypatch.setattr(blog_release, "run_blog_release", lambda **k: (_ for _ in ()).throw(OSError("disk write failed")))
    assert blog_release.main(args) == 2
