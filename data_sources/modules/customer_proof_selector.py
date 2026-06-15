"""
Customer Proof Selector

Ranks approved or candidate customer proof by topic fit and reuse history.
This module helps writers choose the most relevant proof instead of defaulting
to whichever case study is easiest to cite.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

try:
    from .proof_usage import count_customer_proof_usage, usage_matches_candidate
except ImportError:  # pragma: no cover - supports direct script execution.
    from proof_usage import count_customer_proof_usage, usage_matches_candidate


DEFAULT_INDEX_PATH = Path("context/customer-proof-index.json")
DEFAULT_LEDGER_PATH = Path("context/customer-proof-usage-ledger.json")

FindingDict = Dict[str, Any]
SLATE_ROLES = {"experience_story", "metric", "quote", "theme"}

SOURCE_TYPE_WEIGHT = {
    "quote_matrix": 18,
    "reference": 17,
    "customer_story": 16,
    "review_site": 12,
    "case_study": 10,
}

SOURCE_INTENT_BONUS = 18

SOURCE_INTENT_PATTERNS = {
    "review_site": (
        "review",
        "reviews",
        "reviewer",
        "review story",
        "review site",
        "g2",
        "capterra",
        "google review",
        "software advice",
        "softwareadvice",
    ),
    "quote_matrix": ("quote matrix",),
    "reference": ("reference", "references"),
    "customer_story": ("customer story", "customer stories"),
    "case_study": ("case study", "case studies"),
}

APPROVAL_WEIGHT = {
    "approved": 24,
    "ready": 18,
    "candidate": 8,
    "blocked": -8,
    "rejected": -20,
}

STOPWORDS = {
    "about",
    "after",
    "and",
    "are",
    "best",
    "business",
    "businesses",
    "for",
    "from",
    "guide",
    "into",
    "job",
    "jobs",
    "software",
    "that",
    "the",
    "this",
    "with",
    "your",
}


def select_customer_proofs(
    topic: str,
    *,
    index_path: str | Path = DEFAULT_INDEX_PATH,
    ledger_path: str | Path = DEFAULT_LEDGER_PATH,
    article_slug: str = "",
    title: str = "",
    objective: str = "",
    require_eeat_story: bool = False,
    proof_role: str = "any",
    limit: int = 8,
    reference_date: Optional[date] = None,
) -> List[FindingDict]:
    """Return ranked customer proof candidates for a topic."""
    reference = reference_date or date.today()
    index = _load_json(index_path, default={"proof": []})
    ledger = _load_json(ledger_path, default={"uses": []})
    search_text = " ".join(part for part in (topic, title, objective) if part)
    topic_tokens = _tokens(search_text)

    scored = []
    for candidate in index.get("proof", []):
        if not isinstance(candidate, dict):
            continue
        if require_eeat_story and not _is_review_story_eligible(candidate):
            continue
        if not _matches_proof_role(candidate, proof_role):
            continue
        result = dict(candidate)
        result.update(
            count_customer_proof_usage(
                ledger,
                proof_id=str(candidate.get("proof_id", "")),
                source_url=str(candidate.get("public_url", "")),
                customer=str(candidate.get("customer", "")),
                reference_date=reference,
            )
        )
        result["relevance_score"] = _relevance_score(topic_tokens, candidate)
        result["source_intent_score"] = _source_intent_score(search_text, candidate)
        result["proof_role"] = proof_role
        result["review_story_eligible"] = _is_review_story_eligible(candidate)
        result["score"] = _score_candidate(result)
        result["overused"] = bool(result.get("overused", False))
        result["selection_reason"] = _selection_reason(result)
        scored.append(result)

    if article_slug:
        scored = [
            candidate
            for candidate in scored
            if not _used_in_article(candidate, ledger.get("uses", []), article_slug)
        ] or scored

    scored.sort(
        key=lambda item: (
            item.get("score", 0),
            item.get("relevance_score", 0),
            -item.get("recent_uses_90d", 0),
            str(item.get("proof_id", "")),
        ),
        reverse=True,
    )
    return scored[: max(limit, 0)]


def build_customer_proof_slate(
    topic: str,
    *,
    index_path: str | Path = DEFAULT_INDEX_PATH,
    ledger_path: str | Path = DEFAULT_LEDGER_PATH,
    article_slug: str = "",
    title: str = "",
    objective: str = "",
    require_eeat_story: bool = False,
    roles: Sequence[str] = ("metric", "quote", "theme"),
    limit: int = 8,
    selected_overrides: Optional[Dict[str, str]] = None,
    rejected_overrides: Optional[Dict[str, Dict[str, str]]] = None,
    reference_date: Optional[date] = None,
) -> str:
    """Return a sidecar-ready Customer Proof Slate block."""
    selected = selected_overrides or {}
    rejected = rejected_overrides or {}
    normalized_roles = _parse_roles(",".join(roles) if not isinstance(roles, str) else roles)
    command = _slate_selector_command(
        topic,
        title=title,
        objective=objective,
        require_eeat_story=require_eeat_story,
        roles=normalized_roles,
        limit=limit,
    )
    lines = [
        "Customer Proof Slate",
        f"- Selector command: {command}",
    ]
    for role in normalized_roles:
        results = select_customer_proofs(
            topic,
            index_path=index_path,
            ledger_path=ledger_path,
            article_slug=article_slug,
            title=title,
            objective=objective,
            require_eeat_story=require_eeat_story and role == "experience_story",
            proof_role=role,
            limit=limit,
            reference_date=reference_date,
        )
        top_candidates = [str(result.get("proof_id", "")) for result in results if result.get("proof_id")]
        selected_id = selected.get(role) or (top_candidates[0] if top_candidates else "none")
        rejected_text = _format_rejected_candidates(rejected.get(role, {}))
        lines.append(
            "- Role: "
            f"{role} | Top candidates: [{', '.join(top_candidates) if top_candidates else 'none'}] "
            f"| Selected: [{selected_id}] | Rejected stronger candidates: [{rejected_text}]"
        )
    return "\n".join(lines)


def _parse_roles(raw_roles: str) -> List[str]:
    roles = [role.strip().lower() for role in raw_roles.split(",") if role.strip()]
    if not roles:
        roles = ["metric", "quote", "theme"]
    invalid = [role for role in roles if role not in SLATE_ROLES]
    if invalid:
        raise ValueError(f"Unsupported slate role: {', '.join(invalid)}")
    return roles


def _parse_selected_overrides(values: Sequence[str]) -> Dict[str, str]:
    overrides: Dict[str, str] = {}
    for value in values:
        role, proof_id = _split_role_assignment(value)
        overrides[role] = proof_id
    return overrides


def _parse_rejected_overrides(values: Sequence[str]) -> Dict[str, Dict[str, str]]:
    overrides: Dict[str, Dict[str, str]] = {}
    for value in values:
        role, rejected = _split_role_assignment(value)
        proof_id, separator, reason = rejected.partition(":")
        if not separator or not proof_id.strip() or not reason.strip():
            raise ValueError("--reject values must use role=proof_id:reason")
        overrides.setdefault(role, {})[proof_id.strip()] = reason.strip()
    return overrides


def _split_role_assignment(value: str) -> tuple[str, str]:
    role, separator, assigned = value.partition("=")
    role = role.strip().lower()
    assigned = assigned.strip()
    if not separator or role not in SLATE_ROLES or not assigned:
        raise ValueError(f"Expected role=proof_id for override, got: {value}")
    return role, assigned


def _format_rejected_candidates(rejected: Dict[str, str]) -> str:
    if not rejected:
        return "none"
    return ", ".join(f"{proof_id}: {reason}" for proof_id, reason in rejected.items())


def _slate_selector_command(
    topic: str,
    *,
    title: str,
    objective: str,
    require_eeat_story: bool,
    roles: Sequence[str],
    limit: int,
) -> str:
    parts = [
        "python",
        "data_sources/modules/customer_proof_selector.py",
        _quote_command_value(topic),
    ]
    if title:
        parts.extend(["--title", _quote_command_value(title)])
    if objective:
        parts.extend(["--objective", _quote_command_value(objective)])
    if require_eeat_story:
        parts.append("--require-eeat-story")
    parts.extend(["--slate", "--roles", ",".join(roles), "--limit", str(limit)])
    return " ".join(parts)


def _quote_command_value(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _load_json(path: str | Path, default: FindingDict) -> FindingDict:
    candidate = Path(path)
    if not candidate.exists():
        return dict(default)
    return json.loads(candidate.read_text(encoding="utf-8"))


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
    if "quoting" in topic_tokens and "invoicing" in topic_tokens and {"quoting", "invoicing"}.issubset(candidate_tokens):
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
    score -= int(candidate.get("recent_uses_90d", 0)) * 9
    score -= max(int(candidate.get("total_uses", 0)) - int(candidate.get("recent_uses_90d", 0)), 0) * 2
    return score


def _used_in_article(candidate: FindingDict, uses: Iterable[FindingDict], article_slug: str) -> bool:
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


def _matches_proof_role(candidate: FindingDict, proof_role: str) -> bool:
    role = str(proof_role or "any").strip().lower()
    if role == "any":
        return True
    if role == "experience_story":
        source_type = str(candidate.get("source_type", "")).strip().lower()
        if _is_review_story_eligible(candidate):
            return True
        return (
            source_type in {"case_study", "customer_story", "reference"}
            and bool(candidate.get("public_copy_allowed", False))
        )
    if role == "metric":
        return bool(candidate.get("approved_metrics") or [])
    if role == "quote":
        for row in candidate.get("approved_quotes", []) or []:
            if isinstance(row, dict) and str(row.get("status", "")).strip().lower() == "approved":
                return True
            if isinstance(row, str) and "status: approved" in row.lower():
                return True
        return False
    if role == "theme":
        return bool(candidate.get("themes") or candidate.get("evidence") or candidate.get("workflow_fit"))
    return True


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
    public_url = str(story.get("public_url") or candidate.get("public_url") or "").strip()
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


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Rank customer proof candidates for a topic.")
    parser.add_argument("topic", help="Topic or keyword to rank proof against.")
    parser.add_argument("--index", default=str(DEFAULT_INDEX_PATH), help="Customer proof index JSON path.")
    parser.add_argument("--ledger", default=str(DEFAULT_LEDGER_PATH), help="Customer proof usage ledger JSON path.")
    parser.add_argument("--article-slug", default="", help="Optional current article slug to avoid same-article repeats.")
    parser.add_argument("--title", default="", help="Optional article title for proof fit scoring.")
    parser.add_argument("--objective", default="", help="Optional content objective for proof fit scoring.")
    parser.add_argument(
        "--require-eeat-story",
        action="store_true",
        help="Only return review-story rows with a real identity and public review URL.",
    )
    parser.add_argument(
        "--proof-role",
        choices=["experience_story", "metric", "quote", "theme", "any"],
        default="any",
        help="Desired proof role for this selection pass.",
    )
    parser.add_argument("--limit", type=int, default=8, help="Maximum number of candidates to return.")
    parser.add_argument(
        "--slate",
        action="store_true",
        help="Print a sidecar-ready Customer Proof Slate block instead of JSON.",
    )
    parser.add_argument(
        "--roles",
        default="metric,quote,theme",
        help="Comma-separated proof roles to include when --slate is used.",
    )
    parser.add_argument(
        "--selected",
        action="append",
        default=[],
        help="Override selected proof for a slate role, e.g. metric=proof_id. Repeatable.",
    )
    parser.add_argument(
        "--reject",
        action="append",
        default=[],
        help="Document a rejected stronger candidate, e.g. metric=proof_id:section-specific reason. Repeatable.",
    )
    args = parser.parse_args(argv)

    if args.slate:
        try:
            roles = _parse_roles(args.roles)
            selected_overrides = _parse_selected_overrides(args.selected)
            rejected_overrides = _parse_rejected_overrides(args.reject)
        except ValueError as exc:
            parser.error(str(exc))
        print(
            build_customer_proof_slate(
                args.topic,
                index_path=args.index,
                ledger_path=args.ledger,
                article_slug=args.article_slug,
                title=args.title,
                objective=args.objective,
                require_eeat_story=args.require_eeat_story,
                roles=roles,
                limit=args.limit,
                selected_overrides=selected_overrides,
                rejected_overrides=rejected_overrides,
            )
        )
        return 0

    results = select_customer_proofs(
        args.topic,
        index_path=args.index,
        ledger_path=args.ledger,
        article_slug=args.article_slug,
        title=args.title,
        objective=args.objective,
        require_eeat_story=args.require_eeat_story,
        proof_role=args.proof_role,
        limit=args.limit,
    )
    print(json.dumps({"topic": args.topic, "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
