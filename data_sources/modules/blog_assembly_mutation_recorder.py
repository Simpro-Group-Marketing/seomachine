"""Start/finish recorder for draft and manual/agent optimization mutations."""

from __future__ import annotations

import argparse
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from uuid import uuid4

try:
    from . import blog_assembly_capabilities
    from .blog_assembly_contract import (
        atomic_write_json,
        canonical_article_run_id,
        canonical_json_bytes,
        canonical_json_sha256,
        file_sha256,
        load_json_object_snapshot,
        validate_sha256,
    )
    from .blog_assembly_stage_receipt import build_stage_receipt
except ImportError:  # pragma: no cover - supports direct script execution.
    import blog_assembly_capabilities
    from blog_assembly_contract import (
        atomic_write_json,
        canonical_article_run_id,
        canonical_json_bytes,
        canonical_json_sha256,
        file_sha256,
        load_json_object_snapshot,
        validate_sha256,
    )
    from blog_assembly_stage_receipt import build_stage_receipt


MUTATION_STATE_SCHEMA = "simpro-blog-mutation-state/v1"
CONSUMED_STATE_SCHEMA = "simpro-blog-mutation-state-consumed/v1"
MUTATION_STAGES = frozenset({"draft", "optimization"})
MUTATION_STATE_FIELDS = frozenset(
    {
        "schema",
        "article_path",
        "workspace_root",
        "assembly_date",
        "run_id",
        "stage",
        "tool",
        "started_at",
        "input_artifact_hashes",
        "previous_receipt_hash",
        "state_hash",
    }
)
CONSUMED_STATE_FIELDS = frozenset(
    {
        "schema",
        "active_state_hash",
        "receipt_hash",
        "receipt_sha256",
        "consumed_at",
    }
)


def start_mutation(
    *,
    article_path: str | Path,
    state_path: str | Path,
    run_id: str | None = None,
    stage: str,
    tool_name: str,
    tool_version: str,
    input_artifacts: Mapping[str, str | Path] | None = None,
    previous_receipt_hash: str = "",
    started_at: datetime | str | None = None,
    workspace_root: str | Path | None = None,
    assembly_date: str | None = None,
) -> dict[str, Any]:
    """Persist the immutable before-state before any mutation can occur."""
    if stage not in MUTATION_STAGES:
        raise ValueError("mutation recorder stage must be draft or optimization")
    if workspace_root is None or assembly_date is None:
        raise ValueError("workspace_root and assembly_date are required")
    root = Path(workspace_root).resolve()
    if not root.is_dir():
        raise ValueError("workspace_root must be an existing directory")
    article = Path(article_path).resolve()
    _require_within_workspace(article, root, field="article")
    normalized_assembly_date = _canonical_assembly_date(assembly_date)
    normalized_run_id = canonical_article_run_id(
        article,
        workspace_root=root,
        assembly_date=normalized_assembly_date,
    )
    if run_id is not None and _required(run_id, "run_id") != normalized_run_id:
        raise ValueError("run_id must equal the canonical article run identity")
    normalized_tool_name = _required(tool_name, "tool_name")
    normalized_tool_version = _required(tool_version, "tool_version")
    tool_receipt = [
        {
            "stage": stage,
            "tool": {
                "name": normalized_tool_name,
                "version": normalized_tool_version,
            },
        }
    ]
    try:
        if stage == "draft":
            blog_assembly_capabilities.infer_route(tool_receipt)
        else:
            blog_assembly_capabilities.is_optimized(tool_receipt)
    except blog_assembly_capabilities.CapabilityRegistryError as error:
        expected = (
            "registered draft command"
            if stage == "draft"
            else "registered optimize command"
        )
        raise ValueError(f"mutation tool must be the {expected}: {error}") from error
    normalized_started_at = _time_text(started_at)
    supplied_inputs = dict(input_artifacts or {})
    if "article" in supplied_inputs:
        raise ValueError("reserved artifact label: article")
    _reject_output_collision(
        state_path,
        output_label="state",
        inputs={
            "article": article,
            **{f"input {label}": path for label, path in supplied_inputs.items()},
        },
    )
    state_destination = Path(state_path).resolve()
    _require_within_workspace(state_destination, root, field="mutation state")
    if state_destination.exists():
        raise ValueError("mutation state output already exists")
    inputs = {
        label: file_sha256(path)
        for label, path in sorted(supplied_inputs.items())
    }
    seed_created = False
    if not article.is_file():
        if stage != "draft":
            raise ValueError("optimization must start from an existing article")
        if article.exists():
            raise ValueError("draft article path must be a regular file")
        article.parent.mkdir(parents=True, exist_ok=True)
        try:
            with article.open("xb") as handle:
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError as error:
            raise ValueError("draft article appeared before seed initialization") from error
        seed_created = True
    try:
        inputs["article"] = file_sha256(article)
        state = {
            "schema": MUTATION_STATE_SCHEMA,
            "article_path": article.as_posix(),
            "workspace_root": root.as_posix(),
            "assembly_date": normalized_assembly_date,
            "run_id": normalized_run_id,
            "stage": stage,
            "tool": {
                "name": normalized_tool_name,
                "version": normalized_tool_version,
            },
            "started_at": normalized_started_at,
            "input_artifact_hashes": dict(sorted(inputs.items())),
            "previous_receipt_hash": previous_receipt_hash,
        }
        state["state_hash"] = canonical_json_sha256(state)
        _exclusive_write_json(
            state_destination,
            state,
            existing_message="mutation state output already exists",
        )
    except Exception:
        if seed_created and article.is_file() and article.stat().st_size == 0:
            article.unlink(missing_ok=True)
        raise
    return state


