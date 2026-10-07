"""Owned Simpro product language passes every product-sentence gate together."""

from __future__ import annotations

import json
import tempfile
import unittest

import pytest

from data_sources.modules import context_binding_generator
from data_sources.modules.proof_claim_binding_guard import validate_proof_claim_bindings
from data_sources.modules.proof_link_policy import analyze_proof_links
from data_sources.modules import public_research_link_guard
from data_sources.modules.source_support_guard import check_content as source_support_check
from data_sources.modules.url_validator import UrlValidationSummary
from tests import test_context_binding_guard as binding_fixture
from tests.test_source_support_guard import fetcher_with, write_source_classification


SCHEDULING_URL = "https://www.simprogroup.com/features/scheduling/"
PRODUCT_LANGUAGE = (
    "Simpro works by connecting scheduling and job details in one workflow.",
    "Simpro connects scheduling and job details in one record.",
    "Simpro enables dispatchers to assign technicians from the job card.",
    "Simpro allows dispatchers to drag jobs onto the scheduling board.",
)


def _owned_rows(claims, *, claim_type="product_claim", classification="", classification_hash=""):
    registry = (
        f"Classification artifact: {classification} | Classification hash: {classification_hash} | "
        if classification
        else ""
    )
    return "\n".join(
        f"- Claim: {claim} | Claim type: {claim_type} | Source class: owned_product | "
        f"Evidence relation: directly_supports | {registry}URL: {SCHEDULING_URL} | "
        f'Evidence: "{claim}" | Status: approved'
        for claim in claims
    )


def _article(claims) -> str:
    return "# Scheduling guide\n\n## How scheduling works in Simpro\n\n" + "\n\n".join(claims) + "\n"


def _source_support_findings(claims, *, claim_type="product_claim", page_text=None):
    with tempfile.TemporaryDirectory() as tmp:
        classification, classification_hash = write_source_classification(
            tmp, SCHEDULING_URL, "owned_product", "owned"
        )
        rows = _owned_rows(
            claims,
            claim_type=claim_type,
            classification=classification,
            classification_hash=classification_hash,
        )
        return source_support_check(
            f"---\nSource Map:\n{rows}\n---\n\n{_article(claims)}",
            base_path=tmp,
            fetcher=fetcher_with({SCHEDULING_URL: page_text or " ".join(claims)}),
        )


def _binding_kinds(paragraphs, row_claims):
    body = _article(paragraphs)
    sidecar = f"## Source Map\n{_owned_rows(row_claims)}\n"
    findings = validate_proof_claim_bindings(body, [], [], [], proof_content=sidecar)
    return [finding.get("proof_kind") for finding in findings]


def test_source_support_verifies_rows_for_undetected_capability_sentences():
    claim = "Simpro allows dispatchers to assign jobs from one scheduling board."

    findings = _source_support_findings((claim,), page_text="Unrelated page text.")

    assert findings, "an owned row the binding waiver relies on must be verified"


@pytest.mark.parametrize(
    ("paragraph", "row_claim"),
    [
        (
            "Simpro allows dispatchers to save admin time and grow revenue.",
            "Simpro allows dispatchers",
        ),
        (
            "Simpro allows dispatchers to assign jobs from one scheduling board. "
            "It saves office staff time every week.",
            "Simpro allows dispatchers to assign jobs from one scheduling board.",
        ),
        (
            "Simpro allows dispatchers to assign jobs from one scheduling board. "
            "Teams get paid sooner and grow revenue every month.",
            "Simpro allows dispatchers to assign jobs from one scheduling board. "
            "Teams get paid sooner and grow revenue every month.",
        ),
    ],
)
def test_binding_waiver_keeps_obligation_for_uncovered_outcome_text(paragraph, row_claim):
    assert _binding_kinds((paragraph,), (row_claim,)) == ["commercial_claim"]


def test_binding_waiver_covers_a_whole_capability_sentence():
    claim = "Simpro allows dispatchers to assign jobs from one scheduling board."

    assert _binding_kinds((claim,), (claim,)) == []


def test_owned_feature_sentence_without_simpro_subject_stays_sidecar_only():
    claim = "The mobile app shows each technician the day's jobs."

    report = analyze_proof_links(
        _article((claim,)), f"## Source Map\n{_owned_rows((claim,))}\n", brand="Simpro"
    )

    assert [requirement.mode for requirement in report.requirements] == ["sidecar_only"]


