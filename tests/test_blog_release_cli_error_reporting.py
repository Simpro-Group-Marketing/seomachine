from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_sources.modules import blog_release


def _touch(path: Path, payload: str = "{}\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return path


def _cli_args(tmp_path: Path, *, workflow_mode: str = "rewrite") -> list[str]:
    paths = {
        "article": _touch(
            tmp_path / "rewrites" / "article.md",
            "---\nartifact_type: blog\n---\n# Article\n",
        ),
        "proof_sidecar": _touch(tmp_path / "research" / "sidecar.md"),
        "editorial_plan": _touch(tmp_path / "research" / "plan.json"),
        "plan_fulfillment": _touch(tmp_path / "research" / "fulfillment.json"),
        "commercial_pillar_index": _touch(
            tmp_path / "context" / "commercial-pillar-index.json"
        ),
        "plan_review": _touch(tmp_path / "research" / "plan-review.json"),
        "article_review": _touch(tmp_path / "research" / "article-review.json"),
        "keyword_decision": _touch(tmp_path / "research" / "keyword.json"),
        "scrub_receipt": _touch(tmp_path / "research" / "scrub.json"),
        "serp_evidence": _touch(tmp_path / "research" / "serp.json"),
        "stage_receipt": _touch(tmp_path / "research" / "stage.json"),
    }
    return [
        str(paths["article"]),
        "--run-id",
        "run-1",
        "--proof-sidecar",
        str(paths["proof_sidecar"]),
        "--editorial-plan",
        str(paths["editorial_plan"]),
        "--plan-fulfillment",
        str(paths["plan_fulfillment"]),
        "--commercial-pillar-index",
        str(paths["commercial_pillar_index"]),
        "--plan-review",
        str(paths["plan_review"]),
        "--article-review",
        str(paths["article_review"]),
        "--keyword-decision",
        str(paths["keyword_decision"]),
        "--scrub-receipt",
        str(paths["scrub_receipt"]),
        "--serp-evidence",
        str(paths["serp_evidence"]),
        "--stage-receipt",
        str(paths["stage_receipt"]),
        "--workflow-mode",
        workflow_mode,
        "--assembly-date",
        "2026-08-26",
        "--output-dir",
        "research/releases/run",
        "--workspace-root",
        str(tmp_path),
    ]


def test_blog_release_cli_reports_parse_errors_when_run_context_is_available(
    tmp_path: Path,
):
    with pytest.raises(SystemExit) as raised:
        blog_release.main(_cli_args(tmp_path, workflow_mode="invalid"))

    assert raised.value.code == 2
    payload = json.loads(
        (tmp_path / "research" / "release-errors" / "run-1.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["schema"] == "simpro-blog-release-error/v1"
    assert payload["failure_kind"] == "exception"
    assert payload["exception_type"] == "SystemExit"
    assert payload["message"] == "argparse exited with code 2"
    assert payload["phase"] == "cli_parse"
    assert payload["module"] == "release_cli"
    assert payload["artifact"] == "blog"
    assert payload["reuse_status"] == "new"
    assert payload["paths"]["output_dir"] == "research/releases/run"


def test_blog_release_cli_parse_error_uses_cwd_when_workspace_root_is_omitted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    args = _cli_args(tmp_path, workflow_mode="invalid")
    workspace_flag = args.index("--workspace-root")
    del args[workspace_flag : workspace_flag + 2]
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as raised:
        blog_release.main(args)

    assert raised.value.code == 2
    payload = json.loads(
        (tmp_path / "research" / "release-errors" / "run-1.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["phase"] == "cli_parse"
    assert payload["module"] == "release_cli"
    assert payload["paths"]["output_dir"] == "research/releases/run"


def test_blog_release_cli_does_not_overwrite_direct_blog_release_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        blog_release.blog_creation_preflight,
        "build_preflight_report",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("boundary failed")),
    )

    assert blog_release.main(_cli_args(tmp_path)) == 2

    payload = json.loads(
        (tmp_path / "research" / "release-errors" / "run-1.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["failure_kind"] == "exception"
    assert payload["exception_type"] == "OSError"
    assert payload["message"] == "boundary failed"
    assert payload["phase"] == "exception"
    assert payload["module"] == "blog_release"
    assert payload["next_command"] == (
        "Inspect the release artifacts and telemetry, repair the error, "
        "then rerun the blog release command."
    )
    assert payload["reuse_status"] == "new"
    assert payload["paths"]["output_dir"] == "research/releases/run"
