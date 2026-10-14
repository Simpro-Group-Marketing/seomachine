"""Bound research artifacts for the production BOM: parse the bytes that get hashed."""

from __future__ import annotations

import copy
import datetime
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from data_sources.modules.blog_assembly_contract import canonical_artifact
from data_sources.modules.commercial_pillar_index import SEMRUSH_DATABASE_BY_MARKET
from data_sources.modules.production.bom import SpecFileError
from data_sources.modules.production.layout import Layout, stored_run_id

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


def _market_errors(decision: Mapping[str, Any], market: str) -> list[str]:
    """The keyword decision must be for the spec market and that market's Semrush database."""
    market = str(market or "").strip().upper()
    expected = SEMRUSH_DATABASE_BY_MARKET.get(market)
    if expected is None:
        return [f"spec market {market} has no Semrush database"]
    errors = []
    if str(decision.get("market") or "").strip().upper() != market:
        errors.append(f"keyword decision market {decision.get('market')!r} does not match the spec market {market}")
    if str(decision.get("database") or "").strip().lower() != expected:
        errors.append(
            f"keyword decision database {decision.get('database')!r} does not match the spec market {market} "
            f"Semrush database {expected}"
        )
    return errors


def keyword_and_serp(layout: Layout, market: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Copy the keyword and SERP blocks from the shortlist and coverage files, with bindings.

    The bound keyword decision must agree with the spec ``market`` and its Semrush database.
    """
    shortlist, shortlist_binding = read_bound(layout, layout.keyword_shortlist, "keyword shortlist", _SHORTLIST_KEYS)
    coverage, coverage_binding = read_bound(layout, layout.serp_coverage, "SERP coverage", _COVERAGE_KEYS)
    decision, decision_binding = read_bound(layout, layout.keyword_decision, "keyword decision")
    errors = _market_errors(decision, market)
    if errors:
        raise ValueError("\n".join(errors))
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
    collection_date, run_id, identity_errors = _paa_identity(artifact, layout)
    errors += identity_errors
    if errors:
        raise ValueError("\n".join(dict.fromkeys(errors)))
    admitted = [{"question": known[squash(item["question"])], "priority": item["priority"]} for item in questions]
    return {"artifact": binding, "questions": admitted, "collection_date": collection_date, "run_id": run_id}


def _paa_identity(artifact: Mapping[str, Any], layout: Layout) -> tuple[str, str, list[str]]:
    """Read the PAA capture's date and run id; both must be this article's date and production run."""
    name = layout.paa_artifact.name
    errors = []
    collection_date = artifact.get("collection_date")
    try:
        datetime.date.fromisoformat(collection_date if isinstance(collection_date, str) else "")
    except ValueError:
        errors.append(f"PAA artifact {name} collection_date must be YYYY-MM-DD, found: {collection_date!r}")
    if isinstance(collection_date, str) and collection_date != layout.date:
        errors.append(
            f"PAA artifact {name} collection_date {collection_date} does not match the article date {layout.date}"
        )
    receipt = artifact.get("run_receipt")
    run_id = receipt.get("run_id") if isinstance(receipt, Mapping) else None
    if not (isinstance(run_id, str) and run_id):
        return str(collection_date), "", [*errors, f"PAA artifact {name} has no run_receipt.run_id"]
    production_run = stored_run_id(layout)
    if run_id != production_run:
        errors.append(
            f"PAA artifact run id {run_id} does not match the production run id {production_run or '(none recorded)'}"
        )
    return str(collection_date), run_id, errors


def bind_context(layout: Layout) -> dict[str, Any]:
    """Bind the context pack and receipt as they are on disk right now."""
    return {
        "status": "bound",
        "pack": canonical_artifact(layout.context_pack, workspace_root=layout.root),
        "receipt": canonical_artifact(layout.context_receipt, workspace_root=layout.root),
    }