def test_policy_engine_maps_owned_product_claim_rows_to_sidecar_only():
    claims = (
        *PRODUCT_LANGUAGE,
        "Simpro's scheduling board shows technician availability for the day.",
    )

    report = analyze_proof_links(
        _article(claims), f"## Source Map\n{_owned_rows(claims)}\n", brand="Simpro"
    )

    assert len(report.requirements) == len(claims)
    for requirement in report.requirements:
        assert (requirement.mode, requirement.reason) == (
            "sidecar_only",
            "approved_product_language",
        ), requirement.claim


def test_policy_engine_keeps_owned_outcome_numeric_and_status_rows_inline():
    claims = (
        "Simpro reduces the time dispatchers spend on the phone.",
        "Simpro serves 8,000 customers across four countries.",
        "Simpro scheduling is currently available on every plan.",
    )

    report = analyze_proof_links(
        _article(claims), f"## Source Map\n{_owned_rows(claims)}\n", brand="Simpro"
    )

    assert len(report.requirements) == len(claims)
    assert {requirement.mode for requirement in report.requirements} == {"inline_required"}


def test_policy_engine_keeps_section_mode_for_owned_process_rows_not_typed_product_claim():
    claim = "Simpro works by linking each quote to the job it becomes."

    report = analyze_proof_links(
        _article((claim,)),
        f"## Source Map\n{_owned_rows((claim,), claim_type='process')}\n",
        brand="Simpro",
    )

    assert [requirement.mode for requirement in report.requirements] == [
        "section_source_allowed"
    ]


def test_source_support_accepts_owned_product_claim_rows_for_detected_product_language():
    claims = ("Simpro is a software platform for trade contractors.", *PRODUCT_LANGUAGE)

    for claim in claims:
        assert _source_support_findings((claim,)) == [], claim


def test_source_support_rejects_owned_product_claim_rows_for_outcome_claims():
    for claim in (
        "Simpro reduces scheduling conflicts for field service businesses.",
        "Simpro streamlines scheduling for field service businesses.",
    ):
        assert _source_support_findings((claim,)), claim


def test_owned_product_language_passes_every_product_sentence_gate():
    sidecar = f"## Source Map\n{_owned_rows(PRODUCT_LANGUAGE)}\n"
    body = _article(PRODUCT_LANGUAGE)

    research_findings = public_research_link_guard.check_content(
        body, proof_content=sidecar, url_summary=UrlValidationSummary([])
    )
    binding_findings = validate_proof_claim_bindings(body, [], [], [], proof_content=sidecar)

    assert research_findings == []
    assert _source_support_findings(PRODUCT_LANGUAGE) == []
    assert binding_findings == []


class OwnedProductLanguageBindingGeneratorTests(unittest.TestCase):
    setUp = binding_fixture.ContextBindingGuardTests.setUp
    check = binding_fixture.ContextBindingGuardTests.check

    def _generate(self):
        return context_binding_generator.generate_and_install(
            self.article,
            self.request,
            self.pack,
            self.receipt,
            self.sidecar,
            repo_context=[{"path": "context/seo-guidelines.md", "role": "SEO structure"}],
            client=binding_fixture.ValidatingClient(),
        )

    def test_generator_accepts_capability_sentence_backed_by_owned_product_row(self):
        capability = "Simpro allows dispatchers to drag jobs onto the scheduling board."
        pack = json.loads(self.pack.read_text(encoding="utf-8"))
        pack["sections"]["Approved Claim Evidence"][0]["assertion"] = (
            "Simpro helps teams coordinate work."
        )
        self.pack.write_text(json.dumps(pack), encoding="utf-8")
        self.article.write_text(
            self.article.read_text(encoding="utf-8") + f"\n{capability}\n",
            encoding="utf-8",
        )

        with self.assertRaises(context_binding_generator.ContextBindingGenerationError):
            self._generate()

        self.sidecar.write_text(
            f"## Source Map\n{_owned_rows((capability,))}\n", encoding="utf-8"
        )
        self._generate()

        self.assertNotIn(
            "context_proof_claim_unbound",
            {finding["rule_id"] for finding in self.check()},
        )
