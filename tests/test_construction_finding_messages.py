"""Tests for findings_error_text helper."""
from data_sources.modules.blog_assembly.contracts import findings_error_text


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

