"""
PAA Provenance Guard

Deterministic guardrail for FAQ question provenance. It does not prove FAQ
answers; faq_proof_guard owns answer proof. This guard verifies that every FAQ
question in a draft appears in a saved, structured primary-source artifact.
"""

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List, Mapping, Optional

try:
    from .blog_assembly_contract import (
        atomic_write_json,
        canonical_json_sha256,
        canonical_snapshot_artifact,
        load_json_object_snapshot,
        resolve_artifact,
    )
    from .execution_attestation import attest_mapping, verify_mapping_attestation
    from .faq_structure import detect_faq_structure
    from .guard_common import Finding, should_fail, summarize_findings
    from .proof_sidecar import compose_with_sidecar, load_sidecar_content
except ImportError:  # pragma: no cover - supports direct script execution.
    from blog_assembly_contract import (
        atomic_write_json,
        canonical_json_sha256,
        canonical_snapshot_artifact,
        load_json_object_snapshot,
        resolve_artifact,
    )
    from execution_attestation import attest_mapping, verify_mapping_attestation
    from faq_structure import detect_faq_structure
    from guard_common import Finding, should_fail, summarize_findings
    from proof_sidecar import compose_with_sidecar, load_sidecar_content


PROVENANCE_HEADING_RE = re.compile(r"^(?:#{1,6}\s+)?PAA/FAQ Provenance\s*$", re.IGNORECASE)
SOURCE_RE = re.compile(r"^-\s*Source:\s*(.+?)\s*$", re.IGNORECASE)
ARTIFACT_RE = re.compile(r"^-\s*Artifact:\s*`?([^`\s]+)`?\s*$", re.IGNORECASE)
SELECTED_RE = re.compile(r"^-\s*Selected questions:\s*$", re.IGNORECASE)
BULLET_RE = re.compile(r"^\s*-\s+(.+?)\s*$")

