import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from data_sources.modules.wordpress_publisher import (
    WordPressPartialPublishError,
    WordPressPublisher,
)


DRAFT = """# Example Draft

**Meta Title**: Example Draft for WordPress Publishing
**Meta Description**: Example draft description for publisher preflight tests.
**Target Keyword**: example draft
**URL Slug**: /blog/example-draft

This draft cites [a dead source](https://example.com/dead).
"""


CANONICAL_DRAFT = """---
title: "Canonical SEO Title | Simpro"
meta_description: "Canonical description."
primary_keyword: "field service software"
secondary_keywords:
  - "job management"
  - scheduling
target_url: "/blog/canonical-post"
author: "Corey O'Donnell"
last_updated: "2026-08-10"
schema_notes: "BlogPosting and BreadcrumbList"
---

# Canonical Display Title

Canonical body copy.
"""


def passing_readiness():
    return {
        "passed": True,
        "gates": [],
        "score": 91,
        "aeo_geo": {"score": 94},
        "priority_fixes": [],
    }


def failing_readiness():
    return {
        "passed": False,
        "gates": [
            {
                "name": "ai_copy_linter",
                "label": "AI Copy Linter",
                "passed": False,
                "blockers": ["line 8: modal_verb - Modal verbs weaken copy"],
            }
        ],
        "score": 82,
        "aeo_geo": {"score": 88},
        "priority_fixes": [{"issue": "AEO failed"}],
    }


