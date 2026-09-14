"""Locked, crash-resumable quarantine transactions."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .retention_journal_ops import (
    _append_event,
    _compact_transaction,
    _create_transaction,
    _ensure_open_journal,
    _move_row_v3,
    _open_operation,
    _purge_row_v3,
    _reconcile_quarantine_row_v3,
    _restore_row_v3,
    _resume_purge_v3,
    _resume_restore_v3,
)
from .retention_legacy import _purge_legacy, _restore_legacy, _resume_legacy_v2
from .retention_planning import (
    RetentionPlan,
    parse_timestamp,
    referenced_objects,
    require_aware,
    resolve_relative,
    verify_candidate,
)
from .retention_plan_manifests import load_retention_plan_manifest
from .retention_store import (
    DEFAULT_QUARANTINE_DAYS,
    LEGACY_QUARANTINE_SCHEMA,
    LEGACY_QUARANTINE_SCHEMA_V2,
    QUARANTINE_BASE_SCHEMA,
    QUARANTINE_EVENT_SCHEMA,
    QUARANTINE_SCHEMA,
    TERMINAL_STATUSES,
    _artifact_rows,
    _load_transaction,
    _manifest_paths,
    _reject_incomplete_transactions,
    _reload_transaction,
    _resolve_transaction_path,
    _verify_file,
)
from .workspace_lock import artifact_workspace_lock
def apply_retention(
    plan: RetentionPlan | str | Path,
    *,
    workspace_root: str | Path,
    now: datetime,
    quarantine_days: int = DEFAULT_QUARANTINE_DAYS,
) -> Path:
    """Move verified objects through an exclusive, resumable transaction."""
    root = Path(workspace_root).resolve(strict=True)
    current = require_aware(now)
    with artifact_workspace_lock(root):
        effective_plan = (
            plan
            if isinstance(plan, RetentionPlan)
            else load_retention_plan_manifest(plan, workspace_root=root)
        )
        if root != effective_plan.workspace_root or quarantine_days < 1:
            raise ValueError("retention plan does not match the workspace or policy")
        _reject_incomplete_transactions(root)
        current_references = referenced_objects(root)
        for candidate in effective_plan.candidates:
            if candidate.path in current_references:
                relative = candidate.path.relative_to(root).as_posix()
                raise ValueError(f"retention candidate became referenced: {relative}")
            verify_candidate(candidate, root=root)
        transaction = _create_transaction(
            root,
            candidates=effective_plan.candidates,
            now=current,
            quarantine_days=quarantine_days,
        )
        payload = transaction.payload
        for index, row in enumerate(_artifact_rows(payload), start=1):
            transaction = _reload_transaction(transaction.run_root, root=root)
            _move_row_v3(
                row,
                index=index,
                transaction=transaction,
                root=root,
            )
        transaction = _reload_transaction(transaction.run_root, root=root)
        _append_event(transaction, "transaction_complete")
        transaction = _reload_transaction(transaction.run_root, root=root)
        _compact_transaction(transaction, root=root, status="complete")
        return transaction.manifest_path


def resume_retention(
    manifest_path: str | Path,
    *,
    workspace_root: str | Path,
) -> Path:
    """Reconcile and complete one interrupted quarantine transaction."""
    root = Path(workspace_root).resolve(strict=True)
    path = _resolve_transaction_path(manifest_path, root=root)
    with artifact_workspace_lock(root):
        transaction = _load_transaction(path, root=root)
        if transaction.legacy:
            return _resume_legacy_v2(transaction.manifest_path, root=root)
        if transaction.compacted and transaction.payload.get("status") in TERMINAL_STATUSES:
            return transaction.manifest_path
        operation = _open_operation(transaction)
        if operation == "purge":
            _resume_purge_v3(transaction, root=root)
            return transaction.manifest_path
        if operation == "restore":
            _resume_restore_v3(transaction, root=root)
            return transaction.manifest_path
        for index, row in enumerate(_artifact_rows(transaction.payload), start=1):
            transaction = _reload_transaction(transaction.run_root, root=root)
            _reconcile_quarantine_row_v3(
                row,
                index=index,
                transaction=transaction,
                root=root,
            )
        transaction = _reload_transaction(transaction.run_root, root=root)
        _append_event(transaction, "transaction_complete")
        transaction = _reload_transaction(transaction.run_root, root=root)
        _compact_transaction(transaction, root=root, status="complete")
        return transaction.manifest_path


def restore_quarantine(
    manifest_path: str | Path,
    *,
    workspace_root: str | Path,
) -> list[Path]:
    """Restore every intact quarantined artifact without replacement."""
    root = Path(workspace_root).resolve(strict=True)
    path = _resolve_transaction_path(manifest_path, root=root)
    with artifact_workspace_lock(root):
        transaction = _load_transaction(path, root=root)
        if transaction.legacy:
            return _restore_legacy(transaction.manifest_path, root=root)
        if transaction.payload.get("status") not in {"complete", "restored"}:
            raise ValueError("incomplete quarantine must be resumed before restore")
        transaction = _ensure_open_journal(transaction, root=root)
        restored: list[Path] = []
        if transaction.events_path is not None:
            _append_event(transaction, "restore_started")
        for index, row in enumerate(_artifact_rows(transaction.payload), start=1):
            if row.get("status") == "restored":
                continue
            transaction = _reload_transaction(transaction.run_root, root=root)
            restored_path = _restore_row_v3(
                row,
                index=index,
                transaction=transaction,
                root=root,
            )
            restored.append(restored_path)
        transaction = _reload_transaction(transaction.run_root, root=root)
        _append_event(transaction, "transaction_restored")
        transaction = _reload_transaction(transaction.run_root, root=root)
        _compact_transaction(transaction, root=root, status="restored")
        return restored


def purge_expired_quarantine(
    workspace_root: str | Path,
    *,
    now: datetime,
    apply: bool,
) -> list[Path]:
    """Report or delete hash-verified artifacts after their grace period."""
    root = Path(workspace_root).resolve(strict=True)
    current = require_aware(now)
    with artifact_workspace_lock(root):
        eligible: list[Path] = []
        for manifest_path in _manifest_paths(root):
            transaction = _load_transaction(manifest_path, root=root)
            if transaction.legacy:
                eligible.extend(
                    _purge_legacy(
                        transaction.manifest_path,
                        root=root,
                        now=current,
                        apply=apply,
                    )
                )
                continue
            if transaction.payload.get("status") != "complete":
                continue
            if parse_timestamp(transaction.payload.get("delete_after")) > current:
                continue
            rows = []
            for index, row in enumerate(_artifact_rows(transaction.payload), start=1):
                if row.get("status") != "quarantined":
                    continue
                artifact = resolve_relative(root, row.get("quarantine_path"))
                _verify_file(artifact, row, label="quarantined artifact")
                eligible.append(artifact)
                rows.append((index, row, artifact))
            if apply:
                transaction = _ensure_open_journal(transaction, root=root)
                if rows:
                    _append_event(transaction, "purge_started")
                for index, row, artifact in rows:
                    transaction = _reload_transaction(transaction.run_root, root=root)
                    _purge_row_v3(
                        row,
                        index=index,
                        artifact=artifact,
                        transaction=transaction,
                        root=root,
                    )
                transaction = _reload_transaction(transaction.run_root, root=root)
                _append_event(transaction, "transaction_purged")
                transaction = _reload_transaction(transaction.run_root, root=root)
                _compact_transaction(transaction, root=root, status="purged")
        return eligible


__all__ = [
    "DEFAULT_QUARANTINE_DAYS",
    "LEGACY_QUARANTINE_SCHEMA",
    "LEGACY_QUARANTINE_SCHEMA_V2",
    "QUARANTINE_BASE_SCHEMA",
    "QUARANTINE_EVENT_SCHEMA",
    "QUARANTINE_SCHEMA",
    "apply_retention",
    "purge_expired_quarantine",
    "restore_quarantine",
    "resume_retention",
]
