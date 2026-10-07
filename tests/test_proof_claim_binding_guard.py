from __future__ import annotations

from data_sources.modules.context_binding_guard import validate_claim_map
from data_sources.modules.proof_claim_binding_guard import validate_proof_claim_bindings


CAPABILITY = "Simpro allows dispatchers to drag jobs onto the scheduling board."
OUTCOME = "Simpro helps field service businesses reduce administrative work."
OWNED_ROW = (
    "- Claim: {claim} | Claim type: product_claim | Source class: owned_product | "
    "Evidence relation: directly_supports | URL: https://www.simprogroup.com/features/scheduling | "
    'Evidence: "scheduling board" | Status: approved'
)


def _unbound_kinds(findings):
    return [
        finding.get("proof_kind")
        for finding in findings
        if finding["rule_id"] == "context_proof_claim_unbound"
    ]


def _sidecar(claim: str) -> str:
    return "## Source Map\n" + OWNED_ROW.format(claim=claim) + "\n"


def _article(*paragraphs: str) -> str:
    return "# Scheduling guide\n\n" + "\n\n".join(paragraphs) + "\n"


def test_capability_passage_with_approved_owned_product_row_has_no_vault_obligation():
    findings = validate_proof_claim_bindings(
        _article(CAPABILITY), [], [], [], proof_content=_sidecar(CAPABILITY)
    )

    assert _unbound_kinds(findings) == []


def test_capability_passage_without_owned_product_row_still_needs_vault_claim():
    findings = validate_proof_claim_bindings(_article(CAPABILITY), [], [], [])

    assert _unbound_kinds(findings) == ["commercial_claim"]


def test_outcome_sentence_in_same_paragraph_keeps_the_vault_obligation():
    paragraph = f"{CAPABILITY} {OUTCOME}"

    findings = validate_proof_claim_bindings(
        _article(paragraph), [], [], [], proof_content=_sidecar(CAPABILITY)
    )

    assert _unbound_kinds(findings) == ["commercial_claim"]


def test_claim_map_validation_reads_owned_product_rows_from_the_sidecar():
    sidecar = "## Source Map\n" + OWNED_ROW.format(claim=CAPABILITY) + "\n"
    pack = {"sections": {"Approved Claim Evidence": []}}
    receipt = {"claim_decisions": []}

    with_sidecar = validate_claim_map(
        _article(CAPABILITY), pack, receipt, [], proof_content=sidecar
    )
    without_sidecar = validate_claim_map(_article(CAPABILITY), pack, receipt, [])

    assert _unbound_kinds(with_sidecar) == []
    assert _unbound_kinds(without_sidecar) == ["commercial_claim"]


def test_outcome_row_in_sidecar_does_not_waive_the_vault_obligation():
    sidecar = "## Source Map\n" + OWNED_ROW.format(claim=OUTCOME) + "\n"
    pack = {"sections": {"Approved Claim Evidence": []}}
    receipt = {"claim_decisions": []}

    findings = validate_claim_map(_article(OUTCOME), pack, receipt, [], proof_content=sidecar)

    assert _unbound_kinds(findings) == ["commercial_claim"]
