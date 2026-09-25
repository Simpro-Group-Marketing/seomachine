"""Small helpers for the blog draft closeout command."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Mapping, Sequence


def validate_closeout_output_path(
    output_path: str | Path,
    *,
    article_path: str | Path,
    proof_sidecar: str | Path,
    workspace_root: str | Path,
) -> Path:
    """Return a safe report output path or raise a field-specific ValueError."""
    root = Path(workspace_root).resolve()
    output = _resolve_inside_workspace(output_path, root=root)
    output_identity = _path_identity(output)
    input_identities = {
        "article": _path_identity(Path(article_path).resolve()),
        "proof_sidecar": _path_identity(Path(proof_sidecar).resolve()),
    }
    for label, identity in input_identities.items():
        if output_identity == identity:
            raise ValueError(f"output cannot overwrite {label}")
    return output


def artifact_row(path: Path, *, root: Path) -> dict[str, str]:
    """Return path and hash for a bound closeout input artifact."""
    resolved = path.resolve()
    try:
        stored_path = resolved.relative_to(root).as_posix()
    except ValueError:
        stored_path = str(resolved)
    return {"path": stored_path, "sha256": sha256_file(resolved)}


def collect_blockers(
    checks: Mapping[str, Mapping[str, Any]],
    check_names: Sequence[str],
) -> list[dict[str, Any]]:
    """Flatten check blockers while preserving the owning check name."""
    blockers: list[dict[str, Any]] = []
    for check_name in check_names:
        for blocker in checks[check_name].get("blockers", []):
            row = dict(blocker)
            row["check"] = check_name
            blockers.append(row)
    return blockers


def collect_warnings(
    checks: Mapping[str, Mapping[str, Any]],
    check_names: Sequence[str],
) -> list[dict[str, Any]]:
    """Flatten warning findings from checks that expose finding rows."""
    warnings: list[dict[str, Any]] = []
    for check_name in check_names:
        for finding in checks[check_name].get("findings", []):
            if str(finding.get("severity", "")).casefold() != "warning":
                continue
            row = dict(finding)
            row["check"] = check_name
            warnings.append(row)
    return warnings


def failed_tool_check(rule_id: str, error: Exception) -> dict[str, Any]:
    """Represent an unexpected diagnostic failure as a normal failed check."""
    return {
        "status": "failed",
        "passed": False,
        "blockers": [{"rule_id": rule_id, "message": str(error)}],
    }


def finding_blockers(
    check_name: str,
    findings: Sequence[Mapping[str, Any]],
    *,
    failed: bool,
) -> list[dict[str, Any]]:
    """Convert native linter/source-support findings into closeout blockers."""
    if not failed:
        return []
    return [
        {
            "rule_id": str(finding.get("rule_id") or f"{check_name}_finding"),
            "severity": str(finding.get("severity") or "error"),
            "line": finding.get("line"),
            "message": str(finding.get("message") or ""),
        }
        for finding in findings
    ] or [
        {
            "rule_id": f"{check_name}_failed",
            "message": f"{check_name} reported a blocking failure.",
        }
    ]


def url_result_row(result: Any) -> dict[str, Any]:
    """Serialize one URL validation result object into JSON-safe fields."""
    return {
        "url": result.url,
        "status": result.status,
        "status_code": result.status_code,
        "reason": result.reason,
        "line": result.line,
        "anchor": result.anchor,
        "final_url": result.final_url,
    }


def sha256_file(path: Path) -> str:
    """Hash exact bytes on disk."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_inside_workspace(path: str | Path, *, root: Path) -> Path:
    candidate = Path(path)
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve(
        strict=False
    )
    if not _within(resolved, root):
        raise ValueError("output must stay inside workspace_root")
    return resolved


def _path_identity(path: Path) -> str:
    return os.path.normcase(str(path.resolve(strict=False)))


def _within(candidate: Path, root: Path) -> bool:
    try:
        return os.path.commonpath(
            (_path_identity(candidate), _path_identity(root))
        ) == _path_identity(root)
    except ValueError:
        return False
