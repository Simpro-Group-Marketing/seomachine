from tests.fixture_text import fixture_text

import hashlib
import json
import os
import socket
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from data_sources.modules import source_support_guard
from data_sources.modules.source_support_guard import (
    check_content,
    check_file,
    fetch_source_text,
    require_source_support,
    should_fail,
)


SHAFFER_URL = "https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical"
EBITDA_URL = "https://profitabilitypartners.io/what-is-ebitda-contractors/"
PDF_URL = "https://example.com/report.pdf"
G2_URL = "https://www.g2.com/products/simpro/reviews"
PRODUCTION_IMAGE_PLACEHOLDER = (
    '[IMAGE PLACEHOLDER | source: https://cdn.example.com/hero.png | '
    'alt: "Construction plans and estimating tools" | render target: '
    '1200 x 630 px | resize and compress before upload]'
)


def test_production_image_placeholder_is_not_treated_as_a_numeric_claim():
    findings = check_content(PRODUCTION_IMAGE_PLACEHOLDER)

    assert findings == []


def test_standalone_markdown_image_is_not_treated_as_a_public_claim():
    content = (
        "# Article\n\n"
        "![Prevent employee time theft with GPS time tracking and accurate timesheets]"
        "(https://www.datocms-assets.com/16247/time-theft.png)\n"
    )

    findings = check_content(content)

    assert findings == []


def fetcher_with(source_text_by_url):
    def fetcher(url):
        if url not in source_text_by_url:
            raise RuntimeError(f"missing mocked source for {url}")
        return source_text_by_url[url]

    return fetcher


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_source_classification(directory, url, source_class, relationship):
    path = Path(directory) / "source-classification.json"
    source_support_guard.write_source_classification_artifact(
        path,
        source_url=url,
        source_class=source_class,
        publisher_relationship=relationship,
        record_id="source:test-record",
        revision="test-revision-1",
        workspace_root=directory,
    )
    return path.name, _sha256(path)


def write_plain_source_classification(directory, url, source_class, relationship):
    path = Path(directory) / "plain-source-classification.json"
    payload = {
        "schema": "simpro-source-classification/v1",
        "source_url": url,
        "source_class": source_class,
        "classified_at": _utc_now(),
        "publisher": {
            "hostname": url.split("/", 3)[2],
            "relationship": relationship,
        },
        "registry": {
            "record_id": "source:caller-authored",
            "revision": "caller-authored-revision",
        },
        "emitter": {
            "name": "source_registry_export",
            "version": "1.0.0",
        },
    }
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path.name, _sha256(path)


def write_capture_receipt(directory, url, artifact_name, *, method):
    artifact_path = Path(directory) / artifact_name
    source_content_path = Path(directory) / "captured-source-input.bin"
    source_content_path.write_bytes(f"captured bytes for {url}".encode("utf-8"))
    path = Path(directory) / "source-capture-receipt.json"
    source_support_guard.write_source_capture_receipt(
        path,
        source_url=url,
        source_content_path=source_content_path,
        artifact_path=artifact_path,
        artifact_reference=artifact_name,
        method=method,
        workspace_root=directory,
    )
    return path.name, _sha256(path)


def write_plain_capture_receipt(directory, url, artifact_name, *, method):
    artifact_path = Path(directory) / artifact_name
    artifact_hash = _sha256(artifact_path)
    path = Path(directory) / "plain-source-capture-receipt.json"
    payload = {
        "schema": "simpro-source-capture-receipt/v1",
        "source_url": url,
        "retrieved_at": _utc_now(),
        "source_content_sha256": "a" * 64,
        "artifact": {
            "path": artifact_name,
            "sha256": artifact_hash,
        },
        "extraction": {
            "method": method,
            "tool_name": "source_support_capture",
            "tool_version": "1.0.0",
            "input_sha256": "a" * 64,
            "output_sha256": artifact_hash,
        },
        "emitter": {
            "name": "source_support_capture",
            "version": "1.0.0",
        },
    }
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path.name, _sha256(path)


