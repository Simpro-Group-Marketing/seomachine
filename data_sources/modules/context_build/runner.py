"""Resumable runner that turns a context build spec into validated packs and receipts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

try:
    from ..artifact_runtime.content_store import write_context_trace
    from ..artifact_runtime.limits import JSON_MAX_BYTES
    from ..bounded_io import atomic_write_bytes, canonical_json_sha256, parse_json_object, read_bounded
    from ..simpro_vault_client import VaultClientError
    from .checkpoints import CheckpointStore, ContextBuildResumeError
    from .spec import ContextBuildSpec, StageSpec
    from .trace import (
        TRACE_SCHEMA, compact_claims, compact_expansion, compact_read, compact_receipt,
        compact_search, resource_ids,
    )
except ImportError:  # pragma: no cover - supports direct script execution.
    from artifact_runtime.content_store import write_context_trace
    from artifact_runtime.limits import JSON_MAX_BYTES
    from bounded_io import atomic_write_bytes, canonical_json_sha256, parse_json_object, read_bounded
    from simpro_vault_client import VaultClientError
    from context_build.checkpoints import CheckpointStore, ContextBuildResumeError
    from context_build.spec import ContextBuildSpec, StageSpec
    from context_build.trace import (
        TRACE_SCHEMA, compact_claims, compact_expansion, compact_read, compact_receipt,
        compact_search, resource_ids,
    )

LOOKUP_SCHEMA = "simpro-customer-proof-claim-lookup/v1"
LOOKUP_SOURCE = "SimproVaultClient.claims"
DEFAULT_CLAIM_LIMIT = 20
SEARCH_LIMIT = 50


class ContextBuildError(RuntimeError):
    """Raised when the vault state or a build result cannot support a safe context build.

    ``stages_not_rebuilt`` names the stages neither built nor reused in the failed run; their
    files on disk may be stale from an earlier spec.
    """

    stages_not_rebuilt: tuple[str, ...] = ()


@dataclass(frozen=True)
class StageOutcome:
    stage_id: str
    action: str  # "built" or "reused"
    pack_sha256: str  # sha256 of the pack file bytes on disk
    receipt_sha256: str  # sha256 of the receipt file bytes on disk


@dataclass(frozen=True)
class ContextBuildResult:
    stages: tuple[StageOutcome, ...]
    trace_path: Path


def _json_bytes(value: Any) -> bytes:
    """Serialize exactly like the reference per-topic scripts (indent 2, LF, trailing newline)."""
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _write_json(path: Path, value: Any, field: str) -> str:
    data = _json_bytes(value)
    try:
        atomic_write_bytes(path, (data,), max_bytes=JSON_MAX_BYTES, field=field)
    except OSError as error:
        raise ContextBuildError(f"could not write {field} to {path.as_posix()}: {error}") from error
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


Cache = Callable[[str, Callable[[], Any]], Any]


def _cached(store: CheckpointStore, key: str, fetch: Callable[[], Any]) -> Any:
    value = store.get(key)
    if value is None:
        value = fetch()
        store.put(key, value)
    return value


def _read_json(path: Path, field: str) -> dict[str, Any]:
    return parse_json_object(read_bounded(path, max_bytes=JSON_MAX_BYTES, field=field), field=field)


def _write_request(spec: ContextBuildSpec, root: Path, *, resume: bool) -> None:
    path = root / spec.request_path
    if resume and path.exists():
        try:
            existing = _read_json(path, "context request")
        except ValueError as error:
            raise ContextBuildResumeError(f"request changed on disk and is unreadable: {error}") from error
        if existing != spec.request:
            raise ContextBuildResumeError(
                f"request changed since the saved run: {spec.request_path} differs from the spec; "
                "rerun without --resume"
            )
        return
    _write_json(path, spec.request, "context request")


def _ready_status(client: Any) -> dict[str, Any]:
    status = client.status()
    if not isinstance(status, dict) or status.get("status") != "ready":
        raise ContextBuildError(f"vault status is not ready: {status!r}")
    return status


def _check_rediscovery(
    spec: ContextBuildSpec, searches: dict[str, Any], expansions: dict[str, Any]
) -> None:
    found = resource_ids(list(searches.values())) | resource_ids(list(expansions.values()))
    missing = sorted(set(spec.resource_purposes) - found)
    if missing:
        raise ContextBuildError(
            f"selected resource ids were not rediscovered by search or expansion: {', '.join(missing)}"
        )


def _live_status(client: Any, store: CheckpointStore) -> tuple[dict[str, Any], Cache]:
    """Always read status live; scope discovery checkpoints to the live revisions.

    Checkpoint keys are prefixed with a hash of the live revisions, so a changed revision (or a
    missing prior status) leaves earlier discovery and claim checkpoints unreachable.
    """
    status = _ready_status(client)
    namespace = canonical_json_sha256({"revisions": status.get("revisions")})[:16]
    store.put("status", status)
    return status, lambda key, fetch: _cached(store, f"{namespace}:{key}", fetch)


def _discover(spec: ContextBuildSpec, client: Any, status: dict[str, Any], cache: Cache) -> dict[str, Any]:
    describe = cache("describe", client.describe)
    searches = {
        query: cache(f"search:{query}", lambda q=query: client.search(q, limit=SEARCH_LIMIT))
        for query in spec.search_queries
    }
    expansions = {
        rid: cache(f"expand:{rid}", lambda r=rid: client.expand(r, purpose=spec.resource_purposes[r]))
        for rid in spec.expand_resource_ids
    }
    _check_rediscovery(spec, searches, expansions)
    reads = {
        rid: cache(f"read:{rid}", lambda r=rid, p=purpose: client.read(r, purpose=p))
        for rid, purpose in spec.resource_purposes.items()
    }
    return {"status": status, "describe": describe, "searches": searches,
            "expansions": expansions, "reads": reads}


def _lookup_entry(client: Any, row: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(row.get("brand_scope"), str) or not row["brand_scope"].strip():
        raise ContextBuildError(f"claim lookup {row.get('query')!r} requires a brand_scope")
    limit = row.get("limit", DEFAULT_CLAIM_LIMIT)
    rows = client.claims(row["query"], use_mode=row["use_mode"], brand_scope=row["brand_scope"], limit=limit)
    return {
        **row,
        "limit": limit,
        "source": LOOKUP_SOURCE,
        "status": "complete",
        "truncated": False,
        "result_count": len(rows) if isinstance(rows, list) else 0,
        "claim_ids": [
            r.get("claim_id") for r in rows if isinstance(r, dict) and isinstance(r.get("claim_id"), str)
        ] if isinstance(rows, list) else [],
        "rows": rows,
    }


def _claim_lookups(
    spec: ContextBuildSpec, client: Any, cache: Cache, root: Path, now: datetime
) -> dict[str, Any]:
    """Run claim lookups through the checkpoint cache; write the lookup artifact when the spec asks for it."""

    def build_artifact() -> dict[str, Any]:
        lookups = [
            cache(f"claims:{index}", lambda r=row: _lookup_entry(client, r))
            for index, row in enumerate(spec.claim_lookups)
        ]
        return {
            "schema": LOOKUP_SCHEMA,
            "source": LOOKUP_SOURCE,
            "article_slug": spec.slug,
            "generated_at": now.isoformat(),
            "lookups": lookups,
        }

    artifact = cache("claim_lookup_artifact", build_artifact)
    if spec.claim_lookup_path:
        artifact_sha = _write_json(root / spec.claim_lookup_path, artifact, "claim lookup artifact")
        return {"artifact": artifact, "path": spec.claim_lookup_path, "sha256": artifact_sha}
    return {"artifact": artifact, "path": None, "sha256": None}


def _saved_stage(root: Path, stage: StageSpec) -> tuple[dict[str, Any], dict[str, Any]] | None:
    pack_path, receipt_path = root / stage.pack_path, root / stage.receipt_path
    if not (pack_path.is_file() and receipt_path.is_file()):
        return None
    try:
        return _read_json(pack_path, "saved pack"), _read_json(receipt_path, "saved receipt")
    except ValueError:
        return None


def _build_input(spec: ContextBuildSpec, stage: StageSpec) -> dict[str, Any]:
    return {
        "request": spec.request,
        "search_queries": list(spec.search_queries),
        "resource_ids": list(spec.resource_purposes),
        "resource_purposes": dict(spec.resource_purposes),
        "constraints": list(spec.constraints),
        "task_satisfaction": "satisfied",
        "unresolved_gaps": [],
        "claim_requests": [dict(row) for row in stage.claim_requests],
    }


def _stage_digest(spec: ContextBuildSpec, stage: StageSpec) -> str:
    """Hash everything a stage's pack depends on, independent of vault revisions."""
    return canonical_json_sha256({
        "pack_path": stage.pack_path,
        "receipt_path": stage.receipt_path,
        "claim_requests": [dict(row) for row in stage.claim_requests],
        "request": spec.request,
        "search_queries": list(spec.search_queries),
        "resource_purposes": dict(spec.resource_purposes),
        "constraints": list(spec.constraints),
    })


