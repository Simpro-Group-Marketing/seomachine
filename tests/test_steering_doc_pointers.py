"""CLAUDE.md, AGENTS.md, and README.md point to canonical policy instead of restating it."""

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
STEERING = ("CLAUDE.md", "AGENTS.md")
CANONICAL_DOCS = (
    "context/aeo-geo-blog-strategy.md",
    "context/blog-editorial-strategy.md",
    ".claude/commands/publish-readiness.md",
)
RULES = tuple(sorted(path.name for path in (ROOT / ".claude" / "rules").glob("*.md")))
COMMANDS = tuple(sorted(path.stem for path in (ROOT / ".claude" / "commands").glob("*.md")))
RULE_DIR = {"CLAUDE.md": ".claude/rules", "AGENTS.md": ".agents/rules"}


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("name", STEERING)
def test_steering_files_link_every_canonical_policy_home(name: str) -> None:
    content = _read(name)
    for doc in CANONICAL_DOCS:
        assert doc in content, f"{name} must link {doc}"
    for rule in RULES:
        assert f"{RULE_DIR[name]}/{rule}" in content, f"{name} must link {rule}"


@pytest.mark.parametrize("name", STEERING)
def test_steering_files_keep_the_pointer_skeleton(name: str) -> None:
    content = _read(name)
    for heading in ("## Setup", "## Commands", "## Where policy lives", "## Non-negotiables"):
        assert heading in content
    assert len(content.splitlines()) <= 120, f"{name} is growing back into a policy copy"


@pytest.mark.parametrize("name", (*STEERING, "README.md"))
def test_steering_files_list_every_slash_command(name: str) -> None:
    content = _read(name)
    for command in COMMANDS:
        assert f"/{command}" in content, f"{name} must list /{command}"


def test_readme_points_to_the_canonical_policy_and_steering_files() -> None:
    readme = _read("README.md")
    for doc in (*CANONICAL_DOCS[:2], "CLAUDE.md", "AGENTS.md"):
        assert doc in readme
    assert "(NEW!)" not in readme


def test_customer_proof_rule_keeps_ledger_and_zero_recent_use_duties() -> None:
    """These duties lived only in the old steering files before they became pointers."""
    ledger_duty = "add a matching entry to `config/customer-proof-usage-ledger.json` before final handoff"
    for path in (".claude/rules/customer-proof.md", ".agents/rules/customer-proof.md"):
        rule = _read(path)
        assert ledger_duty in rule
        assert "Prefer an approved zero-recent-use source when one fits the same role." in rule
    strategy = _read("context/aeo-geo-blog-strategy.md")
    assert "matching entry must be added to `config/customer-proof-usage-ledger.json` before final handoff" in strategy
