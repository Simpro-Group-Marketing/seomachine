"""PAA provenance collection responsibilities."""

from __future__ import annotations

# ruff: noqa: F401
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

from ..blog_assembly_contract import (
    atomic_write_json,
    canonical_json_sha256,
    canonical_snapshot_artifact,
    load_json_object_snapshot,
    resolve_artifact,
)
from ..artifact_runtime.subprocesses import run_bounded_text_process
from ..execution_attestation import attest_mapping, verify_mapping_attestation
from ..faq_structure import detect_faq_structure
from ..guard_common import Finding, should_fail, summarize_findings
from ..proof_sidecar import compose_with_sidecar, load_sidecar_content
from . import snapshot_validation as paa_provenance_snapshot
from .dependencies import PaaDependencies

from .contracts import (
    ANSWERSOCRATES_ARTIFACT_SCHEMA,
    ANSWERSOCRATES_BLOCKER_PATTERNS,
    ANSWERSOCRATES_BLOCKER_SCOPES,
    ANSWERSOCRATES_BROWSER_OUTPUT_FIELDS,
    ANSWERSOCRATES_CAPTURE_CONTRACTS,
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
)


def _derive_answersocrates_observations(
    raw_response: object,
) -> tuple[list[str], list[str], dict[str, str] | None]:
    """Derive eligible questions and an approved blocker from captured output."""
    from .artifact import _strict_question_list, _strict_text_list

    browser_output, stdout, stderr, returncode = _raw_response_parts(raw_response)
    blocker_texts = _blocker_texts(browser_output, stdout, stderr, returncode)
    blocker_payload = _blocker_payload(blocker_texts, returncode)
    eligible, ineligible = _section_questions(browser_output)
    eligible = list(_strict_question_list(eligible, field="eligible_questions"))
    ineligible = list(_strict_text_list(ineligible, field="ineligible_fragments"))
    if blocker_payload is not None:
        eligible = []
    elif not eligible:
        raise ValueError(
            "AnswerSocrates capture contains no eligible People Also Ask questions"
        )
    return eligible, ineligible, blocker_payload


def _raw_response_parts(
    raw_response: object,
) -> tuple[Mapping[str, Any] | None, str, str, int]:
    if (
        not isinstance(raw_response, Mapping)
        or set(raw_response) != ANSWERSOCRATES_RAW_RESPONSE_FIELDS
    ):
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
    validated = _validate_browser_output(browser_output, returncode=returncode)
    return validated, stdout, stderr, returncode


def _validate_browser_output(
    value: object,
    *,
    returncode: int,
) -> Mapping[str, Any] | None:
    if value is None:
        if returncode == 0:
            raise ValueError("AnswerSocrates browser stdout is not valid JSON")
        return None
    if (
        not isinstance(value, Mapping)
        or set(value) != ANSWERSOCRATES_BROWSER_OUTPUT_FIELDS
    ):
        raise ValueError("AnswerSocrates browser stdout shape is invalid")
    if value.get("page_url") not in ANSWERSOCRATES_PAGE_URLS:
        raise ValueError("AnswerSocrates browser stdout page URL is invalid")
    if not isinstance(value.get("page_title"), str):
        raise ValueError("AnswerSocrates browser stdout title is invalid")
    if not isinstance(value.get("body_text"), str):
        raise ValueError("AnswerSocrates browser stdout body text is invalid")
    return value


def _blocker_texts(
    browser_output: Mapping[str, Any] | None,
    stdout: str,
    stderr: str,
    returncode: int,
) -> list[str]:
    scoped_blocker_texts: list[str] = []
    if isinstance(browser_output, Mapping):
        observations = browser_output.get("blocker_observations")
        if not isinstance(observations, list):
            raise ValueError("AnswerSocrates blocker observations must be a list")
        for observation in observations:
            if not isinstance(observation, Mapping) or set(observation) != {
                "scope",
                "text",
            }:
                raise ValueError("AnswerSocrates blocker observation shape is invalid")
            scope = observation.get("scope")
            text = observation.get("text")
            if scope not in ANSWERSOCRATES_BLOCKER_SCOPES:
                raise ValueError("AnswerSocrates blocker observation scope is invalid")
            if not isinstance(text, str) or not text.strip() or text != text.strip():
                raise ValueError("AnswerSocrates blocker observation text is invalid")
            scoped_blocker_texts.append(text)
    process_failure = "\n".join(
        filter(None, (stderr, stdout if browser_output is None else ""))
    ).strip()
    return (
        scoped_blocker_texts + ([process_failure] if process_failure else [])
        if returncode != 0
        else scoped_blocker_texts
    )


