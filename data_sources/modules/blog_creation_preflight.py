"""Pre-BOM blocker report for proof-governed blog creation workflows."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from . import eeat_strength_guard
    from . import semrush_keyword_decision_guard
    from .blog_assembly_contract import atomic_write_json
    from .blog_assembly_stage_receipt import check_stage_receipt_file
    from .frontmatter import FrontmatterError, split_frontmatter
except ImportError:  # pragma: no cover - supports direct script execution.
    import eeat_strength_guard
    import semrush_keyword_decision_guard
    from blog_assembly_contract import atomic_write_json
    from blog_assembly_stage_receipt import check_stage_receipt_file
    from frontmatter import FrontmatterError, split_frontmatter


SCHEMA = "simpro-blog-creation-preflight/v1"
SEMRUSH_UI_SURFACE = "semrush_ui_chrome_main_browser"
CUSTOMER_PROOF_SELECTOR_SCHEMA = "simpro-customer-proof-selector-evidence/v1"
NO_FIT_CUSTOMER_PROOF_OUTCOME = "no_fit_customer_proof"
REQUIRED_CUSTOMER_PROOF_ROLES = {"metric", "quote", "theme", "experience_story"}


def build_preflight_report(
    article: str | Path,
    *,
    proof_sidecar: str | Path,
    context_request: str | Path,
    context_pack: str | Path,
    context_receipt: str | Path,
    keyword_decision: str | Path,
    assembly_date: str,
    output: str | Path | None = None,
    scrub_receipt: str | Path | None = None,
    customer_proof_evidence: str | Path | None = None,
    fred_authority_evidence: str | Path | None = None,
    semrush_blocker: str | Path | None = None,
    editorial_plan: str | Path | None = None,
    serp_evidence: str | Path | None = None,
    stage_receipts: Sequence[str | Path] | None = None,
    paa_artifact: str | Path | None = None,
    content_brief: str | Path | None = None,
    user_paa_csv: str | Path | None = None,
    answersocrates_blocker: str | Path | None = None,
) -> dict[str, Any]:
    """Return a strict readiness report for deciding whether BOM assembly may run."""
    artifact_paths = {
        "article": _artifact_path(article),
        "proof_sidecar": _artifact_path(proof_sidecar),
        "context_request": _artifact_path(context_request),
        "context_pack": _artifact_path(context_pack),
        "context_receipt": _artifact_path(context_receipt),
        "keyword_decision": _artifact_path(keyword_decision),
        "scrub_receipt": _artifact_path(scrub_receipt),
        "customer_proof_evidence": _artifact_path(customer_proof_evidence),
        "fred_authority_evidence": _artifact_path(fred_authority_evidence),
        "semrush_blocker": _artifact_path(semrush_blocker),
        "editorial_plan": _artifact_path(editorial_plan),
        "serp_evidence": _artifact_path(serp_evidence),
        "stage_receipts": _artifact_paths(stage_receipts),
        "paa_artifact": _artifact_path(paa_artifact),
        "content_brief": _artifact_path(content_brief),
        "user_paa_csv": _artifact_path(user_paa_csv),
        "answersocrates_blocker": _artifact_path(answersocrates_blocker),
        "output": _artifact_path(output),
    }
    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    next_required_commands: list[str] = []
    required_human_inputs: list[str] = []

    required_paths = {
        "article": article,
        "proof_sidecar": proof_sidecar,
        "context_request": context_request,
        "context_pack": context_pack,
        "context_receipt": context_receipt,
        "keyword_decision": keyword_decision,
        "editorial_plan": editorial_plan,
        "serp_evidence": serp_evidence,
    }
    for label, path in required_paths.items():
        _require_file(path, label, blockers)
    _require_stage_receipts(stage_receipts, blockers)
    _check_optional_bom_dependencies(
        paa_artifact=paa_artifact,
        content_brief=content_brief,
        user_paa_csv=user_paa_csv,
        answersocrates_blocker=answersocrates_blocker,
        blockers=blockers,
    )

    metadata = _article_metadata(article, blockers)
    if _is_file(keyword_decision):
        semrush_findings = semrush_keyword_decision_guard.check_file(
            keyword_decision,
            article_path=article if _is_file(article) else None,
            assembly_date=assembly_date,
        )
        blockers.extend(
            _guard_blocker(finding, "keyword_decision") for finding in semrush_findings
        )
        blockers.extend(_check_semrush_ui_surface(keyword_decision))
    if _is_file(semrush_blocker):
        blockers.append(
            _blocker(
                "blocked_semrush_ui_refresh",
                "Semrush UI refresh was attempted in the main Chrome window but did not yield extractable current evidence.",
                "Re-run the authenticated Semrush UI collection in the main Chrome profile before BOM assembly.",
                "semrush_blocker",
            )
        )

    if not scrub_receipt:
        blockers.append(
            _blocker(
                "scrub_receipt_missing",
                "Preflight requires a scrub stage receipt.",
                "Run /scrub for the public article and pass --scrub-receipt.",
                "scrub_receipt",
            )
        )
    elif not _is_file(scrub_receipt):
        blockers.append(
            _blocker(
                "scrub_receipt_missing",
                f"Scrub receipt is unavailable: {scrub_receipt}",
                "Run /scrub for the public article and pass the generated receipt.",
                "scrub_receipt",
            )
        )
    else:
        receipt_findings = check_stage_receipt_file(
            scrub_receipt,
            expected_stage="scrub",
            expected_tool_name="content_scrubber",
            expected_tool_version="1.0.0",
        )
        blockers.extend(
            _guard_blocker(finding, "scrub_receipt") for finding in receipt_findings
        )
        if not receipt_findings:
            blockers.extend(_check_scrub_receipt_article_binding(scrub_receipt, article))

    _check_customer_proof_evidence(customer_proof_evidence, blockers)
    if not _has_expertise_path(metadata, fred_authority_evidence) and not _has_no_author_policy(proof_sidecar):
        required_human_inputs.append("no-author policy, named author, or selected Fred authority evidence")
        blockers.append(
            _blocker(
                "no_author_policy_missing",
                "Preflight requires a recorded no-author policy, named author, or selected Fred authority evidence before BOM assembly.",
                "Record the no-author decision in the validation sidecar, add a verified named author to frontmatter, or pass selected Fred authority evidence.",
                "article",
            )
        )

    eeat_findings = _check_eeat_strength(
        article=article,
        proof_sidecar=proof_sidecar,
        editorial_plan=editorial_plan,
        customer_proof_evidence=customer_proof_evidence,
        fred_authority_evidence=fred_authority_evidence,
    )
    for finding in eeat_findings:
        converted = _guard_blocker(finding, "eeat_strength")
        if str(finding.get("severity") or "").casefold() == "warning":
            warnings.append(converted)
        else:
            blockers.append(converted)

    rule_ids = {blocker["rule_id"] for blocker in blockers}
    if any(rule.startswith("semrush_keyword_decision") or rule.startswith("semrush_") or rule == "blocked_semrush_ui_refresh" for rule in rule_ids):
        next_required_commands.append(
            "Use the authenticated Semrush UI in the main Chrome profile and regenerate the current keyword decision artifact."
        )
    if "scrub_receipt_missing" in rule_ids or any(rule.startswith("stage_receipt") for rule in rule_ids):
        next_required_commands.append("/scrub [article] --stage-receipt-output [scrub-receipt]")
    if any(rule.endswith("_missing") for rule in rule_ids if rule in {
        "editorial_plan_missing",
        "serp_evidence_missing",
        "stage_receipts_missing",
        "stage_receipt_missing",
        "paa_artifact_missing",
        "content_brief_missing",
        "user_paa_csv_missing",
        "answersocrates_blocker_missing",
    }):
        next_required_commands.append(
            "python data_sources/modules/blog_assembly_bom.py build [article] --validation-sidecar [sidecar] --editorial-plan [plan] --keyword-decision [keyword-decision] --serp-evidence [serp-evidence] --stage-receipt [receipt] --workflow-mode [new|rewrite] --assembly-date [YYYY-MM-DD] --output [bom]"
        )
    if "customer_proof_selector_evidence_missing" in rule_ids or "customer_proof_selector_evidence_invalid" in rule_ids:
        next_required_commands.append(
            "python data_sources/modules/customer_proof_selector.py [topic] --slate --roles metric,quote,theme,experience_story --require-eeat-story --evidence-output [selector-evidence] [--allow-no-proof only when public copy omits customer proof]"
        )
    if "no_author_policy_missing" in rule_ids:
        next_required_commands.append(
            "Record Author Policy: not_provided in the validation sidecar, or run python data_sources/modules/fred_authority_selector.py [topic] --slate --output [fred-authority-evidence]"
        )
    if any(rule.startswith("eeat_strength_") for rule in rule_ids):
        next_required_commands.append(
            "Add ## E-E-A-T Strength Decision with Decision: proof_unavailable_safe_to_publish, or select an approved customer proof, review-theme, Fred authority, author, or SME review signal."
        )

    return {
        "schema": SCHEMA,
        "ready_for_bom": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "next_required_commands": next_required_commands,
        "required_human_inputs": required_human_inputs,
        "artifact_paths": artifact_paths,
    }


def _check_eeat_strength(
    *,
    article: str | Path,
    proof_sidecar: str | Path,
    editorial_plan: str | Path | None,
    customer_proof_evidence: str | Path | None,
    fred_authority_evidence: str | Path | None,
) -> list[dict[str, Any]]:
    if not _is_file(article) or not _is_file(proof_sidecar):
        return []
    return eeat_strength_guard.check_file(
        article,
        proof_sidecar=proof_sidecar,
        editorial_plan=editorial_plan if _is_file(editorial_plan) else None,
        customer_proof_selector_evidence=(
            customer_proof_evidence if _is_file(customer_proof_evidence) else None
        ),
        fred_authority_evidence=(
            fred_authority_evidence if _is_file(fred_authority_evidence) else None
        ),
    )


def _artifact_path(path: str | Path | None) -> str | None:
    if path is None:
        return None
    return str(Path(path).resolve(strict=False))


def _artifact_paths(paths: Sequence[str | Path] | None) -> list[str] | None:
    if paths is None:
        return None
    return [_artifact_path(path) or "" for path in paths]


def _is_file(path: str | Path | None) -> bool:
    return bool(path) and Path(path).is_file()


def _require_file(
    path: str | Path | None,
    label: str,
    blockers: list[dict[str, str]],
) -> None:
    if _is_file(path):
        return
    blockers.append(
        _blocker(
            f"{label}_missing",
            f"Required artifact is unavailable: {path or label}",
            f"Generate and pass --{label.replace('_', '-')}.",
            label,
        )
    )


def _require_stage_receipts(
    paths: Sequence[str | Path] | None,
    blockers: list[dict[str, str]],
) -> None:
    if not paths:
        blockers.append(
            _blocker(
                "stage_receipts_missing",
                "Preflight requires the stage receipt files that BOM assembly will bind.",
                "Pass at least one --stage-receipt generated by the native workflow.",
                "stage_receipts",
            )
        )
        return
    for index, path in enumerate(paths, start=1):
        if _is_file(path):
            continue
        blockers.append(
            _blocker(
                "stage_receipt_missing",
                f"Stage receipt {index} is unavailable: {path}",
                "Regenerate the missing workflow stage receipt and pass --stage-receipt.",
                "stage_receipts",
            )
        )


def _check_optional_bom_dependencies(
    *,
    paa_artifact: str | Path | None,
    content_brief: str | Path | None,
    user_paa_csv: str | Path | None,
    answersocrates_blocker: str | Path | None,
    blockers: list[dict[str, str]],
) -> None:
    for label, path in (
        ("paa_artifact", paa_artifact),
        ("content_brief", content_brief),
        ("user_paa_csv", user_paa_csv),
        ("answersocrates_blocker", answersocrates_blocker),
    ):
        if path is not None:
            _require_file(path, label, blockers)


def _check_scrub_receipt_article_binding(
    scrub_receipt: str | Path,
    article: str | Path,
) -> list[dict[str, str]]:
    if not _is_file(article):
        return []
    try:
        payload = json.loads(Path(scrub_receipt).read_text(encoding="utf-8"))
        article_hash = hashlib.sha256(Path(article).read_bytes()).hexdigest()
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    if not isinstance(payload, Mapping):
        return []
    inputs = payload.get("input_artifact_hashes")
    outputs = payload.get("output_artifact_hashes")
    if not isinstance(inputs, Mapping) or not isinstance(outputs, Mapping):
        return []
    if inputs.get("article") == article_hash and outputs.get("article") == article_hash:
        return []
    return [
        _blocker(
            "scrub_receipt_article_hash_mismatch",
            "Scrub receipt does not bind the supplied article's current hash.",
            "Rerun /scrub for this exact article and pass the generated receipt.",
            "scrub_receipt",
        )
    ]


def _article_metadata(
    article: str | Path,
    blockers: list[dict[str, str]],
) -> Mapping[str, Any]:
    if not _is_file(article):
        return {}
    try:
        metadata, _body, _line = split_frontmatter(Path(article).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, FrontmatterError) as error:
        blockers.append(
            _blocker(
                "article_frontmatter_invalid",
                f"Article frontmatter could not be read: {error}",
                "Correct article frontmatter before preflight.",
                "article",
            )
        )
        return {}
    return metadata


def _check_semrush_ui_surface(path: str | Path) -> list[dict[str, str]]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    reports = payload.get("connector_reports") if isinstance(payload, Mapping) else None
    if not isinstance(reports, list):
        return []
    surfaces = {
        str((row.get("parameters") or {}).get("execution_surface") or "").strip()
        for row in reports
        if isinstance(row, Mapping) and isinstance(row.get("parameters"), Mapping)
    }
    blockers: list[dict[str, str]] = []
    if SEMRUSH_UI_SURFACE not in surfaces:
        blockers.append(
            _blocker(
                "semrush_ui_surface_missing",
                "Semrush keyword decision does not identify the main Chrome UI evidence surface.",
                "Regenerate the keyword decision from the authenticated Semrush UI in the main Chrome profile.",
                "keyword_decision",
            )
        )
    prohibited = sorted(
        surface
        for surface in surfaces
        if surface
        and surface.casefold()
        in {"semrush_api_connector", "semrush_mcp", "api", "mcp"}
    )
    if prohibited:
        blockers.append(
            _blocker(
                "semrush_api_fallback_prohibited",
                "Semrush API or MCP evidence cannot satisfy this UI-bound workflow.",
                "Replace the keyword decision with authenticated main Chrome Semrush UI evidence.",
                "keyword_decision",
            )
        )
    return blockers


def _check_customer_proof_evidence(
    path: str | Path | None,
    blockers: list[dict[str, str]],
) -> None:
    if not path or not _is_file(path):
        blockers.append(
            _blocker(
                "customer_proof_selector_evidence_missing",
                "Preflight requires customer proof selector evidence.",
                "Run customer_proof_selector.py with --slate and --evidence-output; add --allow-no-proof only when public copy omits customer proof.",
                "customer_proof_evidence",
            )
        )
        return
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        blockers.append(
            _blocker(
                "customer_proof_selector_evidence_invalid",
                f"Customer proof selector evidence is unreadable: {error}",
                "Regenerate selector evidence as JSON.",
                "customer_proof_evidence",
            )
        )
        return
    if not isinstance(payload, Mapping) or payload.get("schema") != CUSTOMER_PROOF_SELECTOR_SCHEMA:
        blockers.append(
            _blocker(
                "customer_proof_selector_evidence_invalid",
                f"Customer proof selector evidence must use {CUSTOMER_PROOF_SELECTOR_SCHEMA}.",
                "Regenerate selector evidence with --evidence-output.",
                "customer_proof_evidence",
            )
        )
        return
    roles = payload.get("roles")
    role_names = {
        str(role.get("role") or "").strip()
        for role in roles
        if isinstance(role, Mapping)
    } if isinstance(roles, list) else set()
    if payload.get("selection_outcome") == NO_FIT_CUSTOMER_PROOF_OUTCOME:
        blockers.extend(_check_no_fit_customer_proof_evidence(roles, role_names))
        return
    if "experience_story" not in role_names:
        blockers.append(
            _blocker(
                "customer_experience_story_evidence_missing",
                "Customer proof selector evidence must include the experience_story role.",
                "Rerun customer_proof_selector.py with --roles metric,quote,theme,experience_story and --require-eeat-story.",
                "customer_proof_evidence",
            )
        )


def _check_no_fit_customer_proof_evidence(
    roles: Any,
    role_names: set[str],
) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    if role_names != REQUIRED_CUSTOMER_PROOF_ROLES:
        blockers.append(
            _blocker(
                "customer_proof_no_fit_roles_incomplete",
                "No-fit customer proof evidence must include metric, quote, theme, and experience_story roles.",
                "Rerun customer_proof_selector.py with --roles metric,quote,theme,experience_story --require-eeat-story --allow-no-proof.",
                "customer_proof_evidence",
            )
        )
        return blockers
    if not isinstance(roles, list):
        blockers.append(
            _blocker(
                "customer_proof_no_fit_roles_invalid",
                "No-fit customer proof evidence roles must be a list.",
                "Regenerate selector evidence as JSON.",
                "customer_proof_evidence",
            )
        )
        return blockers
    for row in roles:
        if not isinstance(row, Mapping):
            blockers.append(
                _blocker(
                    "customer_proof_no_fit_role_invalid",
                    "No-fit customer proof evidence contains an invalid role row.",
                    "Regenerate selector evidence with --allow-no-proof.",
                    "customer_proof_evidence",
                )
            )
            continue
        role = str(row.get("role") or "").strip()
        reason = str(row.get("no_fit_reason") or "")
        if (
            row.get("candidate_ids") != []
            or row.get("claim_ids") != []
            or str(row.get("selected_id") or "").casefold() != "none"
            or "public copy must omit customer proof" not in reason
        ):
            blockers.append(
                _blocker(
                    "customer_proof_no_fit_role_invalid",
                    f"No-fit customer proof role {role or '[unknown]'} must have no candidates, no claims, selected_id none, and an omission reason.",
                    "Regenerate selector evidence with --allow-no-proof and do not select proof.",
                    "customer_proof_evidence",
                )
            )
    return blockers


def _has_expertise_path(
    metadata: Mapping[str, Any],
    fred_authority_evidence: str | Path | None,
) -> bool:
    if str(metadata.get("author") or "").strip():
        return True
    if not fred_authority_evidence or not _is_file(fred_authority_evidence):
        return False
    try:
        content = Path(fred_authority_evidence).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    if "Fred Voccola Authority Selection" not in content:
        return False
    if not re.search(r"(?im)^-\s*Evaluation status:\s*completed\s*$", content):
        return False
    selected = re.search(r"(?im)^-\s*Selected:\s*\[([^\]]+)\]\s*$", content)
    if not selected:
        return False
    return selected.group(1).strip().casefold() != "none"


def _has_no_author_policy(proof_sidecar: str | Path | None) -> bool:
    if not proof_sidecar or not _is_file(proof_sidecar):
        return False
    try:
        content = Path(proof_sidecar).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    if re.search(
        r"(?im)^\s*(?:[-*+]\s*)?Author policy:\s*(?:not_provided|no[-_ ]author|omitted)\s*$",
        content,
    ):
        return True
    return bool(
        re.search(r"(?im)^\s*[-*+]\s*Named author supplied:\s*no\s*$", content)
        and re.search(r"(?im)^\s*[-*+]\s*Public frontmatter author:\s*omitted\s*$", content)
    )


def _guard_blocker(finding: Mapping[str, Any], artifact: str) -> dict[str, str]:
    return _blocker(
        str(finding.get("rule_id") or "guard_finding"),
        str(finding.get("message") or finding.get("detail") or "Guard finding."),
        str(finding.get("suggestion") or "Regenerate the artifact and rerun preflight."),
        artifact,
    )


def _blocker(
    rule_id: str,
    message: str,
    suggestion: str,
    artifact: str,
) -> dict[str, str]:
    return {
        "rule_id": rule_id,
        "message": message,
        "suggestion": suggestion,
        "artifact": artifact,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a pre-BOM blocker report for blog creation workflows."
    )
    parser.add_argument("article", help="Public blog Markdown artifact.")
    parser.add_argument("--proof-sidecar", required=True)
    parser.add_argument("--context-request", required=True)
    parser.add_argument("--context-pack", required=True)
    parser.add_argument("--context-receipt", required=True)
    parser.add_argument("--keyword-decision", required=True)
    parser.add_argument("--assembly-date", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--scrub-receipt")
    parser.add_argument("--customer-proof-evidence")
    parser.add_argument("--fred-authority-evidence")
    parser.add_argument("--semrush-blocker")
    parser.add_argument("--editorial-plan")
    parser.add_argument("--serp-evidence")
    parser.add_argument("--stage-receipt", action="append", default=[])
    parser.add_argument("--paa-artifact")
    parser.add_argument("--content-brief")
    parser.add_argument("--user-paa-csv")
    parser.add_argument("--answersocrates-blocker")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = build_preflight_report(
        args.article,
        proof_sidecar=args.proof_sidecar,
        context_request=args.context_request,
        context_pack=args.context_pack,
        context_receipt=args.context_receipt,
        keyword_decision=args.keyword_decision,
        assembly_date=args.assembly_date,
        output=args.output,
        scrub_receipt=args.scrub_receipt,
        customer_proof_evidence=args.customer_proof_evidence,
        fred_authority_evidence=args.fred_authority_evidence,
        semrush_blocker=args.semrush_blocker,
        editorial_plan=args.editorial_plan,
        serp_evidence=args.serp_evidence,
        stage_receipts=args.stage_receipt,
        paa_artifact=args.paa_artifact,
        content_brief=args.content_brief,
        user_paa_csv=args.user_paa_csv,
        answersocrates_blocker=args.answersocrates_blocker,
    )
    atomic_write_json(args.output, report)
    return 0 if report["ready_for_bom"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
