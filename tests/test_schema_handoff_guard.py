import pytest

from data_sources.modules.schema_handoff_guard import _main, check_content


def article(schema_lines: list[str], *, author: str = "", faq: bool = True, video: bool = False) -> str:
    author_line = f"author: {author}\n" if author else ""
    schema = "\n".join(f"  - {line}" for line in schema_lines)
    faq_body = (
        "## Frequently Asked Questions\n\n### What is the workflow?\n\nUse a documented process.\n"
        if faq
        else "## Final checklist\n\nUse a documented process.\n"
    )
    video_body = (
        '<iframe src="https://www.youtube-nocookie.com/embed/abc123" title="Workflow"></iframe>\n'
        if video
        else ""
    )
    return f"""---
title: Workflow guide
{author_line}last_updated: 2026-08-06
schema_notes:
{schema}
---
# Workflow guide

{video_body}{faq_body}"""


BASE_SCHEMA = [
    "BlogPosting",
    "BreadcrumbList",
    "FAQPage",
    "Question and Answer inside FAQPage",
    "ImageObject for the featured image or logo",
    "Organization as publisher reference only, not a separate full schema block",
]


def rule_ids(findings: list[dict[str, object]]) -> set[str]:
    return {str(finding["rule_id"]) for finding in findings}


def test_missing_author_passes_without_person_schema_note() -> None:
    assert check_content(article(BASE_SCHEMA)) == []


def test_existing_inline_schema_notes_are_recognized() -> None:
    list_block = "schema_notes:\n" + "\n".join(
        f"  - {line}" for line in BASE_SCHEMA
    )
    inline = (
        'schema_notes: "Use BlogPosting, BreadcrumbList, and FAQPage. '
        'Nest Question and Answer inside FAQPage and ImageObject for the featured image. '
        'Reference Organization as publisher reference only, not a separate full schema block."'
    )
    content = article(BASE_SCHEMA).replace(list_block, inline)

    assert check_content(content) == []


def test_verified_author_requires_person_note_and_missing_author_forbids_it() -> None:
    proof = (
        "## Author Verification\n"
        "- Author: Jordan Lee | URL: https://www.simprogroup.com/authors/jordan-lee "
        "| Evidence: Author profile reviewed | Checked date: 2026-08-06 | Status: verified\n"
    )
    missing_person = check_content(article(BASE_SCHEMA, author="Jordan Lee"), proof_content=proof)
    orphan_person = check_content(article(BASE_SCHEMA + ["Person as author"]))
    unverified_person = check_content(article(BASE_SCHEMA + ["Person as author"], author="Jordan Lee"), proof_content="")
    no_proof_person = check_content(article(BASE_SCHEMA + ["Person as author"], author="Jordan Lee"))

    assert "schema_handoff_person_missing" in rule_ids(missing_person)
    assert "schema_handoff_person_without_author" in rule_ids(orphan_person)
    assert "schema_handoff_author_unverified" in rule_ids(unverified_person)
    assert "schema_handoff_author_unverified" in rule_ids(no_proof_person)
    assert check_content(article(BASE_SCHEMA + ["Person as author"], author="Jordan Lee"), proof_content=proof) == []


def test_bare_author_verification_heading_in_sidecar_verifies_author() -> None:
    proof = (
        "Author Verification\n"
        "- Author: Jordan Lee | URL: https://www.simprogroup.com/authors/jordan-lee "
        "| Evidence: Author profile reviewed | Checked date: 2026-08-06 | Status: verified\n"
    )

    assert check_content(article(BASE_SCHEMA + ["Person as author"], author="Jordan Lee"), proof_content=proof) == []


def test_plural_faq_heading_requires_faqpage_notes() -> None:
    content = article(
        [note for note in BASE_SCHEMA if note not in {"FAQPage", "Question and Answer inside FAQPage"}],
        faq=False,
    ).replace("## Final checklist", "## FAQs")

    findings = check_content(content)

    assert "schema_handoff_faqpage_missing" in rule_ids(findings)
    assert "schema_handoff_question_answer_missing" in rule_ids(findings)


