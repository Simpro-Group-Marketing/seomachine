from tests.fixture_text import fixture_text

import json
import os
from unittest.mock import patch

from data_sources.modules.named_feature_status_guard import check_content, main
from data_sources.modules.vault_claim_receipts import ApprovedClaim, ValidatedClaimSet


STATUS_TABLE = fixture_text("content_evidence:test_named_feature_topology-9-1")
ARTICLE = (
    "# AI workflows\n\n"
    "[Lightning](https://www.simprogroup.com/lightning) connects AI workflows "
    "to Simpro data."
)


def approved_claims() -> ValidatedClaimSet:
    return ValidatedClaimSet(
        [
            ApprovedClaim(
                claim_id="claim-lightning-LCUR-0001",
                selector_id="LCUR-0001",
                assertion="Lightning connects approved Simpro AI workflows.",
                use_mode="public_paraphrase",
                brand_scope=("Simpro",),
                source_hash="a" * 64,
                public_url="https://www.simprogroup.com/lightning",
                approval_source="connector_claim_result",
                receipt_revision="receipt-1",
                authority_resource_id="res-11111111111111111111111111111111",
            )
        ],
        receipt_revision="receipt-1",
    )


def test_receipt_approved_claim_passes_without_legacy_topology(tmp_path):
    legacy_root = tmp_path / "legacy-root-without-indexes"
    legacy_root.mkdir()

    with patch.dict(
        os.environ,
        {"SIMPRO_BRAND_CONTEXT_VAULT": str(legacy_root)},
        clear=False,
    ), patch(
        "data_sources.modules.named_feature_status_guard.load_validated_claim_set",
        return_value=approved_claims(),
    ):
        findings = check_content(
            ARTICLE,
            proof_content=STATUS_TABLE,
            context_pack="context-pack.json",
            context_receipt="context-receipt.json",
        )

    assert findings == []


def test_explicit_root_is_delegated_to_validated_claim_loader(tmp_path):
    explicit_root = tmp_path / "configured-vault-root"
    explicit_root.mkdir()

    with patch(
        "data_sources.modules.named_feature_status_guard.load_validated_claim_set",
        return_value=approved_claims(),
    ) as loader:
        findings = check_content(
            ARTICLE,
            proof_content=STATUS_TABLE,
            vault_path=explicit_root,
            context_pack="context-pack.json",
            context_receipt="context-receipt.json",
        )

    assert findings == []
    assert loader.call_args.kwargs["vault_root"] == explicit_root


def test_claim_absent_from_validated_receipt_fails_closed(tmp_path):
    legacy_root = tmp_path / "legacy-root-without-indexes"
    legacy_root.mkdir()

    with patch.dict(
        os.environ,
        {"SIMPRO_BRAND_CONTEXT_VAULT": str(legacy_root)},
        clear=False,
    ), patch(
        "data_sources.modules.named_feature_status_guard.load_validated_claim_set",
        return_value=ValidatedClaimSet(receipt_revision="receipt-1"),
    ):
        findings = check_content(
            ARTICLE,
            proof_content=STATUS_TABLE,
            context_pack="context-pack.json",
            context_receipt="context-receipt.json",
        )

    assert "named_feature_claim_not_receipt_approved" in {
        finding["rule_id"] for finding in findings
    }


def _unknown_feature_claims() -> ValidatedClaimSet:
    return ValidatedClaimSet(
        [
            ApprovedClaim(
                claim_id="claim-lightning-LCUR-ATLAS",
                selector_id="LCUR-ATLAS",
                assertion="Atlas Dispatch is an approved Simpro feature.",
                use_mode="public_paraphrase",
                brand_scope=("Simpro",),
                source_hash="b" * 64,
                public_url="https://www.simprogroup.com/features/atlas-dispatch",
                approval_source="connector_claim_result",
                receipt_revision="receipt-atlas",
                claim_type="named-feature-status-v1",
                authority_resource_id="res-22222222222222222222222222222222",
            )
        ],
        receipt_revision="receipt-atlas",
    )


