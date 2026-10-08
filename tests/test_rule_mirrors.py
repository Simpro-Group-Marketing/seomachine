import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "sync_rule_mirrors.py"
RULE_DIRS = (".claude/rules", ".agents/rules", ".cursor/rules")


def _run(*args: str, root: Path | None = None):
    cmd = [sys.executable, str(TOOL), *args]
    if root is not None:
        cmd += ["--root", str(root)]
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def _copy_rules(tmp_path: Path) -> Path:
    for rel in RULE_DIRS:
        shutil.copytree(ROOT / rel, tmp_path / rel)
    return tmp_path


def _frontmatter(text: str) -> str:
    match = re.match(r"---\n.*?\n---\n", text, re.S)
    return match.group(0) if match else ""


def test_rule_mirrors_are_in_sync():
    result = _run("--check")
    assert result.returncode == 0, result.stdout + result.stderr


def test_sync_preserves_cursor_frontmatter(tmp_path):
    root = _copy_rules(tmp_path)
    path = root / ".cursor/rules/agent-governance.mdc"
    before = _frontmatter(path.read_text(encoding="utf-8"))
    path.write_text(before + "stale body\n", encoding="utf-8")

    assert _run(root=root).returncode == 0

    after = _frontmatter(path.read_text(encoding="utf-8"))
    assert after == before
    assert "alwaysApply: false" in after
    assert "globs:" in after and '"AGENTS.md"' in after
    assert _run("--check", root=root).returncode == 0


def test_check_names_stale_mirror(tmp_path):
    root = _copy_rules(tmp_path)
    stale = root / ".agents/rules/blog-schema.md"
    stale.write_text(stale.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")

    result = _run("--check", root=root)

    assert result.returncode == 1
    assert ".agents/rules/blog-schema.md" in result.stdout.replace("\\", "/")
    assert stale.read_text(encoding="utf-8").endswith("drift\n")
