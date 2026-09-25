"""Command-line interface for standalone content scoring."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from .scorer import ContentScorer


def main(argv: Sequence[str] | None = None) -> int:
    """Score one Markdown file and print the existing text report."""
    parser = argparse.ArgumentParser(description="Score markdown content quality.")
    parser.add_argument("file_path", help="Path to the draft or rewrite markdown file.")
    parser.add_argument("--validate-urls", action="store_true")
    parser.add_argument("--validate-source-support", action="store_true")
    parser.add_argument("--proof-sidecar")
    parser.add_argument("--paa-workflow-mode")
    parser.add_argument("--paa-content-brief")
    parser.add_argument("--paa-answersocrates-blocker")
    parser.add_argument("--paa-expected-query")
    parser.add_argument("--paa-expected-collection-date")
    parser.add_argument("--paa-expected-run-id")
    parser.add_argument("--paa-artifact")
    parser.add_argument("--assembly-date")
    args = parser.parse_args(argv)
    try:
        content = Path(args.file_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: File not found: {args.file_path}")
        return 1

    scorer = ContentScorer()
    result = scorer.score(
        content,
        validate_urls=args.validate_urls,
        validate_source_support=args.validate_source_support,
        source_path=args.file_path,
        proof_sidecar=args.proof_sidecar,
        paa_workflow_mode=args.paa_workflow_mode,
        paa_content_brief=args.paa_content_brief,
        paa_answersocrates_blocker=args.paa_answersocrates_blocker,
        paa_expected_query=args.paa_expected_query,
        paa_expected_collection_date=args.paa_expected_collection_date,
        paa_expected_run_id=args.paa_expected_run_id,
        paa_artifact=args.paa_artifact,
        assembly_date=args.assembly_date,
    )
    print(scorer.format_report(result))
    return 0 if result["passed"] else 1


__all__ = ["main"]
