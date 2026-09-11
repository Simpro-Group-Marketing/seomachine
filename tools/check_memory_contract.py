"""Validate the repository's compact architectural MEMORY.md contract."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MEMORY_PATH = ROOT / "MEMORY.md"
MAX_BYTES = 8192
MAX_LINES = 100
MAX_WORDS = 750
REQUIRED_SECTIONS = (
    "Architecture",
    "Proof invariants",
    "Resource limits",
    "Evidence index",
    "Update discipline",
)
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
WORD_RE = re.compile(r"\b[\w'-]+\b", re.UNICODE)
CREDENTIAL_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"https?://[^/\s:@]+:[^/\s@]+@", re.IGNORECASE),
)


def memory_errors(
    content: str,
    *,
    repository_root: str | Path,
    tracked_paths: Iterable[str],
) -> list[str]:
    """Return deterministic validation errors for one MEMORY.md value."""
    root = Path(repository_root).resolve()
    tracked = {PurePosixPath(path).as_posix() for path in tracked_paths}
    errors: list[str] = []
    if len(content.encode("utf-8")) > MAX_BYTES:
        errors.append(f"MEMORY.md exceeds {MAX_BYTES} UTF-8 bytes")
    if len(content.splitlines()) > MAX_LINES:
        errors.append(f"MEMORY.md exceeds {MAX_LINES} physical lines")
    if len(WORD_RE.findall(content)) > MAX_WORDS:
        errors.append(f"MEMORY.md exceeds {MAX_WORDS} words")
    if "\r" in content:
        errors.append("MEMORY.md must use LF line endings")
    errors.extend(_section_errors(content))
    errors.extend(_link_errors(content, root=root, tracked=tracked))
    if any(pattern.search(content) for pattern in CREDENTIAL_PATTERNS):
        errors.append("MEMORY.md contains a credential-like token")
    return sorted(set(errors))


def _section_errors(content: str) -> list[str]:
    headings = re.findall(r"(?m)^## ([^\r\n]+)$", content)
    return [
        f"MEMORY.md must contain exactly one {section} section"
        for section in REQUIRED_SECTIONS
        if headings.count(section) != 1
    ]


def _link_errors(content: str, *, root: Path, tracked: set[str]) -> list[str]:
    errors: list[str] = []
    for raw_target in LINK_RE.findall(content):
        target = raw_target.strip()
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or target.startswith(("/", "\\")):
            errors.append("MEMORY.md evidence pointers must be repository-relative")
            continue
        if parsed.query:
            errors.append(f"MEMORY.md evidence pointer cannot contain a query: {target}")
            continue
        relative = parsed.path
        try:
            resolved = (root / Path(relative)).resolve()
            normalized = resolved.relative_to(root).as_posix()
        except ValueError:
            errors.append(f"MEMORY.md evidence pointer escapes the repository: {target}")
            continue
        if not resolved.is_file():
            errors.append(f"MEMORY.md evidence pointer is missing: {relative}")
        elif normalized not in tracked:
            errors.append(f"MEMORY.md evidence pointer is not Git-tracked: {relative}")
    return errors


def _tracked_paths(root: Path) -> set[str]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from data_sources.modules.artifact_runtime.subprocesses import run_bounded_process

    with run_bounded_process(
        ["git", "ls-files", "-z"],
        cwd=root,
        timeout=30,
        max_output_bytes=8 * 1024 * 1024,
    ) as completed:
        if completed.returncode != 0:
            message = completed.stderr.read_text(max_bytes=1024 * 1024).strip()
            raise ValueError(message or "git ls-files failed")
        return {
            value
            for value in completed.stdout.read_text().split("\0")
            if value
        }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory", type=Path, default=MEMORY_PATH)
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    root = args.repository_root.resolve()
    try:
        content = args.memory.read_bytes().decode("utf-8")
        errors = memory_errors(
            content,
            repository_root=root,
            tracked_paths=_tracked_paths(root),
        )
    except (OSError, UnicodeError, ValueError) as error:
        print(f"memory contract check failed: {error}", file=sys.stderr)
        return 2
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
