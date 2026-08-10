import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping
from unittest.mock import patch

import pytest

from data_sources.modules.fred_authority_selector import (
    FredAuthorityDataError,
    _main,
    build_fred_authority_slate,
    select_fred_authority,
)
from data_sources.modules.vault_claim_receipts import load_validated_claim_set


ARTICLE_URL = "https://example.com/skilled-trades"
FINANCE_URL = "https://example.com/private-equity"
VIDEO_URL = "https://www.youtube.com/watch?v=abc123XYZ00"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def fred_claim(
    selector_id: str,
    assertion: str,
    public_url: str,
    *,
    claim_type: str = "fred-authority-joined-v2",
    authority_resource_id: str | None = None,
    claim_id: str | None = None,
    use_mode: str = "authority_support",
) -> dict[str, str]:
    return {
        "claim_id": claim_id or f"claim-fred-{selector_id}",
        "selector_id": selector_id,
        "assertion": assertion,
        "public_url": public_url,
        "claim_type": claim_type,
        "authority_resource_id": authority_resource_id or f"res-fred-{selector_id.lower()}",
        "use_mode": use_mode,
    }


def default_fred_claims() -> list[dict[str, str]]:
    return [
        fred_claim(
            "FVMI-001",
            "Why skilled trades need better workforce technology",
            ARTICLE_URL,
        ),
        fred_claim(
            "FVMI-002",
            "Private equity market conditions and investment strategy",
            FINANCE_URL,
        ),
        fred_claim(
            "FVMI-003",
            "Fred Voccola on field service leadership",
            VIDEO_URL,
        ),
    ]


def write_context_receipt_fixture(
    root: Path,
    claims: Iterable[Mapping[str, str]] | None = None,
) -> tuple[Path, Path, str]:
    """Write a canonical six-section context pack and its bound receipt."""
    sources = list(claims if claims is not None else default_fred_claims())
    requested_use_modes = sorted(
        {str(source.get("use_mode") or "authority_support") for source in sources}
    )
    request = {
        "task": "Select Fred Voccola authority evidence for a Simpro blog.",
        "scope": {
            "artifact_type": "blog",
            "brand": "Simpro",
            "title": "Workforce technology",
            "objective": "Evaluate relevant authority support.",
            "audience": "field service leaders",
            "region": "US",
            "intended_public_use_modes": requested_use_modes,
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
    evidence_rows = []
    decisions = []
    resource_ids = []
    resource_hashes = {}
    for source in sources:
        claim_id = str(source["claim_id"])
        resource_id = str(source.get("authority_resource_id") or "")
        use_mode = str(source.get("use_mode") or "authority_support")
        source_hash = hashlib.sha256(resource_id.encode("utf-8")).hexdigest()
        resource_hashes[resource_id] = source_hash
        evidence_rows.append(
            {
                "claim_id": claim_id,
                "selector_id": str(source["selector_id"]),
                "assertion": str(source["assertion"]),
                "claim_type": str(source.get("claim_type") or ""),
                "authority_resource_id": resource_id,
                "evidence_anchor": f"never-a-locator#{claim_id}",
                "public_url": str(source["public_url"]),
                "source_hash": source_hash,
                "support_resource_ids": [resource_id],
                "support_resource_hashes": {resource_id: source_hash},
                "use_mode": use_mode,
                "brand_scope": "Simpro",
                "authority_date": "2026-08-10",
            }
        )
        decisions.append(
            {
                "claim_id": claim_id,
                "query": "Fred Voccola authority evidence",
                "approved": True,
                "use_mode": use_mode,
                "brand_scope": "Simpro",
                "authority_date": "2026-08-10",
            }
        )
        if resource_id not in resource_ids:
            resource_ids.append(resource_id)
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
                "selected_resource_ids": resource_ids,
                "selected_resource_purposes": {
                    resource_id: "authority_support" for resource_id in resource_ids
                },
            },
            "Retrieved Guidance": [],
            "Approved Claim Evidence": evidence_rows,
            "Constraints and Unresolved Gaps": {
                "constraints": [],
                "unresolved_gaps": [],
            },
            "Selected Resource Inventory": [
                {
                    "resource_id": resource_id,
                    "purpose": "authority_support",
                    "resource_hash": resource_hashes[resource_id],
                }
                for resource_id in resource_ids
            ],
        },
    }
    receipt = {
        "schema": "simpro-context-receipt/v1",
        "request_sha256": _sha256_json(request),
        "pack_sha256": _sha256_json(pack),
        "revisions": revisions,
        "claim_registry_revision": "claims-1",
        "resources": resource_ids,
        "resource_purposes": {
            resource_id: "authority_support" for resource_id in resource_ids
        },
        "claim_decisions": decisions,
        "search_queries": ["Fred Voccola authority evidence"],
        "discovery_trace": [],
        "constraints": [],
        "unresolved_gaps": [],
        "task_satisfaction": "satisfied",
        "validation_time": "2026-08-10T12:00:00Z",
        "errors": [],
    }
    receipt["receipt_sha256"] = _sha256_json(receipt)
    pack_path = root / "context-pack.json"
    receipt_path = root / "context-receipt.json"
    pack_path.write_text(json.dumps(pack, indent=2), encoding="utf-8")
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return pack_path, receipt_path, str(receipt["receipt_sha256"])


