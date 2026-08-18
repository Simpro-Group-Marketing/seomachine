from tests.fixture_text import fixture_text

import os
import base64
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from data_sources.modules.grav_publisher import (
    GravPartialPublishError,
    GravPublishError,
    GravPublisher,
    main,
)


DRAFT_WITH_SLUG = fixture_text("publisher_contracts:test_grav_publisher-21-1")


CANONICAL_DRAFT = fixture_text("publisher_contracts:test_grav_publisher-41-2")


def passing_readiness():
    return {
        "passed": True,
        "gates": [],
        "score": 91,
        "aeo_geo": {"score": 94},
        "priority_fixes": [],
    }


def _write_bom(tmpdir: str) -> str:
    path = Path(tmpdir) / "blog-assembly-bom.json"
    path.write_text('{"schema":"simpro-blog-assembly-bom/v1"}', encoding="utf-8")
    return str(path)


def failing_readiness():
    return {
        "passed": False,
        "gates": [
            {
                "name": "metric_proof_pack",
                "label": "Metric Proof Pack",
                "passed": False,
                "blockers": ["line 1: metric_proof_pack_missing"],
            }
        ],
        "score": 80,
        "aeo_geo": {"score": 88},
        "priority_fixes": [{"issue": "Metric Proof Pack blockers detected"}],
    }


def _write(tmpdir: str, name: str, content: str) -> str:
    path = Path(tmpdir) / name
    path.write_text(content, encoding="utf-8")
    return str(path)


class ParseTests(unittest.TestCase):
    def setUp(self):
        self.pub = GravPublisher(
            repo="owner/repo", branch="dev", blog_path="blogs", lang="en"
        )

    def test_parses_frontmatter_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            draft = self.pub.parse_draft_file(_write(tmp, "post.md", DRAFT_WITH_SLUG))

        self.assertEqual(
            draft["meta_title"], "Payments for Trades Businesses and Faster Cash Flow"
        )
        self.assertEqual(draft["primary_keyword"], "payments for trades businesses")
        self.assertEqual(draft["author"], "Simpro")
        self.assertEqual(draft["last_updated"], "2026-05-28")

    def test_title_prefers_meta_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            draft = self.pub.parse_draft_file(_write(tmp, "post.md", DRAFT_WITH_SLUG))
        self.assertEqual(
            draft["title"], "Payments for Trades Businesses and Faster Cash Flow"
        )

    def test_body_strips_frontmatter_and_leading_h1(self):
        with tempfile.TemporaryDirectory() as tmp:
            draft = self.pub.parse_draft_file(_write(tmp, "post.md", DRAFT_WITH_SLUG))
        body = draft["content"]
        self.assertFalse(body.startswith("---"))
        self.assertNotIn("Meta Title:", body)
        self.assertNotIn("# Payments for Trades Businesses:", body)
        self.assertTrue(
            body.startswith("Payments for trades businesses are the invoice")
        )
        # Subheadings inside the body are preserved.
        self.assertIn("## Why it matters", body)

    def test_parses_canonical_snake_case_frontmatter_and_lists(self):
        with tempfile.TemporaryDirectory() as tmp:
            draft = self.pub.parse_draft_file(
                _write(tmp, "canonical.md", CANONICAL_DRAFT)
            )

        self.assertEqual(draft["title"], "Canonical SEO Title | Simpro")
        self.assertEqual(draft["meta_description"], "Canonical description.")
        self.assertEqual(draft["primary_keyword"], "field service software")
        self.assertEqual(draft["secondary_keywords"], "job management, scheduling")
        self.assertEqual(draft["author"], "Corey O'Donnell")
        self.assertEqual(draft["last_updated"], "2026-08-10")
        self.assertEqual(draft["slug"], "canonical-post")
        self.assertEqual(draft["content"], "Canonical body copy.")


