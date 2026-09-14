"""PAA provenance cli responsibilities."""

from __future__ import annotations

# ruff: noqa: F401
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List, Mapping, Optional

from ..blog_assembly_contract import (
    atomic_write_json,
    canonical_json_sha256,
    canonical_snapshot_artifact,
    load_json_object_snapshot,
    resolve_artifact,
)
from ..execution_attestation import attest_mapping, verify_mapping_attestation
from ..faq_structure import detect_faq_structure
from ..guard_common import Finding, should_fail, summarize_findings
from ..proof_sidecar import compose_with_sidecar, load_sidecar_content
from .dependencies import PaaDependencies

from .contracts import (
    ANSWERSOCRATES_ARTIFACT_SCHEMA,
    WORKFLOW_MODES,
)


def _main(
    argv: Optional[List[str]] = None, *, dependencies: PaaDependencies | None = None
) -> int:
    from .results import evaluate_file

    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if raw_argv and raw_argv[0] == "record":
        return _record_main(raw_argv[1:], dependencies=dependencies)
    parser = argparse.ArgumentParser(
        description="Check FAQ questions for PAA provenance."
    )
    parser.add_argument("path", help="Markdown file to check")
    parser.add_argument(
        "--fail-on",
        default="error",
        choices=["error", "warning", "none"],
        help="Minimum finding severity that returns exit code 1",
    )
    parser.add_argument(
        "--proof-sidecar",
        help="Optional validation sidecar containing PAA/FAQ provenance.",
    )
    parser.add_argument(
        "--workflow-mode",
        default="new",
        choices=sorted(WORKFLOW_MODES),
        help="PAA source policy to apply.",
    )
    parser.add_argument(
        "--paa-artifact",
        help="Exact BOM-bound AnswerSocrates, brief, or user CSV artifact.",
    )
    parser.add_argument(
        "--content-brief",
        help="Bound content brief; its pre-picked PAA takes precedence for rewrites.",
    )
    parser.add_argument(
        "--answersocrates-blocker",
        help="Structured blocked AnswerSocrates run required for user_csv fallback.",
    )
    parser.add_argument(
        "--expected-query",
        help="Exact query required in a structured AnswerSocrates artifact.",
    )
    parser.add_argument(
        "--expected-collection-date",
        help="Exact ISO date required in a structured AnswerSocrates artifact.",
    )
    parser.add_argument(
        "--expected-run-id",
        help="Canonical article run ID required in a structured AnswerSocrates artifact.",
    )
    args = parser.parse_args(raw_argv)
    result = evaluate_file(
        args.path,
        fail_on=args.fail_on,
        proof_sidecar=args.proof_sidecar,
        workflow_mode=args.workflow_mode,
        content_brief=args.content_brief,
        answersocrates_blocker=args.answersocrates_blocker,
        expected_query=args.expected_query,
        expected_collection_date=args.expected_collection_date,
        expected_run_id=args.expected_run_id,
        paa_artifact=args.paa_artifact,
    )
    findings = list(result.findings)
    payload = {
        "path": args.path,
        "fail_on": args.fail_on,
        "summary": summarize_findings(findings),
        "findings": findings,
        "result": result.to_dict(),
    }
    print(json.dumps(payload, indent=2))
    return 1 if should_fail(findings, fail_on=args.fail_on) else 0


def _record_main(
    argv: List[str], *, dependencies: PaaDependencies | None = None
) -> int:
    from .collection import (
        build_answersocrates_artifact,
        collect_answersocrates_raw_capture,
        write_answersocrates_artifact,
    )

    parser = argparse.ArgumentParser(
        description="Record one browser-collected AnswerSocrates run."
    )
    parser.add_argument("--query", required=True)
    parser.add_argument("--collection-date", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--raw-capture-output", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    capture_path = collect_answersocrates_raw_capture(
        query=args.query,
        run_id=args.run_id,
        raw_capture_output=args.raw_capture_output,
        workspace_root=args.workspace_root,
        dependencies=dependencies,
    )
    artifact = build_answersocrates_artifact(
        raw_capture_path=capture_path,
        workspace_root=args.workspace_root,
        expected_query=args.query,
        expected_collection_date=args.collection_date,
        expected_run_id=args.run_id,
    )
    write_answersocrates_artifact(
        args.output, artifact, workspace_root=args.workspace_root
    )
    print(
        json.dumps(
            {
                "schema": ANSWERSOCRATES_ARTIFACT_SCHEMA,
                "status": artifact["status"],
                "output": str(Path(args.output)),
                "receipt_hash": artifact["run_receipt"]["receipt_hash"],
            },
            indent=2,
        )
    )
    return 0


__all__ = [
    "_main",
    "_record_main",
]
