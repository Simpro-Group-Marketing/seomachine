"""Build the production BOM from a Claude-written spec, admitting only verified facts and approved proof.

Usage: python -m data_sources.modules.production.bom_build <article> [--workspace-root DIR]

Exit codes: 0 built, 1 refused (unverified content; one line per reason), 2 operational error.
A refused or failed run moves any earlier BOM aside as ``<name>.refused`` so it cannot be released.
"""

from __future__ import annotations

import argparse
import copy
import datetime
import os
import sys
import unicodedata
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.context_binding_guard import NON_CONNECTOR_BRANDS, SIMPRO_ARTICLE_RE
from data_sources.modules.customer_proof.nonconnector_eligibility import _canonical_brand
from data_sources.modules.production.bom import (
    BOM_SCHEMA,
    BuildEnvironmentError,
    SpecFileError,
    validate_bom,
    validate_spec,
)
from data_sources.modules.production.bom_artifacts import (
    bind_context,
    keyword_and_serp,
    read_spec_bound,
    relative,
    resolve_paa,
)
from data_sources.modules.production.bom_links import resolve_links
from data_sources.modules.production.bom_proof import (
    ClaimLoader,
    resolve_connector_proof,
    resolve_nonconnector_proof,
)
from data_sources.modules.production.bom_text import free_text_number_errors
from data_sources.modules.production.claim_support import SUPPORT_RULE, claim_support_errors
from data_sources.modules.production.facts import verify_quotes
from data_sources.modules.production.layout import Layout, LayoutError, load_or_create_run_id
from data_sources.modules.production.numbers import numbers_supported
from data_sources.modules.public_http import PublicHttpTransport
from data_sources.modules.vault_claim_receipts import load_validated_claim_set


def _normalize(text: str) -> str:
    """NFKC-fold and drop invisible format characters so hidden marks cannot hide a brand name."""
    folded = unicodedata.normalize("NFKC", text)
    return "".join(char for char in folded if unicodedata.category(char) != "Cf")


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return [text for key, item in value.items() for text in [*_strings(key), *_strings(item)]]
    if isinstance(value, (list, tuple)):
        return [text for item in value for text in _strings(item)]
    return []


def is_nonconnector(spec: Mapping[str, Any]) -> bool:
    """Decide connector or nonconnector from the spec, since the article does not exist yet.

    The spec's own ``schema`` value names Simpro, so it is left out of the signal scan.
    Text is normalized first so hidden or fullwidth characters cannot hide the signal.
    """
    brand = _normalize(str(spec.get("brand", ""))).casefold()
    content = _normalize("\n".join(_strings({k: v for k, v in spec.items() if k != "schema"})))
    return brand in NON_CONNECTOR_BRANDS and SIMPRO_ARTICLE_RE.search(content) is None


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
            errors.append(f"required artifact is missing: {relative(layout, path)}")
    return errors


def _fact_errors(facts: Sequence[Mapping[str, Any]]) -> list[str]:
    errors = []
    for fact in facts:
        ok, missing = numbers_supported(fact["claim"], fact["quote"])
        if not ok:
            errors.append(f"fact {fact['id']} claim numbers are not in its quote: {', '.join(sorted(missing))}")
        errors += claim_support_errors(fact["id"], fact["claim"], fact["quote"])
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
                         "verified_at": verified_at, "check_detail": check.detail, "support": SUPPORT_RULE})
    if errors:
        raise ValueError("\n".join(errors))
    return admitted


def _identity(
    layout: Layout, spec: Mapping[str, Any], spec_binding: Mapping[str, str], nonconnector: bool
) -> dict[str, Any]:
    return {
        "slug": layout.slug,
        "date": layout.date,
        "run_id": load_or_create_run_id(layout),
        "brand": _canonical_brand(spec["brand"]) if nonconnector else spec["brand"],
        "market": spec["market"],
        "workflow_mode": layout.workflow_mode,
        "article_path": relative(layout, layout.article),
        "title": spec["title"],
        "objective": spec["objective"],
        "audience": spec["audience"],
        "cta": copy.deepcopy(spec["cta"]),
        "schema_notes": copy.deepcopy(spec["schema_notes"]),
        "spec": dict(spec_binding),
    }


