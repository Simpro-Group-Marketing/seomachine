"""Fail when changed Python files exceed the repository line ceiling."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_sources.modules.artifact_runtime.subprocesses import run_bounded_text_process


DEFAULT_LIMIT = 500


def physical_line_count(path: Path) -> int:
    with path.open("rb") as handle:
        return sum(1 for _ in handle)


def oversized_files(paths: Iterable[Path], *, limit: int) -> list[tuple[Path, int]]:
    rows = [(path, physical_line_count(path)) for path in paths if path.is_file()]
    return sorted(
        ((path, count) for path, count in rows if count > limit),
        key=lambda row: (-row[1], row[0].as_posix()),
    )


def changed_python_files(root: Path, *, base: str) -> list[Path]:
    tracked = _git_lines(
        root,
        "diff",
        "--name-only",
        "--diff-filter=ACMR",
        base,
        "--",
        "*.py",
    )
    untracked = _git_lines(
        root,
        "ls-files",
        "--others",
        "--exclude-standard",
        "--",
        "*.py",
    )
    return [root / path for path in sorted(set(tracked + untracked))]


def _git_lines(root: Path, *args: str) -> list[str]:
    completed = run_bounded_text_process(
        ["git", *args],
        cwd=root,
        timeout=30,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "git command failed")
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check added and modified Python files against a line ceiling."
    )
    parser.add_argument("--base", default="main")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    if args.limit <= 0:
        parser.error("--limit must be positive")
    root = args.root.resolve()
    failures = oversized_files(
        changed_python_files(root, base=args.base),
        limit=args.limit,
    )
    for path, count in failures:
        print(f"{path.relative_to(root).as_posix()}: {count} lines (limit {args.limit})")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
