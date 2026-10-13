import json
import re
import subprocess
from pathlib import Path

from data_sources.modules.context_boundary_guard import (
    ALLOWED_CATEGORIES,
    POLICY_SCHEMA,
    check_content,
)


ROOT = Path(__file__).resolve().parents[1]


def test_current_context_boundary_policy_passes_for_workspace() -> None:
    findings = check_content(workspace_root=ROOT)

    assert findings == []


def test_context_policy_registers_every_current_context_file_with_allowed_category() -> None:
    policy_path = ROOT / "context" / "context-policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    registered = {
        str(path).replace("\\", "/").strip().lstrip("./"): row
        for path, row in policy["files"].items()
    }
    context_files = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "context").rglob("*")
        if path.is_file()
    }

    assert policy["schema"] == POLICY_SCHEMA
    assert set(registered) == context_files
    for row in registered.values():
        category = row.get("category") if isinstance(row, dict) else row
        assert category in ALLOWED_CATEGORIES


DELETED_CONTEXT_MIRROR_RE = re.compile(
    r"context/(brand-voice\.md|features\.md|lightning-positioning\.md|"
    r"style-guide\.md|customer-proof-index\.json|"
    r"customer-proof-usage-ledger\.json|customer-proof-intake[^\s`'\"),]*|"
    r"competitor-analysis\.md|reference/competitors/battlecards|"
    r"reference/writing-examples)"
)
ACTIVE_PATHS = (
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "QUICK-START.md",
    "NEXT-STEPS.md",
    "context/",
    ".claude/agents/",
    ".claude/commands/",
    ".claude/skills/",
    ".agents/",
    ".cursor/",
    "scripts/",
)


def _active_files() -> list[str]:
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    return sorted(
        path
        for path in {entry for entry in listed.split("\x00") if entry}
        if path.startswith(ACTIVE_PATHS)
        and not path.startswith(".claude/worktrees/")
        and (ROOT / path).is_file()
    )


def _deleted_mirror_references() -> list[str]:
    violations = []
    for path in _active_files():
        text = (ROOT / path).read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if DELETED_CONTEXT_MIRROR_RE.search(line):
                violations.append(f"{path}:{lineno}: {line.strip()}")
    return violations


def test_active_docs_have_no_references_to_deleted_context_mirrors() -> None:
    assert _deleted_mirror_references() == []
