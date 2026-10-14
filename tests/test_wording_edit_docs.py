from pathlib import Path

COMMANDS = Path(__file__).resolve().parents[1] / ".claude" / "commands"


def test_writing_commands_no_longer_document_wording_edit_receipts():
    """The production release re-checks every edit, so no receipt chain carries edits forward."""
    for name in ("write.md", "rewrite.md", "optimize.md", "publish-readiness.md"):
        content = (COMMANDS / name).read_text(encoding="utf-8")
        assert "Wording-only edit receipt" not in content, name
        assert "data_sources.modules.wording_edit" not in content, name
        assert "wording-edit receipt" not in content, name


def test_publish_readiness_requires_a_new_release_after_any_edit():
    content = (COMMANDS / "publish-readiness.md").read_text(encoding="utf-8")
    assert "Any edit after a pass therefore needs a new release." in content
