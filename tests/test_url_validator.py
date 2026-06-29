import os
import tempfile
import unittest
from pathlib import Path

import requests

from data_sources.modules.url_validator import (
    UrlValidationResult,
    UrlValidationSummary,
    UrlValidator,
    extract_urls,
    format_summary,
    validate_file_urls,
)


class FakeResponse:
    def __init__(self, status_code, url="https://example.com/final"):
        self.status_code = status_code
        self.url = url


class FakeSession:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if not self.outcomes:
            raise AssertionError("No fake HTTP outcome queued")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class UrlExtractionTests(unittest.TestCase):
    def test_extracts_markdown_and_bare_urls_while_ignoring_images_code_and_special_links(self):
        content = """
---
Meta Title: Example
---

This paragraph has [a source](https://example.com/source) and a bare
https://bare.example/path URL.

![Image alt](https://cdn.example.com/image.png)

`https://inline-code.example.com`

```
[coded](https://code.example.com)
https://also-code.example.com
```

[Mail](mailto:team@example.com)
[Phone](tel:+18005551212)
[Anchor](#faq)
"""

        links = extract_urls(content)

        self.assertEqual(
            [link.url for link in links],
            ["https://example.com/source", "https://bare.example/path"],
        )
        self.assertEqual(links[0].anchor, "a source")
        self.assertGreaterEqual(links[0].line, 6)

    def test_resolves_relative_simpro_paths_against_default_base_url(self):
        links = extract_urls("Read [HVAC software](/industries/hvac-software).")

        self.assertEqual(
            [link.url for link in links],
            ["https://www.simprogroup.com/industries/hvac-software"],
        )


class UrlValidationTests(unittest.TestCase):
    def test_passes_two_hundred_and_three_hundred_statuses(self):
        session = FakeSession([FakeResponse(200), FakeResponse(301)])
        validator = UrlValidator(session=session)

        first = validator.validate_url("https://example.com/ok")
        second = validator.validate_url("https://example.com/redirect")

        self.assertEqual(first.status, "resolved")
        self.assertEqual(second.status, "resolved")

    def test_falls_back_to_get_when_head_is_not_allowed(self):
        session = FakeSession([FakeResponse(405), FakeResponse(200)])
        validator = UrlValidator(session=session)

        result = validator.validate_url("https://example.com/head-not-allowed")

        self.assertEqual(result.status, "resolved")
        self.assertEqual([call[0] for call in session.calls], ["HEAD", "GET"])

    def test_fails_not_found_and_gone_statuses(self):
        session = FakeSession([
            FakeResponse(404),
            FakeResponse(404),
            FakeResponse(410),
            FakeResponse(410),
        ])
        validator = UrlValidator(session=session)

        not_found = validator.validate_url("https://example.com/missing")
        gone = validator.validate_url("https://example.com/gone")

        self.assertEqual(not_found.status, "unresolved")
        self.assertEqual(gone.status, "unresolved")

    def test_treats_forbidden_and_unauthorized_as_manual_review_blockers(self):
        session = FakeSession([
            FakeResponse(401),
            FakeResponse(401),
            FakeResponse(403),
            FakeResponse(403),
        ])
        validator = UrlValidator(session=session)

        unauthorized = validator.validate_url("https://example.com/login")
        forbidden = validator.validate_url("https://example.com/forbidden")

        self.assertEqual(unauthorized.status, "manual_review")
        self.assertEqual(forbidden.status, "manual_review")

    def test_manual_review_summary_tells_agents_to_replace_not_remove_citation(self):
        report = format_summary(
            UrlValidationSummary([
                UrlValidationResult(
                    url="https://www.dol.gov/agencies/whd/fact-sheets/21-flsa-recordkeeping",
                    status="manual_review",
                    status_code=403,
                    reason="HTTP 403",
                    line=7,
                    anchor="DOL recordkeeping",
                )
            ])
        )

        self.assertIn(
            "Replace this source with an equivalent resolved public source",
            report,
        )
        self.assertIn(
            "Do not remove the citation without replacing it",
            report,
        )

    def test_passes_when_get_resolves_after_forbidden_head(self):
        session = FakeSession([FakeResponse(403), FakeResponse(200)])
        validator = UrlValidator(session=session)

        result = validator.validate_url("https://example.com/head-forbidden")

        self.assertEqual(result.status, "resolved")
        self.assertEqual([call[0] for call in session.calls], ["HEAD", "GET"])

    def test_reuses_cached_resolved_result_when_later_requests_are_rate_limited(self):
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            try:
                url = "https://example.com/cached"
                first_session = FakeSession([FakeResponse(200)])
                cache_dir = Path(".cache") / "url_validator"
                first_validator = UrlValidator(session=first_session, cache_dir=cache_dir)

                first = first_validator.validate_url(url)

                second_session = FakeSession([FakeResponse(429), FakeResponse(429)])
                second_validator = UrlValidator(session=second_session, cache_dir=cache_dir)
                second = second_validator.validate_url(url, line=12, anchor="Cached")

                self.assertEqual(first.status, "resolved")
                self.assertEqual(second.status, "resolved")
                self.assertEqual(second.line, 12)
                self.assertEqual(second.anchor, "Cached")
                self.assertEqual(second_session.calls, [])
            finally:
                os.chdir(old_cwd)

    def test_fails_timeout_dns_and_ssl_errors(self):
        session = FakeSession(
            [
                requests.exceptions.Timeout("slow"),
                requests.exceptions.ConnectionError("dns"),
                requests.exceptions.SSLError("ssl"),
            ]
        )
        validator = UrlValidator(session=session)

        results = [
            validator.validate_url("https://example.com/timeout"),
            validator.validate_url("https://example.com/dns"),
            validator.validate_url("https://example.com/ssl"),
        ]

        self.assertEqual([result.status for result in results], ["unresolved"] * 3)
        self.assertIn("slow", results[0].reason)

    def test_file_summary_flags_blockers(self):
        content = "[Good](https://example.com/ok) [Broken](https://example.com/missing)"

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "article.md"
            path.write_text(content, encoding="utf-8")
            session = FakeSession([FakeResponse(200), FakeResponse(404), FakeResponse(404)])
            summary = validate_file_urls(path, validator=UrlValidator(session=session))

        self.assertFalse(summary.passed)
        self.assertEqual(summary.total, 2)
        self.assertEqual(len(summary.blockers), 1)
        self.assertEqual(summary.blockers[0].url, "https://example.com/missing")


class ActiveRewriteUrlTests(unittest.TestCase):
    def test_hvac_rewrite_uses_current_epa_certification_url(self):
        root = Path(__file__).resolve().parents[1]
        candidates = [
            root / "rewrites" / "turn-hvac-business-into-franchise-rewrite-2026-06-09.md",
            root / "published" / "turn-hvac-business-into-franchise-rewrite-2026-06-09.md",
        ]
        path = next((candidate for candidate in candidates if candidate.exists()), None)
        if path is None:
            self.skipTest("Turn HVAC rewrite artifact is not present in this checkout")

        content = path.read_text(encoding="utf-8")

        self.assertNotIn(
            "https://www.epa.gov/section608/refrigerant-transition-and-end-use-restrictions",
            content,
        )
        self.assertIn(
            "https://www.epa.gov/section608/section-608-technician-certification-requirements",
            content,
        )


if __name__ == "__main__":
    unittest.main()
