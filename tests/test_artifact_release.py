from __future__ import annotations

import json
from pathlib import Path

from data_sources.modules import artifact_release


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_landing_release_uses_common_final_bundle_without_bom(
    tmp_path: Path,
    monkeypatch,
):
    article = _write(
        tmp_path / "landing-pages" / "page.md",
        "---\nartifact_type: landing_page\ntitle: Page\n---\n# Page\n\nBody.\n",
    )
    sidecar = _write(tmp_path / "research" / "validation-page.md", "Validation.\n")
    calls: list[tuple[str, object]] = []

    def readiness(*_args, **kwargs):
        calls.append(("readiness", (kwargs["phase"], kwargs["run_id"], kwargs["assembly_bom"])))
        return {
            "schema": "simpro-publish-readiness-result/v1",
            "phase": "preflight",
            "passed": True,
            "run_id": kwargs["run_id"],
            "artifact_kind": "landing_page",
        }

    def write_result(path, result, **kwargs):
        _write(Path(path), json.dumps(result))
        receipt = {"receipt_hash": "a" * 64}
        _write(Path(kwargs["receipt_path"]), json.dumps(receipt))
        return Path(kwargs["receipt_path"])

    def final(preflight, **kwargs):
        calls.append(("final", (kwargs["final_bom"], kwargs["run_id"])))
        return {**preflight, "phase": "final"}

    def prepare(result, **kwargs):
        manifest = Path(kwargs["release_manifest_path"])
        _write(manifest, '{"schema":"simpro-release-manifest/v1"}\n')
        calls.append(("prepare", kwargs["previous_receipt_hash"]))
        return {
            **result,
            "schema": "simpro-publish-readiness-result/v2",
            "release_manifest": str(manifest),
            "release_manifest_sha256": "b" * 64,
        }

    monkeypatch.setattr(artifact_release.publish_readiness, "run_publish_readiness", readiness)
    monkeypatch.setattr(artifact_release.publish_readiness, "write_readiness_result", write_result)
    monkeypatch.setattr(
        artifact_release.publish_readiness,
        "build_final_readiness_attestation",
        final,
    )
    monkeypatch.setattr(
        artifact_release.release_authorization,
        "prepare_final_release_result",
        prepare,
    )
    monkeypatch.setattr(
        artifact_release.release_authorization,
        "load_publish_authorization",
        lambda **kwargs: calls.append(("load", kwargs["workspace_root"])) or object(),
    )

    result = artifact_release.run_artifact_release(
        article=article,
        run_id="landing-run-1",
        proof_sidecar=sidecar,
        output_dir=tmp_path / "research" / "releases" / "landing-run-1",
        workspace_root=tmp_path,
    )

    assert result.exit_code == 0
    assert result.phase == "final_readiness"
    assert calls == [
        ("readiness", ("preflight", "landing-run-1", None)),
        ("final", (None, "landing-run-1")),
        ("prepare", "a" * 64),
        ("load", tmp_path.resolve()),
    ]
    assert sorted(path.name for path in result.output_dir.iterdir()) == [
        "final-readiness-stage-receipt.json",
        "final-readiness.json",
        "preflight-readiness-stage-receipt.json",
        "preflight-readiness.json",
        "release-manifest.json",
        "release-telemetry.json",
    ]
