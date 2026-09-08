"""Validate optional ItemList declarations in blog YAML frontmatter."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


ITEM_LIST_NOTE_RE = re.compile(
    r"ItemList for the (?P<compared_count>[1-9]\d*) compared tools, "
    r"with exactly (?P<entry_count>[1-9]\d*) ListItem entries"
)


@dataclass(frozen=True)
class ItemListSchemaInspection:
    """Normalized result for an optional ItemList frontmatter declaration."""

    active: bool
    note: str
    declared_count: int | None
    entries: tuple[str, ...]
    errors: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors


def inspect_item_list_schema(
    schema_notes: Sequence[str],
    metadata: Mapping[str, Any],
) -> ItemListSchemaInspection:
    """Validate a canonical count-bound ItemList note and its entry names."""

    item_list_notes = [
        str(note).strip()
        for note in schema_notes
        if str(note).strip().startswith("ItemList")
    ]
    canonical: list[tuple[str, int]] = []
    for note in item_list_notes:
        match = ITEM_LIST_NOTE_RE.fullmatch(note)
        if match is None:
            continue
        compared_count = int(match.group("compared_count"))
        entry_count = int(match.group("entry_count"))
        if compared_count == entry_count:
            canonical.append((note, compared_count))

    entries_present = "item_list_entries" in metadata
    active = bool(item_list_notes) or entries_present
    if not active:
        return ItemListSchemaInspection(False, "", None, (), ())

    errors: list[str] = []
    if len(canonical) != 1:
        if entries_present and not item_list_notes:
            errors.append(
                "item_list_entries requires exactly one canonical ItemList schema note"
            )
        else:
            errors.append(
                "schema_notes must contain exactly one canonical ItemList schema note"
            )
    if len(canonical) != len(item_list_notes):
        errors.append("schema_notes contains a noncanonical ItemList schema note")

    raw_entries = metadata.get("item_list_entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        errors.append("item_list_entries must be a nonempty YAML list")
        entries: tuple[str, ...] = ()
    else:
        entries = tuple(str(value).strip() for value in raw_entries)
        if any(not value for value in entries):
            errors.append("item_list_entries cannot contain empty values")
        normalized_entries = [value.casefold() for value in entries if value]
        if len(normalized_entries) != len(set(normalized_entries)):
            errors.append("item_list_entries must contain unique values")

    note = canonical[0][0] if len(canonical) == 1 else ""
    declared_count = canonical[0][1] if len(canonical) == 1 else None
    if declared_count is not None and entries and len(entries) != declared_count:
        errors.append(
            f"item_list_entries count {len(entries)} does not match the "
            f"declared count {declared_count}"
        )

    return ItemListSchemaInspection(
        active=active,
        note=note,
        declared_count=declared_count,
        entries=entries,
        errors=tuple(dict.fromkeys(errors)),
    )
