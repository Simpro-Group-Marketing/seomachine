"""AnswerSocrates raw-response observation derivation."""

from __future__ import annotations

import json
from typing import Any, Mapping

from .contracts import (
    ANSWERSOCRATES_BLOCKER_PATTERNS,
    ANSWERSOCRATES_BLOCKER_SCOPES,
    ANSWERSOCRATES_BROWSER_OUTPUT_FIELDS,
    ANSWERSOCRATES_PAGE_URLS,
    ANSWERSOCRATES_RAW_RESPONSE_FIELDS,
)
from .lists import _strict_question_list, _strict_text_list


def _derive_answersocrates_observations(
    raw_response: object,
) -> tuple[list[str], list[str], dict[str, str] | None]:
    """Derive eligible questions and an approved blocker from captured output."""
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


__all__ = ["_derive_answersocrates_observations"]
