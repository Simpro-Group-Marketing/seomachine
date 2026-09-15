"""Construct a commercial-pillar model from already captured JSON bytes."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .commercial_pillar_index import (
    CommercialPillarIndex,
    CommercialPillarIndexError,
    _record_from_mapping,
)


def index_from_payload(
    value: Any,
    *,
    source_path: str | Path | None = None,
) -> CommercialPillarIndex:
    if not isinstance(value, Mapping):
        raise CommercialPillarIndexError("Commercial pillar index root must be an object.")
    raw_records = value.get("records")
    if not isinstance(raw_records, list):
        raise CommercialPillarIndexError("Commercial pillar index records must be an array.")
    records = []
    for row, item in enumerate(raw_records, start=1):
        if not isinstance(item, Mapping):
            raise CommercialPillarIndexError(f"Record {row} must be an object.")
        records.append(_record_from_mapping(item, row=row))
    return CommercialPillarIndex(
        schema_version=str(value.get("schema_version") or "").strip(),
        updated_at=str(value.get("updated_at") or "").strip(),
        records=tuple(records),
        source_path=Path(source_path).resolve() if source_path is not None else None,
    )


__all__ = ["index_from_payload"]
