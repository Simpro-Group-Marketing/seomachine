import re
from pathlib import Path

from data_sources.modules.production.release import _parser

ROOT = Path(__file__).resolve().parents[1]


def test_documented_release_command_lists_every_option():
    doc = (ROOT / ".claude/commands/publish-readiness.md").read_text(encoding="utf-8")
    blocks = re.findall(r"python -m data_sources\.modules\.production\.release\s[^\n]*", doc)
    assert blocks, "publish-readiness.md must show the production release invocation"
    options = {a.option_strings[0] for a in _parser()._actions if a.option_strings and a.dest != "help"}
    missing = sorted(option for option in options if not any(option in block for block in blocks))
    assert missing == [], f"publish-readiness.md invocation omits {missing}"
    assert "data_sources.modules.blog_release" not in doc
