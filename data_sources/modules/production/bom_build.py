"""Build the production BOM from a Claude-written spec, admitting only verified facts and approved proof.

Usage: python -m data_sources.modules.production.bom_build <article> [--workspace-root DIR]
"""

from __future__ import annotations

import argparse
import copy
import datetime
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from data_sources.modules.blog_assembly_contract import atomic_write_json, canonical_artifact
from data_sources.modules.commercial_pillar_index import get_verified_destination, load_index
from data_sources.modules.context_binding_guard import NON_CONNECTOR_BRANDS, SIMPRO_ARTICLE_RE
from data_sources.modules.production.bom import (
    BOM_SCHEMA,
    SpecFileError,
    load_spec,
    validate_bom,
    validate_spec,
)
from data_sources.modules.production.bom_proof import (
    ClaimLoader,
    resolve_connector_proof,
    resolve_nonconnector_proof,
)
from data_sources.modules.production.facts import verify_quotes
from data_sources.modules.production.layout import Layout, LayoutError, load_or_create_run_id
from data_sources.modules.production.numbers import numbers_supported
from data_sources.modules.public_http import PublicHttpTransport
from data_sources.modules.vault_claim_receipts import load_validated_claim_set

PILLAR_INDEX = Path("context") / "commercial-pillar-index.json"
_SHORTLIST_KEYS = ("primary", "secondary", "candidates", "decision_rule")
_COVERAGE_KEYS = ("query", "topics", "uncovered_questions")


def is_nonconnector(spec: Mapping[str, Any]) -> bool:
    """Decide connector or nonconnector from the spec, since the article does not exist yet.

    The spec's own ``schema`` value names Simpro, so it is left out of the signal scan.
    """
    brand = str(spec.get("brand", "")).casefold()
    content = json.dumps({key: value for key, value in spec.items() if key != "schema"})
    return brand in NON_CONNECTOR_BRANDS and SIMPRO_ARTICLE_RE.search(content) is None


def _squash(text: str) -> str:
    return " ".join(text.casefold().split())


def _relative(layout: Layout, path: Path) -> str:
    return path.relative_to(layout.root).as_posix()


def _required_artifacts(layout: Layout, spec: Mapping[str, Any], nonconnector: bool) -> dict[str, Path]:
    required = {
        "keyword_decision": layout.keyword_decision,
        "keyword_shortlist": layout.keyword_shortlist,
        "serp_evidence": layout.serp_evidence,
        "serp_coverage": layout.serp_coverage,
    }
    if spec["paa_questions"]:
        required["paa_artifact"] = layout.paa_artifact
    if not nonconnector:
        required["context_pack"] = layout.context_pack
        required["context_receipt"] = layout.context_receipt
    return required


def _preflight_errors(layout: Layout, spec: Mapping[str, Any], nonconnector: bool) -> list[str]:
    reason = spec.get("not_applicable_context_reason")
    errors = []
    if nonconnector and not reason:
        errors.append("nonconnector spec requires a non-empty not_applicable_context_reason")
    if not nonconnector and "not_applicable_context_reason" in spec:
        errors.append("connector spec must not carry not_applicable_context_reason")
    for path in _required_artifacts(layout, spec, nonconnector).values():
        if not path.is_file():
            errors.append(f"required artifact is missing: {_relative(layout, path)}")
    return errors


def _bind(layout: Layout, path: Path) -> dict[str, str]:
    return canonical_artifact(path, workspace_root=layout.root)