PRIMARY_SOURCE_KINDS = frozenset({'answersocrates', 'brief_paa', 'user_csv'})
SUPPLEMENTAL_SOURCE_KINDS = frozenset({'serp', 'reddit', 'youtube'})
WORKFLOW_MODES = frozenset({'new', 'rewrite'})
ANSWERSOCRATES_BLOCKER_STATES = frozenset(
    {'login', 'captcha', 'quota', 'unavailability'}
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
ANSWERSOCRATES_RAW_CAPTURE_FIELDS = frozenset({
    "schema", "collector", "query", "run_id", "started_at", "completed_at",
    "page_url", "raw_response", "execution_attestation",
})
ANSWERSOCRATES_RAW_RESPONSE_FIELDS = frozenset({"stdout", "stderr", "returncode"})
ANSWERSOCRATES_BROWSER_OUTPUT_FIELDS = frozenset({
    "page_url", "page_title", "body_text", "sections", "blocker_observations",
})
ANSWERSOCRATES_BLOCKER_SCOPES = frozenset({
    "role_alert",
    "aria_live_assertive",
    "error_container",
    "authentication_gate",
    "captcha_container",
    "quota_container",
})
ANSWERSOCRATES_PAGE_URL = "https://answersocrates.com/paa-extractor"
ANSWERSOCRATES_PAGE_URLS = frozenset({
    ANSWERSOCRATES_PAGE_URL,
    "https://answersocrates.com/",
})
ANSWERSOCRATES_OPEN_TIMEOUT_SECONDS = 30
ANSWERSOCRATES_RUN_TIMEOUT_SECONDS = 90
ANSWERSOCRATES_CLOSE_TIMEOUT_SECONDS = 15
ANSWERSOCRATES_BLOCKER_PATTERNS = (
    ("login", re.compile(r"\b(?:log\s*in|sign\s*in|authentication required)\b", re.I)),
    ("captcha", re.compile(r"\b(?:captcha|not a robot|unusual traffic)\b", re.I)),
    ("quota", re.compile(r"\b(?:quota|free search|too many requests|rate limit)\b", re.I)),
    ("unavailability", re.compile(r"\b(?:unavailable|timeout(?:error)?|timed? out|failed|service error)\b", re.I)),
)
ELIGIBLE_HEADING_RE = re.compile(r'^##\s+Eligible Questions\s*$', re.IGNORECASE)
INELIGIBLE_HEADING_RE = re.compile(r'^##\s+Ineligible Fragments\s*$', re.IGNORECASE)
BRIEF_PAA_HEADING_RE = re.compile(r'^## Pre-picked PAA Questions$')
ANY_H2_RE = re.compile(r'^##\s+')
ARTIFACT_SOURCE_RE = re.compile(r'^Source kind:\s*(\S+)\s*$', re.IGNORECASE)
ARTIFACT_STATUS_RE = re.compile(r'^Status:\s*(\S+)\s*$', re.IGNORECASE)
ARTIFACT_QUERY_RE = re.compile(r'^Query:\s*(.+?)\s*$', re.IGNORECASE)
ARTIFACT_DATE_RE = re.compile(r'^Date:\s*(\S+)\s*$', re.IGNORECASE)
ARTIFACT_BLOCKER_RE = re.compile(r'^Blocker:\s*(.+?)\s*$', re.IGNORECASE)
QUESTION_LIST_ITEM_RE = re.compile(r'^\s*(?:[-*]|\d+[.)])\s+(.+?\?)\s*$')
FENCE_OPEN_RE = re.compile(r'^\s*(`{3,}|~{3,})')


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
    blocker: str = ''
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


def build_answersocrates_artifact(
    *,
    raw_capture_path: str | Path,
    workspace_root: str | Path,
    expected_query: str,
    expected_collection_date: str,
    expected_run_id: str,
) -> dict:
    """Derive a canonical record from one fixed-collector raw browser capture."""
    root = Path(workspace_root).resolve()
    if not isinstance(expected_query, str) or not expected_query.strip():
        raise ValueError("expected_query is required")
    if _parse_iso_date(str(expected_collection_date or "")) is None:
        raise ValueError("expected_collection_date is required as an ISO date")
    if not isinstance(expected_run_id, str) or not expected_run_id.strip():
        raise ValueError("expected_run_id is required")
    snapshot = load_json_object_snapshot(
        raw_capture_path,
        field="AnswerSocrates raw Playwright capture",
    )
    capture = snapshot.payload
    if set(capture) != ANSWERSOCRATES_RAW_CAPTURE_FIELDS:
        raise ValueError("AnswerSocrates raw capture shape is invalid")
    capture_contract = ANSWERSOCRATES_CAPTURE_CONTRACTS.get(capture.get("schema"))
    if capture_contract is None:
        raise ValueError("AnswerSocrates raw capture schema is invalid")
    expected_collector, capture_purpose = capture_contract
    if capture.get("collector") != expected_collector:
        raise ValueError("AnswerSocrates raw capture collector is not approved")
    if not verify_mapping_attestation(
        capture,
        purpose=capture_purpose,
        workspace_root=root,
    ):
        raise ValueError("AnswerSocrates raw capture attestation is invalid")
    query = capture.get("query")
    run_id = capture.get("run_id")
    page_url = capture.get("page_url")
    if not isinstance(query, str) or not query.strip() or query != query.strip():
        raise ValueError("AnswerSocrates raw capture query is invalid")
    if not isinstance(run_id, str) or not run_id.strip() or run_id != run_id.strip():
        raise ValueError("AnswerSocrates raw capture run_id is invalid")
    if page_url not in ANSWERSOCRATES_PAGE_URLS:
        raise ValueError("AnswerSocrates raw capture page URL is invalid")
    started_at = capture.get("started_at")
    completed_at = capture.get("completed_at")
    started = _parse_utc_timestamp(started_at)
    completed = _parse_utc_timestamp(completed_at)
    if started is None or completed is None or completed <= started:
        raise ValueError("AnswerSocrates raw capture timestamps are invalid")
    if completed > datetime.now(timezone.utc):
        raise ValueError("AnswerSocrates raw capture timestamp is in the future")
    collection_date = completed.date().isoformat()
    if query != str(expected_query).strip():
        raise ValueError("AnswerSocrates raw capture query does not match expectation")
    if run_id != str(expected_run_id).strip():
        raise ValueError("AnswerSocrates raw capture run_id does not match expectation")
    if (
        collection_date != str(expected_collection_date).strip()
    ):
        raise ValueError("AnswerSocrates raw capture date does not match expectation")
    questions, fragments, blocker_payload = _derive_answersocrates_observations(
        capture.get("raw_response")
    )
    status = "blocked" if blocker_payload is not None else "collected"
    raw_capture = canonical_snapshot_artifact(snapshot, workspace_root=root)
    payload = {
        "schema": ANSWERSOCRATES_ARTIFACT_SCHEMA,
        "source_kind": "answersocrates",
        "status": status,
        "query": query,
        "collection_date": collection_date,
        "eligible_question_section": "people_also_ask",
        "eligible_questions": questions,
        "ineligible_fragments": fragments,
        "blocker": blocker_payload,
        "raw_capture": raw_capture,
    }
    receipt = attest_mapping({
        "schema": ANSWERSOCRATES_RECEIPT_SCHEMA,
        "run_id": run_id,
        "tool": dict(expected_collector),
        "started_at": started_at,
        "completed_at": completed_at,
        "status": status,
        "payload_sha256": canonical_json_sha256(payload),
        "raw_capture": raw_capture,
    }, purpose=ANSWERSOCRATES_RECEIPT_ATTESTATION_PURPOSE)
    receipt["receipt_hash"] = canonical_json_sha256(receipt)
    return {**payload, "run_receipt": receipt}


def _derive_answersocrates_observations(
    raw_response: object,
) -> tuple[list[str], list[str], dict[str, str] | None]:
    if not isinstance(raw_response, Mapping) or set(raw_response) != ANSWERSOCRATES_RAW_RESPONSE_FIELDS:
        raise ValueError("AnswerSocrates raw visible response shape is invalid")
    stdout = raw_response.get("stdout")
    stderr = raw_response.get("stderr")
    returncode = raw_response.get("returncode")
    if not isinstance(stdout, str) or not isinstance(stderr, str):
        raise ValueError("AnswerSocrates raw stdout and stderr must be text")
    if not isinstance(returncode, int) or isinstance(returncode, bool):
        raise ValueError("AnswerSocrates raw returncode must be an integer")
    try:
        browser_output = json.loads(stdout) if stdout.strip() else None
    except json.JSONDecodeError:
        browser_output = None
    if browser_output is not None and (
        not isinstance(browser_output, Mapping)
        or set(browser_output) != ANSWERSOCRATES_BROWSER_OUTPUT_FIELDS
    ):
        raise ValueError("AnswerSocrates browser stdout shape is invalid")
    if isinstance(browser_output, Mapping):
        if browser_output.get("page_url") not in ANSWERSOCRATES_PAGE_URLS:
            raise ValueError("AnswerSocrates browser stdout page URL is invalid")
        if not isinstance(browser_output.get("page_title"), str):
            raise ValueError("AnswerSocrates browser stdout title is invalid")
        if not isinstance(browser_output.get("body_text"), str):
            raise ValueError("AnswerSocrates browser stdout body text is invalid")
    elif returncode == 0:
        raise ValueError("AnswerSocrates browser stdout is not valid JSON")

    scoped_blocker_texts: list[str] = []
    if isinstance(browser_output, Mapping):
        observations = browser_output.get("blocker_observations")
        if not isinstance(observations, list):
            raise ValueError("AnswerSocrates blocker observations must be a list")
        for observation in observations:
            if not isinstance(observation, Mapping) or set(observation) != {"scope", "text"}:
                raise ValueError("AnswerSocrates blocker observation shape is invalid")
            scope = observation.get("scope")
            text = observation.get("text")
            if scope not in ANSWERSOCRATES_BLOCKER_SCOPES:
                raise ValueError("AnswerSocrates blocker observation scope is invalid")
            if not isinstance(text, str) or not text.strip() or text != text.strip():
                raise ValueError("AnswerSocrates blocker observation text is invalid")
            scoped_blocker_texts.append(text)

    process_failure = "\n".join(filter(None, (
        stderr,
        stdout if browser_output is None else "",
    ))).strip()
    blocker_texts = (
        scoped_blocker_texts + ([process_failure] if process_failure else [])
        if returncode != 0
        else scoped_blocker_texts
    )
    blocker_payload = None
    matched_kinds: list[str] = []
    for blocker_text in blocker_texts:
        matches = [
            kind for kind, pattern in ANSWERSOCRATES_BLOCKER_PATTERNS
            if pattern.search(blocker_text)
        ]
        if len(matches) != 1:
            raise ValueError("AnswerSocrates blocker output does not map to one approved blocker")
        matched_kinds.append(matches[0])
    if returncode != 0 and not blocker_texts:
        raise ValueError("AnswerSocrates failed collector has no scoped blocker output")
    if matched_kinds:
        if len(set(matched_kinds)) != 1:
            raise ValueError("AnswerSocrates blocker output is ambiguous")
        blocker_payload = {
            "kind": matched_kinds[0],
            "reason": "\n".join(blocker_texts),
        }
    sections = browser_output.get("sections") if isinstance(browser_output, Mapping) else []
    if not isinstance(sections, list):
        raise ValueError("AnswerSocrates visible sections must be a list")
    eligible: list[str] = []
    ineligible: list[str] = []
    for section in sections:
        if not isinstance(section, Mapping) or set(section) != {"heading", "items"}:
            raise ValueError("AnswerSocrates visible section shape is invalid")
        heading = section.get("heading")
        items = section.get("items")
        if not isinstance(heading, str) or not isinstance(items, list):
            raise ValueError("AnswerSocrates visible section is invalid")
        paa_section = heading.strip().casefold() == "people also ask"
        for item in items:
            if not isinstance(item, str) or not item.strip() or item != item.strip():
                raise ValueError("AnswerSocrates visible items must be trimmed text")
            if paa_section and item.endswith("?"):
                eligible.append(item)
            else:
                ineligible.append(item)
    eligible = list(_strict_question_list(eligible, field="eligible_questions"))
    ineligible = list(_strict_text_list(ineligible, field="ineligible_fragments"))
    if blocker_payload is not None:
        eligible = []
    elif not eligible:
        raise ValueError("AnswerSocrates capture contains no eligible People Also Ask questions")
    return eligible, ineligible, blocker_payload


def find_npx_executable() -> str | None:
    """Return the fixed Playwright CLI launcher when installed."""
    return shutil.which("npx.cmd" if os.name == "nt" else "npx")


def _answersocrates_extraction_code(query: str) -> str:
    """Return fixed browser code that emits unclassified visible DOM facts."""
    return f"""async (page) => {{
  const clean = value => (value || '').replace(/\\s+/g, ' ').trim();
  await page.goto({json.dumps(ANSWERSOCRATES_PAGE_URL)}, {{ waitUntil: 'domcontentloaded' }});
  const input = page.locator('input[type="search"], input[type="text"], textarea').first();
  await input.fill({json.dumps(query)});
  const submit = page.getByRole('button', {{ name: /search|extract|submit|get questions/i }}).first();
  await submit.click();
  await page.waitForTimeout(3000);
  const observed = await page.evaluate(() => {{
    const clean = value => (value || '').replace(/\\s+/g, ' ').trim();
    const headings = Array.from(document.querySelectorAll('h1,h2,h3,[role="heading"]'));
    const sections = headings.map(heading => {{
      const container = heading.closest('section, article, div') || heading.parentElement;
      const items = container ? Array.from(container.querySelectorAll('li,button,[role="button"]'))
        .map(node => clean(node.innerText || node.textContent || node.getAttribute('aria-label')))
        .filter(Boolean) : [];
      return {{ heading: clean(heading.innerText || heading.textContent), items: Array.from(new Set(items)) }};
    }}).filter(section => section.heading);
    const blockerObservations = [];
    const observe = (scope, nodes) => nodes.forEach(node => {{
      const text = clean(node.innerText || node.textContent || node.getAttribute('aria-label') || node.getAttribute('title'));
      if (text) blockerObservations.push({{ scope, text }});
    }});
    observe('role_alert', Array.from(document.querySelectorAll('[role="alert"]')));
    observe('aria_live_assertive', Array.from(document.querySelectorAll('[aria-live="assertive"]')));
    observe('error_container', Array.from(document.querySelectorAll('[data-testid*="error" i], [data-error], .error-message, .alert-danger')));
    observe('captcha_container', Array.from(document.querySelectorAll('[data-testid*="captcha" i], .g-recaptcha, iframe[src*="recaptcha" i]')));
    observe('quota_container', Array.from(document.querySelectorAll('[data-testid*="quota" i], [data-quota-error]')));
    observe('authentication_gate', Array.from(document.querySelectorAll('main form')).filter(form => form.querySelector('input[type="password"]')));
    const seenBlockers = new Set();
    const uniqueBlockers = blockerObservations.filter(observation => {{
      const key = `${{observation.scope}}\u0000${{observation.text}}`;
      if (seenBlockers.has(key)) return false;
      seenBlockers.add(key);
      return true;
    }});
    return {{
      page_url: window.location.href,
      page_title: document.title,
      body_text: clean(document.body ? document.body.innerText : ''),
      sections,
      blocker_observations: uniqueBlockers,
    }};
  }});
  return JSON.stringify(observed);
}}"""


def collect_answersocrates_raw_capture(
    *,
    query: str,
    run_id: str,
    raw_capture_output: str | Path,
    workspace_root: str | Path,
) -> Path:
    """Run the fixed bounded collector and persist exact subprocess output."""
    root = Path(workspace_root).resolve()
    npx_path = find_npx_executable()
    started_at = datetime.now(timezone.utc)
    stdout = ""
    stderr = "npx unavailable; AnswerSocrates collector failed"
    returncode = 127
    if npx_path:
        prefix = [npx_path, "--yes", "--package", "@playwright/cli", "playwright-cli"]
        try:
            subprocess.run(
                prefix + ["open", "about:blank"],
                text=True, encoding="utf-8", stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, check=True,
                timeout=ANSWERSOCRATES_OPEN_TIMEOUT_SECONDS,
            )
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", suffix=".js", delete=False
            ) as handle:
                handle.write(_answersocrates_extraction_code(query))
                code_path = handle.name
            try:
                completed = subprocess.run(
                    prefix + ["run-code", "--filename", code_path, "--raw"],
                    text=True, encoding="utf-8", stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, check=False,
                    timeout=ANSWERSOCRATES_RUN_TIMEOUT_SECONDS,
                )
                stdout = completed.stdout
                stderr = completed.stderr
                returncode = completed.returncode
            finally:
                Path(code_path).unlink(missing_ok=True)
        except (subprocess.SubprocessError, OSError) as error:
            stderr = str(error)
            returncode = 1
        finally:
            try:
                subprocess.run(
                    prefix + ["close"], text=True, encoding="utf-8",
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    check=False, timeout=ANSWERSOCRATES_CLOSE_TIMEOUT_SECONDS,
                )
            except (subprocess.SubprocessError, OSError):
                pass
    completed_at = datetime.now(timezone.utc)
    if completed_at <= started_at:
        completed_at = started_at + timedelta(microseconds=1)
    payload = {
        "schema": ANSWERSOCRATES_RAW_CAPTURE_SCHEMA,
        "collector": dict(ANSWERSOCRATES_TOOL),
        "query": query,
        "run_id": run_id,
        "started_at": started_at.isoformat().replace("+00:00", "Z"),
        "completed_at": completed_at.isoformat().replace("+00:00", "Z"),
        "page_url": ANSWERSOCRATES_PAGE_URL,
        "raw_response": {
            "stdout": stdout,
            "stderr": stderr,
            "returncode": returncode,
        },
    }
    attested = attest_mapping(
        payload,
        purpose=ANSWERSOCRATES_RAW_CAPTURE_PURPOSE,
        workspace_root=root,
    )
    destination = Path(raw_capture_output)
    atomic_write_json(destination, attested)
    return destination


