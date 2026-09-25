"""Snapshot adapters owned by blog assembly BOM validation."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping


def verify_artifact(
    captured: Any,
    row: Any,
    *,
    field: str,
    root: Path,
    legacy_verify: Any,
) -> Path:
    """Resolve a BOM row through the authoritative store when available."""
    if captured is not None:
        return captured.snapshot_row(row, field=field).path
    return legacy_verify(row, workspace_root=root, field=field)


def json_artifact(
    captured: Any,
    row: Any,
    *,
    field: str,
    root: Path,
    legacy_loader: Any,
    legacy_verify: Any,
) -> Mapping[str, Any]:
    """Return one immutable captured JSON object or a legacy loaded object."""
    if captured is not None:
        return captured.json_row(row, field=field)
    path = legacy_verify(row, workspace_root=root, field=field)
    return legacy_loader(path, field=field).payload


def text_artifact(
    captured: Any,
    row: Any,
    *,
    field: str,
    root: Path,
    legacy_verify: Any,
) -> str:
    """Return strict UTF-8 captured text or use the compatibility file path."""
    if captured is not None:
        return captured.text_row(row, field=field)
    path = legacy_verify(row, workspace_root=root, field=field)
    return path.read_text(encoding="utf-8")


def optional_text(captured: Any, label: str | None) -> str | None:
    """Return captured UTF-8 text for an optional inventory label."""
    if label is None or captured.optional_snapshot(label) is None:
        return None
    return captured.text_row(
        {
            "path": captured.snapshot(label).relative_path,
            "sha256": captured.snapshot(label).sha256,
        },
        field=label,
    )


def json_snapshot(captured: Any, label: str) -> Any:
    """Return a legacy-compatible immutable-file JSON snapshot projection."""
    snapshot = captured.snapshot(label)
    return SimpleNamespace(
        path=snapshot.path,
        relative_path=snapshot.relative_path,
        sha256=snapshot.sha256,
        payload=captured.json_row_copy(
            {"path": snapshot.relative_path, "sha256": snapshot.sha256},
            field=label,
        ),
    )


def expanded_input_rows(
    contract: Any,
    artifacts: Mapping[str, Any],
    machine_reviews: Any,
    *,
    captured: Any,
    root: Path,
    legacy_loader: Any,
    legacy_verify: Any,
) -> dict[str, dict[str, str]]:
    """Return every direct and nested input row represented by one BOM."""
    rows = contract.artifact_inventory_snapshots(artifacts)
    rows.update(_machine_review_rows(machine_reviews))
    if captured is not None:
        inventory = captured.hash_inventory()
        for label in ("serp_raw_capture", "paa_raw_capture"):
            if label in inventory:
                rows[label] = inventory[label]
        return rows
    rows.update(_legacy_nested_rows(
        artifacts,
        root=root,
        legacy_loader=legacy_loader,
        legacy_verify=legacy_verify,
    ))
    return rows


def _machine_review_rows(value: Any) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    if not isinstance(value, Mapping):
        return rows
    for phase, row in value.items():
        if not isinstance(row, Mapping) or set(row) != {"path", "sha256"}:
            raise ValueError(f"machine_reviews.{phase} is invalid")
        rows[f"machine_reviews.{phase}"] = dict(row)
    return rows


def _legacy_nested_rows(
    artifacts: Mapping[str, Any],
    *,
    root: Path,
    legacy_loader: Any,
    legacy_verify: Any,
) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for source_label, nested_label in (
        ("serp_evidence", "serp_raw_capture"),
        ("paa_artifact", "paa_raw_capture"),
    ):
        source = artifacts.get(source_label)
        if not isinstance(source, Mapping):
            continue
        try:
            payload = json_artifact(
                None,
                source,
                field=f"artifacts.{source_label}",
                root=root,
                legacy_loader=legacy_loader,
                legacy_verify=legacy_verify,
            )
        except ValueError:
            continue
        nested = payload.get("raw_capture")
        if isinstance(nested, Mapping) and set(nested) == {"path", "sha256"}:
            rows[nested_label] = dict(nested)
    return rows


def check_machine_review_payload(
    guard: Any,
    payload: Mapping[str, Any],
    *,
    phase: str,
    article_sha256: str,
    editorial_plan_sha256: str,
    proof_sidecar_sha256: str,
) -> list[dict[str, Any]]:
    """Validate a machine review against captured input digests."""
    findings = list(guard["machine_review"].check_machine_review(payload))
    if payload.get("phase") != phase:
        findings.append(
            guard["machine_review"]._finding(
                "machine_review_phase_mismatch",
                "Machine review phase does not match the expected review phase.",
                "Pass the correct plan-review or article-review artifact.",
            )
        )
    bindings = (
        (
            "editorial_plan_sha256",
            editorial_plan_sha256,
            "machine_review_editorial_plan_hash_mismatch",
            "Machine review editorial-plan hash no longer matches the current file.",
        ),
        (
            "article_sha256",
            article_sha256,
            "machine_review_article_hash_mismatch",
            "Machine review article hash no longer matches the current file.",
        ),
        (
            "proof_sidecar_sha256",
            proof_sidecar_sha256,
            "machine_review_proof_sidecar_hash_mismatch",
            "Machine review proof-sidecar hash no longer matches the current file.",
        ),
    )
    for key, expected, rule_id, message in bindings:
        if payload.get(key) != expected:
            findings.append(
                guard["machine_review"]._finding(
                    rule_id,
                    message,
                    "Rerun all six reviewers against the current bytes.",
                )
            )
    return findings


def check_machine_review_pair_payloads(
    guard: Any,
    plan: Mapping[str, Any],
    article: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Validate pair provenance without reopening either review artifact."""
    findings: list[dict[str, Any]] = []
    for field in guard["machine_review"].PAIR_PROVENANCE_FIELDS:
        if plan.get(field) != article.get(field):
            findings.append(
                guard["machine_review"]._finding(
                    f"machine_review_pair_{field}_mismatch",
                    f"Plan and article machine reviews have different {field} values.",
                    "Rerun both review phases within the same command and workflow run.",
                )
            )
    return findings


