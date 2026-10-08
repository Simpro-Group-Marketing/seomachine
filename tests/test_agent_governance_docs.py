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


def test_agents_and_claude_share_the_same_repository_development_contract():
    agents = _repository_development_section(_read(ROOT / "AGENTS.md"))
    claude = _read(ROOT / ".claude" / "rules" / "repository-development.md")

    assert agents == claude

