"""Record a Semrush keyword decision only from numbers a saved transcript shows."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from data_sources.modules.blog_assembly_contract import atomic_write_json, canonical_json_sha256
from data_sources.modules.production.numbers import extract_numbers
from data_sources.modules.semrush_keyword_decision_guard import build_keyword_decision

SHORTLIST_SCHEMA = "simpro-keyword-shortlist/v1"
METRIC_FIELDS = ("volume", "keyword_difficulty", "cpc", "competitive_density", "results")
_DECISION_KEYS = frozenset(
    {
        "brand", "market", "database", "collection_date", "source_boundary", "seed_terms",
        "connector_reports", "candidate_metrics", "serp_finalists", "question_candidates",
        "related_candidates", "selected_primary_keyword", "selected_secondary_keywords",
        "rejected_keywords", "selection_rationale",
    }
)
_INPUT_KEYS = _DECISION_KEYS | {"decision_rule"}


class TranscriptLocationError(ValueError):
    """Raised when the transcript is not inside the workspace root."""


def _collapse(text: str) -> str:
    return " ".join(text.split()).casefold()


def _check_input_keys(decision: Mapping[str, Any]) -> None:
    unknown = sorted(set(decision) - _INPUT_KEYS)
    if unknown:
        raise ValueError(f"unknown keyword decision input keys: {', '.join(unknown)}")
    missing = sorted(_INPUT_KEYS - set(decision))
    if missing:
        raise ValueError(f"missing keyword decision input keys: {', '.join(missing)}")
    rule = decision["decision_rule"]
    if not isinstance(rule, str) or not rule.strip():
        raise ValueError("decision_rule must be non-empty text")


def _check_candidate(row: Mapping[str, Any], collapsed: str, transcript_numbers: frozenset[str]) -> None:
    keyword = row.get("keyword")
    if not isinstance(keyword, str) or not keyword.strip():
        raise ValueError(f"candidate_metrics row has no keyword: {dict(row)!r}")
    if _collapse(keyword) not in collapsed:
        raise ValueError(f"keyword {keyword!r} does not appear in the transcript")
    for field in METRIC_FIELDS:
        if field in row and not extract_numbers(str(row[field])) <= transcript_numbers:
            raise ValueError(
                f"keyword {keyword!r} field {field} value {row[field]!r} "
                "does not appear in the transcript"
            )


def _check_transcript_support(candidates: Any, transcript_text: str) -> None:
    if not isinstance(candidates, Sequence) or isinstance(candidates, str):
        raise ValueError("candidate_metrics must be a list of rows")
    collapsed = _collapse(transcript_text)
    transcript_numbers = extract_numbers(transcript_text)
    for row in candidates:
        if not isinstance(row, Mapping):
            raise ValueError("candidate_metrics rows must be objects")
        _check_candidate(row, collapsed, transcript_numbers)


def _relative_posix(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise TranscriptLocationError(f"transcript {path} is not inside workspace root {root}") from exc


def record_keyword_decision(
    decision: Mapping[str, Any],
    transcript_text: str,
    *,
    workspace_root: Path,
    transcript_path: Path,
) -> dict[str, Any]:
    """Return the attested decision plus a shortlist bound to the transcript and decision."""
    _check_input_keys(decision)
    _check_transcript_support(decision["candidate_metrics"], transcript_text)
    transcript_ref = {
        "path": _relative_posix(Path(transcript_path), Path(workspace_root)),
        "sha256": hashlib.sha256(transcript_text.encode("utf-8")).hexdigest(),
    }
    arguments = {key: decision[key] for key in _DECISION_KEYS}
    payload = build_keyword_decision(**arguments, workspace_root=workspace_root)
    shortlist = {
        "schema": SHORTLIST_SCHEMA,
        "transcript": transcript_ref,
        "decision_sha256": canonical_json_sha256(payload),
        "primary": payload["selected_primary_keyword"],
        "secondary": payload["selected_secondary_keywords"],
        "candidates": payload["candidate_metrics"],
        "decision_rule": decision["decision_rule"],
    }
    return {"decision": payload, "shortlist": shortlist}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="keyword_record", description=__doc__)
    parser.add_argument("--decision", required=True, type=Path)
    parser.add_argument("--transcript", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--shortlist-output", required=True, type=Path)
    parser.add_argument("--workspace-root", type=Path, default=None)
    return parser


def _load_inputs(args: argparse.Namespace) -> tuple[Mapping[str, Any], str]:
    decision = json.loads(args.decision.read_text(encoding="utf-8"))
    if not isinstance(decision, dict):
        raise ValueError("decision input must be a JSON object")
    transcript = args.transcript.read_bytes().decode("utf-8")
    return decision, transcript


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exit_request:
        return int(exit_request.code or 0)
    root = (args.workspace_root or Path.cwd()).resolve()
    try:
        decision, transcript = _load_inputs(args)
    except (OSError, ValueError) as error:
        print(f"keyword_record: cannot read inputs: {error}", file=sys.stderr)
        return 2
    try:
        result = record_keyword_decision(
            decision, transcript, workspace_root=root, transcript_path=args.transcript
        )
    except TranscriptLocationError as error:
        print(f"keyword_record: {error}", file=sys.stderr)
        return 2
    except ValueError as error:
        print(f"keyword_record: {error}", file=sys.stderr)
        return 1
    try:
        atomic_write_json(args.output, result["decision"])
        atomic_write_json(args.shortlist_output, result["shortlist"])
    except (OSError, ValueError) as error:
        print(f"keyword_record: cannot write outputs: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
