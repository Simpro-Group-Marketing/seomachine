"""Regression coverage for repeated sentence opener diagnostics."""

from data_sources.modules.ai_copy_linter import lint_content


def repeated_start_findings(content: str) -> list[dict[str, object]]:
    """Return only repeated sentence opener findings."""
    return [
        finding
        for finding in lint_content(content)
        if finding["rule_id"] == "repeated_sentence_start"
    ]


def test_repeated_sentence_starts_report_every_cluster_and_all_lines() -> None:
    findings = repeated_start_findings(
        "Lead source follows each job.\n"
        "Lead source stays visible after booking.\n"
        "Lead source links ad spend to invoices.\n\n"
        "Job status guides the next action.\n"
        "Job status keeps dispatch aligned.\n"
        "Job status clarifies who owns follow-up."
    )

    assert [(item["match"], item["lines"]) for item in findings] == [
        ("lead source", [1, 2, 3]),
        ("job status", [5, 6, 7]),
    ]
    assert all(item["severity"] == "error" for item in findings)


def test_repeated_instructional_imperative_starts_are_warnings() -> None:
    findings = repeated_start_findings(
        "## Checklist\n\n"
        "Add the job number to the request.\n"
        "Add the requested amount to the request.\n"
        "Add the approval date to the request."
    )

    assert len(findings) == 1
    assert findings[0]["severity"] == "warning"
    assert findings[0]["lines"] == [3, 4, 5]


def test_repeated_what_to_write_table_imperative_starts_are_warnings() -> None:
    findings = repeated_start_findings(
        "| What to write |\n"
        "|---|\n"
        "| Add the job number to the request. |\n"
        "| Add the requested amount to the request. |\n"
        "| Add the approval date to the request. |"
    )

    assert len(findings) == 1
    assert findings[0]["severity"] == "warning"
    assert findings[0]["lines"] == [3, 4, 5]


def test_repeated_checklist_imperative_starts_are_warnings() -> None:
    findings = repeated_start_findings(
        "## Draft Checklist\n\n"
        "- [ ] Review the job scope before drafting.\n"
        "- [ ] Review the proof before drafting.\n"
        "- [ ] Review the call to action before drafting."
    )

    assert len(findings) == 1
    assert findings[0]["severity"] == "warning"
    assert findings[0]["lines"] == [3, 4, 5]


def test_repeated_what_to_write_table_declarative_starts_are_errors() -> None:
    findings = repeated_start_findings(
        "| What to write |\n"
        "|---|\n"
        "| Status remains visible after review. |\n"
        "| Status remains assigned after review. |\n"
        "| Status remains current after review. |"
    )

    assert len(findings) == 1
    assert findings[0]["severity"] == "error"
    assert findings[0]["lines"] == [3, 4, 5]


def test_repeated_checklist_declarative_starts_are_errors() -> None:
    findings = repeated_start_findings(
        "## Draft Checklist\n\n"
        "- [ ] Status remains visible after review.\n"
        "- [ ] Status remains assigned after review.\n"
        "- [ ] Status remains current after review."
    )

    assert len(findings) == 1
    assert findings[0]["severity"] == "error"
    assert findings[0]["lines"] == [3, 4, 5]
