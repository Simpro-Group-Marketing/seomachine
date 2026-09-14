"""PAA provenance schemas, constants, and immutable result contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from ..guard_common import Finding

PROVENANCE_HEADING_RE = re.compile(
    r"^(?:#{1,6}\s+)?PAA/FAQ Provenance\s*$", re.IGNORECASE
)

SOURCE_RE = re.compile(r"^-\s*Source:\s*(.+?)\s*$", re.IGNORECASE)

ARTIFACT_RE = re.compile(r"^-\s*Artifact:\s*`?([^`\s]+)`?\s*$", re.IGNORECASE)

SELECTED_RE = re.compile(r"^-\s*Selected questions:\s*$", re.IGNORECASE)

BULLET_RE = re.compile(r"^\s*-\s+(.+?)\s*$")

PRIMARY_SOURCE_KINDS = frozenset({"answersocrates", "brief_paa", "user_csv"})

SUPPLEMENTAL_SOURCE_KINDS = frozenset({"serp", "reddit", "youtube"})

WORKFLOW_MODES = frozenset({"new", "rewrite"})

ANSWERSOCRATES_BLOCKER_STATES = frozenset(
    {"login", "captcha", "quota", "unavailability"}
)

ANSWERSOCRATES_ARTIFACT_SCHEMA = "simpro-answersocrates-artifact/v1"

ANSWERSOCRATES_RECEIPT_SCHEMA = "simpro-answersocrates-run-receipt/v1"

ANSWERSOCRATES_RECEIPT_ATTESTATION_PURPOSE = ANSWERSOCRATES_RECEIPT_SCHEMA

ANSWERSOCRATES_TOOL = {
    "name": "answersocrates_playwright_collector",
    "version": "1.0.0",
}

ANSWERSOCRATES_CHROME_CONNECTOR_TOOL = {
    "name": "answersocrates_chrome_connector",
    "version": "1.0.0",
}

ANSWERSOCRATES_RAW_CAPTURE_SCHEMA = "simpro-answersocrates-playwright-capture/v1"

ANSWERSOCRATES_RAW_CAPTURE_PURPOSE = ANSWERSOCRATES_RAW_CAPTURE_SCHEMA

ANSWERSOCRATES_CHROME_CONNECTOR_RAW_CAPTURE_SCHEMA = (
    "simpro-answersocrates-chrome-connector-capture/v1"
)

ANSWERSOCRATES_CAPTURE_CONTRACTS = {
    ANSWERSOCRATES_RAW_CAPTURE_SCHEMA: (
        ANSWERSOCRATES_TOOL,
        ANSWERSOCRATES_RAW_CAPTURE_PURPOSE,
    ),
    ANSWERSOCRATES_CHROME_CONNECTOR_RAW_CAPTURE_SCHEMA: (
        ANSWERSOCRATES_CHROME_CONNECTOR_TOOL,
        ANSWERSOCRATES_CHROME_CONNECTOR_RAW_CAPTURE_SCHEMA,
    ),
}

ANSWERSOCRATES_RAW_CAPTURE_FIELDS = frozenset(
    {
        "schema",
        "collector",
        "query",
        "run_id",
        "started_at",
        "completed_at",
        "page_url",
        "raw_response",
        "execution_attestation",
    }
)

ANSWERSOCRATES_RAW_RESPONSE_FIELDS = frozenset({"stdout", "stderr", "returncode"})

ANSWERSOCRATES_BROWSER_OUTPUT_FIELDS = frozenset(
    {
        "page_url",
        "page_title",
        "body_text",
        "sections",
        "blocker_observations",
    }
)

ANSWERSOCRATES_BLOCKER_SCOPES = frozenset(
    {
        "role_alert",
        "aria_live_assertive",
        "error_container",
        "authentication_gate",
        "captcha_container",
        "quota_container",
    }
)

ANSWERSOCRATES_PAGE_URL = "https://answersocrates.com/paa-extractor"

ANSWERSOCRATES_PAGE_URLS = frozenset(
    {
        ANSWERSOCRATES_PAGE_URL,
        "https://answersocrates.com/",
    }
)

ANSWERSOCRATES_OPEN_TIMEOUT_SECONDS = 30

ANSWERSOCRATES_RUN_TIMEOUT_SECONDS = 90

ANSWERSOCRATES_CLOSE_TIMEOUT_SECONDS = 15

ANSWERSOCRATES_BLOCKER_PATTERNS = (
    ("login", re.compile(r"\b(?:log\s*in|sign\s*in|authentication required)\b", re.I)),
    ("captcha", re.compile(r"\b(?:captcha|not a robot|unusual traffic)\b", re.I)),
    (
        "quota",
        re.compile(r"\b(?:quota|free search|too many requests|rate limit)\b", re.I),
    ),
    (
        "unavailability",
        re.compile(
            r"\b(?:unavailable|timeout(?:error)?|timed? out|failed|service error)\b",
            re.I,
        ),
    ),
)

ELIGIBLE_HEADING_RE = re.compile(r"^##\s+Eligible Questions\s*$", re.IGNORECASE)

INELIGIBLE_HEADING_RE = re.compile(r"^##\s+Ineligible Fragments\s*$", re.IGNORECASE)

BRIEF_PAA_HEADING_RE = re.compile(r"^## Pre-picked PAA Questions$")

ANY_H2_RE = re.compile(r"^##\s+")

ARTIFACT_SOURCE_RE = re.compile(r"^Source kind:\s*(\S+)\s*$", re.IGNORECASE)

ARTIFACT_STATUS_RE = re.compile(r"^Status:\s*(\S+)\s*$", re.IGNORECASE)

ARTIFACT_QUERY_RE = re.compile(r"^Query:\s*(.+?)\s*$", re.IGNORECASE)

ARTIFACT_DATE_RE = re.compile(r"^Date:\s*(\S+)\s*$", re.IGNORECASE)

ARTIFACT_BLOCKER_RE = re.compile(r"^Blocker:\s*(.+?)\s*$", re.IGNORECASE)

QUESTION_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(.+?\?)\s*$")

FENCE_OPEN_RE = re.compile(r"^\s*(`{3,}|~{3,})")


@dataclass
class FaqQuestion:
    question: str
    line: int


@dataclass
class ProvenanceBlock:
    source: str
    artifact: str
    selected_questions: List[str]
    line: int


@dataclass(frozen=True)
class QuestionArtifact:
    source_kind: str
    status: str
    query: str
    collection_date: str
    run_id: str
    eligible_questions: tuple[str, ...]
    ineligible_fragments: tuple[str, ...]
    eligible_section_present: bool
    blocker: str = ""
    run_receipt_valid: bool = False


@dataclass(frozen=True)
class PaaProvenanceResult:
    workflow_mode: str
    source_kind: str
    artifact: str
    artifact_sha256: str
    artifact_questions: tuple[str, ...]
    artifact_query: str
    artifact_collection_date: str
    content_brief: str
    content_brief_sha256: str
    answersocrates_blocker: str
    answersocrates_blocker_sha256: str
    expected_query: str
    expected_collection_date: str
    expected_run_id: str
    faq_questions: tuple[str, ...]
    selected_questions: tuple[str, ...]
    findings: tuple[Finding, ...]

    @property
    def passed(self) -> bool:
        return not self.findings

    def to_dict(self) -> dict:
        return {
            "workflow_mode": self.workflow_mode,
            "source_kind": self.source_kind,
            "artifact": self.artifact,
            "artifact_sha256": self.artifact_sha256,
            "artifact_questions": list(self.artifact_questions),
            "artifact_query": self.artifact_query,
            "artifact_collection_date": self.artifact_collection_date,
            "content_brief": self.content_brief,
            "content_brief_sha256": self.content_brief_sha256,
            "answersocrates_blocker": self.answersocrates_blocker,
            "answersocrates_blocker_sha256": self.answersocrates_blocker_sha256,
            "expected_query": self.expected_query,
            "expected_collection_date": self.expected_collection_date,
            "expected_run_id": self.expected_run_id,
            "faq_questions": list(self.faq_questions),
            "selected_questions": list(self.selected_questions),
            "passed": self.passed,
            "findings": [dict(finding) for finding in self.findings],
        }


class _DuplicateBriefPaaSectionsError(ValueError):
    """Raised when a brief contains more than one visible dedicated PAA section."""


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
    "ProvenanceBlock",
    "QUESTION_LIST_ITEM_RE",
    "QuestionArtifact",
    "SELECTED_RE",
    "SOURCE_RE",
    "SUPPLEMENTAL_SOURCE_KINDS",
    "WORKFLOW_MODES",
    "_DuplicateBriefPaaSectionsError",
]
