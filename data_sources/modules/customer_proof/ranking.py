"""Customer-proof eligibility, role matching, and deterministic ranking."""

from __future__ import annotations

import re
from typing import Any, Iterable, List, Sequence

from ..proof_usage import usage_matches_candidate
from .contracts import (
    APPROVAL_WEIGHT,
    FindingDict,
    HISTORICAL_USE_SCORE_PENALTY,
    RECENT_USE_SCORE_PENALTY,
    SOURCE_INTENT_BONUS,
    SOURCE_INTENT_PATTERNS,
    SOURCE_TYPE_WEIGHT,
    STOPWORDS,
)


def _relevance_score(topic_tokens: set[str], candidate: FindingDict) -> int:
    if not topic_tokens:
        return 0
    candidate_tokens = _tokens(_candidate_text(candidate))
    overlap = topic_tokens.intersection(candidate_tokens)
    phrase_bonus = 0
    text = _normalize_space(_candidate_text(candidate).lower())
    topic = _normalize_space(" ".join(sorted(topic_tokens)))
    if "quote to cash" in text or "quote-to-cash" in text:
        phrase_bonus += 8
    if "small trade" in text or "small trades" in text:
        phrase_bonus += 6
    if (
        "quoting" in topic_tokens
        and "invoicing" in topic_tokens
        and {"quoting", "invoicing"}.issubset(candidate_tokens)
    ):
        phrase_bonus += 10
    if topic and topic in text:
        phrase_bonus += 5
    return len(overlap) * 10 + phrase_bonus


def _score_candidate(candidate: FindingDict) -> int:
    approval = str(candidate.get("approval_status", "")).strip().lower()
    source_type = str(candidate.get("source_type", "")).strip().lower()
    public_copy_allowed = bool(candidate.get("public_copy_allowed", False))
    score = int(candidate.get("relevance_score", 0))
    score += APPROVAL_WEIGHT.get(approval, 0)
    score += SOURCE_TYPE_WEIGHT.get(source_type, 0)
    if public_copy_allowed:
        score += 8
    score += int(candidate.get("source_intent_score", 0))
    score -= int(candidate.get("recent_uses_90d", 0)) * RECENT_USE_SCORE_PENALTY
    score -= (
        max(
            int(candidate.get("total_uses", 0))
            - int(candidate.get("recent_uses_90d", 0)),
            0,
        )
        * HISTORICAL_USE_SCORE_PENALTY
    )
    return score


def _used_in_article(
    candidate: FindingDict, uses: Iterable[FindingDict], article_slug: str
) -> bool:
    for usage in uses:
        if str(usage.get("article_slug", "")) != article_slug:
            continue
        if usage_matches_candidate(candidate, usage):
            return True
    return False


def _selection_reason(candidate: FindingDict) -> str:
    parts = [
        f"relevance={candidate.get('relevance_score', 0)}",
        f"source_intent={candidate.get('source_intent_score', 0)}",
        f"source_type={candidate.get('source_type', '')}",
        f"status={candidate.get('approval_status', '')}",
        f"recent_uses_90d={candidate.get('recent_uses_90d', 0)}",
    ]
    if candidate.get("review_story_eligible"):
        parts.append("review_story_eligible=true")
    if candidate.get("overused"):
        parts.append("overused=true")
    return "; ".join(parts)


def _candidate_text(candidate: FindingDict) -> str:
    values: List[str] = []
    for key in (
        "proof_id",
        "customer",
        "source_type",
        "industry",
        "region",
        "company_size",
        "workflow_fit",
        "themes",
        "evidence",
        "restrictions",
    ):
        values.extend(_flatten(candidate.get(key)))
    for row_key in ("approved_quotes", "approved_metrics"):
        for row in candidate.get(row_key, []) or []:
            values.extend(_flatten(row))
    values.extend(_flatten(candidate.get("review_story")))
    return " ".join(values)


