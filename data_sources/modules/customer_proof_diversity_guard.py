"""
Customer Proof Diversity Guard

Validates that customer proof selection is intentional. Source-support guards
prove whether claims are backed; this guard proves the workflow checked beyond
the easiest case-study path and documents repeated proof use.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

try:
    from .guard_common import Finding, should_fail, summarize_findings
    from .customer_proof_selector import select_customer_proofs
    from .proof_sidecar import compose_with_sidecar, load_sidecar_content
    from .proof_usage import count_customer_proof_usage
except ImportError:  # pragma: no cover - supports direct script execution.
    from guard_common import Finding, should_fail, summarize_findings
    from customer_proof_selector import select_customer_proofs
    from proof_sidecar import compose_with_sidecar, load_sidecar_content
    from proof_usage import count_customer_proof_usage


DEFAULT_LEDGER_PATH = Path("context/customer-proof-usage-ledger.json")
DEFAULT_INDEX_PATH = Path("context/customer-proof-index.json")

CASE_STUDY_URL_RE = re.compile(r"https?://[^\s),|]+/case-studies/[^\s),|]+", re.IGNORECASE)
ANY_CUSTOMER_PROOF_URL_RE = re.compile(
    r"https?://[^\s),|]+(?:/case-studies/|/reviews|/customer|/testimonials?)[^\s),|]*",
    re.IGNORECASE,
)
CUSTOMER_PROOF_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?Customer Proof Pack:?\s*$",
    re.IGNORECASE,
)
SELECTION_DECISION_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?Customer Proof Selection Decision:?\s*$",
    re.IGNORECASE,
)
CUSTOMER_PROOF_SLATE_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?Customer Proof Slate:?\s*$",
    re.IGNORECASE,
)
SELECTED_CUSTOMER_PROOF_MINING_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?Selected Customer Proof Mining:?\s*$",
    re.IGNORECASE,
)
NEXT_PROOF_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?(?:PAA/FAQ Provenance|Metric Proof Pack|Source Map|"
    r"Customer Proof Slate|Selected Customer Proof Mining|Customer Proof Selection Decision|"
    r"E-E-A-T Proof Map|FAQ Proof Map|Review Story Selection|Review Site Theme Selection|"
    r"Structured data plan)\s*$",
    re.IGNORECASE,
)
NEXT_DECISION_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?(?:PAA/FAQ Provenance|Metric Proof Pack|Source Map|"
    r"Customer Proof Slate|Selected Customer Proof Mining|Customer Proof Pack|E-E-A-T Proof Map|"
    r"FAQ Proof Map|Review Story Selection|Review Site Theme Selection|Structured data plan)\s*$",
    re.IGNORECASE,
)
NEXT_SLATE_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?(?:PAA/FAQ Provenance|Metric Proof Pack|Source Map|"
    r"Selected Customer Proof Mining|Customer Proof Pack|Customer Proof Selection Decision|"
    r"E-E-A-T Proof Map|FAQ Proof Map|Review Story Selection|Review Site Theme Selection|"
    r"Structured data plan)\s*$",
    re.IGNORECASE,
)
NEXT_MINING_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?(?:PAA/FAQ Provenance|Metric Proof Pack|Source Map|"
    r"Customer Proof Slate|Customer Proof Pack|Customer Proof Selection Decision|"
    r"E-E-A-T Proof Map|FAQ Proof Map|Review Story Selection|Review Site Theme Selection|"
    r"Structured data plan)\s*$",
    re.IGNORECASE,
)
REVIEW_PROOF_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?(?:Review Story Selection|Review Site Theme Selection):?\s*$",
    re.IGNORECASE,
)
BULLET_FIELD_RE = re.compile(r"^\s*[-*+]\s*(?P<key>[^:]+):\s*(?P<value>.*?)\s*$")
EXACT_QUOTE_RE = re.compile(r"(?:\"[^\"]{20,}\"|\u201c[^\u201d]{20,}\u201d)")
QUOTE_CONTEXT_RE = re.compile(
    r"\b(?:said|says|reviewer|testimonial|customer review|case study|quoted|according to)\b",
    re.IGNORECASE,
)

NON_CASE_STUDY_KEYS = {
    "quote matrix candidates",
    "reference candidates",
    "references candidates",
    "customer story candidates",
    "customer stories candidates",
    "review-site experience evidence",
    "review site experience evidence",
}

BLOCKED_OR_EMPTY_RE = re.compile(
    r"^(?:none|none used|none collected|not collected|not checked|not reviewed|"
    r"not searched|n/a|na|no)$",
    re.IGNORECASE,
)
NONE_RESULT_RE = re.compile(
    r"^(?:none|none found|none used|none collected|not found|not usable|no usable|"
    r"n/a|na|no)$",
    re.IGNORECASE,
)
REQUIRED_SLATE_ROLES = ("metric", "quote", "theme")
EMPTY_SELECTION_VALUES = {"", "none", "none used", "n/a", "na", "no", "not selected"}


def check_content(
    content: str,
    *,
    proof_content: Optional[str] = None,
    source_path: str | Path | None = None,
    ledger_path: str | Path = DEFAULT_LEDGER_PATH,
    proof_index_path: str | Path = DEFAULT_INDEX_PATH,
    reference_date: Optional[date] = None,
) -> List[Finding]:
    """Return customer-proof selection and reuse findings."""
    proof_source = compose_with_sidecar(content, proof_content)
    pack = _extract_customer_proof_pack(proof_source)
    decision = _extract_selection_decision(proof_source)
    slate = _extract_customer_proof_slate(proof_source)
    mining = _extract_selected_customer_proof_mining(proof_source)
    article_case_study_urls = _case_study_urls(content)
    proof_urls = _customer_proof_urls(proof_source)
    findings: List[Finding] = []

    if pack is None:
        return _missing_pack_findings(content, article_case_study_urls)

    all_case_study_urls = sorted(set(article_case_study_urls + _case_study_urls("\n".join(pack["lines"]))))
    all_customer_proof_urls = sorted(set(all_case_study_urls + proof_urls))
    findings.extend(
        _pack_selection_findings(
            content,
            pack,
            decision,
            all_case_study_urls=all_case_study_urls,
            all_customer_proof_urls=all_customer_proof_urls,
        )
    )
    findings.extend(
        _slate_findings(
            content,
            proof_source,
            slate,
            decision,
            all_customer_proof_urls=all_customer_proof_urls,
        )
    )
    findings.extend(
        _proof_mining_findings(
            content,
            pack,
            mining,
            all_customer_proof_urls=all_customer_proof_urls,
        )
    )

    ledger = _load_ledger(ledger_path)
    reference = reference_date or date.today()
    reuse_findings, overused_sources = _reuse_findings(
        all_customer_proof_urls,
        pack=pack,
        decision=decision,
        ledger=ledger,
        reference=reference,
    )
    findings.extend(reuse_findings)

    if overused_sources:
        findings.extend(
            _stronger_underused_candidate_findings(
                overused_sources,
                pack=pack,
                decision=decision,
                ledger=ledger,
                ledger_path=ledger_path,
                proof_index_path=proof_index_path,
                reference=reference,
            )
        )

    return sorted(findings, key=lambda finding: (finding["severity"] != "error", finding["line"], finding["rule_id"]))


def check_file(
    path: str | Path,
    *,
    fail_on: str = "error",
    proof_sidecar: Optional[str] = None,
    ledger_path: str | Path = DEFAULT_LEDGER_PATH,
    proof_index_path: str | Path = DEFAULT_INDEX_PATH,
) -> List[Finding]:
    """Check a public article file plus optional validation sidecar."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")
    file_path = Path(path)
    proof_content = load_sidecar_content(file_path, proof_sidecar)
    return check_content(
        file_path.read_text(encoding="utf-8"),
        proof_content=proof_content,
        source_path=file_path,
        ledger_path=ledger_path,
        proof_index_path=proof_index_path,
    )