def _read_object(path: Path, label: str, keys: Sequence[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"{label} cannot be read: {path}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{label} is not a JSON object: {path}")
    missing = [key for key in keys if key not in payload]
    if missing:
        raise ValueError(f"{label} {path.name} is missing: {', '.join(missing)}")
    return payload


def _keyword_and_serp(layout: Layout) -> tuple[dict[str, Any], dict[str, Any]]:
    shortlist = _read_object(layout.keyword_shortlist, "keyword shortlist", _SHORTLIST_KEYS)
    coverage = _read_object(layout.serp_coverage, "SERP coverage", _COVERAGE_KEYS)
    keyword = {key: copy.deepcopy(shortlist[key]) for key in _SHORTLIST_KEYS}
    keyword["decision"] = _bind(layout, layout.keyword_decision)
    keyword["shortlist"] = _bind(layout, layout.keyword_shortlist)
    serp = {key: copy.deepcopy(coverage[key]) for key in _COVERAGE_KEYS}
    serp["evidence"] = _bind(layout, layout.serp_evidence)
    serp["coverage"] = _bind(layout, layout.serp_coverage)
    return keyword, serp


def resolve_paa(spec: Mapping[str, Any], layout: Layout) -> dict[str, Any]:
    """Admit only PAA questions that appear in the bound PAA artifact."""
    questions = spec["paa_questions"]
    if not questions:
        return {"artifact": None, "questions": []}
    artifact = _read_object(layout.paa_artifact, "PAA artifact", ("eligible_questions",))
    eligible = artifact["eligible_questions"]
    if not isinstance(eligible, list) or not all(isinstance(q, str) for q in eligible):
        raise ValueError(f"PAA artifact {layout.paa_artifact.name} eligible_questions must be a list of text")
    known = {_squash(question) for question in eligible}
    absent = [item["question"] for item in questions if _squash(item["question"]) not in known]
    if absent:
        raise ValueError("PAA question is not in the bound PAA artifact: " + "; ".join(absent))
    return {"artifact": _bind(layout, layout.paa_artifact), "questions": copy.deepcopy(questions)}


def _check_pillar(link: Mapping[str, Any], spec: Mapping[str, Any], root: Path) -> None:
    destination_id = link.get("destination_id")
    if not destination_id:
        raise ValueError("commercial_pillar link requires destination_id")
    if link["priority"] != "must":
        raise ValueError("commercial_pillar link priority must be must")
    index = load_index(root / PILLAR_INDEX)
    record = get_verified_destination(
        index, destination_id=destination_id, brand=spec["brand"], market=spec["market"]
    )
    if link["url"] != record.canonical_url:
        raise ValueError(
            f"commercial_pillar url must equal the canonical url {record.canonical_url}, found: {link['url']}"
        )
    if _squash(record.main_keyword) not in _squash(link["anchor"]):
        raise ValueError(
            f"commercial_pillar anchor must contain the main keyword: {record.main_keyword}"
        )


def resolve_links(spec: Mapping[str, Any], root: Path, nonconnector: bool) -> list[dict[str, Any]]:
    """Copy links, requiring and verifying the commercial pillar for connector specs."""
    links = copy.deepcopy(spec["links"])
    pillars = [link for link in links if link["kind"] == "commercial_pillar"]
    if len(pillars) > 1 or (not nonconnector and len(pillars) != 1):
        raise ValueError(f"expected exactly one commercial_pillar link, found {len(pillars)}")
    for pillar in pillars:
        _check_pillar(pillar, spec, root)
    return links


def _number_errors(facts: Sequence[Mapping[str, Any]]) -> list[str]:
    errors = []
    for fact in facts:
        ok, missing = numbers_supported(fact["claim"], fact["quote"])
        if not ok:
            errors.append(f"fact {fact['id']} claim numbers are not in its quote: {', '.join(sorted(missing))}")
    return errors


def verify_facts(facts: Sequence[Mapping[str, Any]], *, transport: Any) -> list[dict[str, Any]]:
    """Verify every fact quote on its live page in one batch; any failure refuses the build."""
    if not facts:
        return []
    results = verify_quotes([(fact["url"], fact["quote"]) for fact in facts], transport=transport)
    verified_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    errors, admitted = [], []
    for fact in facts:
        check = results[(fact["url"], fact["quote"])]
        if check.status != "verified":
            errors.append(f"fact {fact['id']} ({fact['url']}) is {check.status}: {check.detail}")
            continue
        admitted.append({**{key: fact[key] for key in ("id", "claim", "url", "quote", "priority")},
                         "verified_at": verified_at, "check_detail": check.detail})
    if errors:
        raise ValueError("\n".join(errors))
    return admitted


def _context_block(layout: Layout, spec: Mapping[str, Any], nonconnector: bool) -> dict[str, Any]:
    if nonconnector:
        return {"status": "not_applicable", "reason": spec["not_applicable_context_reason"]}
    return {
        "status": "bound",
        "pack": _bind(layout, layout.context_pack),
        "receipt": _bind(layout, layout.context_receipt),
    }


def _identity(layout: Layout, spec: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "slug": layout.slug,
        "date": layout.date,
        "run_id": load_or_create_run_id(layout),
        "brand": spec["brand"],
        "market": spec["market"],
        "workflow_mode": layout.workflow_mode,
        "article_path": _relative(layout, layout.article),
        "title": spec["title"],
        "objective": spec["objective"],
        "audience": spec["audience"],
        "cta": copy.deepcopy(spec["cta"]),
        "schema_notes": copy.deepcopy(spec["schema_notes"]),
    }


def _local_phase(
    layout: Layout, spec: Mapping[str, Any], nonconnector: bool, claim_loader: ClaimLoader
) -> tuple[dict[str, Any], list[str]]:
    """Run every check that needs no network, collecting all refusal reasons."""
    steps = {
        "proof": lambda: (
            resolve_nonconnector_proof(spec["proof"], layout.root)
            if nonconnector
            else resolve_connector_proof(spec["proof"], layout, claim_loader)
        ),
        "paa": lambda: resolve_paa(spec, layout),
        "links": lambda: resolve_links(spec, layout.root, nonconnector),
        "blocks": lambda: _keyword_and_serp(layout),
        "context": lambda: _context_block(layout, spec, nonconnector),
    }
    results: dict[str, Any] = {}
    errors = _number_errors(spec["facts"])
    for name, step in steps.items():
        try:
            results[name] = step()
        except ValueError as error:
            errors.append(str(error))
    return results, errors


def build_bom(
    layout: Layout,
    *,
    transport: Any,
    claim_loader: ClaimLoader = load_validated_claim_set,
) -> dict[str, Any]:
    """Build the BOM; raises ValueError listing every reason when anything is unverified."""
    spec = load_spec(layout.bom_spec)
    spec_errors = validate_spec(spec)
    if spec_errors:
        raise ValueError("\n".join(spec_errors))
    nonconnector = is_nonconnector(spec)
    preflight = _preflight_errors(layout, spec, nonconnector)
    if preflight:
        raise ValueError("\n".join(preflight))
    local, errors = _local_phase(layout, spec, nonconnector, claim_loader)
    if errors:
        raise ValueError("\n".join(errors))
    facts = verify_facts(spec["facts"], transport=transport)
    keyword, serp = local["blocks"]
    bom = {
        "schema": BOM_SCHEMA,
        "identity": _identity(layout, spec),
        "keyword": keyword,
        "serp": serp,
        "sections": copy.deepcopy(spec["sections"]),
        "facts": facts,
        "proof": local["proof"],
        "paa": local["paa"],
        "links": local["links"],
        "context": local["context"],
    }
    problems = validate_bom(bom)
    if problems:
        raise ValueError("\n".join(problems))
    return bom


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bom_build", description=__doc__)
    parser.add_argument("article", type=Path)
    parser.add_argument("--workspace-root", type=Path, default=None)
    return parser


def _report(error: BaseException) -> None:
    for line in str(error).splitlines():
        print(f"bom_build: {line}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exit_request:
        return int(exit_request.code or 0)
    root = (args.workspace_root or Path.cwd()).resolve()
    try:
        layout = Layout.for_article(args.article, root)
        with PublicHttpTransport() as transport:
            bom = build_bom(layout, transport=transport, claim_loader=load_validated_claim_set)
    except (LayoutError, SpecFileError, OSError) as error:
        _report(error)
        return 2
    except ValueError as error:
        _report(error)
        return 1
    try:
        atomic_write_json(layout.bom, bom)
    except (OSError, ValueError) as error:
        _report(error)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
