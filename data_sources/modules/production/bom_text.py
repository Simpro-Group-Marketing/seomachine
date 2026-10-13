"""Free-text number gate: numbers in public text must come from verified facts or approved proof."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from data_sources.modules.production.numbers import extract_numbers


def _flatten(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return " ".join(_flatten(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return " ".join(_flatten(item) for item in value)
    return "" if value is None else json.dumps(value)


def supported_numbers(
    facts: Sequence[Mapping[str, Any]], proof: Sequence[Mapping[str, Any]], year: str
) -> frozenset[str]:
    """Numbers allowed in public text: fact quotes, approved proof, and the article year."""
    texts = [fact["quote"] for fact in facts]
    for item in proof:
        texts += [_flatten(item.get(key)) for key in ("text", "approved_quotes", "approved_metrics")]
    allowed: set[str] = set(extract_numbers(year))
    for text in texts:
        allowed |= extract_numbers(text)
    return frozenset(allowed)


def _public_fields(spec: Mapping[str, Any]) -> list[tuple[str, str]]:
    fields = [("title", spec["title"]), ("cta.text", spec["cta"]["text"])]
    fields += [(f"links[{i}] anchor", link["anchor"]) for i, link in enumerate(spec["links"])]
    fields += [(f"sections[{i}] heading", section["heading"]) for i, section in enumerate(spec["sections"])]
    return fields


def free_text_number_errors(
    spec: Mapping[str, Any], facts: Sequence[Mapping[str, Any]], proof: Sequence[Mapping[str, Any]], year: str
) -> list[str]:
    """Return one line per public field that carries a number no verified source supplies."""
    allowed = supported_numbers(facts, proof, year)
    errors = []
    for name, text in _public_fields(spec):
        unsupported = extract_numbers(text) - allowed
        if unsupported:
            errors.append(
                f"{name} carries numbers no verified fact or approved proof supports: "
                + ", ".join(sorted(unsupported))
            )
    return errors