def finish_mutation(
    *,
    state_path: str | Path,
    article_path: str | Path,
    receipt_path: str | Path,
    evidence_artifacts: Mapping[str, str | Path] | None = None,
    completed_at: datetime | str | None = None,
) -> dict[str, Any]:
    """Close a mutation using the current after-state and write its receipt."""
    try:
        state = load_json_object_snapshot(
            state_path,
            field="mutation state",
        ).payload
    except ValueError as error:
        raise ValueError(f"mutation state is invalid: {error}") from error
    state = _validate_active_state(state)
    state_source = Path(state_path).resolve()
    workspace_root = Path(str(state["workspace_root"])).resolve()
    _require_within_workspace(
        state_source,
        workspace_root,
        field="mutation state",
    )
    article = Path(article_path).resolve()
    if _path_identity(article) != _path_identity(state.get("article_path")):
        raise ValueError("mutation must finish against the same article identity")
    if not article.is_file():
        raise ValueError("mutation output article is unavailable")
    supplied_evidence = dict(evidence_artifacts or {})
    receipt_destination = Path(receipt_path).resolve()
    _require_within_workspace(
        receipt_destination,
        workspace_root,
        field="mutation receipt",
    )
    for label, evidence_path in supplied_evidence.items():
        _require_within_workspace(
            Path(evidence_path).resolve(),
            workspace_root,
            field=f"mutation evidence {label}",
        )
    _reject_output_collision(
        receipt_path,
        output_label="receipt",
        inputs={
            "article": article,
            "state": state_source,
            **{
                f"evidence {label}": path
                for label, path in supplied_evidence.items()
            },
        },
    )
    if receipt_destination.exists():
        raise ValueError("mutation receipt output already exists")
    stage = str(state.get("stage") or "")
    definition_prefixes = (
        "command_definition.",
        "agent_definition.",
        "skill_definition.",
    )
    if any(label.startswith(definition_prefixes) for label in supplied_evidence):
        raise ValueError("repository definition evidence is resolved internally")
    supplied_agent_ids = {
        label.removeprefix("agent_output.")
        for label in supplied_evidence
        if label.startswith("agent_output.")
    }
    non_agent_labels = {
        label
        for label in supplied_evidence
        if not label.startswith("agent_output.")
    }
    if stage == "optimization":
        expected_agent_ids = set(blog_assembly_capabilities.OPTIMIZE_AGENT_IDS)
        if supplied_agent_ids != expected_agent_ids or non_agent_labels:
            raise ValueError(
                "optimization evidence must contain exactly one agent_output.<id> "
                "artifact for every invoked agent"
            )
        try:
            optimization_output_rows = (
                blog_assembly_capabilities.resolve_optimization_agent_outputs(
                    {
                        label.removeprefix("agent_output."): path
                        for label, path in supplied_evidence.items()
                    },
                    workspace_root=workspace_root,
                )
            )
        except blog_assembly_capabilities.CapabilityRegistryError as error:
            raise ValueError(f"optimization agent outputs are invalid: {error}") from error
    elif supplied_agent_ids:
        raise ValueError("agent output evidence is allowed only on optimization")
    after_hash = file_sha256(article)
    input_hashes = state.get("input_artifact_hashes")
    if not isinstance(input_hashes, Mapping):
        raise ValueError("mutation state input hashes are invalid")
    before_hash = input_hashes.get("article")
    if before_hash == after_hash:
        raise ValueError("recorded mutation did not change the article")
    evidence_hashes = {
        label: row["sha256"]
        for label, row in (
            optimization_output_rows.items()
            if stage == "optimization"
            else (
                (label, {"sha256": file_sha256(path)})
                for label, path in sorted(supplied_evidence.items())
            )
        )
    }
    tool = state.get("tool")
    if not isinstance(tool, Mapping):
        raise ValueError("mutation state tool is invalid")
    try:
        definitions = blog_assembly_capabilities.resolve_mutation_definition_evidence(
            stage=stage,
            tool_name=str(tool.get("name") or ""),
            tool_version=str(tool.get("version") or ""),
            workspace_root=workspace_root,
        )
    except blog_assembly_capabilities.CapabilityRegistryError as error:
        raise ValueError(f"mutation repository definitions are invalid: {error}") from error
    evidence_hashes.update(
        {
            label: row["sha256"]
            for label, row in definitions.items()
        }
    )
    completed_text = _time_text(completed_at)
    ledger_root = (
        workspace_root / ".seomachine" / "mutation-consumed"
    ).resolve()
    reservation = _reserve_state_hash(ledger_root, str(state["state_hash"]))
    receipt_written = False
    state_committed = False
    try:
        receipt = build_stage_receipt(
            run_id=str(state.get("run_id") or ""),
            stage=str(state.get("stage") or ""),
            tool_name=str(tool.get("name") or ""),
            tool_version=str(tool.get("version") or ""),
            started_at=str(state.get("started_at") or ""),
            completed_at=completed_text,
            mutation=True,
            input_artifact_hashes=dict(input_hashes),
            output_artifact_hashes={"article": after_hash},
            evidence_hashes=evidence_hashes,
            previous_receipt_hash=str(state.get("previous_receipt_hash") or ""),
        )
        _exclusive_write_json(
            receipt_destination,
            receipt,
            existing_message="mutation receipt output already exists",
        )
        receipt_written = True
        consumed = {
            "schema": CONSUMED_STATE_SCHEMA,
            "active_state_hash": str(state["state_hash"]),
            "receipt_hash": str(receipt["receipt_hash"]),
            "receipt_sha256": file_sha256(receipt_destination),
            "consumed_at": completed_text,
        }
        if set(consumed) != CONSUMED_STATE_FIELDS:  # pragma: no cover - invariant.
            raise RuntimeError("consumed mutation state shape drifted")
        atomic_write_json(state_source, consumed)
        state_committed = True
        atomic_write_json(
            reservation,
            {
                "schema": CONSUMED_STATE_SCHEMA,
                "active_state_hash": str(state["state_hash"]),
                "receipt_hash": str(receipt["receipt_hash"]),
                "receipt_sha256": file_sha256(receipt_destination),
                "consumed_at": completed_text,
                "status": "committed",
            },
        )
    except Exception:
        if receipt_written and not state_committed:
            receipt_destination.unlink(missing_ok=True)
        if not state_committed:
            reservation.unlink(missing_ok=True)
        raise
    return receipt