def _write_unknown_feature_pack(tmp_path):
    pack_path = tmp_path / "atlas-context-pack.json"
    pack_path.write_text(
        json.dumps(
            {
                "schema": "simpro-product-context-pack/v2",
                "sections": {
                    "Retrieved Guidance": [
                        {
                            "resource_id": "res-22222222222222222222222222222222",
                            "title": "Atlas Dispatch feature guidance",
                            "content": (
                                "---\nsemantic_roles:\n  - named_feature\n"
                                "entities:\n  - Atlas Dispatch\n---\n"
                                "Atlas Dispatch guidance."
                            ),
                            "read_purpose": "guidance",
                        }
                    ],
                    "Approved Claim Evidence": [],
                    "Selected Resource Inventory": [
                        {
                            "resource_id": "res-22222222222222222222222222222222"
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    return pack_path


def _atlas_sidecar(*, target_url="https://www.simprogroup.com/features/atlas-dispatch"):
    return f"""## Named Feature Status and Commercial Treatment

| Name | Capability claim ID | Commercial claim ID | Release status | Commercial treatment | Region or account boundary | Public wording decision |
|---|---|---|---|---|---|---|
| Atlas Dispatch | LCUR-ATLAS | | current_public_context | not_asserted | Current Simpro accounts | use |

## Named Feature/Add-On Link Check

| Name | Resource ID | Link decision | Target URL | Reason |
|---|---|---|---|---|
| Atlas Dispatch | res-22222222222222222222222222222222 | link | {target_url} | Receipt-bound feature resource and public URL. |
"""


def test_context_resource_discovers_unknown_feature_and_requires_sidecar(tmp_path):
    pack_path = _write_unknown_feature_pack(tmp_path)
    with patch(
        "data_sources.modules.named_feature_status_guard.load_validated_claim_set",
        return_value=_unknown_feature_claims(),
    ):
        findings = check_content(
            "# Dispatch\n\nAtlas Dispatch assigns the next job.",
            proof_content="",
            context_pack=pack_path,
            context_receipt="context-receipt.json",
        )

    rule_ids = {finding["rule_id"] for finding in findings}
    assert "named_feature_status_row_missing" in rule_ids


def test_link_decision_requires_target_in_article(tmp_path):
    pack_path = _write_unknown_feature_pack(tmp_path)
    with patch(
        "data_sources.modules.named_feature_status_guard.load_validated_claim_set",
        return_value=_unknown_feature_claims(),
    ):
        findings = check_content(
            "# Dispatch\n\nAtlas Dispatch assigns the next job.",
            proof_content=_atlas_sidecar(),
            context_pack=pack_path,
            context_receipt="context-receipt.json",
        )

    assert "named_feature_link_target_not_in_article" in {
        finding["rule_id"] for finding in findings
    }


def test_link_decision_rejects_wrong_first_feature_link(tmp_path):
    pack_path = _write_unknown_feature_pack(tmp_path)
    article = (
        "# Dispatch\n\n"
        "[Atlas Dispatch](https://example.com/wrong) assigns the next job. "
        "See [feature details](https://www.simprogroup.com/features/atlas-dispatch)."
    )
    with patch(
        "data_sources.modules.named_feature_status_guard.load_validated_claim_set",
        return_value=_unknown_feature_claims(),
    ):
        findings = check_content(
            article,
            proof_content=_atlas_sidecar(),
            context_pack=pack_path,
            context_receipt="context-receipt.json",
        )

    assert "named_feature_first_mention_link_mismatch" in {
        finding["rule_id"] for finding in findings
    }


def test_link_decision_rejects_url_not_approved_by_receipt(tmp_path):
    pack_path = _write_unknown_feature_pack(tmp_path)
    wrong_url = "https://www.simprogroup.com/features/not-atlas"
    with patch(
        "data_sources.modules.named_feature_status_guard.load_validated_claim_set",
        return_value=_unknown_feature_claims(),
    ):
        findings = check_content(
            f"# Dispatch\n\n[Atlas Dispatch]({wrong_url}) assigns the next job.",
            proof_content=_atlas_sidecar(target_url=wrong_url),
            context_pack=pack_path,
            context_receipt="context-receipt.json",
        )

    assert "named_feature_link_target_unbound" in {
        finding["rule_id"] for finding in findings
    }


def test_context_discovered_feature_with_receipt_bound_first_link_passes(tmp_path):
    pack_path = _write_unknown_feature_pack(tmp_path)
    with patch(
        "data_sources.modules.named_feature_status_guard.load_validated_claim_set",
        return_value=_unknown_feature_claims(),
    ):
        findings = check_content(
            "# Dispatch\n\n"
            "[Atlas Dispatch](https://www.simprogroup.com/features/atlas-dispatch) "
            "assigns the next job.",
            proof_content=_atlas_sidecar(),
            context_pack=pack_path,
            context_receipt="context-receipt.json",
        )

    assert findings == []

def test_cli_accepts_vault_root_and_forwards_it(tmp_path, capsys):
    captured = {}

    def fake_check_file(path, **kwargs):
        captured.update(kwargs)
        return []

    with patch(
        "data_sources.modules.named_feature_status_guard.check_file",
        side_effect=fake_check_file,
    ):
        try:
            exit_code = main(
                [
                    "article.md",
                    "--vault-root",
                    str(tmp_path),
                    "--context-pack",
                    "context-pack.json",
                    "--context-receipt",
                    "context-receipt.json",
                ]
            )
        except SystemExit as error:
            exit_code = error.code

    capsys.readouterr()
    assert exit_code == 0
    assert captured["vault_root"] == str(tmp_path)
