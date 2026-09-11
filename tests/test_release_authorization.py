from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from data_sources.modules.blog_assembly_contract import canonical_json_bytes
from data_sources.modules.blog_assembly_stage_receipt import (
    build_stage_receipt,
    write_stage_receipt,
)
from data_sources.modules.release_authorization import (
    RELEASE_MANIFEST_SCHEMA,
    load_publish_authorization,
    prepare_final_release_result,
)
from data_sources.modules import publish_readiness
from tests.test_publish_readiness import files as readiness_files, run_with_patches


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_json(path: Path, value: object) -> bytes:
    content = canonical_json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return content


def _gate(name: str = "artifact_identity") -> dict[str, object]:
    return {
        "name": name,
        "label": "Artifact Identity",
        "passed": True,
        "errors": 0,
        "warnings": 0,
        "findings": [],
        "blockers": [],
    }


def _landing_bundle(tmp_path: Path, *, schema: str = "simpro-publish-readiness-result/v2"):
    article = tmp_path / "landing-pages" / "page.md"
    article.parent.mkdir(parents=True)
    article.write_text(
        "---\nartifact_type: landing_page\ntitle: Page\n---\n# Page\n\nBody.\n",
        encoding="utf-8",
    )
    article_bytes = article.read_bytes()
    inventory = {
        "article": {
            "path": "landing-pages/page.md",
            "sha256": _sha256(article_bytes),
            "bytes": len(article_bytes),
        }
    }
    manifest = {
        "schema": RELEASE_MANIFEST_SCHEMA,
        "artifact_kind": "landing_page",
        "run_id": "run-landing-1",
        "created_at": "2026-09-11T12:00:00Z",
        "inputs": inventory,
        "previous_receipt_hash": "",
    }
    manifest_path = tmp_path / "research" / "releases" / "run" / "release-manifest.json"
    manifest_bytes = _write_json(manifest_path, manifest)
    result = {
        "schema": schema,
        "tool": {"name": "publish_readiness", "version": "1.0.0"},
        "phase": "final",
        "verification_scope": "source_artifact",
        "file": str(article),
        "proof_sidecar": None,
        "context_request": None,
        "context_pack": None,
        "context_receipt": None,
        "assembly_bom": None,
        "passed": True,
        "artifact_kind": "landing_page",
        "gates": [_gate()],
        "score": 80,
        "score_threshold": 75,
        "aeo_geo": {"score": 80, "threshold": 75, "passed": True},
        "scorecard": {
            "passed": True,
            "content_quality": {"score": 80, "threshold": 75, "passed": True},
            "seo_quality": {
                "score": None,
                "threshold": None,
                "passed": True,
                "not_applicable": True,
                "critical_issue_count": 0,
                "critical_issues": [],
            },
            "aeo_geo": {
                "score": None,
                "threshold": None,
                "passed": True,
                "not_applicable": True,
            },
        },
        "priority_fixes": [],
        "gate_inventory": ["artifact_identity"],
        "input_hashes": {
            label: {"path": row["path"], "sha256": row["sha256"]}
            for label, row in inventory.items()
        },
        "input_seal": {"status": "verified"},
        "run_id": "run-landing-1",
        "started_at": "2026-09-11T12:01:00Z",
        "completed_at": "2026-09-11T12:02:00Z",
        "release_manifest": "research/releases/run/release-manifest.json",
        "release_manifest_sha256": _sha256(manifest_bytes),
    }
    result_path = manifest_path.with_name("final-readiness.json")
    result_bytes = _write_json(result_path, result)
    receipt = build_stage_receipt(
        run_id="run-landing-1",
        stage="final_readiness_attestation",
        tool_name="publish_readiness",
        tool_version="1.0.0",
        started_at=result["started_at"],
        completed_at=result["completed_at"],
        mutation=False,
        input_artifact_hashes={"article": inventory["article"]["sha256"]},
        output_artifact_hashes={
            "article": inventory["article"]["sha256"],
            "readiness_output": _sha256(result_bytes),
            "release_manifest": _sha256(manifest_bytes),
        },
        previous_receipt_hash="",
        workspace_root=tmp_path,
    )
    receipt_path = manifest_path.with_name("final-readiness-stage-receipt.json")
    write_stage_receipt(receipt_path, receipt, workspace_root=tmp_path)
    return article, manifest_path, result_path, receipt_path


def test_load_publish_authorization_accepts_landing_bundle_without_bom(tmp_path: Path):
    article, manifest_path, result_path, receipt_path = _landing_bundle(tmp_path)

    authorization = load_publish_authorization(
        final_readiness_path=result_path,
        final_receipt_path=receipt_path,
        release_manifest_path=manifest_path,
        workspace_root=tmp_path,
    )

    observed: list[tuple[bytes, dict[str, str]]] = []
    returned = authorization.with_final_input_seal(
        lambda article_bytes, inventory: observed.append((article_bytes, dict(inventory)))
        or "mutated"
    )
    assert returned == "mutated"
    assert observed == [(article.read_bytes(), {"article": _sha256(article.read_bytes())})]


