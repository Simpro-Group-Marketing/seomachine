"""Compatibility facade for PAA provenance validation and collection."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from .blog_assembly_contract import canonical_json_sha256
    from .execution_attestation import verify_mapping_attestation
    from .guard_common import should_fail
except ImportError:  # pragma: no cover - supports top-level/direct-script imports.
    repository_root = str(Path(__file__).resolve().parents[2])
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)
    __package__ = "data_sources.modules"
    from data_sources.modules.blog_assembly_contract import canonical_json_sha256
    from data_sources.modules.execution_attestation import verify_mapping_attestation
    from data_sources.modules.guard_common import should_fail
from .paa_provenance.dependencies import PaaDependencies
from .paa_provenance.collection import (
    _answersocrates_extraction_code,
    _derive_answersocrates_observations,
    build_answersocrates_artifact,
    collect_answersocrates_raw_capture,
    find_npx_executable,
    write_answersocrates_artifact,
)
from .paa_provenance.evaluation import check_content
from .paa_provenance.results import check_file, evaluate_content, evaluate_file
from .paa_provenance.parsing import (
    _extract_faq_questions,
    _extract_provenance_block,
    _provenance_or_bound_artifact,
)
from .paa_provenance.policy import (
    _answersocrates_blocker_finding,
    _answersocrates_record_finding,
    _workflow_policy_finding,
)
from .paa_provenance.artifact import (
    _extract_csv_questions,
    _parse_question_artifact,
    _strict_question_list,
    _strict_text_list,
)
from .paa_provenance.receipt_validation import (
    _parse_utc_timestamp,
    _valid_answersocrates_receipt,
    _valid_raw_capture_binding,
)
from .paa_provenance.matching import (
    _artifact_workspace_root,
    _exact_match,
    _extract_artifact_section,
    _extract_brief_paa_questions,
    _file_sha256,
    _finding,
    _lines_outside_fences,
    _normalize_for_match,
    _parse_iso_date,
    _resolve_artifact_path,
    _resolved_file_sha256,
    _validate_question_match_keys,
)
from .paa_provenance.cli import _main, _record_main
from .paa_provenance.contracts import (
    ANSWERSOCRATES_ARTIFACT_SCHEMA,
    ANSWERSOCRATES_BLOCKER_PATTERNS,
    ANSWERSOCRATES_BLOCKER_SCOPES,
    ANSWERSOCRATES_BLOCKER_STATES,
    ANSWERSOCRATES_BROWSER_OUTPUT_FIELDS,
    ANSWERSOCRATES_CAPTURE_CONTRACTS,
    ANSWERSOCRATES_CHROME_CONNECTOR_RAW_CAPTURE_SCHEMA,
    ANSWERSOCRATES_CHROME_CONNECTOR_TOOL,
    ANSWERSOCRATES_CLOSE_TIMEOUT_SECONDS,
    ANSWERSOCRATES_OPEN_TIMEOUT_SECONDS,
    ANSWERSOCRATES_PAGE_URL,
    ANSWERSOCRATES_PAGE_URLS,
    ANSWERSOCRATES_RAW_CAPTURE_FIELDS,
    ANSWERSOCRATES_RAW_CAPTURE_PURPOSE,
    ANSWERSOCRATES_RAW_CAPTURE_SCHEMA,
    ANSWERSOCRATES_RAW_RESPONSE_FIELDS,
    ANSWERSOCRATES_RECEIPT_ATTESTATION_PURPOSE,
    ANSWERSOCRATES_RECEIPT_SCHEMA,
    ANSWERSOCRATES_RUN_TIMEOUT_SECONDS,
    ANSWERSOCRATES_TOOL,
    ANY_H2_RE,
    ARTIFACT_BLOCKER_RE,
    ARTIFACT_DATE_RE,
    ARTIFACT_QUERY_RE,
    ARTIFACT_RE,
    ARTIFACT_SOURCE_RE,
    ARTIFACT_STATUS_RE,
    BRIEF_PAA_HEADING_RE,
    BULLET_RE,
    ELIGIBLE_HEADING_RE,
    FENCE_OPEN_RE,
    FaqQuestion,
    INELIGIBLE_HEADING_RE,
    PRIMARY_SOURCE_KINDS,
    PROVENANCE_HEADING_RE,
    PaaProvenanceResult,
    ProvenanceBlock,
    QUESTION_LIST_ITEM_RE,
    QuestionArtifact,
    SELECTED_RE,
    SOURCE_RE,
    SUPPLEMENTAL_SOURCE_KINDS,
    WORKFLOW_MODES,
    _DuplicateBriefPaaSectionsError,
)

__all__ = [
    "ANSWERSOCRATES_ARTIFACT_SCHEMA",
    "ANSWERSOCRATES_BLOCKER_PATTERNS",
    "ANSWERSOCRATES_BLOCKER_SCOPES",
    "ANSWERSOCRATES_BLOCKER_STATES",
    "ANSWERSOCRATES_BROWSER_OUTPUT_FIELDS",
    "ANSWERSOCRATES_CAPTURE_CONTRACTS",
    "ANSWERSOCRATES_CHROME_CONNECTOR_RAW_CAPTURE_SCHEMA",
    "ANSWERSOCRATES_CHROME_CONNECTOR_TOOL",
    "ANSWERSOCRATES_CLOSE_TIMEOUT_SECONDS",
    "ANSWERSOCRATES_OPEN_TIMEOUT_SECONDS",
    "ANSWERSOCRATES_PAGE_URL",
    "ANSWERSOCRATES_PAGE_URLS",
    "ANSWERSOCRATES_RAW_CAPTURE_FIELDS",
    "ANSWERSOCRATES_RAW_CAPTURE_PURPOSE",
    "ANSWERSOCRATES_RAW_CAPTURE_SCHEMA",
    "ANSWERSOCRATES_RAW_RESPONSE_FIELDS",
    "ANSWERSOCRATES_RECEIPT_ATTESTATION_PURPOSE",
    "ANSWERSOCRATES_RECEIPT_SCHEMA",
    "ANSWERSOCRATES_RUN_TIMEOUT_SECONDS",
    "ANSWERSOCRATES_TOOL",
    "ANY_H2_RE",
    "ARTIFACT_BLOCKER_RE",
    "ARTIFACT_DATE_RE",
    "ARTIFACT_QUERY_RE",
    "ARTIFACT_RE",
    "ARTIFACT_SOURCE_RE",
    "ARTIFACT_STATUS_RE",
    "BRIEF_PAA_HEADING_RE",
    "BULLET_RE",
    "ELIGIBLE_HEADING_RE",
    "FENCE_OPEN_RE",
    "FaqQuestion",
    "INELIGIBLE_HEADING_RE",
    "PRIMARY_SOURCE_KINDS",
    "PROVENANCE_HEADING_RE",
    "PaaProvenanceResult",
    "PaaDependencies",
    "ProvenanceBlock",
    "QUESTION_LIST_ITEM_RE",
    "QuestionArtifact",
    "SELECTED_RE",
    "SOURCE_RE",
    "SUPPLEMENTAL_SOURCE_KINDS",
    "WORKFLOW_MODES",
    "_DuplicateBriefPaaSectionsError",
    "_answersocrates_blocker_finding",
    "_answersocrates_extraction_code",
    "_answersocrates_record_finding",
    "_artifact_workspace_root",
    "_derive_answersocrates_observations",
    "_exact_match",
    "_extract_artifact_section",
    "_extract_brief_paa_questions",
    "_extract_csv_questions",
    "_extract_faq_questions",
    "_extract_provenance_block",
    "_file_sha256",
    "_finding",
    "_lines_outside_fences",
    "_main",
    "_normalize_for_match",
    "_parse_iso_date",
    "_parse_question_artifact",
    "_parse_utc_timestamp",
    "_provenance_or_bound_artifact",
    "_record_main",
    "_resolve_artifact_path",
    "_resolved_file_sha256",
    "_strict_question_list",
    "_strict_text_list",
    "_valid_answersocrates_receipt",
    "_valid_raw_capture_binding",
    "_validate_question_match_keys",
    "_workflow_policy_finding",
    "build_answersocrates_artifact",
    "canonical_json_sha256",
    "check_content",
    "check_file",
    "collect_answersocrates_raw_capture",
    "evaluate_content",
    "evaluate_file",
    "find_npx_executable",
    "should_fail",
    "verify_mapping_attestation",
    "write_answersocrates_artifact",
]

if __name__ == "__main__":
    sys.exit(_main())
