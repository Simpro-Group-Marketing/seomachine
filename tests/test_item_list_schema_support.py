from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from data_sources.modules import blog_assembly_contract
from data_sources.modules.aeo_geo_rater import _check_schema
from data_sources.modules.blog_assembly_bom import _schema_policy
from data_sources.modules.blog_assembly_bom_guard import check_bom
from data_sources.modules.frontmatter import FrontmatterError, split_frontmatter
from data_sources.modules.publishable_markdown import read_publishable_markdown
from tests.test_blog_assembly_bom import (
    _build,
    _fixture,
    _refresh_normal_stage_receipts,
)


BASE_SCHEMA_NOTES = [
    "BlogPosting",
    "BreadcrumbList",
    "ImageObject for the featured image or logo",
    "Organization as publisher reference only, not a separate full schema block",
]
ITEM_LIST_NOTE = (
    "ItemList for the 14 compared tools, with exactly 14 ListItem entries"
)
ITEM_LIST_ENTRIES = [f"Tool {index}" for index in range(1, 15)]


def _metadata(
    *,
    note: str | None = ITEM_LIST_NOTE,
    entries: object = ITEM_LIST_ENTRIES,
) -> dict[str, object]:
    schema_notes = list(BASE_SCHEMA_NOTES)
    if note is not None:
        schema_notes.append(note)
    metadata: dict[str, object] = {"schema_notes": schema_notes}
    if entries is not None:
        metadata["item_list_entries"] = entries
    return metadata


def _add_item_list_frontmatter(
    article_path: Path,
    *,
    note: str = ITEM_LIST_NOTE,
    entries: list[str] = ITEM_LIST_ENTRIES,
) -> None:
    raw = article_path.read_text(encoding="utf-8")
    marker = (
        "  - Organization as publisher reference only, not a separate full "
        "schema block\n"
    )
    insertion = (
        f"{marker}  - {note}\n"
        "item_list_entries:\n"
        + "".join(f"  - {entry}\n" for entry in entries)
    )
    article_path.write_text(raw.replace(marker, insertion, 1), encoding="utf-8")


def test_aeo_schema_accepts_a_count_bound_item_list() -> None:
    result = _check_schema(
        "",
        _metadata(),
        visible_faq=False,
        finalized_bom=None,
    )

    assert result["passed"] is True
    assert result["details"]["item_list_entry_count"] == 14
    assert result["details"]["item_list_errors"] == []
    assert ITEM_LIST_NOTE not in result["details"]["unknown_entities"]


@pytest.mark.parametrize(
    ("note", "entries", "expected_error"),
    [
        (
            ITEM_LIST_NOTE,
            ITEM_LIST_ENTRIES[:-1],
            "item_list_entries count 13 does not match the declared count 14",
        ),
        (
            ITEM_LIST_NOTE,
            ITEM_LIST_ENTRIES[:-1] + ["Tool 1"],
            "item_list_entries must contain unique values",
        ),
        (
            ITEM_LIST_NOTE,
            [],
            "item_list_entries must be a nonempty YAML list",
        ),
        (
            ITEM_LIST_NOTE,
            "Tool 1",
            "item_list_entries must be a nonempty YAML list",
        ),
        (
            ITEM_LIST_NOTE,
            ITEM_LIST_ENTRIES[:-1] + [" "],
            "item_list_entries cannot contain empty values",
        ),
        (
            None,
            ITEM_LIST_ENTRIES,
            "item_list_entries requires exactly one canonical ItemList schema note",
        ),
    ],
)
def test_aeo_schema_rejects_inconsistent_item_list_metadata(
    note: str | None,
    entries: object,
    expected_error: str,
) -> None:
    result = _check_schema(
        "",
        _metadata(note=note, entries=entries),
        visible_faq=False,
        finalized_bom=None,
    )

    assert result["passed"] is False
    assert expected_error in result["details"]["item_list_errors"]


def test_aeo_schema_rejects_duplicate_item_list_notes() -> None:
    metadata = _metadata()
    metadata["schema_notes"] = [
        *metadata["schema_notes"],  # type: ignore[misc]
        ITEM_LIST_NOTE,
    ]

    result = _check_schema(
        "",
        metadata,
        visible_faq=False,
        finalized_bom=None,
    )

    assert result["passed"] is False
    assert (
        "schema_notes must contain exactly one canonical ItemList schema note"
        in result["details"]["item_list_errors"]
    )


