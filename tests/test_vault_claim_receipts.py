import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from data_sources.modules.vault_claim_receipts import (
    VaultClaimReceiptError,
    load_validated_claim_set,
)


class ValidatingClient:
    def __init__(self, result=None):
        self.result = result or {"valid": True, "errors": []}
        self.calls = []

    def validate_context(self, request, pack, receipt):
        self.calls.append((request, pack, receipt))
        return self.result


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def write_receipt_fixture(
    root: Path,
    *,
    claim_id: str = "claim-fred-FVMI-001",
    use_mode: str = "authority_support",
    brand_scope=None,
    assertion: str = "Why skilled trades need better workforce technology",
    source_hash: str = "a" * 64,
    public_url: str = "https://example.com/skilled-trades",
    tamper_pack_hash: bool = False,
    request_query: str = "",
) -> tuple[Path, Path]:
    if brand_scope is None:
        brand_scope = "Simpro"
    request = {
        "task": "Select Fred authority for a Simpro article.",
        "scope": {
            "artifact_type": "blog",
            "brand": "Simpro",
            "title": "Workforce technology",
            "objective": "Rank proof",
            "audience": "field service leaders",
            "region": "US",
            "intended_public_use_modes": [use_mode],
        },
    }
    if request_query:
        request["query"] = request_query

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
        "assertion": assertion,
        "claim_type": "fred-authority-joined-v2",
        "authority_resource_id": "res-proof",
        "evidence_anchor": "authority-row-1",
        "use_mode": use_mode,
        "brand_scope": brand_scope,
        "source_hash": source_hash,
        "support_resource_ids": ["res-proof"],
        "support_resource_hashes": {"res-proof": source_hash},
        "public_url": public_url,
        "authority_date": "2026-08-10",
    }
    pack = {
        "schema": "simpro-product-context-pack/v2",
        "revisions": revisions,
        "claim_registry_revision": "claims-1",
        "sections": {
            "Task and Scope": {
                **({"request": request} if request_query else {}),
                "task": request["task"],
                "scope": request["scope"],
                "task_satisfaction": "satisfied",
            },
            "Discovery Trace": {
                "entries": [],
                "selected_resource_ids": ["res-proof"],
                "selected_resource_purposes": {"res-proof": "context"},
            },
            "Retrieved Guidance": [],
            "Approved Claim Evidence": [evidence],
            "Constraints and Unresolved Gaps": {
                "constraints": [],
                "unresolved_gaps": [],
            },
            "Selected Resource Inventory": [],
        },
    }
    receipt = {
        "schema": "simpro-context-receipt/v1",
        "request_sha256": sha256_json(request),
        "pack_sha256": "bad-hash" if tamper_pack_hash else sha256_json(pack),
        "revisions": revisions,
        "claim_registry_revision": "claims-1",
        "resources": [],
        "resource_purposes": {"res-proof": "context"},
        "claim_decisions": [
            {
                "claim_id": claim_id,
                "query": "Fred workforce technology",
                "approved": True,
                "use_mode": use_mode,
                "brand_scope": brand_scope,
                "authority_date": "2026-08-10",
            }
        ],
        "search_queries": ["Fred workforce technology"],
        "discovery_trace": [],
        "constraints": [],
        "unresolved_gaps": [],
        "task_satisfaction": "satisfied",
        "validation_time": "2026-08-10T12:00:00Z",
        "errors": [],
    }
    receipt["receipt_sha256"] = sha256_json(receipt)
    pack_path = root / "context-pack.json"
    receipt_path = root / "context-receipt.json"
    pack_path.write_text(json.dumps(pack, indent=2), encoding="utf-8")
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return pack_path, receipt_path