def _blocker_payload(
    blocker_texts: list[str],
    returncode: int,
) -> dict[str, str] | None:
    matched_kinds: list[str] = []
    for blocker_text in blocker_texts:
        matches = [
            kind
            for kind, pattern in ANSWERSOCRATES_BLOCKER_PATTERNS
            if pattern.search(blocker_text)
        ]
        if len(matches) != 1:
            raise ValueError(
                "AnswerSocrates blocker output does not map to one approved blocker"
            )
        matched_kinds.append(matches[0])
    if returncode != 0 and (not blocker_texts):
        raise ValueError("AnswerSocrates failed collector has no scoped blocker output")
    if matched_kinds:
        if len(set(matched_kinds)) != 1:
            raise ValueError("AnswerSocrates blocker output is ambiguous")
        return {"kind": matched_kinds[0], "reason": "\n".join(blocker_texts)}
    return None


def _section_questions(
    browser_output: Mapping[str, Any] | None,
) -> tuple[list[str], list[str]]:
    sections = (
        browser_output.get("sections") if isinstance(browser_output, Mapping) else []
    )
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
        paa_section = heading.strip().casefold() in {
            "people also ask",
            "people also asked",
        }
        for item in items:
            if not isinstance(item, str) or not item.strip() or item != item.strip():
                raise ValueError("AnswerSocrates visible items must be trimmed text")
            if paa_section and item.endswith("?"):
                eligible.append(item)
            else:
                ineligible.append(item)
    return eligible, ineligible


def build_answersocrates_artifact(
    *,
    raw_capture_path: str | Path,
    workspace_root: str | Path,
    expected_query: str,
    expected_collection_date: str,
    expected_run_id: str,
) -> dict:
    """Derive a canonical record from one fixed-collector raw browser capture."""
    from .artifact import _parse_utc_timestamp
    from .matching import _parse_iso_date

    root = Path(workspace_root).resolve()
    _validate_build_expectations(
        expected_query, expected_collection_date, expected_run_id, _parse_iso_date
    )
    snapshot = load_json_object_snapshot(
        raw_capture_path, field="AnswerSocrates raw Playwright capture"
    )
    capture = snapshot.payload
    expected_collector, capture_purpose = _capture_contract(capture)
    if not verify_mapping_attestation(
        capture, purpose=capture_purpose, workspace_root=root
    ):
        raise ValueError("AnswerSocrates raw capture attestation is invalid")
    query, run_id = _capture_identity(capture)
    started_at, completed_at, collection_date = _capture_timing(
        capture, _parse_utc_timestamp
    )
    _validate_capture_expectations(
        query,
        run_id,
        collection_date,
        expected_query,
        expected_run_id,
        expected_collection_date,
    )
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
    receipt = attest_mapping(
        {
            "schema": ANSWERSOCRATES_RECEIPT_SCHEMA,
            "run_id": run_id,
            "tool": dict(expected_collector),
            "started_at": started_at,
            "completed_at": completed_at,
            "status": status,
            "payload_sha256": canonical_json_sha256(payload),
            "raw_capture": raw_capture,
        },
        purpose=ANSWERSOCRATES_RECEIPT_ATTESTATION_PURPOSE,
    )
    receipt["receipt_hash"] = canonical_json_sha256(receipt)
    return {**payload, "run_receipt": receipt}


def _validate_build_expectations(
    query: object,
    collection_date: object,
    run_id: object,
    parse_date: Any,
) -> None:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("expected_query is required")
    if parse_date(str(collection_date or "")) is None:
        raise ValueError("expected_collection_date is required as an ISO date")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("expected_run_id is required")


