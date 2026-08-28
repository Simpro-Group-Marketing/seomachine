from unittest.mock import patch

from data_sources.modules.fred_authority_guard import check_content
import pytest

from data_sources.modules.fred_authority_selector import (
    FredAuthorityDataError,
    select_fred_authority,
)
from data_sources.modules.vault_claim_receipts import ApprovedClaim, ValidatedClaimSet


def _claim(
    *,
    selector_id: str = "FVMI-001",
    claim_id: str = "claim-fred-FVMI-001",
    claim_type: str = "fred-authority-joined-v2",
    authority_resource_id: str = "res-fred-authority-001",
) -> ApprovedClaim:
    return ApprovedClaim(
        claim_id=claim_id,
        selector_id=selector_id,
        assertion="Fred Voccola explains workforce technology for skilled trades.",
        use_mode="authority_support",
        brand_scope=("Simpro",),
        source_hash="a" * 64,
        public_url="https://example.com/skilled-trades",
        approval_source="connector_claim_result",
        receipt_revision="receipt-revision-1",
        claim_type=claim_type,
        authority_resource_id=authority_resource_id,
        evidence_anchor="indexes/fred-voccola-media-inventory.csv#FVMI-001",
    )


def _selection_block(**overrides: str) -> str:
    fields = {
        "Selector command": "python data_sources/modules/fred_authority_selector.py topic --slate",
        "Evaluation status": "completed",
        "Top candidates": "[FVMI-001]",
        "Selected": "[FVMI-001]",
        "Context receipt": "context-receipt.json",
        "Claim IDs": "[claim-fred-FVMI-001]",
        "Receipt revision": "receipt-revision-1",
        "Approval source": "connector_claim_result",
        "Fit decision": "The selected source directly supports the workforce technology discussion.",
        "Intended use": "inline_citation",
        "Target section": "Workforce technology",
        "Authority row": "[res-fred-authority-001]",
        "Public URL": "https://example.com/skilled-trades",
        "Evidence status": "receipt_approved",
        "Verification method": "not_applicable",
        "Evidence excerpt": "not applicable",
        "Timestamp or locator": "not applicable",
        "Playback verified": "not_applicable",
        "Exact quote": "not applicable",
        "Embed decision": "no",
        "VideoObject": "not applicable",
    }
    fields.update(overrides)
    return "## Fred Voccola Authority Selection\n" + "\n".join(
        f"- {key}: {value}" for key, value in fields.items()
    )


def test_selector_uses_receipt_claims_without_legacy_env_or_raw_vault_files(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("SIMPRO_BRAND_CONTEXT_VAULT", str(tmp_path / "legacy-vault"))
    claims = ValidatedClaimSet([_claim()])

    with patch(
        "data_sources.modules.fred_authority_selector.load_validated_claim_set",
        return_value=claims,
    ):
        results = select_fred_authority(
            "skilled trades workforce",
            vault_root=tmp_path / "empty-root",
            context_pack=tmp_path / "context-pack.json",
            context_receipt=tmp_path / "context-receipt.json",
        )

    assert results[0]["inventory_id"] == "FVMI-001"
    assert results[0]["authority_id"] == "res-fred-authority-001"
    assert results[0]["evidence_status"] == "receipt_approved"


def test_selector_filters_non_fred_and_incomplete_receipt_claims(tmp_path):
    claims = ValidatedClaimSet(
        [
            _claim(claim_id="claim-other", claim_type="named-feature-status-v1"),
            _claim(
                selector_id="FVMI-002",
                claim_id="claim-fred-FVMI-002",
                authority_resource_id="",
            ),
        ]
    )

    with patch(
        "data_sources.modules.fred_authority_selector.load_validated_claim_set",
        return_value=claims,
    ):
        results = select_fred_authority(
            "workforce",
            context_pack=tmp_path / "context-pack.json",
            context_receipt=tmp_path / "context-receipt.json",
        )

    assert results == []


def test_selector_fails_closed_when_context_receipt_is_unavailable():
    with patch(
        "data_sources.modules.fred_authority_selector.load_validated_claim_set",
        return_value=ValidatedClaimSet(blocker="connector unavailable"),
    ):
        with pytest.raises(FredAuthorityDataError, match="connector unavailable"):
            select_fred_authority("workforce")


def test_selector_forwards_explicit_root_to_receipt_validation(tmp_path):
    calls = []

    def loader(context_pack, context_receipt, *, vault_root=None):
        calls.append((context_pack, context_receipt, vault_root))
        return ValidatedClaimSet([_claim()])

    pack = tmp_path / "pack.json"
    receipt = tmp_path / "receipt.json"
    with patch(
        "data_sources.modules.fred_authority_selector.load_validated_claim_set",
        new=loader,
    ):
        select_fred_authority(
            "workforce",
            vault_root=tmp_path,
            context_pack=pack,
            context_receipt=receipt,
        )

    assert calls == [(pack, receipt, tmp_path)]


def test_guard_validates_selected_source_from_receipt_without_using_evidence_anchor(
    tmp_path,
):
    claims = ValidatedClaimSet([_claim()])
    article = (
        "## Workforce technology\n\n"
        "Fred Voccola discusses workforce technology in this "
        "[skilled trades workforce interview](https://example.com/skilled-trades).\n"
    )

    with patch(
        "data_sources.modules.fred_authority_guard.load_validated_claim_set",
        return_value=claims,
    ):
        findings = check_content(
            article,
            proof_content=_selection_block(),
            vault_root=tmp_path / "empty-root",
            context_pack=tmp_path / "context-pack.json",
            context_receipt=tmp_path / "context-receipt.json",
        )

    assert findings == []


def test_guard_fails_closed_when_selected_claim_is_not_receipt_approved(tmp_path):
    with patch(
        "data_sources.modules.fred_authority_guard.load_validated_claim_set",
        return_value=ValidatedClaimSet([]),
    ):
        findings = check_content(
            "Article without public Fred evidence.",
            proof_content=_selection_block(),
            context_pack=tmp_path / "context-pack.json",
            context_receipt=tmp_path / "context-receipt.json",
        )

    assert any(item["rule_id"] == "fred_authority_id_unknown" for item in findings)
