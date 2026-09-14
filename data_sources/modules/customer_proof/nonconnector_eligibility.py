"""Nonconnector eligibility, role matching, and ranking."""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Mapping
from urllib.parse import urlsplit

from .nonconnector_contracts import (
    STOPWORDS,
    SUPPORTED_BRAND_HOSTS,
    SUPPORTED_SOURCE_TYPES,
    NonVaultProofDataError,
)


def _eligible_source(source: Mapping[str, Any], *, expected_host: str) -> bool:
    if str(source.get("approval_status") or "").casefold() != "approved":
        return False
    if source.get("public_copy_allowed") is not True:
        return False
    if str(source.get("source_type") or "").casefold() not in SUPPORTED_SOURCE_TYPES:
        return False
    proof_id = str(source.get("proof_id") or "").strip()
    if not proof_id:
        return False
    hostname = (urlsplit(str(source.get("public_url") or "")).hostname or "").casefold()
    return hostname in {expected_host, f"www.{expected_host}"}


def _supports_role(
    source: Mapping[str, Any],
    role: str,
    *,
    require_eeat_story: bool,
) -> bool:
    if role == "metric":
        return bool(source.get("approved_metrics"))
    if role == "quote":
        return bool(source.get("approved_quotes"))
    if role == "theme":
        return True
    story = source.get("review_story")
    if not isinstance(story, Mapping) or story.get("story_allowed") is not True:
        return not require_eeat_story
    identity = str(
        story.get("identity_display")
        or story.get("business_name")
        or story.get("person_name")
        or source.get("customer")
        or ""
    ).strip()
    public_url = str(
        story.get("public_url") or source.get("public_url") or ""
    ).strip()
    return bool(identity and public_url.startswith(("http://", "https://")))


def _experience_binding(source: Mapping[str, Any]) -> dict[str, str]:
    story = source.get("review_story")
    if not isinstance(story, Mapping):
        story = {}
    return {
        "proof_id": str(source.get("proof_id") or ""),
        "identity": str(
            story.get("identity_display")
            or story.get("business_name")
            or story.get("person_name")
            or source.get("customer")
            or ""
        ),
        "public_url": str(
            story.get("public_url") or source.get("public_url") or ""
        ),
        "story": str(story.get("workflow_story") or source.get("evidence") or ""),
    }


def _relevance_score(query_tokens: set[str], source: Mapping[str, Any]) -> int:
    source_text = " ".join(
        str(value)
        for key in (
            "proof_id",
            "customer",
            "industry",
            "workflow_fit",
            "themes",
            "evidence",
        )
        for value in _values(source.get(key))
    )
    return len(query_tokens.intersection(_tokens(source_text))) * 10


def _source_weight(source_type: str) -> int:
    return {"customer_story": 16, "reference": 14, "case_study": 12}.get(
        source_type.casefold(), 0
    )


def _recent_uses(
    ledger: Mapping[str, Any], *, proof_id: str, reference_date: date
) -> int:
    count = 0
    for row in ledger.get("uses", []):
        if (
            not isinstance(row, Mapping)
            or str(row.get("proof_id") or "") != proof_id
        ):
            continue
        raw_date = str(
            row.get("date_used") or row.get("date") or row.get("used_on") or ""
        )
        try:
            used_on = date.fromisoformat(raw_date)
        except ValueError:
            continue
        if 0 <= (reference_date - used_on).days <= 90:
            count += 1
    return count


def _brand_key(brand: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "", brand.casefold())
    if key not in SUPPORTED_BRAND_HOSTS:
        raise NonVaultProofDataError(f"unsupported nonconnector brand: {brand}")
    return key


def _canonical_brand(brand: str) -> str:
    return {
        "aroflo": "AroFlo",
        "bigchange": "BigChange",
        "clockshark": "ClockShark",
    }[_brand_key(brand)]


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if token not in STOPWORDS
    }


def _values(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


__all__ = [
    '_eligible_source',
    '_supports_role',
    '_experience_binding',
    '_relevance_score',
    '_source_weight',
    '_recent_uses',
    '_brand_key',
    '_canonical_brand',
    '_tokens',
    '_values'
]
