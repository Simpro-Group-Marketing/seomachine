from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from data_sources.modules import source_classification_preflight
from data_sources.modules.source_support import persistence


SOURCE_URL = "https://example.com/field-service-guidance"
DECISION_ID = "source:example-guidance"


def _run_git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True)


def _write_inventory(root: Path, candidates: list[dict[str, str]]) -> Path:
    path = root / "research" / "source-candidates.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "simpro-source-candidate-inventory/v1",
                "candidates": candidates,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def _commit_approved_decision(root: Path) -> Path:
    path = root / "context" / "source-classification-decisions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "simpro-source-classification-decisions/v1",
                "revision": "test-revision-1",
                "decisions": [
                    {
                        "decision_id": DECISION_ID,
                        "status": "approved",
                        "source_url": SOURCE_URL,
                        "hostname": "example.com",
                        "source_class": "non_competing_expert",
                        "publisher_relationship": "independent",
                    }
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    _run_git(root, "init", "-q")
    _run_git(root, "config", "user.email", "tests@example.com")
    _run_git(root, "config", "user.name", "Tests")
    _run_git(root, "add", "context/source-classification-decisions.json")
    _run_git(root, "commit", "-qm", "approve source decision")
    return path


def test_preflight_emits_one_classification_from_an_approved_committed_decision(
    tmp_path: Path,
) -> None:
    inventory = _write_inventory(
        tmp_path,
        [{"source_url": SOURCE_URL, "decision_id": DECISION_ID}],
    )
    decision_path = _commit_approved_decision(tmp_path)

    report = source_classification_preflight.build_preflight_report(
        inventory,
        classification_directory=tmp_path / "research" / "source-classifications",
        decision_path=decision_path,
        workspace_root=tmp_path,
    )

    artifact = tmp_path / report["classification_artifacts"][0]["path"]
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert report == {
        "schema": "simpro-source-classification-preflight/v1",
        "ready_for_drafting": True,
        "blockers": [],
        "classification_artifacts": [
            {
                "source_url": SOURCE_URL,
                "decision_id": DECISION_ID,
                "path": "research/source-classifications/"
                + "source-classification-"
                + hashlib.sha256(SOURCE_URL.encode("utf-8")).hexdigest()
                + ".json",
                "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            }
        ],
    }
    assert payload["source_url"] == SOURCE_URL
    assert payload["source_class"] == "non_competing_expert"
    assert payload["registry"]["record_id"] == DECISION_ID


def test_preflight_reports_missing_decision_without_writing_a_classification(
    tmp_path: Path,
) -> None:
    inventory = _write_inventory(
        tmp_path,
        [{"source_url": SOURCE_URL, "decision_id": DECISION_ID}],
    )
    output = tmp_path / "research" / "preflight.json"

    exit_code = source_classification_preflight.main(
        [
            "--inventory",
            str(inventory),
            "--classification-directory",
            str(tmp_path / "research" / "source-classifications"),
            "--decision-path",
            str(tmp_path / "context" / "source-classification-decisions.json"),
            "--workspace-root",
            str(tmp_path),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 1
    assert json.loads(output.read_text(encoding="utf-8")) == {
        "schema": "simpro-source-classification-preflight/v1",
        "ready_for_drafting": False,
        "blockers": [
            {
                "rule_id": "source_classification_decision_missing",
                "source_url": SOURCE_URL,
                "message": "No approved repository source classification decision is available for this URL.",
                "suggestion": "Record and commit an approved exact-URL source classification decision before drafting.",
            }
        ],
        "classification_artifacts": [],
    }
    assert not (tmp_path / "research" / "source-classifications").exists()


def test_preflight_requires_the_approved_decision_to_match_the_exact_url(
    tmp_path: Path,
) -> None:
    inventory = _write_inventory(
        tmp_path,
        [{"source_url": SOURCE_URL + "/", "decision_id": DECISION_ID}],
    )
    decision_path = _commit_approved_decision(tmp_path)

    report = source_classification_preflight.build_preflight_report(
        inventory,
        classification_directory=tmp_path / "research" / "source-classifications",
        decision_path=decision_path,
        workspace_root=tmp_path,
    )

    assert report["ready_for_drafting"] is False
    assert report["blockers"][0]["rule_id"] == "source_classification_decision_missing"
    assert report["blockers"][0]["source_url"] == SOURCE_URL + "/"
    assert report["classification_artifacts"] == []


def test_preflight_keeps_committed_registry_validation_intact(tmp_path: Path) -> None:
    inventory = _write_inventory(
        tmp_path,
        [{"source_url": SOURCE_URL, "decision_id": DECISION_ID}],
    )
    decision_path = _commit_approved_decision(tmp_path)
    decision_path.write_text(decision_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    report = source_classification_preflight.build_preflight_report(
        inventory,
        classification_directory=tmp_path / "research" / "source-classifications",
        decision_path=decision_path,
        workspace_root=tmp_path,
    )

    assert report["ready_for_drafting"] is False
    assert report["blockers"][0]["rule_id"] == "source_classification_preflight_failed"
    assert report["classification_artifacts"] == []


def test_preflight_reuses_a_current_classification_on_an_identical_repeat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inventory = _write_inventory(
        tmp_path,
        [{"source_url": SOURCE_URL, "decision_id": DECISION_ID}],
    )
    decision_path = _commit_approved_decision(tmp_path)
    output = tmp_path / "research" / "preflight.json"
    classification_directory = tmp_path / "research" / "source-classifications"
    arguments = [
        "--inventory", str(inventory),
        "--classification-directory", str(classification_directory),
        "--decision-path", str(decision_path),
        "--workspace-root", str(tmp_path),
        "--output", str(output),
    ]
    timestamps = iter(["2026-09-16T12:00:00Z", "2026-09-16T12:00:01Z"])
    monkeypatch.setattr(persistence, "_utc_timestamp_now", lambda: next(timestamps))

    assert source_classification_preflight.main(arguments) == 0
    first_report = output.read_bytes()
    artifact = next(classification_directory.glob("*.json"))
    first_artifact = artifact.read_bytes()

    assert source_classification_preflight.main(arguments) == 0

    assert output.read_bytes() == first_report
    assert artifact.read_bytes() == first_artifact


def test_preflight_blocks_an_omitted_decision_id_when_registry_exists(
    tmp_path: Path,
) -> None:
    inventory = _write_inventory(tmp_path, [{"source_url": SOURCE_URL}])
    decision_path = _commit_approved_decision(tmp_path)

    report = source_classification_preflight.build_preflight_report(
        inventory,
        classification_directory=tmp_path / "research" / "source-classifications",
        decision_path=decision_path,
        workspace_root=tmp_path,
    )

    assert report["ready_for_drafting"] is False
    assert report["blockers"][0]["rule_id"] == "source_classification_decision_missing"
    assert not (tmp_path / "research" / "source-classifications").exists()


def test_preflight_does_not_promote_partial_classifications(tmp_path: Path) -> None:
    second_url = "https://example.com/second-source"
    inventory = _write_inventory(
        tmp_path,
        [
            {"source_url": SOURCE_URL, "decision_id": DECISION_ID},
            {"source_url": second_url, "decision_id": "source:missing"},
        ],
    )
    decision_path = _commit_approved_decision(tmp_path)
    classification_directory = tmp_path / "research" / "source-classifications"

    report = source_classification_preflight.build_preflight_report(
        inventory,
        classification_directory=classification_directory,
        decision_path=decision_path,
        workspace_root=tmp_path,
    )

    assert report["ready_for_drafting"] is False
    assert report["blockers"][0]["rule_id"] == "source_classification_decision_missing"
    assert report["blockers"][0]["source_url"] == second_url
    assert report["classification_artifacts"] == []
    assert not classification_directory.exists()


@pytest.mark.parametrize("directory", ["drafts", "rewrites", "published", "review-required"])
def test_preflight_rejects_protected_classification_destinations(
    tmp_path: Path,
    directory: str,
) -> None:
    inventory = _write_inventory(
        tmp_path,
        [{"source_url": SOURCE_URL, "decision_id": DECISION_ID}],
    )
    decision_path = _commit_approved_decision(tmp_path)
    classification_directory = tmp_path / directory / "source-classifications"

    with pytest.raises(ValueError, match="public article directory"):
        source_classification_preflight.build_preflight_report(
            inventory,
            classification_directory=classification_directory,
            decision_path=decision_path,
            workspace_root=tmp_path,
        )

    assert not classification_directory.exists()
