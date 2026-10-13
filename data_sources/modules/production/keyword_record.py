"""Record a Semrush keyword decision only from numbers a saved transcript shows.

The transcript is bound by sha256, not by provenance: it must be the verbatim
captured Semrush page text. Each candidate's metrics must follow its keyword
within METRIC_WINDOW_CHARS characters of the collapsed transcript.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from data_sources.modules.blog_assembly_contract import atomic_write_json, canonical_json_sha256
from data_sources.modules.production.numbers import extract_numbers
from data_sources.modules.semrush_keyword_decision_guard import build_keyword_decision

SHORTLIST_SCHEMA = "simpro-keyword-shortlist/v1"
METRIC_WINDOW_CHARS = 1000
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


def _keyword_starts(collapsed: str, keyword: str) -> list[int]:
    pattern = rf"(?<![a-z0-9]){re.escape(_collapse(keyword))}(?![a-z0-9])"
    return [match.start() for match in re.finditer(pattern, collapsed)]


def _window_numbers(collapsed: str, start: int) -> frozenset[str]:
    end = collapsed.find(" ", start + METRIC_WINDOW_CHARS)
    return extract_numbers(collapsed[start:] if end == -1 else collapsed[start:end])


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


def _metric_numbers(keyword: str, row: Mapping[str, Any]) -> dict[str, frozenset[str]]:
    unknown = sorted(set(row) - {"keyword", *METRIC_FIELDS})
    if unknown:
        raise ValueError(f"keyword {keyword!r} has unsupported keys: {', '.join(unknown)}")
    numbers: dict[str, frozenset[str]] = {}
    for field in METRIC_FIELDS:
        if field not in row:
            continue
        value = row[field]
        valid = (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value >= 0
        )
        found = extract_numbers(str(value)) if valid else frozenset()
        if not found:
            raise ValueError(
                f"keyword {keyword!r} field {field} must be a finite non-negative "
                f"number, found {value!r}"
            )
        numbers[field] = found
    return numbers


def _check_candidate(row: Mapping[str, Any], collapsed: str) -> None:
    keyword = row.get("keyword")
    if not isinstance(keyword, str) or not keyword.strip():
        raise ValueError(f"candidate_metrics row has no keyword: {dict(row)!r}")
    metrics = _metric_numbers(keyword, row)
    starts = _keyword_starts(collapsed, keyword)
    if not starts:
        raise ValueError(f"keyword {keyword!r} does not appear in the transcript")
    best: list[str] | None = None
    for start in starts:
        window = _window_numbers(collapsed, start)
        missing = [field for field, found in metrics.items() if not found <= window]
        if not missing:
            return
        if best is None or len(missing) < len(best):
            best = missing
    raise ValueError(
        f"keyword {keyword!r} field {', '.join(best or [])} does not appear within "
        f"{METRIC_WINDOW_CHARS} characters after the keyword in the transcript"
    )


def _check_rows(value: Any, name: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        raise ValueError(f"{name} must be a list of rows")
    for row in value:
        if not isinstance(row, Mapping):
            raise ValueError(f"{name} rows must be objects")
    return list(value)


def _check_listed_keywords(rows: Sequence[Mapping[str, Any]], name: str, collapsed: str) -> None:
    for row in rows:
        keyword = row.get("keyword")
        if not isinstance(keyword, str) or not _keyword_starts(collapsed, keyword):
            raise ValueError(f"{name} keyword {keyword!r} does not appear in the transcript")


def _check_serp(finalists: Sequence[Mapping[str, Any]], collapsed: str) -> None:
    for finalist in finalists:
        for result in _check_rows(finalist.get("results", []), "serp_finalists results"):
            for field in ("url", "domain"):
                value = result.get(field)
                if not isinstance(value, str) or value.casefold() not in collapsed:
                    raise ValueError(
                        f"serp result {field} {value!r} for keyword "
                        f"{finalist.get('keyword')!r} does not appear in the transcript"
                    )


def _check_transcript_support(decision: Mapping[str, Any], transcript_text: str) -> None:
    collapsed = _collapse(transcript_text)
    for row in _check_rows(decision["candidate_metrics"], "candidate_metrics"):
        _check_candidate(row, collapsed)
    _check_serp(_check_rows(decision["serp_finalists"], "serp_finalists"), collapsed)
    for name in ("question_candidates", "related_candidates"):
        _check_listed_keywords(_check_rows(decision[name], name), name, collapsed)


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
    _check_transcript_support(decision, transcript_text)
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


def _distinct_paths(args: argparse.Namespace) -> bool:
    paths = [args.decision, args.transcript, args.output, args.shortlist_output]
    return len({os.path.normcase(str(path.resolve())) for path in paths}) == len(paths)


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
    if not _distinct_paths(args):
        print("keyword_record: decision, transcript, output and shortlist paths must be distinct", file=sys.stderr)
        return 2
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