def write_answersocrates_artifact(
    path: str | Path,
    artifact: dict,
    *,
    workspace_root: str | Path,
) -> None:
    """Atomically persist an already validated AnswerSocrates run artifact."""
    parsed = _parse_question_artifact(json.dumps(artifact), workspace_root=workspace_root)
    if parsed is None or not parsed.run_receipt_valid:
        raise ValueError("AnswerSocrates artifact contract is invalid")
    atomic_write_json(path, artifact)


def check_content(
    content: str,
    source_path: Optional[str] = None,
    proof_content: Optional[str] = None,
    *,
    workflow_mode: str = "new",
    content_brief: Optional[str] = None,
    answersocrates_blocker: Optional[str] = None,
    expected_query: Optional[str] = None,
    expected_collection_date: Optional[str] = None,
    expected_run_id: Optional[str] = None,
    paa_artifact: Optional[str] = None,
) -> List[Finding]:
    """
    Check FAQ questions against a saved PAA/FAQ provenance artifact.

    Args:
        content: Markdown article or rewrite content.
        source_path: Optional markdown file path used to resolve relative artifact paths.
        proof_content: Optional validation-sidecar content.
        workflow_mode: Exact workflow mode: new or rewrite.
        content_brief: Bound content brief with a dedicated rewrite PAA section.
        answersocrates_blocker: Structured blocked-run record required
            when user_csv is the primary source.
        expected_query: Exact query expected in an AnswerSocrates record.
        expected_collection_date: Exact ISO date expected in an
            AnswerSocrates record.

    Returns:
        Structured findings for missing, invalid, or unsupported PAA provenance.
    """
    faq_structure = detect_faq_structure(content)
    if faq_structure.unsupported_lines:
        return [
            _finding(
                "paa_faq_structure_unsupported",
                faq_structure.unsupported_lines[0],
                None,
                "FAQ-like question markup uses an unsupported structure.",
                "Use a recognized FAQ H2 followed by H3-H5 question headings so provenance can be verified.",
            )
        ]
    faq_questions = _extract_faq_questions(content)
    if not faq_questions and not paa_artifact:
        if workflow_mode == "new":
            return [
                _finding(
                    "paa_new_answersocrates_required",
                    1,
                    None,
                    "A new blog requires a structured AnswerSocrates artifact even when no FAQ is selected.",
                    "Collect and bind the AnswerSocrates artifact, recording an empty selected-question decision when FAQ is not applicable.",
                )
            ]
        if workflow_mode == "rewrite":
            return [
                _finding(
                    "paa_rewrite_answersocrates_required",
                    1,
                    None,
                    "A rewrite without bound pre-picked brief PAA requires a structured AnswerSocrates artifact.",
                    "Bind the dedicated brief PAA artifact when it exists; otherwise collect and bind AnswerSocrates.",
                )
            ]
        return []

    proof_source = compose_with_sidecar(content, proof_content)
    provenance = _provenance_or_bound_artifact(
        proof_source,
        paa_artifact=paa_artifact,
        content_brief=content_brief,
    )
    if provenance is None:
        first = faq_questions[0]
        return [
            _finding(
                "paa_provenance_missing",
                first.line,
                first.question,
                "FAQ section exists, but no PAA/FAQ Provenance block was found.",
                (
                    "Add a PAA/FAQ Provenance block with Source, Artifact, and "
                    "Selected questions before scoring or publishing."
                ),
            )
        ]

    source_kind = provenance.source.strip()
    if source_kind in SUPPLEMENTAL_SOURCE_KINDS:
        return [
            _finding(
                "paa_supplemental_source_cannot_qualify",
                provenance.line,
                None,
                f"Supplemental PAA source cannot qualify as primary provenance: {source_kind}",
                "Use AnswerSocrates, dedicated brief PAA, or a blocker-backed user CSV.",
                match=source_kind,
            )
        ]

    if source_kind not in PRIMARY_SOURCE_KINDS:
        return [
            _finding(
                "paa_source_unsupported",
                provenance.line,
                None,
                f"PAA/FAQ source is not allowed: {provenance.source}",
                "Use the exact source kind answersocrates, brief_paa, or user_csv.",
                match=provenance.source,
            )
        ]

    if workflow_mode not in WORKFLOW_MODES:
        return [
            _finding(
                "paa_workflow_mode_invalid",
                provenance.line,
                None,
                f"PAA workflow mode is not supported: {workflow_mode}",
                "Use the exact workflow mode new or rewrite.",
                match=workflow_mode,
            )
        ]

    policy_finding = _workflow_policy_finding(
        workflow_mode=workflow_mode,
        source_kind=source_kind,
        provenance=provenance,
        source_path=source_path,
        content_brief=content_brief,
    )
    if policy_finding is not None:
        return [policy_finding]

    if not provenance.artifact:
        return [
            _finding(
                "paa_artifact_missing",
                provenance.line,
                None,
                "PAA/FAQ Provenance block does not include an Artifact path.",
                "Add an Artifact path that points to the saved PAA/FAQ source file.",
            )
        ]

    artifact_path = _resolve_artifact_path(provenance.artifact, source_path)
    if artifact_path is None or not artifact_path.is_file():
        return [
            _finding(
                "paa_artifact_missing",
                provenance.line,
                None,
                f"PAA/FAQ artifact does not resolve: {provenance.artifact}",
                "Save the source artifact and point Artifact to its repo-relative or absolute path.",
                match=provenance.artifact,
            )
        ]

    if faq_questions and not provenance.selected_questions:
        return [
            _finding(
                "paa_selected_questions_missing",
                provenance.line,
                None,
                "PAA/FAQ Provenance block does not list selected questions.",
                "Add each FAQ question under Selected questions in the provenance block.",
            )
        ]

    if source_kind == "user_csv":
        if artifact_path.suffix.lower() != ".csv":
            return [
                _finding(
                    "paa_user_csv_invalid",
                    provenance.line,
                    None,
                    "The user_csv primary artifact is not a .csv file.",
                    "Save the supplied questions as a CSV and reference that exact file.",
                    match=provenance.artifact,
                )
            ]

        blocker_finding = _answersocrates_blocker_finding(
            answersocrates_blocker,
            source_path=source_path,
            line=provenance.line,
            expected_query=expected_query,
            expected_collection_date=expected_collection_date,
            expected_run_id=expected_run_id,
        )
        if blocker_finding is not None:
            return [blocker_finding]

        try:
            eligible_questions = _extract_csv_questions(artifact_path)
        except (OSError, UnicodeError, csv.Error):
            eligible_questions = ()
        if not eligible_questions:
            return [
                _finding(
                    "paa_user_csv_invalid",
                    provenance.line,
                    None,
                    "The user CSV does not contain any complete question cells.",
                    "Add exact, complete questions ending in a question mark to the CSV.",
                    match=provenance.artifact,
                )
            ]
        ineligible_fragments: tuple[str, ...] = ()
    elif source_kind == "brief_paa":
        try:
            artifact_text = artifact_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return [
                _finding(
                    "paa_artifact_unreadable",
                    provenance.line,
                    None,
                    "The bound PAA artifact cannot be read as a UTF-8 file.",
                    "Restore a readable UTF-8 PAA artifact and rerun provenance validation.",
                    match=provenance.artifact,
                )
            ]
        try:
            brief_questions = _extract_brief_paa_questions(artifact_text)
        except _DuplicateBriefPaaSectionsError:
            return [
                _finding(
                    "paa_brief_sections_duplicate",
                    provenance.line,
                    None,
                    "The bound content brief contains duplicate visible Pre-picked PAA Questions sections.",
                    "Keep exactly one visible ## Pre-picked PAA Questions section in the rewrite brief.",
                    match=provenance.artifact,
                )
            ]
        if not brief_questions:
            return [
                _finding(
                    "paa_brief_questions_missing",
                    provenance.line,
                    None,
                    "The bound content brief has no dedicated Pre-picked PAA Questions.",
                    "Add complete questions under the exact ## Pre-picked PAA Questions heading.",
                    match=provenance.artifact,
                )
            ]
        eligible_questions = brief_questions
        ineligible_fragments = ()
    else:
        try:
            artifact_text = artifact_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return [
                _finding(
                    "paa_artifact_unreadable",
                    provenance.line,
                    None,
                    "The bound PAA artifact cannot be read as a UTF-8 file.",
                    "Restore a readable UTF-8 PAA artifact and rerun provenance validation.",
                    match=provenance.artifact,
                )
            ]
        artifact_record = _parse_question_artifact(
            artifact_text,
            workspace_root=_artifact_workspace_root(artifact_path),
        )
        record_finding = _answersocrates_record_finding(
            artifact_record,
            required_status="collected",
            expected_query=expected_query,
            expected_collection_date=expected_collection_date,
            expected_run_id=expected_run_id,
            line=provenance.line,
            artifact=provenance.artifact,
            require_eligible_section=True,
        )
        if record_finding is not None:
            return [record_finding]
        assert artifact_record is not None
        eligible_questions = artifact_record.eligible_questions
        ineligible_fragments = artifact_record.ineligible_fragments

    try:
        _validate_question_match_keys(
            provenance.selected_questions,
            field="selected questions",
        )
        _validate_question_match_keys(
            eligible_questions,
            field="eligible questions",
        )
        _validate_question_match_keys(
            (question.question for question in faq_questions),
            field="visible FAQ questions",
        )
    except ValueError as error:
        return [
            _finding(
                "paa_question_normalization_invalid",
                provenance.line,
                None,
                str(error),
                "Use distinct complete questions that retain a non-empty Unicode-aware match key.",
            )
        ]

    exact_match = source_kind == "brief_paa"
    match_key = _exact_match if exact_match else _normalize_for_match
    selected_normalized = {
        match_key(question) for question in provenance.selected_questions
    }
    eligible_normalized = {match_key(question) for question in eligible_questions}
    ineligible_normalized = {
        match_key(question) for question in ineligible_fragments
    }
    findings: List[Finding] = []

    for faq_question in faq_questions:
        normalized_question = match_key(faq_question.question)

        if normalized_question not in selected_normalized:
            findings.append(
                _finding(
                    "paa_question_missing_from_provenance",
                    faq_question.line,
                    faq_question.question,
                    "FAQ question is not listed in PAA/FAQ Provenance selected questions.",
                    "Add the exact FAQ question to Selected questions or remove it from the FAQ.",
                )
            )
            continue

        if normalized_question in ineligible_normalized:
            findings.append(
                _finding(
                    "paa_question_ineligible_fragment",
                    faq_question.line,
                    faq_question.question,
                    "FAQ question appears in the artifact's ineligible fragment section.",
                    "Use an exact complete question from ## Eligible Questions.",
                )
            )
            continue

        if normalized_question not in eligible_normalized:
            findings.append(
                _finding(
                    "paa_question_missing_from_artifact",
                    faq_question.line,
                    faq_question.question,
                    "FAQ question is not present in the saved PAA/FAQ artifact.",
                    "Use a question from the saved artifact or collect a new source artifact.",
                )
            )

    if source_kind == "brief_paa":
        visible_questions = {question.question for question in faq_questions}
        for brief_question in eligible_questions:
            if brief_question in visible_questions:
                continue
            findings.append(
                _finding(
                    "paa_brief_question_missing_from_faq",
                    provenance.line,
                    brief_question,
                    "A pre-picked content-brief PAA question is not an exact visible FAQ heading.",
                    "Use every pre-picked question verbatim as a visible FAQ heading.",
                )
            )

    return findings


