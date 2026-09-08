"""Parser and validation model for the production blog strategy contract."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Optional

try:
    from .guard_common import Finding, make_finding
except ImportError:  # pragma: no cover - direct script execution.
    from guard_common import Finding, make_finding


CONTRACT_VERSION = "blog-strategy-contract/v1"
SECTION_NAMES = (
    "Search Intent and Format Decision",
    "Commercial Pillar and Anchor Decision",
    "Lifecycle Refresh Record",
)
REQUIRED_FIELDS = {
    "Search Intent and Format Decision": (
        "contract version",
        "primary query or prompt",
        "searcher task",
        "intent class",
        "funnel stage",
        "serp evidence artifact",
        "dominant content type",
        "selected content type",
        "observed serp features",
        "related-query/paa artifact",
        "format decision",
        "exception reason",
        "status",
    ),
    "Commercial Pillar and Anchor Decision": (
        "contract version",
        "article title",
        "article primary keyword",
        "article intent",
        "destination id",
        "commercial pillar url",
        "planned anchor text",
        "planned h2 section",
        "existing overlapping urls checked",
        "pillar-versus-blog intent difference",
        "cannibalization decision",
        "incoming-link candidates",
        "status",
    ),
    "Lifecycle Refresh Record": (
        "contract version",
        "last-updated date",
        "volatility",
        "next review date",
        "review command",
        "gsc lane",
        "ga4 lane",
        "semrush lane",
        "ai-citation lane",
        "decision",
        "status",
    ),
}
ENUM_FIELDS = {
    ("Search Intent and Format Decision", "intent class"): {
        "informational",
        "commercial",
        "transactional",
        "navigational",
        "mixed",
    },
    ("Search Intent and Format Decision", "funnel stage"): {
        "tofu",
        "mofu",
        "bofu",
        "thought_leadership",
    },
    ("Search Intent and Format Decision", "format decision"): {
        "match_dominant",
        "documented_exception",
    },
    ("Search Intent and Format Decision", "status"): {"ready", "blocked"},
    ("Commercial Pillar and Anchor Decision", "article intent"): {
        "informational",
        "commercial",
        "transactional",
        "navigational",
        "mixed",
    },
    ("Commercial Pillar and Anchor Decision", "cannibalization decision"): {
        "create_new",
        "different_intent",
        "update_existing",
        "consolidate",
    },
    ("Commercial Pillar and Anchor Decision", "status"): {"aligned", "blocked"},
    ("Lifecycle Refresh Record", "volatility"): {"high", "standard"},
    ("Lifecycle Refresh Record", "decision"): {
        "retain",
        "refresh",
        "update",
        "consolidate",
    },
    ("Lifecycle Refresh Record", "status"): {"scheduled", "blocked"},
}
HEADING_RE = re.compile(r"^\s*#{1,6}\s+(?P<title>.*?)\s*$")
FIELD_RE = re.compile(r"^\s*[-*+]\s*(?P<key>[^:]+):\s*(?P<value>.*?)\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
PLACEHOLDER_RE = re.compile(
    r"(?:\b(?:tbd|todo|placeholder|fill[ -]?in|insert here|unknown)\b|\[(?:insert|add|describe)[^\]]*\])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SearchIntentDecision:
    contract_version: str
    primary_query_or_prompt: str
    searcher_task: str
    intent_class: str
    funnel_stage: str
    serp_evidence_artifact: str
    dominant_content_type: str
    selected_content_type: str
    observed_serp_features: str
    related_query_paa_artifact: str
    format_decision: str
    exception_reason: str
    status: str


@dataclass(frozen=True)
class CommercialPillarDecision:
    contract_version: str
    article_title: str
    article_primary_keyword: str
    article_intent: str
    destination_id: str
    commercial_pillar_url: str
    planned_anchor_text: str
    planned_h2_section: str
    existing_overlapping_urls_checked: str
    pillar_versus_blog_intent_difference: str
    cannibalization_decision: str
    incoming_link_candidates: str
    status: str


@dataclass(frozen=True)
class LifecycleRefreshRecord:
    contract_version: str
    last_updated_date: str
    volatility: str
    next_review_date: str
    review_command: str
    gsc_lane: str
    ga4_lane: str
    semrush_lane: str
    ai_citation_lane: str
    decision: str
    status: str


@dataclass(frozen=True)
class BlogStrategyContract:
    search_intent: SearchIntentDecision
    commercial_pillar: CommercialPillarDecision
    lifecycle: LifecycleRefreshRecord


def validate_contract(content: str) -> tuple[Optional[BlogStrategyContract], list[Finding]]:
    """Parse all required blocks, returning no model when any blocker exists."""
    sections, findings = _extract_sections(content)
    for section_name in SECTION_NAMES:
        blocks = sections.get(section_name, [])
        if not blocks:
            findings.append(
                _finding(
                    "blog_strategy_contract_section_missing",
                    1,
                    f"Missing required sidecar section: {section_name}.",
                )
            )
        elif len(blocks) > 1:
            for line, _ in blocks[1:]:
                findings.append(
                    _finding(
                        "blog_strategy_contract_section_duplicate",
                        line,
                        f"Duplicate sidecar section: {section_name}.",
                    )
                )

    if findings:
        return None, _sort_findings(findings)

    parsed: dict[str, dict[str, str]] = {}
    for section_name in SECTION_NAMES:
        line, fields = sections[section_name][0]
        parsed[section_name] = fields
        for field in REQUIRED_FIELDS[section_name]:
            value = fields.get(field, "").strip()
            if not value:
                findings.append(
                    _finding(
                        "blog_strategy_contract_field_missing",
                        line,
                        f"{section_name} is missing required field: {field}.",
                    )
                )
            elif PLACEHOLDER_RE.search(value):
                findings.append(
                    _finding(
                        "blog_strategy_contract_placeholder",
                        line,
                        f"{section_name} contains placeholder content in: {field}.",
                    )
                )

        version = fields.get("contract version", "")
        if version and version != CONTRACT_VERSION:
            findings.append(
                _finding(
                    "blog_strategy_contract_version_unsupported",
                    line,
                    f"Unsupported contract version in {section_name}: {version}.",
                )
            )

        for (enum_section, field), allowed in ENUM_FIELDS.items():
            if enum_section != section_name:
                continue
            value = fields.get(field, "").strip().casefold()
            if value and value not in allowed:
                findings.append(
                    _finding(
                        "blog_strategy_contract_enum_invalid",
                        line,
                        f"Unsupported {field} value in {section_name}: {fields.get(field)}.",
                    )
                )

    search = parsed["Search Intent and Format Decision"]
    if (
        search.get("format decision", "").casefold() == "documented_exception"
        and search.get("exception reason", "").strip().casefold() == "none"
    ):
        findings.append(
            _finding(
                "blog_strategy_contract_exception_reason_missing",
                sections["Search Intent and Format Decision"][0][0],
                "A documented format exception requires a substantive exception reason.",
            )
        )
    if search.get("format decision", "").casefold() == "match_dominant" and _normalize_value(
        search.get("dominant content type", "")
    ) != _normalize_value(search.get("selected content type", "")):
        findings.append(
            _finding(
                "blog_strategy_contract_format_mismatch",
                sections["Search Intent and Format Decision"][0][0],
                "Format decision match_dominant requires Selected content type to match Dominant content type.",
            )
        )

    if findings:
        return None, _sort_findings(findings)
    return _build_contract(parsed), []


def _extract_sections(
    content: str,
) -> tuple[dict[str, list[tuple[int, dict[str, str]]]], list[Finding]]:
    lines = _executable_lines(content)
    sections: dict[str, list[tuple[int, dict[str, str]]]] = {}
    findings: list[Finding] = []
    index = 0
    while index < len(lines):
        line_number, line = lines[index]
        canonical_title = _contract_section_title(line)
        if canonical_title is None:
            index += 1
            continue
        fields: dict[str, str] = {}
        field_lines: dict[str, int] = {}
        cursor = index + 1
        while cursor < len(lines):
            cursor_line_number, cursor_line = lines[cursor]
            if HEADING_RE.match(cursor_line) or _contract_section_title(cursor_line):
                break
            field_match = FIELD_RE.match(cursor_line)
            if field_match:
                key = _normalize_field(field_match.group("key"))
                value = field_match.group("value").strip()
                if key in fields:
                    findings.append(
                        _finding(
                            "blog_strategy_contract_field_duplicate",
                            cursor_line_number,
                            f"Duplicate field {key} in {canonical_title}; first declared on line {field_lines[key]}.",
                        )
                    )
                else:
                    fields[key] = value
                    field_lines[key] = cursor_line_number
            elif cursor_line.strip():
                break
            cursor += 1
        sections.setdefault(canonical_title, []).append((line_number, fields))
        index = cursor
    return sections, findings


def _contract_section_title(line: str) -> Optional[str]:
    stripped = line.strip()
    heading_match = HEADING_RE.match(stripped)
    title = (
        heading_match.group("title").strip().rstrip(":")
        if heading_match
        else stripped.rstrip(":")
    )
    return next(
        (name for name in SECTION_NAMES if name.casefold() == title.casefold()),
        None,
    )


def _executable_lines(content: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    in_fence = False
    in_comment = False
    for line_number, line in enumerate(content.splitlines(), start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        visible, in_comment = _strip_comments(line, in_comment=in_comment)
        if visible or not line.strip():
            lines.append((line_number, visible))
    return lines


def _strip_comments(line: str, *, in_comment: bool) -> tuple[str, bool]:
    output = line
    if in_comment:
        if "-->" not in output:
            return "", True
        output = output.split("-->", 1)[1]
        in_comment = False
    while "<!--" in output:
        before, after = output.split("<!--", 1)
        if "-->" not in after:
            return before, True
        output = before + after.split("-->", 1)[1]
    return output, in_comment


def _normalize_field(value: str) -> str:
    normalized = value.strip().replace("**", "").replace("__", "")
    normalized = normalized.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", normalized.casefold()).strip()


def _normalize_value(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _build_contract(sections: Mapping[str, Mapping[str, str]]) -> BlogStrategyContract:
    search = sections["Search Intent and Format Decision"]
    pillar = sections["Commercial Pillar and Anchor Decision"]
    lifecycle = sections["Lifecycle Refresh Record"]
    return BlogStrategyContract(
        search_intent=SearchIntentDecision(
            contract_version=search["contract version"],
            primary_query_or_prompt=search["primary query or prompt"],
            searcher_task=search["searcher task"],
            intent_class=search["intent class"].casefold(),
            funnel_stage=search["funnel stage"].casefold(),
            serp_evidence_artifact=search["serp evidence artifact"],
            dominant_content_type=search["dominant content type"],
            selected_content_type=search["selected content type"],
            observed_serp_features=search["observed serp features"],
            related_query_paa_artifact=search["related-query/paa artifact"],
            format_decision=search["format decision"].casefold(),
            exception_reason=search["exception reason"],
            status=search["status"].casefold(),
        ),
        commercial_pillar=CommercialPillarDecision(
            contract_version=pillar["contract version"],
            article_title=pillar["article title"],
            article_primary_keyword=pillar["article primary keyword"],
            article_intent=pillar["article intent"].casefold(),
            destination_id=pillar["destination id"],
            commercial_pillar_url=pillar["commercial pillar url"],
            planned_anchor_text=pillar["planned anchor text"],
            planned_h2_section=pillar["planned h2 section"],
            existing_overlapping_urls_checked=pillar["existing overlapping urls checked"],
            pillar_versus_blog_intent_difference=pillar["pillar-versus-blog intent difference"],
            cannibalization_decision=pillar["cannibalization decision"].casefold(),
            incoming_link_candidates=pillar["incoming-link candidates"],
            status=pillar["status"].casefold(),
        ),
        lifecycle=LifecycleRefreshRecord(
            contract_version=lifecycle["contract version"],
            last_updated_date=lifecycle["last-updated date"],
            volatility=lifecycle["volatility"].casefold(),
            next_review_date=lifecycle["next review date"],
            review_command=lifecycle["review command"],
            gsc_lane=lifecycle["gsc lane"],
            ga4_lane=lifecycle["ga4 lane"],
            semrush_lane=lifecycle["semrush lane"],
            ai_citation_lane=lifecycle["ai-citation lane"],
            decision=lifecycle["decision"].casefold(),
            status=lifecycle["status"].casefold(),
        ),
    )


def _finding(rule_id: str, line: int, message: str) -> Finding:
    return make_finding(
        rule_id,
        "error",
        line,
        message=message,
        suggestion="Regenerate the sidecar from blog-strategy-contract/v1 and resolve every field explicitly.",
    )


def _sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda finding: (int(finding["line"]), str(finding["rule_id"])))