def mutation_ledger_entry_path(
    ledger_path: str | Path,
    state_hash: str,
) -> Path:
    """Return the durable replay-lock path for one validated state hash."""
    digest = validate_sha256(state_hash, field="state_hash")
    return Path(ledger_path).resolve() / f"{digest}.json"


def _reserve_state_hash(ledger_path: Path, state_hash: str) -> Path:
    entry = mutation_ledger_entry_path(ledger_path, state_hash)
    entry.parent.mkdir(parents=True, exist_ok=True)
    reservation = {
        "schema": "simpro-blog-mutation-state-reservation/v1",
        "active_state_hash": state_hash,
        "reservation_id": str(uuid4()),
        "status": "reserved",
    }
    try:
        with entry.open("xb") as handle:
            handle.write(canonical_json_bytes(reservation))
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as error:
        raise ValueError("mutation state was already consumed") from error
    return entry


def _validate_active_state(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping) and value.get("schema") == CONSUMED_STATE_SCHEMA:
        raise ValueError("mutation state was already consumed")
    if not isinstance(value, Mapping):
        raise ValueError("mutation state must be an object")
    if set(value) != MUTATION_STATE_FIELDS:
        raise ValueError("mutation state must use the exact field set")
    if value.get("schema") != MUTATION_STATE_SCHEMA:
        raise ValueError("mutation state schema is invalid")
    expected_hash = canonical_json_sha256(
        {key: child for key, child in value.items() if key != "state_hash"}
    )
    if value.get("state_hash") != expected_hash:
        raise ValueError("mutation state hash is invalid")
    if value.get("stage") not in MUTATION_STAGES:
        raise ValueError("mutation state stage is invalid")
    for field in (
        "article_path",
        "workspace_root",
        "assembly_date",
        "run_id",
        "started_at",
    ):
        _required(value.get(field), f"mutation state {field}")
    root_text = str(value["workspace_root"])
    root = Path(root_text).resolve()
    if root.as_posix() != root_text or not root.is_dir():
        raise ValueError("mutation state workspace_root is not canonical")
    article = Path(str(value["article_path"])).resolve()
    if article.as_posix() != value["article_path"]:
        raise ValueError("mutation state article_path is not canonical")
    _require_within_workspace(article, root, field="mutation state article")
    assembly_date = _canonical_assembly_date(str(value["assembly_date"]))
    expected_run_id = canonical_article_run_id(
        article,
        workspace_root=root,
        assembly_date=assembly_date,
    )
    if value.get("run_id") != expected_run_id:
        raise ValueError("mutation state run_id is not canonical")
    tool = value.get("tool")
    if not isinstance(tool, Mapping) or set(tool) != {"name", "version"}:
        raise ValueError("mutation state tool must contain exactly name and version")
    _required(tool.get("name"), "mutation state tool name")
    _required(tool.get("version"), "mutation state tool version")
    inputs = value.get("input_artifact_hashes")
    if not isinstance(inputs, Mapping) or "article" not in inputs:
        raise ValueError("mutation state input hashes are invalid")
    for label, digest in inputs.items():
        _required(label, "mutation state input label")
        validate_sha256(digest, field=f"input_artifact_hashes.{label}")
    previous = value.get("previous_receipt_hash")
    if not isinstance(previous, str):
        raise ValueError("mutation state previous_receipt_hash must be a string")
    if previous:
        validate_sha256(previous, field="previous_receipt_hash")
    return dict(value)


