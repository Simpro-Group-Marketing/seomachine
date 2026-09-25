from __future__ import annotations

from data_sources.modules.content_scoring.aeo_metadata_schema import _check_schema
from tests.test_item_list_schema_support import ITEM_LIST_ENTRIES, _metadata


def test_aeo_schema_accepts_immutable_item_list_entries() -> None:
    result = _check_schema(
        "",
        _metadata(entries=tuple(ITEM_LIST_ENTRIES)),
        visible_faq=False,
        finalized_bom=None,
    )

    assert result["passed"] is True
    assert result["details"]["item_list_entry_count"] == 14
    assert result["details"]["item_list_errors"] == []
