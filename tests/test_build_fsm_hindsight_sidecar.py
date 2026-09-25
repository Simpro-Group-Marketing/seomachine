from datetime import date

import pytest

from data_sources.modules.source_quality_guard import check_content
from scripts import build_fsm_hindsight_sidecar as builder


def source_map_rows(content: str) -> list[str]:
    start = content.index(f"{builder.SOURCE_MAP_HEADING}\n")
    end = content.index(f"{builder.SOURCE_MAP_NEXT_HEADING}\n", start)
    return [
        line
        for line in content[start:end].splitlines(keepends=True)
        if line.startswith("- Claim: ")
    ]


def test_historical_source_transform_removes_only_obsolete_fieldedge_row() -> None:
    historical = builder.SOURCE.read_text(encoding="utf-8")
    before_rows = source_map_rows(historical)

    transformed = builder.remove_obsolete_fieldedge_source_row(historical)
    after_rows = source_map_rows(transformed)

    obsolete_rows = [
        row
        for row in before_rows
        if builder.OBSOLETE_FIELDEDGE_CLAIM in row
        and builder.OBSOLETE_FIELDEDGE_URL in row
    ]
    assert len(obsolete_rows) == 1
    assert transformed == historical.replace(obsolete_rows[0], "", 1)
    assert after_rows == [row for row in before_rows if row != obsolete_rows[0]]
    assert builder.OBSOLETE_FIELDEDGE_CLAIM not in transformed
    assert builder.OBSOLETE_FIELDEDGE_URL not in transformed
    assert builder.FIELDEDGE_PRICING_URL in transformed


def test_historical_source_transform_requires_fieldedge_pricing_row() -> None:
    historical = builder.SOURCE.read_text(encoding="utf-8")
    pricing_row = next(
        row
        for row in source_map_rows(historical)
        if builder.FIELDEDGE_PRICING_URL in row
    )

    with pytest.raises(ValueError, match="valid FieldEdge pricing Source Map row"):
        builder.remove_obsolete_fieldedge_source_row(
            historical.replace(pricing_row, "", 1)
        )


def test_correction_record_supersedes_active_2026_09_24_artifact() -> None:
    historical = builder.SOURCE.read_text(encoding="utf-8")

    transformed = builder.add_correction_record(historical)

    assert transformed.count(builder.CORRECTION_RECORD.strip()) == 1
    assert (
        "2026-09-25.md` supersedes "
        "`research/validation-best-field-service-management-software-2026-09-24.md`"
        in transformed
    )
    assert "FieldEdge marketing page did not substantiate" in transformed
    assert "follow-up tasks, office notices, customer messages, or audit trails" in transformed
    assert transformed.index("## Governed Correction and Supersession Record") < transformed.index(
        "## Live-versus-local attribution boundary"
    )


def test_corrected_article_and_sidecar_lifecycle_dates_align() -> None:
    historical = builder.SOURCE.read_text(encoding="utf-8")
    transformed = builder.remove_obsolete_fieldedge_source_row(historical)
    transformed = transformed.replace(
        "- Last-updated date: 2026-09-24",
        "- Last-updated date: 2026-09-25",
        1,
    ).replace(
        "- Next review date: 2026-12-23",
        "- Next review date: 2026-12-24",
        1,
    )
    article = builder.ARTICLE.read_text(encoding="utf-8")

    findings = check_content(
        article,
        proof_content=transformed,
        today=date(2026, 9, 25),
    )

    assert findings == []
