from pathlib import Path

COMMANDS = Path(__file__).resolve().parents[1] / ".claude" / "commands"


def test_writing_commands_document_the_wording_edit_receipt():
    for name in ("write.md", "rewrite.md", "optimize.md"):
        content = (COMMANDS / name).read_text(encoding="utf-8")
        assert "## Wording-only edit receipt" in content, name
        assert "python -m data_sources.modules.wording_edit begin" in content, name
        assert "python -m data_sources.modules.wording_edit finish" in content, name
        assert "do not survive `/optimize`" in content, name


def test_publish_readiness_explains_wording_edit_receipt_order():
    content = (COMMANDS / "publish-readiness.md").read_text(encoding="utf-8")
    assert "wording-edit receipt" in content
