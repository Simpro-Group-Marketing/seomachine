"""Bound research artifacts for the production BOM: parse the bytes that get hashed."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from data_sources.modules.blog_assembly_contract import canonical_artifact
from data_sources.modules.production.bom import SpecFileError
from data_sources.modules.production.layout import Layout

_SHORTLIST_KEYS = ("primary", "secondary", "candidates", "decision_rule")
_COVERAGE_KEYS = ("query", "topics", "uncovered_questions")


def squash(text: str) -> str:
    return " ".join(text.casefold().split())


def relative(layout: Layout, path: Path) -> str:
    return path.relative_to(layout.root).as_posix()


def _bind_bytes(layout: Layout, path: Path, raw: bytes) -> dict[str, str]:
    binding = canonical_artifact(path, workspace_root=layout.root)
    if binding["sha256"] != hashlib.sha256(raw).hexdigest():
        raise ValueError(f"artifact changed while the BOM was built: {relative(layout, path)}")
    return binding


def read_bound(
    layout: Layout, path: Path, label: str, keys: Sequence[str] = ()
) -> tuple[dict[str, Any], dict[str, str]]:
    """Read an artifact once, parse those bytes, and bind the hash of the same bytes."""
    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except ValueError as error:
        raise ValueError(f"{label} is not valid JSON: {relative(layout, path)}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{label} is not a JSON object: {relative(layout, path)}")
    missing = [key for key in keys if key not in payload]
    if missing:
        raise ValueError(f"{label} {path.name} is missing: {', '.join(missing)}")
    return payload, _bind_bytes(layout, path, raw)


def read_spec_bound(layout: Layout) -> tuple[dict[str, Any], dict[str, str]]:
    """Read the BOM spec once; unreadable or non-object content raises SpecFileError."""
    path = layout.bom_spec
    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError) as error:
        raise SpecFileError(f"BOM spec {path} cannot be read: {error}") from error
    if not isinstance(payload, dict):
        raise SpecFileError(f"BOM spec {path} is not a JSON object")
    return payload, _bind_bytes(layout, path, raw)


def keyword_and_serp(layout: Layout) -> tuple[dict[str, Any], dict[str, Any]]:
    """Copy the keyword and SERP blocks from the shortlist and coverage files, with bindings."""
    shortlist, shortlist_binding = read_bound(layout, layout.keyword_shortlist, "keyword shortlist", _SHORTLIST_KEYS)
    coverage, coverage_binding = read_bound(layout, layout.serp_coverage, "SERP coverage", _COVERAGE_KEYS)
    _, decision_binding = read_bound(layout, layout.keyword_decision, "keyword decision")
    _, evidence_binding = read_bound(layout, layout.serp_evidence, "SERP evidence")
    keyword = {key: copy.deepcopy(shortlist[key]) for key in _SHORTLIST_KEYS}
    keyword.update(decision=decision_binding, shortlist=shortlist_binding)
    serp = {key: copy.deepcopy(coverage[key]) for key in _COVERAGE_KEYS}
    serp.update(evidence=evidence_binding, coverage=coverage_binding)
    return keyword, serp


def resolve_paa(spec: Mapping[str, Any], layout: Layout) -> dict[str, Any]:
    """Admit only PAA questions found in the bound artifact, copying the artifact's own wording."""
    questions = spec["paa_questions"]
    if not questions:
        return {"artifact": None, "questions": []}
    artifact, binding = read_bound(layout, layout.paa_artifact, "PAA artifact", ("eligible_questions",))
    eligible = artifact["eligible_questions"]
    if not isinstance(eligible, list) or not all(isinstance(q, str) for q in eligible):
        raise ValueError(f"PAA artifact {layout.paa_artifact.name} eligible_questions must be a list of text")
    known: dict[str, str] = {}
    for question in eligible:
        known.setdefault(squash(question), question)
    asked = [squash(item["question"]) for item in questions]
    errors = [f"duplicate PAA question: {item['question']}" for item in questions if asked.count(squash(item["question"])) > 1]
    errors += [f"PAA question is not in the bound PAA artifact: {item['question']}" for item in questions if squash(item["question"]) not in known]
    if errors:
        raise ValueError("\n".join(dict.fromkeys(errors)))
    admitted = [{"question": known[squash(item["question"])], "priority": item["priority"]} for item in questions]
    return {"artifact": binding, "questions": admitted}


def bind_context(layout: Layout) -> dict[str, Any]:
    """Bind the context pack and receipt as they are on disk right now."""
    return {
        "status": "bound",
        "pack": canonical_artifact(layout.context_pack, workspace_root=layout.root),
        "receipt": canonical_artifact(layout.context_receipt, workspace_root=layout.root),
    }