def _capture_contract(capture: Mapping[str, Any]) -> tuple[Mapping[str, str], str]:
    if set(capture) != ANSWERSOCRATES_RAW_CAPTURE_FIELDS:
        raise ValueError("AnswerSocrates raw capture shape is invalid")
    capture_contract = ANSWERSOCRATES_CAPTURE_CONTRACTS.get(capture.get("schema"))
    if capture_contract is None:
        raise ValueError("AnswerSocrates raw capture schema is invalid")
    expected_collector, capture_purpose = capture_contract
    if capture.get("collector") != expected_collector:
        raise ValueError("AnswerSocrates raw capture collector is not approved")
    return expected_collector, capture_purpose


def _capture_identity(capture: Mapping[str, Any]) -> tuple[str, str]:
    query = capture.get("query")
    run_id = capture.get("run_id")
    page_url = capture.get("page_url")
    if not isinstance(query, str) or not query.strip() or query != query.strip():
        raise ValueError("AnswerSocrates raw capture query is invalid")
    if not isinstance(run_id, str) or not run_id.strip() or run_id != run_id.strip():
        raise ValueError("AnswerSocrates raw capture run_id is invalid")
    if page_url not in ANSWERSOCRATES_PAGE_URLS:
        raise ValueError("AnswerSocrates raw capture page URL is invalid")
    return query, run_id


def _capture_timing(
    capture: Mapping[str, Any], parse_timestamp: Any
) -> tuple[str, str, str]:
    started_at = capture.get("started_at")
    completed_at = capture.get("completed_at")
    started = parse_timestamp(started_at)
    completed = parse_timestamp(completed_at)
    if started is None or completed is None or completed <= started:
        raise ValueError("AnswerSocrates raw capture timestamps are invalid")
    if completed > datetime.now(timezone.utc):
        raise ValueError("AnswerSocrates raw capture timestamp is in the future")
    return str(started_at), str(completed_at), completed.date().isoformat()


def _validate_capture_expectations(
    query: str,
    run_id: str,
    collection_date: str,
    expected_query: str,
    expected_run_id: str,
    expected_collection_date: str,
) -> None:
    if query != str(expected_query).strip():
        raise ValueError("AnswerSocrates raw capture query does not match expectation")
    if run_id != str(expected_run_id).strip():
        raise ValueError("AnswerSocrates raw capture run_id does not match expectation")
    if collection_date != str(expected_collection_date).strip():
        raise ValueError("AnswerSocrates raw capture date does not match expectation")


def write_answersocrates_artifact(
    path: str | Path, artifact: dict, *, workspace_root: str | Path
) -> None:
    """Atomically persist an already validated AnswerSocrates run artifact."""
    from .artifact import _parse_question_artifact

    parsed = _parse_question_artifact(
        json.dumps(artifact), workspace_root=workspace_root
    )
    if parsed is None or not parsed.run_receipt_valid:
        raise ValueError("AnswerSocrates artifact contract is invalid")
    atomic_write_json(path, artifact)


def find_npx_executable() -> str | None:
    """Return the fixed Playwright CLI launcher when installed."""
    return shutil.which("npx.cmd" if os.name == "nt" else "npx")


def default_dependencies() -> PaaDependencies:
    """Return production collection dependencies."""
    return PaaDependencies(
        executable_resolver=find_npx_executable,
        subprocess_runner=run_bounded_text_process,
    )


