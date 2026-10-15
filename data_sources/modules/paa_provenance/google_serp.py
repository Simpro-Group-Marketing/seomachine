"""Google SERP "People also ask" fallback for PAA provenance when AnswerSocrates is unavailable.

AnswerSocrates stays the first PAA source. When it shows a login, captcha, quota, or unavailability
state, the run may record the Google results page's "People also ask" questions instead. The capture
must carry that AnswerSocrates blocker (state, verbatim text, page URL, time), observed on the article
date before the Google capture, and the client that read both pages (``capture_client``). Provenance
caveat: the attestation proves this workspace wrote the record and that it is unchanged, not that
Google or AnswerSocrates served it; the observations and the client are self-declared, like the
other browser captures.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..capture_client import UNRECORDED, client_error
from ..editorial_plan.contracts import _rfc3339_utc
from ..execution_attestation import verify_mapping_attestation
from .contracts import ANSWERSOCRATES_BLOCKER_STATES, ANSWERSOCRATES_PAGE_URLS
from .matching import _artifact_workspace_root

GOOGLE_SERP_PAA_SCHEMA = "simpro-google-serp-paa-capture/v1"
GOOGLE_SERP_PAA_SOURCE_KIND = "google_serp_paa"
GOOGLE_SERP_PAA_COLLECTOR = {"name": "google_serp_chrome_connector", "version": "1.0.0"}
RELEASE_CHECK = "paa_google_serp_fallback"
BLOCKER_KEYS = frozenset({"state", "observed_text", "page_url", "observed_at"})
MAX_BLOCKER_TEXT = 500


def _load(path: Path, content: str | None) -> Any:
    try:
        return json.loads(content if content is not None else path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return None


def capture_client(payload: Mapping[str, Any]) -> str:
    """The client that recorded the capture, or ``unrecorded`` for one made before the field existed."""
    return str(payload.get("client") or UNRECORDED)


def is_google_serp_capture(path: Path) -> bool:
    """True when ``path`` holds a capture written by the Google SERP PAA recorder."""
    payload = _load(path, None)
    return isinstance(payload, Mapping) and payload.get("schema") == GOOGLE_SERP_PAA_SCHEMA


def blocker_error(blocker: Any, *, collection_date: str, collected_at: str) -> str:
    """Return why the recorded AnswerSocrates blocker is invalid, or an empty string."""
    if not isinstance(blocker, Mapping) or set(blocker) != BLOCKER_KEYS:
        return f"answersocrates_blocker must have exactly {sorted(BLOCKER_KEYS)}"
    if blocker["state"] not in ANSWERSOCRATES_BLOCKER_STATES:
        return f"answersocrates_blocker state must be one of {sorted(ANSWERSOCRATES_BLOCKER_STATES)}"
    text = blocker["observed_text"]
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_BLOCKER_TEXT:
        return f"answersocrates_blocker observed_text must be 1-{MAX_BLOCKER_TEXT} characters of page text"
    if blocker["page_url"] not in ANSWERSOCRATES_PAGE_URLS:
        return f"answersocrates_blocker page_url must be one of {sorted(ANSWERSOCRATES_PAGE_URLS)}"
    observed = _rfc3339_utc(str(blocker["observed_at"]))
    collected = _rfc3339_utc(collected_at)
    if observed is None or collected is None:
        return "answersocrates_blocker observed_at and collected_at must be RFC 3339 UTC times"
    if observed.date().isoformat() != collection_date or observed > collected:
        return "answersocrates_blocker must be observed on the collection date, before the Google capture"
    return ""


def _identity_errors(payload: Mapping[str, Any], expected: Mapping[str, str | None]) -> list[str]:
    receipt = payload.get("run_receipt") if isinstance(payload.get("run_receipt"), Mapping) else {}
    actual = {"query": payload.get("query"), "collection_date": payload.get("collection_date"),
              "run_id": receipt.get("run_id")}
    return [f"{key} {actual[key]!r} is not {value!r}" for key, value in expected.items() if value and actual[key] != value]


def _capture_error(path: Path, payload: Any, expected: Mapping[str, str | None]) -> str:
    if not isinstance(payload, Mapping) or payload.get("schema") != GOOGLE_SERP_PAA_SCHEMA:
        return f"not a {GOOGLE_SERP_PAA_SCHEMA} capture"
    if payload.get("collector") != GOOGLE_SERP_PAA_COLLECTOR:
        return "collector is not the Google SERP Chrome recorder"
    if "client" in payload and client_error(payload["client"]):  # absent on captures made before the field existed
        return client_error(payload["client"])
    if not verify_mapping_attestation(payload, purpose=GOOGLE_SERP_PAA_SCHEMA,
                                      workspace_root=_artifact_workspace_root(path)):
        return "execution attestation does not verify (edited or not written by the recorder)"
    errors = _identity_errors(payload, expected)
    if errors:
        return "; ".join(errors)
    questions = payload.get("eligible_questions")
    if not isinstance(questions, list) or not all(isinstance(q, str) and q.strip() for q in questions):
        return "eligible_questions must be a list of question text"
    return blocker_error(payload.get("answersocrates_blocker"), collection_date=str(payload.get("collection_date")),
                         collected_at=str(payload.get("collected_at")))


def google_serp_questions(
    path: Path,
    content: str | None,
    *,
    expected_query: str | None,
    expected_collection_date: str | None,
    expected_run_id: str | None,
) -> tuple[tuple[str, ...], Mapping[str, Any], str]:
    """Return the capture's questions, its AnswerSocrates blocker, and an empty error; or why it is invalid."""
    payload = _load(path, content)
    error = _capture_error(path, payload, {"query": expected_query, "collection_date": expected_collection_date,
                                           "run_id": expected_run_id})
    if error:
        return (), {}, error
    return tuple(payload["eligible_questions"]), dict(payload["answersocrates_blocker"]), ""


__all__ = [
    "GOOGLE_SERP_PAA_COLLECTOR",
    "GOOGLE_SERP_PAA_SCHEMA",
    "GOOGLE_SERP_PAA_SOURCE_KIND",
    "RELEASE_CHECK",
    "blocker_error",
    "capture_client",
    "google_serp_questions",
    "is_google_serp_capture",
]
