import unittest
from datetime import date

from data_sources.modules.proof_usage import count_customer_proof_usage


class ProofUsageTests(unittest.TestCase):
    def test_unique_article_count_ignores_duplicate_artifact_rows(self):
        ledger = {
            "uses": [
                {
                    "proof_id": "case-study-teamwired",
                    "customer": "TEAMWired",
                    "source_url": "https://www.simprogroup.com/case-studies/teamwired",
                    "article_slug": "same-article",
                    "artifact_path": "drafts/same-article.md",
                    "date_used": "2026-06-12",
                },
                {
                    "proof_id": "case-study-teamwired",
                    "customer": "TEAMWired",
                    "source_url": "https://www.simprogroup.com/case-studies/teamwired",
                    "article_slug": "same-article",
                    "artifact_path": "research/validation-same-article.md",
                    "date_used": "2026-06-12",
                },
            ],
        }

        usage = count_customer_proof_usage(
            ledger,
            proof_id="case-study-teamwired",
            source_url="https://www.simprogroup.com/case-studies/teamwired",
            customer="TEAMWired",
            reference_date=date(2026, 6, 15),
        )

        self.assertEqual(usage["total_uses"], 1)
        self.assertEqual(usage["recent_uses_90d"], 1)
        self.assertEqual(usage["total_occurrences"], 2)
        self.assertEqual(usage["recent_occurrences_90d"], 2)
        self.assertEqual(usage["baseline_recent_uses_90d"], 0)

    def test_overuse_baseline_raises_effective_reuse_counts(self):
        ledger = {
            "overuse_baselines": [
                {
                    "proof_id": "case-study-bge-digital",
                    "customer": "BGE Digital",
                    "source_url": "https://www.simprogroup.com/case-studies/bge-digital",
                    "recent_uses_90d": 3,
                    "total_uses": 5,
                    "source_note": "repo scan before active article repair",
                    "last_reviewed": "2026-06-15",
                }
            ],
            "uses": [],
        }

        usage = count_customer_proof_usage(
            ledger,
            proof_id="case-study-bge-digital",
            source_url="https://www.simprogroup.com/case-studies/bge-digital",
            customer="BGE Digital",
            reference_date=date(2026, 6, 15),
        )

        self.assertEqual(usage["total_uses"], 5)
        self.assertEqual(usage["recent_uses_90d"], 3)
        self.assertEqual(usage["total_occurrences"], 0)
        self.assertEqual(usage["recent_occurrences_90d"], 0)
        self.assertEqual(usage["baseline_recent_uses_90d"], 3)
        self.assertEqual(usage["baseline_total_uses"], 5)
        self.assertTrue(usage["overused"])

    def test_missing_baseline_does_not_change_normal_counts(self):
        ledger = {
            "overuse_baselines": [],
            "uses": [
                {
                    "proof_id": "quote-matrix-zebra-plumbing-onsite-quoting",
                    "customer": "Zebra Plumbing",
                    "source_url": "https://www.simprogroup.com/case-studies/zebra-plumbing",
                    "article_slug": "best-job-quoting",
                    "artifact_path": "drafts/best-job-quoting.md",
                    "date_used": "2026-06-12",
                }
            ],
        }

        usage = count_customer_proof_usage(
            ledger,
            proof_id="quote-matrix-zebra-plumbing-onsite-quoting",
            source_url="https://www.simprogroup.com/case-studies/zebra-plumbing",
            customer="Zebra Plumbing",
            reference_date=date(2026, 6, 15),
        )

        self.assertEqual(usage["total_uses"], 1)
        self.assertEqual(usage["recent_uses_90d"], 1)
        self.assertEqual(usage["baseline_recent_uses_90d"], 0)
        self.assertFalse(usage["overused"])


if __name__ == "__main__":
    unittest.main()
