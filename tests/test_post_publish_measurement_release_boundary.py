"""Keep post-publish measurement evidence outside release contracts."""

import json
from pathlib import Path

import pytest

from data_sources.modules import (
    blog_assembly_contract,
    blog_assembly_bom_guard,
    editorial_plan_guard,
    publish_readiness,
)


RECEIPT_FIELD = "post_publish_measurement_receipt"


def _rule_ids(findings: list[dict[str, object]]) -> set[str]:
    return {str(finding["rule_id"]) for finding in findings}


def test_bom_rejects_post_publish_measurement_receipt_artifact(
    tmp_path: Path,
) -> None:
    article = tmp_path / "article.md"
    sidecar = tmp_path / "research" / "validation.md"
    article.write_text("---\ntitle: Boundary check\n---\n\n# Boundary check\n", encoding="utf-8")
    sidecar.parent.mkdir(parents=True)
    sidecar.write_text("# Validation\n", encoding="utf-8")
    bom = {
        "artifacts": {
            RECEIPT_FIELD: {
                "path": "research/performance-receipt-boundary.json",
                "sha256": "0" * 64,
            }
        }
    }

    findings = blog_assembly_bom_guard.check_bom(
        bom,
        article_path=article,
        validation_sidecar_path=sidecar,
        workspace_root=tmp_path,
    )

    assert "bom_artifacts_unknown_fields" in _rule_ids(findings)


def test_bom_rejects_measurement_receipt_smuggled_as_optimizer_output(
    tmp_path: Path,
) -> None:
    article = tmp_path / "article.md"
    sidecar = tmp_path / "research" / "validation.md"
    receipt = tmp_path / "research" / "performance-receipt-boundary.json"
    article.write_text("---\ntitle: Boundary check\n---\n\n# Boundary check\n", encoding="utf-8")
    sidecar.parent.mkdir(parents=True)
    sidecar.write_text("# Validation\n", encoding="utf-8")
    receipt.write_text(
        json.dumps({"schema": "simpro-post-publish-measurement-receipt/v1"}) + "\n",
        encoding="utf-8",
    )
    bom = {
        "artifacts": {
            "optimizer_outputs": [
                blog_assembly_contract.canonical_artifact(
                    receipt,
                    workspace_root=tmp_path,
                )
            ]
        }
    }

    findings = blog_assembly_bom_guard.check_bom(
        bom,
        article_path=article,
        validation_sidecar_path=sidecar,
        workspace_root=tmp_path,
    )

    assert "bom_post_publish_measurement_receipt_forbidden" in _rule_ids(findings)


@pytest.mark.parametrize(
    "relative_path",
    [
        "research/performance-review-boundary-2026-08-21.md",
        "repurposed/boundary-repurposed-2026-08-21.md",
    ],
)
def test_bom_rejects_post_publish_markdown_smuggled_as_optimizer_output(
    tmp_path: Path,
    relative_path: str,
) -> None:
    article = tmp_path / "article.md"
    sidecar = tmp_path / "research" / "validation.md"
    post_publish = tmp_path / relative_path
    article.write_text(
        "---\ntitle: Boundary check\n---\n\n# Boundary check\n",
        encoding="utf-8",
    )
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text("# Validation\n", encoding="utf-8")
    post_publish.parent.mkdir(parents=True, exist_ok=True)
    post_publish.write_text("# Advisory handoff\n", encoding="utf-8")
    bom = {
        "artifacts": {
            "optimizer_outputs": [
                blog_assembly_contract.canonical_artifact(
                    post_publish,
                    workspace_root=tmp_path,
                )
            ]
        }
    }

    findings = blog_assembly_bom_guard.check_bom(
        bom,
        article_path=article,
        validation_sidecar_path=sidecar,
        workspace_root=tmp_path,
    )

    assert "bom_post_publish_artifact_forbidden" in _rule_ids(findings)


def test_editorial_plan_rejects_post_publish_measurement_receipt_field() -> None:
    findings = editorial_plan_guard.check_plan(
        {RECEIPT_FIELD: {"path": "research/performance-receipt-boundary.json"}}
    )

    assert "editorial_plan_unknown_field" in _rule_ids(findings)
    assert any(
        finding.get("location") == f"/{RECEIPT_FIELD}"
        for finding in findings
    )


def test_publish_readiness_cli_rejects_measurement_receipt_input(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as error:
        publish_readiness.main(
            [
                "article.md",
                "--post-publish-measurement-receipt",
                "research/performance-receipt-boundary.json",
            ]
        )

    assert error.value.code == 2
    assert "unrecognized arguments: --post-publish-measurement-receipt" in capsys.readouterr().err
