"""Shared constants and helpers for the workplace risk assessment artifact builders."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


DATE = "2026-09-25"
SLUG = "workplace-risk-assessment"
ARTICLE = ROOT / "rewrites" / f"{SLUG}-rewrite-{DATE}.md"
PLAN = ROOT / "research" / f"editorial-plan-{SLUG}-{DATE}.json"
KEYWORD = ROOT / "research" / f"semrush-keyword-decision-{SLUG}-{DATE}.json"
BRIEF = ROOT / "research" / f"content-brief-{SLUG}-{DATE}.md"
SIDECAR = ROOT / "research" / f"validation-{SLUG}-{DATE}.md"
FULFILLMENT = ROOT / "research" / f"blog-plan-fulfillment-{SLUG}-{DATE}.json"
SERP_BLOCKER = ROOT / "research" / f"serp-evidence-blocker-{SLUG}-{DATE}.json"
SEMRUSH_UI = ROOT / "research" / f"semrush-ui-{SLUG}-{DATE}.txt"

TITLE = "Workplace Risk Assessment: How to Identify, Control and Record Risks in 5 Steps"
PRIMARY = "workplace risk assessment"
SECONDARY = [
    "workplace risk assessments",
    "what is a risk assessment",
    "risk assessment example",
    "risk assessment meaning",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def section(
    number: int,
    kind: str,
    heading: str,
    words: int,
    angle: str,
    hook: str,
    question: str,
    payoff: str,
    previous: str | None,
    following: str | None,
    *,
    gaps: list[str] | None = None,
    data: list[str] | None = None,
    links: list[str] | None = None,
    cta: str | None = None,
    next_action: str | None = None,
    mini_story: bool = False,
    featured_snippet: bool = False,
) -> dict[str, object]:
    return {
        "section_number": number,
        "type": kind,
        "heading": heading,
        "word_target": words,
        "strategic_angle": angle,
        "engagement_hook": hook,
        "reader_question": question,
        "section_payoff": payoff,
        "bridge_from_previous": previous,
        "bridge_to_next": following,
        "knowledge_gaps": gaps or [],
        "unique_data": data or [],
        "internal_links": links or [],
        "cta": cta,
        "next_action": next_action,
        "mini_story": mini_story,
        "featured_snippet": featured_snippet,
    }
