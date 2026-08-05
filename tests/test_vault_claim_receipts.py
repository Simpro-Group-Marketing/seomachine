import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from data_sources.modules.vault_claim_receipts import (
    VaultClaimReceiptError,
    load_validated_claim_set,
)


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def write_receipt_fixture(
    root: Path,
    *,
    claim_id: str = "claim-fred-FVMI-001",
    selector_id: str = "FVMI-001",
    use_mode: str = "authority_support",
    brand_scope=None,
    assertion: str = "Why skilled trades need better workforce technology",
    source_hash: str = "abc123",
    public_url: str = "https://example.com/skilled-trades",
    approval_source: str = "connector_claim_result",
    tamper_pack_hash: bool = False,
) -> tuple[Path, Path]:
    if brand_scope is None:
        brand_scope = ["Simpro"]
    request = {
        "topic": "skilled trades",
        "title": "Workforce technology",
        "objective": "Rank proof",
    }
    revisions = {
        "content_revision": "content-1",
        "contract_revision": "contract-1",
        "inventory_revision": "inventory-1",
        "manifest_revision": "manifest-1",
        "claim_registry_revision": "claims-1",
        "approval_policy_revision": "policy-1",
    }
    evidence = {
        "claim_id": claim_id,
        "selector_id": selector_id,
        "assertion": assertion,
        "use_mode": use_mode,
        "brand_scope": brand_scope,
        "source_hash": source_hash,
        "support_resource_hashes": {"res-proof": source_hash},
        "public_url": public_url,
        "approval_source": approval_source,
    }
    pack = {
        "schema": "simpro-product-context-pack/v2",
        "request": request,
        "revisions": revisions,
        "approved_claim_evidence": [evidence],
    }
    receipt = {
        "schema": "simpro-context-receipt/v1",
        "request_sha256": sha256_json(request),
        "pack_sha256": "bad-hash" if tamper_pack_hash else sha256_json(pack),
        "revisions": revisions,
        "claim_decisions": [
            {
                "claim_id": claim_id,
                "selector_id": selector_id,
                "assertion": assertion,
                "requested_use_mode": use_mode,
                "brand_scope": brand_scope,
                "source_hash": source_hash,
                "public_url": public_url,
                "approval_source": approval_source,
                "decision": "approved",
            }
        ],
        "canonical_receipt_sha256": "not-self-validated-in-v1-file-adapter",
    }
    pack_path = root / "context-pack.json"
    receipt_path = root / "context-receipt.json"
    pack_path.write_text(json.dumps(pack, indent=2), encoding="utf-8")
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return pack_path, receipt_path


class VaultClaimReceiptTests(unittest.TestCase):
    def test_valid_receipt_returns_approved_claim_by_selector_and_use_mode(self):
        with TemporaryDirectory() as temp_dir:
            pack_path, receipt_path = write_receipt_fixture(Path(temp_dir))

            claims = load_validated_claim_set(pack_path, receipt_path)

        claim = claims.require_selector_claim(
            "FVMI-001",
            use_modes={"authority_support"},
            public_url="https://example.com/skilled-trades",
        )
        self.assertEqual(claim.claim_id, "claim-fred-FVMI-001")
        self.assertEqual(claim.approval_source, "connector_claim_result")

    def test_missing_receipt_path_returns_no_claims(self):
        claims = load_validated_claim_set(None, None)

        self.assertFalse(claims.available)
        self.assertIsNone(
            claims.require_selector_claim("FVMI-001", use_modes={"authority_support"})
        )
        self.assertIn("context pack and receipt are required", claims.blocker)

    def test_invalid_pack_hash_rejects_receipt(self):
        with TemporaryDirectory() as temp_dir:
            pack_path, receipt_path = write_receipt_fixture(
                Path(temp_dir),
                tamper_pack_hash=True,
            )

            with self.assertRaisesRegex(VaultClaimReceiptError, "pack hash"):
                load_validated_claim_set(pack_path, receipt_path)

    def test_policy_overlay_approval_source_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            pack_path, receipt_path = write_receipt_fixture(
                Path(temp_dir),
                approval_source="approval_policy",
            )

            with self.assertRaisesRegex(VaultClaimReceiptError, "approval source"):
                load_validated_claim_set(pack_path, receipt_path)

    def test_missing_simpro_scope_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            pack_path, receipt_path = write_receipt_fixture(
                Path(temp_dir),
                brand_scope=[],
            )

            with self.assertRaisesRegex(VaultClaimReceiptError, "Simpro scope"):
                load_validated_claim_set(pack_path, receipt_path)

    def test_missing_public_url_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            pack_path, receipt_path = write_receipt_fixture(
                Path(temp_dir),
                public_url="",
            )

            with self.assertRaisesRegex(VaultClaimReceiptError, "public URL"):
                load_validated_claim_set(pack_path, receipt_path)

    def test_claim_decision_assertion_mismatch_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            pack_path, receipt_path = write_receipt_fixture(Path(temp_dir))
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["claim_decisions"][0]["assertion"] = "Changed assertion"
            receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

            with self.assertRaisesRegex(VaultClaimReceiptError, "assertion"):
                load_validated_claim_set(pack_path, receipt_path)


if __name__ == "__main__":
    unittest.main()