def _extract_customer_proof_pack(content: str) -> Optional[Dict[str, object]]:
    return _extract_bullet_block(content, CUSTOMER_PROOF_HEADING_RE, NEXT_PROOF_HEADING_RE)


def _extract_selection_decision(content: str) -> Optional[Dict[str, object]]:
    return _extract_bullet_block(content, SELECTION_DECISION_HEADING_RE, NEXT_DECISION_HEADING_RE)


def _extract_customer_proof_slate(content: str) -> Optional[Dict[str, object]]:
    slate = _extract_bullet_block(content, CUSTOMER_PROOF_SLATE_HEADING_RE, NEXT_SLATE_HEADING_RE)
    if slate is None:
        return None
    slate["roles"] = _parse_slate_roles(slate)
    return slate


def _extract_selected_customer_proof_mining(content: str) -> Optional[Dict[str, object]]:
    return _extract_bullet_block(
        content,
        SELECTED_CUSTOMER_PROOF_MINING_HEADING_RE,
        NEXT_MINING_HEADING_RE,
    )


def _extract_bullet_block(
    content: str,
    heading_re: re.Pattern[str],
    next_heading_re: re.Pattern[str],
) -> Optional[Dict[str, object]]:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if not heading_re.match(line.strip()):
            continue
        pack_lines: List[str] = []
        fields: List[Dict[str, object]] = []
        for offset, block_line in enumerate(lines[index + 1 :], start=index + 2):
            stripped = block_line.strip()
            if stripped.startswith("```"):
                break
            if next_heading_re.match(stripped):
                break
            if stripped and not stripped.startswith(("-", "*", "+")) and re.match(r"^\s*(?:#{1,6}\s+)?[A-Za-z].*$", stripped):
                break
            if not stripped:
                if pack_lines:
                    break
                continue
            pack_lines.append(block_line)
            match = BULLET_FIELD_RE.match(block_line)
            if match:
                fields.append(
                    {
                        "key": _normalize_key(match.group("key")),
                        "value": match.group("value").strip(),
                        "line": offset,
                    }
                )
        return {"line": index + 1, "lines": pack_lines, "fields": fields}
    return None


