import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from data_sources.modules.named_feature_status_guard import check_content as _check_content


CSV_HEADER = (
    '"claim_id","claim_domain","claim_text","brand_scope","audience","source_id",'
    '"source_date","effective_from","effective_to","evidence_status",'
    '"agent_allowed_use","public_use_status","supersedes_claim_id","notes"\n'
)


def claim_row(
    claim_id,
    claim_text,
    *,
    evidence_status="current_checked_usable_public_product_context",
    public_use_status="usable_public_product_context",
    effective_to="",
    allowed_use="Use in public product context.",
):
    values = [
        claim_id,
        "test",
        claim_text,
        "Simpro",
        "public|internal",
        "PLG-TEST",
        "2026-07-29",
        "2026-07-01",
        effective_to,
        evidence_status,
        allowed_use,
        public_use_status,
        "",
        "Test fixture.",
    ]
    return ",".join(f'"{value}"' for value in values) + "\n"


def status_table(*rows):
    return "\n".join(
        [
            "## Named Feature Status and Commercial Treatment",
            "",
            "| Name | Capability claim ID | Commercial claim ID | Release status | Commercial treatment | Region or account boundary | Public wording decision |",
            "|---|---|---|---|---|---|---|",
            *rows,
        ]
    )


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def write_context_receipt_fixture(vault_path: Path) -> tuple[Path, Path]:
    claim_path = vault_path / "indexes" / "lightning-current-claim-status.csv"
    request = {"topic": "named feature fixture"}
    revisions = {
        "content_revision": "content-1",
        "contract_revision": "contract-1",
        "inventory_revision": "inventory-1",
        "manifest_revision": "manifest-1",
        "claim_registry_revision": "claims-1",
        "approval_policy_revision": "policy-1",
    }
    evidence = []
    decisions = []
    with claim_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        claim_id = str(row.get("claim_id") or "").strip()
        public_status = str(row.get("public_use_status") or "").strip()
        evidence_status = str(row.get("evidence_status") or "").strip()
        if not claim_id or not public_status.startswith("usable_public"):
            continue
        if "internal" in evidence_status or "superseded" in evidence_status:
            continue
        mode = (
            "public_metric"
            if public_status == "usable_public_source_bound_metric"
            else "public_paraphrase"
        )
        source_hash = f"hash-{claim_id}-{mode}"
        item = {
            "claim_id": f"claim-lightning-{claim_id}",
            "selector_id": claim_id,
            "assertion": str(row.get("claim_text") or claim_id),
            "use_mode": mode,
            "brand_scope": ["Simpro"],
            "source_hash": source_hash,
            "support_resource_hashes": {f"res-{claim_id}": source_hash},
            "public_url": f"https://www.simprogroup.com/lightning/{claim_id.lower()}",
            "approval_source": "connector_claim_result",
        }
        evidence.append(item)
        decisions.append(
            {
                "claim_id": item["claim_id"],
                "selector_id": item["selector_id"],
                "assertion": item["assertion"],
                "requested_use_mode": item["use_mode"],
                "brand_scope": item["brand_scope"],
                "source_hash": item["source_hash"],
                "public_url": item["public_url"],
                "approval_source": item["approval_source"],
                "decision": "approved",
            }
        )
    pack = {
        "schema": "simpro-product-context-pack/v2",
        "request": request,
        "revisions": revisions,
        "approved_claim_evidence": evidence,
    }
    receipt = {
        "schema": "simpro-context-receipt/v1",
        "request_sha256": sha256_json(request),
        "pack_sha256": sha256_json(pack),
        "revisions": revisions,
        "claim_decisions": decisions,
        "canonical_receipt_sha256": "named-feature-receipt-fixture",
    }
    pack_path = vault_path / "context-pack.json"
    receipt_path = vault_path / "context-receipt.json"
    pack_path.write_text(json.dumps(pack, indent=2), encoding="utf-8")
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return pack_path, receipt_path


def check_content(*args, **kwargs):
    if kwargs.get("vault_path") and not kwargs.get("context_pack") and not kwargs.get("context_receipt"):
        pack_path, receipt_path = write_context_receipt_fixture(Path(kwargs["vault_path"]))
        kwargs["context_pack"] = pack_path
        kwargs["context_receipt"] = receipt_path
    return _check_content(*args, **kwargs)


class NamedFeatureStatusGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.vault_path = Path(self.temp_dir.name)
        indexes = self.vault_path / "indexes"
        indexes.mkdir()
        (indexes / "lightning-current-claim-status.csv").write_text(
            CSV_HEADER
            + claim_row("LCUR-0001", "Lightning is the Simpro AI intelligence layer.")
            + claim_row("LCUR-0008", "FieldReady creates business-specific training.")
            + claim_row(
                "LCUR-0022",
                "RAIN features require Lightning.",
                effective_to="2099-09-30",
            )
            + claim_row(
                "LCUR-0023",
                "Intelligent AI Scheduler supports schedule creation.",
                effective_to="2099-09-30",
            )
            + claim_row(
                "LCUR-0049",
                "Pulse was an internal roadmap specialist name.",
                evidence_status="current_checked_usable_internal_sales_context",
                public_use_status="internal_only",
            )
            + claim_row(
                "LCUR-0050",
                "The old roadmap commitment is superseded.",
                evidence_status="superseded_do_not_use_as_current",
                public_use_status="do_not_use_current",
                allowed_use="Do not use.",
            )
            + claim_row(
                "LCUR-COM-1",
                "Lightning is included in the Enterprise package.",
            ),
            encoding="utf-8",
        )

    def test_article_without_named_lightning_features_passes(self):
        findings = check_content(
            "# Scheduling\n\nRank options after a cancellation.",
            vault_path=self.vault_path,
        )

        self.assertEqual(findings, [])

    def test_named_feature_claim_requires_context_receipt(self):
        row = "| Lightning | LCUR-0001 | | current_public_context | not_asserted | Current Simpro accounts | use |"
        findings = _check_content(
            "# AI workflows\n\nLightning helps connect AI workflows to Simpro data.",
            proof_content=status_table(row),
            vault_path=self.vault_path,
        )

        self.assertTrue(
            any(f["rule_id"] == "named_feature_context_receipt_missing" for f in findings)
        )

    def test_missing_status_row_fails(self):
        findings = check_content(
            "# AI workflows\n\nLightning helps connect AI workflows to Simpro data.",
            proof_content="",
            vault_path=self.vault_path,
        )

        self.assertTrue(
            any(f["rule_id"] == "named_feature_status_row_missing" for f in findings)
        )

    def test_duplicate_status_rows_fail(self):
        row = "| Lightning | LCUR-0001 | | current_public_context | not_asserted | Current Simpro accounts | use |"
        findings = check_content(
            "# AI workflows\n\nLightning helps connect AI workflows to Simpro data.",
            proof_content=status_table(row, row),
            vault_path=self.vault_path,
        )

        self.assertTrue(
            any(f["rule_id"] == "named_feature_status_row_duplicate" for f in findings)
        )

    def test_invalid_release_and_commercial_enums_fail(self):
        row = "| Lightning | LCUR-0001 | | generally_available | bundled | Current Simpro accounts | use |"
        findings = check_content(
            "# AI workflows\n\nLightning helps connect AI workflows to Simpro data.",
            proof_content=status_table(row),
            vault_path=self.vault_path,
        )
        rule_ids = {finding["rule_id"] for finding in findings}

        self.assertIn("named_feature_release_status_invalid", rule_ids)
        self.assertIn("named_feature_commercial_treatment_invalid", rule_ids)

    def test_superseded_pulse_evidence_and_non_omit_wording_fail(self):
        row = "| Pulse | LCUR-0050 | | roadmap | not_asserted | Not publicly available | qualify |"
        findings = check_content(
            "# Roadmap\n\nPulse is our customer service agent on the roadmap.",
            proof_content=status_table(row),
            vault_path=self.vault_path,
        )
        rule_ids = {finding["rule_id"] for finding in findings}

        self.assertIn("named_feature_claim_unusable", rule_ids)
        self.assertIn("named_feature_public_wording_must_omit", rule_ids)

    def test_internal_only_claim_fails(self):
        row = "| Pulse | LCUR-0049 | | roadmap | not_asserted | Internal roadmap context | omit |"
        findings = check_content(
            "# Roadmap\n\nPulse is our customer service agent on the roadmap.",
            proof_content=status_table(row),
            vault_path=self.vault_path,
        )

        self.assertTrue(
            any(f["rule_id"] == "named_feature_claim_unusable" for f in findings)
        )

    def test_target_timed_scheduler_with_rain_requirement_passes(self):
        scheduler_row = "| Intelligent AI Scheduler | LCUR-0023; LCUR-0022 | | target_timed | not_asserted | Current target may shift; requires Lightning | qualify |"
        rain_row = "| RAIN | LCUR-0022 | | target_timed | not_asserted | Current target may shift; requires Lightning | qualify |"
        lightning_row = "| Lightning | LCUR-0001 | | current_public_context | not_asserted | Current Simpro accounts | use |"
        findings = check_content(
            "# Scheduling\n\n"
            "Intelligent AI Scheduler is a target-timed RAIN feature. "
            "Current timing may shift and it requires Lightning.",
            proof_content=status_table(scheduler_row, rain_row, lightning_row),
            vault_path=self.vault_path,
        )

        self.assertEqual(findings, [])

    def test_scheduler_without_rain_requirement_fails(self):
        row = "| Intelligent AI Scheduler | LCUR-0023 | | target_timed | not_asserted | Current target may shift | qualify |"
        findings = check_content(
            "# Scheduling\n\n"
            "Intelligent AI Scheduler is a target-timed RAIN feature. "
            "Current timing may shift.",
            proof_content=status_table(row),
            vault_path=self.vault_path,
        )

        self.assertTrue(
            any(f["rule_id"] == "named_feature_scheduler_requirement_missing" for f in findings)
        )

    def test_commercial_assertion_requires_commercial_claim_id(self):
        row = "| Lightning | LCUR-0001 | | current_public_context | included | Enterprise package | use |"
        findings = check_content(
            "# AI workflows\n\nLightning is included in the Enterprise package.",
            proof_content=status_table(row),
            vault_path=self.vault_path,
        )

        self.assertTrue(
            any(f["rule_id"] == "named_feature_commercial_claim_missing" for f in findings)
        )

    def test_not_asserted_rejected_when_public_copy_makes_commercial_claim(self):
        row = "| Lightning | LCUR-0001 | | current_public_context | not_asserted | Current accounts | use |"
        findings = check_content(
            "# AI workflows\n\nLightning is available as a paid add-on.",
            proof_content=status_table(row),
            vault_path=self.vault_path,
        )

        self.assertTrue(
            any(f["rule_id"] == "named_feature_commercial_treatment_required" for f in findings)
        )

    def test_usable_commercial_claim_passes(self):
        row = "| Lightning | LCUR-0001 | LCUR-COM-1 | current_public_context | included | Enterprise package | use |"
        findings = check_content(
            "# AI workflows\n\nLightning is included in the Enterprise package.",
            proof_content=status_table(row),
            vault_path=self.vault_path,
        )

        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
