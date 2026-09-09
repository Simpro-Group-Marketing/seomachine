import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").strip()


def _repository_development_section(content: str) -> str:
    match = re.search(
        r"(?ms)^## Repository Development Rules\n.*?(?=^## |\Z)",
        content,
    )
    assert match is not None, "Repository Development Rules section is missing"
    return match.group(0).strip()


def _cursor_rule_body(content: str) -> str:
    if content.startswith("---\n"):
        _, _, body = content.split("---\n", 2)
        return body.strip()
    return content.strip()


def test_agents_and_claude_share_the_same_repository_development_contract():
    agents = _repository_development_section(_read(ROOT / "AGENTS.md"))
    claude = _read(ROOT / ".claude" / "rules" / "repository-development.md")

    assert agents == claude


def test_agent_governance_mirrors_share_the_same_rule_body():
    agents = _read(ROOT / ".agents" / "rules" / "agent-governance.md")
    claude = _read(ROOT / ".claude" / "rules" / "agent-governance.md")
    cursor = _cursor_rule_body(_read(ROOT / ".cursor" / "rules" / "agent-governance.mdc"))

    assert agents == claude == cursor
