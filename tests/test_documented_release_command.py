import re
from pathlib import Path
from data_sources.modules.readiness.release_cli import _parser

ROOT = Path(__file__).resolve().parents[1]

def test_documented_release_wrapper_lists_every_required_flag():
    required = {a.option_strings[0] for a in _parser()._actions if a.required and a.option_strings}
    doc = (ROOT / ".claude/commands/publish-readiness.md").read_text(encoding="utf-8")
    blocks = re.findall(r"python -m data_sources\.modules\.blog_release\s[^\n]*", doc)
    assert len(blocks) >= 2
    for block in blocks:
        missing = sorted(f for f in required if f not in block)
        assert missing == [], f"publish-readiness.md invocation omits {missing}"
