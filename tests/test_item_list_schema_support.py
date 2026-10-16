from __future__ import annotations

import pytest

from data_sources.modules.content_scoring.aeo_metadata_schema import _check_schema
from data_sources.modules.frontmatter import FrontmatterError, split_frontmatter


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


def test_aeo_schema_accepts_a_count_bound_item_list() -> None:
    result = _check_schema(
        "",
        _metadata(),
        visible_faq=False,
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
    )

    assert result["passed"] is False
    assert (
        "schema_notes must contain exactly one canonical ItemList schema note"
        in result["details"]["item_list_errors"]
    )


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
