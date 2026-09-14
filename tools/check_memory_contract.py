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
RESOURCE_LIMIT_RE = re.compile(r"(?m)^\| `([a-z][a-z0-9_]*)` \| ([0-9]+) \|$")


def _runtime_limits() -> dict[str, int]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from data_sources.modules.artifact_runtime.limits import (
        ARTICLE_MAX_BYTES,
        JSON_MAX_BYTES,
        SIDECAR_MAX_BYTES,
        SUBPROCESS_MAX_INPUT_BYTES,
        SUBPROCESS_MAX_OUTPUT_BYTES,
        SUBPROCESS_SPOOL_THRESHOLD_BYTES,
    )
    from data_sources.modules.bounded_io import HASH_CHUNK_BYTES
    from data_sources.modules.public_http import DEFAULT_HTTP_BATCH_POLICY
    from data_sources.modules.public_http.policies import MAX_CACHE_BYTES
    from tools.check_worker_metrics import DEFAULT_MAX_PEAK_RSS_BYTES

    network_budget = DEFAULT_HTTP_BATCH_POLICY.max_aggregate_response_bytes
    return {
        "article_max_bytes": ARTICLE_MAX_BYTES,
        "hash_chunk_bytes": HASH_CHUNK_BYTES,
        "http_batch_max_bytes": network_budget,
        "http_cache_max_bytes": MAX_CACHE_BYTES,
        "json_max_bytes": JSON_MAX_BYTES,
        "session_normalized_source_max_bytes": network_budget,
        "sidecar_max_bytes": SIDECAR_MAX_BYTES,
        "subprocess_spool_threshold_bytes": SUBPROCESS_SPOOL_THRESHOLD_BYTES,
        "subprocess_input_max_bytes": SUBPROCESS_MAX_INPUT_BYTES,
        "subprocess_stream_max_bytes": SUBPROCESS_MAX_OUTPUT_BYTES,
        "xdist_worker_peak_rss_max_bytes": DEFAULT_MAX_PEAK_RSS_BYTES,
    }


RUNTIME_LIMITS = _runtime_limits()


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
    errors.extend(_resource_limit_errors(content, expected=RUNTIME_LIMITS))
    errors.extend(_link_errors(content, root=root, tracked=tracked))
    if any(pattern.search(content) for pattern in CREDENTIAL_PATTERNS):
        errors.append("MEMORY.md contains a credential-like token")
    return sorted(set(errors))


def _resource_limit_errors(
    content: str,
    *,
    expected: dict[str, int],
) -> list[str]:
    section_match = re.search(
        r"(?ms)^## Resource limits\n(.*?)(?=^## |\Z)",
        content,
    )
    section = section_match.group(1) if section_match is not None else ""
    rows = RESOURCE_LIMIT_RE.findall(section)
    keys = [key for key, _ in rows]
    errors: list[str] = []
    for key, runtime_value in sorted(expected.items()):
        matches = [int(value) for row_key, value in rows if row_key == key]
        if len(matches) != 1:
            errors.append(f"MEMORY.md resource limit {key} must appear exactly once")
        for documented in matches:
            if documented != runtime_value:
                errors.append(
                    f"MEMORY.md resource limit {key} is {documented}; "
                    f"runtime is {runtime_value}"
                )
    for key in sorted(set(keys) - set(expected)):
        errors.append(f"MEMORY.md has unknown resource limit {key}")
    return errors


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
