"""Release record: the one file a release writes, and the check that an article is publishable.

Each release run writes ``release-record.json`` into the next unused release directory for the
article's run id. ``verify_publishable`` trusts only the latest record, so a newer failing release
supersedes an older pass, and the article and BOM bytes must still be the ones that release checked.
The commands (/write, /rewrite, /repurpose) run it through this CLI. The WordPress (blog posts)
and Grav publishers call ``verify_publishable`` before any write, and after a successful live
publish they record the article's linked BOM proof in the customer-proof usage ledger
(``production.usage_ledger``).

Usage: python -m data_sources.modules.production.record verify <article> [--workspace-root DIR]
Prints the latest record path and its passed state. Exit codes: 0 publishable; 1 refused (the
reason is printed); 2 argument or layout error.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import hashlib
import json
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.production.layout import Layout, LayoutError, stored_run_id

RECORD_SCHEMA = "simpro-release-record/v1"
RECORD_NAME = "release-record.json"
_CLAIM_ATTEMPTS = 100
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


def _capture_bindings(bom: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    """Each fact's Chrome capture receipt as ``facts.<id>.capture``; the receipt hash covers its text hash."""
    facts = bom.get("facts")
    return {
        f"facts.{fact.get('id')}.capture": {"path": fact["capture"]["path"], "sha256": fact["capture"]["sha256"]}
        for fact in (facts if isinstance(facts, list) else [])
        if isinstance(fact, Mapping) and _is_binding(fact.get("capture"))
    }


def bom_bindings(bom: Mapping[str, Any], prefix: str = "") -> dict[str, dict[str, str]]:
    """Every bound artifact in the BOM (except the spec), keyed by its dotted location."""
    found: dict[str, dict[str, str]] = _capture_bindings(bom) if not prefix else {}
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


def _blocks(findings: Iterable[Mapping[str, Any]]) -> int:
    """Anything that is not a warning blocks, including unknown severities."""
    return sum(row["severity"] != "warn" for row in findings)


def record_passed(findings: Iterable[Mapping[str, Any]], scores: Mapping[str, Any] | None) -> bool:
    """A release passes only with no blocking finding and all three score gates passed."""
    return scores is not None and scores.get("passed") is True and _blocks(findings) == 0


def _claim_release_dir(layout: Layout, run_id: str) -> Path:
    """Create the next unused release directory; retry if a concurrent run took it first."""
    for _attempt in range(_CLAIM_ATTEMPTS):
        target = layout.release_dir(run_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.mkdir()
        except FileExistsError:
            continue
        return target
    raise OSError(f"could not claim a release directory after {_CLAIM_ATTEMPTS} attempts in {target.parent}")


def write_record(
    layout: Layout,
    run_id: str,
    *,
    article_sha256: str,
    bom_sha256: str | None,
    findings: Iterable[Any],
    scores: Mapping[str, Any] | None,
    bom: Mapping[str, Any] | None,
    workers: int,
    bom_path: Path | None = None,
) -> Path:
    """Write one release record into a new release directory and return its path.

    A failure record may have no scores, no BOM (``bom_sha256`` None), or bind a refused BOM file
    through ``bom_path``; it never passes.
    """
    rows = [_finding_row(finding) for finding in findings]
    bom = bom or {}
    spec = (bom.get("identity") or {}).get("spec")
    bom_file = bom_path or layout.bom
    payload = {
        "schema": RECORD_SCHEMA,
        "run_id": run_id,
        "created_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "article": {"path": _relative(layout, layout.article), "sha256": article_sha256},
        "bom": {"path": _relative(layout, bom_file), "sha256": bom_sha256} if bom_sha256 else None,
        "spec": {"path": spec["path"], "sha256": spec["sha256"]} if _is_binding(spec) else None,
        "evidence": bom_bindings(bom),
        "findings": rows,
        "blocks": _blocks(rows),
        "warns": sum(row["severity"] == "warn" for row in rows),
        "scores": dict(scores) if scores is not None else None,
        "passed": record_passed(rows, scores),
        "workers": workers,
    }
    path = _claim_release_dir(layout, run_id) / RECORD_NAME
    atomic_write_json(path, payload)
    return path


def latest_record_path(layout: Layout) -> Path | None:
    """Path of the record in the highest-numbered release directory for this run, or None."""
    run_id = stored_run_id(layout)
    existing = layout.release_dirs(run_id) if run_id else []
    return existing[-1] / RECORD_NAME if existing else None


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


def _binding_errors(layout: Layout, payload: Mapping[str, Any]) -> list[str]:
    """The spec and every evidence binding must still match the files on disk."""
    bindings = dict(payload.get("evidence") or {})
    bindings["spec"] = payload.get("spec")
    errors = []
    for name, binding in sorted(bindings.items()):
        if not _is_binding(binding):
            errors.append(f"release record has no {name} binding")
        elif _current_sha(layout.root / binding["path"]) != binding["sha256"]:
            errors.append(f"{binding['path']} changed since the passing release")
    return errors


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
    article = _relative(layout, layout.article)
    if (payload.get("article") or {}).get("path") != article:
        raise ValueError(f"latest release record is for {(payload.get('article') or {}).get('path')}, not {article}")
    if _recorded_sha(payload, "article") != _current_sha(layout.article):
        raise ValueError(f"article changed since its passing release: {layout.article.name}; release it again")
    if _recorded_sha(payload, "bom") != _current_sha(layout.bom):
        raise ValueError(f"production BOM changed since the passing release: {layout.bom.name}; release it again")
    errors = _binding_errors(layout, payload)
    if errors:
        raise ValueError("; ".join(errors) + "; release it again")
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="record", description="Check that an article's latest release passed.")
    parser.add_argument("action", choices=("verify",))
    parser.add_argument("article", type=Path)
    parser.add_argument("--workspace-root", type=Path, default=None)
    return parser


def _verify(article: Path, root: Path) -> int:
    layout = Layout.for_article(article, root)
    path = latest_record_path(layout)
    print(f"record: {path if path else 'none'}")
    try:
        latest = latest_record(layout)
        if latest is not None:
            print(f"passed: {'true' if latest.get('passed') is True else 'false'}")
        verify_publishable(article, root)
    except ValueError as error:
        print(f"refused: {error}")
        return 1
    print("publishable")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exit_request:
        return int(exit_request.code or 0)
    try:
        return _verify(args.article, (args.workspace_root or Path.cwd()).resolve())
    except LayoutError as error:
        print(f"record: {error}", file=sys.stderr)
        return 2


__all__ = [
    "RECORD_NAME",
    "RECORD_SCHEMA",
    "bom_bindings",
    "file_sha256",
    "latest_record",
    "latest_record_path",
    "main",
    "record_passed",
    "verify_publishable",
    "write_record",
]


if __name__ == "__main__":
    raise SystemExit(main())
