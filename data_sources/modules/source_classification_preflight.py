"""Pre-draft external-source classification from committed decisions only."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlsplit

try:
    from .blog_assembly_contract import (
        atomic_write_json,
        load_json_object_snapshot,
        validate_governance_output_path,
    )
    from .source_support.classification import validate_source_classification_binding
    from .source_support.common import SOURCE_DECISIONS_PATH
    from .source_support.persistence import write_source_classification_artifact
except ImportError:  # pragma: no cover - supports direct script execution.
    from blog_assembly_contract import (
        atomic_write_json,
        load_json_object_snapshot,
        validate_governance_output_path,
    )
    from source_support.classification import validate_source_classification_binding
    from source_support.common import SOURCE_DECISIONS_PATH
    from source_support.persistence import write_source_classification_artifact


INVENTORY_SCHEMA = "simpro-source-candidate-inventory/v1"
REPORT_SCHEMA = "simpro-source-classification-preflight/v1"
_DECISION_MISSING_ERRORS = frozenset(
    {
        "source classification decision must resolve exactly once",
        "source classification decision is not approved",
        "source classification decision URL does not match",
        "source classification decision hostname does not match",
    }
)


@dataclass(frozen=True)
class SourceCandidate:
    """One external source URL and its optional approved decision identifier."""

    source_url: str
    decision_id: str | None


def build_preflight_report(
    inventory_path: str | Path,
    *,
    classification_directory: str | Path,
    decision_path: str | Path | None = None,
    workspace_root: str | Path,
) -> dict[str, Any]:
    """Classify approved candidates and return a pre-draft readiness report."""
    root = Path(workspace_root).resolve()
    candidates = load_source_candidate_inventory(inventory_path)
    directory = _workspace_path(classification_directory, root=root)
    registry = _workspace_path(
        decision_path or root / SOURCE_DECISIONS_PATH,
        root=root,
    )
    missing = _missing_authority_blockers(candidates, registry=registry)
    if missing:
        return _report(blockers=missing, artifacts=[])

    destinations = [
        (candidate, validate_governance_output_path(directory / _artifact_name(candidate.source_url)))
        for candidate in candidates
    ]
    artifacts: dict[str, dict[str, str | None]] = {}
    pending: list[tuple[SourceCandidate, Path]] = []
    for candidate, final_path in destinations:
        artifact = _current_classification_artifact(candidate, final_path, root=root)
        if artifact is None:
            pending.append((candidate, final_path))
        else:
            artifacts[candidate.source_url] = artifact

    if not pending:
        return _report(
            blockers=[],
            artifacts=[artifacts[candidate.source_url] for candidate in candidates],
        )

    staged: list[tuple[SourceCandidate, Path, Path]] = []
    directory.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        dir=directory.parent,
        prefix=".source-classification-preflight-",
    ) as temporary:
        temporary_directory = Path(temporary)
        for candidate, final_path in pending:
            staged_path = temporary_directory / final_path.name
            try:
                write_source_classification_artifact(
                    staged_path,
                    source_url=candidate.source_url,
                    decision_id=candidate.decision_id or "",
                    decision_path=registry,
                    workspace_root=root,
                )
            except ValueError as error:
                if str(error) in _DECISION_MISSING_ERRORS:
                    return _report(
                        blockers=[_missing_blocker(candidate.source_url)],
                        artifacts=[],
                    )
                return _report(
                    blockers=[_failure_blocker(candidate.source_url, error)],
                    artifacts=[],
                )
            staged.append((candidate, staged_path, final_path))
        directory.mkdir(parents=True, exist_ok=True)
        for _candidate, staged_path, final_path in staged:
            staged_path.replace(final_path)

    for candidate, _staged_path, final_path in staged:
        artifacts[candidate.source_url] = _artifact_record(candidate, final_path, root=root)
    return _report(
        blockers=[],
        artifacts=[artifacts[candidate.source_url] for candidate in candidates],
    )


def load_source_candidate_inventory(path: str | Path) -> tuple[SourceCandidate, ...]:
    """Load the strict, ordered source-candidate inventory contract."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"source candidate inventory is invalid: {error}") from error
    if not isinstance(payload, dict) or set(payload) != {"schema", "candidates"}:
        raise ValueError("source candidate inventory shape is invalid")
    if payload.get("schema") != INVENTORY_SCHEMA or not isinstance(payload["candidates"], list):
        raise ValueError("source candidate inventory schema is invalid")
    candidates = tuple(_parse_candidate(value) for value in payload["candidates"])
    urls = [candidate.source_url for candidate in candidates]
    if len(urls) != len(set(urls)):
        raise ValueError("source candidate inventory URLs must be unique")
    return candidates


