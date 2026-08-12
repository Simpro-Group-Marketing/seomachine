"""Fail-closed classification for person-like blog bylines."""

from __future__ import annotations

import re
import unicodedata
from typing import Any


_NON_PERSON_TOKENS = frozenset(
    {
        "admin",
        "administrator",
        "author",
        "authors",
        "bigchange",
        "by",
        "ceo",
        "cfo",
        "chief",
        "cmo",
        "communications",
        "company",
        "content",
        "contributor",
        "contributors",
        "corporate",
        "corporation",
        "department",
        "director",
        "editor",
        "editorial",
        "editors",
        "electrical",
        "field",
        "guest",
        "group",
        "lead",
        "marketing",
        "newsroom",
        "organisation",
        "organization",
        "plumbing",
        "product",
        "president",
        "simpro",
        "service",
        "services",
        "software",
        "staff",
        "team",
        "writer",
        "writers",
    }
)
_HONORIFICS = frozenset({"dr", "mr", "mrs", "ms", "prof", "professor"})
_SUFFIXES = frozenset({"ii", "iii", "iv", "jr", "sr"})
_NAME_PART_RE = re.compile(r"^[^\W\d_]+(?:[\-\u2019'][^\W\d_]+)*\.?$", re.UNICODE)


def is_named_person(value: Any) -> bool:
    """Return whether a byline is person-like rather than a team or role.

    This is deliberately a syntactic, fail-closed check. It does not claim to
    verify identity; it prevents organizational and generic role bylines from
    being promoted to ``Person as author``.
    """
    if not isinstance(value, str):
        return False
    candidate = unicodedata.normalize("NFC", " ".join(value.strip().split()))
    if not candidate or any(marker in candidate for marker in ("@", "/", "\\", "&")):
        return False
    tokens = candidate.split(" ")
    normalized = [token.strip(".,").casefold() for token in tokens]
    token_parts = [
        part
        for token in normalized
        for part in re.split(r"[-\u2019']", token)
        if part
    ]
    camel_parts = [
        part.casefold()
        for token in tokens
        for part in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])", token)
    ]
    if any(
        token in _NON_PERSON_TOKENS
        for token in (*token_parts, *camel_parts)
    ):
        return False
    if any(not _NAME_PART_RE.fullmatch(token.strip(",")) for token in tokens):
        return False
    core = [
        token
        for token in normalized
        if token not in _HONORIFICS and token not in _SUFFIXES
    ]
    return len(core) >= 2