def _exclusive_write_json(
    path: Path,
    payload: Mapping[str, Any],
    *,
    existing_message: str,
) -> None:
    """Publish fully written JSON only when the destination does not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(canonical_json_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise ValueError(existing_message) from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record a draft or optimization mutation.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    start = subparsers.add_parser("start")
    start.add_argument("--article", required=True)
    start.add_argument("--state", required=True)
    start.add_argument("--run-id")
    start.add_argument("--assembly-date", required=True)
    start.add_argument("--workspace-root", required=True)
    start.add_argument("--stage", choices=sorted(MUTATION_STAGES), required=True)
    start.add_argument("--tool-name", required=True)
    start.add_argument("--tool-version", required=True)
    start.add_argument("--input", action="append", default=[])
    start.add_argument("--previous-receipt-hash", default="")
    finish = subparsers.add_parser("finish")
    finish.add_argument("--article", required=True)
    finish.add_argument("--state", required=True)
    finish.add_argument("--receipt", required=True)
    finish.add_argument("--evidence", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        if args.command == "start":
            start_mutation(
                article_path=args.article,
                state_path=args.state,
                run_id=args.run_id,
                stage=args.stage,
                tool_name=args.tool_name,
                tool_version=args.tool_version,
                input_artifacts=_label_paths(args.input),
                previous_receipt_hash=args.previous_receipt_hash,
                workspace_root=args.workspace_root,
                assembly_date=args.assembly_date,
            )
        else:
            finish_mutation(
                state_path=args.state,
                article_path=args.article,
                receipt_path=args.receipt,
                evidence_artifacts=_label_paths(args.evidence),
            )
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))
    return 0


def _label_paths(values: Sequence[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("artifact arguments must use label=path")
        label, path = value.split("=", 1)
        normalized_label = _required(label, "artifact label")
        if normalized_label in result:
            raise ValueError(f"duplicate artifact label: {normalized_label}")
        result[normalized_label] = Path(_required(path, "artifact path"))
    return result


def _reject_output_collision(
    output_path: str | Path,
    *,
    output_label: str,
    inputs: Mapping[str, str | Path],
) -> None:
    destination = _path_identity(output_path)
    for label, path in inputs.items():
        if destination == _path_identity(path):
            raise ValueError(
                f"mutation {output_label} output cannot overwrite input {label}"
            )


def _path_identity(path: Any) -> str:
    if not isinstance(path, (str, Path)) or not str(path).strip():
        raise ValueError("artifact path must be a non-empty path")
    return os.path.normcase(str(Path(path).resolve(strict=False)))


def _require_within_workspace(candidate: Path, root: Path, *, field: str) -> None:
    candidate_identity = os.path.normcase(str(candidate.resolve(strict=False)))
    root_identity = os.path.normcase(str(root.resolve(strict=False)))
    try:
        within = os.path.commonpath((candidate_identity, root_identity)) == root_identity
    except ValueError:
        within = False
    if not within:
        raise ValueError(f"{field} must be inside workspace_root")


def _canonical_assembly_date(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("assembly_date must be a canonical ISO date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("assembly_date must be a canonical ISO date") from error
    if parsed.isoformat() != value:
        raise ValueError("assembly_date must be a canonical ISO date")
    return value


def _required(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _time_text(value: datetime | str | None) -> str:
    if value is None:
        value = datetime.now(timezone.utc)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("mutation timestamps must be timezone aware")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return _required(value, "timestamp")


if __name__ == "__main__":
    raise SystemExit(main())