def _parse_candidate(value: object) -> SourceCandidate:
    if not isinstance(value, dict) or set(value) not in (
        {"source_url"},
        {"source_url", "decision_id"},
    ):
        raise ValueError("source candidate row is invalid")
    source_url = value.get("source_url")
    if not isinstance(source_url, str) or not source_url or source_url.strip() != source_url:
        raise ValueError("source candidate source_url is invalid")
    parsed = urlsplit(source_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("source candidate source_url must be an external HTTP URL")
    decision_id = value.get("decision_id")
    if decision_id is not None and (
        not isinstance(decision_id, str)
        or not decision_id
        or decision_id.strip() != decision_id
    ):
        raise ValueError("source candidate decision_id is invalid")
    return SourceCandidate(source_url=source_url, decision_id=decision_id)


def _workspace_path(path: str | Path, *, root: Path) -> Path:
    candidate = Path(path)
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError("source classification preflight paths must stay in the workspace") from error
    return resolved


def _missing_authority_blockers(
    candidates: Sequence[SourceCandidate],
    *,
    registry: Path,
) -> list[dict[str, str]]:
    if registry.is_file():
        return [
            _missing_blocker(candidate.source_url)
            for candidate in candidates
            if candidate.decision_id is None
        ]
    return [_missing_blocker(candidate.source_url) for candidate in candidates]


def _artifact_name(source_url: str) -> str:
    digest = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
    return f"source-classification-{digest}.json"


def _current_classification_artifact(
    candidate: SourceCandidate,
    path: Path,
    *,
    root: Path,
) -> dict[str, str | None] | None:
    if not path.is_file():
        return None
    try:
        snapshot = load_json_object_snapshot(path, field="source classification artifact")
        payload = snapshot.payload
        source_class = payload.get("source_class")
        record_id = payload.get("registry", {}).get("record_id")
    except (AttributeError, ValueError):
        return None
    if source_class is None or record_id != candidate.decision_id:
        return None
    rule_id = validate_source_classification_binding(
        source_url=candidate.source_url,
        source_class=source_class,
        classification_artifact=path.relative_to(root).as_posix(),
        classification_hash=snapshot.sha256,
        base_path=root,
    )
    return None if rule_id is not None else _artifact_record(candidate, path, root=root)


def _artifact_record(
    candidate: SourceCandidate,
    path: Path,
    *,
    root: Path,
) -> dict[str, str | None]:
    return {
        "source_url": candidate.source_url,
        "decision_id": candidate.decision_id,
        "path": path.relative_to(root).as_posix(),
        "sha256": _sha256_file(path),
    }


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _missing_blocker(source_url: str) -> dict[str, str]:
    return {
        "rule_id": "source_classification_decision_missing",
        "source_url": source_url,
        "message": "No approved repository source classification decision is available for this URL.",
        "suggestion": "Record and commit an approved exact-URL source classification decision before drafting.",
    }


def _failure_blocker(source_url: str, error: ValueError) -> dict[str, str]:
    return {
        "rule_id": "source_classification_preflight_failed",
        "source_url": source_url,
        "message": f"Source classification authority could not be validated: {error}",
        "suggestion": "Repair the committed decision registry and rerun source classification preflight.",
    }


def _report(
    *,
    blockers: list[dict[str, str]],
    artifacts: list[dict[str, str | None]],
) -> dict[str, Any]:
    return {
        "schema": REPORT_SCHEMA,
        "ready_for_drafting": not blockers,
        "blockers": blockers,
        "classification_artifacts": artifacts,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Classify external source candidates before drafting."
    )
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--classification-directory", required=True)
    parser.add_argument("--decision-path")
    parser.add_argument("--workspace-root", default=".")
    parser.add_argument("--output", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.workspace_root).resolve()
    report = build_preflight_report(
        args.inventory,
        classification_directory=args.classification_directory,
        decision_path=args.decision_path,
        workspace_root=root,
    )
    atomic_write_json(args.output, report)
    return 0 if report["ready_for_drafting"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
