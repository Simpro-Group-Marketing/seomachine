"""Run every release check once and report all blockers together."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Sequence

try:
    from .blog_assembly_contract import atomic_write_json
    from .readiness.release_cli import _parser
    from .release_workflow.precheck_sweep import run_release_sweep
except ImportError:  # pragma: no cover - supports direct script execution.
    from blog_assembly_contract import atomic_write_json
    from readiness.release_cli import _parser
    from release_workflow.precheck_sweep import run_release_sweep


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    parser.description = "Run every release check once and report all blockers together."
    for action in parser._actions:  # the sweep writes no release directory
        if action.dest == "output_dir":
            action.required = False
    parser.add_argument("--sweep-output", required=True)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--include-slow", action="store_true")
    args = parser.parse_args(argv)
    report = run_release_sweep(
        args,
        workspace_root=Path(args.workspace_root),
        offline=args.offline,
        include_slow=args.include_slow,
    )
    atomic_write_json(Path(args.sweep_output), report)
    for row in report["findings"]:
        print(f"{row['severity']}\t{row['check']}\t{row['rule_id']}\t{row['message'][:160]}")
    print(json.dumps({
        "passed": report["passed"],
        "findings": len(report["findings"]),
        "skipped": len(report["skipped"]),
        "elapsed_seconds": report["elapsed_seconds"],
    }))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