def _stage_checkpoint_matches(
    spec: ContextBuildSpec, stage: StageSpec, root: Path, store: CheckpointStore
) -> bool:
    saved = store.get(f"stage:{stage.stage_id}")
    if not isinstance(saved, dict) or saved.get("stage_digest") != _stage_digest(spec, stage):
        return False
    try:
        return (
            _sha256_file(root / stage.pack_path) == saved.get("pack_sha256")
            and _sha256_file(root / stage.receipt_path) == saved.get("receipt_sha256")
        )
    except OSError:
        return False


def _reuse_stage(
    spec: ContextBuildSpec, stage: StageSpec, client: Any, root: Path, store: CheckpointStore
) -> tuple[StageOutcome, dict[str, Any], dict[str, Any]] | None:
    """Reuse a saved stage only if it was built for this exact stage, is unmodified, and validates."""
    if not _stage_checkpoint_matches(spec, stage, root, store):
        return None
    saved = _saved_stage(root, stage)
    if saved is None:
        return None
    pack, receipt = saved
    try:
        validation = client.validate_context(spec.request, pack, receipt)
    except VaultClientError as error:
        if getattr(error, "code", None) == "pack_stale":
            return None  # stale receipt or vault revisions: rebuild this stage
        raise
    if not isinstance(validation, dict) or validation.get("valid") is not True:
        return None
    outcome = StageOutcome(
        stage.stage_id, "reused", _sha256_file(root / stage.pack_path), _sha256_file(root / stage.receipt_path)
    )
    return outcome, receipt, validation