class WordPressPublisherPreflightTests(unittest.TestCase):
    def test_page_template_preserves_safe_relative_identifier_case(self):
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "landing-page.md"
            path.write_text(DRAFT, encoding="utf-8")
            with (
                patch(
                    "data_sources.modules.wordpress_publisher.run_publish_readiness",
                    return_value=passing_readiness(),
                ),
                patch.object(
                    publisher,
                    "create_draft",
                    return_value={
                        "id": 91,
                        "link": "https://wordpress.example/?page_id=91",
                    },
                ) as create_draft,
                patch.object(
                    publisher,
                    "set_yoast_meta",
                    return_value={"yoast_seo": {}},
                ),
            ):
                result = publisher.publish_draft(
                    str(path),
                    post_type="page",
                    template="Templates/LandingPage.php",
                )

        self.assertEqual(
            create_draft.call_args.kwargs["template"],
            "Templates/LandingPage.php",
        )
        self.assertEqual(result["template"], "Templates/LandingPage.php")

    def test_unsafe_rendered_html_blocks_before_any_wordpress_write(self):
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )
        unsafe = DRAFT + '\n<img src="https://example.com/x.png" onerror="alert(1)">\n'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_text(unsafe, encoding="utf-8")
            with (
                patch(
                    "data_sources.modules.wordpress_publisher.run_publish_readiness",
                    return_value=passing_readiness(),
                ) as readiness,
                patch.object(publisher, "create_draft") as create_draft,
            ):
                with self.assertRaisesRegex(ValueError, "unsafe|onerror"):
                    publisher.publish_draft(str(path))

        readiness.assert_not_called()
        create_draft.assert_not_called()

    def test_javascript_markdown_url_blocks_before_any_wordpress_write(self):
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )
        unsafe = DRAFT + "\n[unsafe](javascript:alert(1))\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_text(unsafe, encoding="utf-8")
            with (
                patch(
                    "data_sources.modules.wordpress_publisher.run_publish_readiness",
                    return_value=passing_readiness(),
                ),
                patch.object(publisher, "create_draft") as create_draft,
            ):
                with self.assertRaisesRegex(ValueError, "URL scheme"):
                    publisher.publish_draft(str(path))

        create_draft.assert_not_called()

    def test_public_plain_text_fields_reject_tags_controls_and_encoded_markup(self):
        unsafe_drafts = {
            "display_title": DRAFT.replace(
                "# Example Draft",
                "# &lt;img src=x onerror=alert(1)&gt;",
            ),
            "meta_title": DRAFT.replace(
                "Example Draft for WordPress Publishing",
                "%3Cscript%3Ealert(1)%3C/script%3E",
            ),
            "description": DRAFT.replace(
                "Example draft description for publisher preflight tests.",
                "&lt;svg onload=alert(1)&gt;",
            ),
            "keyword_control": DRAFT.replace(
                "**Target Keyword**: example draft",
                "**Target Keyword**: example\u0007draft",
            ),
            "category": DRAFT.replace(
                "**URL Slug**: /blog/example-draft",
                "**Category**: %3Ciframe%3E\n**URL Slug**: /blog/example-draft",
            ),
            "tag": DRAFT.replace(
                "**URL Slug**: /blog/example-draft",
                "**Tags**: &lt;script&gt;\n**URL Slug**: /blog/example-draft",
            ),
        }
        for field, source in unsafe_drafts.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "draft.md"
                path.write_text(source, encoding="utf-8")
                publisher = WordPressPublisher(
                    url="https://wordpress.example",
                    username="editor",
                    app_password="password",
                )
                with (
                    patch(
                        "data_sources.modules.wordpress_publisher.run_publish_readiness",
                        return_value=passing_readiness(),
                    ) as readiness,
                    patch.object(
                        publisher,
                        "create_draft",
                        return_value={"id": 1, "link": ""},
                    ) as create_draft,
                    patch.object(
                        publisher,
                        "set_yoast_meta",
                        return_value={},
                    ),
                ):
                    with self.assertRaisesRegex(ValueError, "plain text"):
                        publisher.publish_draft(str(path))

                readiness.assert_not_called()
                create_draft.assert_not_called()

    def test_page_publish_forwards_template_and_noindex_settings(self):
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "landing-page.md"
            path.write_text(DRAFT, encoding="utf-8")
            with (
                patch(
                    "data_sources.modules.wordpress_publisher.run_publish_readiness",
                    return_value=passing_readiness(),
                ),
                patch.object(
                    publisher,
                    "create_draft",
                    return_value={
                        "id": 91,
                        "link": "https://wordpress.example/?page_id=91",
                    },
                ) as create_draft,
                patch.object(
                    publisher,
                    "set_yoast_meta",
                    return_value={"yoast_seo": {"robots_noindex": True}},
                ) as set_yoast,
            ):
                publisher.publish_draft(
                    str(path),
                    post_type="page",
                    template="landing-page",
                    noindex=True,
                )

        self.assertEqual(create_draft.call_args.kwargs["template"], "landing-page")
        self.assertTrue(set_yoast.call_args.kwargs["noindex"])

    def test_invalid_page_template_blocks_before_readiness(self):
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "landing-page.md"
            path.write_text(DRAFT, encoding="utf-8")
            with patch(
                "data_sources.modules.wordpress_publisher.run_publish_readiness"
            ) as readiness:
                with self.assertRaisesRegex(ValueError, "template"):
                    publisher.publish_draft(
                        str(path),
                        post_type="page",
                        template="../unsafe.php",
                    )

        readiness.assert_not_called()

    def test_publish_rejects_post_type_paths_before_readiness_or_api_calls(self):
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_text(DRAFT, encoding="utf-8")
            with (
                patch(
                    "data_sources.modules.wordpress_publisher.run_publish_readiness"
                ) as readiness,
                patch.object(publisher.session, "post") as post,
            ):
                with self.assertRaisesRegex(ValueError, "post type"):
                    publisher.publish_draft(str(path), post_type="posts/123")

        readiness.assert_not_called()
        post.assert_not_called()

    def test_publish_rejects_custom_post_type_before_readiness(self):
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_text(DRAFT, encoding="utf-8")
            with patch(
                "data_sources.modules.wordpress_publisher.run_publish_readiness"
            ) as readiness:
                with self.assertRaisesRegex(ValueError, "posts or pages"):
                    publisher.publish_draft(str(path), post_type="compare")

        readiness.assert_not_called()

    def test_noindex_is_written_when_seo_fields_are_empty(self):
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )
        parsed = {
            "title": "Draft",
            "meta_title": "",
            "meta_description": "",
            "target_keyword": "",
            "secondary_keywords": "",
            "slug": "draft",
            "category": "",
            "tags": "",
            "content": "Body.",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_text(DRAFT, encoding="utf-8")
            with (
                patch(
                    "data_sources.modules.wordpress_publisher.run_publish_readiness",
                    return_value=passing_readiness(),
                ),
                patch.object(publisher, "parse_draft_file", return_value=parsed),
                patch.object(
                    publisher,
                    "create_draft",
                    return_value={"id": 42, "link": "https://wordpress.example/?p=42"},
                ),
                patch.object(
                    publisher, "set_yoast_meta", return_value={"yoast_seo": {}}
                ) as set_yoast,
            ):
                publisher.publish_draft(str(path), noindex=True)

        set_yoast.assert_called_once()
        self.assertTrue(set_yoast.call_args.kwargs["noindex"])

    def test_publish_stops_before_api_calls_when_url_gate_fails(self):
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_text(DRAFT, encoding="utf-8")

            with (
                patch(
                    "data_sources.modules.wordpress_publisher.run_publish_readiness",
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
                patch.object(publisher, "create_draft") as create_draft,
            ):
                with self.assertRaises(ValueError) as raised:
                    publisher.publish_draft(str(path))

        create_draft.assert_not_called()
        self.assertIn("url_validator", str(raised.exception))
        self.assertIn("https://example.com/dead", str(raised.exception))

    def test_publish_stops_before_api_calls_when_source_support_gate_fails(self):
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_text(DRAFT, encoding="utf-8")

            with (
                patch(
                    "data_sources.modules.wordpress_publisher.run_publish_readiness",
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
                patch.object(publisher, "create_draft") as create_draft,
            ):
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
            request = Path(tmp) / "context-request.json"
            pack = Path(tmp) / "context-pack.json"
            receipt = Path(tmp) / "context-receipt.json"
            path.write_text(DRAFT, encoding="utf-8")
            sidecar.write_text("Metric Proof Pack\n", encoding="utf-8")

            with (
                patch(
                    "data_sources.modules.wordpress_publisher.run_publish_readiness",
                    return_value=failing_readiness(),
                ) as readiness,
                patch.object(publisher, "create_draft") as create_draft,
            ):
                with self.assertRaises(ValueError) as raised:
                    publisher.publish_draft(
                        str(path),
                        proof_sidecar=str(sidecar),
                        context_request=str(request),
                        context_pack=str(pack),
                        context_receipt=str(receipt),
                        vault_root=Path(tmp),
                    )

        readiness.assert_called_once_with(
            str(path),
            proof_sidecar=str(sidecar),
            context_request=str(request),
            context_pack=str(pack),
            context_receipt=str(receipt),
            vault_root=Path(tmp),
        )
        create_draft.assert_not_called()
        self.assertIn(
            "Publish readiness failed before WordPress publish", str(raised.exception)
        )
        self.assertIn("ai_copy_linter", str(raised.exception))

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

            with (
                patch(
                    "data_sources.modules.wordpress_publisher.run_publish_readiness",
                    side_effect=readiness,
                ),
                patch.object(publisher, "create_draft", side_effect=create_draft),
                patch.object(
                    publisher,
                    "set_yoast_meta",
                    return_value={},
                ),
            ):
                result = publisher.publish_draft(str(path))

        self.assertEqual(calls, ["readiness", "create_draft"])
        self.assertEqual(result["post_id"], 123)

    def test_publish_rejects_article_changed_during_readiness(self):
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_text(DRAFT, encoding="utf-8")

            def mutate_then_pass(*args, **kwargs):
                path.write_text(
                    "# Changed after readiness started\n\nChanged body.\n",
                    encoding="utf-8",
                )
                return passing_readiness()

            with (
                patch(
                    "data_sources.modules.wordpress_publisher.run_publish_readiness",
                    side_effect=mutate_then_pass,
                ),
                patch.object(
                    publisher,
                    "create_draft",
                    return_value={"id": 88, "link": "https://wordpress.example/?p=88"},
                ) as create_draft,
                patch.object(publisher, "set_yoast_meta", return_value={}),
            ):
                with self.assertRaisesRegex(ValueError, "changed during readiness"):
                    publisher.publish_draft(str(path))

        create_draft.assert_not_called()

    def test_publish_rejects_sidecar_changed_after_readiness_before_first_write(self):
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            sidecar = Path(tmp) / "validation.md"
            path.write_text(DRAFT, encoding="utf-8")
            sidecar.write_text("approved input", encoding="utf-8")
            parsed = publisher.parse_draft_file(str(path))

            def parse_and_mutate(*args, **kwargs):
                sidecar.write_text("changed after readiness", encoding="utf-8")
                return parsed

            with (
                patch(
                    "data_sources.modules.wordpress_publisher.run_publish_readiness",
                    return_value=passing_readiness(),
                ),
                patch.object(
                    publisher, "parse_draft_file", side_effect=parse_and_mutate
                ),
                patch.object(publisher, "create_draft") as create_draft,
            ):
                with self.assertRaisesRegex(ValueError, "publish inputs changed"):
                    publisher.publish_draft(
                        str(path),
                        proof_sidecar=str(sidecar),
                    )

        create_draft.assert_not_called()

    def test_publish_reports_partial_when_receipt_changes_during_draft_creation(self):
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            receipt = Path(tmp) / "receipt.json"
            path.write_text(DRAFT, encoding="utf-8")
            receipt.write_text('{"receipt":"sealed"}', encoding="utf-8")

            def create_and_mutate(*args, **kwargs):
                receipt.write_text('{"receipt":"changed"}', encoding="utf-8")
                return {"id": 91, "link": "https://wordpress.example/?p=91"}

            with (
                patch(
                    "data_sources.modules.wordpress_publisher.run_publish_readiness",
                    return_value=passing_readiness(),
                ),
                patch.object(publisher, "create_draft", side_effect=create_and_mutate),
                patch.object(publisher, "set_yoast_meta") as set_yoast,
            ):
                with self.assertRaises(WordPressPartialPublishError) as raised:
                    publisher.publish_draft(
                        str(path),
                        context_receipt=str(receipt),
                    )

        self.assertEqual(raised.exception.post_id, 91)
        self.assertIn("publish inputs changed", str(raised.exception))
        set_yoast.assert_not_called()

    def test_meta_failure_reports_created_draft_as_partial_success(self):
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_text(DRAFT, encoding="utf-8")
            with (
                patch(
                    "data_sources.modules.wordpress_publisher.run_publish_readiness",
                    return_value=passing_readiness(),
                ),
                patch.object(
                    publisher,
                    "create_draft",
                    return_value={"id": 77, "link": "https://wordpress.example/?p=77"},
                ),
                patch.object(
                    publisher,
                    "set_yoast_meta",
                    side_effect=RuntimeError("Yoast update failed"),
                ),
            ):
                with self.assertRaises(RuntimeError) as raised:
                    publisher.publish_draft(str(path))

        self.assertEqual(getattr(raised.exception, "post_id", None), 77)
        self.assertEqual(
            getattr(raised.exception, "edit_url", None),
            "https://wordpress.example/wp-admin/post.php?post=77&action=edit",
        )
        self.assertIn("draft was created", str(raised.exception).lower())


class WordPressPublisherParsingTests(unittest.TestCase):
    def test_parse_canonical_frontmatter_without_leaking_it_into_body(self):
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "canonical.md"
            path.write_text(CANONICAL_DRAFT, encoding="utf-8")
            draft = publisher.parse_draft_file(str(path))

        self.assertEqual(draft["title"], "Canonical Display Title")
        self.assertEqual(draft["meta_title"], "Canonical SEO Title | Simpro")
        self.assertEqual(draft["meta_description"], "Canonical description.")
        self.assertEqual(draft["target_keyword"], "field service software")
        self.assertEqual(draft["secondary_keywords"], "job management, scheduling")
        self.assertEqual(draft["slug"], "canonical-post")
        self.assertEqual(draft["content"], "Canonical body copy.")
        self.assertNotIn("schema_notes", draft["content"])


class WordPressPublisherApiBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )

    @staticmethod
    def _response(payload, headers=None):
        response = Mock()
        response.json.return_value = payload
        response.headers = headers or {}
        response.status_code = 200
        response.raise_for_status.return_value = None
        return response

    def _managed_draft(self, source_hash, post_id=501):
        publication_key = self.publisher._publication_key("posts", "title", source_hash)
        return {
            "id": post_id,
            "status": "draft",
            "slug": "title",
            "link": f"https://wordpress.example/?p={post_id}",
            "title": {"raw": "Title"},
            "content": {"raw": "<p>Body.</p>"},
            "excerpt": {"raw": ""},
            "categories": [],
            "tags": [],
            "meta": {
                "seo_machine_publication_key": publication_key,
                "seo_machine_source_sha256": source_hash,
            },
        }

    def test_create_draft_uses_bounded_request_timeout_and_exact_readback(self):
        content_hash = hashlib.sha256(b"<p>Body.</p>").hexdigest()
        publication_key = self.publisher._publication_key(
            "posts", "title", content_hash
        )
        self.publisher.session.post = Mock(
            return_value=self._response(
                {"id": 123, "link": "https://wordpress.example/?p=123"}
            )
        )
        self.publisher.session.get = Mock(
            side_effect=[
                self._response([]),
                self._response(
                    {
                        "id": 123,
                        "status": "draft",
                        "slug": "title",
                        "link": "https://wordpress.example/?p=123",
                        "title": {"raw": "Title"},
                        "content": {"raw": "<p>Body.</p>"},
                        "excerpt": {"raw": ""},
                        "categories": [],
                        "tags": [],
                        "meta": {
                            "seo_machine_publication_key": publication_key,
                            "seo_machine_source_sha256": content_hash,
                        },
                    }
                ),
            ]
        )

        result = self.publisher.create_draft("Title", "<p>Body.</p>", "title")

        self.assertEqual(result["status"], "draft")
        self.assertEqual(
            self.publisher.session.post.call_args.kwargs["timeout"], (5, 30)
        )
        self.assertEqual(self.publisher.session.get.call_count, 2)
        self.assertEqual(
            self.publisher.session.get.call_args_list[0].kwargs["params"],
            {"slug": "title", "status": "draft", "context": "edit", "per_page": 100},
        )
        self.assertEqual(
            self.publisher.session.get.call_args_list[1].kwargs["params"],
            {"context": "edit"},
        )

    def test_ambiguous_create_timeout_recovers_matching_draft_by_publication_key(self):
        source_hash = "a" * 64
        publication_key = self.publisher._publication_key("posts", "title", source_hash)
        recovered = {
            "id": 501,
            "status": "draft",
            "slug": "title",
            "link": "https://wordpress.example/?p=501",
            "title": {"raw": "Title"},
            "content": {"raw": "<p>Body.</p>"},
            "excerpt": {"raw": ""},
            "categories": [],
            "tags": [],
            "meta": {
                "seo_machine_publication_key": publication_key,
                "seo_machine_source_sha256": source_hash,
            },
        }
        self.publisher.session.get = Mock(
            side_effect=[self._response([]), self._response([recovered])]
        )
        self.publisher.session.post = Mock(
            side_effect=requests.Timeout("response lost after server accepted request")
        )

        result = self.publisher.create_draft(
            "Title",
            "<p>Body.</p>",
            "title",
            source_sha256=source_hash,
        )

        self.assertEqual(result["id"], 501)
        self.assertEqual(self.publisher.session.post.call_count, 1)
        self.assertEqual(self.publisher.session.get.call_count, 2)
        self.assertEqual(
            self.publisher.session.post.call_args.kwargs["json"]["meta"],
            {
                "seo_machine_publication_key": publication_key,
                "seo_machine_source_sha256": source_hash,
            },
        )

    def test_ambiguous_connection_5xx_and_malformed_success_all_reconcile(self):
        source_hash = "c" * 64
        cases = ("connection_error", "server_error", "malformed_success")
        for case in cases:
            with self.subTest(case=case):
                recovered = self._managed_draft(source_hash)
                self.publisher.session.get = Mock(
                    side_effect=[self._response([]), self._response([recovered])]
                )
                if case == "connection_error":
                    post = Mock(
                        side_effect=requests.ConnectionError("connection reset")
                    )
                elif case == "server_error":
                    response = self._response({"code": "server_error"})
                    response.status_code = 503
                    response.raise_for_status.side_effect = requests.HTTPError(
                        "server error",
                        response=response,
                    )
                    post = Mock(return_value=response)
                else:
                    response = self._response(None)
                    response.status_code = 201
                    response.json.side_effect = ValueError("truncated JSON")
                    post = Mock(return_value=response)
                self.publisher.session.post = post

                result = self.publisher.create_draft(
                    "Title",
                    "<p>Body.</p>",
                    "title",
                    source_sha256=source_hash,
                )

                self.assertEqual(result["id"], 501)
                self.assertEqual(post.call_count, 1)
                self.assertEqual(self.publisher.session.get.call_count, 2)

    def test_atomic_publication_conflict_reconciles_without_second_create(self):
        source_hash = "d" * 64
        recovered = self._managed_draft(source_hash, post_id=601)
        self.publisher.session.get = Mock(
            side_effect=[self._response([]), self._response([recovered])]
        )
        conflict = self._response(
            {
                "code": "seo_machine_publication_exists",
                "data": {"status": 409, "existing_post_id": 601},
            }
        )
        conflict.status_code = 409
        conflict.raise_for_status.side_effect = requests.HTTPError(
            "publication conflict",
            response=conflict,
        )
        self.publisher.session.post = Mock(return_value=conflict)

        result = self.publisher.create_draft(
            "Title",
            "<p>Body.</p>",
            "title",
            source_sha256=source_hash,
        )

        self.assertEqual(result["id"], 601)
        self.assertEqual(self.publisher.session.post.call_count, 1)
        self.assertEqual(self.publisher.session.get.call_count, 2)

    def test_matching_unmanaged_draft_blocks_instead_of_creating_duplicate(self):
        candidate = {
            "id": 502,
            "status": "draft",
            "slug": "title",
            "title": {"raw": "Title"},
            "content": {"raw": "<p>Body.</p>"},
            "excerpt": {"raw": ""},
            "categories": [],
            "tags": [],
            "meta": {},
        }
        self.publisher.session.get = Mock(return_value=self._response([candidate]))
        self.publisher.session.post = Mock()

        with self.assertRaisesRegex(RuntimeError, "missing idempotency metadata"):
            self.publisher.create_draft("Title", "<p>Body.</p>", "title")

        self.publisher.session.post.assert_not_called()

    def test_idempotency_lookup_checks_all_declared_pages_before_create(self):
        source_hash = "b" * 64
        publication_key = self.publisher._publication_key("posts", "title", source_hash)
        unrelated = [
            {
                "id": index + 1,
                "status": "draft",
                "slug": "title",
                "title": {"raw": f"Other {index}"},
                "content": {"raw": "Other body"},
                "excerpt": {"raw": ""},
                "categories": [],
                "tags": [],
                "meta": {},
            }
            for index in range(100)
        ]
        recovered = {
            "id": 700,
            "status": "draft",
            "slug": "title",
            "link": "https://wordpress.example/?p=700",
            "title": {"raw": "Title"},
            "content": {"raw": "<p>Body.</p>"},
            "excerpt": {"raw": ""},
            "categories": [],
            "tags": [],
            "meta": {
                "seo_machine_publication_key": publication_key,
                "seo_machine_source_sha256": source_hash,
            },
        }
        self.publisher.session.get = Mock(
            side_effect=[
                self._response(unrelated, {"X-WP-TotalPages": "2"}),
                self._response([recovered], {"X-WP-TotalPages": "2"}),
            ]
        )
        self.publisher.session.post = Mock()

        result = self.publisher.create_draft(
            "Title",
            "<p>Body.</p>",
            "title",
            source_sha256=source_hash,
        )

        self.assertEqual(result["id"], 700)
        self.publisher.session.post.assert_not_called()
        self.assertEqual(
            self.publisher.session.get.call_args_list[1].kwargs["params"]["page"],
            2,
        )

    def test_create_draft_reports_partial_when_remote_content_differs(self):
        content_hash = hashlib.sha256(b"<p>Body.</p>").hexdigest()
        publication_key = self.publisher._publication_key(
            "posts", "title", content_hash
        )
        self.publisher.session.post = Mock(
            return_value=self._response(
                {"id": 124, "link": "https://wordpress.example/?p=124"}
            )
        )
        self.publisher.session.get = Mock(
            side_effect=[
                self._response([]),
                self._response(
                    {
                        "id": 124,
                        "status": "draft",
                        "slug": "title",
                        "title": {"raw": "Title"},
                        "content": {"raw": "<p>Server changed the body.</p>"},
                        "excerpt": {"raw": ""},
                        "categories": [],
                        "tags": [],
                        "meta": {
                            "seo_machine_publication_key": publication_key,
                            "seo_machine_source_sha256": content_hash,
                        },
                    }
                ),
            ]
        )

        with self.assertRaises(WordPressPartialPublishError) as raised:
            self.publisher.create_draft("Title", "<p>Body.</p>", "title")

        self.assertEqual(raised.exception.post_id, 124)
        self.assertIn("draft readback", str(raised.exception))

    def test_yoast_page_noindex_payload_is_verified_from_response(self):
        response = self._response(
            {
                "yoast_seo": {
                    "seo_title": "Landing | Simpro",
                    "meta_description": "Landing description.",
                    "focus_keyphrase": "landing page",
                    "robots_noindex": True,
                }
            }
        )
        self.publisher.session.post = Mock(return_value=response)

        result = self.publisher.set_yoast_meta(
            42,
            "Landing | Simpro",
            "Landing description.",
            "landing page",
            post_type="pages",
            noindex=True,
        )

        payload = self.publisher.session.post.call_args.kwargs["json"]["yoast_seo"]
        self.assertTrue(payload["robots_noindex"])
        self.assertTrue(result["yoast_seo"]["robots_noindex"])

    def test_category_pagination_stops_at_declared_last_page(self):
        self.publisher.session.get = Mock(
            side_effect=[
                self._response(
                    [{"id": 4, "name": "Operations"}],
                    {"X-WP-TotalPages": "1"},
                ),
                self._response([]),
            ]
        )

        categories = self.publisher.get_categories()

        self.assertEqual(categories, {"operations": 4})
        self.assertEqual(self.publisher.session.get.call_count, 1)
        self.assertEqual(
            self.publisher.session.get.call_args.kwargs["timeout"],
            (5, 30),
        )

    def test_yoast_rest_plugin_supports_posts_pages_and_noindex(self):
        plugin = (
            Path(__file__).resolve().parents[1]
            / "wordpress"
            / "seo-machine-yoast-rest.php"
        ).read_text(encoding="utf-8")

        self.assertIn("foreach (['post', 'page'] as $post_type)", plugin)
        self.assertIn("_yoast_wpseo_meta-robots-noindex", plugin)
        self.assertIn("'robots_noindex'", plugin)
        self.assertIn("seo_machine_publication_key", plugin)
        self.assertIn("seo_machine_source_sha256", plugin)
        self.assertIn("rest_pre_insert_{$post_type}", plugin)
        self.assertIn("seo_machine_publication_recovery_required", plugin)
        self.assertIn("seo_machine_publication_reservation_unavailable", plugin)
        self.assertIn("'status' => 409", plugin)
        self.assertNotIn("rest_request_after_callbacks", plugin)
        self.assertIn("count($posts) >= 1", plugin)
        self.assertIn("seo_machine_publication_reservation_name", plugin)
        self.assertIn("seo_machine_acquire_publication_reservation", plugin)
        self.assertIn("seo_machine_release_publication_reservation", plugin)
        self.assertIn("add_option($reservation_name", plugin)
        self.assertIn("wp_json_encode", plugin)
        self.assertIn("'created_at'", plugin)
        self.assertIn("DELETE FROM {$wpdb->options}", plugin)
        self.assertNotIn("GET_LOCK", plugin)
        self.assertNotIn("SEO_MACHINE_PUBLICATION_LOCK_TTL", plugin)
        self.assertNotIn("publication_lock_is_stale", plugin)
        self.assertIn(
            "Ambiguous REST failures intentionally retain the durable reservation",
            plugin,
        )
        self.assertEqual(plugin.count("seo_machine_release_publication_reservation("), 3)
        self.assertGreaterEqual(plugin.count("seo_machine_find_publication("), 3)


if __name__ == "__main__":
    unittest.main()
