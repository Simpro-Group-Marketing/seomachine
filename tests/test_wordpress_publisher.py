import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from data_sources.modules.url_validator import UrlValidationResult, UrlValidationSummary
from data_sources.modules.wordpress_publisher import WordPressPublisher


DRAFT = """# Example Draft

**Meta Title**: Example Draft for WordPress Publishing
**Meta Description**: Example draft description for publisher preflight tests.
**Target Keyword**: example draft
**URL Slug**: /blog/example-draft

This draft cites [a dead source](https://example.com/dead).
"""


def passing_readiness():
    return {
        "passed": True,
        "gates": [],
        "score": 91,
        "aeo_geo": {"score": 94},
        "priority_fixes": [],
    }


def failing_readiness(gate_name="ai_copy_linter"):
    return {
        "passed": False,
        "gates": [
            {
                "name": gate_name,
                "label": gate_name.replace("_", " ").title(),
                "passed": False,
                "blockers": ["line 8: modal_verb - Modal verbs weaken copy"],
            }
        ],
        "score": 82,
        "aeo_geo": {"score": 88},
        "priority_fixes": [{"issue": "AEO failed"}],
    }


class WordPressPublisherPreflightTests(unittest.TestCase):
    def test_new_strategy_guards_block_before_wordpress_api_calls(self):
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )

        for gate_name in ("source_quality", "blog_strategy", "schema_handoff"):
            with self.subTest(gate_name=gate_name), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "draft.md"
                sidecar = Path(tmp) / "validation-draft.md"
                path.write_text(DRAFT, encoding="utf-8")
                sidecar.write_text("Validation sidecar\n", encoding="utf-8")
                with patch(
                    "data_sources.modules.wordpress_publisher.validate_file_urls",
                    return_value=UrlValidationSummary([]),
                ), patch(
                    "data_sources.modules.wordpress_publisher.require_source_support",
                    return_value=[],
                ), patch(
                    "data_sources.modules.wordpress_publisher.run_publish_readiness",
                    return_value=failing_readiness(gate_name),
                ), patch.object(publisher, "create_draft") as create_draft:
                    with self.assertRaises(ValueError):
                        publisher.publish_draft(str(path), proof_sidecar=str(sidecar))
                create_draft.assert_not_called()

    def test_publish_stops_before_api_calls_when_url_validation_fails(self):
        blocked = UrlValidationResult(
            url="https://example.com/dead",
            status="unresolved",
            status_code=404,
            reason="HTTP 404",
            line=8,
            anchor="dead source",
        )
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_text(DRAFT, encoding="utf-8")

            with patch(
                "data_sources.modules.wordpress_publisher.validate_file_urls",
                return_value=UrlValidationSummary([blocked]),
            ), patch(
                "data_sources.modules.wordpress_publisher.run_publish_readiness",
                return_value=passing_readiness(),
            ), patch.object(publisher, "create_draft") as create_draft:
                with self.assertRaises(ValueError) as raised:
                    publisher.publish_draft(str(path))

        create_draft.assert_not_called()
        self.assertIn("URL validation failed", str(raised.exception))
        self.assertIn("https://example.com/dead", str(raised.exception))

    def test_publish_stops_before_api_calls_when_source_support_fails(self):
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_text(DRAFT, encoding="utf-8")

            with patch(
                "data_sources.modules.wordpress_publisher.validate_file_urls",
                return_value=UrlValidationSummary([]),
            ), patch(
                "data_sources.modules.wordpress_publisher.require_source_support",
                side_effect=ValueError("Source support validation failed before WordPress publish"),
            ), patch(
                "data_sources.modules.wordpress_publisher.run_publish_readiness",
                return_value=passing_readiness(),
            ), patch.object(publisher, "create_draft") as create_draft:
                with self.assertRaises(ValueError) as raised:
                    publisher.publish_draft(str(path))

        create_draft.assert_not_called()
        self.assertIn("Source support validation failed", str(raised.exception))

    def test_publish_stops_before_api_calls_when_publish_readiness_fails(self):
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            sidecar = Path(tmp) / "validation-draft.md"
            path.write_text(DRAFT, encoding="utf-8")
            sidecar.write_text("Metric Proof Pack\n", encoding="utf-8")

            with patch(
                "data_sources.modules.wordpress_publisher.validate_file_urls",
                return_value=UrlValidationSummary([]),
            ), patch(
                "data_sources.modules.wordpress_publisher.require_source_support",
                return_value=[],
            ), patch(
                "data_sources.modules.wordpress_publisher.run_publish_readiness",
                return_value=failing_readiness(),
            ) as readiness, patch.object(publisher, "create_draft") as create_draft:
                with self.assertRaises(ValueError) as raised:
                    publisher.publish_draft(str(path), proof_sidecar=str(sidecar))

        readiness.assert_called_once_with(str(path), proof_sidecar=str(sidecar))
        create_draft.assert_not_called()
        self.assertIn("Publish readiness failed before WordPress publish", str(raised.exception))
        self.assertIn("ai_copy_linter", str(raised.exception))

    def test_publish_forwards_context_artifacts_to_publish_readiness(self):
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "draft.md"
            sidecar = root / "validation-draft.md"
            request = root / "request.json"
            pack = root / "pack.json"
            receipt = root / "receipt.json"
            vault_root = root / "vault"
            path.write_text(DRAFT, encoding="utf-8")
            sidecar.write_text("Metric Proof Pack\n", encoding="utf-8")
            for artifact in (request, pack, receipt):
                artifact.write_text("{}", encoding="utf-8")
            vault_root.mkdir()

            with patch(
                "data_sources.modules.wordpress_publisher.validate_file_urls",
                return_value=UrlValidationSummary([]),
            ), patch(
                "data_sources.modules.wordpress_publisher.require_source_support",
                return_value=[],
            ), patch(
                "data_sources.modules.wordpress_publisher.run_publish_readiness",
                return_value=passing_readiness(),
            ) as readiness, patch.object(
                publisher,
                "create_draft",
                return_value={"id": 123, "link": "https://wordpress.example/example-draft"},
            ), patch.object(publisher, "set_yoast_meta", return_value={}):
                publisher.publish_draft(
                    str(path),
                    proof_sidecar=str(sidecar),
                    context_request=str(request),
                    context_pack=str(pack),
                    context_receipt=str(receipt),
                    vault_root=str(vault_root),
                )

        readiness.assert_called_once_with(
            str(path),
            proof_sidecar=str(sidecar),
            context_request=str(request),
            context_pack=str(pack),
            context_receipt=str(receipt),
            vault_root=str(vault_root),
        )

    def test_page_publish_selects_landing_page_readiness(self):
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "service-page.md"
            path.write_text(DRAFT, encoding="utf-8")

            with patch(
                "data_sources.modules.wordpress_publisher.validate_file_urls",
                return_value=UrlValidationSummary([]),
            ), patch(
                "data_sources.modules.wordpress_publisher.require_source_support",
                return_value=[],
            ), patch(
                "data_sources.modules.wordpress_publisher.run_publish_readiness",
                return_value=passing_readiness(),
            ) as readiness, patch.object(
                publisher,
                "create_draft",
                return_value={"id": 123, "link": "https://wordpress.example/service-page"},
            ), patch.object(publisher, "set_yoast_meta", return_value={}):
                publisher.publish_draft(str(path), post_type="page")

        readiness.assert_called_once_with(
            str(path),
            proof_sidecar=None,
            artifact_kind="landing_page",
        )

    def test_publish_runs_readiness_before_wordpress_api_calls(self):
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )
        calls = []

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_text(DRAFT, encoding="utf-8")

            def readiness(*args, **kwargs):
                calls.append("readiness")
                return passing_readiness()

            def create_draft(*args, **kwargs):
                calls.append("create_draft")
                return {"id": 123, "link": "https://wordpress.example/example-draft"}

            with patch(
                "data_sources.modules.wordpress_publisher.validate_file_urls",
                return_value=UrlValidationSummary([]),
            ), patch(
                "data_sources.modules.wordpress_publisher.require_source_support",
                return_value=[],
            ), patch(
                "data_sources.modules.wordpress_publisher.run_publish_readiness",
                side_effect=readiness,
            ), patch.object(publisher, "create_draft", side_effect=create_draft), patch.object(
                publisher,
                "set_yoast_meta",
                return_value={},
            ):
                result = publisher.publish_draft(str(path))

        self.assertEqual(calls, ["readiness", "create_draft"])
        self.assertEqual(result["post_id"], 123)


if __name__ == "__main__":
    unittest.main()