def _run_stage(
    spec: ContextBuildSpec, stage: StageSpec, client: Any, root: Path, store: CheckpointStore, *, resume: bool
) -> tuple[StageOutcome, dict[str, Any], dict[str, Any]]:
    if resume:
        reused = _reuse_stage(spec, stage, client, root, store)
        if reused is not None:
            return reused
    output = client.build_context(_build_input(spec, stage))
    try:
        pack, receipt = output["pack"], output["receipt"]
    except (KeyError, TypeError) as error:
        raise ContextBuildError(
            f"stage {stage.stage_id} build_context result lacks a usable pack and receipt: {error!r}"
        ) from error
    validation = client.validate_context(spec.request, pack, receipt)
    if not isinstance(validation, dict) or validation.get("valid") is not True:
        raise ContextBuildError(f"stage {stage.stage_id} context validation did not return valid: {validation!r}")
    pack_sha = _write_json(root / stage.pack_path, pack, f"{stage.stage_id} pack")
    receipt_sha = _write_json(root / stage.receipt_path, receipt, f"{stage.stage_id} receipt")
    store.put(
        f"stage:{stage.stage_id}",
        {"pack_sha256": pack_sha, "receipt_sha256": receipt_sha, "stage_digest": _stage_digest(spec, stage)},
    )
    return StageOutcome(stage.stage_id, "built", pack_sha, receipt_sha), receipt, validation


def _write_trace(
    spec: ContextBuildSpec, root: Path, now: datetime, discovery: dict[str, Any],
    lookups: dict[str, Any], stages: list[tuple[StageOutcome, dict[str, Any], dict[str, Any]]],
) -> Path:
    describe = discovery["describe"]
    payload = {
        "schema": TRACE_SCHEMA,
        "slug": spec.slug,
        "date": spec.date,
        "spec_digest": spec.digest,
        "status": discovery["status"],
        "describe": {k: describe.get(k) for k in ("schema", "capabilities", "claim_health")}
        if isinstance(describe, dict) else describe,
        "searches": {q: compact_search(r) for q, r in discovery["searches"].items()},
        "expansions": {rid: compact_expansion(r) for rid, r in discovery["expansions"].items()},
        "reads": {rid: compact_read(r) for rid, r in discovery["reads"].items()},
        "claim_lookups": {
            "path": lookups["path"],
            "sha256": lookups["sha256"],
            "lookups": [
                {"query": e.get("query"), "use_mode": e.get("use_mode"), "claims": compact_claims(e.get("rows"))}
                for e in lookups["artifact"]["lookups"]
            ],
        },
        "stages": {
            outcome.stage_id: {
                "action": outcome.action,
                "pack_sha256": outcome.pack_sha256,
                "receipt_sha256": outcome.receipt_sha256,
                "receipt": compact_receipt(receipt),
                "validation": validation,
            }
            for outcome, receipt, validation in stages
        },
    }
    try:
        write_context_trace(root / spec.trace_path, payload, workspace_root=root, generated_at=now)
    except OSError as error:
        raise ContextBuildError(f"could not write the context trace to {spec.trace_path}: {error}") from error
    return root / spec.trace_path


def run_context_build(
    spec: ContextBuildSpec,
    *,
    client: Any,
    workspace_root: Path,
    resume: bool,
    now: datetime | None = None,
) -> ContextBuildResult:
    """Run discovery, claim lookups, and every stage, checkpointing each vault call and each pack."""
    root = Path(workspace_root)
    stamp = now or datetime.now(timezone.utc)
    stages: list[tuple[StageOutcome, dict[str, Any], dict[str, Any]]] = []
    try:
        store = CheckpointStore(root, spec, resume=resume)
        _write_request(spec, root, resume=resume)
        status, cache = _live_status(client, store)
        discovery = _discover(spec, client, status, cache)
        lookups = _claim_lookups(spec, client, cache, root, stamp)
        for stage in spec.stages:
            stages.append(_run_stage(spec, stage, client, root, store, resume=resume))
    except (ContextBuildError, ContextBuildResumeError, VaultClientError) as error:
        done = {outcome.stage_id for outcome, _, _ in stages}
        error.stages_not_rebuilt = tuple(s.stage_id for s in spec.stages if s.stage_id not in done)
        raise
    trace_path = _write_trace(spec, root, stamp, discovery, lookups, stages)
    return ContextBuildResult(tuple(outcome for outcome, _, _ in stages), trace_path)