def _slate_findings(
    content: str,
    proof_source: str,
    slate: Optional[Dict[str, object]],
    decision: Optional[Dict[str, object]],
    *,
    all_customer_proof_urls: Sequence[str],
) -> List[Finding]:
    if not all_customer_proof_urls and not _has_customer_quote_claim(content):
        return []
    if slate is None:
        return [
            _finding(
                "customer_proof_slate_missing",
                1,
                "Customer proof appears, but no Customer Proof Slate was found.",
                (
                    "Add Customer Proof Slate to the validation sidecar with selector-backed "
                    "metric, quote, and theme role rows before drafting."
                ),
            )
        ]

    findings: List[Finding] = []
    roles = slate.get("roles", {})
    if not isinstance(roles, dict):
        roles = {}

    if not _first_field_value(slate, "selector command"):
        findings.append(
            _finding(
                "customer_proof_slate_selector_command_missing",
                int(slate["line"]),
                "Customer Proof Slate is missing a selector command.",
                "Add the customer_proof_selector.py command used to build the proof slate.",
            )
        )

    for role in REQUIRED_SLATE_ROLES:
        if role not in roles:
            findings.append(
                _finding(
                    "customer_proof_slate_role_missing",
                    int(slate["line"]),
                    f"Customer Proof Slate is missing the required {role} role row.",
                    "Add Role rows for metric, quote, theme, and experience_story when review-derived copy appears.",
                    match=role,
                )
            )

    if "experience_story" not in roles:
        findings.append(
            _finding(
                "customer_proof_slate_experience_story_missing",
                int(slate["line"]),
                "Customer proof appears without an experience_story Customer Proof Slate role.",
                (
                    "Run or consult the selector with --require-eeat-story and add an "
                    "experience_story role row. Select a proof-backed story only when it "
                    "improves the article objective; otherwise use Selected: [none] with "
                    "section-specific rejection reasons."
                ),
            )
        )
    else:
        findings.extend(_experience_story_consideration_findings(roles["experience_story"]))

    selected_ids = _selected_proof_ids(decision)
    slate_selected_ids = _slate_selected_ids(roles)
    for proof_id in selected_ids:
        if proof_id not in slate_selected_ids:
            findings.append(
                _finding(
                    "customer_proof_selected_not_in_slate",
                    int(decision["line"]) if decision else int(slate["line"]),
                    "Customer Proof Selection Decision selected proof that is not selected in Customer Proof Slate.",
                    "Add the proof ID to the matching slate Role selected list or choose a selected slate candidate.",
                    match=proof_id,
                )
            )

    findings.extend(_stronger_slate_candidate_findings(slate))
    return findings


def _proof_mining_findings(
    content: str,
    pack: Dict[str, object],
    mining: Optional[Dict[str, object]],
    *,
    all_customer_proof_urls: Sequence[str],
) -> List[Finding]:
    if not all_customer_proof_urls and not _has_customer_quote_claim(content):
        return []
    if mining is None:
        return [
            _finding(
                "selected_customer_proof_mining_missing",
                int(pack["line"]),
                "Customer proof appears, but no Selected Customer Proof Mining block was found.",
                (
                    "Read the selected public proof URL before drafting and add Selected Customer "
                    "Proof Mining with quote, metric, POV/story, workflow-theme, recommended-use, "
                    "final-use, exclusion, and approved status details."
                ),
            )
        ]

    findings: List[Finding] = []
    for required_key in ("checked for", "recommended use", "final use in copy", "status"):
        if not _first_field_value(mining, required_key):
            findings.append(
                _finding(
                    "selected_customer_proof_mining_required_field_missing",
                    int(mining["line"]),
                    f"Selected Customer Proof Mining is missing required field: {required_key}.",
                    "Add Checked for, Recommended use, Final use in copy, and Status: approved.",
                    match=required_key,
                )
            )

    status = _first_field_value(mining, "status")
    if status and "approved" not in status.lower():
        findings.append(
            _finding(
                "selected_customer_proof_mining_status_not_approved",
                int(mining["line"]),
                "Selected Customer Proof Mining status is not approved.",
                "Set Status: approved only after the selected source was mined for quotes, metrics, POV/story, and themes.",
                match=status,
            )
        )

    if _pack_declares_none_used(pack, "approved quotes") and not _first_field_value(
        mining, "usable quotes found"
    ):
        findings.append(
            _finding(
                "selected_customer_proof_mining_quote_result_missing",
                int(mining["line"]),
                "Customer Proof Pack says approved quotes are none used, but mining does not document usable quote results.",
                "Add Usable quotes found with approved rows, none found, or a rejected quote reason.",
            )
        )

    if _pack_declares_none_used(pack, "approved metrics") and not _first_field_value(
        mining, "usable metrics found"
    ):
        findings.append(
            _finding(
                "selected_customer_proof_mining_metric_result_missing",
                int(mining["line"]),
                "Customer Proof Pack says approved metrics are none used, but mining does not document usable metric results.",
                "Add Usable metrics found with approved rows, none found, or a rejected metric reason.",
            )
        )

    findings.extend(_omitted_usable_mined_proof_findings(mining))
    return findings


def _pack_declares_none_used(pack: Dict[str, object], key: str) -> bool:
    normalized_key = _normalize_key(key)
    for field in pack.get("fields", []):
        if str(field.get("key", "")) != normalized_key:
            continue
        value = _normalize_space(str(field.get("value", "")))
        if not value:
            return False
        return "none" in value and "used" in value or bool(NONE_RESULT_RE.match(value))
    return False