class SourceSupportGuardTests(unittest.TestCase):
    def test_one_authority_can_support_a_table_row_with_multiple_evidence_snippets(self):
        url = "https://regulator.example.gov/tradesman"
        content = f"""# License guide

| License | Current fees |
|---|---|
| Tradesman license | A $36 exam fee and a $35 initial license fee. See [Tradesman requirements]({url}). |
"""
        sidecar = f"""## Source Map
- Claim: $36 exam fee | URL: {url} | Evidence: Exam Fee: $36 | Status: approved
- Claim: $35 initial license fee | URL: {url} | Evidence: Initial License Fee: $35 | Status: approved
"""

        findings = check_content(
            content,
            proof_content=sidecar,
            fetcher=fetcher_with(
                {url: "Fees. Exam Fee: $36. Initial License Fee: $35."}
            ),
        )

        self.assertEqual(findings, [])

    def test_short_exact_numeric_claim_can_bind_without_two_lexical_words(self):
        url = "https://regulator.example.gov/apprentice"
        content = f"""# License guide

| Registration | Age |
|---|---|
| Apprentice | Be at least 16. See [Apprentice requirements]({url}). |
"""
        sidecar = f"""## Source Map
- Claim: Be at least 16 | URL: {url} | Evidence: you are at least 16 years old | Status: approved
"""

        findings = check_content(
            content,
            proof_content=sidecar,
            fetcher=fetcher_with({url: "you are at least 16 years old"}),
        )

        self.assertEqual(findings, [])

    def test_table_row_fails_when_evidence_snippets_leave_a_material_number_unmapped(self):
        url = "https://regulator.example.gov/tradesman"
        content = f"""# License guide

| License | Current fees |
|---|---|
| Tradesman license | A $36 exam fee, a $35 initial license fee, and a $99 renewal fee. See [Tradesman requirements]({url}). |
"""
        sidecar = f"""## Source Map
- Claim: $36 exam fee | URL: {url} | Evidence: Exam Fee: $36 | Status: approved
- Claim: $35 initial license fee | URL: {url} | Evidence: Initial License Fee: $35 | Status: approved
"""

        findings = check_content(
            content,
            proof_content=sidecar,
            fetcher=fetcher_with(
                {url: "Fees. Exam Fee: $36. Initial License Fee: $35."}
            ),
        )

        self.assertTrue(findings)
        self.assertTrue(
            any(finding["rule_id"] == "missing_strict_proof" for finding in findings)
        )

    def test_numeric_table_proof_does_not_hide_an_unmapped_legal_scope_claim(self):
        url = "https://regulator.example.gov/tradesman"
        content = f"""# License guide

| License | Fee and scope |
|---|---|
| Tradesman license | A $36 exam fee applies, and work is permitted only under direct supervision. See [Tradesman requirements]({url}). |
"""
        sidecar = f"""## Source Map
- Claim: $36 exam fee | URL: {url} | Evidence: Exam Fee: $36 | Status: approved
"""

        findings = check_content(
            content,
            proof_content=sidecar,
            fetcher=fetcher_with({url: "Fees. Exam Fee: $36."}),
        )

        self.assertTrue(findings)
        self.assertTrue(
            any(
                "direct supervision" in finding.get("match", "")
                for finding in findings
            )
        )

    def test_general_claim_detection_covers_unmistakable_assertion_forms(self):
        claims = (
            "A shared dispatch board helps teams reduce assignment conflicts.",
            "A standardized intake form streamlines handoffs between dispatch and field teams.",
            "Unlike manual boards, scheduling software updates assignments in one shared view.",
            "Manual boards require separate updates, whereas scheduling software keeps one shared queue.",
            "A work order is a document that authorizes specific field service tasks.",
            "Dispatching is when a coordinator assigns available technicians to jobs.",
            "First confirm technician availability, then assign the job, and finally notify the customer.",
            "The dispatch process moves from triage to assignment to confirmation.",
            "Do not dispatch a technician until the required license is confirmed.",
        )

        for claim in claims:
            with self.subTest(claim=claim):
                findings = check_content(f"# Scheduling guide\n\n{claim}\n")

                self.assertEqual(
                    [finding["rule_id"] for finding in findings],
                    ["general_claim_source_missing"],
                )

    def test_general_claim_detection_does_not_sweep_navigation_or_descriptive_prose(self):
        ordinary_sentences = (
            "This guide helps readers navigate the scheduling examples below.",
            "Unlike the previous section, this section covers invoice timing.",
            "First, this article explains scheduling; then, it introduces invoicing.",
            "Review the next section for implementation details.",
            "Review technician capacity before assigning urgent work.",
            "Confirm the job type and supervisor before accepting an assignment.",
            "Check the application details before sending the form.",
            "Dispatchers review capacity during the morning meeting.",
            "The example is a document excerpt used for discussion.",
        )

        for sentence in ordinary_sentences:
            with self.subTest(sentence=sentence):
                self.assertEqual(
                    check_content(f"# Scheduling guide\n\n{sentence}\n"),
                    [],
                )

    def test_faq_answers_with_faq_proof_map_are_not_source_support_duplicates(self):
        content = """# Texas plumbing license

## Frequently asked questions

### What is the difference between a Master Plumber and a Responsible Master Plumber?

Master Plumber is a Texas license. Responsible Master Plumber is a designation. The [TSBPE RMP requirements](https://tsbpe.texas.gov/license-types/responsible-master-plumber/) also require good standing and at least $300,000 in commercial liability insurance.
"""
        sidecar = """## FAQ Source Policy
- Allowed source classes: neutral, non_competing_expert.
- Competitor-owned FAQ sources: prohibited.
- Status: aligned.

## FAQ Proof Map
- FAQ: What is the difference between a Master Plumber and a Responsible Master Plumber? | URL: https://tsbpe.texas.gov/license-types/responsible-master-plumber/ | Source class: neutral | Competitor check: passed | Support: Current official RMP requirements distinguish the designation from the Master license.
"""

        self.assertEqual(check_content(content, proof_content=sidecar), [])

    def test_proof_not_required_advice_does_not_exempt_risky_or_factual_claims(self):
        claims = (
            "Review the licensing rules before assigning regulated work.",
            "Check the local authority before starting work, even when the state exemption applies.",
            "Check the local authority before starting homestead work.",
            "Start the renewal process 60 days before expiration.",
            "Organizing applications reduces processing delays.",
            "A careful renewal approach is better than waiting.",
            "Review technician capacity before assigning urgent work. This can help teams find scheduling gaps.",
        )

        for claim in claims:
            with self.subTest(claim=claim):
                findings = check_content(f"# Licensing guide\n\n{claim}\n")

                self.assertTrue(findings)
                self.assertTrue(
                    any(
                        finding["rule_id"]
                        in {"general_claim_source_missing", "missing_strict_proof"}
                        for finding in findings
                    )
                )

    def test_fact_free_advice_in_high_risk_paragraph_needs_no_separate_mapping(self):
        advice = "Confirm the job type and supervisor before accepting an assignment."
        content = (
            "# Tradesman work\n\n"
            "A Tradesman performs plumbing only under the direct supervision of a "
            f"Journeyman or Master Plumber. {advice}\n"
        )

        findings = check_content(content)

        self.assertTrue(findings)
        self.assertFalse(
            any(finding.get("match") == advice for finding in findings)
        )

    def test_all_planned_general_claim_classes_are_detected(self):
        claims = (
            "Capacity planning drives fewer assignment conflicts.",
            "Automated scheduling produces higher utilization than manual boards.",
            "A dispatch queue is a prioritized list of jobs.",
            "The scheduling workflow follows a sequence of assessment, assignment, and confirmation.",
            "It is advisable to verify technician certifications before dispatch.",
        )

        for claim in claims:
            with self.subTest(claim=claim):
                findings = check_content(f"# Scheduling guide\n\n{claim}\n")

                self.assertEqual(
                    [finding["rule_id"] for finding in findings],
                    ["general_claim_source_missing"],
                )

    def test_general_recommendation_requires_claim_fit_source_map_row(self):
        content = fixture_text("content_evidence:test_source_support_guard-188-1")

        findings = check_content(content, fetcher=fetcher_with({}))

        self.assertIn("general_claim_source_missing", [row["rule_id"] for row in findings])

    def test_general_claim_requires_registry_backed_source_classification(self):
        url = "https://example.com/scheduling-guidance"
        claim = "Field service leaders should review technician capacity before assigning urgent work."
        content = f"""---
Source Map:
- Claim: {claim} | Claim type: recommendation | Source class: non_competing_expert | Evidence relation: directly_supports | URL: {url} | Evidence: "review technician capacity before assigning urgent work" | Status: approved
---

# Scheduling guide

{claim}
"""

        findings = check_content(
            content,
            fetcher=fetcher_with(
                {url: "Experts should review technician capacity before assigning urgent work."}
            ),
        )

        self.assertIn(
            "source_classification_artifact_missing",
            [finding["rule_id"] for finding in findings],
        )

    def test_caller_authored_rehashed_source_classification_is_not_tool_evidence(self):
        url = "https://example.com/scheduling-guidance"
        claim = "Field service leaders should review technician capacity before assigning urgent work."
        evidence = "Field service leaders should review technician capacity before assigning urgent work."
        with tempfile.TemporaryDirectory() as tmp:
            classification, classification_hash = write_plain_source_classification(
                tmp,
                url,
                "non_competing_expert",
                "independent",
            )
            content = f"""---
Source Map:
- Claim: {claim} | Claim type: recommendation | Source class: non_competing_expert | Evidence relation: directly_supports | Classification artifact: {classification} | Classification hash: {classification_hash} | URL: {url} | Evidence: \"{evidence}\" | Status: approved
---

# Scheduling guide

{claim}
"""

            findings = check_content(
                content,
                base_path=tmp,
                fetcher=fetcher_with({url: evidence}),
            )

        self.assertIn(
            "source_classification_execution_attestation_invalid",
            [finding["rule_id"] for finding in findings],
        )

    def test_source_classification_emitter_writes_atomic_attested_artifact(self):
        self.assertTrue(
            hasattr(source_support_guard, "write_source_classification_artifact"),
            "source classification emitter is missing",
        )
        url = "https://example.com/scheduling-guidance"
        claim = "Field service leaders should review technician capacity before assigning urgent work."
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "source-classification.json"
            payload = source_support_guard.write_source_classification_artifact(
                output,
                source_url=url,
                source_class="non_competing_expert",
                publisher_relationship="independent",
                record_id="source:test-record",
                revision="test-revision-1",
                workspace_root=tmp,
            )
            stored = json.loads(output.read_text(encoding="utf-8"))
            content = f"""---
Source Map:
- Claim: {claim} | Claim type: recommendation | Source class: non_competing_expert | Evidence relation: directly_supports | Classification artifact: {output.name} | Classification hash: {_sha256(output)} | URL: {url} | Evidence: \"{claim}\" | Status: approved
---

# Scheduling guide

{claim}
"""
            findings = check_content(
                content,
                base_path=tmp,
                fetcher=fetcher_with({url: claim}),
            )

            self.assertEqual(stored, payload)
            self.assertIn("execution_attestation", payload)
            self.assertFalse(any(path.name.endswith(".tmp") for path in Path(tmp).iterdir()))
            self.assertEqual(findings, [])

    def test_general_claim_rejects_two_word_overlap_instead_of_claim_binding(self):
        url = "https://example.com/scheduling-guidance"
        article_claim = "Field service leaders should review technician capacity before assigning urgent work."
        mapped_claim = "Technician capacity improves profitability."
        evidence = "Technician capacity improves profitability."
        with tempfile.TemporaryDirectory() as tmp:
            classification, classification_hash = write_source_classification(
                tmp,
                url,
                "non_competing_expert",
                "independent",
            )
            content = f"""---
Source Map:
- Claim: {mapped_claim} | Claim type: recommendation | Source class: non_competing_expert | Evidence relation: directly_supports | Classification artifact: {classification} | Classification hash: {classification_hash} | URL: {url} | Evidence: "{evidence}" | Status: approved
---

# Scheduling guide

{article_claim}
"""

            findings = check_content(
                content,
                base_path=tmp,
                fetcher=fetcher_with({url: evidence}),
            )

        self.assertIn(
            "source_claim_binding_mismatch",
            [finding["rule_id"] for finding in findings],
        )

    def test_general_claim_rejects_source_evidence_that_contradicts_it(self):
        url = "https://example.com/dispatch-research"
        claim = "Digital dispatch improves field coordination."
        evidence = "Digital dispatch does not improve field coordination."
        with tempfile.TemporaryDirectory() as tmp:
            classification, classification_hash = write_source_classification(
                tmp,
                url,
                "independent_research",
                "independent",
            )
            content = f"""---
Source Map:
- Claim: {claim} | Claim type: causal | Source class: independent_research | Evidence relation: directly_supports | Classification artifact: {classification} | Classification hash: {classification_hash} | URL: {url} | Evidence: "{evidence}" | Status: approved
---

# Dispatch research

{claim}
"""

            findings = check_content(
                content,
                base_path=tmp,
                fetcher=fetcher_with({url: evidence}),
            )

        self.assertIn(
            "source_evidence_contradicts_claim",
            [finding["rule_id"] for finding in findings],
        )

    def test_general_claim_rejects_relabelled_competitor_classification(self):
        url = "https://competitor.example/scheduling-guidance"
        claim = "Field service leaders should review technician capacity before assigning urgent work."
        evidence = "Leaders should review technician capacity before assigning urgent work."
        with tempfile.TemporaryDirectory() as tmp:
            classification, classification_hash = write_source_classification(
                tmp,
                url,
                "competitor",
                "competitor",
            )
            content = f"""---
Source Map:
- Claim: {claim} | Claim type: recommendation | Source class: non_competing_expert | Evidence relation: directly_supports | Classification artifact: {classification} | Classification hash: {classification_hash} | URL: {url} | Evidence: "{evidence}" | Status: approved
---

# Scheduling guide

{claim}
"""

            findings = check_content(
                content,
                base_path=tmp,
                fetcher=fetcher_with({url: evidence}),
            )

        self.assertIn(
            "source_classification_mismatch",
            [finding["rule_id"] for finding in findings],
        )

    def test_general_claim_requires_a_public_http_source_url(self):
        url = "ftp://example.com/scheduling-guidance"
        claim = "Field service leaders should review technician capacity before assigning urgent work."
        evidence = "Leaders should review technician capacity before assigning urgent work."
        with tempfile.TemporaryDirectory() as tmp:
            classification, classification_hash = write_source_classification(
                tmp,
                url,
                "non_competing_expert",
                "independent",
            )
            content = f"""---
Source Map:
- Claim: {claim} | Claim type: recommendation | Source class: non_competing_expert | Evidence relation: directly_supports | Classification artifact: {classification} | Classification hash: {classification_hash} | URL: {url} | Evidence: "{evidence}" | Status: approved
---

# Scheduling guide

{claim}
"""

            findings = check_content(
                content,
                base_path=tmp,
                fetcher=fetcher_with({url: evidence}),
            )

        self.assertIn(
            "source_url_not_public",
            [finding["rule_id"] for finding in findings],
        )

    def test_each_general_claim_sentence_requires_its_own_exact_mapping(self):
        url = "https://example.com/scheduling-guidance"
        supported_claim = "Capacity planning drives fewer assignment conflicts."
        unsupported_claim = "It is advisable to verify technician certifications before dispatch."
        evidence = "Capacity planning drives fewer assignment conflicts."
        with tempfile.TemporaryDirectory() as tmp:
            classification, classification_hash = write_source_classification(
                tmp,
                url,
                "independent_research",
                "independent",
            )
            content = f"""---
Source Map:
- Claim: {supported_claim} | Claim type: causal | Source class: independent_research | Evidence relation: directly_supports | Classification artifact: {classification} | Classification hash: {classification_hash} | URL: {url} | Evidence: "{evidence}" | Status: approved
---

# Scheduling guide

{supported_claim} {unsupported_claim}
"""

            findings = check_content(
                content,
                base_path=tmp,
                fetcher=fetcher_with({url: evidence}),
            )

        self.assertEqual(
            [finding["rule_id"] for finding in findings],
            ["general_claim_source_missing"],
        )

    def test_general_claim_passes_with_exact_source_class_and_claim_type(self):
        url = "https://example.com/scheduling-guidance"
        with tempfile.TemporaryDirectory() as tmp:
            classification, classification_hash = write_source_classification(
                tmp,
                url,
                "non_competing_expert",
                "independent",
            )
            content = f"""---
Source Map:
- Claim: Field service leaders should review technician capacity before assigning urgent work | Claim type: recommendation | Source class: non_competing_expert | Evidence relation: directly_supports | Classification artifact: {classification} | Classification hash: {classification_hash} | URL: {url} | Evidence: "review technician capacity before assigning urgent work" | Status: approved
---

# Scheduling guide

Field service leaders should review technician capacity before assigning urgent work.
"""

            findings = check_content(
                content,
                base_path=tmp,
                fetcher=fetcher_with(
                    {url: "Experts should review technician capacity before assigning urgent work."}
                ),
            )

        self.assertEqual(findings, [])

    def test_general_claim_rejects_unknown_source_class(self):
        url = "https://example.com/scheduling-guidance"
        content = f"""---
Source Map:
- Claim: Field service leaders should review technician capacity before assigning urgent work | Claim type: recommendation | Source class: blog | URL: {url} | Evidence: "review technician capacity before assigning urgent work" | Status: approved
---

# Scheduling guide

Field service leaders should review technician capacity before assigning urgent work.
"""

        findings = check_content(
            content,
            fetcher=fetcher_with(
                {url: "Experts should review technician capacity before assigning urgent work."}
            ),
        )

        self.assertIn("source_class_invalid", [row["rule_id"] for row in findings])

    def test_general_claim_rejects_mismatched_claim_type(self):
        url = "https://example.com/scheduling-guidance"
        content = f"""---
Source Map:
- Claim: Field service leaders should review technician capacity before assigning urgent work | Claim type: definition | Source class: non_competing_expert | URL: {url} | Evidence: "review technician capacity before assigning urgent work" | Status: approved
---

# Scheduling guide

Field service leaders should review technician capacity before assigning urgent work.
"""

        findings = check_content(
            content,
            fetcher=fetcher_with(
                {url: "Experts should review technician capacity before assigning urgent work."}
            ),
        )

        self.assertIn("source_claim_type_mismatch", [row["rule_id"] for row in findings])

    def test_general_causal_and_process_language_requires_claim_fit_source(self):
        content = fixture_text("content_evidence:test_source_support_guard-527-2")

        findings = check_content(content)

        self.assertEqual(
            [row["rule_id"] for row in findings],
            ["general_claim_source_missing", "general_claim_source_missing"],
        )

    def test_any_claim_fit_row_can_satisfy_claim_when_an_earlier_row_is_weak(self):
        url = "https://example.org/scheduling"
        with tempfile.TemporaryDirectory() as tmp:
            owned_classification, owned_hash = write_source_classification(
                tmp,
                url,
                "owned_product",
                "owned",
            )
            owned_path = Path(tmp) / owned_classification
            owned_path.rename(Path(tmp) / "owned-classification.json")
            owned_classification = "owned-classification.json"
            owned_hash = _sha256(Path(tmp) / owned_classification)
            classification, classification_hash = write_source_classification(
                tmp,
                url,
                "non_competing_expert",
                "independent",
            )
            content = f"""---
Source Map:
- Claim: Field service leaders should review technician capacity before assigning urgent work | Claim type: recommendation | Source class: owned_product | Evidence relation: directly_supports | Classification artifact: {owned_classification} | Classification hash: {owned_hash} | URL: {url} | Evidence: "review technician capacity before assigning urgent work" | Status: approved
- Claim: Field service leaders should review technician capacity before assigning urgent work | Claim type: recommendation | Source class: non_competing_expert | Evidence relation: directly_supports | Classification artifact: {classification} | Classification hash: {classification_hash} | URL: {url} | Evidence: "review technician capacity before assigning urgent work" | Status: approved
---

# Scheduling workflow

Field service leaders should review technician capacity before assigning urgent work.
"""

            findings = check_content(
                content,
                base_path=tmp,
                fetcher=fetcher_with(
                    {url: "Field service leaders should review technician capacity before assigning urgent work."}
                ),
            )

        self.assertEqual(findings, [])

    def test_owned_product_source_cannot_support_general_outcome_or_advice_claims(self):
        url = "https://www.simprogroup.com/features/scheduling/"
        cases = (
            (
                "causal",
                "Simpro reduces scheduling conflicts for field service businesses.",
            ),
            (
                "causal",
                "Simpro improves first-time fix rates for field service businesses.",
            ),
            (
                "recommendation",
                "Field service businesses should choose Simpro for scheduling.",
            ),
            (
                "comparative",
                "Simpro is faster than manual scheduling.",
            ),
        )

        for claim_type, claim in cases:
            with self.subTest(claim_type=claim_type, claim=claim):
                with tempfile.TemporaryDirectory() as tmp:
                    classification, classification_hash = write_source_classification(
                        tmp,
                        url,
                        "owned_product",
                        "owned",
                    )
                    content = f'''---
Source Map:
- Claim: {claim} | Claim type: {claim_type} | Source class: owned_product | Evidence relation: directly_supports | Classification artifact: {classification} | Classification hash: {classification_hash} | URL: {url} | Evidence: "{claim}" | Status: approved
---

# Scheduling guide

{claim}
'''

                    findings = check_content(
                        content,
                        base_path=tmp,
                        fetcher=fetcher_with({url: claim}),
                    )

                self.assertIn(
                    "source_class_claim_fit_invalid",
                    [row["rule_id"] for row in findings],
                )

    def test_owned_product_source_can_support_a_simpro_product_process_fact(self):
        url = "https://www.simprogroup.com/features/scheduling/"
        claim = "Simpro works by connecting scheduling and job details in one workflow."
        with tempfile.TemporaryDirectory() as tmp:
            classification, classification_hash = write_source_classification(
                tmp,
                url,
                "owned_product",
                "owned",
            )
            content = f'''---
Source Map:
- Claim: {claim} | Claim type: process | Source class: owned_product | Evidence relation: directly_supports | Classification artifact: {classification} | Classification hash: {classification_hash} | URL: {url} | Evidence: "{claim}" | Status: approved
---

# Scheduling guide

{claim}
'''

            findings = check_content(
                content,
                base_path=tmp,
                fetcher=fetcher_with({url: claim}),
            )

        self.assertEqual(findings, [])

    def test_fetch_source_text_uses_builtin_file_cache_when_diskcache_is_unavailable(self):
        class FakeResponse:
            text = "<html><body>Visible proof text for source support.</body></html>"

            def raise_for_status(self):
                return None

        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            try:
                request = Mock(return_value=FakeResponse())
                with patch("data_sources.modules.source_support_guard.Cache", None), patch(
                    "data_sources.modules.source_support_guard.request_public_url",
                    request,
                ):
                    first = fetch_source_text("https://example.com/source")
                    second = fetch_source_text("https://example.com/source")

                self.assertIn("Visible proof text", first)
                self.assertEqual(first, second)
                self.assertEqual(request.call_count, 1)
            finally:
                os.chdir(old_cwd)

    def test_fetch_source_text_blocks_private_destination_before_request(self):
        def resolver(host, port, *, type=socket.SOCK_STREAM):
            return [(socket.AF_INET, type, 6, "", ("169.254.169.254", port))]

        with self.assertRaisesRegex(ValueError, "not public"):
            fetch_source_text(
                "http://metadata.example/latest/meta-data",
                resolver=resolver,
            )

    def test_contextual_case_study_link_passes_with_case_study_proof_path(self):
        content = f"""---
Customer Proof Pack:
- Case-study proof paths: Shaffer Beacon Mechanical, {SHAFFER_URL}, supported non-numeric theme: HVAC/plumbing operations perspective
---

# HVAC franchise software

[The Shaffer Beacon Mechanical case study]({SHAFFER_URL}) adds an HVAC and plumbing operator perspective to the discussion of franchise-ready field workflows.
"""

        findings = check_content(content, fetcher=fetcher_with({}))

        self.assertEqual(findings, [])

    def test_review_site_paraphrased_context_passes_with_review_experience_evidence(self):
        content = f"""---
Customer Proof Pack:
- Review-site experience evidence: G2, {G2_URL}, date checked 2026-06-09, product: Simpro, experience pattern: field workflow pain, evidence summary: reviewers discuss dispatch and field visibility, exact quote/rating approval status: not approved
---

# Field service software

Public review themes can inform a paraphrased E-E-A-T discussion of field workflow pain, without naming a reviewer or using ratings.
"""

        findings = check_content(content, fetcher=fetcher_with({}))

        self.assertEqual(findings, [])

    def test_named_customer_outcome_without_number_requires_claim_row(self):
        content = f"""---
Customer Proof Pack:
- Case-study proof paths: Shaffer Beacon Mechanical, {SHAFFER_URL}, supported non-numeric theme: centralized job data
---

# HVAC franchise software

[Shaffer Beacon Mechanical]({SHAFFER_URL}) centralized job data across office and field teams.
"""

        findings = check_content(content, fetcher=fetcher_with({}))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "missing_strict_proof")

    def test_regulator_claim_names_are_not_inferred_as_customer_names(self):
        url = "https://regulator.example.gov/apprentice"
        content = (
            "# License guide\n\n"
            f"The [TSBPE Apprentice requirements]({url}) list a $15 registration fee.\n"
        )
        sidecar = f"""## Source Map
- Claim: The TSBPE Apprentice requirements list a $15 registration fee. | Source class: primary_authority | URL: {url} | Evidence: Registration fee: $15 | Status: approved
"""

        findings = check_content(
            content,
            proof_content=sidecar,
            fetcher=fetcher_with({url: "Registration fee: $15"}),
        )

        self.assertFalse(
            any(
                finding["rule_id"]
                in {
                    "named_customer_metric_requires_approved_metric",
                    "named_customer_metric_requires_approved_metric",
                }
                for finding in findings
            )
        )

    def test_shaffer_60_percent_claim_fails_when_source_lacks_evidence(self):
        content = f"""---
Source Map:
- Claim: Shaffer Beacon Mechanical achieved a 60% increase in profit margin | URL: {SHAFFER_URL} | Evidence: "60% increase in profit margin" | Status: approved | Use: named customer metric
---

# HVAC franchise software

Standardized operations software is what makes brand standards enforceable. [Shaffer Beacon Mechanical]({SHAFFER_URL}), an HVAC and mechanical contractor, achieved a 60% increase in profit margin using Simpro's real-time job costing workflows.
"""

        findings = check_content(
            content,
            fetcher=fetcher_with(
                {
                    SHAFFER_URL: (
                        "Shaffer Beacon Mechanical is an HVAC & Plumbing contractor. "
                        "Simpro helped centralize data, increased profits, and can "
                        "process twice the amount of business with the same resources."
                    )
                }
            ),
        )

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "source_evidence_not_found")
        self.assertIn("60%", findings[0]["match"])

    def test_corrected_shaffer_claim_passes_with_customer_proof_pack_evidence(self):
        content = f"""---
Customer Proof Pack:
- Claim: Shaffer Beacon Mechanical can process twice the amount of business with the same resources | URL: {SHAFFER_URL} | Evidence: "We can process twice the amount of business with the same amount of resources" | Status: approved | Use: paraphrased customer outcome
---

# HVAC franchise software

Standardized operations software is what makes brand standards enforceable. [Shaffer Beacon Mechanical]({SHAFFER_URL}), an HVAC and plumbing contractor, used Simpro to centralize job data and process twice the amount of business with the same resources.
"""

        findings = check_content(
            content,
            fetcher=fetcher_with(
                {
                    SHAFFER_URL: (
                        "Simpro helped the team at Shaffer Beacon centralize all of "
                        "their data. \"We can process twice the amount of business "
                        "with the same amount of resources,\" Hrdlicka said."
                    )
                }
            ),
        )

        self.assertEqual(findings, [])

    def test_named_customer_metric_fails_when_only_source_map_approves_it(self):
        content = f"""---
Source Map:
- Claim: Shaffer Beacon Mechanical achieved a 60% increase in profit margin | URL: {SHAFFER_URL} | Evidence: "60% increase in profit margin" | Status: approved | Use: named customer metric
---

# HVAC franchise software

[Shaffer Beacon Mechanical]({SHAFFER_URL}) achieved a 60% increase in profit margin using Simpro job costing workflows.
"""

        findings = check_content(
            content,
            fetcher=fetcher_with({SHAFFER_URL: "Shaffer Beacon Mechanical achieved a 60% increase in profit margin."}),
        )

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "named_customer_metric_requires_approved_metric")

    def test_named_customer_metric_passes_with_approved_metric_row(self):
        content = f"""---
Customer Proof Pack:
- Approved metric: Shaffer Beacon Mechanical achieved a 60% increase in profit margin | Customer/brand: Shaffer Beacon Mechanical | URL: {SHAFFER_URL} | Evidence: "60% increase in profit margin" | Status: approved
---

# HVAC franchise software

[Shaffer Beacon Mechanical]({SHAFFER_URL}) achieved a 60% increase in profit margin using Simpro job costing workflows.
"""

        findings = check_content(
            content,
            fetcher=fetcher_with({SHAFFER_URL: "Shaffer Beacon Mechanical achieved a 60% increase in profit margin."}),
        )

        self.assertEqual(findings, [])

    def test_named_customer_metric_passes_with_sidecar_approved_metric_row(self):
        content = f"""# HVAC franchise software

[Shaffer Beacon Mechanical]({SHAFFER_URL}) achieved a 60% increase in profit margin using Simpro job costing workflows.
"""
        sidecar = f"""Customer Proof Pack
- Approved metric: Shaffer Beacon Mechanical achieved a 60% increase in profit margin | Customer/brand: Shaffer Beacon Mechanical | URL: {SHAFFER_URL} | Evidence: "60% increase in profit margin" | Status: approved
"""

        findings = check_content(
            content,
            proof_content=sidecar,
            fetcher=fetcher_with({SHAFFER_URL: "Shaffer Beacon Mechanical achieved a 60% increase in profit margin."}),
        )

        self.assertEqual(findings, [])

    def test_spelled_out_named_customer_metric_passes_with_approved_metric_row(self):
        bge_url = "https://www.simprogroup.com/case-studies/bge-digital"
        content = f"""---
Customer Proof Pack:
- Approved metric: BGE Digital put quotes out ten times quicker than spreadsheets | Customer/brand: BGE Digital | URL: {bge_url} | Evidence: "put a quote out ten times quicker" | Status: approved
---

# Quoting workflow

[BGE Digital]({bge_url}) put quotes out ten times quicker than spreadsheets after changing its quoting workflow.
"""

        findings = check_content(
            content,
            fetcher=fetcher_with({bge_url: "BGE Digital can put a quote out ten times quicker than spreadsheets."}),
        )

        self.assertEqual(findings, [])

    def test_ebitda_claim_passes_when_source_contains_evidence(self):
        content = f"""---
Source Map:
- Claim: HVAC operators should target 15% to 20% EBITDA margins | URL: {EBITDA_URL} | Evidence: "15% to 20% EBITDA margins" | Status: approved | Use: FAQ benchmark
---

# HVAC profitability

Well-run HVAC operators should target [15% to 20% EBITDA margins]({EBITDA_URL}) when service, replacement, and maintenance work are balanced.
"""

        findings = check_content(
            content,
            fetcher=fetcher_with({EBITDA_URL: "HVAC companies should target 15% to 20% EBITDA margins when well run."}),
        )

        self.assertEqual(findings, [])

    def test_source_that_lacks_evidence_snippet_fails(self):
        content = f"""---
Source Map:
- Claim: HVAC operators should target 15% to 20% EBITDA margins | URL: {EBITDA_URL} | Evidence: "15% to 20% EBITDA margins" | Status: approved | Use: FAQ benchmark
---

# HVAC profitability

Well-run HVAC operators should target [15% to 20% EBITDA margins]({EBITDA_URL}) when service, replacement, and maintenance work are balanced.
"""

        findings = check_content(
            content,
            fetcher=fetcher_with({EBITDA_URL: "HVAC companies need clean books and disciplined reporting."}),
        )

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "source_evidence_not_found")

    def test_context_only_proof_path_fails(self):
        content = fixture_text("content_evidence:test_source_support_guard-906-3")

        findings = check_content(content, fetcher=fetcher_with({}))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "missing_strict_proof")

    def test_pdf_source_without_local_text_artifact_fails(self):
        content = f"""---
Source Map:
- Claim: Specialty trade contractors reported adjusted EBITDA margins from 18.1% to 20.4% | URL: {PDF_URL} | Evidence: "18.1% to 20.4%" | Status: approved | Use: benchmark
---

# HVAC profitability

Specialty trade contractors reported adjusted EBITDA margins from 18.1% to 20.4%.
"""

        findings = check_content(content, fetcher=fetcher_with({}))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "unsupported_pdf_source")

    def test_pdf_source_with_locally_authored_artifact_but_no_capture_receipt_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            proof = Path(tmp) / "gf-data-proof.md"
            proof.write_text("Specialty trades adjusted EBITDA margin was 18.1% to 20.4%.", encoding="utf-8")
            content = f"""---
Source Map:
- Claim: Specialty trade contractors reported adjusted EBITDA margins from 18.1% to 20.4% | URL: {PDF_URL} | Evidence: "18.1% to 20.4%" | Artifact: gf-data-proof.md | Status: approved | Use: benchmark
---

# HVAC profitability

Specialty trade contractors reported adjusted EBITDA margins from 18.1% to 20.4%.
"""

            findings = check_content(content, base_path=tmp, fetcher=fetcher_with({}))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "source_capture_receipt_missing")

    def test_caller_authored_rehashed_capture_receipt_is_not_tool_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            proof = Path(tmp) / "gf-data-proof.md"
            proof.write_text(
                "Specialty trades adjusted EBITDA margin was 18.1% to 20.4%.",
                encoding="utf-8",
            )
            receipt, receipt_hash = write_plain_capture_receipt(
                tmp,
                PDF_URL,
                proof.name,
                method="pdf_text",
            )
            content = f"""---
Source Map:
- Claim: Specialty trade contractors reported adjusted EBITDA margins from 18.1% to 20.4% | URL: {PDF_URL} | Evidence: "18.1% to 20.4%" | Artifact: {proof.name} | Capture receipt: {receipt} | Capture receipt hash: {receipt_hash} | Status: approved | Use: benchmark
---

# HVAC profitability

Specialty trade contractors reported adjusted EBITDA margins from 18.1% to 20.4%.
"""

            findings = check_content(content, base_path=tmp, fetcher=fetcher_with({}))

        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["rule_id"],
            "source_capture_execution_attestation_invalid",
        )

    def test_source_capture_emitter_writes_atomic_attested_receipt(self):
        self.assertTrue(
            hasattr(source_support_guard, "write_source_capture_receipt"),
            "source capture emitter is missing",
        )
        with tempfile.TemporaryDirectory() as tmp:
            source_content = Path(tmp) / "captured-source.pdf"
            source_content.write_bytes(b"captured source bytes")
            proof = Path(tmp) / "gf-data-proof.md"
            proof.write_text(
                "Specialty trades adjusted EBITDA margin was 18.1% to 20.4%.",
                encoding="utf-8",
            )
            output = Path(tmp) / "source-capture-receipt.json"
            payload = source_support_guard.write_source_capture_receipt(
                output,
                source_url=PDF_URL,
                source_content_path=source_content,
                artifact_path=proof,
                artifact_reference=proof.name,
                method="pdf_text",
                workspace_root=tmp,
            )
            stored = json.loads(output.read_text(encoding="utf-8"))
            content = f"""---
Source Map:
- Claim: Specialty trade contractors reported adjusted EBITDA margins from 18.1% to 20.4% | URL: {PDF_URL} | Evidence: "18.1% to 20.4%" | Artifact: {proof.name} | Capture receipt: {output.name} | Capture receipt hash: {_sha256(output)} | Status: approved | Use: benchmark
---

# HVAC profitability

Specialty trade contractors reported adjusted EBITDA margins from 18.1% to 20.4%.
"""
            findings = check_content(content, base_path=tmp, fetcher=fetcher_with({}))

            self.assertEqual(stored, payload)
            self.assertIn("execution_attestation", payload)
            self.assertFalse(any(path.name.endswith(".tmp") for path in Path(tmp).iterdir()))
            self.assertEqual(findings, [])

    def test_pdf_source_with_valid_capture_receipt_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            proof = Path(tmp) / "gf-data-proof.md"
            proof.write_text("Specialty trades adjusted EBITDA margin was 18.1% to 20.4%.", encoding="utf-8")
            receipt, receipt_hash = write_capture_receipt(
                tmp,
                PDF_URL,
                proof.name,
                method="pdf_text",
            )
            content = f"""---
Source Map:
- Claim: Specialty trade contractors reported adjusted EBITDA margins from 18.1% to 20.4% | URL: {PDF_URL} | Evidence: "18.1% to 20.4%" | Artifact: {proof.name} | Capture receipt: {receipt} | Capture receipt hash: {receipt_hash} | Status: approved | Use: benchmark
---

# HVAC profitability

Specialty trade contractors reported adjusted EBITDA margins from 18.1% to 20.4%.
"""

            findings = check_content(content, base_path=tmp, fetcher=fetcher_with({}))

        self.assertEqual(findings, [])

    def test_capture_receipt_rejects_tampered_local_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            proof = Path(tmp) / "gf-data-proof.md"
            proof.write_text("Specialty trades adjusted EBITDA margin was 18.1% to 20.4%.", encoding="utf-8")
            receipt, receipt_hash = write_capture_receipt(
                tmp,
                PDF_URL,
                proof.name,
                method="pdf_text",
            )
            proof.write_text("Tampered 18.1% to 20.4% artifact.", encoding="utf-8")
            content = f"""---
Source Map:
- Claim: Specialty trade contractors reported adjusted EBITDA margins from 18.1% to 20.4% | URL: {PDF_URL} | Evidence: "18.1% to 20.4%" | Artifact: {proof.name} | Capture receipt: {receipt} | Capture receipt hash: {receipt_hash} | Status: approved | Use: benchmark
---

# HVAC profitability

Specialty trade contractors reported adjusted EBITDA margins from 18.1% to 20.4%.
"""

            findings = check_content(content, base_path=tmp, fetcher=fetcher_with({}))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "source_capture_artifact_hash_mismatch")

    def test_capture_receipt_rejects_future_retrieval_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            proof = Path(tmp) / "gf-data-proof.md"
            proof.write_text("Specialty trades adjusted EBITDA margin was 18.1% to 20.4%.", encoding="utf-8")
            receipt, _ = write_capture_receipt(
                tmp,
                PDF_URL,
                proof.name,
                method="pdf_text",
            )
            receipt_path = Path(tmp) / receipt
            payload = json.loads(receipt_path.read_text(encoding="utf-8"))
            payload["retrieved_at"] = "2999-08-11T12:00:00Z"
            receipt_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
            receipt_hash = _sha256(receipt_path)
            content = f"""---
Source Map:
- Claim: Specialty trade contractors reported adjusted EBITDA margins from 18.1% to 20.4% | URL: {PDF_URL} | Evidence: "18.1% to 20.4%" | Artifact: {proof.name} | Capture receipt: {receipt} | Capture receipt hash: {receipt_hash} | Status: approved | Use: benchmark
---

# HVAC profitability

Specialty trade contractors reported adjusted EBITDA margins from 18.1% to 20.4%.
"""

            findings = check_content(content, base_path=tmp, fetcher=fetcher_with({}))

        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["rule_id"],
            "source_capture_execution_attestation_invalid",
        )

    def test_blocked_html_source_with_locally_authored_artifact_but_no_receipt_fails(self):
        blocked_url = "https://www.capterra.com/p/166811/AroFlo/reviews/"
        with tempfile.TemporaryDirectory() as tmp:
            proof = Path(tmp) / "capterra-aroflo-proof.md"
            proof.write_text(
                "Capterra AroFlo review page, Gill M. review, checked 2026-06-29; paraphrased only.",
                encoding="utf-8",
            )
            content = f"""---
Source Map:
- Claim: A public Capterra AroFlo review from Gill M. supports a maintenance plumbing workflow story about scheduling, inventory, integrations, and time-and-material billing accuracy. | URL: {blocked_url} | Evidence: Capterra AroFlo review page, Gill M. review, checked 2026-06-29; paraphrased only. | Artifact: capterra-aroflo-proof.md | Status: approved | Use: E-E-A-T review story paragraph
---

# Plumbing pricing

A public [Capterra AroFlo review]({blocked_url}) from Gill M., a business owner, describes a maintenance plumbing workflow where scheduling, inventory, integrations, and time-and-material billing affect job accuracy.
"""

            def blocked_fetcher(url):
                raise RuntimeError("403 forbidden")

            findings = check_content(content, base_path=tmp, fetcher=blocked_fetcher)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "source_capture_receipt_missing")
        self.assertEqual(findings[0]["severity"], "error")

    def test_blocked_html_source_with_valid_capture_receipt_passes(self):
        blocked_url = "https://www.capterra.com/p/166811/AroFlo/reviews/"
        with tempfile.TemporaryDirectory() as tmp:
            proof = Path(tmp) / "capterra-aroflo-proof.md"
            evidence = (
                "Capterra AroFlo review page, Gill M. review, checked 2026-06-29; "
                "paraphrased only."
            )
            proof.write_text(evidence, encoding="utf-8")
            receipt, receipt_hash = write_capture_receipt(
                tmp,
                blocked_url,
                proof.name,
                method="html_visible_text",
            )
            content = f"""---
Source Map:
- Claim: A public Capterra AroFlo review from Gill M. supports a maintenance plumbing workflow story about scheduling, inventory, integrations, and time-and-material billing accuracy. | URL: {blocked_url} | Evidence: {evidence} | Artifact: {proof.name} | Capture receipt: {receipt} | Capture receipt hash: {receipt_hash} | Status: approved | Use: E-E-A-T review story paragraph
---

# Plumbing pricing

A public [Capterra AroFlo review]({blocked_url}) from Gill M., a business owner, describes a maintenance plumbing workflow where scheduling, inventory, integrations, and time-and-material billing affect job accuracy.
"""

            def blocked_fetcher(url):
                raise RuntimeError("403 forbidden")

            findings = check_content(content, base_path=tmp, fetcher=blocked_fetcher)

        self.assertEqual(findings, [])

    def test_unreachable_source_fails_closed(self):
        def failing_fetcher(url):
            raise RuntimeError("timeout")

        content = f"""---
Source Map:
- Claim: HVAC operators should target 15% to 20% EBITDA margins | URL: {EBITDA_URL} | Evidence: "15% to 20% EBITDA margins" | Status: approved | Use: FAQ benchmark
---

# HVAC profitability

Well-run HVAC operators should target [15% to 20% EBITDA margins]({EBITDA_URL}) when service, replacement, and maintenance work are balanced.
"""

        findings = check_content(content, fetcher=failing_fetcher)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "source_fetch_failed")

    def test_exact_case_study_quote_fails_without_approved_quote(self):
        content = f"""---
Customer Proof Pack:
- Case-study proof paths: Shaffer Beacon Mechanical, {SHAFFER_URL}, supported non-numeric theme: technician workflow perspective
---

# HVAC franchise software

[Shaffer Beacon Mechanical]({SHAFFER_URL}) said, "The system gives our technicians one place to work from."
"""

        findings = check_content(content, fetcher=fetcher_with({SHAFFER_URL: "The system gives our technicians one place to work from."}))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "quote_requires_approved_quote")

    def test_exact_case_study_quote_passes_with_approved_quote(self):
        content = f"""---
Customer Proof Pack:
- Approved quote: "The system gives our technicians one place to work from." | Customer/brand: Shaffer Beacon Mechanical | Source type: case study | URL: {SHAFFER_URL} | Evidence: "The system gives our technicians one place to work from." | Status: approved | Use: exact quote
---

# HVAC franchise software

[Shaffer Beacon Mechanical]({SHAFFER_URL}) said, "The system gives our technicians one place to work from."
"""

        findings = check_content(content, fetcher=fetcher_with({SHAFFER_URL: "The system gives our technicians one place to work from."}))

        self.assertEqual(findings, [])

    def test_exact_review_quote_fails_with_only_review_experience_evidence(self):
        content = f"""---
Customer Proof Pack:
- Review-site experience evidence: G2, {G2_URL}, date checked 2026-06-09, product: Simpro, experience pattern: scheduling pain, evidence summary: reviewers mention scheduling workflows, exact quote/rating approval status: not approved
---

# Field service software

A G2 reviewer said, "Scheduling is much easier for our field team now."
"""

        findings = check_content(content, fetcher=fetcher_with({G2_URL: "Scheduling is much easier for our field team now."}))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "quote_requires_approved_quote")

    def test_approved_quote_with_candidate_status_fails(self):
        content = f"""---
Customer Proof Pack:
- Approved quote: "The system gives our technicians one place to work from." | Customer/brand: Shaffer Beacon Mechanical | Source type: case study | URL: {SHAFFER_URL} | Evidence: "The system gives our technicians one place to work from." | Status: candidate | Use: exact quote
---

# HVAC franchise software

[Shaffer Beacon Mechanical]({SHAFFER_URL}) said, "The system gives our technicians one place to work from."
"""

        findings = check_content(content, fetcher=fetcher_with({SHAFFER_URL: "The system gives our technicians one place to work from."}))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "quote_requires_approved_quote")

    def test_approved_quote_with_missing_source_evidence_fails(self):
        content = f"""---
Customer Proof Pack:
- Approved quote: "The system gives our technicians one place to work from." | Customer/brand: Shaffer Beacon Mechanical | Source type: case study | URL: {SHAFFER_URL} | Evidence: "The system gives our technicians one place to work from." | Status: approved | Use: exact quote
---

# HVAC franchise software

[Shaffer Beacon Mechanical]({SHAFFER_URL}) said, "The system gives our technicians one place to work from."
"""

        findings = check_content(content, fetcher=fetcher_with({SHAFFER_URL: "Shaffer Beacon Mechanical uses Simpro for HVAC and plumbing workflows."}))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "source_evidence_not_found")

    def test_named_reviewer_ranking_language_fails_without_approved_strict_row(self):
        content = f"""---
Customer Proof Pack:
- Review-site experience evidence: G2, {G2_URL}, date checked 2026-06-09, product: Simpro, experience pattern: category comparison, evidence summary: reviewers discuss field service software options, exact quote/rating approval status: not approved
---

# Field service software

G2 reviewer Jane Smith described Simpro as a category leader for field service software.
"""

        findings = check_content(content, fetcher=fetcher_with({G2_URL: "Jane Smith described Simpro as a category leader for field service software."}))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "missing_strict_proof")

    def test_named_reviewer_ranking_language_passes_with_approved_strict_row(self):
        content = f"""---
Customer Proof Pack:
- Claim: G2 reviewer Jane Smith described Simpro as a category leader for field service software | URL: {G2_URL} | Evidence: "Jane Smith described Simpro as a category leader for field service software" | Status: approved | Use: named reviewer claim
---

# Field service software

G2 reviewer Jane Smith described Simpro as a category leader for field service software.
"""

        findings = check_content(content, fetcher=fetcher_with({G2_URL: "Jane Smith described Simpro as a category leader for field service software."}))

        self.assertEqual(findings, [])

    def test_check_file_failure_threshold_and_require_source_support(self):
        content = f"""---
Source Map:
- Claim: HVAC operators should target 15% to 20% EBITDA margins | URL: {EBITDA_URL} | Evidence: "15% to 20% EBITDA margins" | Status: approved | Use: FAQ benchmark
---

# HVAC profitability

Well-run HVAC operators should target [15% to 20% EBITDA margins]({EBITDA_URL}) when service, replacement, and maintenance work are balanced.
"""

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name

        try:
            findings = check_file(
                temp_path,
                fail_on="error",
                fetcher=fetcher_with({EBITDA_URL: "This page has no EBITDA benchmark."}),
            )
            self.assertTrue(should_fail(findings, fail_on="error"))
            self.assertFalse(should_fail(findings, fail_on="none"))
            with self.assertRaises(ValueError):
                require_source_support(
                    temp_path,
                    context="publish",
                    fetcher=fetcher_with({EBITDA_URL: "This page has no EBITDA benchmark."}),
                )
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    unittest.main()
