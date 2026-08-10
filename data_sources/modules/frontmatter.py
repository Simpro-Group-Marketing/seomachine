"""Strict YAML frontmatter parsing shared by guards and publishers."""

from __future__ import annotations

import math
import re
from datetime import date, datetime
from typing import Any, Mapping

import yaml
from yaml.nodes import MappingNode, ScalarNode


FRONTMATTER_RE = re.compile(
    r"\A---[ \t]*\r?\n(?P<block>.*?)\r?\n---[ \t]*(?:\r?\n|\Z)",
    re.DOTALL,
)
OPENING_DELIMITER_RE = re.compile(r"\A---[ \t]*(?:\r?\n|\Z)")
ARTIFACT_KIND_ALIASES = {
    "article": "blog",
    "post": "blog",
    "posts": "blog",
    "blog": "blog",
    "page": "landing_page",
    "pages": "landing_page",
    "landing": "landing_page",
    "landingpage": "landing_page",
    "landing_page": "landing_page",
}
IDENTITY_FIELDS = frozenset({"brand", "artifact_type", "artifact_kind"})


class FrontmatterError(ValueError):
    """A Markdown artifact contains unsafe or unsupported frontmatter."""


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """SafeLoader variant rejecting raw and normalized duplicate mapping keys."""


def normalize_key(value: str) -> str:
    """Normalize supported metadata key spelling to the repository contract."""
    return re.sub(
        r"_+",
        "_",
        value.strip().lower().replace("-", "_").replace(" ", "_"),
    )


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader,
    node: MappingNode,
    deep: bool = False,
) -> dict[str, Any]:
    if not isinstance(node, MappingNode):
        raise FrontmatterError("YAML frontmatter must be a mapping.")
    mapping: dict[str, Any] = {}
    for key_node, value_node in node.value:
        if not isinstance(key_node, ScalarNode):
            raise FrontmatterError("YAML frontmatter keys must be scalar strings.")
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise FrontmatterError("YAML frontmatter keys must be strings.")
        normalized_key = normalize_key(key)
        if not normalized_key:
            raise FrontmatterError("YAML frontmatter keys cannot be empty.")
        if normalized_key in mapping:
            raise FrontmatterError(
                f"Duplicate YAML frontmatter key after normalization: {normalized_key}."
            )
        mapping[normalized_key] = loader.construct_object(value_node, deep=True)
    return mapping


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def split_frontmatter(raw: str) -> tuple[dict[str, Any], str, int]:
    """Return normalized metadata, body, and the body's one-based start line.

    A document without a leading frontmatter delimiter remains valid legacy
    Markdown. A leading delimiter must have a matching closing delimiter and
    its payload must satisfy the strict metadata contract.
    """
    match = FRONTMATTER_RE.match(raw)
    if not match:
        if OPENING_DELIMITER_RE.match(raw):
            raise FrontmatterError("YAML frontmatter is missing its closing delimiter.")
        return {}, raw, 1

    block = match.group("block")
    try:
        loaded = yaml.load(block, Loader=_UniqueKeySafeLoader)
    except FrontmatterError:
        raise
    except yaml.YAMLError as exc:
        problem = getattr(exc, "problem", None) or str(exc).splitlines()[0]
        raise FrontmatterError(f"Malformed YAML frontmatter: {problem}.") from exc

    if loaded is None:
        metadata: dict[str, Any] = {}
    elif not isinstance(loaded, Mapping):
        raise FrontmatterError("YAML frontmatter must be a mapping.")
    else:
        metadata = {
            key: _normalize_value(key, value)
            for key, value in loaded.items()
        }
    _validate_identity_fields(metadata)
    body_start_line = raw[: match.end()].count("\n") + 1
    return metadata, raw[match.end() :], body_start_line


def _normalize_value(key: str, value: Any) -> str | list[str]:
    if isinstance(value, Mapping):
        raise FrontmatterError(
            f"YAML frontmatter field {key} uses an unsupported object value."
        )
    if isinstance(value, (list, tuple, set)):
        items: list[str] = []
        for item in value:
            if isinstance(item, (Mapping, list, tuple, set)):
                raise FrontmatterError(
                    f"YAML frontmatter field {key} uses an unsupported nested value."
                )
            normalized = _normalize_scalar(key, item)
            if normalized:
                items.append(normalized)
        return items
    return _normalize_scalar(key, value)


def _normalize_scalar(key: str, value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise FrontmatterError(
                f"YAML frontmatter field {key} must contain a finite number."
            )
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise FrontmatterError(
        f"YAML frontmatter field {key} uses unsupported scalar type "
        f"{type(value).__name__}."
    )


def _validate_identity_fields(metadata: Mapping[str, Any]) -> None:
    for key in IDENTITY_FIELDS:
        value = metadata.get(key)
        if isinstance(value, list):
            raise FrontmatterError(
                f"YAML frontmatter identity field {key} must be a scalar."
            )

    declared_kinds: list[str] = []
    for key in ("artifact_type", "artifact_kind"):
        raw_value = metadata.get(key)
        if not isinstance(raw_value, str) or not raw_value:
            continue
        normalized = raw_value.casefold().replace("-", "_").replace(" ", "_")
        kind = ARTIFACT_KIND_ALIASES.get(normalized)
        if kind is not None:
            declared_kinds.append(kind)
    if len(set(declared_kinds)) > 1:
        raise FrontmatterError(
            "YAML frontmatter artifact_type and artifact_kind conflict."
        )