def _omitted_usable_mined_proof_findings(mining: Dict[str, object]) -> List[Finding]:
    findings: List[Finding] = []
    final_use = _first_field_value(mining, "final use in copy")
    excluded_proof = _first_field_value(mining, "excluded proof")
    checks = [
        (
            "quote",
            _first_field_value(mining, "usable quotes found"),
            ("quote", "exact quote", "testimonial"),
        ),
        (
            "POV/story",
            _first_field_value(mining, "usable pov/story found"),
            ("pov", "story", "experience"),
        ),
    ]
    for proof_type, value, final_use_terms in checks:
        if not _mining_value_indicates_usable_proof(value):
            continue
        if any(term in final_use.lower() for term in final_use_terms):
            continue
        if _has_specific_excluded_proof_reason(excluded_proof, proof_type):
            continue
        findings.append(
            _finding(
                "selected_customer_proof_mining_usable_proof_omitted",
                int(mining["line"]),
                f"Selected Customer Proof Mining found usable {proof_type} evidence, but final copy omits it without a section-specific reason.",
                (
                    "Use the mined proof if it improves the article objective, or document why it was excluded "
                    "for this section."
                ),
                severity="warning",
                match=proof_type,
            )
        )
    return findings


def _mining_value_indicates_usable_proof(value: str) -> bool:
    normalized = _normalize_space(value)
    if not normalized or NONE_RESULT_RE.match(normalized):
        return False
    if "none found" in normalized or "no usable" in normalized or "not found" in normalized:
        return False
    return True


def _has_specific_excluded_proof_reason(value: str, proof_type: str) -> bool:
    normalized = _normalize_space(value)
    if not normalized or NONE_RESULT_RE.match(normalized):
        return False
    if proof_type.lower().split("/", 1)[0] not in normalized and "proof" not in normalized:
        return False
    reason_signals = ("because", "current", "section", "omitted", "excluded", "does not", "not relevant")
    return len(normalized.split()) >= 8 and any(signal in normalized for signal in reason_signals)


def _parse_slate_roles(slate: Dict[str, object]) -> Dict[str, Dict[str, object]]:
    roles: Dict[str, Dict[str, object]] = {}
    for field in slate.get("fields", []):
        if str(field.get("key", "")) != "role":
            continue
        value = str(field.get("value", ""))
        role, details = _parse_role_row(value)
        if role:
            details["line"] = field.get("line", slate.get("line", 1))
            roles[role] = details
    return roles


def _parse_role_row(value: str) -> tuple[str, Dict[str, object]]:
    segments = [segment.strip() for segment in value.split("|") if segment.strip()]
    if not segments:
        return "", {}
    role = _normalize_key(segments[0]).replace(" ", "_")
    details: Dict[str, object] = {
        "top_candidates": [],
        "selected": [],
        "rejected": {},
    }
    for segment in segments[1:]:
        if ":" not in segment:
            continue
        key, raw_value = segment.split(":", 1)
        normalized_key = _normalize_key(key)
        if normalized_key == "top candidates":
            details["top_candidates"] = _parse_proof_id_list(raw_value)
        elif normalized_key == "selected":
            details["selected"] = _parse_proof_id_list(raw_value)
        elif normalized_key == "rejected stronger candidates":
            details["rejected"] = _parse_rejected_candidates(raw_value)
    return role, details


def _parse_proof_id_list(value: str) -> List[str]:
    cleaned = value.strip().strip("[]")
    proof_ids: List[str] = []
    for raw_item in cleaned.split(","):
        item = _clean_proof_id(raw_item)
        if not item or item.lower() in EMPTY_SELECTION_VALUES or " or none" in item.lower():
            continue
        proof_ids.append(item)
    return proof_ids


def _parse_rejected_candidates(value: str) -> Dict[str, str]:
    cleaned = value.strip().strip("[]")
    rejected: Dict[str, str] = {}
    for raw_item in cleaned.split(","):
        item = raw_item.strip()
        if not item or item.lower() in EMPTY_SELECTION_VALUES:
            continue
        proof_id, _, reason = item.partition(":")
        clean_id = _clean_proof_id(proof_id)
        clean_reason = reason.strip()
        if clean_id and clean_reason:
            rejected[clean_id] = clean_reason
    return rejected


def _selected_proof_ids(decision: Optional[Dict[str, object]]) -> List[str]:
    if decision is None:
        return []
    proof_ids: List[str] = []
    for field in decision.get("fields", []):
        if str(field.get("key", "")) != "selected proof":
            continue
        value = str(field.get("value", ""))
        proof_id = _clean_proof_id(value.split("|", 1)[0])
        if proof_id and proof_id.lower() not in EMPTY_SELECTION_VALUES:
            proof_ids.append(proof_id)
    return proof_ids


def _slate_selected_ids(roles: Dict[str, object]) -> set[str]:
    selected: set[str] = set()
    for role_details in roles.values():
        if not isinstance(role_details, dict):
            continue
        selected.update(str(proof_id) for proof_id in role_details.get("selected", []))
    return selected