def test_authorization_rejects_historical_v1_and_unknown_fields(tmp_path: Path):
    _, manifest_path, result_path, receipt_path = _landing_bundle(
        tmp_path, schema="simpro-publish-readiness-result/v1"
    )
    with pytest.raises(ValueError, match="v2"):
        load_publish_authorization(
            final_readiness_path=result_path,
            final_receipt_path=receipt_path,
            release_manifest_path=manifest_path,
            workspace_root=tmp_path,
        )

    _, manifest_path, result_path, receipt_path = _landing_bundle(tmp_path / "unknown")
    value = json.loads(result_path.read_text(encoding="utf-8"))
    value["unexpected"] = True
    _write_json(result_path, value)
    with pytest.raises(ValueError, match="field set"):
        load_publish_authorization(
            final_readiness_path=result_path,
            final_receipt_path=receipt_path,
            release_manifest_path=manifest_path,
            workspace_root=tmp_path / "unknown",
        )


def test_authorization_fails_before_callback_when_an_input_changes(tmp_path: Path):
    article, manifest_path, result_path, receipt_path = _landing_bundle(tmp_path)
    authorization = load_publish_authorization(
        final_readiness_path=result_path,
        final_receipt_path=receipt_path,
        release_manifest_path=manifest_path,
        workspace_root=tmp_path,
    )
    article.write_text("changed", encoding="utf-8")
    called = False

    def mutation(*_args):
        nonlocal called
        called = True

    with pytest.raises(ValueError, match="article"):
        authorization.with_final_input_seal(mutation)
    assert called is False


def test_authorization_detects_change_and_restore_before_mutation(tmp_path: Path):
    article, manifest_path, result_path, receipt_path = _landing_bundle(tmp_path)
    authorization = load_publish_authorization(
        final_readiness_path=result_path,
        final_receipt_path=receipt_path,
        release_manifest_path=manifest_path,
        workspace_root=tmp_path,
    )
    original = article.read_bytes()
    article.write_bytes(b"temporary replacement")
    article.write_bytes(original)
    called = False

    def mutation(*_args):
        nonlocal called
        called = True

    with pytest.raises(ValueError, match="changed since authorization"):
        authorization.with_final_input_seal(mutation)
    assert called is False


def test_authorization_rejects_wrong_workspace_and_modified_bundle(tmp_path: Path):
    _, manifest_path, result_path, receipt_path = _landing_bundle(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(ValueError, match="workspace"):
        load_publish_authorization(
            final_readiness_path=result_path,
            final_receipt_path=receipt_path,
            release_manifest_path=manifest_path,
            workspace_root=other,
        )

    result_path.write_bytes(result_path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="readiness output"):
        load_publish_authorization(
            final_readiness_path=result_path,
            final_receipt_path=receipt_path,
            release_manifest_path=manifest_path,
            workspace_root=tmp_path,
        )


def test_real_blog_finalization_round_trips_through_authorization(
    readiness_files: tuple[Path, Path],
):
    article, sidecar = readiness_files
    preflight, _, _, _ = run_with_patches(article, sidecar)
    provisional_path = Path(preflight["assembly_bom"])
    bom = json.loads(provisional_path.read_text(encoding="utf-8"))
    bom["lifecycle_state"] = "final"
    final_bom = provisional_path.with_name("final-bom.json")
    _write_json(final_bom, bom)
    final = publish_readiness.build_final_readiness_attestation(
        preflight,
        final_bom=final_bom,
        workspace_root=article.parent,
    )
    release_dir = article.parent / "research" / "releases" / "round-trip"
    manifest_path = release_dir / "release-manifest.json"
    final = prepare_final_release_result(
        final,
        release_manifest_path=manifest_path,
        previous_receipt_hash="",
        workspace_root=article.parent,
    )
    readiness_path = release_dir / "final-readiness.json"
    receipt_path = release_dir / "final-readiness-stage-receipt.json"
    publish_readiness.write_readiness_result(
        readiness_path,
        final,
        receipt_path=receipt_path,
        workspace_root=article.parent,
    )

    authorization = load_publish_authorization(
        final_readiness_path=readiness_path,
        final_receipt_path=receipt_path,
        release_manifest_path=manifest_path,
        workspace_root=article.parent,
    )
    assert authorization.artifact_kind == "blog"
    assert authorization.artifacts["assembly_bom"].path == final_bom.resolve()

    with pytest.raises(ValueError, match="already exists"):
        publish_readiness.write_readiness_result(
            readiness_path,
            final,
            receipt_path=receipt_path,
            workspace_root=article.parent,
        )
