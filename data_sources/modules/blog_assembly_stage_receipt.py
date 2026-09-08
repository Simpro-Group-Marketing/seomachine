"""Create and validate audit-grade blog workflow stage receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Collection, Mapping, Sequence

try:
    from .blog_assembly_contract import (
        atomic_write_json,
        canonical_json_sha256,
        file_sha256,
        validate_sha256,
    )
    from .execution_attestation import attest_mapping, verify_mapping_attestation
    from .guard_common import Finding, make_finding
except ImportError:  # pragma: no cover - supports direct script execution.
    from blog_assembly_contract import (
        atomic_write_json,
        canonical_json_sha256,
        file_sha256,
        validate_sha256,
    )
    from execution_attestation import attest_mapping, verify_mapping_attestation
    from guard_common import Finding, make_finding


STAGE_RECEIPT_SCHEMA = "simpro-blog-stage-receipt/v1"
STAGE_EVIDENCE_SCHEMA = "simpro-blog-stage-evidence/v1"
STAGE_RECEIPT_ATTESTATION_PURPOSE = "simpro-blog-stage-receipt/v1"
NORMAL_STAGE_SEQUENCE = (
    "draft",
    "scrub",
    "context_binding",
    "preflight_readiness",
    "final_readiness_attestation",
)
OPTIMIZED_STAGE_SEQUENCE = (
    "draft",
    "scrub",
    "context_binding",
    "preflight_readiness",
    "optimization",
    "post_optimization_scrub",
    "post_optimization_context_binding",
    "final_preflight_readiness",
    "final_readiness_attestation",
)
OPTIMIZED_TAIL_STAGE_SEQUENCE = (
    "post_optimization_scrub",
    "post_optimization_context_binding",
    "final_preflight_readiness",
    "final_readiness_attestation",
)
STAGES = tuple(dict.fromkeys((*NORMAL_STAGE_SEQUENCE, *OPTIMIZED_STAGE_SEQUENCE)))
DETERMINISTIC_TOOLS = {
    "scrub": ("content_scrubber", "1.0.0"),
    "post_optimization_scrub": ("content_scrubber", "1.0.0"),
    "context_binding": ("context_binding_generator", "1.0.0"),
    "post_optimization_context_binding": ("context_binding_generator", "1.0.0"),
    "preflight_readiness": ("publish_readiness", "1.0.0"),
    "final_preflight_readiness": ("publish_readiness", "1.0.0"),
    "final_readiness_attestation": ("publish_readiness", "1.0.0"),
}
NON_MUTATING_STAGES = frozenset(
    {
        "context_binding",
        "preflight_readiness",
        "post_optimization_context_binding",
        "final_preflight_readiness",
        "final_readiness_attestation",
    }
)
RFC3339_UTC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)
RECEIPT_FIELDS = frozenset(
    {
        "schema",
        "run_id",
        "stage",
        "tool",
        "started_at",
        "completed_at",
        "status",
        "mutation",
        "input_artifact_hashes",
        "output_artifact_hashes",
        "evidence_hashes",
        "previous_receipt_hash",
        "execution_attestation",
        "receipt_hash",
    }
)
TOOL_FIELDS = frozenset({"name", "version"})
MUTATING_STAGES = frozenset({"draft", "optimization"})
NATIVE_EDIT_STATE_SCHEMA = "simpro-blog-native-edit-state/v1"
CONSUMED_NATIVE_EDIT_STATE_SCHEMA = "simpro-blog-native-edit-state-consumed/v1"
EMPTY_ARTICLE_SHA256 = hashlib.sha256(b"").hexdigest()
NATIVE_EDIT_STATE_FIELDS = frozenset(
    {
        "schema",
        "article_path",
        "article_existed",
        "run_id",
        "stage",
        "tool",
        "started_at",
        "input_artifact_hashes",
        "previous_receipt_hash",
        "state_hash",
    }
)


class StageReceiptError(ValueError):
    """A stage receipt could not be created under the strict contract."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def begin_native_edit(
    *,
    article_path: str | Path,
    state_path: str | Path,
    run_id: str,
    stage: str,
    tool_name: str,
    tool_version: str,
    input_artifacts: Mapping[str, str | Path] | None = None,
    previous_receipt_hash: str = "",
    started_at: datetime | str | None = None,
) -> dict[str, Any]:
    """Snapshot a native-owned draft or optimization without writing article copy."""
    if stage not in MUTATING_STAGES:
        raise StageReceiptError(
            "native_edit_stage_invalid",
            "native edit stage must be draft or optimization",
        )
    article = Path(article_path).resolve(strict=False)
    if article.exists() and not article.is_file():
        raise StageReceiptError(
            "native_edit_article_invalid",
            "article path must be a regular file",
        )
    article_existed = article.is_file()
    if stage == "optimization" and not article_existed:
        raise StageReceiptError(
            "native_edit_article_missing",
            "optimization must start from an existing article",
        )
    destination = Path(state_path).resolve(strict=False)
    if destination.exists():
        raise StageReceiptError(
            "native_edit_state_exists",
            "native edit state output already exists",
        )
    supplied_inputs = dict(input_artifacts or {})
    if "article" in supplied_inputs:
        raise StageReceiptError(
            "native_edit_input_invalid",
            "article is a reserved input artifact label",
        )
    _reject_path_collision(destination, {"article": article, **supplied_inputs})
    inputs: dict[str, str] = {}
    try:
        for label, path in sorted(supplied_inputs.items()):
            inputs[_required_text(label, "native_edit_input_invalid", "input label")] = file_sha256(path)
    except OSError as error:
        raise StageReceiptError("native_edit_input_invalid", str(error)) from error
    inputs["article"] = file_sha256(article) if article_existed else EMPTY_ARTICLE_SHA256
    started_text = _native_edit_time(started_at)
    previous = previous_receipt_hash or ""
    if previous:
        try:
            validate_sha256(previous, field="previous_receipt_hash")
        except ValueError as error:
            raise StageReceiptError("native_edit_previous_hash_invalid", str(error)) from error
    state: dict[str, Any] = {
        "schema": NATIVE_EDIT_STATE_SCHEMA,
        "article_path": article.as_posix(),
        "article_existed": article_existed,
        "run_id": _required_text(run_id, "native_edit_run_id_invalid", "run_id"),
        "stage": stage,
        "tool": {
            "name": _required_text(tool_name, "native_edit_tool_invalid", "tool_name"),
            "version": _required_text(tool_version, "native_edit_tool_invalid", "tool_version"),
        },
        "started_at": started_text,
        "input_artifact_hashes": dict(sorted(inputs.items())),
        "previous_receipt_hash": previous,
    }
    state["state_hash"] = canonical_json_sha256(state)
    atomic_write_json(destination, state)
    return state


