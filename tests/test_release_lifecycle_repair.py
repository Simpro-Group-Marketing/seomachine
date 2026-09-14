from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from data_sources.modules.artifact_release import run_artifact_release
from data_sources.modules.readiness import artifact_store
from data_sources.modules.release_authorization import load_publish_authorization
from data_sources.modules.readiness.finalization import build_final_attestation
from data_sources.modules.readiness.input_spec import ReadinessInputSpec
from data_sources.modules.readiness.persistence import persist_new_result_pair
from data_sources.modules.readiness.workspace_bindings import (
    _capture_readiness_inputs,
    _verify_result_inputs_unchanged,
)
from data_sources.modules.release_authorization.artifact_capture import (
    capture_manifest_inputs,
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, data: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")
    return path


def test_canonical_spec_includes_fixed_workspace_inputs(tmp_path: Path) -> None:
    article = _write(tmp_path / "landing-pages" / "page.md", "# Page\n")
    registry = _write(
        tmp_path / "context" / "source-classification-decisions.json",
        '{"schema":"registry"}\n',
    )
    proof_index = _write(
        tmp_path / "context" / "customer-proof-index.json",
        '{"schema":"proof-index"}\n',
    )
    ledger = _write(
        tmp_path / "context" / "customer-proof-usage-ledger.json",
        '{"schema":"proof-ledger"}\n',
    )

    spec = ReadinessInputSpec.for_readiness(
        {"article": article},
        workspace_root=tmp_path,
    )
    inputs = _capture_readiness_inputs(
        article=article,
        validation_sidecar=None,
        context_request=None,
        context_pack=None,
        context_receipt=None,
        assembly_bom=None,
        workspace_root=tmp_path,
    )

    assert spec.labels == (
        "article",
        "customer_proof_index",
        "customer_proof_usage_ledger",
        "source_decision_registry",
    )
    assert inputs.hash_inventory() == {
        "article": {"path": "landing-pages/page.md", "sha256": _sha256(article.read_bytes())},
        "customer_proof_index": {
            "path": "context/customer-proof-index.json",
            "sha256": _sha256(proof_index.read_bytes()),
        },
        "customer_proof_usage_ledger": {
            "path": "context/customer-proof-usage-ledger.json",
            "sha256": _sha256(ledger.read_bytes()),
        },
        "source_decision_registry": {
            "path": "context/source-classification-decisions.json",
            "sha256": _sha256(registry.read_bytes()),
        },
    }


def test_manifest_aliases_share_one_physical_capture(tmp_path: Path) -> None:
    article = _write(tmp_path / "article.md", "# Article\n")
    digest = _sha256(article.read_bytes())
    rows = {
        "article": {"path": "article.md", "sha256": digest, "bytes": article.stat().st_size},
        "historical_preflight.article": {
            "path": "article.md",
            "sha256": digest,
            "bytes": article.stat().st_size,
        },
    }

    artifacts = capture_manifest_inputs(rows, root=tmp_path)

    assert set(artifacts) == set(rows)
    assert artifacts["article"].data is artifacts["historical_preflight.article"].data
    assert artifacts["article"].file_identity == artifacts["historical_preflight.article"].file_identity


def test_manifest_aliases_read_and_hash_physical_file_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    article = _write(tmp_path / "article.md", "# Article\n")
    data = article.read_bytes()
    row = {
        "path": "article.md",
        "sha256": _sha256(data),
        "bytes": len(data),
    }
    reads: list[Path] = []
    hashes: list[bytes] = []
    real_read = artifact_store._read_bounded
    real_hash = artifact_store.hashlib.sha256

    def counted_read(path: Path, *, max_bytes: int, field: str) -> bytes:
        reads.append(path)
        return real_read(path, max_bytes=max_bytes, field=field)

    def counted_hash(content: bytes = b""):
        hashes.append(content)
        return real_hash(content)

    monkeypatch.setattr(artifact_store, "_read_bounded", counted_read)
    monkeypatch.setattr(artifact_store.hashlib, "sha256", counted_hash)

    capture_manifest_inputs(
        {"article": row, "historical_preflight.article": row},
        root=tmp_path,
    )

    assert reads == [article]
    assert hashes == [data]


@pytest.mark.parametrize("field,value", [("sha256", "0" * 64), ("bytes", 1)])
def test_manifest_aliases_reject_conflicting_physical_contract(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    article = _write(tmp_path / "article.md", "# Article\n")
    row = {
        "path": "article.md",
        "sha256": _sha256(article.read_bytes()),
        "bytes": article.stat().st_size,
    }
    conflicting = dict(row)
    conflicting[field] = value

    with pytest.raises(ValueError, match="alias|match current bytes"):
        capture_manifest_inputs(
            {"article": row, "historical_preflight.article": conflicting},
            root=tmp_path,
        )


def test_landing_final_result_does_not_require_a_bom(tmp_path: Path) -> None:
    article = _write(tmp_path / "landing-pages" / "page.md", "# Page\n")
    digest = _sha256(article.read_bytes())

    _verify_result_inputs_unchanged(
        {
            "phase": "final",
            "artifact_kind": "landing_page",
            "input_seal": {"status": "verified"},
            "input_hashes": {"article": {"path": "landing-pages/page.md", "sha256": digest}},
        },
        workspace_root=tmp_path,
    )


@pytest.mark.parametrize(
    "extra",
    [
        {"assembly_bom": "final-bom.json"},
        {"final_bom_sha256": "0" * 64},
    ],
)
def test_landing_final_result_rejects_blog_bom_bindings(
    tmp_path: Path,
    extra: dict[str, str],
) -> None:
    article = _write(tmp_path / "landing-pages" / "page.md", "# Page\n")
    digest = _sha256(article.read_bytes())
    result = {
        "phase": "final",
        "artifact_kind": "landing_page",
        "input_seal": {"status": "verified"},
        "input_hashes": {
            "article": {"path": "landing-pages/page.md", "sha256": digest}
        },
        **extra,
    }

    with pytest.raises(ValueError, match="must not contain"):
        _verify_result_inputs_unchanged(result, workspace_root=tmp_path)


def test_blog_final_result_requires_bom(tmp_path: Path) -> None:
    article = _write(tmp_path / "article.md", "# Article\n")

    with pytest.raises(ValueError, match="requires a final assembly BOM"):
        _verify_result_inputs_unchanged(
            {
                "phase": "final",
                "artifact_kind": "blog",
                "input_seal": {"status": "verified"},
                "input_hashes": {
                    "article": {
                        "path": "article.md",
                        "sha256": _sha256(article.read_bytes()),
                    }
                },
            },
            workspace_root=tmp_path,
        )


def test_final_attestation_runs_complete_bom_guard(tmp_path: Path) -> None:
    article = _write(tmp_path / "article.md", "# Article\n")
    sidecar = _write(tmp_path / "validation.md", "Validation\n")
    final_bom = _write(
        tmp_path / "final-bom.json",
        '{"lifecycle_state":"final","artifacts":{}}\n',
    )

    with pytest.raises(ValueError, match="final BOM is invalid"):
        build_final_attestation(
            {
                "phase": "preflight",
                "artifact_kind": "blog",
                "file": str(article),
                "proof_sidecar": str(sidecar),
                "context_request": None,
                "context_pack": None,
                "context_receipt": None,
                "input_hashes": {
                    "article": {"path": "article.md", "sha256": _sha256(article.read_bytes())},
                    "validation_sidecar": {
                        "path": "validation.md",
                        "sha256": _sha256(sidecar.read_bytes()),
                    },
                },
            },
            final_bom_path=final_bom,
            workspace_root=tmp_path,
            validate_execution=lambda *_args, **_kwargs: None,
            validate_result=lambda *_args, **_kwargs: None,
            executed_result_factory=lambda value, **_kwargs: value,
            readiness_run_id=lambda _bom, article_hash: f"run-{article_hash[:8]}",
        )


def test_result_pair_rolls_back_first_install_when_second_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "final-readiness.json"
    receipt = tmp_path / "final-readiness-stage-receipt.json"
    real_link = os.link
    calls = 0

    def fail_second(source: str | Path, destination: str | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("forced receipt install failure")
        real_link(source, destination)

    monkeypatch.setattr(os, "link", fail_second)

    with pytest.raises(OSError, match="forced receipt"):
        persist_new_result_pair(output, {"result": True}, receipt, {"receipt": True})

    assert not output.exists()
    assert not receipt.exists()
    assert not list(tmp_path.glob("*.bundle.tmp"))


def test_result_pair_digests_both_staged_files_before_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from data_sources.modules.readiness import persistence

    output = tmp_path / "final-readiness.json"
    receipt = tmp_path / "final-readiness-stage-receipt.json"
    events: list[tuple[str, str]] = []
    real_hash = persistence._sha256_file
    real_link = os.link

    def record_hash(path: Path) -> str:
        events.append(("hash", path.name))
        return real_hash(path)

    def record_link(source: str | Path, destination: str | Path) -> None:
        events.append(("link", Path(destination).name))
        real_link(source, destination)

    monkeypatch.setattr(persistence, "_sha256_file", record_hash)
    monkeypatch.setattr(os, "link", record_link)

    persist_new_result_pair(output, {"result": True}, receipt, {"receipt": True})

    assert [kind for kind, _name in events[:3]] == ["hash", "hash", "link"]


def test_result_pair_collision_preserves_existing_destination(tmp_path: Path) -> None:
    output = _write(tmp_path / "final-readiness.json", "existing\n")
    receipt = tmp_path / "final-readiness-stage-receipt.json"

    with pytest.raises(ValueError, match="already exists"):
        persist_new_result_pair(output, {"result": True}, receipt, {"receipt": True})

    assert output.read_text(encoding="utf-8") == "existing\n"
    assert not receipt.exists()


def test_result_pair_rollback_never_deletes_replaced_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "final-readiness.json"
    receipt = tmp_path / "final-readiness-stage-receipt.json"
    real_link = os.link
    calls = 0

    def replace_then_fail(source: str | Path, destination: str | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            real_link(source, destination)
            return
        output.unlink()
        output.write_text("replacement\n", encoding="utf-8")
        raise OSError("forced receipt install failure")

    monkeypatch.setattr(os, "link", replace_then_fail)

    with pytest.raises(RuntimeError, match="could not safely remove"):
        persist_new_result_pair(output, {"result": True}, receipt, {"receipt": True})

    assert output.read_text(encoding="utf-8") == "replacement\n"
    assert not receipt.exists()


def test_real_landing_release_round_trip_without_orchestration_mocks(
    tmp_path: Path,
) -> None:
    paragraphs = [
        "Organize incoming work in one clear queue so coordinators review priorities, assign ownership, and keep the next action visible to the team.",
        "Give technicians a concise view of the work requested, the location, the contact details, and the notes they need before travel begins.",
        "Keep scheduling decisions easy to review by grouping urgent work, planned work, and follow-up tasks in a consistent operating rhythm.",
        "Use a simple handoff between office and field teams so updates remain visible without relying on a separate explanation or hidden process.",
        "Review each request before assignment, confirm that the scope is understandable, and record the next action in language the whole team follows.",
        "Build a repeatable dispatch routine around clear ownership, practical notes, and a shared view of what is ready to move forward.",
        "Keep the request, decision, and assigned owner together from intake through completion to limit avoidable back-and-forth.",
        "Show managers the work that needs attention and give each team member a focused, readable view of current work.",
        "Keep the process flexible enough for changing priorities while preserving the context behind each scheduling and assignment decision.",
        "Make daily coordination easier with a straightforward review step, an explicit owner, and a visible outcome for every accepted request.",
        "Support a calm operating cadence by separating ready work from incomplete requests and returning unclear items for useful clarification.",
        "Close the loop by recording the outcome, checking the response to the request, and making completed work easy to review later.",
    ]
    article = _write(
        tmp_path / "landing-pages" / "dispatch.md",
        "---\nartifact_type: landing_page\nbrand: AroFlo\npage_type: ppc\n"
        "conversion_goal: demo\ntitle: Clear Dispatch Workflows\n---\n"
        "# Reduce scheduling friction with a clear dispatch workflow\n\n"
        "Plan work around a visible next step. Choose a service that lets you **cancel any time.**\n\n"
        "[Book a demo today](#demo)\n\n"
        "## Keep work clear from intake to completion\n\n"
        + "\n\n".join(paragraphs[:6])
        + "\n\n- **Review** each request.\n- **Assign** one owner.\n- **Confirm** the next action.\n\n"
        "## Give every team member a useful handoff\n\n"
        + "\n\n".join(paragraphs[6:])
        + "\n\n[Schedule a demo today](#demo)\n\n"
        "See the workflow in context and decide whether it fits your operating model.\n\n"
        "[Book a demo now](#demo)\n",
    )
    sidecar = _write(
        tmp_path / "research" / "validation-dispatch.md",
        "# Validation\n\nNo proof-sensitive public claims are present.\n\n"
        "## Early Artifact Plan\n"
        "- Early artifact requirement: not applicable\n"
        "- Reason: This concise conversion page has no data deliverable that fits its purpose.\n",
    )

    result = run_artifact_release(
        article=article,
        run_id="landing-round-trip",
        proof_sidecar=sidecar,
        output_dir=tmp_path / "research" / "releases" / "landing-round-trip",
        workspace_root=tmp_path,
    )

    assert result.exit_code == 0
    authorization = load_publish_authorization(
        final_readiness_path=result.output_dir / "final-readiness.json",
        final_receipt_path=result.output_dir / "final-readiness-stage-receipt.json",
        release_manifest_path=result.output_dir / "release-manifest.json",
        workspace_root=tmp_path,
    )
    calls: list[bytes] = []
    returned = authorization.with_final_input_seal(
        lambda article_bytes, _inventory: calls.append(article_bytes) or "published"
    )
    assert returned == "published"
    assert calls == [article.read_bytes()]