@pytest.mark.parametrize(
    ("missing_note", "expected_rule"),
    [
        ("BlogPosting", "schema_handoff_blogposting_missing"),
        ("BreadcrumbList", "schema_handoff_breadcrumb_missing"),
        ("FAQPage", "schema_handoff_faqpage_missing"),
        ("Question and Answer inside FAQPage", "schema_handoff_question_answer_missing"),
        ("ImageObject for the featured image or logo", "schema_handoff_imageobject_missing"),
        ("Organization as publisher reference only, not a separate full schema block", "schema_handoff_publisher_reference_missing"),
    ],
)
def test_required_handoff_notes_fail_closed(missing_note: str, expected_rule: str) -> None:
    findings = check_content(article([note for note in BASE_SCHEMA if note != missing_note]))

    assert expected_rule in rule_ids(findings)


def test_faq_notes_are_forbidden_without_visible_faqs() -> None:
    findings = check_content(article(BASE_SCHEMA, faq=False))

    assert "schema_handoff_faqpage_without_faq" in rule_ids(findings)
    assert "schema_handoff_question_answer_without_faq" in rule_ids(findings)


def test_videoobject_is_required_if_and_only_if_video_is_embedded() -> None:
    missing = check_content(article(BASE_SCHEMA, video=True))
    orphan = check_content(article(BASE_SCHEMA + ["VideoObject"], video=False))

    assert "schema_handoff_videoobject_missing" in rule_ids(missing)
    assert "schema_handoff_videoobject_without_video" in rule_ids(orphan)
    assert check_content(article(BASE_SCHEMA + ["VideoObject"], video=True)) == []


def test_a_plain_video_source_link_is_not_an_embedded_video() -> None:
    content = article(BASE_SCHEMA).replace(
        "Use a documented process.",
        "Use a [documented process](https://www.youtube.com/watch?v=abc123).",
    )

    assert check_content(content) == []


def test_non_video_iframe_does_not_require_videoobject() -> None:
    content = article(BASE_SCHEMA).replace(
        "# Workflow guide\n\n",
        '# Workflow guide\n\n<iframe src="https://forms.example.com/contact" title="Contact form"></iframe>\n\n',
    )

    assert check_content(content) == []


def test_rendered_json_ld_and_implementation_claims_are_forbidden() -> None:
    rendered = article(BASE_SCHEMA) + '\n<script type="application/ld+json">{"@type":"BlogPosting"}</script>\n'
    claimed = article(BASE_SCHEMA + ["Rendered JSON-LD implemented in CMS"])

    assert "schema_handoff_rendered_jsonld_forbidden" in rule_ids(check_content(rendered))
    assert "schema_handoff_implementation_claim_forbidden" in rule_ids(check_content(claimed))


def test_explicitly_negated_schema_implementation_note_is_allowed() -> None:
    content = article(
        BASE_SCHEMA
        + ["CMS handoff only; JSON-LD is not rendered or implemented in this artifact"]
    )

    assert check_content(content) == []


def test_cli_accepts_proof_sidecar_for_verified_author(tmp_path) -> None:
    article_path = tmp_path / "article.md"
    proof_path = tmp_path / "validation.md"
    article_path.write_text(article(BASE_SCHEMA + ["Person as author"], author="Jordan Lee"), encoding="utf-8")
    proof_path.write_text(
        "## Author Verification\n"
        "- Author: Jordan Lee | URL: https://www.simprogroup.com/authors/jordan-lee "
        "| Evidence: Author profile reviewed | Checked date: 2026-08-06 | Status: verified\n",
        encoding="utf-8",
    )

    assert _main([str(article_path), "--proof-sidecar", str(proof_path)]) == 0
