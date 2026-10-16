from __future__ import annotations

from pathlib import Path

import pytest

from data_sources.modules.blog_identity_guard import check_article
from data_sources.modules.publishable_markdown import read_publishable_markdown
from data_sources.modules.video_embed import inspect_video_embeds


BASE_SCHEMA = (
    "  - BlogPosting\n"
    "  - BreadcrumbList\n"
    "  - ImageObject for the featured image or logo\n"
    "  - Organization as publisher reference only, not a separate full schema block\n"
)


def _article_text(*, author: str | None = None, body: str = "Body.") -> str:
    author_line = f"author: {author}\n" if author is not None else ""
    return (
        "---\n"
        "artifact_type: blog\n"
        "brand: BigChange\n"
        "title: Scheduling guide\n"
        "objective: Help service leaders make scheduling decisions\n"
        "audience: Field service leaders\n"
        "region: US\n"
        "last_updated: 2026-08-11\n"
        f"{author_line}"
        "schema_notes:\n"
        f"{BASE_SCHEMA}"
        "---\n"
        "# Scheduling guide\n\n"
        f"{body}\n"
    )


def _article(tmp_path: Path, *, author: str | None = None, body: str = "Body."):
    path = tmp_path / "article.md"
    path.write_text(_article_text(author=author, body=body), encoding="utf-8")
    return read_publishable_markdown(path)


@pytest.mark.parametrize(
    "author",
    (
        "Simpro Editorial Team",
        "Marketing Team",
        "Staff",
        "Admin",
        "Jane Smith, CEO",
        "By Jane Smith",
        "Acme Plumbing",
        "Field Service",
        "SimproGroup EditorialTeam",
    ),
)
def test_blog_identity_rejects_organizational_or_role_bylines(author: str):
    rules = {
        finding["rule_id"]
        for finding in check_article(_article_text(author=author))
    }

    assert "blog_identity_author_not_named_person" in rules


@pytest.mark.parametrize(
    "author",
    (
        "Corey O'Donnell",
        "Jean-Luc Picard",
        "J. R. Martinez",
        "María José Carreño Quiñones",
        "Jose\u0301 Garcia",
    ),
)
def test_blog_identity_preserves_person_like_named_authors(author: str):
    assert check_article(_article_text(author=author)) == []


@pytest.mark.parametrize(
    "embed",
    (
        '<iframe src="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"></iframe>',
        '<iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ?rel=0"></iframe>',
        '<iframe src="https://player.vimeo.com/video/123456789"></iframe>',
        '<video src="https://cdn.example.com/demo.mp4"></video>',
        '<video><source src="https://cdn.example.com/demo.webm"></video>',
    ),
)
def test_validated_https_video_sources_are_supported_embeds(
    tmp_path: Path,
    embed: str,
):
    inspection = inspect_video_embeds(_article(tmp_path, body=embed).raw)

    assert inspection.has_supported_embed is True
    assert inspection.errors == ()


@pytest.mark.parametrize(
    "embed",
    (
        '<iframe src="https://www.youtube-nocookie.com/embed/abc123"></iframe>',
        '<iframe src="https://player.vimeo.com/video/not-a-number"></iframe>',
        '<iframe src="http://www.youtube.com/embed/dQw4w9WgXcQ"></iframe>',
        '<iframe src="https://evil.youtube.com/embed/dQw4w9WgXcQ"></iframe>',
        '<iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ" src="https://example.com/not-video"></iframe>',
        "<video></video>",
        '<video src=""></video>',
        '<video src="http://cdn.example.com/demo.mp4"></video>',
        '<video><source src="https://cdn.example.com/readme.txt"></video>',
        '<video src="https://cdn.example.com/demo.mp4" src="https://cdn.example.com/other.mp4"></video>',
    ),
)
def test_attempted_but_invalid_video_embeds_report_errors(
    tmp_path: Path,
    embed: str,
):
    assert inspect_video_embeds(_article(tmp_path, body=embed).raw).errors


def test_a_non_video_iframe_is_not_a_video_embed(tmp_path: Path):
    inspection = inspect_video_embeds(
        _article(
            tmp_path,
            body='<iframe src="https://maps.example.com/embed/location"></iframe>',
        ).raw
    )

    assert inspection.has_supported_embed is False
    assert inspection.errors == ()


@pytest.mark.parametrize(
    "body",
    (
        "`<iframe src=\"https://www.youtube.com/embed/dQw4w9WgXcQ\"></iframe>`",
        "~~~html\n<iframe src=\"https://www.youtube.com/embed/dQw4w9WgXcQ\"></iframe>\n~~~",
    ),
)
def test_inline_and_tilde_fenced_embed_examples_are_ignored(
    tmp_path: Path,
    body: str,
):
    inspection = inspect_video_embeds(_article(tmp_path, body=body).raw)

    assert inspection.has_supported_embed is False
    assert inspection.errors == ()


def test_an_unclosed_video_iframe_reports_an_error(tmp_path: Path):
    assert inspect_video_embeds(
        _article(
            tmp_path,
            body='<iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ">',
        ).raw
    ).errors
