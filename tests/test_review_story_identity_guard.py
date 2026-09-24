import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from data_sources.modules.review_story_identity_guard import (
    check_content,
    check_file,
    should_fail,
)


G2_URL = "https://www.g2.com/products/simpro/reviews/simpro-review-4999668"
CAPTERRA_URL = "https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/"
BIGCHANGE_CAPTERRA_URL = (
    "https://www.capterra.co.uk/software/149479/jobwatch-powered-by-bigchange"
)


def write_index(root: Path) -> Path:
    index_path = root / "context" / "customer-proof-index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(
            {
                "version": 1,
                "proof": [
                    {
                        "proof_id": "review-capterra-megan-qbo-quotes",
                        "source_type": "review_site",
                        "public_url": CAPTERRA_URL,
                        "review_story": {
                            "story_allowed": True,
                            "identity_type": "person",
                            "identity_display": "Megan B",
                            "business_name": "",
                            "person_name": "Megan B",
                            "role_title": "Owner",
                            "platform": "Capterra",
                            "source_row_ref": "Capterra row 50",
                            "public_url": CAPTERRA_URL,
                            "workflow_story": "Owner describes service jobs, recurring jobs, quotes, invoices, and QBO integration.",
                            "objective_fit": ["quote-to-cash", "small trade business"],
                            "copy_use": "paraphrased E-E-A-T story with same-paragraph source link",
                            "verification_status": "brand-captured public review source",
                        },
                    },
                    {
                        "proof_id": "review-g2-small-electrical-quote-conversion-job-invoice",
                        "source_type": "review_site",
                        "public_url": G2_URL,
                        "review_story": {
                            "story_allowed": False,
                            "identity_type": "none",
                            "identity_display": "",
                            "business_name": "",
                            "person_name": "",
                            "role_title": "Administrator",
                            "platform": "G2",
                            "source_row_ref": "G2 row 211",
                            "public_url": G2_URL,
                            "workflow_story": "Role-only review describes quote conversion to job and invoice.",
                            "objective_fit": ["quote-to-job-to-invoice"],
                            "copy_use": "review theme only",
                            "verification_status": "anonymous role-only row",
                        },
                    },
                    {
                        "proof_id": "review-google-kingson-electrical-quote-to-invoice",
                        "source_type": "review_site",
                        "public_url": "",
                        "review_story": {
                            "story_allowed": False,
                            "identity_type": "business",
                            "identity_display": "Kingson Electrical",
                            "business_name": "Kingson Electrical",
                            "person_name": "",
                            "role_title": "",
                            "platform": "Google Review",
                            "source_row_ref": "Google Review Quotes row 2",
                            "public_url": "",
                            "workflow_story": "Business review describes quote-to-invoice visibility.",
                            "objective_fit": ["quote-to-invoice"],
                            "copy_use": "internal research only",
                            "verification_status": "missing public URL",
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return index_path


def write_bigchange_index(root: Path) -> Path:
    index_path = root / "context" / "customer-proof-index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(
            {
                "version": 1,
                "proof": [
                    {
                        "proof_id": "bigchange-review-capterra-owner-job-scheduling",
                        "source_type": "review_site",
                        "public_url": BIGCHANGE_CAPTERRA_URL,
                        "approved_quotes": [
                            {
                                "quote": "Job scheduling got so much faster with JobWatch.",
                                "status": "approved",
                            }
                        ],
                        "review_story": {
                            "story_allowed": True,
                            "identity_type": "person",
                            "identity_display": "Dana R",
                            "business_name": "",
                            "person_name": "Dana R",
                            "role_title": "Operations Manager",
                            "platform": "Capterra",
                            "source_row_ref": "Capterra row 12",
                            "public_url": BIGCHANGE_CAPTERRA_URL,
                            "workflow_story": "Dana R describes faster job scheduling after switching to JobWatch.",
                            "objective_fit": ["job scheduling"],
                            "copy_use": "paraphrased E-E-A-T story with same-paragraph source link",
                            "verification_status": "brand-captured public review source",
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return index_path


def write_two_reviewer_index(
    root: Path, *, suzanne_quote: str = "Job scheduling got so much faster with JobWatch."
) -> Path:
    """Two Capterra reviewers sharing one product-page URL: Clare (paraphrase-only,
    no approved_quotes) and Suzanne (a bound approved quote)."""
    index_path = root / "context" / "customer-proof-index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(
            {
                "version": 1,
                "proof": [
                    {
                        "proof_id": "review-capterra-clare-onboarding",
                        "source_type": "review_site",
                        "public_url": BIGCHANGE_CAPTERRA_URL,
                        "approved_quotes": [],
                        "review_story": {
                            "story_allowed": True,
                            "identity_type": "person",
                            "identity_display": "Clare",
                            "person_name": "Clare",
                            "platform": "Capterra",
                            "public_url": BIGCHANGE_CAPTERRA_URL,
                            "workflow_story": "Clare describes onboarding new team members quickly.",
                        },
                    },
                    {
                        "proof_id": "review-capterra-suzanne-job-scheduling",
                        "source_type": "review_site",
                        "public_url": BIGCHANGE_CAPTERRA_URL,
                        "approved_quotes": [
                            {"quote": suzanne_quote, "status": "approved"}
                        ],
                        "review_story": {
                            "story_allowed": True,
                            "identity_type": "person",
                            "identity_display": "Suzanne",
                            "person_name": "Suzanne",
                            "platform": "Capterra",
                            "public_url": BIGCHANGE_CAPTERRA_URL,
                            "workflow_story": "Suzanne describes faster job scheduling with JobWatch.",
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return index_path


TWO_REVIEWER_ARTICLE = (
    "# Article\n\n"
    f"[Clare's Capterra review]({BIGCHANGE_CAPTERRA_URL}) describes onboarding new team members quickly.\n\n"
    f"[Suzanne's Capterra review]({BIGCHANGE_CAPTERRA_URL}), "
    '"Job scheduling got so much faster with JobWatch."\n'
)


def two_reviewer_sidecar(
    current_proof_id: str,
    current_identity: str,
    other_proof_id: str,
    other_identity: str,
    *,
    url: str = BIGCHANGE_CAPTERRA_URL,
) -> str:
    return f"""Review Story Selection
- Selected story: {current_proof_id} | Identity: {current_identity} | Platform: Capterra | URL: {url} | Status: approved | Use: E-E-A-T experience story

Review Story Selection
- Selected story: {other_proof_id} | Identity: {other_identity} | Platform: Capterra | URL: {url} | Status: approved | Use: E-E-A-T experience story
"""


def sidecar(proof_id: str, identity: str, platform: str, url: str, status: str = "approved") -> str:
    return f"""Review Story Selection
- Article title: Best job quoting and invoicing software
- Content objective: help trade businesses choose quote-to-cash software
- Selector command: python data_sources/modules/customer_proof_selector.py "best job quoting and invoicing software" --title "Best job quoting and invoicing software" --objective "help trade businesses choose quote-to-cash software" --require-eeat-story
- Selected story: {proof_id} | Identity: {identity} | Platform: {platform} | URL: {url} | Workflow story: owner describes service jobs, recurring jobs, quotes, invoices, and QBO integration | Status: {status} | Use: E-E-A-T experience story
- Why selected: fit to quote-to-cash article objective
- Article link requirement: same paragraph as review-derived paraphrase must link to the selected public review URL
- Exact quote use: not approved unless listed under Approved quote
"""


def theme_sidecar(url: str = CAPTERRA_URL, status: str = "approved for paraphrased review-theme use") -> str:
    return f"""Review Site Theme Selection
- Article title: Best job quoting and invoicing software
- Content objective: help trade businesses choose quote-to-cash software
- Platform: Capterra
- Source row ref: Capterra tab row 50
- Public review-site URL: {url}
- Workflow theme: owner review describes service jobs, recurring jobs, quotes, invoices, and QBO integration
- Status: {status}
- Article link requirement: same paragraph must link to the Capterra review-site URL
- Limits: no exact quote, reviewer-name claim, rating, ranking, or metric unless separately approved
"""


class ReviewStoryIdentityGuardTests(unittest.TestCase):
    def test_not_applicable_review_story_record_passes_without_review_copy(self):
        content = (
            "# Article\n\n"
            "Mabry's Electrical Service offers one customer-story example of "
            "buddy-punching prevention."
        )
        proof_content = """Review Story Selection
- Decision: not applicable
- Reason: The selected passage comes from an official customer story, not a review platform.
- Public-copy boundary: No review-derived anecdote, rating, reviewer identity, or exact review quote is used.
- Status: not applicable
"""

        findings = check_content(content, proof_content=proof_content)

        self.assertEqual(findings, [])

    def test_not_applicable_review_story_record_cannot_mask_review_copy(self):
        content = "# Article\n\nA Capterra reviewer describes a faster quote workflow."
        proof_content = """Review Story Selection
- Decision: not applicable
- Reason: No review story selected.
- Status: not applicable
"""

        findings = check_content(content, proof_content=proof_content)

        self.assertIn(
            "review_story_selection_not_applicable_with_public_story",
            {finding["rule_id"] for finding in findings},
        )

    def test_review_paraphrase_without_same_paragraph_link_fails(self):
        with TemporaryDirectory() as temp_dir:
            index_path = write_index(Path(temp_dir))
            content = "# Article\n\nMegan B describes a service business using Simpro for service jobs, recurring jobs, quotes, invoices, and QBO integration."

            findings = check_content(
                content,
                proof_content=sidecar("review-capterra-megan-qbo-quotes", "Megan B", "Capterra", CAPTERRA_URL),
                proof_index_path=index_path,
            )

        self.assertTrue(any(finding["rule_id"] == "review_story_link_missing" for finding in findings))
        self.assertTrue(should_fail(findings))

    def test_review_paraphrase_with_public_source_link_passes(self):
        with TemporaryDirectory() as temp_dir:
            index_path = write_index(Path(temp_dir))
            content = f"# Article\n\n[Megan B's Capterra review]({CAPTERRA_URL}) describes a service business using Simpro for service jobs, recurring jobs, quotes, invoices, and QBO integration."

            findings = check_content(
                content,
                proof_content=sidecar("review-capterra-megan-qbo-quotes", "Megan B", "Capterra", CAPTERRA_URL),
                proof_index_path=index_path,
            )

        self.assertEqual(findings, [])

    def test_review_story_rejects_generic_or_bare_same_paragraph_urls(self):
        with TemporaryDirectory() as temp_dir:
            index_path = write_index(Path(temp_dir))
            generic = f"# Article\n\nMegan B describes a service business using Simpro for quotes and invoices in this [source]({CAPTERRA_URL})."
            bare = f"# Article\n\nMegan B describes a service business using Simpro for quotes and invoices. {CAPTERRA_URL}"

            for content in (generic, bare):
                findings = check_content(
                    content,
                    proof_content=sidecar(
                        "review-capterra-megan-qbo-quotes",
                        "Megan B",
                        "Capterra",
                        CAPTERRA_URL,
                    ),
                    proof_index_path=index_path,
                )
                self.assertIn(
                    "review_story_link_missing",
                    {finding["rule_id"] for finding in findings},
                )

    def test_review_story_uses_canonical_url_identity(self):
        with TemporaryDirectory() as temp_dir:
            index_path = write_index(Path(temp_dir))
            visible_url = CAPTERRA_URL.rstrip("/") + "?utm_source=article#reviews"
            content = f"# Article\n\n[Megan B's Capterra review]({visible_url}) describes a service business using Simpro for quotes and invoices."

            findings = check_content(
                content,
                proof_content=sidecar(
                    "review-capterra-megan-qbo-quotes",
                    "Megan B",
                    "Capterra",
                    CAPTERRA_URL,
                ),
                proof_index_path=index_path,
            )

        self.assertEqual(findings, [])

    def test_internal_only_google_review_story_fails_until_public_url_exists(self):
        with TemporaryDirectory() as temp_dir:
            index_path = write_index(Path(temp_dir))
            content = "# Article\n\nKingson Electrical describes quote-to-invoice visibility in a Google review."

            findings = check_content(
                content,
                proof_content=sidecar("review-google-kingson-electrical-quote-to-invoice", "Kingson Electrical", "Google Review", ""),
                proof_index_path=index_path,
            )

        self.assertTrue(any(finding["rule_id"] == "review_story_public_url_missing" for finding in findings))

    def test_role_only_review_story_fails_identity_requirement(self):
        with TemporaryDirectory() as temp_dir:
            index_path = write_index(Path(temp_dir))
            content = f"# Article\n\n[A G2 administrator review]({G2_URL}) describes quote conversion into jobs and invoices."

            findings = check_content(
                content,
                proof_content=sidecar("review-g2-small-electrical-quote-conversion-job-invoice", "", "G2", G2_URL),
                proof_index_path=index_path,
            )

        self.assertTrue(any(finding["rule_id"] == "review_story_identity_missing" for finding in findings))

    def test_exact_review_quote_fails_without_approved_quote(self):
        with TemporaryDirectory() as temp_dir:
            index_path = write_index(Path(temp_dir))
            content = f'# Article\n\n[Megan B said on Capterra]({CAPTERRA_URL}), "Quotes are easy and invoicing takes no time at all."'

            findings = check_content(
                content,
                proof_content=sidecar("review-capterra-megan-qbo-quotes", "Megan B", "Capterra", CAPTERRA_URL),
                proof_index_path=index_path,
            )

        self.assertTrue(any(finding["rule_id"] == "review_quote_requires_approved_quote" for finding in findings))

    def test_generic_review_theme_cannot_stand_in_for_review_story_selection(self):
        with TemporaryDirectory() as temp_dir:
            index_path = write_index(Path(temp_dir))
            content = f"# Article\n\n[G2 reviews]({G2_URL}) mention quote-to-invoice workflows for trade businesses."
            proof_content = f"""Customer Proof Pack
- Review-site experience evidence: G2, {G2_URL}, date checked 2026-06-12, product: Simpro, experience pattern: quote-to-invoice workflow, evidence summary: reviewers discuss quote-to-invoice workflows, exact quote/rating approval status: not approved.
"""

            findings = check_content(
                content,
                proof_content=proof_content,
                proof_index_path=index_path,
            )

        self.assertTrue(any(finding["rule_id"] == "review_story_selection_missing" for finding in findings))

    def test_capterra_theme_with_same_paragraph_review_site_link_passes(self):
        with TemporaryDirectory() as temp_dir:
            index_path = write_index(Path(temp_dir))
            content = f"# Article\n\n[Capterra reviews]({CAPTERRA_URL}) include owner perspectives on using Simpro for service jobs, recurring jobs, quotes, invoices, and QuickBooks Online integration."

            findings = check_content(
                content,
                proof_content=theme_sidecar(),
                proof_index_path=index_path,
            )

        self.assertEqual(findings, [])

    def test_capterra_theme_without_same_paragraph_review_site_link_fails(self):
        with TemporaryDirectory() as temp_dir:
            index_path = write_index(Path(temp_dir))
            content = "# Article\n\nCapterra reviews include owner perspectives on using Simpro for service jobs, recurring jobs, quotes, invoices, and QuickBooks Online integration."

            findings = check_content(
                content,
                proof_content=theme_sidecar(),
                proof_index_path=index_path,
            )

        self.assertTrue(any(finding["rule_id"] == "review_theme_link_missing" for finding in findings))

    def test_capterra_theme_with_rating_claim_fails_without_approved_proof(self):
        with TemporaryDirectory() as temp_dir:
            index_path = write_index(Path(temp_dir))
            content = f"# Article\n\n[Capterra reviews]({CAPTERRA_URL}) show high ratings for Simpro quote and invoice workflows."

            findings = check_content(
                content,
                proof_content=theme_sidecar(),
                proof_index_path=index_path,
            )

        self.assertTrue(any(finding["rule_id"] == "review_rating_claim_requires_approved_proof" for finding in findings))

    def test_bigchange_capterra_story_passes_with_name_and_link_in_same_paragraph(self):
        with TemporaryDirectory() as temp_dir:
            index_path = write_bigchange_index(Path(temp_dir))
            content = (
                "# Article\n\n[Dana R's Capterra review]"
                f"({BIGCHANGE_CAPTERRA_URL}) describes faster job scheduling with JobWatch."
            )

            findings = check_content(
                content,
                proof_content=sidecar(
                    "bigchange-review-capterra-owner-job-scheduling",
                    "Dana R",
                    "Capterra",
                    BIGCHANGE_CAPTERRA_URL,
                ),
                proof_index_path=index_path,
            )

        self.assertEqual(findings, [])

    def test_bigchange_capterra_story_with_rating_phrase_fails(self):
        with TemporaryDirectory() as temp_dir:
            index_path = write_bigchange_index(Path(temp_dir))
            content = (
                "# Article\n\n[Dana R's 5.0 star Capterra review]"
                f"({BIGCHANGE_CAPTERRA_URL}) describes faster job scheduling with JobWatch."
            )

            findings = check_content(
                content,
                proof_content=sidecar(
                    "bigchange-review-capterra-owner-job-scheduling",
                    "Dana R",
                    "Capterra",
                    BIGCHANGE_CAPTERRA_URL,
                ),
                proof_index_path=index_path,
            )

        self.assertTrue(
            any(
                finding["rule_id"] == "review_rating_claim_requires_approved_proof"
                for finding in findings
            )
        )

    def test_bigchange_capterra_exact_quote_not_in_approved_quotes_fails(self):
        with TemporaryDirectory() as temp_dir:
            index_path = write_bigchange_index(Path(temp_dir))
            content = (
                f'# Article\n\n[Dana R said on Capterra]({BIGCHANGE_CAPTERRA_URL}), '
                '"Scheduling was a total mess before we switched."'
            )

            findings = check_content(
                content,
                proof_content=sidecar(
                    "bigchange-review-capterra-owner-job-scheduling",
                    "Dana R",
                    "Capterra",
                    BIGCHANGE_CAPTERRA_URL,
                ),
                proof_index_path=index_path,
            )

        self.assertTrue(
            any(
                finding["rule_id"] == "review_quote_requires_approved_quote"
                for finding in findings
            )
        )

    def test_bigchange_capterra_exact_quote_bound_to_approved_quotes_passes(self):
        with TemporaryDirectory() as temp_dir:
            index_path = write_bigchange_index(Path(temp_dir))
            content = (
                f'# Article\n\n[Dana R said on Capterra]({BIGCHANGE_CAPTERRA_URL}), '
                '"Job scheduling got so much faster with JobWatch."'
            )

            findings = check_content(
                content,
                proof_content=sidecar(
                    "bigchange-review-capterra-owner-job-scheduling",
                    "Dana R",
                    "Capterra",
                    BIGCHANGE_CAPTERRA_URL,
                ),
                proof_index_path=index_path,
            )

        self.assertEqual(findings, [])

    def test_bigchange_capterra_second_unbound_quote_in_same_paragraph_fails(self):
        with TemporaryDirectory() as temp_dir:
            index_path = write_bigchange_index(Path(temp_dir))
            content = (
                f'# Article\n\n[Dana R said on Capterra]({BIGCHANGE_CAPTERRA_URL}), '
                '"Job scheduling got so much faster with JobWatch." '
                'She added, "Scheduling was a total mess before we switched to it."'
            )

            findings = check_content(
                content,
                proof_content=sidecar(
                    "bigchange-review-capterra-owner-job-scheduling",
                    "Dana R",
                    "Capterra",
                    BIGCHANGE_CAPTERRA_URL,
                ),
                proof_index_path=index_path,
            )

        self.assertTrue(
            any(
                finding["rule_id"] == "review_quote_requires_approved_quote"
                for finding in findings
            )
        )

    def test_two_reviewers_sharing_url_clare_row_has_no_finding_for_suzanne_bound_quote(self):
        with TemporaryDirectory() as temp_dir:
            index_path = write_two_reviewer_index(Path(temp_dir))

            findings = check_content(
                TWO_REVIEWER_ARTICLE,
                proof_content=two_reviewer_sidecar(
                    "review-capterra-clare-onboarding",
                    "Clare",
                    "review-capterra-suzanne-job-scheduling",
                    "Suzanne",
                ),
                proof_index_path=index_path,
            )

        self.assertEqual(findings, [])

    def test_two_reviewers_sharing_url_suzanne_row_has_no_finding_for_own_bound_quote(self):
        with TemporaryDirectory() as temp_dir:
            index_path = write_two_reviewer_index(Path(temp_dir))

            findings = check_content(
                TWO_REVIEWER_ARTICLE,
                proof_content=two_reviewer_sidecar(
                    "review-capterra-suzanne-job-scheduling",
                    "Suzanne",
                    "review-capterra-clare-onboarding",
                    "Clare",
                ),
                proof_index_path=index_path,
            )

        self.assertEqual(findings, [])

    def test_two_reviewers_sharing_url_suzannes_own_unbound_quote_still_fails(self):
        with TemporaryDirectory() as temp_dir:
            index_path = write_two_reviewer_index(
                Path(temp_dir), suzanne_quote="A completely different approved snippet."
            )

            findings = check_content(
                TWO_REVIEWER_ARTICLE,
                proof_content=two_reviewer_sidecar(
                    "review-capterra-suzanne-job-scheduling",
                    "Suzanne",
                    "review-capterra-clare-onboarding",
                    "Clare",
                ),
                proof_index_path=index_path,
            )

        self.assertTrue(
            any(
                finding["rule_id"] == "review_quote_requires_approved_quote"
                for finding in findings
            )
        )

    def test_quote_paragraph_naming_no_selected_identity_still_fails_closed(self):
        with TemporaryDirectory() as temp_dir:
            index_path = write_two_reviewer_index(Path(temp_dir))
            article = (
                TWO_REVIEWER_ARTICLE
                + '\nA reviewer on Capterra also said, "Support response times were '
                'disappointing at first."\n'
            )

            findings = check_content(
                article,
                proof_content=two_reviewer_sidecar(
                    "review-capterra-clare-onboarding",
                    "Clare",
                    "review-capterra-suzanne-job-scheduling",
                    "Suzanne",
                ),
                proof_index_path=index_path,
            )

        self.assertTrue(
            any(
                finding["rule_id"] == "review_quote_requires_approved_quote"
                for finding in findings
            )
        )

    def test_check_file_accepts_sidecar_and_index_paths(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = write_index(root)
            article = root / "drafts" / "article.md"
            validation = root / "research" / "validation-article.md"
            article.parent.mkdir(parents=True)
            validation.parent.mkdir(parents=True)
            article.write_text(
                f"# Article\n\n[Megan B's Capterra review]({CAPTERRA_URL}) describes a service business using Simpro for service jobs, recurring jobs, quotes, invoices, and QBO integration.",
                encoding="utf-8",
            )
            validation.write_text(
                sidecar("review-capterra-megan-qbo-quotes", "Megan B", "Capterra", CAPTERRA_URL),
                encoding="utf-8",
            )

            findings = check_file(article, proof_sidecar=str(validation), proof_index_path=index_path)

        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
