"""Compatibility facade for customer-proof diversity validation."""

from __future__ import annotations

import sys
from pathlib import Path

if not __package__:  # pragma: no cover - supports direct script execution.
    repository_root = str(Path(__file__).resolve().parents[2])
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)
    __package__ = "data_sources.modules"

from .customer_proof.diversity import check_content, check_file
from .customer_proof.diversity_cli import _main
from .customer_proof.contracts import CustomerProofDataError
from .customer_proof.diversity_common import (
    _blank_fenced_code,
    _case_study_urls,
    _customer_proof_link_findings,
    _customer_proof_urls,
    _finding,
    _first_quote_line,
    _has_customer_quote_claim,
    _load_ledger,
    _normalize_key,
    _normalize_space,
    _normalize_text,
    _paragraphs,
    _proof_id_from_url,
)
from .customer_proof.diversity_contracts import (
    ANY_CUSTOMER_PROOF_URL_RE,
    BLOCKED_OR_EMPTY_RE,
    BULLET_FIELD_RE,
    CASE_STUDY_URL_RE,
    CUSTOMER_PROOF_HEADING_RE,
    CUSTOMER_PROOF_SLATE_HEADING_RE,
    DEFAULT_INDEX_PATH,
    DEFAULT_LEDGER_PATH,
    EMPTY_SELECTION_VALUES,
    EXACT_QUOTE_RE,
    NEXT_DECISION_HEADING_RE,
    NEXT_MINING_HEADING_RE,
    NEXT_PROOF_HEADING_RE,
    NEXT_SLATE_HEADING_RE,
    NONE_RESULT_RE,
    NON_CASE_STUDY_KEYS,
    QUOTE_CONTEXT_RE,
    REQUIRED_SLATE_ROLES,
    REVIEW_PROOF_HEADING_RE,
    SELECTED_CUSTOMER_PROOF_MINING_HEADING_RE,
    SELECTION_DECISION_HEADING_RE,
)
from .customer_proof.diversity_mining import (
    _has_specific_excluded_proof_reason,
    _mining_value_indicates_usable_proof,
    _omitted_usable_mined_proof_findings,
    _pack_declares_none_used,
    _proof_mining_findings,
    _selector_evidence_findings,
)
from .customer_proof.diversity_parsing import (
    _clean_proof_id,
    _extract_bullet_block,
    _extract_customer_proof_pack,
    _extract_customer_proof_slate,
    _extract_selected_customer_proof_mining,
    _extract_selection_decision,
    _first_field_value,
    _parse_proof_id_list,
    _parse_rejected_candidates,
    _parse_role_row,
    _parse_slate_roles,
    _selected_proof_ids,
    _slate_selected_ids,
)
from .customer_proof.diversity_reuse import (
    _candidate_matches_identifiers,
    _decision_rejects_candidate,
    _index_candidate_for_url,
    _is_stronger_underused_candidate,
    _matching_ranked_candidate,
    _reuse_findings,
    _selector_proof_role,
    _selector_query,
    _source_identifiers,
    _source_specific_reuse_reason,
    _source_specific_zero_use_comparison,
    _stronger_underused_candidate_findings,
)
from .customer_proof.diversity_selection import (
    _has_approved_quote,
    _has_non_case_study_attempt,
    _has_reuse_reason,
    _is_documented_attempt,
    _missing_pack_findings,
    _pack_selection_findings,
)
from .customer_proof.diversity_slate import (
    _experience_story_consideration_findings,
    _has_section_specific_story_rejection_reason,
    _needs_experience_story_slate_role,
    _slate_findings,
    _stronger_slate_candidate_findings,
)
from .customer_proof.evidence import verify_selector_evidence_roles
from .customer_proof.selection import select_customer_proofs
from .guard_common import should_fail

__all__ = [
    "ANY_CUSTOMER_PROOF_URL_RE",
    "BLOCKED_OR_EMPTY_RE",
    "BULLET_FIELD_RE",
    "CASE_STUDY_URL_RE",
    "CUSTOMER_PROOF_HEADING_RE",
    "CUSTOMER_PROOF_SLATE_HEADING_RE",
    "CustomerProofDataError",
    "DEFAULT_INDEX_PATH",
    "DEFAULT_LEDGER_PATH",
    "EMPTY_SELECTION_VALUES",
    "EXACT_QUOTE_RE",
    "NEXT_DECISION_HEADING_RE",
    "NEXT_MINING_HEADING_RE",
    "NEXT_PROOF_HEADING_RE",
    "NEXT_SLATE_HEADING_RE",
    "NONE_RESULT_RE",
    "NON_CASE_STUDY_KEYS",
    "QUOTE_CONTEXT_RE",
    "REQUIRED_SLATE_ROLES",
    "REVIEW_PROOF_HEADING_RE",
    "SELECTED_CUSTOMER_PROOF_MINING_HEADING_RE",
    "SELECTION_DECISION_HEADING_RE",
    "_blank_fenced_code",
    "_candidate_matches_identifiers",
    "_case_study_urls",
    "_clean_proof_id",
    "_customer_proof_link_findings",
    "_customer_proof_urls",
    "_decision_rejects_candidate",
    "_experience_story_consideration_findings",
    "_extract_bullet_block",
    "_extract_customer_proof_pack",
    "_extract_customer_proof_slate",
    "_extract_selected_customer_proof_mining",
    "_extract_selection_decision",
    "_finding",
    "_first_field_value",
    "_first_quote_line",
    "_has_approved_quote",
    "_has_customer_quote_claim",
    "_has_non_case_study_attempt",
    "_has_reuse_reason",
    "_has_section_specific_story_rejection_reason",
    "_has_specific_excluded_proof_reason",
    "_index_candidate_for_url",
    "_is_documented_attempt",
    "_is_stronger_underused_candidate",
    "_load_ledger",
    "_main",
    "_matching_ranked_candidate",
    "_mining_value_indicates_usable_proof",
    "_missing_pack_findings",
    "_needs_experience_story_slate_role",
    "_normalize_key",
    "_normalize_space",
    "_normalize_text",
    "_omitted_usable_mined_proof_findings",
    "_pack_declares_none_used",
    "_pack_selection_findings",
    "_paragraphs",
    "_parse_proof_id_list",
    "_parse_rejected_candidates",
    "_parse_role_row",
    "_parse_slate_roles",
    "_proof_id_from_url",
    "_proof_mining_findings",
    "_reuse_findings",
    "_selected_proof_ids",
    "_selector_evidence_findings",
    "_selector_proof_role",
    "_selector_query",
    "_slate_findings",
    "_slate_selected_ids",
    "_source_identifiers",
    "_source_specific_reuse_reason",
    "_source_specific_zero_use_comparison",
    "_stronger_slate_candidate_findings",
    "_stronger_underused_candidate_findings",
    "check_content",
    "check_file",
    "select_customer_proofs",
    "should_fail",
    "verify_selector_evidence_roles",
]

if __name__ == "__main__":
    raise SystemExit(_main())