def _stronger_slate_candidate_findings(slate: Dict[str, object]) -> List[Finding]:
    roles = slate.get("roles", {})
    if not isinstance(roles, dict):
        return []
    findings: List[Finding] = []
    for role, details in roles.items():
        if not isinstance(details, dict):
            continue
        top_candidates = [str(candidate) for candidate in details.get("top_candidates", [])]
        selected = {str(candidate) for candidate in details.get("selected", [])}
        rejected = details.get("rejected", {})
        rejected_ids = set(rejected.keys()) if isinstance(rejected, dict) else set()
        if not top_candidates or not selected:
            continue
        selected_indexes = [
            index for index, candidate in enumerate(top_candidates) if candidate in selected
        ]
        if not selected_indexes:
            continue
        first_selected_index = min(selected_indexes)
        for candidate in top_candidates[:first_selected_index]:
            if candidate in selected or candidate in rejected_ids:
                continue
            findings.append(
                _finding(
                    "customer_proof_stronger_slate_candidate_available",
                    int(details.get("line", slate["line"])),
                    (
                        "Customer Proof Slate selected a lower-ranked proof while a stronger "
                        f"{role} candidate is documented: {candidate}."
                    ),
                    (
                        "Use the stronger candidate or add it to Rejected stronger candidates "
                        "with a section-specific reason."
                    ),
                    severity="warning",
                    match=candidate,
                )
            )
    return findings


def _experience_story_consideration_findings(role_details: Dict[str, object]) -> List[Finding]:
    selected = {str(candidate) for candidate in role_details.get("selected", [])}
    if selected:
        return []

    top_candidates = [str(candidate) for candidate in role_details.get("top_candidates", [])]
    if not top_candidates:
        return [
            _finding(
                "customer_proof_slate_experience_story_candidates_missing",
                int(role_details.get("line", 1)),
                "experience_story slate row has no story candidates.",
                (
                    "Run or consult the selector with --require-eeat-story and list the "
                    "strongest identity-backed story candidates, even when none are used."
                ),
            )
        ]

    rejected = role_details.get("rejected", {})
    if not isinstance(rejected, dict):
        rejected = {}

    for candidate, reason in rejected.items():
        if candidate in top_candidates and _has_section_specific_story_rejection_reason(str(reason)):
            return []

    return [
        _finding(
            "customer_proof_slate_experience_story_rejection_missing",
            int(role_details.get("line", 1)),
            (
                "experience_story slate row selected no story but did not give a "
                "section-specific rejection reason for a ranked story candidate."
            ),
            (
                "Use the proof-backed story if it improves the article objective, or "
                "add at least one ranked candidate to Rejected stronger candidates with "
                "a concrete section-specific reason."
            ),
            match=top_candidates[0],
        )
    ]


def _has_section_specific_story_rejection_reason(reason: str) -> bool:
    normalized = _normalize_space(reason)
    if not normalized or NONE_RESULT_RE.match(normalized):
        return False
    reason_signals = (
        "because",
        "section",
        "article",
        "objective",
        "omitted",
        "not used",
        "instead",
        "while",
    )
    return len(normalized.split()) >= 8 and any(signal in normalized for signal in reason_signals)


def _needs_experience_story_slate_role(content: str, proof_source: str) -> bool:
    if REVIEW_PROOF_HEADING_RE.search(proof_source):
        return True
    review_signal = re.search(
        r"(?:capterra\.com|g2\.com/products/simpro/reviews|review-derived|reviewer)",
        _blank_fenced_code(content),
        flags=re.IGNORECASE,
    )
    return bool(review_signal)


def _clean_proof_id(value: str) -> str:
    return value.strip().strip("[]").strip("`").strip()


def _missing_pack_findings(
    content: str,
    article_case_study_urls: Sequence[str],
) -> List[Finding]:
    if not article_case_study_urls and not _has_customer_quote_claim(content):
        return []
    return [
        _finding(
            "customer_proof_pack_missing",
            1,
            "Customer proof appears in public copy, but no Customer Proof Pack was found.",
            (
                "Add a Customer Proof Pack to the validation sidecar with proof candidates, "
                "non-case-study search evidence, selected proof, and claims excluded."
            ),
        )
    ]


def _pack_selection_findings(
    content: str,
    pack: Dict[str, object],
    decision: Optional[Dict[str, object]],
    *,
    all_case_study_urls: Sequence[str],
    all_customer_proof_urls: Sequence[str],
) -> List[Finding]:
    findings: List[Finding] = []
    if all_customer_proof_urls and decision is None:
        findings.append(
            _finding(
                "customer_proof_selection_decision_missing",
                pack["line"],
                "Customer proof appears, but no Customer Proof Selection Decision block was found.",
                (
                    "Add Customer Proof Selection Decision to the validation sidecar with selector command, "
                    "selected proof IDs, rejected stronger candidates, and final use in copy."
                ),
            )
        )

    if all_case_study_urls and not _has_non_case_study_attempt(pack):
        findings.append(
            _finding(
                "customer_proof_non_case_study_attempt_missing",
                pack["line"],
                "Customer Proof Pack uses case-study proof without a documented Quote Matrix, Reference, Customer Story, or review-site search attempt.",
                (
                    "Add Quote Matrix candidates, Reference candidates, Customer Stories candidates, "
                    "or review-site experience evidence with the search result, blocker, or approval status."
                ),
            )
        )

    if _has_customer_quote_claim(content) and not _has_approved_quote(pack):
        findings.append(
            _finding(
                "customer_quote_requires_approved_quote",
                _first_quote_line(content),
                "Exact quote or testimonial wording appears in public copy without an approved Customer Proof Pack quote row.",
                (
                    "Add an Approved quote row with customer or reviewer identity, source type, "
                    "URL or source ref, Evidence, Status: approved, and intended Use."
                ),
            )
        )
    return findings