def _answersocrates_extraction_code(query: str) -> str:
    """Return fixed browser code that emits unclassified visible DOM facts."""
    return f"""async (page) => {{\n  const clean = value => (value || '').replace(/\\s+/g, ' ').trim();\n  await page.goto({json.dumps(ANSWERSOCRATES_PAGE_URL)}, {{ waitUntil: 'domcontentloaded' }});\n  const input = page.locator('input[type="search"], input[type="text"], textarea').first();\n  await input.fill({json.dumps(query)});\n  const submit = page.getByRole('button', {{ name: /search|extract|submit|get questions/i }}).first();\n  await submit.click();\n  await page.waitForTimeout(3000);\n  const observed = await page.evaluate(() => {{\n    const clean = value => (value || '').replace(/\\s+/g, ' ').trim();\n    const headings = Array.from(document.querySelectorAll('h1,h2,h3,[role="heading"]'));\n    const sections = headings.map(heading => {{\n      const container = heading.closest('section, article, div') || heading.parentElement;\n      const items = container ? Array.from(container.querySelectorAll('li,button,[role="button"]'))\n        .map(node => clean(node.innerText || node.textContent || node.getAttribute('aria-label')))\n        .filter(Boolean) : [];\n      return {{ heading: clean(heading.innerText || heading.textContent), items: Array.from(new Set(items)) }};\n    }}).filter(section => section.heading);\n    const blockerObservations = [];\n    const observe = (scope, nodes) => nodes.forEach(node => {{\n      const text = clean(node.innerText || node.textContent || node.getAttribute('aria-label') || node.getAttribute('title'));\n      if (text) blockerObservations.push({{ scope, text }});\n    }});\n    observe('role_alert', Array.from(document.querySelectorAll('[role="alert"]')));\n    observe('aria_live_assertive', Array.from(document.querySelectorAll('[aria-live="assertive"]')));\n    observe('error_container', Array.from(document.querySelectorAll('[data-testid*="error" i], [data-error], .error-message, .alert-danger')));\n    observe('captcha_container', Array.from(document.querySelectorAll('[data-testid*="captcha" i], .g-recaptcha, iframe[src*="recaptcha" i]')));\n    observe('quota_container', Array.from(document.querySelectorAll('[data-testid*="quota" i], [data-quota-error]')));\n    observe('authentication_gate', Array.from(document.querySelectorAll('main form')).filter(form => form.querySelector('input[type="password"]')));\n    const seenBlockers = new Set();\n    const uniqueBlockers = blockerObservations.filter(observation => {{\n      const key = `${{observation.scope}}\x00${{observation.text}}`;\n      if (seenBlockers.has(key)) return false;\n      seenBlockers.add(key);\n      return true;\n    }});\n    return {{\n      page_url: window.location.href,\n      page_title: document.title,\n      body_text: clean(document.body ? document.body.innerText : ''),\n      sections,\n      blocker_observations: uniqueBlockers,\n    }};\n  }});\n  return JSON.stringify(observed);\n}}"""


def collect_answersocrates_raw_capture(
    *,
    query: str,
    run_id: str,
    raw_capture_output: str | Path,
    workspace_root: str | Path,
    dependencies: PaaDependencies | None = None,
) -> Path:
    """Run the fixed bounded collector and persist exact subprocess output."""
    root = Path(workspace_root).resolve()
    active = dependencies or default_dependencies()
    npx_path = active.executable_resolver()
    run_process = active.subprocess_runner
    started_at = datetime.now(timezone.utc)
    stdout = ""
    stderr = "npx unavailable; AnswerSocrates collector failed"
    returncode = 127
    if npx_path:
        prefix = [npx_path, "--yes", "--package", "@playwright/cli", "playwright-cli"]
        try:
            opened = run_process(
                prefix + ["open", "about:blank"],
                encoding="utf-8",
                errors="replace",
                timeout=ANSWERSOCRATES_OPEN_TIMEOUT_SECONDS,
                max_output_bytes=1024 * 1024,
            )
            if opened.returncode != 0:
                raise RuntimeError((opened.stderr or opened.stdout).strip())
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", suffix=".js", delete=False
            ) as handle:
                handle.write(_answersocrates_extraction_code(query))
                code_path = handle.name
            try:
                completed = run_process(
                    prefix + ["run-code", "--filename", code_path, "--raw"],
                    encoding="utf-8",
                    errors="replace",
                    timeout=ANSWERSOCRATES_RUN_TIMEOUT_SECONDS,
                    max_output_bytes=8 * 1024 * 1024,
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
                run_process(
                    prefix + ["close"],
                    encoding="utf-8",
                    errors="replace",
                    timeout=ANSWERSOCRATES_CLOSE_TIMEOUT_SECONDS,
                    max_output_bytes=1024 * 1024,
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
        "raw_response": {"stdout": stdout, "stderr": stderr, "returncode": returncode},
    }
    attested = attest_mapping(
        payload, purpose=ANSWERSOCRATES_RAW_CAPTURE_PURPOSE, workspace_root=root
    )
    destination = Path(raw_capture_output)
    atomic_write_json(destination, attested)
    return destination


__all__ = [
    "_derive_answersocrates_observations",
    "build_answersocrates_artifact",
    "write_answersocrates_artifact",
    "find_npx_executable",
    "default_dependencies",
    "_answersocrates_extraction_code",
    "collect_answersocrates_raw_capture",
]