def _matches_proof_role(
    candidate: FindingDict,
    proof_role: str,
    *,
    approved_claim: Any | None = None,
) -> bool:
    role = str(proof_role or "any").strip().lower()
    if role == "any":
        return True
    approved_mode = str(getattr(approved_claim, "use_mode", "") or "").strip()
    if role == "experience_story":
        source_type = str(candidate.get("source_type", "")).strip().lower()
        if _is_review_story_eligible(candidate):
            return True
        return source_type in {"case_study", "customer_story", "reference"} and bool(
            candidate.get("public_copy_allowed", False)
        )
    if role == "metric":
        if approved_mode == "public_metric":
            return True
        return bool(candidate.get("approved_metrics") or [])
    if role == "quote":
        if approved_mode == "exact_quote":
            return True
        return any(
            _approved_quote_row(row)
            for row in candidate.get("approved_quotes", []) or []
        )
    if role == "theme":
        return bool(
            candidate.get("themes")
            or candidate.get("evidence")
            or candidate.get("workflow_fit")
        )
    return True


def _approved_quote_row(row: object) -> bool:
    if isinstance(row, dict):
        return str(row.get("status", "")).strip().lower() == "approved"
    return isinstance(row, str) and "status: approved" in row.lower()


def _use_modes_for_role(proof_role: str) -> set[str]:
    role = str(proof_role or "any").strip().lower()
    if role == "metric":
        return {"public_metric"}
    if role == "quote":
        return {"exact_quote"}
    if role in {"theme", "experience_story"}:
        return {"public_paraphrase"}
    return {"public_metric", "exact_quote", "public_paraphrase"}


def _is_review_story_eligible(candidate: FindingDict) -> bool:
    story = candidate.get("review_story") or {}
    if not isinstance(story, dict):
        return False
    if story.get("story_allowed") is not True:
        return False
    identity_type = str(story.get("identity_type", "")).strip().lower()
    if identity_type not in {"person", "business", "person_and_business"}:
        return False
    identity = (
        str(story.get("identity_display", "")).strip()
        or str(story.get("person_name", "")).strip()
        or str(story.get("business_name", "")).strip()
    )
    if not identity:
        return False
    public_url = str(
        story.get("public_url") or candidate.get("public_url") or ""
    ).strip()
    return public_url.startswith(("http://", "https://"))


def _source_intent_score(topic: str, candidate: FindingDict) -> int:
    source_type = str(candidate.get("source_type", "")).strip().lower()
    patterns = SOURCE_INTENT_PATTERNS.get(source_type, ())
    if not patterns:
        return 0
    normalized_topic = _normalize_space(_normalize_text(topic))
    raw_topic = topic.lower()
    for pattern in patterns:
        normalized_pattern = _normalize_space(_normalize_text(pattern))
        if pattern in raw_topic or normalized_pattern in normalized_topic:
            return SOURCE_INTENT_BONUS
    return 0


def _flatten(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [str(item) for pair in value.items() for item in pair]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        flattened: List[str] = []
        for item in value:
            flattened.extend(_flatten(item))
        return flattened
    return [str(value)]


def _tokens(text: str) -> set[str]:
    normalized = _normalize_text(text.replace("-", " "))
    tokens = set()
    for token in re.findall(r"[a-z0-9]+", normalized):
        if len(token) < 3 or token in STOPWORDS:
            continue
        if token == "quotes":
            token = "quoting"
        if token in {"invoice", "invoices"}:
            token = "invoicing"
        tokens.add(token)
    return tokens


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


__all__ = [
    '_relevance_score',
    '_score_candidate',
    '_used_in_article',
    '_selection_reason',
    '_candidate_text',
    '_matches_proof_role',
    '_approved_quote_row',
    '_use_modes_for_role',
    '_is_review_story_eligible',
    '_source_intent_score',
    '_flatten',
    '_tokens',
    '_normalize_text',
    '_normalize_space'
]
