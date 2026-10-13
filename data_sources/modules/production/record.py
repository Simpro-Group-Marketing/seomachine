"""Release record: the one file a release writes and the publishers trust.

Each release run writes ``release-record.json`` into the next unused release directory for the
article's run id. Publishers call ``verify_publishable``: only the latest record counts, so a
newer failing release supersedes an older pass, and the article and BOM bytes must still be the
ones that release checked.
"""

from __future__ import annotations

import dataclasses
import datetime
import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.production.layout import Layout, stored_run_id

RECORD_SCHEMA = "simpro-release-record/v1"
RECORD_NAME = "release-record.json"
RELEASE_COMMAND = "python -m data_sources.modules.production.release"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _relative(layout: Layout, path: Path) -> str:
    return path.relative_to(layout.root).as_posix()


def _is_binding(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and isinstance(value.get("path"), str)
        and isinstance(value.get("sha256"), str)
    )


def bom_bindings(bom: Mapping[str, Any], prefix: str = "") -> dict[str, dict[str, str]]:
    """Every bound artifact in the BOM (except the spec), keyed by its dotted location."""
    found: dict[str, dict[str, str]] = {}
    for key, value in bom.items():
        where = f"{prefix}{key}"
        if _is_binding(value):
            if where != "identity.spec":
                found[where] = {"path": value["path"], "sha256": value["sha256"]}
        elif isinstance(value, Mapping):
            found.update(bom_bindings(value, f"{where}."))
    return found


def _finding_row(finding: Any) -> dict[str, Any]:
    row = dataclasses.asdict(finding) if dataclasses.is_dataclass(finding) else dict(finding)
    return {key: row.get(key) for key in ("check", "severity", "message", "line")}


def record_passed(findings: Iterable[Mapping[str, Any]], scores: Mapping[str, Any]) -> bool:
    """A release passes only with no block finding and all three score gates passed."""
    return scores.get("passed") is True and not any(row["severity"] == "block" for row in findings)


def _claim_release_dir(layout: Layout, run_id: str) -> Path:
    """Create the next unused release directory; retry if a concurrent run took it first."""
    while True:
        target = layout.release_dir(run_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.mkdir()
        except FileExistsError:
            continue
        return target


def write_record(
    layout: Layout,
    run_id: str,
    *,
    article_sha256: str,
    bom_sha256: str,
    findings: Iterable[Any],
    scores: Mapping[str, Any],
    bom: Mapping[str, Any],
    workers: int,
) -> Path:
    """Write one release record into a new release directory and return its path."""
    rows = [_finding_row(finding) for finding in findings]
    spec = (bom.get("identity") or {}).get("spec")
    payload = {
        "schema": RECORD_SCHEMA,
        "run_id": run_id,
        "created_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "article": {"path": _relative(layout, layout.article), "sha256": article_sha256},
        "bom": {"path": _relative(layout, layout.bom), "sha256": bom_sha256},
        "spec": {"path": spec["path"], "sha256": spec["sha256"]} if _is_binding(spec) else None,
        "evidence": bom_bindings(bom),
        "findings": rows,
        "blocks": sum(row["severity"] == "block" for row in rows),
        "warns": sum(row["severity"] == "warn" for row in rows),
        "scores": dict(scores),
        "passed": record_passed(rows, scores),
        "workers": workers,
    }
    path = _claim_release_dir(layout, run_id) / RECORD_NAME
    atomic_write_json(path, payload)
    return path


def latest_record_path(layout: Layout) -> Path | None:
    """Path of the record in the highest-numbered release directory for this run, or None."""
    run_id = stored_run_id(layout)
    if not run_id:
        return None
    probe = layout.release_dir(run_id)
    pattern = re.compile(re.escape(probe.name.rsplit("-", 1)[0]) + r"-(\d+)")
    numbered = [
        (int(match.group(1)), path)
        for path in (probe.parent.iterdir() if probe.parent.is_dir() else [])
        if path.is_dir() and (match := pattern.fullmatch(path.name))
    ]
    return max(numbered)[1] / RECORD_NAME if numbered else None


def latest_record(layout: Layout) -> dict[str, Any] | None:
    """The latest release record for this run; raises ValueError when it cannot be trusted."""
    path = latest_record_path(layout)
    if path is None:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"latest release record {path} is unreadable: {error}") from error
    if not isinstance(payload, dict) or payload.get("schema") != RECORD_SCHEMA:
        raise ValueError(f"latest release record {path} is not a {RECORD_SCHEMA} record")
    return payload


def _current_sha(path: Path) -> str:
    return file_sha256(path) if path.is_file() else "missing"


def _recorded_sha(payload: Mapping[str, Any], key: str) -> Any:
    block = payload.get(key)
    return block.get("sha256") if isinstance(block, Mapping) else None


def verify_publishable(article_path: Path, root: Path) -> dict[str, Any]:
    """Return the latest release record, or raise ValueError unless it passed for these exact bytes."""
    layout = Layout.for_article(article_path, root)
    payload = latest_record(layout)
    if payload is None:
        raise ValueError(f"no release record for {layout.article.name}; run {RELEASE_COMMAND} <article>")
    if payload.get("run_id") != stored_run_id(layout):
        raise ValueError("latest release record belongs to another run of this article; release it again")
    if payload.get("passed") is not True:
        raise ValueError(f"latest release of {layout.article.name} did not pass; fix it and release again")
    if _recorded_sha(payload, "article") != _current_sha(layout.article):
        raise ValueError(f"article changed since its passing release: {layout.article.name}; release it again")
    if _recorded_sha(payload, "bom") != _current_sha(layout.bom):
        raise ValueError(f"production BOM changed since the passing release: {layout.bom.name}; release it again")
    return payload


__all__ = [
    "RECORD_NAME",
    "RECORD_SCHEMA",
    "bom_bindings",
    "file_sha256",
    "latest_record",
    "latest_record_path",
    "record_passed",
    "verify_publishable",
    "write_record",
]
