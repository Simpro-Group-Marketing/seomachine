import io
import json
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from data_sources.modules import publish_readiness
from data_sources.modules.url_validator import UrlValidationResult, UrlValidationSummary


def finding(rule_id="blocked", severity="error", line=7):
    return {
        "rule_id": rule_id,
        "severity": severity,
        "line": line,
        "column": 1,
        "message": "Blocked by test fixture.",
        "suggestion": "Fix the fixture.",
    }


def passing_score():
    return {
        "passed": True,
        "content_quality_score": 91.2,
        "aeo_geo": {"score": 96, "passed": True},
        "priority_fixes": [],
    }


def failing_score():
    return {
        "passed": False,
        "content_quality_score": 81.0,
        "aeo_geo": {"score": 88, "passed": False},
        "priority_fixes": [{"dimension": "aeo_geo", "issue": "AEO failed"}],
    }


class PublishReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.article_path = Path(self.temp_dir.name) / "draft.md"
        self.article_path.write_text("# Draft\n\nBody copy.", encoding="utf-8")
        self.sidecar_path = Path(self.temp_dir.name) / "validation-draft.md"
        self.sidecar_path.write_text("Metric Proof Pack\n", encoding="utf-8")

    def patch_passing_gates(self, call_order=None, score=None):
        if call_order is None:
            call_order = []

        def gate(name):
            def _check(*args, **kwargs):
                call_order.append(name)
                return []

            return _check

        def url_check(*args, **kwargs):
            call_order.append("url_validator")
            return UrlValidationSummary([
                UrlValidationResult(
                    url="https://example.com/source",
                    status="resolved",
                    status_code=200,
                    reason="HTTP 200",
                )
            ])

        fake_scorer = Mock()

        def score_content(*args, **kwargs):
            call_order.append("content_scorer")
            return score or passing_score()

        fake_scorer.score.side_effect = score_content

        return [
            patch("data_sources.modules.publish_readiness.public_artifact_guard.check_file", side_effect=gate("public_artifact")),
            patch("data_sources.modules.publish_readiness.ai_copy_linter.lint_file", side_effect=gate("ai_copy_linter")),
            patch("data_sources.modules.publish_readiness.validate_file_urls", side_effect=url_check),
            patch("data_sources.modules.publish_readiness.public_research_link_guard.check_file", side_effect=gate("public_research_links")),
            patch("data_sources.modules.publish_readiness.metric_proof_pack_guard.check_file", side_effect=gate("metric_proof_pack")),
            patch("data_sources.modules.publish_readiness.numeric_claim_source_guard.check_file", side_effect=gate("numeric_claim_source")),
            patch("data_sources.modules.publish_readiness.faq_proof_guard.check_file", side_effect=gate("faq_proof")),
            patch("data_sources.modules.publish_readiness.paa_provenance_guard.check_file", side_effect=gate("paa_provenance")),
            patch("data_sources.modules.publish_readiness.source_support_guard.check_file", side_effect=gate("source_support")),
            patch("data_sources.modules.publish_readiness.customer_proof_diversity_guard.check_file", side_effect=gate("customer_proof_diversity")),
            patch("data_sources.modules.publish_readiness.review_story_identity_guard.check_file", side_effect=gate("review_story_identity")),
            patch("data_sources.modules.publish_readiness.ContentScorer", return_value=fake_scorer),
        ]

    def test_all_gates_pass_in_required_order(self):
        call_order = []
        patchers = self.patch_passing_gates(call_order=call_order)
        with patchers[0], patchers[1], patchers[2], patchers[3], patchers[4], patchers[5], patchers[6], patchers[7], patchers[8], patchers[9], patchers[10], patchers[11]:
            result = publish_readiness.run_publish_readiness(
                self.article_path,
                proof_sidecar=self.sidecar_path,
            )

        self.assertTrue(result["passed"])
        self.assertEqual(
            call_order,
            [
                "public_artifact",
                "ai_copy_linter",
                "url_validator",
                "public_research_links",
                "metric_proof_pack",
                "numeric_claim_source",
                "faq_proof",
                "paa_provenance",
                "source_support",
                "customer_proof_diversity",
                "review_story_identity",
                "content_scorer",
            ],
        )
        self.assertEqual([gate["name"] for gate in result["gates"]], call_order)
        self.assertEqual(result["score"], 91.2)
        self.assertEqual(result["aeo_geo"]["score"], 96)

    def test_finding_based_guard_error_fails_runner(self):
        patchers = self.patch_passing_gates()
        with patchers[0], patchers[1], patchers[2], patchers[3], patch(
            "data_sources.modules.publish_readiness.metric_proof_pack_guard.check_file",
            return_value=[finding("metric_source_unavailable")],
        ), patchers[5], patchers[6], patchers[7], patchers[8], patchers[9], patchers[10], patchers[11]:
            result = publish_readiness.run_publish_readiness(
                self.article_path,
                proof_sidecar=self.sidecar_path,
            )

        self.assertFalse(result["passed"])
        metric_gate = next(gate for gate in result["gates"] if gate["name"] == "metric_proof_pack")
        self.assertFalse(metric_gate["passed"])
        self.assertEqual(metric_gate["errors"], 1)

    def test_url_validation_blocker_fails_runner(self):
        patchers = self.patch_passing_gates()
        failing_url = UrlValidationSummary([
            UrlValidationResult(
                url="https://example.com/missing",
                status="unresolved",
                status_code=404,
                reason="HTTP 404",
                line=3,
                anchor="Missing",
            )
        ])
        with patchers[0], patchers[1], patch(
            "data_sources.modules.publish_readiness.validate_file_urls",
            return_value=failing_url,
        ), patchers[3], patchers[4], patchers[5], patchers[6], patchers[7], patchers[8], patchers[9], patchers[10], patchers[11]:
            result = publish_readiness.run_publish_readiness(
                self.article_path,
                proof_sidecar=self.sidecar_path,
            )

        self.assertFalse(result["passed"])
        url_gate = next(gate for gate in result["gates"] if gate["name"] == "url_validator")
        self.assertFalse(url_gate["passed"])
        self.assertEqual(url_gate["errors"], 1)

    def test_content_scorer_failure_fails_runner(self):
        patchers = self.patch_passing_gates(score=failing_score())
        with patchers[0], patchers[1], patchers[2], patchers[3], patchers[4], patchers[5], patchers[6], patchers[7], patchers[8], patchers[9], patchers[10], patchers[11]:
            result = publish_readiness.run_publish_readiness(
                self.article_path,
                proof_sidecar=self.sidecar_path,
            )

        self.assertFalse(result["passed"])
        score_gate = next(gate for gate in result["gates"] if gate["name"] == "content_scorer")
        self.assertFalse(score_gate["passed"])
        self.assertEqual(result["score"], 81.0)
        self.assertEqual(result["priority_fixes"][0]["issue"], "AEO failed")

    def test_warning_only_gate_counts_warnings_without_blocker_lines(self):
        patchers = self.patch_passing_gates()
        with patchers[0], patch(
            "data_sources.modules.publish_readiness.ai_copy_linter.lint_file",
            return_value=[finding("modal_verb", severity="warning")],
        ), patchers[2], patchers[3], patchers[4], patchers[5], patchers[6], patchers[7], patchers[8], patchers[9], patchers[10], patchers[11]:
            result = publish_readiness.run_publish_readiness(
                self.article_path,
                proof_sidecar=self.sidecar_path,
            )

        self.assertTrue(result["passed"])
        lint_gate = next(gate for gate in result["gates"] if gate["name"] == "ai_copy_linter")
        self.assertEqual(lint_gate["warnings"], 1)
        self.assertEqual(lint_gate["blockers"], [])

    def test_ai_copy_avoid_rule_error_fails_runner(self):
        patchers = self.patch_passing_gates()
        with patchers[0], patch(
            "data_sources.modules.publish_readiness.ai_copy_linter.lint_file",
            return_value=[finding("modal_verb", severity="error")],
        ), patchers[2], patchers[3], patchers[4], patchers[5], patchers[6], patchers[7], patchers[8], patchers[9], patchers[10], patchers[11]:
            result = publish_readiness.run_publish_readiness(
                self.article_path,
                proof_sidecar=self.sidecar_path,
            )

        self.assertFalse(result["passed"])
        lint_gate = next(gate for gate in result["gates"] if gate["name"] == "ai_copy_linter")
        self.assertFalse(lint_gate["passed"])
        self.assertEqual(lint_gate["errors"], 1)
        self.assertIn("modal_verb", lint_gate["blockers"][0])

    def test_proof_sidecar_is_passed_to_proof_gates_and_scorer(self):
        patchers = self.patch_passing_gates()
        with patchers[0], patchers[1], patchers[2], patchers[3] as public_research, patchers[4] as metric, patchers[5] as numeric, patchers[6] as faq, patchers[7] as paa, patchers[8] as source, patchers[9] as customer, patchers[10] as review, patchers[11] as scorer_class:
            result = publish_readiness.run_publish_readiness(
                self.article_path,
                proof_sidecar=self.sidecar_path,
            )

        self.assertTrue(result["passed"])
        self.assertEqual(public_research.call_args.kwargs["proof_sidecar"], str(self.sidecar_path))
        self.assertIn("url_summary", public_research.call_args.kwargs)
        for guard in [metric, numeric, faq, paa, source, customer, review]:
            self.assertEqual(guard.call_args.kwargs["proof_sidecar"], str(self.sidecar_path))
        scorer = scorer_class.return_value
        self.assertEqual(scorer.score.call_args.kwargs["proof_sidecar"], str(self.sidecar_path))
        self.assertTrue(scorer.score.call_args.kwargs["validate_urls"])
        self.assertTrue(scorer.score.call_args.kwargs["validate_source_support"])

    def test_public_research_guard_fails_manual_review_research_url(self):
        dol_url = "https://www.dol.gov/agencies/whd/flsa"
        self.article_path.write_text(
            (
                "# Draft\n\n"
                "## Keep employee time tracking compliant\n\n"
                f"Use the [FLSA overview]({dol_url}) for wage-hour recordkeeping guidance.\n"
            ),
            encoding="utf-8",
        )
        self.sidecar_path.write_text(
            (
                "## Source Map\n\n"
                "- Claim: The FLSA establishes wage-hour recordkeeping standards. "
                f"| URL: {dol_url} | Evidence: recordkeeping | Status: approved\n"
            ),
            encoding="utf-8",
        )
        failing_url = UrlValidationSummary([
            UrlValidationResult(
                url=dol_url,
                status="manual_review",
                status_code=403,
                reason="HTTP 403",
                line=5,
                anchor="FLSA overview",
            )
        ])
        patchers = self.patch_passing_gates()
        with ExitStack() as stack:
            stack.enter_context(patchers[0])
            stack.enter_context(patchers[1])
            stack.enter_context(patch(
                "data_sources.modules.publish_readiness.validate_file_urls",
                return_value=failing_url,
            ))
            for patcher in patchers[4:]:
                stack.enter_context(patcher)
            result = publish_readiness.run_publish_readiness(
                self.article_path,
                proof_sidecar=self.sidecar_path,
            )

        self.assertFalse(result["passed"])
        guard_gate = next(gate for gate in result["gates"] if gate["name"] == "public_research_links")
        self.assertFalse(guard_gate["passed"])
        self.assertIn(
            "Replace this source with an equivalent resolved public source",
            "\n".join(guard_gate["blockers"]),
        )

    def test_public_research_guard_passes_resolved_ecfr_replacement(self):
        ecfr_url = (
            "https://www.ecfr.gov/current/title-29/subtitle-B/chapter-V/"
            "subchapter-A/part-516/subpart-A/section-516.2"
        )
        self.article_path.write_text(
            (
                "# Draft\n\n"
                "## Keep employee time tracking compliant\n\n"
                f"Federal [recordkeeping rules for covered employees]({ecfr_url}) "
                "include hours worked each workday and total hours worked each workweek.\n"
            ),
            encoding="utf-8",
        )
        self.sidecar_path.write_text(
            (
                "## Source Map\n\n"
                "- Claim: Covered employers must keep records for non-exempt workers, "
                "including hours worked each day and total hours worked each workweek. "
                "| URL: https://www.dol.gov/agencies/whd/fact-sheets/21-flsa-recordkeeping "
                "| Status: rejected manual_review replacement required\n"
                "- Claim: Federal recordkeeping rules include hours worked each workday "
                f"and total hours worked each workweek. | URL: {ecfr_url} "
                "| Evidence: hours worked each workday and total hours worked each workweek "
                "| Status: approved | Use: public replacement link\n"
            ),
            encoding="utf-8",
        )
        passing_url = UrlValidationSummary([
            UrlValidationResult(
                url=ecfr_url,
                status="resolved",
                status_code=200,
                reason="HTTP 200",
                line=5,
                anchor="recordkeeping rules for covered employees",
            )
        ])
        patchers = self.patch_passing_gates()
        with ExitStack() as stack:
            stack.enter_context(patchers[0])
            stack.enter_context(patchers[1])
            stack.enter_context(patch(
                "data_sources.modules.publish_readiness.validate_file_urls",
                return_value=passing_url,
            ))
            for patcher in patchers[4:]:
                stack.enter_context(patcher)
            result = publish_readiness.run_publish_readiness(
                self.article_path,
                proof_sidecar=self.sidecar_path,
            )

        self.assertTrue(result["passed"], result)
        guard_gate = next(gate for gate in result["gates"] if gate["name"] == "public_research_links")
        self.assertTrue(guard_gate["passed"], guard_gate)

    def test_json_output_uses_stable_top_level_keys(self):
        patchers = self.patch_passing_gates()
        stdout = io.StringIO()
        with patchers[0], patchers[1], patchers[2], patchers[3], patchers[4], patchers[5], patchers[6], patchers[7], patchers[8], patchers[9], patchers[10], patchers[11], redirect_stdout(stdout):
            exit_code = publish_readiness.main([
                str(self.article_path),
                "--proof-sidecar",
                str(self.sidecar_path),
                "--json",
            ])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(
            sorted(payload.keys()),
            ["aeo_geo", "file", "gates", "passed", "priority_fixes", "proof_sidecar", "score"],
        )
        self.assertTrue(payload["passed"])


if __name__ == "__main__":
    unittest.main()
