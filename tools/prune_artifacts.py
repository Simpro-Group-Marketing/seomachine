"""Report or quarantine expired, unreferenced managed artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def main(argv: Sequence[str] | None = None) -> int:
    from data_sources.modules.artifact_runtime.retention import (
        apply_retention,
        plan_retention,
        purge_expired_quarantine,
        resume_retention,
        restore_quarantine,
    )

    parser = _parser()
    args = parser.parse_args(argv)
    root = args.workspace_root.resolve()
    try:
        if args.resume is not None:
            manifest = resume_retention(args.resume, workspace_root=root)
            _print({"status": "complete", "manifest": _relative(manifest, root)})
            return 0
        if args.restore is not None:
            restored = restore_quarantine(args.restore, workspace_root=root)
            _print({"status": "restored", "paths": [_relative(path, root) for path in restored]})
            return 0
        if args.purge_quarantine:
            paths = purge_expired_quarantine(root, now=datetime.now(timezone.utc), apply=args.apply)
            _print(
                {
                    "status": "purged" if args.apply else "planned",
                    "apply": args.apply,
                    "candidate_count": len(paths),
                    "candidates": [_relative(path, root) for path in paths],
                }
            )
            return 0
        now = datetime.now(timezone.utc)
        plan = plan_retention(
            root,
            now=now,
            research_retention_days=args.research_days,
            tracked_paths=_tracked_paths(root),
        )
        payload: dict[str, object] = {
            "status": "planned",
            "apply": args.apply,
            "candidate_count": len(plan.candidates),
            "candidates": [
                {
                    "path": _relative(item.path, root),
                    "sha256": item.sha256,
                    "bytes": item.byte_count,
                    "age_days": item.age_days,
                }
                for item in plan.candidates
            ],
        }
        if args.apply and plan.candidates:
            manifest = apply_retention(
                plan,
                workspace_root=root,
                now=now,
                quarantine_days=args.quarantine_days,
            )
            payload["status"] = "quarantined"
            payload["manifest"] = _relative(manifest, root)
        _print(payload)
        return 0
    except (OSError, UnicodeError, ValueError, RuntimeError) as error:
        print(f"artifact retention failed: {error}", file=sys.stderr)
        return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--research-days", type=int, default=90)
    parser.add_argument("--quarantine-days", type=int, default=14)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--restore", type=Path)
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--purge-quarantine", action="store_true")
    return parser


def _tracked_paths(root: Path) -> set[str]:
    from data_sources.modules.artifact_runtime.subprocesses import run_bounded_process

    with run_bounded_process(
        ["git", "ls-files", "-z"],
        cwd=root,
        timeout=30,
        max_output_bytes=8 * 1024 * 1024,
    ) as completed:
        if completed.returncode != 0:
            message = completed.stderr.read_text(max_bytes=1024 * 1024).strip()
            raise RuntimeError(message or "git ls-files failed")
        return {item for item in completed.stdout.read_text().split("\0") if item}


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def _print(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