def check_captured_machine_reviews(
    guard: Any,
    reviews: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    captured: Any,
) -> list[dict[str, Any]]:
    """Validate both machine reviews solely from session-owned snapshots."""
    required = {
        name: artifacts.get(name)
        for name in ("article", "editorial_plan", "validation_sidecar")
    }
    if any(not isinstance(row, Mapping) for row in required.values()):
        return [
            guard["_finding"](
                "bom_machine_reviews_inputs_missing",
                "Machine reviews require bound article, editorial_plan, and validation_sidecar artifacts.",
            )
        ]
    try:
        article = captured.snapshot_row(required["article"], field="artifacts.article")
        plan = captured.snapshot_row(
            required["editorial_plan"], field="artifacts.editorial_plan"
        )
        sidecar = captured.snapshot_row(
            required["validation_sidecar"], field="artifacts.validation_sidecar"
        )
    except ValueError as error:
        return [
            guard["_finding"](
                "bom_machine_reviews_inputs_invalid",
                f"Machine review inputs are invalid: {error}",
            )
        ]
    payloads: dict[str, Mapping[str, Any]] = {}
    findings: list[dict[str, Any]] = []
    for phase in ("plan", "article"):
        row = reviews.get(phase)
        try:
            payload = captured.json_row_copy(
                row, field=f"machine_reviews.{phase}",
            )
        except ValueError as error:
            findings.append(
                guard["_finding"](
                    "bom_machine_review_artifact_invalid",
                    f"Machine review {phase} artifact is invalid: {error}",
                )
            )
            continue
        payloads[phase] = payload
        review_findings = check_machine_review_payload(
            guard,
            payload,
            phase=phase,
            article_sha256=article.sha256,
            editorial_plan_sha256=plan.sha256,
            proof_sidecar_sha256=sidecar.sha256,
        )
        findings.extend(_wrap_machine_findings(guard, review_findings))
    if set(payloads) == {"plan", "article"}:
        findings.extend(
            _wrap_machine_findings(
                guard,
                check_machine_review_pair_payloads(
                    guard, payloads["plan"], payloads["article"]
                ),
            )
        )
    return findings


