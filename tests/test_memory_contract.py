from __future__ import annotations

from pathlib import Path

from tools.check_memory_contract import (
    REQUIRED_SECTIONS,
    RUNTIME_LIMITS,
    memory_errors,
)


def _memory(link: str = "[Evidence](evidence.md)") -> str:
    limits = "\n".join(
        f"| `{key}` | {value} |" for key, value in sorted(RUNTIME_LIMITS.items())
    )
    values = {
        heading: (
            "| Limit key | Bytes |\n| --- | ---: |\n" + limits
            if heading == "Resource limits"
            else link
        )
        for heading in REQUIRED_SECTIONS
    }
    sections = "\n\n".join(
        f"## {heading}\n\n{values[heading]}" for heading in REQUIRED_SECTIONS
    )
    return f"# Architectural Memory\n\n{sections}\n"


def test_valid_compact_memory_with_tracked_evidence_passes(tmp_path: Path) -> None:
    (tmp_path / "evidence.md").write_text("evidence\n", encoding="utf-8")

    assert memory_errors(
        _memory(),
        repository_root=tmp_path,
        tracked_paths={"evidence.md"},
    ) == []


def test_memory_contract_rejects_missing_duplicate_and_untracked_sections(
    tmp_path: Path,
) -> None:
    (tmp_path / "evidence.md").write_text("evidence\n", encoding="utf-8")
    value = _memory().replace("## Architecture", "## Proof invariants")

    errors = memory_errors(
        value,
        repository_root=tmp_path,
        tracked_paths=set(),
    )

    assert "MEMORY.md must contain exactly one Architecture section" in errors
    assert "MEMORY.md must contain exactly one Proof invariants section" in errors
    assert "MEMORY.md evidence pointer is not Git-tracked: evidence.md" in errors


def test_memory_contract_rejects_escape_external_secret_and_size(tmp_path: Path) -> None:
    value = _memory("[Evidence](../outside.md)") + "sk-" + ("x" * 9000)

    errors = memory_errors(value, repository_root=tmp_path, tracked_paths=set())

    assert "MEMORY.md exceeds 8192 UTF-8 bytes" in errors
    assert "MEMORY.md contains a credential-like token" in errors
    assert "MEMORY.md evidence pointer escapes the repository: ../outside.md" in errors


def test_memory_contract_rejects_crlf_and_external_links(tmp_path: Path) -> None:
    errors = memory_errors(
        _memory("[Evidence](https://example.com/evidence)").replace("\n", "\r\n"),
        repository_root=tmp_path,
        tracked_paths=set(),
    )

    assert "MEMORY.md must use LF line endings" in errors
    assert "MEMORY.md evidence pointers must be repository-relative" in errors


def test_memory_contract_rejects_missing_stale_and_duplicate_runtime_limits(
    tmp_path: Path,
) -> None:
    value = _memory()
    key, expected = next(iter(sorted(RUNTIME_LIMITS.items())))
    row = f"| `{key}` | {expected} |"
    value = value.replace(row, f"| `{key}` | {expected + 1} |\n{row}")

    errors = memory_errors(value, repository_root=tmp_path, tracked_paths=set())

    assert f"MEMORY.md resource limit {key} must appear exactly once" in errors
    assert f"MEMORY.md resource limit {key} is {expected + 1}; runtime is {expected}" in errors


def test_memory_contract_rejects_unknown_runtime_limit(tmp_path: Path) -> None:
    value = _memory().replace(
        "| Limit key | Bytes |",
        "| Limit key | Bytes |\n| `invented_limit` | 123 |",
    )

    errors = memory_errors(value, repository_root=tmp_path, tracked_paths=set())

    assert "MEMORY.md has unknown resource limit invented_limit" in errors
