import csv
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from data_sources.modules.named_feature_status_guard import check_content as _check_content
from tests.vault_context_fixture import (
    load_validated_claim_set_for_unit_test,
    write_connector_context_fixture,
)


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
    lines = [
        "## Named Feature Status and Commercial Treatment",
        "",
        "| Name | Capability claim ID | Commercial claim ID | Release status | Commercial treatment | Region or account boundary | Public wording decision |",
        "|---|---|---|---|---|---|---|",
        *rows,
        "",
        "## Named Feature/Add-On Link Check",
        "",
        "| Name | Resource ID | Link decision | Target URL | Reason |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        name = cells[0]
        capability_id = next(
            (item.strip() for item in cells[1].replace(";", ",").split(",") if item.strip()),
            "LCUR-UNKNOWN",
        )
        connector_claim_id = f"claim-lightning-{capability_id}"
        resource_id = (
            "res-" + hashlib.sha256(connector_claim_id.encode("utf-8")).hexdigest()[:32]
        )
        lines.append(
            f"| {name} | {resource_id} | do_not_link | | No approved feature URL in this fixture. |"
        )
    return "\n".join(lines)


def named_feature_status_proof(claim, *, url=None):
    approved_url = url or "https://www.simprogroup.com/lightning/lcur-0001"
    return (
        "## Source Map\n\n"
        f"- Claim: {claim} | Claim type: product_status | "
        f"Source class: named_feature_status | URL: {approved_url} | "
        "Status: approved | Use: named feature status"
    )


def link_decision(proof, *, name, capability_id, decision, target_url=""):
    connector_claim_id = f"claim-lightning-{capability_id}"
    resource_id = "res-" + hashlib.sha256(
        connector_claim_id.encode("utf-8")
    ).hexdigest()[:32]
    old = (
        f"| {name} | {resource_id} | do_not_link | | "
        "No approved feature URL in this fixture. |"
    )
    new = (
        f"| {name} | {resource_id} | {decision} | {target_url} | "
        "Receipt-approved feature status source. |"
    )
    return proof.replace(old, new)


def write_context_receipt_fixture(vault_path: Path) -> tuple[Path, Path]:
    claim_path = vault_path / "indexes" / "lightning-current-claim-status.csv"
    evidence = []
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
    return write_connector_context_fixture(vault_path, evidence)


def check_content(*args, **kwargs):
    if kwargs.get("vault_path") and not kwargs.get("context_pack") and not kwargs.get("context_receipt"):
        pack_path, receipt_path = write_context_receipt_fixture(Path(kwargs["vault_path"]))
        kwargs["context_pack"] = pack_path
        kwargs["context_receipt"] = receipt_path
    return _check_content(*args, **kwargs)


class NamedFeatureStatusGuardTests(unittest.TestCase):
    def setUp(self):
        validation_patch = patch(
            "data_sources.modules.named_feature_status_guard.load_validated_claim_set",
            new=load_validated_claim_set_for_unit_test,
        )
        validation_patch.start()
        self.addCleanup(validation_patch.stop)
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

    def test_named_feature_requires_link_check_block(self):
        row = "| Lightning | LCUR-0001 | | current_public_context | not_asserted | Current Simpro accounts | use |"
        proof = status_table(row).split("## Named Feature/Add-On Link Check", 1)[0]

        findings = check_content(
            "# AI workflows\n\nLightning helps connect AI workflows to Simpro data.",
            proof_content=proof,
            vault_path=self.vault_path,
        )

        self.assertTrue(
            any(f["rule_id"] == "named_feature_link_check_missing" for f in findings)
        )

    def test_sidecar_name_does_not_define_feature_inventory(self):
        row = "| AI CSR Agent | | | roadmap | not_asserted | Not publicly available | use |"

        findings = check_content(
            "# AI roadmap\n\nThe AI CSR Agent is coming soon for Simpro customers.",
            proof_content=status_table(row),
            vault_path=self.vault_path,
        )

        self.assertEqual(findings, [])

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

    def test_unapproved_pulse_claim_and_non_omit_wording_fail(self):
        row = "| Pulse | LCUR-0050 | | roadmap | not_asserted | Not publicly available | qualify |"
        findings = check_content(
            "# Roadmap\n\nPulse is our customer service agent on the roadmap.",
            proof_content=status_table(row),
            vault_path=self.vault_path,
        )
        rule_ids = {finding["rule_id"] for finding in findings}

        self.assertIn("named_feature_claim_not_receipt_approved", rule_ids)
        self.assertIn("named_feature_public_wording_must_omit", rule_ids)

    def test_internal_only_claim_is_not_receipt_approved(self):
        row = "| Pulse | LCUR-0049 | | roadmap | not_asserted | Internal roadmap context | omit |"
        findings = check_content(
            "# Roadmap\n\nPulse is our customer service agent on the roadmap.",
            proof_content=status_table(row),
            vault_path=self.vault_path,
        )

        self.assertTrue(
            any(
                f["rule_id"] == "named_feature_claim_not_receipt_approved"
                for f in findings
            )
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

    def test_inline_required_status_claim_cannot_be_bypassed_by_do_not_link(self):
        claim = "Lightning is currently available to eligible accounts."
        row = "| Lightning | LCUR-0001 | | current_public_context | not_asserted | Eligible accounts | use |"
        proof = status_table(row) + "\n\n" + named_feature_status_proof(claim)

        findings = check_content(
            f"# AI workflows\n\n{claim}",
            proof_content=proof,
            vault_path=self.vault_path,
        )

        self.assertIn(
            "named_feature_inline_status_link_missing",
            {finding["rule_id"] for finding in findings},
        )

    def test_inline_status_link_accepts_canonical_variants_in_paragraph_and_table_row(self):
        claim = "Lightning is currently available to eligible accounts."
        canonical_url = "https://www.simprogroup.com/lightning/lcur-0001"
        variant_url = canonical_url + "/?utm_source=campaign#availability"
        row = "| Lightning | LCUR-0001 | | current_public_context | not_asserted | Eligible accounts | use |"
        proof = link_decision(
            status_table(row),
            name="Lightning",
            capability_id="LCUR-0001",
            decision="link",
            target_url=canonical_url,
        )
        proof += "\n\n" + named_feature_status_proof(claim, url=canonical_url)
        articles = (
            f"# AI workflows\n\n[Lightning is currently available]({variant_url}) to eligible accounts.",
            "# AI workflows\n\n| Status |\n|---|\n"
            f"| [Lightning is currently available to eligible accounts]({variant_url}). |",
        )

        for article in articles:
            with self.subTest(article=article):
                findings = check_content(
                    article,
                    proof_content=proof,
                    vault_path=self.vault_path,
                )

                self.assertEqual(findings, [])

    def test_inline_status_link_rejects_generic_and_bare_citations(self):
        claim = "Lightning is currently available to eligible accounts."
        canonical_url = "https://www.simprogroup.com/lightning/lcur-0001"
        row = "| Lightning | LCUR-0001 | | current_public_context | not_asserted | Eligible accounts | use |"
        proof = status_table(row) + "\n\n" + named_feature_status_proof(
            claim,
            url=canonical_url,
        )
        articles = (
            f"# AI workflows\n\n{claim} [Source]({canonical_url})",
            f"# AI workflows\n\n{claim} {canonical_url}",
        )

        for article in articles:
            with self.subTest(article=article):
                findings = check_content(
                    article,
                    proof_content=proof,
                    vault_path=self.vault_path,
                )

                self.assertIn(
                    "named_feature_inline_status_link_missing",
                    {finding["rule_id"] for finding in findings},
                )

    def test_inline_status_link_rejects_url_not_approved_by_receipt(self):
        claim = "Lightning is currently available to eligible accounts."
        unapproved_url = "https://example.com/lightning-status"
        row = "| Lightning | LCUR-0001 | | current_public_context | not_asserted | Eligible accounts | use |"
        proof = status_table(row) + "\n\n" + named_feature_status_proof(
            claim,
            url=unapproved_url,
        )

        findings = check_content(
            "# AI workflows\n\n"
            f"[Lightning is currently available]({unapproved_url}) to eligible accounts.",
            proof_content=proof,
            vault_path=self.vault_path,
        )

        self.assertIn(
            "named_feature_inline_status_link_missing",
            {finding["rule_id"] for finding in findings},
        )


if __name__ == "__main__":
    unittest.main()
