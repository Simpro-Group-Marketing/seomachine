"""Prepare governance evidence required before the native /write draft step."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Sequence

try:
    from .blog_assembly_contract import atomic_write_json, file_sha256, validate_governance_output_path
    from .source_classification_preflight import build_preflight_report
    from .source_support.common import SOURCE_DECISIONS_PATH
except ImportError:  # pragma: no cover - supports direct script execution.
    from blog_assembly_contract import atomic_write_json, file_sha256, validate_governance_output_path
    from source_classification_preflight import build_preflight_report
    from source_support.common import SOURCE_DECISIONS_PATH


SCHEMA = "simpro-blog-write-preflight/v1"


def build_write_preflight_report(
    draft_path: str | Path,
    *,
    source_candidate_inventory: str | Path,
    classification_directory: str | Path,
    source_classification_output: str | Path,
    decision_path: str | Path | None = None,
    workspace_root: str | Path,
) -> dict[str, Any]:
    """Create classification evidence before the native writer may create a draft."""
    root = Path(workspace_root).resolve()
    draft = _workspace_path(draft_path, root=root)
    inventory = _collision_path(source_candidate_inventory, root=root)
    decision = _workspace_path(
        decision_path or root / SOURCE_DECISIONS_PATH,
        root=root,
    )
    source_output = validate_governance_output_path(
        _workspace_path(source_classification_output, root=root),
        inputs=_source_inputs(inventory, decision),
    )
    classification = build_preflight_report(
        inventory,
        classification_directory=classification_directory,
        decision_path=decision,
        workspace_root=root,
    )
    atomic_write_json(source_output, classification)
    return {
        "schema": SCHEMA,
        "ready_for_drafting": classification["ready_for_drafting"],
        "blockers": classification["blockers"],
        "draft_path": draft.relative_to(root).as_posix(),
        "source_classification_preflight": {
            "path": source_output.relative_to(root).as_posix(),
            "sha256": file_sha256(source_output),
        },
    }


def _workspace_path(path: str | Path, *, root: Path) -> Path:
    candidate = Path(path)
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError("write preflight paths must stay in the workspace") from error
    return resolved


def _collision_path(path: str | Path, *, root: Path) -> Path:
    candidate = Path(path)
    return (candidate if candidate.is_absolute() else root / candidate).resolve()


def _source_inputs(
    inventory: str | Path,
    decision_path: str | Path,
) -> dict[str, str | Path]:
    return {
        "source_candidate_inventory": inventory,
        "source_decision_registry": decision_path,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare source-classification evidence before native blog drafting."
    )
    parser.add_argument("--draft", required=True)
    parser.add_argument("--source-candidate-inventory", required=True)
    parser.add_argument("--classification-directory", required=True)
    parser.add_argument("--source-classification-output", required=True)
    parser.add_argument("--decision-path")
    parser.add_argument("--workspace-root", default=".")
    parser.add_argument("--output", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.workspace_root).resolve()
    output = validate_governance_output_path(
        args.output,
        inputs={
            **_source_inputs(
                _collision_path(args.source_candidate_inventory, root=root),
                _workspace_path(
                    args.decision_path or root / SOURCE_DECISIONS_PATH,
                    root=root,
                ),
            ),
            "source_classification_output": args.source_classification_output,
        },
    )
    report = build_write_preflight_report(
        args.draft,
        source_candidate_inventory=args.source_candidate_inventory,
        classification_directory=args.classification_directory,
        source_classification_output=args.source_classification_output,
        decision_path=args.decision_path,
        workspace_root=root,
    )
    atomic_write_json(output, report)
    return 0 if report["ready_for_drafting"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
