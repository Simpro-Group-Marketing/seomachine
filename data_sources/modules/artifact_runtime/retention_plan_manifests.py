"""Bounded, immutable retention-plan persistence and validation."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from uuid import uuid4

from ..bounded_io import (
    JsonOutputLimitError,
    bounded_canonical_json_bytes,
    parse_json_object,
    read_bounded,
)
from .limits import JSON_MAX_BYTES
from .retention_planning import (
    RetentionCandidate,
    RetentionPlan,
    format_timestamp,
    parse_timestamp,
    referenced_objects,
    resolve_relative,
    verify_candidate,
)
from .workspace_lock import artifact_workspace_lock


RETENTION_PLAN_SCHEMA = "simpro-artifact-retention-plan/v1"
PLAN_PREFIX = Path(".seomachine/retention-plans/v1")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RUN_ID_RE = re.compile(r"^[0-9a-f]{32}$")


def persist_retention_plan(
    plan: RetentionPlan,
    *,
    workspace_root: str | Path,
) -> Path:
    """Revalidate and atomically persist one non-overwriting dry-run plan."""
    root = Path(workspace_root).resolve(strict=True)
    if root != plan.workspace_root:
        raise ValueError("retention plan does not match the workspace")
    with artifact_workspace_lock(root):
        current_references = referenced_objects(root)
        for candidate in plan.candidates:
            if candidate.path in current_references:
                relative = candidate.path.relative_to(root).as_posix()
                raise ValueError(f"retention candidate became referenced: {relative}")
            verify_candidate(candidate, root=root)
        return _persist_new(plan, root=root)


def load_retention_plan_manifest(
    manifest_path: str | Path,
    *,
    workspace_root: str | Path,
) -> RetentionPlan:
    """Bounded-read and strictly validate one persisted plan."""
    root = Path(workspace_root).resolve(strict=True)
    path = _resolve_manifest(manifest_path, root=root)
    try:
        payload = parse_json_object(
            read_bounded(path, max_bytes=JSON_MAX_BYTES, field="retention plan manifest"),
            field="retention plan manifest",
        )
        return _parse_payload(payload, root=root)
    except (OSError, ValueError) as error:
        raise ValueError(f"retention plan manifest is invalid: {error}") from error


def _persist_new(plan: RetentionPlan, *, root: Path) -> Path:
    run_id = uuid4().hex
    stamp = plan.evaluated_at.strftime("%Y%m%dT%H%M%SZ")
    run_root = root / PLAN_PREFIX / f"{stamp}-{run_id}"
    run_root.mkdir(parents=True, exist_ok=False)
    manifest_path = run_root / "manifest.json"
    payload = _payload(plan, root=root, run_id=run_id)
    try:
        serialized = bounded_canonical_json_bytes(payload, max_bytes=JSON_MAX_BYTES)
        _write_exclusive(manifest_path, serialized)
    except JsonOutputLimitError as error:
        run_root.rmdir()
        raise ValueError(f"retention plan exceeds {JSON_MAX_BYTES} bytes") from error
    except BaseException:
        if not manifest_path.exists():
            run_root.rmdir()
        raise
    return manifest_path


def _payload(plan: RetentionPlan, *, root: Path, run_id: str) -> dict[str, object]:
    candidates = [
        {
            "path": candidate.path.relative_to(root).as_posix(),
            "sha256": candidate.sha256,
            "bytes": candidate.byte_count,
            "age_days": candidate.age_days,
        }
        for candidate in plan.candidates
    ]
    return {
        "schema": RETENTION_PLAN_SCHEMA,
        "run_id": run_id,
        "evaluated_at": format_timestamp(plan.evaluated_at),
        "policy": {"research_retention_days": plan.research_retention_days},
        "candidate_count": len(candidates),
        "candidate_bytes": sum(candidate.byte_count for candidate in plan.candidates),
        "candidates": candidates,
    }


def _parse_payload(payload: dict[str, object], *, root: Path) -> RetentionPlan:
    expected = {
        "schema",
        "run_id",
        "evaluated_at",
        "policy",
        "candidate_count",
        "candidate_bytes",
        "candidates",
    }
    if set(payload) != expected or payload.get("schema") != RETENTION_PLAN_SCHEMA:
        raise ValueError("fields or schema do not match")
    run_id = payload.get("run_id")
    if not isinstance(run_id, str) or _RUN_ID_RE.fullmatch(run_id) is None:
        raise ValueError("run_id is invalid")
    policy = payload.get("policy")
    if not isinstance(policy, dict) or set(policy) != {"research_retention_days"}:
        raise ValueError("policy is invalid")
    retention_days = policy.get("research_retention_days")
    if isinstance(retention_days, bool) or not isinstance(retention_days, int) or retention_days < 1:
        raise ValueError("research_retention_days is invalid")
    rows = payload.get("candidates")
    if not isinstance(rows, list):
        raise ValueError("candidate inventory is invalid")
    candidates = tuple(_parse_candidate(row, root=root) for row in rows)
    paths = [candidate.path for candidate in candidates]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ValueError("candidate inventory must be unique and ordered")
    _validate_summary(payload, candidates=candidates)
    return RetentionPlan(
        workspace_root=root,
        candidates=candidates,
        referenced=(),
        evaluated_at=parse_timestamp(payload.get("evaluated_at")),
        research_retention_days=retention_days,
    )


def _parse_candidate(value: object, *, root: Path) -> RetentionCandidate:
    if not isinstance(value, dict) or set(value) != {"path", "sha256", "bytes", "age_days"}:
        raise ValueError("candidate row is invalid")
    digest = value.get("sha256")
    if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
        raise ValueError("candidate sha256 is invalid")
    byte_count = _nonnegative_int(value.get("bytes"), field="candidate bytes")
    age_days = _nonnegative_int(value.get("age_days"), field="candidate age_days")
    path = resolve_relative(root, value.get("path"))
    object_root = root / "research" / ".objects" / "context-traces" / "v1" / "sha256"
    path.relative_to(object_root.resolve())
    return RetentionCandidate(
        path=path,
        sha256=digest,
        byte_count=byte_count,
        age_days=age_days,
    )


def _validate_summary(
    payload: dict[str, object],
    *,
    candidates: tuple[RetentionCandidate, ...],
) -> None:
    count = _nonnegative_int(payload.get("candidate_count"), field="candidate_count")
    byte_count = _nonnegative_int(payload.get("candidate_bytes"), field="candidate_bytes")
    if count != len(candidates) or byte_count != sum(item.byte_count for item in candidates):
        raise ValueError("candidate summary does not match inventory")


def _nonnegative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} is invalid")
    return value


def _resolve_manifest(path: str | Path, *, root: Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve(strict=True)
    resolved.relative_to(root)
    if not resolved.is_file():
        raise ValueError("retention plan manifest is unavailable")
    return resolved


def _write_exclusive(path: Path, content: bytes) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=".retention-plan-",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


__all__ = [
    "RETENTION_PLAN_SCHEMA",
    "load_retention_plan_manifest",
    "persist_retention_plan",
]