def write_connector_v2_fixture(root: Path) -> tuple[Path, Path]:
    request = {
        "task": "Select Fred authority for a Simpro article.",
        "scope": {
            "artifact_type": "blog",
            "brand": "Simpro",
            "title": "AI in field service",
            "objective": "Explain operational AI.",
            "audience": "field service leaders",
            "region": "US",
            "intended_public_use_modes": ["authority_support"],
        },
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
        "claim_id": "claim-fred-FVMI-001",
        "assertion": "Why skilled trades need better workforce technology",
        "claim_type": "fred-authority-joined-v2",
        "authority_resource_id": "res-proof",
        "evidence_anchor": "authority-row-1",
        "public_url": "https://example.com/skilled-trades",
        "source_hash": "a" * 64,
        "support_resource_ids": ["res-proof"],
        "support_resource_hashes": {"res-proof": "a" * 64},
        "use_mode": "authority_support",
        "brand_scope": "Simpro",
        "authority_date": "2026-08-10",
    }
    pack = {
        "schema": "simpro-product-context-pack/v2",
        "revisions": revisions,
        "claim_registry_revision": "claims-1",
        "sections": {
            "Task and Scope": {
                "task": request["task"],
                "scope": request["scope"],
                "task_satisfaction": "satisfied",
            },
            "Discovery Trace": {
                "entries": [],
                "selected_resource_ids": ["res-proof"],
                "selected_resource_purposes": {"res-proof": "context"},
            },
            "Retrieved Guidance": [],
            "Approved Claim Evidence": [evidence],
            "Constraints and Unresolved Gaps": {
                "constraints": [],
                "unresolved_gaps": [],
            },
            "Selected Resource Inventory": [],
        },
    }
    receipt = {
        "schema": "simpro-context-receipt/v1",
        "request_sha256": sha256_json(request),
        "pack_sha256": sha256_json(pack),
        "revisions": revisions,
        "claim_registry_revision": "claims-1",
        "resources": [],
        "resource_purposes": {"res-proof": "context"},
        "claim_decisions": [
            {
                "claim_id": "claim-fred-FVMI-001",
                "query": "Fred workforce technology",
                "approved": True,
                "use_mode": "authority_support",
                "brand_scope": "Simpro",
                "authority_date": "2026-08-10",
            }
        ],
        "search_queries": ["Fred workforce technology"],
        "discovery_trace": [],
        "constraints": [],
        "unresolved_gaps": [],
        "task_satisfaction": "satisfied",
        "validation_time": "2026-08-10T12:00:00Z",
        "errors": [],
    }
    receipt["receipt_sha256"] = sha256_json(receipt)
    pack_path = root / "connector-context-pack.json"
    receipt_path = root / "connector-context-receipt.json"
    pack_path.write_text(json.dumps(pack, indent=2), encoding="utf-8")
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return pack_path, receipt_path


