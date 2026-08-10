import unittest

from data_sources.modules.publish_content_safety import (
    PublishContentSafetyError,
    validate_publish_content,
)


class PublishContentSafetyTests(unittest.TestCase):
    def test_allows_safe_markdown_and_approved_youtube_embed(self):
        markdown = """Read [the guide](/blog/guide) and [email us](mailto:team@example.com).

<div class="video" style="position: relative; aspect-ratio: 16/9; overflow: hidden">
<iframe src="https://www.youtube-nocookie.com/embed/abc123" title="Demo video" loading="lazy" allowfullscreen></iframe>
</div>
"""

        validate_publish_content(markdown)

    def test_ignores_markup_demonstrated_inside_code(self):
        markdown = """Use this example:

```html
<script>alert('demonstration only')</script>
```

Inline `<script>` is also code.
"""

        validate_publish_content(markdown)

    def test_rejects_javascript_markdown_autolink(self):
        with self.assertRaisesRegex(PublishContentSafetyError, "URL scheme"):
            validate_publish_content("<javascript:alert(1)>")
    def test_rejects_percent_encoded_javascript_scheme(self):
        with self.assertRaisesRegex(PublishContentSafetyError, "URL scheme"):
            validate_publish_content("[unsafe](java%73cript:alert(1))")

    def test_rejects_unsafe_url_with_nested_markdown_label(self):
        with self.assertRaisesRegex(PublishContentSafetyError, "URL scheme"):
            validate_publish_content("[outer [inner]](javascript:alert(1))")
    def test_rejects_entity_encoded_event_url_in_rendered_html(self):
        with self.assertRaisesRegex(PublishContentSafetyError, "URL scheme"):
            validate_publish_content(
                "Safe source.",
                rendered_html='<a href="jav&#x61;script:alert(1)">unsafe</a>',
            )

    def test_rejects_data_image_and_unapproved_iframe_host(self):
        with self.assertRaisesRegex(PublishContentSafetyError, "URL scheme"):
            validate_publish_content('<img src="data:image/svg+xml;base64,PHN2Zz4=">')
        with self.assertRaisesRegex(PublishContentSafetyError, "iframe source"):
            validate_publish_content(
                '<iframe src="https://video.example/embed/1" title="Video"></iframe>'
            )

    def test_rejects_unsafe_inline_style(self):
        with self.assertRaisesRegex(PublishContentSafetyError, "inline style"):
            validate_publish_content(
                '<div style="background-image: url(javascript:alert(1))">x</div>'
            )


if __name__ == "__main__":
    unittest.main()