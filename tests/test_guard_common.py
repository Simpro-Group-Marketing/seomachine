import unittest


class GuardCommonTests(unittest.TestCase):
    def test_should_fail_matches_existing_guard_thresholds(self):
        from data_sources.modules.guard_common import should_fail

        findings = [
            {"severity": "warning"},
            {"severity": "error"},
        ]

        self.assertTrue(should_fail(findings, fail_on="warning"))
        self.assertTrue(should_fail(findings, fail_on="error"))
        self.assertFalse(should_fail(findings, fail_on="none"))
        self.assertFalse(should_fail([{"severity": "warning"}], fail_on="error"))

        with self.assertRaises(ValueError):
            should_fail(findings, fail_on="invalid")

    def test_summarize_findings_counts_error_and_warning_only(self):
        from data_sources.modules.guard_common import summarize_findings

        self.assertEqual(
            summarize_findings(
                [
                    {"severity": "warning"},
                    {"severity": "error"},
                    {"severity": "info"},
                    {"severity": "error"},
                ]
            ),
            {"error": 2, "warning": 1},
        )

    def test_make_finding_preserves_existing_json_shape_and_extra_fields(self):
        from data_sources.modules.guard_common import make_finding

        finding = make_finding(
            "example_rule",
            "error",
            7,
            message="Problem",
            suggestion="Fix it",
            match="bad text",
            customer="Example Co",
        )

        self.assertEqual(
            finding,
            {
                "rule_id": "example_rule",
                "severity": "error",
                "line": 7,
                "column": 1,
                "match": "bad text",
                "message": "Problem",
                "suggestion": "Fix it",
                "customer": "Example Co",
            },
        )

    def test_normalization_helpers_match_existing_guard_behavior(self):
        from data_sources.modules.guard_common import (
            normalize_for_match,
            normalize_key,
            normalize_whitespace,
        )

        self.assertEqual(normalize_for_match("What is Simpro's ROI?"), "what is simpro s roi")
        self.assertEqual(normalize_key(" Customer / Proof-ID "), "customer proof id")
        self.assertEqual(normalize_whitespace("  Same\n paragraph\tlink  "), "same paragraph link")


if __name__ == "__main__":
    unittest.main()