def _reuse_findings(
    customer_proof_urls: Sequence[str],
    *,
    pack: Dict[str, object],
    decision: Optional[Dict[str, object]],
    ledger: Dict[str, object],
    reference: date,
) -> tuple[List[Finding], List[Dict[str, object]]]:
    findings: List[Finding] = []
    overused_sources: List[Dict[str, object]] = []
    for url in customer_proof_urls:
        usage = count_customer_proof_usage(
            ledger,
            proof_id=_proof_id_from_url(url),
            source_url=url,
            reference_date=reference,
        )
        if usage["recent_uses_90d"] >= 3:
            overused_sources.append({"url": url, "usage": usage})
        reason = _source_specific_reuse_reason(url, pack, decision)
        if usage["recent_uses_90d"] >= 3 and not reason:
            findings.append(
                _finding(
                    "customer_proof_reuse_requires_source_specific_reason",
                    pack["line"],
                    f"Customer proof source has been used {usage['recent_uses_90d']} times in the last 90 days: {url}",
                    (
                        "Add a source-specific Reuse reason naming the proof ID, customer, or URL, "
                        "or choose a stronger underused proof source from customer-proof-index.json."
                    ),
                    match=url,
                )
            )
        elif usage["recent_uses_90d"] >= 2 and not reason:
            findings.append(
                _finding(
                    "customer_proof_reuse_warning",
                    pack["line"],
                    f"Customer proof source has already been used {usage['recent_uses_90d']} times in the last 90 days: {url}",
                    "Consider a fresher proof source or document a Reuse reason.",
                    severity="warning",
                    match=url,
                )
            )
    return findings, overused_sources


def _stronger_underused_candidate_findings(
    overused_sources: Sequence[Dict[str, object]],
    *,
    pack: Dict[str, object],
    decision: Optional[Dict[str, object]],
    ledger: Dict[str, object],
    ledger_path: str | Path,
    proof_index_path: str | Path,
    reference: date,
) -> List[Finding]:
    index_status = _load_index_for_comparison(proof_index_path)
    if index_status["error"]:
        return [
            _finding(
                str(index_status["rule_id"]),
                pack["line"],
                str(index_status["message"]),
                str(index_status["suggestion"]),
            )
        ]

    index = index_status["index"]
    if not isinstance(index, dict) or not index.get("proof"):
        return []

    selector_query = _selector_query(decision)
    proof_role = _selector_proof_role(decision)
    ranked = select_customer_proofs(
        selector_query,
        index_path=proof_index_path,
        ledger_path=ledger_path,
        proof_role=proof_role,
        limit=25,
        reference_date=reference,
    )
    findings: List[Finding] = []
    for source in overused_sources:
        url = str(source.get("url", ""))
        selected = _matching_ranked_candidate(url, ranked, index)
        selected_score = int(selected.get("score", 0)) if selected else 0
        stronger = [
            candidate
            for candidate in ranked
            if _is_stronger_underused_candidate(candidate, selected_score, url)
            and not _decision_rejects_candidate(candidate, decision)
        ]
        if stronger:
            best = stronger[0]
            findings.append(
                _finding(
                    "customer_proof_stronger_underused_candidate_available",
                    pack["line"],
                    (
                        "Overused customer proof was selected while a stronger underused approved proof candidate "
                        f"is available: {best.get('proof_id')} ({best.get('customer')})."
                    ),
                    (
                        "Use the stronger underused proof or add a Rejected stronger underused candidate row "
                        "with the candidate proof ID and a section-specific rejection reason."
                    ),
                    match=f"{url} -> {best.get('proof_id')}",
                )
            )
    return findings


def _load_index_for_comparison(path: str | Path) -> Dict[str, object]:
    index_path = Path(path)
    if not index_path.exists():
        return {
            "error": True,
            "rule_id": "customer_proof_index_missing",
            "message": f"Customer proof index is required to compare overused proof sources, but it was not found: {index_path}",
            "suggestion": "Pass --proof-index context/customer-proof-index.json or create the proof index before running publish readiness.",
            "index": {},
        }
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "error": True,
            "rule_id": "customer_proof_index_invalid",
            "message": f"Customer proof index is not valid JSON: {index_path}: {exc}",
            "suggestion": "Fix customer-proof-index.json so overused proof can be compared against approved alternatives.",
            "index": {},
        }
    if not isinstance(payload, dict) or not isinstance(payload.get("proof", []), list):
        return {
            "error": True,
            "rule_id": "customer_proof_index_invalid",
            "message": f"Customer proof index must be an object with a proof list: {index_path}",
            "suggestion": "Fix customer-proof-index.json so overused proof can be compared against approved alternatives.",
            "index": {},
        }
    return {"error": False, "index": payload}


