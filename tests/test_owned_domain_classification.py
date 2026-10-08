from tests.fixture_text import fixture_text

import unittest

from data_sources.modules import public_research_link_guard
from data_sources.modules.content_scoring.seo_constants import is_owned_host
from data_sources.modules.numeric_claim_source_guard import _is_owned_proof_url
from data_sources.modules.url_validator import UrlValidationResult, UrlValidationSummary


DOL_SOURCE_MAP = fixture_text("content_evidence:test_public_research_link_guard-7-1")


def _owned_link_findings(url: str, anchor: str):
    article = (
        "# Draft\n\n## Keep employee time tracking compliant\n\n"
        f"FLSA recordkeeping guidance matters for payroll records. See [{anchor}]({url}).\n"
    )
    summary = UrlValidationSummary([
        UrlValidationResult(
            url=url,
            status="resolved",
            status_code=200,
            reason="HTTP 200",
            line=5,
            anchor=anchor,
        )
    ])
    return public_research_link_guard.check_content(
        article,
        proof_content=DOL_SOURCE_MAP,
        url_summary=summary,
    )


class OwnedHostTests(unittest.TestCase):
    def test_apex_www_and_subdomains_are_owned(self):
        for host in (
            "aroflo.com",
            "www.aroflo.com",
            "app.bigchange.com",
            "WWW.SimproGroup.com",
            "simpro.ai",
            "docs.clockshark.com",
            "www.simprogroup.com.",
            "aroflo.com.",
        ):
            with self.subTest(host=host):
                self.assertTrue(is_owned_host(host))

    def test_lookalike_and_unrelated_hosts_are_not_owned(self):
        for host in ("notaroflo.com", "aroflo.com.evil.test", "simpro.com", "dol.gov", ""):
            with self.subTest(host=host):
                self.assertFalse(is_owned_host(host))


class OwnedDomainTableDriftTests(unittest.TestCase):
    def test_group_owned_domains_match_shared_owned_apex_domains(self):
        from data_sources.modules.content_scoring.seo_constants import OWNED_APEX_DOMAINS
        from data_sources.modules.proof_link_policy import GROUP_OWNED_DOMAINS

        union = {
            domain.removeprefix("www.")
            for domains in GROUP_OWNED_DOMAINS.values()
            for domain in domains
        }
        self.assertEqual(union, set(OWNED_APEX_DOMAINS))


class OwnedLinksAreNotExternalResearchTests(unittest.TestCase):
    def _assert_owned_link_does_not_count(self, url: str, anchor: str):
        findings = _owned_link_findings(url, anchor)

        self.assertTrue(findings)
        self.assertIn(
            "do not count",
            " ".join(str(finding.get("suggestion", "")) for finding in findings),
        )

    def test_aroflo_links_do_not_count_as_external_research(self):
        self._assert_owned_link_does_not_count(
            "https://www.aroflo.com/features/timesheets", "AroFlo timesheets"
        )

    def test_bigchange_links_do_not_count_as_external_research(self):
        self._assert_owned_link_does_not_count(
            "https://www.bigchange.com/features/job-scheduling", "BigChange scheduling"
        )


class OwnedLinksAreNotManualReviewResearchTests(unittest.TestCase):
    def _manual_review_rule_ids(self, url: str) -> set[str]:
        article = f"""# Draft

## Timesheets

See the [timesheet guide]({url}).
"""
        summary = UrlValidationSummary([
            UrlValidationResult(
                url=url,
                status="manual_review",
                status_code=403,
                reason="HTTP 403",
                line=5,
                anchor="timesheet guide",
            )
        ])
        findings = public_research_link_guard.check_content(
            article, url_summary=summary
        )
        return {finding["rule_id"] for finding in findings}

    def test_owned_brand_links_are_not_flagged_as_public_research(self):
        for url in (
            "https://www.aroflo.com/features/timesheets",
            "https://www.bigchange.com/features/job-scheduling",
        ):
            with self.subTest(url=url):
                self.assertNotIn(
                    "manual_review_public_research_link",
                    self._manual_review_rule_ids(url),
                )

    def test_independent_manual_review_link_is_still_flagged(self):
        self.assertIn(
            "manual_review_public_research_link",
            self._manual_review_rule_ids("https://www.dol.gov/agencies/whd/flsa"),
        )


class OwnedProofUrlTests(unittest.TestCase):
    def test_simpro_ai_is_owned_proof(self):
        self.assertTrue(_is_owned_proof_url("https://www.simpro.ai/x"))

    def test_retired_simpro_com_is_not_owned_proof(self):
        self.assertFalse(_is_owned_proof_url("https://simpro.com/x"))

    def test_existing_owned_proof_domains_stay_owned(self):
        for url in (
            "https://www.simprogroup.com/x",
            "https://www.aroflo.com/x",
            "https://www.bigchange.com/x",
            "https://www.clockshark.com/x",
        ):
            with self.subTest(url=url):
                self.assertTrue(_is_owned_proof_url(url))


if __name__ == "__main__":
    unittest.main()