def finish_native_edit(
    *,
    state_path: str | Path,
    article_path: str | Path,
    receipt_path: str | Path,
    evidence_artifacts: Mapping[str, str | Path] | None = None,
    completed_at: datetime | str | None = None,
    workspace_root: str | Path | None = None,
) -> dict[str, Any]:
    """Close a native edit and write only its detached governance receipt."""
    state_source = Path(state_path).resolve(strict=False)
    try:
        state = json.loads(state_source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise StageReceiptError("native_edit_state_invalid", str(error)) from error
    state = _validate_native_edit_state(state)
    article = Path(article_path).resolve(strict=False)
    if _path_identity(article) != _path_identity(state["article_path"]):
        raise StageReceiptError(
            "native_edit_article_mismatch",
            "native edit must finish against the same article",
        )
    if not article.is_file():
        raise StageReceiptError(
            "native_edit_article_missing",
            "native edit output article is unavailable",
        )
    destination = Path(receipt_path).resolve(strict=False)
    if destination.exists():
        raise StageReceiptError(
            "native_edit_receipt_exists",
            "native edit receipt output already exists",
        )
    evidence = dict(evidence_artifacts or {})
    _reject_path_collision(
        destination,
        {"article": article, "state": state_source, **evidence},
    )
    after_hash = file_sha256(article)
    before_hash = state["input_artifact_hashes"]["article"]
    if before_hash == after_hash:
        raise StageReceiptError(
            "native_edit_unchanged",
            "native edit did not change the article",
        )
    try:
        evidence_hashes = {
            _required_text(label, "native_edit_evidence_invalid", "evidence label"): file_sha256(path)
            for label, path in sorted(evidence.items())
        }
    except OSError as error:
        raise StageReceiptError("native_edit_evidence_invalid", str(error)) from error
    tool = state["tool"]
    completed_text = _native_edit_time(completed_at)
    receipt = build_stage_receipt(
        run_id=state["run_id"],
        stage=state["stage"],
        tool_name=tool["name"],
        tool_version=tool["version"],
        started_at=state["started_at"],
        completed_at=completed_text,
        mutation=True,
        input_artifact_hashes=state["input_artifact_hashes"],
        output_artifact_hashes={"article": after_hash},
        evidence_hashes=evidence_hashes,
        previous_receipt_hash=state["previous_receipt_hash"],
        workspace_root=workspace_root,
    )
    write_stage_receipt(destination, receipt, workspace_root=workspace_root)
    atomic_write_json(
        state_source,
        {
            "schema": CONSUMED_NATIVE_EDIT_STATE_SCHEMA,
            "active_state_hash": state["state_hash"],
            "receipt_hash": receipt["receipt_hash"],
            "receipt_sha256": file_sha256(destination),
            "consumed_at": completed_text,
        },
    )
    return receipt


def build_stage_receipt(
    *,
    run_id: str,
    stage: str,
    tool_name: str,
    tool_version: str,
    started_at: datetime | str,
    completed_at: datetime | str,
    mutation: bool,
    input_artifact_hashes: Mapping[str, str],
    output_artifact_hashes: Mapping[str, str],
    evidence_hashes: Mapping[str, str] | None = None,
    previous_receipt_hash: str | None = None,
    workspace_root: str | Path | None = None,
) -> dict[str, Any]:
    """Build one complete receipt from real start and finish observations."""
    normalized_run_id = _required_text(run_id, "stage_receipt_run_id_invalid", "run_id")
    if stage not in STAGES:
        raise StageReceiptError("stage_receipt_stage_invalid", "stage is not a closed workflow stage")
    normalized_tool_name = _required_text(
        tool_name,
        "stage_receipt_tool_invalid",
        "tool_name",
    )
    normalized_tool_version = _required_text(
        tool_version,
        "stage_receipt_tool_invalid",
        "tool_version",
    )
    if not isinstance(mutation, bool):
        raise StageReceiptError("stage_receipt_mutation_invalid", "mutation must be a boolean")
    started_text, started = _timestamp(started_at, "started_at")
    completed_text, completed = _timestamp(completed_at, "completed_at")
    if completed <= started:
        raise StageReceiptError(
            "stage_receipt_timestamp_order_invalid",
            "completed_at must be strictly later than started_at",
        )
    inputs = _hash_mapping(
        input_artifact_hashes,
        code="stage_receipt_input_hash_invalid",
        field="input_artifact_hashes",
    )
    outputs = _hash_mapping(
        output_artifact_hashes,
        code="stage_receipt_output_hash_invalid",
        field="output_artifact_hashes",
    )
    evidence = _hash_mapping(
        evidence_hashes or {},
        code="stage_receipt_evidence_hash_invalid",
        field="evidence_hashes",
    )
    previous = previous_receipt_hash or ""
    if previous:
        try:
            validate_sha256(previous, field="previous_receipt_hash")
        except ValueError as error:
            raise StageReceiptError("stage_receipt_previous_hash_invalid", str(error)) from error
    payload: dict[str, Any] = {
        "schema": STAGE_RECEIPT_SCHEMA,
        "run_id": normalized_run_id,
        "stage": stage,
        "tool": {
            "name": normalized_tool_name,
            "version": normalized_tool_version,
        },
        "started_at": started_text,
        "completed_at": completed_text,
        "status": "completed",
        "mutation": mutation,
        "input_artifact_hashes": inputs,
        "output_artifact_hashes": outputs,
        "evidence_hashes": evidence,
        "previous_receipt_hash": previous,
    }
    payload = attest_mapping(
        payload,
        purpose=STAGE_RECEIPT_ATTESTATION_PURPOSE,
        workspace_root=workspace_root,
    )
    payload["receipt_hash"] = receipt_hash(payload)
    findings = check_stage_receipt(payload, workspace_root=workspace_root)
    if findings:
        first = findings[0]
        raise StageReceiptError(str(first["rule_id"]), str(first.get("message") or "invalid receipt"))
    return payload


def receipt_hash(receipt: Mapping[str, Any]) -> str:
    """Hash canonical receipt JSON while excluding the self-hash field."""
    payload = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_stage_receipt(
    path: str | Path,
    receipt: Mapping[str, Any],
    *,
    workspace_root: str | Path | None = None,
) -> None:
    """Validate and atomically persist one receipt."""
    findings = check_stage_receipt(receipt, workspace_root=workspace_root)
    if findings:
        first = findings[0]
        raise StageReceiptError(str(first["rule_id"]), str(first.get("message") or "invalid receipt"))
    atomic_write_json(path, receipt)


def load_stage_receipt(
    path: str | Path,
    *,
    workspace_root: str | Path | None = None,
) -> dict[str, Any]:
    """Load one receipt and reject invalid JSON or contract drift."""
    try:
        value = load_json_object_snapshot(path, field="stage receipt").payload
    except ValueError as error:
        raise StageReceiptError("stage_receipt_file_invalid", str(error)) from error
    findings = check_stage_receipt(value, workspace_root=workspace_root)
    if findings:
        first = findings[0]
        raise StageReceiptError(str(first["rule_id"]), str(first.get("message") or "invalid receipt"))
    return value


def check_stage_receipt(
    receipt: Any,
    *,
    expected_stage: str | None = None,
    expected_tool_name: str | None = None,
    expected_tool_version: str | None = None,
    workspace_root: str | Path | None = None,
) -> list[Finding]:
    """Return stable findings for one in-memory receipt."""
    if not isinstance(receipt, Mapping):
        return [_finding("stage_receipt_invalid", "Stage receipt must be an object.")]
    findings: list[Finding] = []
    actual_fields = set(receipt)
    if actual_fields != RECEIPT_FIELDS:
        missing = sorted(RECEIPT_FIELDS - actual_fields)
        unknown = sorted(actual_fields - RECEIPT_FIELDS)
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if unknown:
            details.append("unknown " + ", ".join(unknown))
        findings.append(
            _finding(
                "stage_receipt_shape_invalid",
                "Stage receipt must use the exact v1 field set ("
                + "; ".join(details)
                + ").",
            )
        )
    if receipt.get("schema") != STAGE_RECEIPT_SCHEMA:
        findings.append(_finding("stage_receipt_schema_invalid", f"Stage receipt must use {STAGE_RECEIPT_SCHEMA}."))
    if not verify_mapping_attestation(
        receipt,
        purpose=STAGE_RECEIPT_ATTESTATION_PURPOSE,
        workspace_root=workspace_root,
        excluded_fields=("receipt_hash",),
    ):
        findings.append(
            _finding(
                "stage_receipt_execution_attestation_invalid",
                "Stage receipt lacks a valid workspace execution attestation.",
            )
        )
    run_id = receipt.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        findings.append(_finding("stage_receipt_run_id_invalid", "Stage receipt run_id is required."))
    stage = receipt.get("stage")
    if stage not in STAGES:
        findings.append(_finding("stage_receipt_stage_invalid", "Stage receipt stage is invalid."))
    if expected_stage is not None and stage != expected_stage:
        findings.append(_finding("stage_receipt_stage_mismatch", "Stage receipt does not match the expected stage."))
    tool = receipt.get("tool")
    if not isinstance(tool, Mapping):
        findings.append(_finding("stage_receipt_tool_invalid", "Stage receipt tool must contain name and version."))
        tool_name = tool_version = ""
    else:
        if set(tool) != TOOL_FIELDS:
            findings.append(
                _finding(
                    "stage_receipt_tool_invalid",
                    "Stage receipt tool must contain exactly name and version.",
                )
            )
        tool_name = tool.get("name")
        tool_version = tool.get("version")
        if not isinstance(tool_name, str) or not tool_name.strip() or not isinstance(tool_version, str) or not tool_version.strip():
            findings.append(_finding("stage_receipt_tool_invalid", "Stage receipt tool name and version are required."))
    if stage in DETERMINISTIC_TOOLS and (tool_name, tool_version) != DETERMINISTIC_TOOLS[stage]:
        findings.append(_finding("stage_receipt_tool_invalid", "Deterministic stage uses the wrong tool identity."))
    if expected_tool_name is not None and tool_name != expected_tool_name:
        findings.append(_finding("stage_receipt_tool_mismatch", "Stage receipt tool name does not match."))
    if expected_tool_version is not None and tool_version != expected_tool_version:
        findings.append(_finding("stage_receipt_tool_mismatch", "Stage receipt tool version does not match."))
    if receipt.get("status") != "completed":
        findings.append(_finding("stage_receipt_status_invalid", "Stage receipt status must be completed."))
    mutation = receipt.get("mutation")
    if not isinstance(mutation, bool):
        findings.append(_finding("stage_receipt_mutation_invalid", "Stage receipt mutation must be boolean."))

    parsed_times: list[datetime] = []
    for field in ("started_at", "completed_at"):
        try:
            _, parsed = _timestamp(receipt.get(field), field)
        except StageReceiptError:
            findings.append(_finding("stage_receipt_timestamp_invalid", f"Stage receipt {field} must be RFC 3339 UTC."))
        else:
            parsed_times.append(parsed)
    if len(parsed_times) == 2 and parsed_times[1] <= parsed_times[0]:
        findings.append(_finding("stage_receipt_timestamp_order_invalid", "completed_at must be strictly later than started_at."))

    mappings: dict[str, Mapping[str, Any]] = {}
    for field, code in (
        ("input_artifact_hashes", "stage_receipt_input_hash_invalid"),
        ("output_artifact_hashes", "stage_receipt_output_hash_invalid"),
        ("evidence_hashes", "stage_receipt_evidence_hash_invalid"),
    ):
        value = receipt.get(field)
        if not isinstance(value, Mapping):
            findings.append(_finding(code, f"Stage receipt {field} must be a hash object."))
            continue
        mappings[field] = value
        for label, digest in value.items():
            if not isinstance(label, str) or not label.strip():
                findings.append(_finding(code, f"Stage receipt {field} has an invalid label."))
                continue
            try:
                validate_sha256(digest, field=f"{field}.{label}")
            except ValueError as error:
                findings.append(_finding(code, str(error)))
    previous = receipt.get("previous_receipt_hash")
    if not isinstance(previous, str):
        findings.append(_finding("stage_receipt_previous_hash_invalid", "previous_receipt_hash must be a string."))
    elif previous:
        try:
            validate_sha256(previous, field="previous_receipt_hash")
        except ValueError as error:
            findings.append(_finding("stage_receipt_previous_hash_invalid", str(error)))
    stored_hash = receipt.get("receipt_hash")
    try:
        validate_sha256(stored_hash, field="receipt_hash")
    except ValueError as error:
        findings.append(_finding("stage_receipt_hash_invalid", str(error)))
    else:
        if stored_hash != receipt_hash(receipt):
            findings.append(_finding("stage_receipt_hash_mismatch", "Stage receipt canonical hash is invalid."))

    inputs = mappings.get("input_artifact_hashes", {})
    outputs = mappings.get("output_artifact_hashes", {})
    article_in = inputs.get("article")
    article_out = outputs.get("article")
    if not article_out:
        findings.append(
            _finding(
                "stage_receipt_article_output_missing",
                "Every closed stage must bind its output article hash.",
            )
        )
    if not article_in:
        findings.append(
            _finding(
                "stage_receipt_article_input_missing",
                "Every closed stage must bind its input article hash.",
            )
        )
    if stage in MUTATING_STAGES and mutation is not True:
        findings.append(
            _finding(
                "stage_receipt_mutation_required",
                "Draft and optimization receipts must record a real mutation.",
            )
        )
    if stage in NON_MUTATING_STAGES and mutation is True:
        findings.append(_finding("stage_receipt_mutation_forbidden", "This deterministic stage cannot mutate the article."))
    if mutation is False and article_in and article_out and article_in != article_out:
        findings.append(_finding("stage_receipt_mutation_semantics_invalid", "A no-change receipt cannot change the article hash."))
    if mutation is True and article_in and article_out and article_in == article_out:
        findings.append(_finding("stage_receipt_mutation_semantics_invalid", "A mutation receipt must change the article hash."))
    return _sorted(findings)


def check_stage_receipt_file(path: str | Path, **expected: Any) -> list[Finding]:
    """Return findings for one receipt file without leaking raw exceptions."""
    try:
        value = load_json_object_snapshot(path, field="stage receipt").payload
    except ValueError as error:
        return [_finding("stage_receipt_file_invalid", str(error))]
    return check_stage_receipt(value, **expected)


def check_receipt_chain(
    receipts: Any,
    *,
    workspace_root: str | Path | None = None,
    expected_run_id: str | None = None,
    assembly_date: str | date | None = None,
    now: datetime | None = None,
    resolvable_evidence_hashes: Collection[str] | None = None,
) -> list[Finding]:
    """Validate global order, time, hash, and article continuity."""
    if not isinstance(receipts, list) or not all(isinstance(item, Mapping) for item in receipts):
        return [_finding("stage_receipt_chain_invalid", "Receipt chain must be a list of objects.")]
    if not receipts:
        return [_finding("stage_receipt_chain_empty", "Receipt chain cannot be empty.")]
    findings: list[Finding] = []
    for receipt in receipts:
        findings.extend(
            check_stage_receipt(receipt, workspace_root=workspace_root)
        )
    stages = tuple(str(receipt.get("stage") or "") for receipt in receipts)
    valid_prefix = any(
        stages == sequence[: len(stages)]
        for sequence in (
            NORMAL_STAGE_SEQUENCE,
            OPTIMIZED_STAGE_SEQUENCE,
            OPTIMIZED_TAIL_STAGE_SEQUENCE,
        )
    )
    if not valid_prefix:
        findings.append(_finding("stage_receipt_stage_order_invalid", "Receipt stages must follow the closed workflow order."))
    run_ids = {receipt.get("run_id") for receipt in receipts}
    if len(run_ids) != 1:
        findings.append(_finding("stage_receipt_run_id_mismatch", "All receipts in a chain must share one run_id."))
    if expected_run_id is not None and run_ids != {expected_run_id}:
        findings.append(_finding("stage_receipt_run_id_mismatch", "Receipt run_id does not match the canonical article run identity."))
    parsed_assembly_date = _assembly_date(assembly_date)
    observed_now = _now(now)
    if observed_now is None:
        findings.append(
            _finding(
                "stage_receipt_clock_invalid",
                "Injected receipt validation clock must be timezone-aware UTC.",
            )
        )
    for index, receipt in enumerate(receipts):
        try:
            _, started = _timestamp(receipt.get("started_at"), "started_at")
            _, completed = _timestamp(receipt.get("completed_at"), "completed_at")
        except StageReceiptError:
            started = completed = None
        if completed is not None and observed_now is not None and completed > observed_now:
            findings.append(_finding("stage_receipt_timestamp_future", "Receipt completion time cannot be in the future."))
        if (
            started is not None
            and parsed_assembly_date is not None
            and started.date() != parsed_assembly_date
        ):
            findings.append(_finding("stage_receipt_stale", "Receipt execution must occur on the BOM assembly date."))
        if resolvable_evidence_hashes is not None:
            evidence = receipt.get("evidence_hashes")
            if isinstance(evidence, Mapping):
                for label, digest in evidence.items():
                    if digest not in resolvable_evidence_hashes:
                        findings.append(
                            _finding(
                                "stage_receipt_evidence_unresolved",
                                f"Receipt evidence {label} does not resolve to a current artifact or repository definition.",
                            )
                        )
        previous = str(receipt.get("previous_receipt_hash") or "")
        if index == 0:
            if previous and not stages == OPTIMIZED_TAIL_STAGE_SEQUENCE[: len(stages)]:
                findings.append(_finding("stage_receipt_previous_hash_mismatch", "First receipt cannot name a predecessor."))
            continue
        prior = receipts[index - 1]
        if previous != prior.get("receipt_hash"):
            findings.append(_finding("stage_receipt_previous_hash_mismatch", "Receipt predecessor hash chain is broken."))
        try:
            _, prior_completed = _timestamp(prior.get("completed_at"), "completed_at")
            _, current_started = _timestamp(receipt.get("started_at"), "started_at")
        except StageReceiptError:
            pass
        else:
            if current_started <= prior_completed:
                findings.append(_finding("stage_receipt_timestamps_not_monotonic", "Receipt timestamps must be globally monotonic."))
        prior_outputs = prior.get("output_artifact_hashes")
        current_inputs = receipt.get("input_artifact_hashes")
        prior_article = prior_outputs.get("article") if isinstance(prior_outputs, Mapping) else None
        current_article = current_inputs.get("article") if isinstance(current_inputs, Mapping) else None
        if prior_article and current_article != prior_article:
            findings.append(_finding("stage_receipt_article_chain_broken", "Article hashes are not continuous between stages."))
    return _sorted(findings)


def _assembly_date(value: str | date | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return None
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _now(value: datetime | None) -> datetime | None:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        return None
    return value.astimezone(timezone.utc)


def _hash_mapping(value: Any, *, code: str, field: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise StageReceiptError(code, f"{field} must be an object")
    result: dict[str, str] = {}
    for label, digest in value.items():
        if not isinstance(label, str) or not label.strip():
            raise StageReceiptError(code, f"{field} labels must be non-empty strings")
        try:
            result[label.strip()] = validate_sha256(digest, field=f"{field}.{label}")
        except ValueError as error:
            raise StageReceiptError(code, str(error)) from error
    return dict(sorted(result.items()))


def _validate_native_edit_state(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping) and value.get("schema") == CONSUMED_NATIVE_EDIT_STATE_SCHEMA:
        raise StageReceiptError(
            "native_edit_state_consumed",
            "native edit state was already consumed",
        )
    if not isinstance(value, Mapping) or set(value) != NATIVE_EDIT_STATE_FIELDS:
        raise StageReceiptError(
            "native_edit_state_invalid",
            "native edit state must use the exact field set",
        )
    if value.get("schema") != NATIVE_EDIT_STATE_SCHEMA:
        raise StageReceiptError("native_edit_state_invalid", "native edit state schema is invalid")
    expected_hash = canonical_json_sha256(
        {key: child for key, child in value.items() if key != "state_hash"}
    )
    if value.get("state_hash") != expected_hash:
        raise StageReceiptError("native_edit_state_invalid", "native edit state hash is invalid")
    if value.get("stage") not in MUTATING_STAGES:
        raise StageReceiptError("native_edit_state_invalid", "native edit state stage is invalid")
    if not isinstance(value.get("article_existed"), bool):
        raise StageReceiptError("native_edit_state_invalid", "article_existed must be boolean")
    _required_text(value.get("article_path"), "native_edit_state_invalid", "article_path")
    _required_text(value.get("run_id"), "native_edit_state_invalid", "run_id")
    _timestamp(value.get("started_at"), "started_at")
    tool = value.get("tool")
    if not isinstance(tool, Mapping) or set(tool) != TOOL_FIELDS:
        raise StageReceiptError("native_edit_state_invalid", "native edit tool is invalid")
    _required_text(tool.get("name"), "native_edit_state_invalid", "tool name")
    _required_text(tool.get("version"), "native_edit_state_invalid", "tool version")
    inputs = value.get("input_artifact_hashes")
    if not isinstance(inputs, Mapping) or "article" not in inputs:
        raise StageReceiptError("native_edit_state_invalid", "native edit input hashes are invalid")
    _hash_mapping(
        inputs,
        code="native_edit_state_invalid",
        field="input_artifact_hashes",
    )
    previous = value.get("previous_receipt_hash")
    if not isinstance(previous, str):
        raise StageReceiptError("native_edit_state_invalid", "previous receipt hash is invalid")
    if previous:
        try:
            validate_sha256(previous, field="previous_receipt_hash")
        except ValueError as error:
            raise StageReceiptError("native_edit_state_invalid", str(error)) from error
    return dict(value)


def _reject_path_collision(
    output_path: str | Path,
    inputs: Mapping[str, str | Path],
) -> None:
    destination = _path_identity(output_path)
    for label, path in inputs.items():
        if destination == _path_identity(path):
            raise StageReceiptError(
                "native_edit_output_collision",
                f"governance output cannot overwrite input {label}",
            )


def _path_identity(path: Any) -> str:
    if not isinstance(path, (str, Path)) or not str(path).strip():
        raise StageReceiptError("native_edit_path_invalid", "artifact path must be non-empty")
    return os.path.normcase(str(Path(path).resolve(strict=False)))


def _native_edit_time(value: datetime | str | None) -> str:
    if value is None:
        value = datetime.now(timezone.utc)
    text, _ = _timestamp(value, "native edit timestamp")
    return text


def _required_text(value: Any, code: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StageReceiptError(code, f"{field} must be a non-empty string")
    return value.strip()


def _timestamp(value: datetime | str | Any, field: str) -> tuple[str, datetime]:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise StageReceiptError("stage_receipt_timestamp_invalid", f"{field} must use UTC")
        normalized = value.astimezone(timezone.utc)
        text = normalized.isoformat().replace("+00:00", "Z")
        return text, normalized
    if not isinstance(value, str) or not RFC3339_UTC_RE.fullmatch(value):
        raise StageReceiptError("stage_receipt_timestamp_invalid", f"{field} must be RFC 3339 UTC")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise StageReceiptError("stage_receipt_timestamp_invalid", f"{field} is invalid") from error
    return value, parsed


def _sorted(findings: Sequence[Finding]) -> list[Finding]:
    unique: dict[tuple[str, str], Finding] = {}
    for finding in findings:
        key = (str(finding.get("rule_id")), str(finding.get("message")))
        unique[key] = finding
    return sorted(unique.values(), key=lambda item: (str(item["rule_id"]), str(item.get("message", ""))))


def _finding(rule_id: str, message: str) -> Finding:
    return make_finding(
        rule_id,
        "error",
        1,
        message=message,
        suggestion="Regenerate this receipt from the actual stage execution.",
    )


def _label_paths(values: Sequence[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise StageReceiptError(
                "native_edit_artifact_argument_invalid",
                "artifact arguments must use label=path",
            )
        label, path = value.split("=", 1)
        normalized = _required_text(
            label,
            "native_edit_artifact_argument_invalid",
            "artifact label",
        )
        if normalized in result:
            raise StageReceiptError(
                "native_edit_artifact_argument_invalid",
                f"duplicate artifact label: {normalized}",
            )
        result[normalized] = Path(
            _required_text(
                path,
                "native_edit_artifact_argument_invalid",
                "artifact path",
            )
        )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create and validate blog stage receipts.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    begin = subparsers.add_parser("begin-native-edit")
    begin.add_argument("--article", required=True)
    begin.add_argument("--state", required=True)
    begin.add_argument("--run-id", required=True)
    begin.add_argument("--stage", choices=sorted(MUTATING_STAGES), required=True)
    begin.add_argument("--tool-name", required=True)
    begin.add_argument("--tool-version", required=True)
    begin.add_argument("--input", action="append", default=[])
    begin.add_argument("--previous-receipt-hash", default="")
    finish = subparsers.add_parser("finish-native-edit")
    finish.add_argument("--article", required=True)
    finish.add_argument("--state", required=True)
    finish.add_argument("--receipt", required=True)
    finish.add_argument("--evidence", action="append", default=[])
    finish.add_argument("--workspace-root")
    args = parser.parse_args(argv)
    try:
        if args.command == "begin-native-edit":
            begin_native_edit(
                article_path=args.article,
                state_path=args.state,
                run_id=args.run_id,
                stage=args.stage,
                tool_name=args.tool_name,
                tool_version=args.tool_version,
                input_artifacts=_label_paths(args.input),
                previous_receipt_hash=args.previous_receipt_hash,
            )
        else:
            finish_native_edit(
                state_path=args.state,
                article_path=args.article,
                receipt_path=args.receipt,
                evidence_artifacts=_label_paths(args.evidence),
                workspace_root=args.workspace_root,
            )
    except (OSError, UnicodeError, StageReceiptError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