def evaluate_content(
    content: str,
    source_path: Optional[str] = None,
    proof_content: Optional[str] = None,
    *,
    workflow_mode: str = "new",
    content_brief: Optional[str] = None,
    answersocrates_blocker: Optional[str] = None,
    expected_query: Optional[str] = None,
    expected_collection_date: Optional[str] = None,
    expected_run_id: Optional[str] = None,
    paa_artifact: Optional[str] = None,
) -> PaaProvenanceResult:
    """Return reusable PAA provenance state and findings for article content."""
    faq_questions = tuple(
        question.question for question in _extract_faq_questions(content)
    )
    proof_source = compose_with_sidecar(content, proof_content)
    provenance = _provenance_or_bound_artifact(
        proof_source,
        paa_artifact=paa_artifact,
        content_brief=content_brief,
    )
    source_kind = provenance.source.strip() if provenance is not None else ""
    artifact = provenance.artifact if provenance is not None else ""
    selected_questions = (
        tuple(provenance.selected_questions) if provenance is not None else ()
    )
    artifact_sha256 = ""
    artifact_questions: tuple[str, ...] = ()
    artifact_query = ""
    artifact_collection_date = ""
    artifact_path = _resolve_artifact_path(artifact, source_path) if artifact else None
    if artifact_path is not None and artifact_path.is_file():
        try:
            artifact_sha256 = _file_sha256(artifact_path)
            if source_kind == "user_csv":
                artifact_questions = _extract_csv_questions(artifact_path)
            else:
                artifact_text = artifact_path.read_text(encoding="utf-8")
                if source_kind == "brief_paa":
                    artifact_questions = (
                        _extract_brief_paa_questions(artifact_text) or ()
                    )
                elif source_kind == "answersocrates":
                    artifact_record = _parse_question_artifact(
                        artifact_text,
                        workspace_root=_artifact_workspace_root(artifact_path),
                    )
                    if artifact_record is not None:
                        artifact_questions = artifact_record.eligible_questions
                        artifact_query = artifact_record.query
                        artifact_collection_date = artifact_record.collection_date
        except (
            OSError,
            UnicodeError,
            csv.Error,
            _DuplicateBriefPaaSectionsError,
        ):
            artifact_questions = ()

    findings = check_content(
        content,
        source_path=source_path,
        proof_content=proof_content,
        workflow_mode=workflow_mode,
        content_brief=content_brief,
        answersocrates_blocker=answersocrates_blocker,
        expected_query=expected_query,
        expected_collection_date=expected_collection_date,
        expected_run_id=expected_run_id,
        paa_artifact=paa_artifact,
    )
    return PaaProvenanceResult(
        workflow_mode=workflow_mode,
        source_kind=source_kind,
        artifact=artifact,
        artifact_sha256=artifact_sha256,
        artifact_questions=artifact_questions,
        artifact_query=artifact_query,
        artifact_collection_date=artifact_collection_date,
        content_brief=str(content_brief or ""),
        content_brief_sha256=_resolved_file_sha256(content_brief, source_path),
        answersocrates_blocker=str(answersocrates_blocker or ""),
        answersocrates_blocker_sha256=_resolved_file_sha256(
            answersocrates_blocker,
            source_path,
        ),
        expected_query=str(expected_query or ""),
        expected_collection_date=str(expected_collection_date or ""),
        expected_run_id=str(expected_run_id or ""),
        faq_questions=faq_questions,
        selected_questions=selected_questions,
        findings=tuple(findings),
    )