class AcceptingContextClient:
    def validate_context(self, request, pack, receipt):
        return {"valid": True, "errors": []}


def load_validated_claim_set_for_unit_test(
    context_pack,
    context_receipt,
    *,
    vault_root=None,
):
    return load_validated_claim_set(
        context_pack,
        context_receipt,
        vault_root=vault_root,
        client=AcceptingContextClient(),
    )


@pytest.fixture(autouse=True)
def _mock_live_validator():
    with patch(
        "data_sources.modules.fred_authority_selector.load_validated_claim_set",
        new=load_validated_claim_set_for_unit_test,
    ):
        yield


def test_public_fred_authority_requires_context_receipt():
    with pytest.raises(FredAuthorityDataError, match="context pack and receipt are required"):
        select_fred_authority("skilled trades")


def test_topic_fit_ranks_relevant_receipt_claim_first(tmp_path):
    pack, receipt, _ = write_context_receipt_fixture(tmp_path)

    results = select_fred_authority(
        "skilled trades workforce",
        title="How workforce technology supports field service teams",
        objective="Explain labor challenges in the trades",
        context_pack=pack,
        context_receipt=receipt,
    )

    assert results[0]["inventory_id"] == "FVMI-001"
    assert results[0]["authority_id"] == "res-fred-fvmi-001"
    assert results[0]["score"] > results[1]["score"]


def test_selector_filters_non_fred_receipt_claims(tmp_path):
    claims = default_fred_claims() + [
        fred_claim(
            "OTHER-001",
            "Skilled trades workforce technology",
            "https://example.com/not-fred",
            claim_type="named-feature-status-v1",
        )
    ]
    pack, receipt, _ = write_context_receipt_fixture(tmp_path, claims)

    results = select_fred_authority(
        "skilled trades workforce",
        context_pack=pack,
        context_receipt=receipt,
        limit=10,
    )

    assert {item["inventory_id"] for item in results} == {
        "FVMI-001",
        "FVMI-002",
        "FVMI-003",
    }


def test_youtube_watch_claim_is_embed_eligible_not_playlist_only(tmp_path):
    pack, receipt, _ = write_context_receipt_fixture(tmp_path)

    result = next(
        item
        for item in select_fred_authority(
            "field service leadership",
            context_pack=pack,
            context_receipt=receipt,
        )
        if item["inventory_id"] == "FVMI-003"
    )

    assert result["playlist_only"] is False
    assert result["authority_kind"] == "earned_media_authority"


def test_slate_defaults_to_no_public_selection_and_binds_receipt(tmp_path):
    pack, receipt, revision = write_context_receipt_fixture(tmp_path)

    slate = build_fred_authority_slate(
        "skilled trades workforce",
        context_pack=pack,
        context_receipt=receipt,
        limit=3,
    )

    assert "- Evaluation status: completed" in slate
    assert "- Selected: [none]" in slate
    assert "- Intended use: none" in slate
    assert f"- Receipt revision: {revision}" in slate
    assert "- Claim IDs: [claim-fred-FVMI-001" in slate


def test_slate_records_selected_resource_id_and_approved_url(tmp_path):
    pack, receipt, _ = write_context_receipt_fixture(tmp_path)

    slate = build_fred_authority_slate(
        "skilled trades workforce technology",
        context_pack=pack,
        context_receipt=receipt,
        selected_id="FVMI-001",
    )

    assert "- Selected: [FVMI-001]" in slate
    assert "- Authority row: [res-fred-fvmi-001]" in slate
    assert f"- Public URL: {ARTICLE_URL}" in slate
    assert "- Evidence status: receipt_approved" in slate


def test_slate_rejects_selection_outside_limited_candidate_set(tmp_path):
    pack, receipt, _ = write_context_receipt_fixture(tmp_path)

    with pytest.raises(FredAuthorityDataError, match="not in the verified candidate slate"):
        build_fred_authority_slate(
            "skilled trades workforce",
            context_pack=pack,
            context_receipt=receipt,
            limit=1,
            selected_id="FVMI-002",
        )


def test_tampered_pack_fails_closed(tmp_path):
    pack, receipt, _ = write_context_receipt_fixture(tmp_path)
    payload = json.loads(pack.read_text(encoding="utf-8"))
    payload["sections"]["Task and Scope"]["task"] = "tampered task"
    pack.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(FredAuthorityDataError, match="request hash does not match"):
        select_fred_authority(
            "workforce",
            context_pack=pack,
            context_receipt=receipt,
        )


def test_cli_prints_receipt_ranked_json(tmp_path, capsys):
    pack, receipt, _ = write_context_receipt_fixture(tmp_path)

    exit_code = _main(
        [
            "skilled trades workforce",
            "--context-pack",
            str(pack),
            "--context-receipt",
            str(receipt),
            "--limit",
            "1",
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert len(output) == 1
    assert output[0]["inventory_id"] == "FVMI-001"


def test_cli_slate_output_preserves_selector_command(tmp_path, capsys):
    pack, receipt, _ = write_context_receipt_fixture(tmp_path)

    exit_code = _main(
        [
            "workforce technology",
            "--title",
            "Workforce technology",
            "--objective",
            "Explain workforce challenges",
            "--context-pack",
            str(pack),
            "--context-receipt",
            str(receipt),
            "--slate",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "## Fred Voccola Authority Selection" in output
    assert "--context-pack" in output
    assert "--context-receipt" in output