class SlugTests(unittest.TestCase):
    def setUp(self):
        self.pub = GravPublisher(repo="owner/repo")

    def test_slug_from_url_slug_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "some-random-filename-2026.md", DRAFT_WITH_SLUG)
            draft = self.pub.parse_draft_file(path)
        self.assertEqual(draft["slug"], "modern-customer-payment-expectations-trades")

    def test_slug_falls_back_to_filename(self):
        no_slug = DRAFT_WITH_SLUG.replace(
            "URL Slug: /blog/modern-customer-payment-expectations-trades\n", ""
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "How To Price HVAC Jobs.md", no_slug)
            draft = self.pub.parse_draft_file(path)
        self.assertEqual(draft["slug"], "how-to-price-hvac-jobs")

    def test_slug_falls_back_to_h1_when_no_slug_or_filename(self):
        no_slug = DRAFT_WITH_SLUG.replace(
            "URL Slug: /blog/modern-customer-payment-expectations-trades\n", ""
        )
        with tempfile.TemporaryDirectory() as tmp:
            # Filename of only punctuation slugifies to empty -> fall back to H1.
            path = _write(tmp, "___.md", no_slug)
            draft = self.pub.parse_draft_file(path)
        self.assertEqual(
            draft["slug"],
            "payments-for-trades-businesses-meeting-modern-customer-expectations",
        )


class FrontmatterTests(unittest.TestCase):
    def setUp(self):
        self.pub = GravPublisher(repo="owner/repo", blog_path="blogs", lang="en")

    def _draft(self, tmp):
        return self.pub.parse_draft_file(_write(tmp, "post.md", DRAFT_WITH_SLUG))

    def test_frontmatter_contains_grav_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            fm = self.pub.build_grav_frontmatter(self._draft(tmp))

        self.assertTrue(fm.startswith("---"))
        self.assertTrue(fm.endswith("---"))
        self.assertIn(
            "title: 'Payments for Trades Businesses and Faster Cash Flow'", fm
        )
        self.assertIn("date: '2026-05-28 00:00'", fm)
        self.assertIn("taxonomy:", fm)
        self.assertIn("        - blog", fm)
        self.assertIn("        - 'field service payments'", fm)
        self.assertIn("    description: 'Improve payments", fm)
        self.assertIn(
            "    keywords: 'payments for trades businesses, field service payments", fm
        )
        self.assertIn("author: 'Simpro'", fm)
        self.assertIn("published: true", fm)

    def test_yaml_quote_escapes_single_quotes(self):
        self.assertEqual(self.pub._yaml_quote("don't"), "'don''t'")

    def test_article_path_uses_blog_path_slug_and_lang(self):
        self.assertEqual(
            self.pub.article_repo_path("my-post"), "blogs/my-post/article.en.md"
        )

    def test_build_article_combines_frontmatter_and_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            draft = self._draft(tmp)
            article = self.pub.build_article(draft)
        self.assertIn("---\ntitle:", article)
        self.assertIn("Payments for trades businesses are the invoice", article)


