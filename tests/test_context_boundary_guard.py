import json
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


def test_rg_invariant_has_no_active_references_to_deleted_context_mirrors() -> None:
    pattern = (
        r"context/(brand-voice\.md|features\.md|lightning-positioning\.md|"
        r"style-guide\.md|customer-proof-index\.json|"
        r"customer-proof-usage-ledger\.json|customer-proof-intake[^\s`'\"),]*|"
        r"competitor-analysis\.md|reference/competitors/battlecards|"
        r"reference/writing-examples)"
    )
    active_paths = [
        "AGENTS.md",
        "CLAUDE.md",
        "README.md",
        "QUICK-START.md",
        "NEXT-STEPS.md",
        "context",
        ".claude/agents",
        ".claude/commands",
        ".claude/skills",
        ".agents",
        "scripts",
    ]
    existing_paths = [path for path in active_paths if (ROOT / path).exists()]
    result = subprocess.run(
        [
            "rg",
            "-n",
            "--glob",
            "!.claude/worktrees/**",
            pattern,
            *existing_paths,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1, result.stdout
    assert result.stdout == ""