def _context_block(layout: Layout, spec: Mapping[str, Any], nonconnector: bool) -> dict[str, Any]:
    if nonconnector:
        return {"status": "not_applicable", "reason": spec["not_applicable_context_reason"]}
    return bind_context(layout)


def _local_phase(
    layout: Layout, spec: Mapping[str, Any], nonconnector: bool, claim_loader: ClaimLoader
) -> tuple[dict[str, Any], list[str]]:
    """Run every check that needs no network, collecting all refusal reasons."""
    steps = {
        "context": lambda: _context_block(layout, spec, nonconnector),
        "proof": lambda: (
            resolve_nonconnector_proof(spec["proof"], layout.root, spec["brand"], spec["market"])
            if nonconnector
            else resolve_connector_proof(spec["proof"], layout, claim_loader)
        ),
        "paa": lambda: resolve_paa(spec, layout),
        "links": lambda: resolve_links(spec, layout.root, nonconnector),
        "blocks": lambda: keyword_and_serp(layout),
    }
    results: dict[str, Any] = {}
    errors = _fact_errors(spec["facts"])
    for name, step in steps.items():
        try:
            results[name] = step()
        except ValueError as error:
            errors.append(str(error))
    if "proof" in results:
        errors += free_text_number_errors(spec, spec["facts"], results["proof"], layout.date[:4])
    if "context" in results and _context_block(layout, spec, nonconnector) != results["context"]:
        errors.append("artifact changed while the BOM was built: context pack or receipt")
    return results, errors


def build_bom(
    layout: Layout,
    *,
    transport: Any,
    claim_loader: ClaimLoader = load_validated_claim_set,
) -> dict[str, Any]:
    """Build the BOM; raises ValueError listing every reason when anything is unverified."""
    spec, spec_binding = read_spec_bound(layout)
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
        "identity": _identity(layout, spec, spec_binding, nonconnector),
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


def _report(error: BaseException | str) -> None:
    for line in str(error).splitlines():
        print(f"bom_build: {line}", file=sys.stderr)


def _retire_stale_bom(layout: Layout) -> None:
    """Move an earlier BOM aside so a refused or failed rebuild cannot leave a releasable one."""
    if not layout.bom.exists():
        return
    try:
        os.replace(layout.bom, layout.bom.with_name(layout.bom.name + ".refused"))
    except OSError as error:
        _report(f"cannot retire the earlier BOM {layout.bom}: {error}")


def _write_bom(layout: Layout, bom: Mapping[str, Any]) -> None:
    try:
        atomic_write_json(layout.bom, bom)
    except ValueError as error:
        raise OSError(str(error)) from error


def _run(args: argparse.Namespace, root: Path, holder: list[Layout]) -> int:
    try:
        layout = Layout.for_article(args.article, root)
        holder.append(layout)
        with PublicHttpTransport() as transport:
            bom = build_bom(layout, transport=transport, claim_loader=load_validated_claim_set)
        _write_bom(layout, bom)
    except (LayoutError, SpecFileError, BuildEnvironmentError, OSError) as error:
        _report(error)
        return 2
    except ValueError as error:
        _report(error)
        return 1
    except Exception as error:  # noqa: BLE001 - the CLI must never leak a traceback
        _report(f"unexpected error: {type(error).__name__}: {error}")
        return 2
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exit_request:
        return int(exit_request.code or 0)
    holder: list[Layout] = []
    code = _run(args, (args.workspace_root or Path.cwd()).resolve(), holder)
    if code != 0 and holder:
        _retire_stale_bom(holder[0])
    return code


if __name__ == "__main__":
    raise SystemExit(main())