def evaluate_file(
    path: str,
    fail_on: str = "error",
    proof_sidecar: Optional[str] = None,
    *,
    workflow_mode: str = "new",
    content_brief: Optional[str] = None,
    answersocrates_blocker: Optional[str] = None,
    expected_query: Optional[str] = None,
    expected_collection_date: Optional[str] = None,
    expected_run_id: Optional[str] = None,
    paa_artifact: Optional[str] = None,
) -> PaaProvenanceResult:
    """Return reusable PAA provenance state and findings for a Markdown file."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")

    content = Path(path).read_text(encoding="utf-8")
    proof_content = load_sidecar_content(path, proof_sidecar)
    result = evaluate_content(
        content,
        source_path=path,
        proof_content=proof_content,
        workflow_mode=workflow_mode,
        content_brief=content_brief,
        answersocrates_blocker=answersocrates_blocker,
        expected_query=expected_query,
        expected_collection_date=expected_collection_date,
        expected_run_id=expected_run_id,
        paa_artifact=paa_artifact,
    )
    if paa_artifact:
        expected_path = Path(paa_artifact).resolve()
        actual_path = _resolve_artifact_path(result.artifact, path)
        mismatch = actual_path is None or actual_path.resolve() != expected_path
        artifact_hash_unreadable = False
        try:
            hash_mismatch = bool(
                expected_path.is_file()
                and result.artifact_sha256
                and _file_sha256(expected_path) != result.artifact_sha256
            )
        except OSError:
            artifact_hash_unreadable = True
            hash_mismatch = False
        extra: list[Finding] = []
        if mismatch:
            extra.append(
                _finding(
                    "paa_artifact_binding_mismatch",
                    1,
                    None,
                    "PAA provenance does not reference the exact BOM-bound artifact.",
                    "Regenerate provenance from the exact bound PAA artifact.",
                )
            )
        elif artifact_hash_unreadable:
            extra.append(
                _finding(
                    "paa_artifact_unreadable",
                    1,
                    None,
                    "The BOM-bound PAA artifact disappeared during validation.",
                    "Restore the exact artifact and rerun PAA provenance validation.",
                    match=str(paa_artifact),
                )
            )
        elif hash_mismatch:
            extra.append(
                _finding(
                    "paa_artifact_hash_mismatch",
                    1,
                    None,
                    "The BOM-bound PAA artifact changed after provenance was recorded.",
                    "Regenerate the PAA binding from current artifact bytes.",
                )
            )
        if extra:
            result = replace(result, findings=tuple([*result.findings, *extra]))
    return result


def check_file(
    path: str,
    fail_on: str = "error",
    proof_sidecar: Optional[str] = None,
    *,
    workflow_mode: str = "new",
    content_brief: Optional[str] = None,
    answersocrates_blocker: Optional[str] = None,
    expected_query: Optional[str] = None,
    expected_collection_date: Optional[str] = None,
    expected_run_id: Optional[str] = None,
    paa_artifact: Optional[str] = None,
) -> List[Finding]:
    """
    Check a Markdown file for FAQ/PAA provenance.

    Args:
        path: Markdown file path.
        fail_on: Included for CLI/API symmetry.

    Returns:
        Structured findings.
    """
    result = evaluate_file(
        path,
        fail_on=fail_on,
        proof_sidecar=proof_sidecar,
        workflow_mode=workflow_mode,
        content_brief=content_brief,
        answersocrates_blocker=answersocrates_blocker,
        expected_query=expected_query,
        expected_collection_date=expected_collection_date,
        expected_run_id=expected_run_id,
        paa_artifact=paa_artifact,
    )
    return list(result.findings)


def _extract_faq_questions(content: str) -> List[FaqQuestion]:
    return [
        FaqQuestion(question=entry.question, line=entry.line)
        for entry in detect_faq_structure(content).entries
    ]


def _extract_provenance_block(content: str) -> Optional[ProvenanceBlock]:
    lines = content.splitlines()

    for index, line in enumerate(lines):
        if not PROVENANCE_HEADING_RE.match(line.strip()):
            continue

        source = ""
        artifact = ""
        selected_questions: List[str] = []
        in_selected_questions = False

        for block_line in lines[index + 1 :]:
            stripped = block_line.strip()
            if not stripped:
                if in_selected_questions:
                    break
                continue
            if stripped.startswith("```"):
                break
            if stripped.startswith("#"):
                break
            if PROVENANCE_HEADING_RE.match(stripped):
                break

            source_match = SOURCE_RE.match(stripped)
            if source_match:
                source = source_match.group(1).strip()
                in_selected_questions = False
                continue

            artifact_match = ARTIFACT_RE.match(stripped)
            if artifact_match:
                artifact = artifact_match.group(1).strip()
                in_selected_questions = False
                continue

            if SELECTED_RE.match(stripped):
                in_selected_questions = True
                continue

            if in_selected_questions:
                bullet_match = BULLET_RE.match(block_line)
                if bullet_match:
                    selected_questions.append(bullet_match.group(1).strip())
                else:
                    break

        return ProvenanceBlock(
            source=source,
            artifact=artifact,
            selected_questions=selected_questions,
            line=index + 1,
        )

    return None


def _provenance_or_bound_artifact(
    content: str,
    *,
    paa_artifact: Optional[str],
    content_brief: Optional[str],
) -> Optional[ProvenanceBlock]:
    provenance = _extract_provenance_block(content)
    if provenance is not None or not paa_artifact:
        return provenance
    artifact_path = Path(paa_artifact)
    source_kind = "answersocrates"
    if artifact_path.suffix.casefold() == ".csv":
        source_kind = "user_csv"
    elif content_brief:
        try:
            if artifact_path.resolve() == Path(content_brief).resolve():
                source_kind = "brief_paa"
        except OSError:
            pass
    return ProvenanceBlock(
        source=source_kind,
        artifact=str(paa_artifact),
        selected_questions=[
            question.question for question in _extract_faq_questions(content)
        ],
        line=1,
    )


def _workflow_policy_finding(
    *,
    workflow_mode: str,
    source_kind: str,
    provenance: ProvenanceBlock,
    source_path: Optional[str],
    content_brief: Optional[str],
) -> Optional[Finding]:
    if workflow_mode == "new" and source_kind == "brief_paa":
        return _finding(
            "paa_new_answersocrates_required",
            provenance.line,
            None,
            "A new blog cannot use dedicated brief PAA as its primary source.",
            "Collect structured AnswerSocrates questions or document its blocker before using user_csv.",
            match=source_kind,
        )

    if workflow_mode != "rewrite":
        return None

    if not content_brief:
        if source_kind == "brief_paa":
            return _finding(
                "paa_rewrite_answersocrates_required",
                provenance.line,
                None,
                "This rewrite has no bound content brief with dedicated PAA questions.",
                "Use structured AnswerSocrates questions or a blocker-backed user CSV.",
                match=source_kind,
            )
        return None

    provenance_path = _resolve_artifact_path(provenance.artifact, source_path)
    brief_path = _resolve_artifact_path(str(content_brief), source_path)
    if brief_path is None or not brief_path.is_file():
        return _finding(
            "paa_content_brief_unreadable",
            provenance.line,
            None,
            "The bound rewrite content brief cannot be read.",
            "Bind the current readable content brief before evaluating PAA precedence.",
            match=str(content_brief),
        )
    try:
        pre_picked_questions = _extract_brief_paa_questions(
            brief_path.read_text(encoding="utf-8")
        )
    except _DuplicateBriefPaaSectionsError:
        return _finding(
            "paa_brief_sections_duplicate",
            provenance.line,
            None,
            "The bound content brief contains duplicate visible Pre-picked PAA Questions sections.",
            "Keep exactly one visible ## Pre-picked PAA Questions section in the rewrite brief.",
            match=str(content_brief),
        )
    except (OSError, UnicodeError):
        return _finding(
            "paa_content_brief_unreadable",
            provenance.line,
            None,
            "The bound rewrite content brief cannot be read as UTF-8.",
            "Save a valid UTF-8 content brief before evaluating PAA precedence.",
            match=str(content_brief),
        )
    if not pre_picked_questions:
        if source_kind == "brief_paa":
            return _finding(
                "paa_rewrite_answersocrates_required",
                provenance.line,
                None,
                "The rewrite brief does not contain non-empty pre-picked PAA questions.",
                "Use structured AnswerSocrates questions or a blocker-backed user CSV.",
                match=source_kind,
            )
        return None
    if (
        source_kind != "brief_paa"
        or provenance_path is None
        or brief_path is None
        or provenance_path.resolve() != brief_path.resolve()
    ):
        return _finding(
            "paa_rewrite_brief_precedence_violation",
            provenance.line,
            None,
            "A rewrite with pre-picked brief PAA must use the bound content brief as primary provenance.",
            "Set Source to brief_paa and Artifact to the supplied content brief file.",
            match=source_kind,
        )
    return None


def _answersocrates_blocker_finding(
    blocker_artifact: Optional[str],
    *,
    source_path: Optional[str],
    line: int,
    expected_query: Optional[str],
    expected_collection_date: Optional[str],
    expected_run_id: Optional[str],
) -> Optional[Finding]:
    if not blocker_artifact:
        return _finding(
            "paa_user_csv_blocker_missing",
            line,
            None,
            "user_csv is allowed only when a structured AnswerSocrates blocker artifact is supplied.",
            "Supply the blocked AnswerSocrates artifact with Source kind, Status, and Blocker fields.",
        )

    blocker_path = _resolve_artifact_path(str(blocker_artifact), source_path)
    if blocker_path is None or not blocker_path.exists():
        return _finding(
            "paa_user_csv_blocker_missing",
            line,
            None,
            f"AnswerSocrates blocker artifact does not resolve: {blocker_artifact}",
            "Save the blocked AnswerSocrates record and supply its path.",
            match=str(blocker_artifact),
        )

    try:
        blocker_record = _parse_question_artifact(
            blocker_path.read_text(encoding="utf-8"),
            workspace_root=_artifact_workspace_root(blocker_path),
        )
    except (OSError, UnicodeError):
        blocker_record = None
    return _answersocrates_record_finding(
        blocker_record,
        required_status="blocked",
        expected_query=expected_query,
        expected_collection_date=expected_collection_date,
        expected_run_id=expected_run_id,
        line=line,
        artifact=str(blocker_artifact),
        require_eligible_section=False,
        invalid_rule="paa_answersocrates_blocker_invalid",
    )


def _answersocrates_record_finding(
    record: Optional[QuestionArtifact],
    *,
    required_status: str,
    expected_query: Optional[str],
    expected_collection_date: Optional[str],
    expected_run_id: Optional[str],
    line: int,
    artifact: str,
    require_eligible_section: bool,
    invalid_rule: str = "paa_answersocrates_artifact_unstructured",
) -> Optional[Finding]:
    invalid = (
        record is None
        or record.source_kind != "answersocrates"
        or record.status != required_status
        or not record.query
        or _parse_iso_date(record.collection_date) is None
        or (require_eligible_section and not record.eligible_section_present)
        or not record.run_receipt_valid
        or (
            required_status == "blocked"
            and record.blocker.casefold() not in ANSWERSOCRATES_BLOCKER_STATES
        )
    )
    if invalid:
        return _finding(
            invalid_rule,
            line,
            None,
            f"The AnswerSocrates artifact is not a structured {required_status} record.",
            (
                "Use the receipt-bound simpro-answersocrates-artifact/v1 JSON contract"
                + (
                    " with an eligible People Also Ask question section."
                    if require_eligible_section
                    else (
                        " with an exact blocker state and non-empty reason: login, "
                        "captcha, quota, or unavailability."
                    )
                )
            ),
            match=artifact,
        )

    expected_date = _parse_iso_date(str(expected_collection_date or ""))
    if (
        not str(expected_query or "").strip()
        or expected_date is None
        or not str(expected_run_id or "").strip()
    ):
        return _finding(
            "paa_answersocrates_expectation_missing",
            line,
            None,
            "AnswerSocrates validation requires expected query, collection date, and canonical run ID.",
            "Pass expected_query, expected_collection_date, and expected_run_id from the bound plan and BOM.",
            match=artifact,
        )

    assert record is not None
    if record.query != str(expected_query).strip():
        return _finding(
            "paa_answersocrates_query_mismatch",
            line,
            None,
            "AnswerSocrates artifact query does not match the bound expected query.",
            "Recollect with the bound query or supply the matching artifact.",
            match=record.query,
        )

    if record.run_id != str(expected_run_id).strip():
        return _finding(
            "paa_answersocrates_run_mismatch",
            line,
            None,
            "AnswerSocrates artifact run ID does not match the canonical article run.",
            "Recollect within the current article assembly run.",
            match=record.run_id,
        )

    if record.collection_date != expected_date.isoformat():
        return _finding(
            "paa_answersocrates_date_mismatch",
            line,
            None,
            "AnswerSocrates artifact date does not match the expected collection date.",
            "Collect a current artifact for the bound assembly date.",
            match=record.collection_date,
        )
    return None


def _extract_csv_questions(path: Path) -> tuple[str, ...]:
    questions: List[str] = []
    seen = set()
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        for row in csv.reader(csv_file):
            for cell in row:
                question = cell.strip()
                if not question.endswith("?") or question in seen:
                    continue
                questions.append(question)
                seen.add(question)
    return tuple(questions)


def _parse_question_artifact(
    content: str,
    *,
    workspace_root: str | Path | None = None,
) -> Optional[QuestionArtifact]:
    try:
        value = json.loads(content)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or set(value) != {
        "schema",
        "source_kind",
        "status",
        "query",
        "collection_date",
        "eligible_question_section",
        "eligible_questions",
        "ineligible_fragments",
        "blocker",
        "raw_capture",
        "run_receipt",
    }:
        return None
    status = value.get("status")
    blocker_value = value.get("blocker")
    blocker = ""
    blocker_valid = blocker_value is None
    if status == "blocked" and isinstance(blocker_value, dict):
        blocker_valid = set(blocker_value) == {"kind", "reason"}
        blocker_kind = blocker_value.get("kind")
        blocker_reason = blocker_value.get("reason")
        blocker_valid = bool(
            blocker_valid
            and isinstance(blocker_kind, str)
            and blocker_kind.casefold() in ANSWERSOCRATES_BLOCKER_STATES
            and isinstance(blocker_reason, str)
            and blocker_reason.strip()
        )
        if blocker_valid:
            blocker = str(blocker_kind).casefold()
    try:
        eligible = _strict_question_list(
            value.get("eligible_questions"),
            field="eligible_questions",
        )
        ineligible = _strict_text_list(
            value.get("ineligible_fragments"),
            field="ineligible_fragments",
        )
    except ValueError:
        return None
    payload = {
        key: value[key]
        for key in (
            "schema",
            "source_kind",
            "status",
            "query",
            "collection_date",
            "eligible_question_section",
            "eligible_questions",
            "ineligible_fragments",
            "blocker",
            "raw_capture",
        )
    }
    receipt = value.get("run_receipt")
    raw_capture = value.get("raw_capture")
    raw_capture_valid = _valid_raw_capture_binding(
        raw_capture,
        workspace_root=workspace_root,
        expected_query=value.get("query"),
        expected_run_id=(receipt.get("run_id") if isinstance(receipt, Mapping) else None),
        expected_collection_date=value.get("collection_date"),
        expected_questions=value.get("eligible_questions"),
        expected_fragments=value.get("ineligible_fragments"),
        expected_blocker=value.get("blocker"),
    )
    receipt_valid = _valid_answersocrates_receipt(receipt, payload=payload)
    structural = bool(
        value.get("schema") == ANSWERSOCRATES_ARTIFACT_SCHEMA
        and value.get("source_kind") == "answersocrates"
        and status in {"collected", "blocked"}
        and isinstance(value.get("query"), str)
        and str(value.get("query")).strip() == value.get("query")
        and _parse_iso_date(str(value.get("collection_date") or "")) is not None
        and value.get("eligible_question_section") == "people_also_ask"
        and blocker_valid
        and (status != "blocked" or not eligible)
        and (status != "collected" or blocker_value is None)
        and raw_capture_valid
    )
    if not structural:
        return None
    return QuestionArtifact(
        source_kind="answersocrates",
        status=str(status),
        query=str(value["query"]),
        collection_date=str(value["collection_date"]),
        run_id=str(receipt.get("run_id") if isinstance(receipt, Mapping) else ""),
        eligible_questions=eligible,
        ineligible_fragments=ineligible,
        eligible_section_present=True,
        blocker=blocker,
        run_receipt_valid=receipt_valid,
    )


def _valid_answersocrates_receipt(value: object, *, payload: dict) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "schema",
        "run_id",
        "tool",
        "started_at",
        "completed_at",
        "status",
        "payload_sha256",
        "raw_capture",
        "execution_attestation",
        "receipt_hash",
    }:
        return False
    tool = value.get("tool")
    if tool not in (
        ANSWERSOCRATES_TOOL,
        ANSWERSOCRATES_CHROME_CONNECTOR_TOOL,
    ):
        return False
    started = _parse_utc_timestamp(value.get("started_at"))
    completed = _parse_utc_timestamp(value.get("completed_at"))
    if started is None or completed is None or completed <= started:
        return False
    if (
        value.get("schema") != ANSWERSOCRATES_RECEIPT_SCHEMA
        or not isinstance(value.get("run_id"), str)
        or not str(value.get("run_id")).strip()
        or value.get("status") != payload.get("status")
        or value.get("payload_sha256") != canonical_json_sha256(payload)
        or value.get("raw_capture") != payload.get("raw_capture")
    ):
        return False
    receipt_without_hash = dict(value)
    stored_hash = receipt_without_hash.pop("receipt_hash", None)
    hash_valid = (
        isinstance(stored_hash, str)
        and re.fullmatch(r"[0-9a-f]{64}", stored_hash) is not None
        and stored_hash == canonical_json_sha256(receipt_without_hash)
    )
    return hash_valid and verify_mapping_attestation(
        value,
        purpose=ANSWERSOCRATES_RECEIPT_ATTESTATION_PURPOSE,
        excluded_fields=("receipt_hash",),
    )


def _valid_raw_capture_binding(
    binding: object,
    *,
    workspace_root: str | Path | None,
    expected_query: object,
    expected_run_id: object,
    expected_collection_date: object,
    expected_questions: object,
    expected_fragments: object,
    expected_blocker: object,
) -> bool:
    if workspace_root is None:
        return isinstance(binding, Mapping) and set(binding) == {"path", "sha256"}
    if not isinstance(binding, Mapping) or set(binding) != {"path", "sha256"}:
        return False
    try:
        path = resolve_artifact(binding.get("path"), workspace_root=workspace_root)
        snapshot = load_json_object_snapshot(path, field="AnswerSocrates raw capture")
    except ValueError:
        return False
    if snapshot.sha256 != binding.get("sha256"):
        return False
    capture = snapshot.payload
    capture_contract = ANSWERSOCRATES_CAPTURE_CONTRACTS.get(capture.get("schema"))
    if capture_contract is None:
        return False
    expected_collector, capture_purpose = capture_contract
    if (
        set(capture) != ANSWERSOCRATES_RAW_CAPTURE_FIELDS
        or capture.get("collector") != expected_collector
        or capture.get("query") != expected_query
        or capture.get("run_id") != expected_run_id
        or not verify_mapping_attestation(
            capture,
            purpose=capture_purpose,
            workspace_root=workspace_root,
        )
    ):
        return False
    completed = _parse_utc_timestamp(capture.get("completed_at"))
    started = _parse_utc_timestamp(capture.get("started_at"))
    if (
        started is None
        or completed is None
        or completed <= started
        or completed > datetime.now(timezone.utc)
        or completed.date().isoformat() != expected_collection_date
    ):
        return False
    try:
        questions, fragments, blocker = _derive_answersocrates_observations(
            capture.get("raw_response")
        )
    except ValueError:
        return False
    return (
        questions == expected_questions
        and fragments == expected_fragments
        and blocker == expected_blocker
    )


def _strict_question_list(value: object, *, field: str) -> tuple[str, ...]:
    items = _strict_text_list(value, field=field)
    if any(not item.endswith("?") for item in items):
        raise ValueError(f"{field} entries must be complete questions")
    _validate_question_match_keys(items, field=field)
    return items


def _strict_text_list(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be a list")
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip() or item != item.strip():
            raise ValueError(f"{field} entries must be non-empty trimmed strings")
        key = item.casefold()
        if key in seen:
            raise ValueError(f"{field} cannot contain duplicates")
        seen.add(key)
        normalized.append(item)
    return tuple(normalized)


def _parse_utc_timestamp(value: object) -> Optional[datetime]:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        return None
    return parsed


def _extract_brief_paa_questions(content: str) -> Optional[tuple[str, ...]]:
    return _extract_artifact_section(
        _lines_outside_fences(content.splitlines()),
        BRIEF_PAA_HEADING_RE,
    )


def _extract_artifact_section(
    lines: List[str],
    heading_re: re.Pattern[str],
) -> Optional[tuple[str, ...]]:
    heading_indexes = [
        index
        for index, line in enumerate(lines)
        if heading_re.fullmatch(line.strip())
    ]
    if not heading_indexes:
        return None
    if len(heading_indexes) > 1:
        raise _DuplicateBriefPaaSectionsError(
            "content brief contains duplicate visible dedicated PAA sections"
        )
    start = heading_indexes[0] + 1

    questions: List[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if ANY_H2_RE.match(stripped):
            break
        match = QUESTION_LIST_ITEM_RE.match(stripped)
        if match:
            questions.append(match.group(1).strip())
    return tuple(questions)


def _lines_outside_fences(lines: List[str]) -> List[str]:
    """Return visible Markdown lines while preserving section order."""
    visible: List[str] = []
    fence_character = ""
    fence_length = 0
    for line in lines:
        if fence_character:
            closing = line.strip()
            if (
                closing
                and set(closing) == {fence_character}
                and len(closing) >= fence_length
            ):
                fence_character = ""
                fence_length = 0
            continue
        match = FENCE_OPEN_RE.match(line)
        if match is not None:
            marker = match.group(1)
            fence_character = marker[0]
            fence_length = len(marker)
            continue
        visible.append(line)
    return visible


def _resolve_artifact_path(artifact: str, source_path: Optional[str]) -> Optional[Path]:
    artifact_path = Path(artifact)
    if artifact_path.is_absolute():
        return artifact_path

    candidates = [Path.cwd() / artifact_path]

    if source_path:
        source = Path(source_path).resolve()
        candidates.append(source.parent / artifact_path)
        candidates.append(source.parent.parent / artifact_path)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0] if candidates else None


def _resolved_file_sha256(
    artifact: Optional[str],
    source_path: Optional[str],
) -> str:
    if not artifact:
        return ""
    path = _resolve_artifact_path(str(artifact), source_path)
    if path is None or not path.is_file():
        return ""
    try:
        return _file_sha256(path)
    except OSError:
        return ""


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_iso_date(value: str) -> Optional[date]:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.isoformat() == value else None


def _artifact_workspace_root(path: Path) -> Path:
    """Resolve the workspace root for conventional research-bound artifacts."""
    resolved = path.resolve()
    for parent in resolved.parents:
        if parent.name == "research":
            return parent.parent
    return resolved.parent


def _exact_match(text: str) -> str:
    return text.strip()


def _normalize_for_match(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(
        "".join(character if character.isalnum() else " " for character in normalized).split()
    )


def _validate_question_match_keys(
    questions,
    *,
    field: str,
) -> None:
    """Reject empty or ambiguous Unicode-aware question identities."""
    seen: dict[str, str] = {}
    for question in questions:
        key = _normalize_for_match(question)
        if not key:
            raise ValueError(
                f"{field} contains a question with an empty normalization key"
            )
        previous = seen.get(key)
        if previous is not None:
            raise ValueError(
                f"{field} contains questions that collide after normalization"
            )
        seen[key] = question


def _finding(
    rule_id: str,
    line: int,
    question: Optional[str],
    message: str,
    suggestion: str,
    match: Optional[str] = None,
) -> Finding:
    finding: Finding = {
        "rule_id": rule_id,
        "severity": "error",
        "line": line,
        "column": 1,
        "message": message,
        "suggestion": suggestion,
    }
    if question is not None:
        finding["question"] = question
    if match is not None:
        finding["match"] = match
    return finding


def _main(argv: Optional[List[str]] = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if raw_argv and raw_argv[0] == "record":
        return _record_main(raw_argv[1:])
    parser = argparse.ArgumentParser(description="Check FAQ questions for PAA provenance.")
    parser.add_argument("path", help="Markdown file to check")
    parser.add_argument(
        "--fail-on",
        default="error",
        choices=["error", "warning", "none"],
        help="Minimum finding severity that returns exit code 1",
    )
    parser.add_argument(
        "--proof-sidecar",
        help="Optional validation sidecar containing PAA/FAQ provenance.",
    )
    parser.add_argument(
        "--workflow-mode",
        default="new",
        choices=sorted(WORKFLOW_MODES),
        help="PAA source policy to apply.",
    )
    parser.add_argument(
        "--paa-artifact",
        help="Exact BOM-bound AnswerSocrates, brief, or user CSV artifact.",
    )
    parser.add_argument(
        "--content-brief",
        help="Bound content brief; its pre-picked PAA takes precedence for rewrites.",
    )
    parser.add_argument(
        "--answersocrates-blocker",
        help="Structured blocked AnswerSocrates run required for user_csv fallback.",
    )
    parser.add_argument(
        "--expected-query",
        help="Exact query required in a structured AnswerSocrates artifact.",
    )
    parser.add_argument(
        "--expected-collection-date",
        help="Exact ISO date required in a structured AnswerSocrates artifact.",
    )
    parser.add_argument(
        "--expected-run-id",
        help="Canonical article run ID required in a structured AnswerSocrates artifact.",
    )
    args = parser.parse_args(raw_argv)

    result = evaluate_file(
        args.path,
        fail_on=args.fail_on,
        proof_sidecar=args.proof_sidecar,
        workflow_mode=args.workflow_mode,
        content_brief=args.content_brief,
        answersocrates_blocker=args.answersocrates_blocker,
        expected_query=args.expected_query,
        expected_collection_date=args.expected_collection_date,
        expected_run_id=args.expected_run_id,
        paa_artifact=args.paa_artifact,
    )
    findings = list(result.findings)
    payload = {
        "path": args.path,
        "fail_on": args.fail_on,
        "summary": summarize_findings(findings),
        "findings": findings,
        "result": result.to_dict(),
    }
    print(json.dumps(payload, indent=2))
    return 1 if should_fail(findings, fail_on=args.fail_on) else 0


def _record_main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Record one browser-collected AnswerSocrates run."
    )
    parser.add_argument("--query", required=True)
    parser.add_argument("--collection-date", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--raw-capture-output", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    capture_path = collect_answersocrates_raw_capture(
        query=args.query,
        run_id=args.run_id,
        raw_capture_output=args.raw_capture_output,
        workspace_root=args.workspace_root,
    )
    artifact = build_answersocrates_artifact(
        raw_capture_path=capture_path,
        workspace_root=args.workspace_root,
        expected_query=args.query,
        expected_collection_date=args.collection_date,
        expected_run_id=args.run_id,
    )
    write_answersocrates_artifact(
        args.output,
        artifact,
        workspace_root=args.workspace_root,
    )
    print(
        json.dumps(
            {
                "schema": ANSWERSOCRATES_ARTIFACT_SCHEMA,
                "status": artifact["status"],
                "output": str(Path(args.output)),
                "receipt_hash": artifact["run_receipt"]["receipt_hash"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(_main())