def test_bom_schema_policy_accepts_and_requires_a_valid_item_list(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        blog_assembly_contract,
        "current_utc_date",
        lambda: date(2026, 8, 11),
    )
    paths = _fixture(tmp_path)
    _add_item_list_frontmatter(paths["article"])
    _refresh_normal_stage_receipts(paths)

    bom = _build(tmp_path, paths)

    assert ITEM_LIST_NOTE in bom["schema_policy"]["declared_entities"]
    assert ITEM_LIST_NOTE in bom["schema_policy"]["required_entities"]
    findings = check_bom(
        bom,
        article_path=paths["article"],
        validation_sidecar_path=paths["sidecar"],
        workspace_root=tmp_path,
        expected_lifecycle_state="provisional",
    )
    assert not {
        "bom_schema_entities_mismatch",
        "bom_schema_policy_mismatch",
    }.intersection(finding["rule_id"] for finding in findings)


def test_bom_schema_policy_accepts_a_valid_item_list_note_in_any_note_position(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        blog_assembly_contract,
        "current_utc_date",
        lambda: date(2026, 8, 11),
    )
    paths = _fixture(tmp_path)
    _add_item_list_frontmatter(paths["article"])
    raw = paths["article"].read_text(encoding="utf-8")
    raw = raw.replace(f"  - {ITEM_LIST_NOTE}\n", "", 1)
    raw = raw.replace(
        "  - BreadcrumbList\n",
        f"  - BreadcrumbList\n  - {ITEM_LIST_NOTE}\n",
        1,
    )
    paths["article"].write_text(raw, encoding="utf-8")
    _refresh_normal_stage_receipts(paths)

    bom = _build(tmp_path, paths)
    findings = check_bom(
        bom,
        article_path=paths["article"],
        validation_sidecar_path=paths["sidecar"],
        workspace_root=tmp_path,
        expected_lifecycle_state="provisional",
    )

    assert not {
        "bom_schema_entities_mismatch",
        "bom_schema_policy_mismatch",
    }.intersection(finding["rule_id"] for finding in findings)


def test_bom_builder_rejects_an_item_list_count_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        blog_assembly_contract,
        "current_utc_date",
        lambda: date(2026, 8, 11),
    )
    paths = _fixture(tmp_path)
    _add_item_list_frontmatter(paths["article"], entries=ITEM_LIST_ENTRIES[:-1])
    _refresh_normal_stage_receipts(paths)

    with pytest.raises(
        ValueError,
        match="item_list_entries count 13 does not match the declared count 14",
    ):
        _build(tmp_path, paths)


def test_bom_guard_returns_a_stable_item_list_finding_for_invalid_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        blog_assembly_contract,
        "current_utc_date",
        lambda: date(2026, 8, 11),
    )
    paths = _fixture(tmp_path)
    _add_item_list_frontmatter(paths["article"])
    _refresh_normal_stage_receipts(paths)
    bom = _build(tmp_path, paths)
    raw = paths["article"].read_text(encoding="utf-8")
    paths["article"].write_text(
        raw.replace("  - Tool 14\n", "", 1),
        encoding="utf-8",
    )

    findings = check_bom(
        bom,
        article_path=paths["article"],
        validation_sidecar_path=paths["sidecar"],
        workspace_root=tmp_path,
        expected_lifecycle_state="provisional",
    )

    assert "bom_item_list_schema_invalid" in {
        finding["rule_id"] for finding in findings
    }


def test_bom_policy_rejects_a_blank_item_even_when_the_remaining_count_matches(
    tmp_path: Path,
) -> None:
    article_path = tmp_path / "item-list.md"
    entries = "".join(f"  - Tool {index}\n" for index in range(1, 14))
    article_path.write_text(
        "---\n"
        "schema_notes:\n"
        + "".join(f"  - {note}\n" for note in BASE_SCHEMA_NOTES)
        + "  - ItemList for the 13 compared tools, with exactly 13 ListItem entries\n"
        "item_list_entries:\n"
        + entries
        + "  -\n"
        "---\n"
        "# ItemList article\n",
        encoding="utf-8",
    )

    article = read_publishable_markdown(article_path)

    with pytest.raises(
        ValueError,
        match="item_list_entries cannot contain empty values",
    ):
        _schema_policy(article)


def test_frontmatter_requires_item_list_entries_to_use_a_yaml_sequence() -> None:
    content = (
        "---\n"
        "item_list_entries: !!set\n"
        "  Tool 1:\n"
        "---\n"
        "# ItemList article\n"
    )

    with pytest.raises(
        FrontmatterError,
        match="item_list_entries must be a YAML list",
    ):
        split_frontmatter(content)