def _selector_query(decision: Optional[Dict[str, object]]) -> str:
    command = _first_field_value(decision, "selector command")
    if command:
        try:
            parts = shlex.split(command)
        except ValueError:
            parts = command.split()
        for index, part in enumerate(parts):
            if part.endswith("customer_proof_selector.py") and index + 1 < len(parts):
                return parts[index + 1]
        if parts:
            return " ".join(parts)
    return "customer proof selection"


def _selector_proof_role(decision: Optional[Dict[str, object]]) -> str:
    command = _first_field_value(decision, "selector command")
    if not command:
        return "any"
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()
    for index, part in enumerate(parts):
        if part == "--proof-role" and index + 1 < len(parts):
            role = parts[index + 1]
            if role in {"experience_story", "metric", "quote", "theme", "any"}:
                return role
    return "any"


def _matching_ranked_candidate(
    url: str,
    ranked: Sequence[Dict[str, Any]],
    index: Dict[str, Any],
) -> Dict[str, Any]:
    slug = _proof_id_from_url(url)
    indexed = _index_candidate_for_url(url, index)
    identifiers = {slug, url}
    if indexed:
        identifiers.add(str(indexed.get("proof_id", "")))
        identifiers.add(str(indexed.get("customer", "")))
    for candidate in ranked:
        if _candidate_matches_identifiers(candidate, identifiers):
            return candidate
    return indexed or {}


def _index_candidate_for_url(url: str, index: Dict[str, Any]) -> Dict[str, Any]:
    slug = _proof_id_from_url(url)
    for candidate in index.get("proof", []):
        if not isinstance(candidate, dict):
            continue
        if str(candidate.get("public_url", "")) == url:
            return candidate
        if str(candidate.get("proof_id", "")) == slug:
            return candidate
    return {}


def _is_stronger_underused_candidate(candidate: Dict[str, Any], selected_score: int, selected_url: str) -> bool:
    if str(candidate.get("public_url", "")) == selected_url:
        return False
    if str(candidate.get("proof_id", "")) == _proof_id_from_url(selected_url):
        return False
    if str(candidate.get("approval_status", "")).strip().lower() != "approved":
        return False
    if not bool(candidate.get("public_copy_allowed", False)):
        return False
    if int(candidate.get("recent_uses_90d", 0)) >= 3:
        return False
    return int(candidate.get("score", 0)) >= selected_score


def _decision_rejects_candidate(candidate: Dict[str, Any], decision: Optional[Dict[str, object]]) -> bool:
    if decision is None:
        return False
    identifiers = [
        str(candidate.get("proof_id", "")).strip().lower(),
        str(candidate.get("public_url", "")).strip().lower(),
        str(candidate.get("customer", "")).strip().lower(),
    ]
    for field in decision.get("fields", []):
        key = str(field.get("key", ""))
        if "rejected" not in key:
            continue
        value = str(field.get("value", "")).strip().lower()
        if not value or "none found" in value or "none" == value:
            continue
        if any(identifier and identifier in value for identifier in identifiers):
            return True
    return False


def _first_field_value(block: Optional[Dict[str, object]], key: str) -> str:
    if block is None:
        return ""
    normalized_key = _normalize_key(key)
    for field in block.get("fields", []):
        if str(field.get("key", "")) == normalized_key:
            return str(field.get("value", "")).strip()
    return ""


def _has_non_case_study_attempt(pack: Dict[str, object]) -> bool:
    for field in pack.get("fields", []):
        key = str(field.get("key", ""))
        value = str(field.get("value", "")).strip()
        if key not in NON_CASE_STUDY_KEYS:
            continue
        if _is_documented_attempt(value):
            return True
    return False


def _is_documented_attempt(value: str) -> bool:
    normalized = _normalize_space(value)
    if not normalized or BLOCKED_OR_EMPTY_RE.match(normalized):
        return False
    if "none collected" in normalized or "not collected" in normalized:
        return False
    return True


def _has_reuse_reason(pack: Dict[str, object]) -> bool:
    for field in pack.get("fields", []):
        key = str(field.get("key", ""))
        value = str(field.get("value", "")).strip()
        if key == "reuse reason" and value:
            return True
    return False


def _source_specific_reuse_reason(
    url: str,
    pack: Dict[str, object],
    decision: Optional[Dict[str, object]],
) -> str:
    identifiers = _source_identifiers(url, pack, decision)
    for block in (pack, decision):
        if block is None:
            continue
        for field in block.get("fields", []):
            key = str(field.get("key", ""))
            if key != "reuse reason":
                continue
            value = str(field.get("value", "")).strip()
            normalized_value = _normalize_text(value)
            if value and any(identifier and identifier in normalized_value for identifier in identifiers):
                return value
    return ""


