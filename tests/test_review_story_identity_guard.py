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
