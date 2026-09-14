"""Strict list validators shared by PAA provenance modules."""

from __future__ import annotations


def _strict_text_list(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be a list")
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip() or item != item.strip():
            raise ValueError(f"{field} entries must be non-empty trimmed strings")
        key = item.casefold()
        if key in seen:
            raise ValueError(f"{field} cannot contain duplicates")
        seen.add(key)
        normalized.append(item)
    return tuple(normalized)


def _strict_question_list(value: object, *, field: str) -> tuple[str, ...]:
    from .matching import _validate_question_match_keys

    items = _strict_text_list(value, field=field)
    if any((not item.endswith("?") for item in items)):
        raise ValueError(f"{field} entries must be complete questions")
    _validate_question_match_keys(items, field=field)
    return items


__all__ = ["_strict_text_list", "_strict_question_list"]
