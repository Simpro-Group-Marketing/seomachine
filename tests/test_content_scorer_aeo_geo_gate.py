from tests.fixture_text import fixture_text

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from data_sources.modules import content_scorer as content_scorer_module
from data_sources.modules import seo_quality_rater as seo_quality_rater_module
from data_sources.modules.content_scorer import ContentScorer
from data_sources.modules.seo_quality_rater import PUBLISHING_THRESHOLD
from data_sources.modules.paa_provenance_guard import build_answersocrates_artifact
from data_sources.modules.url_validator import UrlValidationResult, UrlValidationSummary
from tests.research_provenance_fixtures import build_answersocrates_fixture
from tests.test_aeo_geo_rater import (
    AUTHOR_VERIFICATION_BLOCK,
    write_bound_experience_story_evidence,
)
from tests.vault_context_fixture import load_validated_claim_set_for_unit_test


PAA_ARTIFACT = "research/paa-questions-hvac-scheduling-2026-05-22.md"
METRIC_ARTIFACT = "research/metric-proof-hvac-scheduling-2026-05-22.md"
PAA_PROVENANCE_BLOCK = f"""
```text
PAA/FAQ Provenance
- Source: answersocrates
- Artifact: {PAA_ARTIFACT}
- Selected questions:
  - What is the best way to schedule HVAC technicians?
  - How does HVAC scheduling software reduce missed appointments?
  - Should HVAC scheduling connect to invoicing?
```
"""
FAQ_PROOF_BLOCK = fixture_text("content_evidence:test_content_scorer_aeo_geo_gate-29-1")
METRIC_PROOF_BLOCK = f"""
```text
Metric Proof Pack
- Metric requirement: required
- Search log: Checked Simpro company proof for platform scale.
- Approved metric: Simpro supports more than 24,000 trade businesses | URL: {METRIC_ARTIFACT} | Evidence: "more than 24,000 trade businesses" | Status: approved | Use: platform scale proof
```
"""
CUSTOMER_PROOF_BLOCK = fixture_text("content_evidence:test_content_scorer_aeo_geo_gate-50-2")

COMPLIANT_ARTICLE = fixture_text("content_evidence:test_content_scorer_aeo_geo_gate-84-10") + METRIC_PROOF_BLOCK + PAA_PROVENANCE_BLOCK + FAQ_PROOF_BLOCK + CUSTOMER_PROOF_BLOCK + fixture_text("content_evidence:test_content_scorer_aeo_geo_gate-131-3")


