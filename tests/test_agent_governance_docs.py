from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_agents_md_points_codex_at_the_repository_development_rule_mirror():
    agents = _read(ROOT / "AGENTS.md")
    mirror = _read(ROOT / ".agents" / "rules" / "repository-development.md")
    claude = _read(ROOT / ".claude" / "rules" / "repository-development.md")

    assert ".agents/rules/repository-development.md" in agents
    assert mirror == claude
