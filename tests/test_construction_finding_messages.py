"""Tests for findings_error_text helper."""
import pytest
from data_sources.modules.blog_assembly.contracts import findings_error_text
from data_sources.modules.blog_assembly.construction_support import validate_plan_fulfillment_inputs


def test_findings_error_text_keeps_rule_ids_and_messages() -> None:
    findings = [
        {"rule_id": "stage_receipt_evidence_unresolved", "message": "Receipt evidence humanizer_policy does not resolve to a current artifact or repository definition."},
        {"rule_id": "stage_receipt_previous_hash_mismatch", "message": "Receipt predecessor hash chain is broken."},
    ]
    text = findings_error_text("stage receipt chain is invalid", findings)
    assert text.startswith("stage receipt chain is invalid: stage_receipt_evidence_unresolved, stage_receipt_previous_hash_mismatch")
    assert "humanizer_policy does not resolve" in text
    assert "predecessor hash chain is broken" in text


def test_findings_error_text_limits_messages() -> None:
    findings = [{"rule_id": f"r{i}", "message": f"m{i}"} for i in range(9)]
    text = findings_error_text("x", findings, limit=3)
    assert "m2" in text and "m3" not in text and "6 more" in text


def test_plan_fulfillment_error_preserves_finding_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that plan fulfillment error raises include finding messages, not just rule IDs."""
    def mock_check_fulfillment(*args, **kwargs):
        return [
            {"rule_id": "fulfillment_keyword_mismatch", "message": "Article primary keyword does not match editorial plan keyword."},
            {"rule_id": "fulfillment_title_mismatch", "message": "Article title does not match editorial plan title."},
        ]

    monkeypatch.setattr(
        "data_sources.modules.blog_assembly.construction_support.check_fulfillment",
        mock_check_fulfillment
    )

    class MockSnapshot:
        def __init__(self, payload, sha256="abc123"):
            self.payload = payload
            self.sha256 = sha256

    class MockArticle:
        def __init__(self, raw):
            self.raw = raw

    with pytest.raises(ValueError) as exc_info:
        validate_plan_fulfillment_inputs(
            editorial_plan_snapshot=MockSnapshot({}),
            fulfillment_snapshot=MockSnapshot({}),
            article=MockArticle(""),
        )

    error_text = str(exc_info.value)
    assert "plan fulfillment is invalid" in error_text
    assert "fulfillment_keyword_mismatch" in error_text
    assert "fulfillment_title_mismatch" in error_text
    assert "Article primary keyword does not match" in error_text
    assert "Article title does not match" in error_text
