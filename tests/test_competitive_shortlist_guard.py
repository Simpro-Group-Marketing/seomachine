from pathlib import Path
from unittest.mock import patch

import pytest

from data_sources.modules.competitive_shortlist_guard import check_content
from data_sources.modules.vault_claim_receipts import ApprovedClaim, ValidatedClaimSet


SERVICE_TITAN_RESOURCE = "res-11111111111111111111111111111111"
JOBBER_RESOURCE = "res-22222222222222222222222222222222"
SERVICE_TITAN_URL = "https://www.servicetitan.com/features/dispatching"


def article(body: str = "ServiceTitan offers dispatching tools for service teams.") -> str:
    return f"""---
artifact_type: blog
brand: Simpro
title: Simpro vs ServiceTitan
objective: Compare scheduling tools for growing contractors
---
# Simpro vs ServiceTitan

{body}
"""


def sidecar(*, selected="ServiceTitan", rejected="Jobber", resource=SERVICE_TITAN_RESOURCE,
            claim_id="claim-competitor-servicetitan-dispatch", public_url=SERVICE_TITAN_URL,
            objective="Compare scheduling tools for growing contractors") -> str:
    return f"""## Competitive Shortlist Decision

- Article objective: {objective}
- Authority: vault connector
- Status: approved

| Competitor | Decision | Reason | Resource ID | Claim ID | Public URL |
| --- | --- | --- | --- | --- | --- |
| {selected} | selected | Fits the article objective and target buyer workflow. | {resource} | {claim_id} | {public_url} |
| {rejected} | rejected | Does not fit the commercial-contractor objective. | {JOBBER_RESOURCE} |  |  |
"""


def context_pack() -> dict:
    return {
        "sections": {
            "Selected Resource Inventory": [
                {
                    "resource_id": SERVICE_TITAN_RESOURCE,
                    "title": "ServiceTitan competitive product context",
                    "topics": ["competitor", "ServiceTitan", "dispatching"],
                },
                {
                    "resource_id": JOBBER_RESOURCE,
                    "title": "Jobber competitive product context",
                    "topics": ["competitor", "Jobber", "small business"],
                },
            ]
        }
    }


def context_receipt() -> dict:
    return {
        "resources": [
            {"resource_id": SERVICE_TITAN_RESOURCE},
            {"resource_id": JOBBER_RESOURCE},
        ]
    }


def claims() -> ValidatedClaimSet:
    return ValidatedClaimSet(
        [
            ApprovedClaim(
                claim_id="claim-competitor-servicetitan-dispatch",
                selector_id="COMP-SERVICETITAN-DISPATCH",
                assertion="ServiceTitan offers dispatching tools for service teams.",
                use_mode="public_paraphrase",
                brand_scope=("Simpro",),
                source_hash="a" * 64,
                public_url=SERVICE_TITAN_URL,
                approval_source="connector_claim_result",
                receipt_revision="receipt-1",
                claim_type="competitive-context",
                authority_resource_id=SERVICE_TITAN_RESOURCE,
            )
        ]
    )


def findings_for(public_copy: str, proof: str, *, pack=None, receipt=None):
    with patch(
        "data_sources.modules.competitive_shortlist_guard.load_validated_claim_set",
        return_value=claims(),
    ):
        return check_content(
            public_copy,
            proof_content=proof,
            context_pack=pack if pack is not None else context_pack(),
            context_receipt=receipt if receipt is not None else context_receipt(),
        )


@pytest.mark.parametrize(
    ("proof", "rule_id"),
    [
        ("", "competitive_shortlist_missing"),
        (
            """## Competitive Shortlist Decision
- Article objective: Compare scheduling tools for growing contractors
- Authority: vault connector
- Status: approved
""",
            "competitive_shortlist_rows_missing",
        ),
        (sidecar(objective="Explain invoice workflows"), "competitive_shortlist_objective_mismatch"),
        (sidecar(resource="res-99999999999999999999999999999999"), "competitive_shortlist_resource_unbound"),
        (sidecar(selected="Jobber", rejected="ServiceTitan", resource=JOBBER_RESOURCE), "competitive_shortlist_public_competitor_not_selected"),
        (sidecar(claim_id="claim-invented"), "competitive_shortlist_claim_unapproved"),
        (sidecar(public_url="https://example.com/invented"), "competitive_shortlist_public_url_mismatch"),
    ],
)
def test_competitor_aware_articles_fail_closed_on_shortlist_gaps(proof, rule_id):
    findings = findings_for(article(), proof)

    assert rule_id in {finding["rule_id"] for finding in findings}


def test_serp_only_shortlist_cannot_authorize_named_competitors():
    proof = sidecar().replace("- Authority: vault connector", "- Authority: public SERP pages")

    findings = findings_for(article(), proof, pack={"sections": {"Selected Resource Inventory": []}})

    rule_ids = {finding["rule_id"] for finding in findings}
    assert "competitive_shortlist_authority_invalid" in rule_ids
    assert "competitive_shortlist_resource_unbound" in rule_ids


def test_valid_connector_bound_shortlist_passes():
    assert findings_for(article(), sidecar()) == []


def test_non_competitor_article_does_not_require_shortlist():
    public_copy = """---
artifact_type: blog
brand: Simpro
title: Scheduling workflow guide
objective: Explain scheduling workflow choices
---
# Scheduling workflow guide

Use this checklist to review dispatch capacity.
"""

    assert check_content(public_copy, proof_content="") == []


def test_operating_baseline_comparisons_do_not_trigger_competitor_shortlist():
    public_copy = """---
artifact_type: blog
brand: Simpro
title: AI field service economics
objective: Compare the same operating baseline before and after a pilot
---
# AI field service economics

Compare the same measures after a bounded pilot. The comparison tests the workflow, not vendors.
"""

    assert check_content(public_copy, proof_content="") == []
