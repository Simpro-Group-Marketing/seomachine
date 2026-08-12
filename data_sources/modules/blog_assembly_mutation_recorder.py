"""Start/finish recorder for draft and manual/agent optimization mutations."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .blog_assembly_contract import (
        atomic_write_json,
        canonical_json_bytes,
        canonical_json_sha256,
        file_sha256,
        validate_sha256,
    )
    from .blog_assembly_stage_receipt import build_stage_receipt
except ImportError:  # pragma: no cover - supports direct script execution.
    from blog_assembly_contract import (
        atomic_write_json,
        canonical_json_bytes,
        canonical_json_sha256,
        file_sha256,
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
    run_id: str,
    stage: str,
    tool_name: str,
    tool_version: str,
    input_artifacts: Mapping[str, str | Path] | None = None,
    previous_receipt_hash: str = "",
    started_at: datetime | str | None = None,
) -> dict[str, Any]:
    """Persist the immutable before-state before any mutation can occur."""
    if stage not in MUTATION_STAGES:
        raise ValueError("mutation recorder stage must be draft or optimization")
    article = Path(article_path).resolve()
    normalized_run_id = _required(run_id, "run_id")
    normalized_tool_name = _required(tool_name, "tool_name")
    normalized_tool_version = _required(tool_version, "tool_version")
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
        state = json.loads(Path(state_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"mutation state is invalid: {error}") from error
    state = _validate_active_state(state)
    state_source = Path(state_path).resolve()
    article = Path(article_path).resolve()
    if _path_identity(article) != _path_identity(state.get("article_path")):
        raise ValueError("mutation must finish against the same article identity")
    if not article.is_file():
        raise ValueError("mutation output article is unavailable")
    supplied_evidence = dict(evidence_artifacts or {})
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
    receipt_destination = Path(receipt_path).resolve()
    if receipt_destination.exists():
        raise ValueError("mutation receipt output already exists")
    after_hash = file_sha256(article)
    input_hashes = state.get("input_artifact_hashes")
    if not isinstance(input_hashes, Mapping):
        raise ValueError("mutation state input hashes are invalid")
    before_hash = input_hashes.get("article")
    if before_hash == after_hash:
        raise ValueError("recorded mutation did not change the article")
    evidence_hashes = {
        label: file_sha256(path)
        for label, path in sorted(supplied_evidence.items())
    }
    tool = state.get("tool")
    if not isinstance(tool, Mapping):
        raise ValueError("mutation state tool is invalid")
    completed_text = _time_text(completed_at)
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
    consumed = {
        "schema": CONSUMED_STATE_SCHEMA,
        "active_state_hash": str(state["state_hash"]),
        "receipt_hash": str(receipt["receipt_hash"]),
        "receipt_sha256": file_sha256(receipt_destination),
        "consumed_at": completed_text,
    }
    if set(consumed) != CONSUMED_STATE_FIELDS:  # pragma: no cover - invariant.
        raise RuntimeError("consumed mutation state shape drifted")
    try:
        atomic_write_json(state_source, consumed)
    except Exception:
        receipt_destination.unlink(missing_ok=True)
        raise
    return receipt


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
    for field in ("article_path", "run_id", "started_at"):
        _required(value.get(field), f"mutation state {field}")
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
    start.add_argument("--run-id", required=True)
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