def _source_identifiers(
    url: str,
    pack: Dict[str, object],
    decision: Optional[Dict[str, object]],
) -> List[str]:
    identifiers = {
        _normalize_text(url),
        _normalize_text(_proof_id_from_url(url)),
        _normalize_text(url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ")),
    }
    for block in (pack, decision):
        if block is None:
            continue
        for field in block.get("fields", []):
            value = str(field.get("value", ""))
            if url not in value:
                continue
            for segment in re.split(r"\s*\|\s*", value):
                if segment.strip().lower().startswith("customer"):
                    identifiers.add(_normalize_text(segment.split(":", 1)[-1]))
                if segment.strip().lower().startswith("customer/brand"):
                    identifiers.add(_normalize_text(segment.split(":", 1)[-1]))
                if segment.strip().lower().startswith("selected proof"):
                    identifiers.add(_normalize_text(segment.split(":", 1)[-1]))
            prefix = value.split("|", 1)[0]
            if "," in prefix:
                identifiers.add(_normalize_text(prefix.split(",", 1)[0]))
    return sorted(identifier for identifier in identifiers if identifier)


def _candidate_matches_identifiers(candidate: Dict[str, Any], identifiers: set[str]) -> bool:
    candidate_identifiers = {
        str(candidate.get("proof_id", "")),
        str(candidate.get("public_url", "")),
        str(candidate.get("customer", "")),
    }
    normalized_candidate_identifiers = {_normalize_text(identifier) for identifier in candidate_identifiers if identifier}
    normalized_identifiers = {_normalize_text(identifier) for identifier in identifiers if identifier}
    return bool(normalized_candidate_identifiers.intersection(normalized_identifiers))


def _has_approved_quote(pack: Dict[str, object]) -> bool:
    for field in pack.get("fields", []):
        key = str(field.get("key", ""))
        value = str(field.get("value", ""))
        if key == "approved quote" and "status: approved" in value.lower():
            return True
    return False


def _has_customer_quote_claim(content: str) -> bool:
    public_content = _blank_fenced_code(content)
    for paragraph in _paragraphs(public_content):
        if not EXACT_QUOTE_RE.search(paragraph):
            continue
        if QUOTE_CONTEXT_RE.search(paragraph) or ANY_CUSTOMER_PROOF_URL_RE.search(paragraph):
            return True
    return False


def _first_quote_line(content: str) -> int:
    public_content = _blank_fenced_code(content)
    for line_number, line in enumerate(public_content.splitlines(), start=1):
        if EXACT_QUOTE_RE.search(line):
            return line_number
    return 1


def _case_study_urls(content: str) -> List[str]:
    return [match.group(0).rstrip(".,") for match in CASE_STUDY_URL_RE.finditer(content)]


def _customer_proof_urls(content: str) -> List[str]:
    return [match.group(0).rstrip(".,") for match in ANY_CUSTOMER_PROOF_URL_RE.finditer(content)]


def _load_ledger(path: str | Path) -> Dict[str, object]:
    ledger_path = Path(path)
    if not ledger_path.exists():
        return {"uses": []}
    return json.loads(ledger_path.read_text(encoding="utf-8"))


def _proof_id_from_url(url: str) -> str:
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    if "/case-studies/" in url:
        return f"case-study-{slug}"
    return slug


def _paragraphs(content: str) -> Iterable[str]:
    chunks = re.split(r"\n\s*\n", content)
    for chunk in chunks:
        stripped = chunk.strip()
        if stripped:
            yield stripped


def _blank_fenced_code(content: str) -> str:
    lines = content.splitlines()
    blanked: List[str] = []
    in_fence = False
    for line in lines:
        if line.strip().startswith("```"):
            in_fence = not in_fence
            blanked.append("")
            continue
        blanked.append("" if in_fence else line)
    return "\n".join(blanked)


def _normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower()).strip()


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower()).strip()


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _finding(
    rule_id: str,
    line: int,
    message: str,
    suggestion: str,
    *,
    severity: str = "error",
    match: str = "",
) -> Finding:
    finding: Finding = {
        "rule_id": rule_id,
        "severity": severity,
        "line": line,
        "column": 1,
        "message": message,
        "suggestion": suggestion,
    }
    if match:
        finding["match"] = match
    return finding


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check customer proof selection and reuse governance.")
    parser.add_argument("path", help="Markdown file to check")
    parser.add_argument(
        "--fail-on",
        choices=["error", "warning", "none"],
        default="error",
        help="Finding severity that should produce a nonzero exit code.",
    )
    parser.add_argument("--proof-sidecar", help="Optional validation sidecar containing Customer Proof Pack rows.")
    parser.add_argument("--ledger", default=str(DEFAULT_LEDGER_PATH), help="Customer proof usage ledger JSON path.")
    parser.add_argument("--proof-index", default=str(DEFAULT_INDEX_PATH), help="Customer proof index JSON path.")
    args = parser.parse_args(argv)

    findings = check_file(
        args.path,
        fail_on=args.fail_on,
        proof_sidecar=args.proof_sidecar,
        ledger_path=args.ledger,
        proof_index_path=args.proof_index,
    )
    payload = {
        "path": args.path,
        "fail_on": args.fail_on,
        "summary": summarize_findings(findings),
        "findings": findings,
    }
    print(json.dumps(payload, indent=2))
    return 1 if should_fail(findings, fail_on=args.fail_on) else 0


if __name__ == "__main__":
    sys.exit(_main())
