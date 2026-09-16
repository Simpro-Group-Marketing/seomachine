from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from data_sources.modules import source_classification_preflight


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
