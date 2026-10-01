"""Bounded Git helpers for release-artifact scripts."""

from __future__ import annotations

from pathlib import Path

from .subprocesses import run_bounded_text_process


def repository_commit(
    repository_root: Path,
    *,
    short: bool = False,
    fallback: str | None = None,
    timeout: float = 10,
) -> str:
    """Return the current Git commit hash using bounded subprocess execution."""
    args = ["git", "rev-parse"]
    if short:
        args.append("--short")
    args.append("HEAD")
    completed = run_bounded_text_process(
        args,
        cwd=repository_root,
        timeout=timeout,
        max_output_bytes=4096,
        errors="replace",
    )
    if completed.returncode == 0:
        value = completed.stdout.strip()
        if value:
            return value
    if fallback is not None:
        return fallback
    detail = (completed.stderr or completed.stdout).strip()
    raise RuntimeError(detail or "git rev-parse HEAD failed")


__all__ = ["repository_commit"]
