from __future__ import annotations

from pathlib import Path

from tools.check_memory_contract import REQUIRED_SECTIONS, memory_errors


def _memory(link: str = "[Evidence](evidence.md)") -> str:
    sections = "\n\n".join(f"## {heading}\n\n{link}" for heading in REQUIRED_SECTIONS)
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