def sidecar_binding_errors(
    contract: Any,
    sidecar_content: str,
    artifacts: Mapping[str, Any],
    *,
    captured: Any,
    root: Path,
    required: bool,
) -> list[tuple[str, str]]:
    """Validate sidecar evidence bindings without reopening Fred evidence."""
    if captured is None:
        return contract.sidecar_evidence_binding_errors(
            sidecar_content, artifacts, workspace_root=root, required=required,
        )
    if not required:
        return []
    errors: list[tuple[str, str]] = []
    selector = artifacts.get("customer_proof_selector_evidence")
    matches = list(contract.SELECTOR_EVIDENCE_LINE_RE.finditer(sidecar_content))
    if len(matches) != 1:
        errors.append((
            "bom_customer_proof_evidence_binding_missing",
            "Connector-bound sidecar must contain exactly one selector evidence path/hash binding.",
        ))
    elif not isinstance(selector, Mapping) or (
        matches[0].group(1).strip().strip("\"'") != selector.get("path")
        or matches[0].group(2) != selector.get("sha256")
    ):
        errors.append((
            "bom_customer_proof_evidence_binding_mismatch",
            "Sidecar selector evidence path/hash does not match the BOM inventory.",
        ))
    fred = artifacts.get("fred_authority_evidence")
    sections = [
        match.group(0).strip()
        for match in contract.FRED_SELECTION_SECTION_RE.finditer(sidecar_content)
    ]
    if len(sections) != 1:
        errors.append((
            "bom_fred_evidence_binding_missing",
            "Connector-bound sidecar must contain exactly one Fred Voccola Authority Selection block.",
        ))
    elif not isinstance(fred, Mapping):
        errors.append((
            "bom_fred_evidence_binding_mismatch",
            "Fred selection evidence has no matching BOM artifact.",
        ))
    else:
        try:
            fred_content = _logical_text(
                captured.text_row(
                    fred, field="artifacts.fred_authority_evidence",
                )
            )
        except ValueError:
            fred_content = ""
        if not fred_content or fred_content != _logical_text(sections[0]):
            errors.append((
                "bom_fred_evidence_binding_mismatch",
                "Sidecar Fred selection block does not exactly match the BOM evidence artifact.",
            ))
    return errors


def _logical_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def _wrap_machine_findings(
    guard: Any,
    findings: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        guard["_finding"](
            str(finding.get("rule_id") or "machine_review_invalid"),
            str(finding.get("message") or "Machine review is invalid."),
        )
        for finding in findings
    ]


def load_primary_artifacts(
    guard: Any,
    *,
    captured: Any,
    artifacts: Mapping[str, Any],
    article_path: str | Path,
    validation_sidecar_path: str | Path,
    root: Path,
) -> tuple[Any, str, Mapping[str, Any] | None, bool, bool, list[dict[str, Any]]]:
    """Load article, sidecar, and plan from a session or legacy file adapters."""
    if captured is not None:
        return (
            captured.markdown_view("article"),
            captured.text("validation_sidecar"),
            captured.json_object("editorial_plan"),
            True,
            True,
            [],
        )
    article = None
    sidecar_content = ""
    findings: list[dict[str, Any]] = []
    article_input_safe = guard["_is_workspace_file"](article_path, root)
    sidecar_input_safe = guard["_is_workspace_file"](validation_sidecar_path, root)
    if article_input_safe:
        try:
            article = guard["read_publishable_markdown"](article_path)
        except (OSError, UnicodeError, guard["FrontmatterError"]) as error:
            findings.append(guard["_finding"](
                "bom_article_unreadable",
                f"Article cannot be read: {error}",
            ))
    if sidecar_input_safe:
        try:
            sidecar_content = Path(validation_sidecar_path).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            findings.append(guard["_finding"](
                "bom_sidecar_unreadable",
                f"Sidecar cannot be read: {error}",
            ))
    return (
        article,
        sidecar_content,
        guard["_load_bound_editorial_plan"](artifacts, root),
        article_input_safe,
        sidecar_input_safe,
        findings,
    )


__all__ = [
    "json_artifact",
    "check_machine_review_pair_payloads",
    "check_machine_review_payload",
    "check_captured_machine_reviews",
    "load_primary_artifacts",
    "json_snapshot",
    "optional_text",
    "expanded_input_rows",
    "sidecar_binding_errors",
    "text_artifact",
    "verify_artifact",
]