def write_paa_fixture(test_case: unittest.TestCase, content: str) -> str:
    temp_dir = TemporaryDirectory()
    test_case.addCleanup(temp_dir.cleanup)
    root = Path(temp_dir.name)
    artifact = root / PAA_ARTIFACT
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        "\n".join(
            [
                "# AnswerSocrates PAA Questions",
                "",
                "What is the best way to schedule HVAC technicians?",
                "How does HVAC scheduling software reduce missed appointments?",
                "Should HVAC scheduling connect to invoicing?",
            ]
        ),
        encoding="utf-8",
    )
    metric_artifact = root / METRIC_ARTIFACT
    metric_artifact.parent.mkdir(parents=True, exist_ok=True)
    metric_artifact.write_text(
        "Simpro supports more than 24,000 trade businesses worldwide.",
        encoding="utf-8",
    )
    article_path = root / "drafts" / "hvac-scheduling-software.md"
    article_path.parent.mkdir(parents=True, exist_ok=True)
    article_path.write_text(content, encoding="utf-8")
    artifact.write_text(
        json.dumps(
            build_answersocrates_fixture(
                root,
                query="hvac scheduling software",
                collection_date="2026-05-22",
                questions=(
                    "What is the best way to schedule HVAC technicians?",
                    "How does HVAC scheduling software reduce missed appointments?",
                    "Should HVAC scheduling connect to invoicing?",
                ),
                run_id="content-scorer-fixture",
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding='utf-8',
    )
    return str(article_path)


def write_sidecar_fixture(test_case: unittest.TestCase, content: str) -> tuple[str, str]:
    article_path = Path(write_paa_fixture(test_case, content))
    sidecar_path = (
        article_path.parent.parent
        / "research"
        / f"validation-{article_path.stem}.md"
    )
    sidecar_path.write_text(
        METRIC_PROOF_BLOCK + PAA_PROVENANCE_BLOCK + FAQ_PROOF_BLOCK + CUSTOMER_PROOF_BLOCK + AUTHOR_VERIFICATION_BLOCK,
        encoding="utf-8",
    )
    return str(article_path), str(sidecar_path)


class ContentScorerAeoGeoGateTests(unittest.TestCase):
    def test_clean_for_analysis_excludes_non_visible_html_and_keeps_table_text(self):
        content = (
            "# Platform guide\n\n"
            "<table><tr><td>Visible buyer fit</td></tr></table>\n"
            '<script type="application/ld+json">'
            '{"description": "Hidden schema duplicate."}'
            "</script>\n"
        )

        cleaned = ContentScorer()._clean_for_analysis(content)

        self.assertIn("Visible buyer fit", cleaned)
        self.assertNotIn("Hidden schema duplicate", cleaned)
        self.assertNotIn("<td>", cleaned)

    def test_structure_balance_counts_rendered_html_table_as_structure(self):
        content = (
            "# Platform guide\n\n"
            "Use this guide to compare the products against your daily workflow.\n\n"
            "<table>\n"
            "<tr><th>Platform</th><th>Buyer fit</th></tr>\n"
            "<tr><td>Alpha</td><td>Service teams</td></tr>\n"
            "<tr><td>Beta</td><td>Project teams</td></tr>\n"
            "</table>\n"
            '<script type="application/ld+json">\n'
            '{"description": "Schema text must not count as prose."}\n'
            "</script>\n"
        )

        result = ContentScorer()._score_structure_balance(content)

        self.assertGreater(result["details"]["table_chars"], 0)
        self.assertLess(result["prose_ratio"], 0.75)

    def test_seo_gate_uses_the_canonical_seo_quality_threshold(self):
        self.assertEqual(content_scorer_module.SEO_PUBLISHING_THRESHOLD, PUBLISHING_THRESHOLD)
        self.assertFalse(hasattr(ContentScorer, "SEO_PASS_THRESHOLD"))

    def test_seo_gate_uses_the_canonical_advisory_target(self):
        self.assertEqual(content_scorer_module.SEO_TARGET_SCORE, 95)
        self.assertEqual(
            content_scorer_module.SEO_TARGET_SCORE,
            seo_quality_rater_module.SEO_TARGET_SCORE,
        )

    def test_seo_score_honors_exact_internal_link_override_from_sidecar(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sidecar = root / "validation.md"
            sidecar.write_text(
                "\n".join(
                    [
                        "## Link inventory and internal link decision",
                        "- Override scope: `pre_faq_body`.",
                        "- Override interpretation: exact_count `2` governs the two brief-selected supporting links and suppresses independently derived industry and down-funnel requirements not included in the bound brief.",
                    ]
                ),
                encoding="utf-8",
            )
            body = (
                "# Texas Plumbing License Guide\n\n"
                "Texas plumbing license decisions start with the state credential path.\n\n"
                "## Practical records\n\n"
                + (
                    "Use a simple folder for applications, renewals, exams, and records. "
                    "Keep each document name clear and easy to scan. "
                )
                * 40
                + "\n\n"
                "[plumbing training and licensing resources](https://www.simprogroup.com/blog/informational-resources-for-plumbing-contractors)\n"
                "[grow a plumbing business](https://www.simprogroup.com/blog/how-to-grow-plumbing-business)\n"
            )

            result = ContentScorer()._score_seo(
                body,
                {
                    "meta_title": "Texas Plumbing License Requirements Guide | Simpro",
                    "meta_description": (
                        "Texas plumbing license steps, records, renewals, and practical planning "
                        "help plumbers choose the right credential path with less rework."
                    ),
                    "primary_keyword": "Texas plumbing license",
                },
                proof_sidecar=str(sidecar),
            )

        issue_text = "\n".join(issue["issue"] for issue in result["issues"])
        self.assertGreaterEqual(result["score"], 90)
        self.assertNotIn("Too few internal links", issue_text)
        self.assertNotIn("down-funnel internal link", issue_text)

    def test_seo_score_honors_frontmatter_aeo_title_topic(self):
        content = """---
brand: Simpro
primary_keyword: ai field service management
primary_aeo_topic: ai field service economics
---

# AI Field Service Economics: What to Measure Before You Automate

AI field service management starts with a measurable constraint and a bounded pilot.

## Build the scorecard

Use operating data to compare the same workflow before and after the pilot.
"""

        result = ContentScorer()._score_seo(
            content,
            {
                "meta_title": "AI Field Service Economics: Practical Scorecard | Simpro",
                "meta_description": (
                    "Use an AI field service economics scorecard to test capacity, "
                    "cost, quality, and controls before expanding a field service pilot."
                ),
            },
        )

        self.assertEqual(result["details"]["h1_keyword"], "ai field service economics")
        self.assertNotIn(
            "missing from H1",
            "\n".join(result["critical_issues"]),
        )

    def test_legacy_70_score_no_longer_meets_quality_threshold(self):
        scorer = ContentScorer()

        self.assertEqual(scorer.PASS_THRESHOLD, 85)

    def test_humanity_lint_uses_raw_markdown_context(self):
        scorer = ContentScorer()
        content = fixture_text("content_evidence:test_content_scorer_aeo_geo_gate-222-4")

        result = scorer.score(content, {"primary_keyword": "hvac ppc"})

        self.assertEqual(
            result["dimensions"]["humanity"]["details"]["ai_copy_lint_errors"],
            0,
        )

    def test_humanity_score_receives_chatbot_blocker_from_shared_linter(self):
        """Bypassing the shared blocker in humanity scoring must make this fail."""
        result = ContentScorer()._score_humanity(
            "I hope this helps. Feel free to ask for another version."
        )

        details = result["details"]
        self.assertEqual(details["ai_copy_lint_errors"], 2)
        self.assertIn(
            "humanizer.chatbot_residue",
            {
                finding["rule_id"]
                for finding in details["ai_copy_lint_findings"]
            },
        )

    def test_contextual_humanizer_guidance_does_not_enter_humanity_score(self):
        """Penalizing advisory Humanizer guidance in scoring must make this fail."""
        result = ContentScorer()._score_humanity(
            "This serves as the operating record. Let's dive in. Frankly, the handoff is late."
        )

        findings = result["details"]["ai_copy_lint_findings"]
        self.assertFalse(
            [
                finding
                for finding in findings
                if str(finding["rule_id"]).startswith("humanizer.")
            ]
        )

    def test_seo_score_reads_lowercase_frontmatter_metadata(self):
        scorer = ContentScorer()
        content = COMPLIANT_ARTICLE.replace(
            "Meta Title: HVAC Scheduling Software for Contractors | Simpro",
            "meta_title: HVAC Scheduling Software for Contractors | Simpro",
        ).replace(
            "Meta Description: HVAC scheduling software helps contractors assign jobs, avoid double-booking, and keep technicians moving from one real-time calendar.",
            "meta_description: HVAC scheduling software helps contractors assign jobs, avoid double-booking, and keep technicians moving from one real-time calendar.",
        ).replace(
            "Primary Keyword: hvac scheduling software",
            "primary_keyword: hvac scheduling software",
        )

        result = scorer._score_seo(content, {})

        self.assertEqual(result["details"]["meta_title"], "HVAC Scheduling Software for Contractors | Simpro")
        self.assertEqual(result["details"]["primary_keyword"], "hvac scheduling software")
        self.assertNotIn("Missing meta title", [issue["issue"] for issue in result["issues"]])
        self.assertNotIn("Missing meta description", [issue["issue"] for issue in result["issues"]])

    def test_score_seo_records_word_count_without_short_content_issue(self):
        scorer = ContentScorer()
        content = fixture_text("content_evidence:test_content_scorer_aeo_geo_gate-262-5")

        result = scorer._score_seo(content, {})
        issues = [issue["issue"] for issue in result["issues"]]

        self.assertLess(result["details"]["word_count"], 2000)
        self.assertFalse(any(issue.startswith("Content too short") for issue in issues))

    def test_content_dimensions_ignore_arbitrary_yaml_frontmatter(self):
        scorer = ContentScorer()
        body = fixture_text("content_evidence:test_content_scorer_aeo_geo_gate-289-6")
        frontmatter = fixture_text("content_evidence:test_content_scorer_aeo_geo_gate-301-7")
        metadata = {
            "meta_title": "HVAC Scheduling Software for Contractors | Simpro",
            "meta_description": (
                "HVAC scheduling software helps contractors assign jobs, coordinate "
                "technicians, and keep customers informed from one dispatch workflow."
            ),
            "primary_keyword": "hvac scheduling software",
        }

        baseline = scorer.score(body, metadata)
        with_frontmatter = scorer.score(frontmatter + body, metadata)

        for dimension in (
            "humanity",
            "specificity",
            "structure_balance",
            "seo",
            "readability",
        ):
            with self.subTest(dimension=dimension):
                self.assertEqual(
                    with_frontmatter["dimensions"][dimension]["score"],
                    baseline["dimensions"][dimension]["score"],
                )
        self.assertEqual(with_frontmatter["composite_score"], baseline["composite_score"])

    def test_score_seo_delegates_once_to_strengthened_seo_rater(self):
        scorer = ContentScorer()
        content = fixture_text("content_evidence:test_content_scorer_aeo_geo_gate-338-8")
        rated = {
            "overall_score": 86.4,
            "grade": "B (Good)",
            "category_scores": {"links": 80},
            "critical_issues": ["Missing down-funnel internal link"],
            "warnings": ["Keyword use is slightly high"],
            "suggestions": ["Tighten the meta title"],
            "publishing_ready": False,
            "details": {"word_count": 42},
        }

        with patch.object(scorer.seo_rater, "rate", return_value=rated) as rate:
            result = scorer._score_seo(content, {})

        rate.assert_called_once_with(
            content,
            meta_title="HVAC Scheduling Software for Contractors | Simpro",
            meta_description=(
                "HVAC scheduling software helps contractors assign jobs, avoid "
                "double-booking, and keep technicians moving from one real-time calendar."
            ),
            primary_keyword="hvac scheduling software",
            secondary_keywords=None,
        )
        self.assertEqual(result["score"], 86)
        self.assertEqual(
            [item["issue"] for item in result["issues"]],
            [
                "Missing down-funnel internal link",
                "Keyword use is slightly high",
                "Tighten the meta title",
            ],
        )
        self.assertEqual(result["details"]["category_scores"], {"links": 80})

    def test_specificity_scores_concrete_workflow_detail_without_forcing_numbers(self):
        scorer = ContentScorer()
        content = (
            "Dispatchers sort urgent callouts, technician skills, parts availability, "
            "travel windows, customer access notes, and invoice readiness before they "
            "move a job on the schedule. The workflow explains who decides, what "
            "changes, and which handoff prevents office teams from rekeying the same "
            "job details after field work is complete."
        )

        result = scorer._score_specificity(content)
        issues = [issue["issue"] for issue in result["issues"]]

        self.assertGreaterEqual(result["score"], 70)
        self.assertNotIn("Lacks specific numbers and data", issues)
        self.assertGreater(result["details"]["concrete_workflow_terms_per_1000"], 0)

    def test_specificity_reports_proof_sensitive_details_without_scoring_them_as_proof(self):
        scorer = ContentScorer()
        content = (
            'In 2026, Sarah said "This saved 73% of our time and $500 a month" '
            "in a claim about 200 businesses dated March 12. The passage contains "
            "numbers, a named attribution, a date, and an outcome without source "
            "proof in this scoring context."
        )

        result = scorer._score_specificity(content)
        issues = [issue["issue"] for issue in result["issues"]]

        self.assertEqual(result["score"], 70)
        self.assertNotIn("Unsupported specifics require proof context", issues)
        self.assertGreater(result["details"]["proof_sensitive_specifics_per_1000"], 0)

    def test_specificity_records_plain_percentage_without_changing_score(self):
        result = ContentScorer()._score_specificity(
            "The measured change was 25%."
        )

        self.assertEqual(result["score"], 70)
        self.assertEqual(result["details"]["proof_sensitive_specifics_count"], 1)

    def test_proof_sensitive_claim_does_not_gain_workflow_specificity_points(self):
        scorer = ContentScorer()
        baseline = scorer._score_specificity("The measured change was material.")
        claimed = scorer._score_specificity(
            "Sarah at Acme Mechanical saved 25% of customer time in 2026."
        )

        self.assertEqual(claimed["score"], baseline["score"])
        self.assertGreater(
            claimed["details"]["proof_sensitive_specifics_count"],
            baseline["details"]["proof_sensitive_specifics_count"],
        )

    def test_specificity_does_not_assume_named_details_are_unsupported_before_proof_gates(self):
        scorer = ContentScorer()
        content = (
            "Sarah at Acme Mechanical moved dispatch handoffs into the job workflow "
            "and helped 24,000 trade businesses avoid delayed invoices. The scene "
            "names a person, a company, a business count, and an outcome without "
            "approved proof in this scoring context."
        )

        result = scorer._score_specificity(content)
        issues = [issue["issue"] for issue in result["issues"]]

        self.assertNotIn("Unsupported specifics require proof context", issues)
        self.assertGreaterEqual(result["details"]["proof_sensitive_specifics_count"], 3)

    def test_specificity_does_not_penalize_proof_sensitive_details_with_public_context(self):
        scorer = ContentScorer()
        content = (
            'Sarah at Acme Mechanical said "The approved workflow reduced invoice '
            'delays by 25% in 2026." The public case study documents the customer, '
            "quote, metric, date, and outcome."
        )

        result = scorer._score_specificity(content)
        issues = [issue["issue"] for issue in result["issues"]]

        self.assertNotIn("Unsupported specifics require proof context", issues)
        self.assertGreater(result["details"]["proof_sensitive_specifics_count"], 0)

    def test_content_quality_can_pass_while_aeo_geo_gate_fails(self):
        scorer = ContentScorer()
        content = COMPLIANT_ARTICLE.replace(
            "HVAC scheduling software helps contractors assign technicians, avoid double-booking, and keep customers updated from one real-time calendar.",
            "Running a service business has always been complicated, and teams face more pressure every year.",
        )

        with patch.object(
            ContentScorer,
            "_score_humanity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_specificity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_structure_balance",
            return_value={"score": 100, "issues": [], "details": {}, "prose_ratio": 0.65},
        ), patch.object(
            ContentScorer,
            "_score_seo",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_readability",
            return_value={"score": 100, "issues": [], "details": {}, "flesch": 68},
        ):
            result = scorer.score(
                content,
                {"primary_keyword": "hvac scheduling software"},
                source_path=write_paa_fixture(self, content),
                paa_expected_run_id="content-scorer-fixture",
            )

        self.assertFalse(result["passed"])
        self.assertGreaterEqual(result["content_quality_score"], 85)
        self.assertLess(result["aeo_geo"]["score"], 90)
        self.assertIn("aeo_geo", result["quality_gates"])
        self.assertFalse(result["quality_gates"]["aeo_geo"]["passed"])

    def test_fully_compliant_content_passes_quality_and_aeo_geo_gates(self):
        scorer = ContentScorer()
        content = COMPLIANT_ARTICLE.replace(CUSTOMER_PROOF_BLOCK, "").replace(
            "\n[BWE Engineering](https://www.simprogroup.com/case-studies/bwe-engineering) shows how field service teams use connected workflows to improve operational control.\n",
            "\n[Megan B's Capterra review](https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/) describes using service jobs, quotes, invoices, and QBO integration in one connected workflow.\n",
        )
        customer_governance = fixture_text("content_evidence:test_content_scorer_aeo_geo_gate-513-9")

        with TemporaryDirectory() as temp_dir:
            proof_sidecar, proof_sidecar_path = (
                write_bound_experience_story_evidence(
                    self,
                    Path(temp_dir),
                )
            )
            proof_sidecar += FAQ_PROOF_BLOCK + METRIC_PROOF_BLOCK + customer_governance
            proof_sidecar_path.write_text(proof_sidecar, encoding="utf-8")
            with patch.object(
                ContentScorer,
                "_score_humanity",
                return_value={"score": 100, "issues": [], "details": {}},
            ), patch.object(
                ContentScorer,
                "_score_specificity",
                return_value={"score": 100, "issues": [], "details": {}},
            ), patch.object(
                ContentScorer,
                "_score_structure_balance",
                return_value={"score": 100, "issues": [], "details": {}, "prose_ratio": 0.65},
            ), patch.object(
                ContentScorer,
                "_score_seo",
                return_value={"score": 100, "issues": [], "details": {}},
            ), patch.object(
                ContentScorer,
                "_score_readability",
                return_value={"score": 100, "issues": [], "details": {}, "flesch": 68},
            ), patch(
                "data_sources.modules.customer_proof_selector.load_validated_claim_set",
                new=load_validated_claim_set_for_unit_test,
            ):
                result = scorer.score(
                    content,
                    {"primary_keyword": "hvac scheduling software"},
                    source_path=write_paa_fixture(self, content),
                    paa_expected_run_id="content-scorer-fixture",
                    proof_sidecar=str(proof_sidecar_path),
                )

        self.assertTrue(result["passed"])
        self.assertGreaterEqual(result["content_quality_score"], 85)
        self.assertGreaterEqual(result["aeo_geo"]["score"], 90)
        self.assertTrue(result["quality_gates"]["content_quality"]["passed"])
        self.assertTrue(result["quality_gates"]["aeo_geo"]["passed"])
        self.assertTrue(result["quality_gates"]["metric_proof_pack"]["passed"])

    def test_strong_composite_cannot_bypass_canonical_seo_blockers(self):
        scorer = ContentScorer()

        with patch.object(
            ContentScorer,
            "_score_humanity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_specificity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_structure_balance",
            return_value={"score": 100, "issues": [], "details": {}, "prose_ratio": 0.65},
        ), patch.object(
            ContentScorer,
            "_score_seo",
            return_value={
                "score": 100,
                "passed": False,
                "issues": [{
                    "issue": "Missing down-funnel internal link",
                    "fix": "Add an intent-matched down-funnel link.",
                    "severity": "high",
                }],
                "details": {},
            },
        ), patch.object(
            ContentScorer,
            "_score_readability",
            return_value={"score": 100, "issues": [], "details": {}, "flesch": 68},
        ):
            result = scorer.score(
                COMPLIANT_ARTICLE,
                {"primary_keyword": "hvac scheduling software"},
                source_path=write_paa_fixture(self, COMPLIANT_ARTICLE),
                paa_expected_run_id="content-scorer-fixture",
            )

        self.assertGreaterEqual(result["content_quality_score"], 85)
        self.assertFalse(result["passed"])
        self.assertFalse(result["quality_gates"]["seo_quality"]["passed"])

    def test_sidecar_customer_proof_without_hash_bound_evidence_blocks_scoring(self):
        scorer = ContentScorer()
        content = COMPLIANT_ARTICLE.replace(METRIC_PROOF_BLOCK, "").replace(
            PAA_PROVENANCE_BLOCK,
            "",
        ).replace(
            FAQ_PROOF_BLOCK,
            "",
        )
        article_path, sidecar_path = write_sidecar_fixture(self, content)

        with patch.object(
            ContentScorer,
            "_score_humanity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_specificity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_structure_balance",
            return_value={"score": 100, "issues": [], "details": {}, "prose_ratio": 0.65},
        ), patch.object(
            ContentScorer,
            "_score_seo",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_readability",
            return_value={"score": 100, "issues": [], "details": {}, "flesch": 68},
        ):
            result = scorer.score(
                content,
                {"primary_keyword": "hvac scheduling software"},
                source_path=article_path,
                paa_expected_run_id="content-scorer-fixture",
                proof_sidecar=sidecar_path,
            )

        self.assertFalse(result["passed"])
        self.assertTrue(result["quality_gates"]["paa_provenance"]["passed"])
        self.assertTrue(result["quality_gates"]["metric_proof_pack"]["passed"])
        customer_gate = result["quality_gates"]["customer_proof_diversity"]
        self.assertFalse(customer_gate["passed"])
        self.assertEqual(
            customer_gate["findings"][0]["rule_id"],
            "customer_proof_selector_evidence_unverified",
        )

    def test_review_story_identity_failure_blocks_content_scorer(self):
        scorer = ContentScorer()
        content = COMPLIANT_ARTICLE.replace(
            "\n[BWE Engineering](https://www.simprogroup.com/case-studies/bwe-engineering) shows how field service teams use connected workflows to improve operational control.\n",
            "\n[G2 reviews](https://www.g2.com/products/simpro/reviews) mention quote-to-invoice workflows for trade businesses.\n",
        )
        content = content.replace(METRIC_PROOF_BLOCK, "").replace(PAA_PROVENANCE_BLOCK, "")
        article_path, sidecar_path = write_sidecar_fixture(self, content)

        with patch.object(
            ContentScorer,
            "_score_humanity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_specificity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_structure_balance",
            return_value={"score": 100, "issues": [], "details": {}, "prose_ratio": 0.65},
        ), patch.object(
            ContentScorer,
            "_score_seo",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_readability",
            return_value={"score": 100, "issues": [], "details": {}, "flesch": 68},
        ):
            result = scorer.score(
                content,
                {"primary_keyword": "hvac scheduling software"},
                source_path=article_path,
                paa_expected_run_id="content-scorer-fixture",
                proof_sidecar=sidecar_path,
            )

        self.assertFalse(result["passed"])
        self.assertIn("review_story_identity", result["quality_gates"])
        self.assertFalse(result["quality_gates"]["review_story_identity"]["passed"])
        self.assertIn("Review story identity blockers detected", result["priority_fixes"][0]["issue"])

    def test_quality_gate_passes_resolved_proof_sidecar_path_to_aeo_rater(self):
        scorer = ContentScorer()
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            article = root / "drafts" / "article.md"
            sidecar = root / "research" / "validation-article.md"
            article.parent.mkdir(parents=True)
            sidecar.parent.mkdir(parents=True)
            article.write_text("# Article\n", encoding="utf-8")
            sidecar.write_text("# Validation\n", encoding="utf-8")
            with patch(
                "data_sources.modules.content_scorer.rate_aeo_geo",
                return_value={"passed": True, "checks": {}},
            ) as rate, patch(
                "data_sources.modules.content_scorer.check_metric_proof_pack",
                return_value=[],
            ), patch(
                "data_sources.modules.content_scorer.check_customer_proof_diversity",
                return_value=[],
            ), patch(
                "data_sources.modules.content_scorer.check_review_story_identity",
                return_value=[],
            ):
                scorer._run_quality_gates(
                    "# Article\n",
                    {},
                    validate_urls=False,
                    validate_source_support=False,
                    source_path=str(article),
                    proof_sidecar=str(sidecar),
                )

        self.assertEqual(
            rate.call_args.kwargs["proof_sidecar_path"],
            str(sidecar.resolve()),
        )

    def test_quality_gate_forwards_bound_bom_and_strict_paa_inputs_to_aeo_rater(self):
        scorer = ContentScorer()
        finalized_bom = {
            "schema": "simpro-blog-assembly-bom/v1",
            "lifecycle_state": "final",
            "author_policy": {
                "status": "not_provided",
                "name": "",
                "frontmatter_author_required": False,
                "schema_person_required": False,
                "named_author_voice_allowed": False,
            },
        }

        with patch(
            "data_sources.modules.content_scorer.rate_aeo_geo",
            return_value={"passed": True, "checks": {}},
        ) as rate, patch(
            "data_sources.modules.content_scorer.check_metric_proof_pack",
            return_value=[],
        ), patch(
            "data_sources.modules.content_scorer.check_customer_proof_diversity",
            return_value=[],
        ), patch(
            "data_sources.modules.content_scorer.check_review_story_identity",
            return_value=[],
        ):
            scorer._run_quality_gates(
                "# Article\n",
                {},
                validate_urls=False,
                validate_source_support=False,
                source_path="drafts/article.md",
                proof_sidecar=None,
                finalized_bom=finalized_bom,
                assembly_date="2026-05-22",
                paa_workflow_mode="refresh",
                paa_content_brief="research/content-brief-article.md",
                paa_answersocrates_blocker="collection unavailable",
                paa_expected_query="field service scheduling",
                paa_expected_collection_date="2026-05-21",
                paa_expected_run_id="article-run-123",
                paa_artifact="research/paa-questions-article-2026-05-21.md",
            )

        rate.assert_called_once_with(
            "# Article\n",
            {},
            source_path="drafts/article.md",
            proof_sidecar_content="",
            proof_sidecar_path=None,
            finalized_bom=finalized_bom,
            assembly_date="2026-05-22",
            paa_workflow_mode="refresh",
            paa_content_brief="research/content-brief-article.md",
            paa_answersocrates_blocker="collection unavailable",
            paa_expected_query="field service scheduling",
            paa_expected_collection_date="2026-05-21",
            paa_expected_run_id="article-run-123",
            paa_artifact="research/paa-questions-article-2026-05-21.md",
        )

    def test_quality_gate_passes_resolved_proof_sidecar_path_to_customer_proof_guard(
        self,
    ):
        scorer = ContentScorer()
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            article = root / "drafts" / "article.md"
            sidecar = root / "research" / "validation-article.md"
            article.parent.mkdir(parents=True)
            sidecar.parent.mkdir(parents=True)
            article.write_text("# Article\n", encoding="utf-8")
            sidecar.write_text("# Validation\n", encoding="utf-8")
            with patch(
                "data_sources.modules.content_scorer.rate_aeo_geo",
                return_value={"passed": True, "checks": {}},
            ), patch(
                "data_sources.modules.content_scorer.check_metric_proof_pack",
                return_value=[],
            ), patch(
                "data_sources.modules.content_scorer.check_customer_proof_diversity",
                return_value=[],
            ) as check_customer_proof, patch(
                "data_sources.modules.content_scorer.check_review_story_identity",
                return_value=[],
            ):
                scorer._run_quality_gates(
                    "# Article\n",
                    {},
                    validate_urls=False,
                    validate_source_support=False,
                    source_path=str(article),
                    proof_sidecar=str(sidecar),
                )

        self.assertEqual(
            check_customer_proof.call_args.kwargs["proof_sidecar_path"],
            str(sidecar.resolve()),
        )

    def test_url_validation_failure_blocks_content_scorer_when_enabled(self):
        scorer = ContentScorer()
        blocked = UrlValidationResult(
            url="https://example.com/dead",
            status="unresolved",
            status_code=404,
            reason="HTTP 404",
            line=9,
            anchor="dead source",
        )

        with patch(
            "data_sources.modules.content_scorer.validate_content_urls",
            return_value=UrlValidationSummary([blocked]),
        ), patch.object(
            ContentScorer,
            "_score_humanity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_specificity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_structure_balance",
            return_value={"score": 100, "issues": [], "details": {}, "prose_ratio": 0.65},
        ), patch.object(
            ContentScorer,
            "_score_seo",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_readability",
            return_value={"score": 100, "issues": [], "details": {}, "flesch": 68},
        ):
            result = scorer.score(
                COMPLIANT_ARTICLE,
                {"primary_keyword": "hvac scheduling software"},
                validate_urls=True,
                source_path=write_paa_fixture(self, COMPLIANT_ARTICLE),
                paa_expected_run_id="content-scorer-fixture",
            )

        self.assertFalse(result["passed"])
        self.assertIn("url_validation", result["quality_gates"])
        self.assertFalse(result["quality_gates"]["url_validation"]["passed"])
        self.assertIn("URL validation blockers detected", result["priority_fixes"][0]["issue"])

    def test_faq_proof_failure_blocks_content_scorer(self):
        scorer = ContentScorer()
        content = COMPLIANT_ARTICLE.replace(
            "[field service scheduling](https://www.fieldtechnologiesonline.com/)",
            "a live dispatch calendar",
        ).replace(
            "[field service mobile app](https://www.achrnews.com/)",
            "mobile software",
        ).replace(
            "[field service invoicing](https://www.mckinsey.com/)",
            "invoicing",
        ).replace(FAQ_PROOF_BLOCK, "")

        with patch.object(
            ContentScorer,
            "_score_humanity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_specificity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_structure_balance",
            return_value={"score": 100, "issues": [], "details": {}, "prose_ratio": 0.65},
        ), patch.object(
            ContentScorer,
            "_score_seo",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_readability",
            return_value={"score": 100, "issues": [], "details": {}, "flesch": 68},
        ):
            result = scorer.score(
                content,
                {"primary_keyword": "hvac scheduling software"},
                source_path=write_paa_fixture(self, content),
                paa_expected_run_id="content-scorer-fixture",
            )

        self.assertFalse(result["passed"])
        self.assertIn("faq_proof", result["quality_gates"])
        self.assertFalse(result["quality_gates"]["faq_proof"]["passed"])
        self.assertIn("FAQ proof blockers detected", result["priority_fixes"][0]["issue"])
        faq_fix = result["priority_fixes"][0]["fix"]
        self.assertIn("citation_mode", faq_fix)
        self.assertIn("inline_required", faq_fix)
        self.assertIn("first visible answer paragraph", faq_fix)
        self.assertIn("natural", faq_fix)
        self.assertIn("quota-only", faq_fix)
        self.assertNotIn("or add question-specific", faq_fix)

    def test_source_support_failure_blocks_content_scorer_when_enabled(self):
        scorer = ContentScorer()
        source_support_findings = [
            {
                "rule_id": "source_evidence_not_found",
                "severity": "error",
                "line": 35,
                "column": 1,
                "match": "Shaffer Beacon Mechanical achieved a 60% increase in profit margin.",
                "message": "Proof evidence was not found in the cited source.",
            }
        ]

        with patch(
            "data_sources.modules.content_scorer.check_source_support",
            return_value=source_support_findings,
        ), patch.object(
            ContentScorer,
            "_score_humanity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_specificity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_structure_balance",
            return_value={"score": 100, "issues": [], "details": {}, "prose_ratio": 0.65},
        ), patch.object(
            ContentScorer,
            "_score_seo",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_readability",
            return_value={"score": 100, "issues": [], "details": {}, "flesch": 68},
        ):
            result = scorer.score(
                COMPLIANT_ARTICLE,
                {"primary_keyword": "hvac scheduling software"},
                validate_source_support=True,
                source_path=write_paa_fixture(self, COMPLIANT_ARTICLE),
                paa_expected_run_id="content-scorer-fixture",
            )

        self.assertFalse(result["passed"])
        self.assertIn("source_support", result["quality_gates"])
        self.assertFalse(result["quality_gates"]["source_support"]["passed"])
        self.assertIn("Source support blockers detected", result["priority_fixes"][0]["issue"])

    def test_source_support_runs_before_url_validation_when_both_are_enabled(self):
        scorer = ContentScorer()
        call_order = []

        def fake_source_support(*args, **kwargs):
            call_order.append("source_support")
            return []

        def fake_url_validation(*args, **kwargs):
            call_order.append("url_validation")
            return UrlValidationSummary([
                UrlValidationResult(
                    url="https://www.simprogroup.com/features/scheduling-software",
                    status="resolved",
                    status_code=200,
                    reason="HTTP 200",
                )
            ])

        with patch(
            "data_sources.modules.content_scorer.check_source_support",
            side_effect=fake_source_support,
        ), patch(
            "data_sources.modules.content_scorer.validate_content_urls",
            side_effect=fake_url_validation,
        ), patch.object(
            ContentScorer,
            "_score_humanity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_specificity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_structure_balance",
            return_value={"score": 100, "issues": [], "details": {}, "prose_ratio": 0.65},
        ), patch.object(
            ContentScorer,
            "_score_seo",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_readability",
            return_value={"score": 100, "issues": [], "details": {}, "flesch": 68},
        ):
            result = scorer.score(
                COMPLIANT_ARTICLE,
                {"primary_keyword": "hvac scheduling software"},
                validate_urls=True,
                validate_source_support=True,
                source_path=write_paa_fixture(self, COMPLIANT_ARTICLE),
                paa_expected_run_id="content-scorer-fixture",
            )

        self.assertTrue(result["quality_gates"]["source_support"]["passed"])
        self.assertTrue(result["quality_gates"]["url_validation"]["passed"])
        self.assertEqual(call_order, ["source_support", "url_validation"])

    def test_paa_provenance_failure_blocks_content_scorer(self):
        scorer = ContentScorer()
        content = COMPLIANT_ARTICLE.replace(PAA_PROVENANCE_BLOCK, "")

        with patch.object(
            ContentScorer,
            "_score_humanity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_specificity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_structure_balance",
            return_value={"score": 100, "issues": [], "details": {}, "prose_ratio": 0.65},
        ), patch.object(
            ContentScorer,
            "_score_seo",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_readability",
            return_value={"score": 100, "issues": [], "details": {}, "flesch": 68},
        ):
            result = scorer.score(
                content,
                {"primary_keyword": "hvac scheduling software"},
                source_path=write_paa_fixture(self, content),
                paa_expected_run_id="content-scorer-fixture",
            )

        self.assertFalse(result["passed"])
        self.assertIn("paa_provenance", result["quality_gates"])
        self.assertFalse(result["quality_gates"]["paa_provenance"]["passed"])
        self.assertIn("PAA provenance blockers detected", result["priority_fixes"][0]["issue"])

    def test_metric_proof_pack_failure_blocks_content_scorer(self):
        scorer = ContentScorer()
        content = COMPLIANT_ARTICLE.replace(METRIC_PROOF_BLOCK, "")

        with patch.object(
            ContentScorer,
            "_score_humanity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_specificity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_structure_balance",
            return_value={"score": 100, "issues": [], "details": {}, "prose_ratio": 0.65},
        ), patch.object(
            ContentScorer,
            "_score_seo",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_readability",
            return_value={"score": 100, "issues": [], "details": {}, "flesch": 68},
        ):
            result = scorer.score(
                content,
                {"primary_keyword": "hvac scheduling software"},
                source_path=write_paa_fixture(self, content),
                paa_expected_run_id="content-scorer-fixture",
            )

        self.assertFalse(result["passed"])
        self.assertIn("metric_proof_pack", result["quality_gates"])
        self.assertFalse(result["quality_gates"]["metric_proof_pack"]["passed"])
        self.assertIn("Metric Proof Pack blockers detected", result["priority_fixes"][0]["issue"])

    def test_customer_proof_diversity_failure_blocks_content_scorer(self):
        scorer = ContentScorer()
        content = COMPLIANT_ARTICLE.replace(CUSTOMER_PROOF_BLOCK, "")

        with patch.object(
            ContentScorer,
            "_score_humanity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_specificity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_structure_balance",
            return_value={"score": 100, "issues": [], "details": {}, "prose_ratio": 0.65},
        ), patch.object(
            ContentScorer,
            "_score_seo",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_readability",
            return_value={"score": 100, "issues": [], "details": {}, "flesch": 68},
        ):
            result = scorer.score(
                content,
                {"primary_keyword": "hvac scheduling software"},
                source_path=write_paa_fixture(self, content),
                paa_expected_run_id="content-scorer-fixture",
            )

        self.assertFalse(result["passed"])
        self.assertIn("customer_proof_diversity", result["quality_gates"])
        self.assertFalse(result["quality_gates"]["customer_proof_diversity"]["passed"])
        self.assertIn("Customer proof diversity blockers detected", result["priority_fixes"][0]["issue"])

    def test_raw_prevalidated_findings_do_not_suppress_proof_gate_runs(self):
        scorer = ContentScorer()
        aeo_result = {
            "score": 100,
            "passed": True,
            "checks": {
                "faq_proof": {"passed": True, "details": {"findings": []}},
                "paa_provenance": {"passed": True, "details": {"findings": []}},
            },
            "issues": [],
        }
        with patch(
            "data_sources.modules.content_scorer.rate_aeo_geo",
            return_value=aeo_result,
        ) as rate, patch(
            "data_sources.modules.content_scorer.check_metric_proof_pack",
            return_value=[],
        ) as metric_gate, patch(
            "data_sources.modules.content_scorer.check_customer_proof_diversity",
            return_value=[],
        ) as diversity_gate, patch(
            "data_sources.modules.content_scorer.check_review_story_identity",
            return_value=[],
        ) as review_gate:
            scorer.score(
                COMPLIANT_ARTICLE,
                {"primary_keyword": "hvac scheduling software"},
                source_path=write_paa_fixture(self, COMPLIANT_ARTICLE),
                paa_expected_run_id="content-scorer-fixture",
                prevalidated_gate_findings={
                    "metric_proof_pack": (),
                    "customer_proof_diversity": (),
                    "review_story_identity": (),
                },
            )

        metric_gate.assert_called_once()
        diversity_gate.assert_called_once()
        review_gate.assert_called_once()
        self.assertNotIn("prevalidated_gate_findings", rate.call_args.kwargs)

    def test_raw_prevalidated_findings_cannot_bypass_proof_gate_execution(self):
        scorer = ContentScorer()
        blocker = {
            "rule_id": "metric_proof_missing",
            "severity": "error",
            "line": 1,
            "column": 1,
            "message": "Metric proof is missing.",
            "suggestion": "Add proof.",
        }

        with patch(
            "data_sources.modules.content_scorer.check_metric_proof_pack",
            return_value=[blocker],
        ) as metric_gate:
            result = scorer.score(
                COMPLIANT_ARTICLE,
                {"primary_keyword": "hvac scheduling software"},
                source_path=write_paa_fixture(self, COMPLIANT_ARTICLE),
                paa_expected_run_id="content-scorer-fixture",
                prevalidated_gate_findings={"metric_proof_pack": ()},
            )

        metric_gate.assert_called_once()
        self.assertFalse(result["quality_gates"]["metric_proof_pack"]["passed"])


if __name__ == "__main__":
    unittest.main()