class PublishPreflightTests(unittest.TestCase):
    def setUp(self):
        self.pub = GravPublisher(
            repo="owner/repo", branch="dev", blog_path="blogs", lang="en"
        )

    def test_public_plain_text_fields_reject_tags_controls_and_encoded_markup(self):
        unsafe_drafts = {
            "display_title": DRAFT_WITH_SLUG.replace(
                "# Payments for Trades Businesses: Meeting Modern Customer Expectations",
                "# &lt;img src=x onerror=alert(1)&gt;",
            ),
            "meta_title": DRAFT_WITH_SLUG.replace(
                "Payments for Trades Businesses and Faster Cash Flow",
                '"%3Cscript%3Ealert(1)%3C/script%3E"',
            ),
            "description": DRAFT_WITH_SLUG.replace(
                "Improve payments for trades businesses with clear invoices and flexible options.",
                '"&lt;svg onload=alert(1)&gt;"',
            ),
            "primary_keyword": DRAFT_WITH_SLUG.replace(
                "payments for trades businesses\nSecondary Keywords:",
                '"unsafe\\u0007keyword"\nSecondary Keywords:',
            ),
            "secondary_keyword": DRAFT_WITH_SLUG.replace(
                "field service payments, embedded payments, faster field service payments",
                "field service payments, %3Ciframe%3E",
            ),
            "author": DRAFT_WITH_SLUG.replace(
                "Author: Simpro", 'Author: "&lt;script&gt;"'
            ),
        }
        for field, source in unsafe_drafts.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                path = _write(tmp, "post.md", source)
                publisher = GravPublisher(repo="owner/repo")
                publisher.preview_root = Path(tmp) / "preview"

                with patch("pathlib.Path.write_text", return_value=1) as write_text:
                    with self.assertRaisesRegex(GravPublishError, "plain text"):
                        publisher.publish(path, dry_run=True)

                write_text.assert_not_called()

    def test_publish_stops_before_push_when_url_gate_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "post.md", DRAFT_WITH_SLUG)
            with (
                patch(
                    "data_sources.modules.grav_publisher.run_publish_readiness",
                    return_value={
                        "passed": False,
                        "gates": [
                            {
                                "name": "url_validator",
                                "label": "URL Validator",
                                "passed": False,
                                "blockers": ["https://example.com/dead: HTTP 404"],
                            }
                        ],
                        "priority_fixes": [],
                    },
                ),
                patch.object(self.pub, "push_article") as push_article,
            ):
                with self.assertRaises(GravPublishError) as raised:
                    self.pub.publish(path, dry_run=False)

        push_article.assert_not_called()
        self.assertIn("url_validator", str(raised.exception))
        self.assertIn("https://example.com/dead", str(raised.exception))

    def test_publish_stops_before_push_when_source_support_gate_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "post.md", DRAFT_WITH_SLUG)
            with (
                patch(
                    "data_sources.modules.grav_publisher.run_publish_readiness",
                    return_value={
                        "passed": False,
                        "gates": [
                            {
                                "name": "source_support",
                                "label": "Source Support",
                                "passed": False,
                                "blockers": ["Source support validation failed"],
                            }
                        ],
                        "priority_fixes": [],
                    },
                ),
                patch.object(self.pub, "push_article") as push_article,
            ):
                with self.assertRaises(GravPublishError) as raised:
                    self.pub.publish(path, dry_run=False)

        push_article.assert_not_called()
        self.assertIn("Source support validation failed", str(raised.exception))

    def test_publish_stops_before_push_when_publish_readiness_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "post.md", DRAFT_WITH_SLUG)
            sidecar = _write(tmp, "validation-post.md", "Metric Proof Pack\n")
            request = _write(tmp, "context-request.json", "{}")
            pack = _write(tmp, "context-pack.json", "{}")
            receipt = _write(tmp, "context-receipt.json", "{}")
            bom = _write_bom(tmp)
            with (
                patch(
                    "data_sources.modules.grav_publisher.run_publish_readiness",
                    return_value=failing_readiness(),
                ) as readiness,
                patch.object(self.pub, "push_article") as push_article,
            ):
                with self.assertRaises(GravPublishError) as raised:
                    self.pub.publish(
                        path,
                        dry_run=False,
                        proof_sidecar=sidecar,
                        context_request=request,
                        context_pack=pack,
                        context_receipt=receipt,
                        assembly_bom=bom,
                        vault_root=Path(tmp),
                    )

        readiness.assert_called_once_with(
            path,
            proof_sidecar=sidecar,
            context_request=request,
            context_pack=pack,
            context_receipt=receipt,
            assembly_bom=bom,
            vault_root=Path(tmp),
        )
        push_article.assert_not_called()
        self.assertIn(
            "Publish readiness failed before Grav publish", str(raised.exception)
        )
        self.assertIn("metric_proof_pack", str(raised.exception))

    def test_publish_runs_readiness_before_grav_push(self):
        calls = []

        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "post.md", DRAFT_WITH_SLUG)

            def readiness(*args, **kwargs):
                calls.append("readiness")
                return passing_readiness()

            def push_article(*args, **kwargs):
                calls.append("push_article")
                return {
                    "action": "created",
                    "commit_url": "https://github.example/commit",
                }

            with (
                patch(
                    "data_sources.modules.grav_publisher.run_publish_readiness",
                    side_effect=readiness,
                ),
                patch.object(self.pub, "push_article", side_effect=push_article),
            ):
                result = self.pub.publish(path, dry_run=False)

        self.assertEqual(calls, ["readiness", "push_article"])
        self.assertFalse(result["dry_run"])

    def test_publish_forwards_bom_and_reports_bom_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "post.md", DRAFT_WITH_SLUG)
            sidecar = _write(tmp, "validation.md", "Metric Proof Pack\n")
            bom = _write_bom(tmp)
            bom_hash = hashlib.sha256(Path(bom).read_bytes()).hexdigest()

            with (
                patch(
                    "data_sources.modules.grav_publisher.run_publish_readiness",
                    return_value=passing_readiness(),
                ) as readiness,
                patch.object(
                    self.pub,
                    "push_article",
                    return_value={
                        "action": "created",
                        "commit_url": "https://github.example/commit",
                    },
                ),
            ):
                result = self.pub.publish(
                    path,
                    dry_run=False,
                    proof_sidecar=sidecar,
                    assembly_bom=bom,
                )

        readiness.assert_called_once_with(
            path,
            proof_sidecar=sidecar,
            context_request=None,
            context_pack=None,
            context_receipt=None,
            assembly_bom=bom,
            vault_root=None,
        )
        self.assertEqual(
            result["publish_input_sha256"]["assembly_bom"],
            bom_hash,
        )

    def test_publish_rejects_article_changed_during_readiness(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(_write(tmp, "post.md", DRAFT_WITH_SLUG))

            def mutate_then_pass(*args, **kwargs):
                path.write_text(
                    "# Changed after readiness started\n\nChanged body.\n",
                    encoding="utf-8",
                )
                return passing_readiness()

            with (
                patch(
                    "data_sources.modules.grav_publisher.run_publish_readiness",
                    side_effect=mutate_then_pass,
                ),
                patch.object(self.pub, "push_article") as push_article,
            ):
                with self.assertRaisesRegex(
                    GravPublishError, "changed during readiness"
                ):
                    self.pub.publish(str(path), dry_run=False)

        push_article.assert_not_called()

    def test_publish_rejects_sidecar_changed_after_readiness_before_push(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "post.md", DRAFT_WITH_SLUG)
            sidecar = Path(_write(tmp, "validation.md", "sealed input"))

            original_build = self.pub.build_article

            def build_and_mutate(draft):
                sidecar.write_text("changed after readiness", encoding="utf-8")
                return original_build(draft)

            with (
                patch(
                    "data_sources.modules.grav_publisher.run_publish_readiness",
                    return_value=passing_readiness(),
                ),
                patch.object(self.pub, "build_article", side_effect=build_and_mutate),
                patch.object(self.pub, "push_article") as push_article,
            ):
                with self.assertRaisesRegex(GravPublishError, "publish inputs changed"):
                    self.pub.publish(
                        path,
                        dry_run=False,
                        proof_sidecar=str(sidecar),
                    )

        push_article.assert_not_called()

    def test_publish_reports_partial_when_receipt_changes_during_push(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "post.md", DRAFT_WITH_SLUG)
            receipt = Path(_write(tmp, "receipt.json", '{"receipt":"sealed"}'))

            def push_and_mutate(*args, **kwargs):
                receipt.write_text('{"receipt":"changed"}', encoding="utf-8")
                return {
                    "action": "created",
                    "commit_url": "https://github.example/commit/91",
                    "content_url": "https://github.example/content/91",
                }

            with (
                patch(
                    "data_sources.modules.grav_publisher.run_publish_readiness",
                    return_value=passing_readiness(),
                ),
                patch.object(self.pub, "push_article", side_effect=push_and_mutate),
            ):
                with self.assertRaises(GravPublishError) as raised:
                    self.pub.publish(
                        path,
                        dry_run=False,
                        context_receipt=str(receipt),
                    )

        self.assertIn("publish inputs changed", str(raised.exception))
        self.assertIn("https://github.example/commit/91", str(raised.exception))

    def test_unset_repo_fails_closed_for_live_request_but_explicit_dry_run_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "post.md", DRAFT_WITH_SLUG)
            preview_root = Path(tmp) / "preview"
            with patch.dict(os.environ, {"GRAV_REPO": ""}, clear=False):
                publisher = GravPublisher(repo=None)
            publisher.preview_root = preview_root

            with (
                patch(
                    "data_sources.modules.grav_publisher.run_publish_readiness"
                ) as readiness,
                patch("pathlib.Path.write_text", return_value=1),
            ):
                with self.assertRaisesRegex(GravPublishError, "GRAV_REPO"):
                    publisher.publish(path, dry_run=False)
                explicit = publisher.publish(path, dry_run=True)

        readiness.assert_not_called()
        self.assertTrue(explicit["dry_run"])
        self.assertNotIn("preview_path", explicit)
        self.assertFalse(preview_root.exists())

    def test_dry_run_cli_prints_in_memory_article_without_preview_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "post.md", DRAFT_WITH_SLUG)
            output = StringIO()
            with (
                patch.object(sys, "argv", ["grav_publisher.py", path, "--dry-run"]),
                patch.object(sys, "stdout", output),
            ):
                main()

        rendered = output.getvalue()
        self.assertIn("[dry run] No push performed.", rendered)
        self.assertIn("----- article.en.md -----", rendered)
        self.assertNotIn("Preview written to:", rendered)

    def test_unsafe_html_blocks_before_preview_write(self):
        unsafe = (
            DRAFT_WITH_SLUG
            + '\n<script src="https://example.com/payload.js"></script>\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "post.md", unsafe)
            publisher = GravPublisher(repo="owner/repo")
            publisher.preview_root = Path(tmp) / "preview"

            with patch("pathlib.Path.write_text", return_value=1) as write_text:
                with self.assertRaisesRegex(GravPublishError, "unsafe|script"):
                    publisher.publish(path, dry_run=True)

        write_text.assert_not_called()

    def test_unsafe_content_blocks_before_live_readiness_or_push(self):
        unsafe = DRAFT_WITH_SLUG + '\n<img src="data:text/html,payload">\n'
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "post.md", unsafe)
            publisher = GravPublisher(repo="owner/repo")

            with (
                patch(
                    "data_sources.modules.grav_publisher.run_publish_readiness"
                ) as readiness,
                patch.object(publisher, "push_article") as push_article,
            ):
                with self.assertRaisesRegex(GravPublishError, "URL scheme"):
                    publisher.publish(path, dry_run=False)

        readiness.assert_not_called()
        push_article.assert_not_called()

    def test_javascript_markdown_url_blocks_before_preview_write(self):
        unsafe = DRAFT_WITH_SLUG + "\n[unsafe](javascript:alert(1))\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "post.md", unsafe)
            publisher = GravPublisher(repo="owner/repo")
            publisher.preview_root = Path(tmp) / "preview"

            with patch("pathlib.Path.write_text", return_value=1) as write_text:
                with self.assertRaisesRegex(GravPublishError, "URL scheme"):
                    publisher.publish(path, dry_run=True)

        write_text.assert_not_called()

    def test_javascript_autolink_blocks_before_preview_write(self):
        unsafe = DRAFT_WITH_SLUG + "\n<javascript:alert(1)>\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "post.md", unsafe)
            publisher = GravPublisher(repo="owner/repo")
            publisher.preview_root = Path(tmp) / "preview"

            with patch("pathlib.Path.write_text", return_value=1) as write_text:
                with self.assertRaisesRegex(GravPublishError, "URL scheme"):
                    publisher.publish(path, dry_run=True)

        write_text.assert_not_called()

    def test_language_traversal_blocks_before_preview_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "post.md", DRAFT_WITH_SLUG)
            publisher = GravPublisher(repo="owner/repo")
            publisher.preview_root = Path(tmp) / "preview"

            with patch("pathlib.Path.write_text", return_value=1) as write_text:
                with self.assertRaisesRegex(GravPublishError, "language"):
                    publisher.publish(path, dry_run=True, lang="../../outside")

        write_text.assert_not_called()

    def test_blog_path_traversal_is_rejected(self):
        with self.assertRaisesRegex(GravPublishError, "blog path"):
            GravPublisher(repo="owner/repo", blog_path="../outside")


class GitHubApiBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.pub = GravPublisher(repo="owner/repo", branch="dev")

    def test_existing_sha_lookup_uses_explicit_get(self):
        with patch.object(
            self.pub,
            "_gh_api",
            return_value=(0, '{"sha":"abc123"}'),
        ) as api:
            sha = self.pub._get_existing_sha("blogs/post/article.en.md")

        self.assertEqual(sha, "abc123")
        self.assertEqual(
            api.call_args.args[0],
            [
                "-X",
                "GET",
                "repos/owner/repo/contents/blogs/post/article.en.md",
                "-f",
                "ref=dev",
            ],
        )

    def test_existing_sha_lookup_treats_only_404_as_missing(self):
        with patch.object(
            self.pub, "_gh_api", return_value=(1, "gh: Not Found (HTTP 404)")
        ):
            self.assertIsNone(self.pub._get_existing_sha("blogs/missing/article.en.md"))

        with patch.object(
            self.pub, "_gh_api", return_value=(1, "gh: Forbidden (HTTP 403)")
        ):
            with self.assertRaisesRegex(GravPublishError, "inspect existing"):
                self.pub._get_existing_sha("blogs/private/article.en.md")

    def test_push_article_requires_exact_remote_content_readback(self):
        article = "---\ntitle: 'Test'\n---\n\nBody.\n"
        encoded = base64.b64encode(article.encode("utf-8")).decode("ascii")
        put_response = json.dumps(
            {
                "commit": {"html_url": "https://github.example/commit/1"},
                "content": {
                    "html_url": "https://github.example/content/1",
                    "sha": "blob-1",
                },
            }
        )
        readback_response = json.dumps(
            {"sha": "blob-1", "encoding": "base64", "content": encoded}
        )
        with patch.object(
            self.pub,
            "_gh_api",
            side_effect=[
                (1, "gh: Not Found (HTTP 404)"),
                (0, put_response),
                (0, readback_response),
            ],
        ) as api:
            result = self.pub.push_article(
                "blogs/test/article.en.md",
                article,
                "Publish test",
            )

        self.assertEqual(result["commit_url"], "https://github.example/commit/1")
        self.assertEqual(result["content_url"], "https://github.example/content/1")
        self.assertEqual(
            result["remote_content_sha256"],
            hashlib.sha256(article.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(api.call_count, 3)

    def test_invalid_put_success_response_recovers_from_exact_readback(self):
        article = "Expected body.\n"
        encoded = base64.b64encode(article.encode("utf-8")).decode("ascii")
        readback = json.dumps(
            {"sha": "blob-recovered", "encoding": "base64", "content": encoded}
        )
        for invalid_response in ("not-json", "[]", "{}"):
            with (
                self.subTest(response=invalid_response),
                patch.object(
                    self.pub,
                    "_gh_api",
                    side_effect=[
                        (1, "gh: Not Found (HTTP 404)"),
                        (0, invalid_response),
                        (0, readback),
                    ],
                ) as api,
            ):
                result = self.pub.push_article(
                    "blogs/test/article.en.md",
                    article,
                    "Publish test",
                )

            self.assertEqual(result["action"], "recovered")
            self.assertTrue(result["recovered_after_ambiguous_failure"])
            self.assertEqual(api.call_count, 3)

    def test_ambiguous_put_failure_recovers_when_exact_target_content_is_visible(self):
        article = "Expected body.\n"
        encoded = base64.b64encode(article.encode("utf-8")).decode("ascii")
        readback = json.dumps(
            {"sha": "blob-recovered", "encoding": "base64", "content": encoded}
        )
        for failure in (
            "gh: HTTP 502 Bad Gateway",
            "read tcp: connection reset by peer",
            "context deadline exceeded",
            "Post https://api.github.com/repos/owner/repo/contents/x: EOF",
            "gh: error connecting to api.github.com",
            "Client.Timeout exceeded while awaiting headers",
            "gh: Client Closed Request (HTTP 499)",
        ):
            with (
                self.subTest(failure=failure),
                patch.object(
                    self.pub,
                    "_gh_api",
                    side_effect=[
                        (1, "gh: Not Found (HTTP 404)"),
                        (1, failure),
                        (0, readback),
                    ],
                ) as api,
            ):
                result = self.pub.push_article(
                    "blogs/test/article.en.md",
                    article,
                    "Publish test",
                )

            self.assertEqual(result["action"], "recovered")
            self.assertTrue(result["recovered_after_ambiguous_failure"])
            self.assertEqual(api.call_count, 3)

    def test_definitive_put_failure_does_not_attempt_ambiguous_readback(self):
        for status in (400, 401, 403, 404, 409, 422):
            with (
                self.subTest(status=status),
                patch.object(
                    self.pub,
                    "_gh_api",
                    side_effect=[
                        (1, "gh: Not Found (HTTP 404)"),
                        (1, f"gh: definitive failure (HTTP {status})"),
                    ],
                ) as api,
            ):
                with self.assertRaisesRegex(GravPublishError, f"HTTP {status}"):
                    self.pub.push_article(
                        "blogs/test/article.en.md",
                        "Expected body.\n",
                        "Publish test",
                    )

            self.assertEqual(api.call_count, 2)

    def test_put_timeout_recovers_when_exact_target_content_is_visible(self):
        article = "Expected body.\n"
        encoded = base64.b64encode(article.encode("utf-8")).decode("ascii")
        completed = [
            subprocess.CompletedProcess(
                [], 1, stdout="", stderr="gh: Not Found (HTTP 404)"
            ),
            subprocess.TimeoutExpired(["gh", "api"], 30),
            subprocess.CompletedProcess(
                [],
                0,
                stdout=json.dumps(
                    {"sha": "blob-recovered", "encoding": "base64", "content": encoded}
                ),
                stderr="",
            ),
        ]
        with (
            patch(
                "data_sources.modules.grav_publisher.shutil.which",
                return_value="gh",
            ),
            patch(
                "data_sources.modules.grav_publisher.subprocess.run",
                side_effect=completed,
            ) as run,
        ):
            result = self.pub.push_article(
                "blogs/test/article.en.md",
                article,
                "Publish test",
            )

        expected_hash = hashlib.sha256(article.encode("utf-8")).hexdigest()
        self.assertEqual(result["action"], "recovered")
        self.assertTrue(result["recovered_after_timeout"])
        self.assertEqual(result["remote_content_sha256"], expected_hash)
        put_calls = [call for call in run.call_args_list if "PUT" in call.args[0]]
        self.assertEqual(len(put_calls), 1)

    def test_put_timeout_with_different_target_returns_structured_partial_error(self):
        article = "Expected body.\n"
        wrong = base64.b64encode(b"Different body.\n").decode("ascii")
        completed = [
            subprocess.CompletedProcess(
                [], 1, stdout="", stderr="gh: Not Found (HTTP 404)"
            ),
            subprocess.TimeoutExpired(["gh", "api"], 30),
            subprocess.CompletedProcess(
                [],
                0,
                stdout=json.dumps(
                    {"sha": "blob-other", "encoding": "base64", "content": wrong}
                ),
                stderr="",
            ),
        ]
        with (
            patch(
                "data_sources.modules.grav_publisher.shutil.which",
                return_value="gh",
            ),
            patch(
                "data_sources.modules.grav_publisher.subprocess.run",
                side_effect=completed,
            ) as run,
        ):
            with self.assertRaises(GravPartialPublishError) as raised:
                self.pub.push_article(
                    "blogs/test/article.en.md",
                    article,
                    "Publish test",
                )

        expected_hash = hashlib.sha256(article.encode("utf-8")).hexdigest()
        self.assertEqual(raised.exception.repo, "owner/repo")
        self.assertEqual(raised.exception.branch, "dev")
        self.assertEqual(raised.exception.repo_path, "blogs/test/article.en.md")
        self.assertEqual(raised.exception.expected_content_sha256, expected_hash)
        self.assertIn(expected_hash, str(raised.exception))
        put_calls = [call for call in run.call_args_list if "PUT" in call.args[0]]
        self.assertEqual(len(put_calls), 1)

    def test_push_article_reports_partial_when_remote_content_differs(self):
        article = "Expected body.\n"
        put_response = json.dumps(
            {
                "commit": {"html_url": "https://github.example/commit/2"},
                "content": {
                    "html_url": "https://github.example/content/2",
                    "sha": "blob-2",
                },
            }
        )
        wrong = base64.b64encode(b"Different body.\n").decode("ascii")
        with patch.object(
            self.pub,
            "_gh_api",
            side_effect=[
                (1, "gh: Not Found (HTTP 404)"),
                (0, put_response),
                (
                    0,
                    json.dumps(
                        {"sha": "blob-2", "encoding": "base64", "content": wrong}
                    ),
                ),
            ],
        ):
            with self.assertRaises(GravPublishError) as raised:
                self.pub.push_article(
                    "blogs/test/article.en.md",
                    article,
                    "Publish test",
                )

        self.assertIn("https://github.example/commit/2", str(raised.exception))
        self.assertIn("readback", str(raised.exception))

    def test_gh_subprocess_timeout_becomes_grav_publish_error(self):
        with (
            patch(
                "data_sources.modules.grav_publisher.shutil.which", return_value="gh"
            ),
            patch(
                "data_sources.modules.grav_publisher.subprocess.run",
                side_effect=subprocess.TimeoutExpired(["gh", "api"], 30),
            ),
        ):
            with self.assertRaisesRegex(GravPublishError, "timed out"):
                self.pub._gh_api(["repos/owner/repo"])


if __name__ == "__main__":
    unittest.main()