class VaultClaimReceiptTests(unittest.TestCase):
    def test_uses_embedded_exact_request_when_present(self):
        with TemporaryDirectory() as temp_dir:
            pack_path, receipt_path = write_receipt_fixture(
                Path(temp_dir),
                request_query="Fred workforce technology",
            )
            validator = ValidatingClient()
            load_validated_claim_set(pack_path, receipt_path, client=validator)

        self.assertEqual(
            validator.calls[0][0]["query"],
            "Fred workforce technology",
        )

    def test_accepts_the_installed_connectors_six_section_v2_contract(self):
        with TemporaryDirectory() as temp_dir:
            pack_path, receipt_path = write_connector_v2_fixture(Path(temp_dir))

            validator = ValidatingClient()
            claims = load_validated_claim_set(
                pack_path,
                receipt_path,
                client=validator,
            )

        claim = claims.require_selector_claim(
            "FVMI-001",
            use_modes={"authority_support"},
            public_url="https://example.com/skilled-trades",
        )
        self.assertIsNotNone(claim)
        self.assertEqual(claim.claim_id, "claim-fred-FVMI-001")
        self.assertEqual(claim.approval_source, "connector_claim_result")
        self.assertEqual(claim.claim_type, "fred-authority-joined-v2")
        self.assertEqual(claim.authority_resource_id, "res-proof")
        self.assertEqual(claim.evidence_anchor, "authority-row-1")
        self.assertEqual(claims.approved_claims(), (claim,))
        self.assertEqual(len(validator.calls), 1)

    def test_valid_receipt_returns_approved_claim_by_selector_and_use_mode(self):
        with TemporaryDirectory() as temp_dir:
            pack_path, receipt_path = write_receipt_fixture(Path(temp_dir))

            claims = load_validated_claim_set(
                pack_path,
                receipt_path,
                client=ValidatingClient(),
            )

        claim = claims.require_selector_claim(
            "FVMI-001",
            use_modes={"authority_support"},
            public_url="https://example.com/skilled-trades",
        )
        self.assertEqual(claim.claim_id, "claim-fred-FVMI-001")
        self.assertEqual(claim.approval_source, "connector_claim_result")

    def test_selector_lookup_does_not_authorize_arbitrary_claim_suffix(self):
        with TemporaryDirectory() as temp_dir:
            pack_path, receipt_path = write_receipt_fixture(
                Path(temp_dir),
                claim_id="claim-unrelated-LCUR-0001",
                use_mode="public_paraphrase",
            )
            claims = load_validated_claim_set(
                pack_path,
                receipt_path,
                client=ValidatingClient(),
            )

        self.assertIsNone(
            claims.require_selector_claim(
                "LCUR-0001",
                use_modes={"public_paraphrase"},
            )
        )

    def test_generic_claim_id_is_not_an_implicit_selector_id(self):
        with TemporaryDirectory() as temp_dir:
            pack_path, receipt_path = write_receipt_fixture(
                Path(temp_dir),
                claim_id="case-study-teamwired",
                use_mode="public_paraphrase",
            )
            claims = load_validated_claim_set(
                pack_path,
                receipt_path,
                client=ValidatingClient(),
            )

        self.assertIsNone(
            claims.require_selector_claim(
                "case-study-teamwired",
                use_modes={"public_paraphrase"},
            )
        )

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
                load_validated_claim_set(
                    pack_path,
                    receipt_path,
                    client=ValidatingClient(),
                )

    def test_unapproved_receipt_decision_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            pack_path, receipt_path = write_receipt_fixture(Path(temp_dir))
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["claim_decisions"][0]["approved"] = False
            receipt.pop("receipt_sha256")
            receipt["receipt_sha256"] = sha256_json(receipt)
            receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

            with self.assertRaisesRegex(VaultClaimReceiptError, "not approved"):
                load_validated_claim_set(
                    pack_path,
                    receipt_path,
                    client=ValidatingClient(),
                )

    def test_missing_simpro_scope_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            pack_path, receipt_path = write_receipt_fixture(
                Path(temp_dir),
                brand_scope=[],
            )

            with self.assertRaisesRegex(VaultClaimReceiptError, "Simpro scope"):
                load_validated_claim_set(
                    pack_path,
                    receipt_path,
                    client=ValidatingClient(),
                )

    def test_mixed_brand_scope_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            pack_path, receipt_path = write_receipt_fixture(
                Path(temp_dir),
                brand_scope=["Simpro", "BigChange"],
            )

            with self.assertRaisesRegex(VaultClaimReceiptError, "Simpro scope"):
                load_validated_claim_set(
                    pack_path,
                    receipt_path,
                    client=ValidatingClient(),
                )

    def test_missing_public_url_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            pack_path, receipt_path = write_receipt_fixture(
                Path(temp_dir),
                public_url="",
            )

            with self.assertRaisesRegex(VaultClaimReceiptError, "public URL"):
                load_validated_claim_set(
                    pack_path,
                    receipt_path,
                    client=ValidatingClient(),
                )

    def test_receipt_self_hash_mismatch_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            pack_path, receipt_path = write_receipt_fixture(Path(temp_dir))
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["claim_decisions"][0]["query"] = "Changed query"
            receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

            with self.assertRaisesRegex(VaultClaimReceiptError, "self-hash"):
                load_validated_claim_set(
                    pack_path,
                    receipt_path,
                    client=ValidatingClient(),
                )

    def test_self_consistent_receipt_rejected_when_live_connector_rejects_it(self):
        with TemporaryDirectory() as temp_dir:
            pack_path, receipt_path = write_receipt_fixture(Path(temp_dir))
            rejecting = ValidatingClient(
                {"valid": False, "errors": ["pack revisions are stale"]}
            )

            with self.assertRaisesRegex(VaultClaimReceiptError, "live connector"):
                load_validated_claim_set(
                    pack_path,
                    receipt_path,
                    client=rejecting,
                )


if __name__ == "__main__":
    unittest.main()
