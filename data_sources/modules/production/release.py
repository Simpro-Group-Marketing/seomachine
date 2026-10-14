"""One-pass release check: refresh same-day inputs, rebuild the BOM, check, score, and record.

Usage: python -m data_sources.modules.production.release <article> [--workspace-root DIR] [--workers N]

Steps: refresh the customer-proof selector evidence (connector or nonvault, decided from the spec
as the BOM build does) from the inputs recorded in it, pinned to the BOM's current selections (a
pinned proof the selector no longer offers refuses the BOM); rebuild the production BOM (live fact
checks and the selector-first check run again; a fact whose page is merely unreachable keeps its
earlier verification, and truth warns); run the truth and coverage checks in a thread pool while
the scorer runs; write one release record. Every run that fails after the refresh also writes a
failing record, so an older pass never stays the latest. ``record.verify_publishable`` (the
``record verify`` CLI) trusts only the latest record; the WordPress and Grav publishers are not
wired to the record. Release never writes the customer-proof usage ledger: per the customer-proof
rule, the ledger entry is added before final handoff.

Workers: ``--workers N`` overrides ``SEOMACHINE_RELEASE_WORKERS``, which defaults to 2.
With 1 worker everything runs sequentially in this process, with no pools.

Exit codes: 0 passed; 1 blocked (refused rebuild, block findings, or failed scores);
2 operational or argument error (missing BOM or spec, bad layout, refresh failure such as a
vault outage, stale evidence at scoring, an article edited mid-run, or any unexpected error).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from data_sources.modules.production.bom import BuildEnvironmentError, SpecFileError, load_bom
from data_sources.modules.production.bom_artifacts import read_spec_bound
from data_sources.modules.production.bom_build import _retire_stale_bom, _write_bom, build_bom, is_nonconnector
from data_sources.modules.production.bom_selector import evidence_path
from data_sources.modules.production.coverage import check_coverage
from data_sources.modules.production.layout import Layout, LayoutError, load_or_create_run_id, stored_bom_sha256
from data_sources.modules.production.record import file_sha256, write_record
from data_sources.modules.production.scoring import ScoringPreflightError, score_article
from data_sources.modules.production.selector_refresh import PinnedSelectionRejected, refresh_selector_evidence
from data_sources.modules.production.truth import check_truth
from data_sources.modules.production.truth_text import Finding
from data_sources.modules.public_http import PublicHttpTransport
from data_sources.modules.vault_claim_receipts import load_validated_claim_set

ENV_WORKERS = "SEOMACHINE_RELEASE_WORKERS"
DEFAULT_WORKERS = 2
_SCORE_LINES = (("content", "content_quality"), ("seo", "seo_quality"), ("aeo_geo", "aeo_geo"))

BOM_BUILD_COMMAND = "python -m data_sources.modules.production.bom_build"

Refresher = Callable[[Layout, bool, Mapping[str, Any]], Any]


class ReleaseStop(Exception):
    """Stop the release with an exit code, one message line per reason, and the record check name."""

    def __init__(self, code: int, lines: Sequence[str], *, check: str = "release_error", bom_retired: bool = False):
        super().__init__("\n".join(lines))
        self.code, self.lines, self.check, self.bom_retired = code, list(lines), check, bom_retired


@dataclass(frozen=True)
class _Run:
    """What the release fixed at its start: layout, run id, article bytes, spec, and the old BOM."""

    layout: Layout
    run_id: str
    article_bytes: bytes
    article_sha: str
    spec: dict[str, Any]
    old_bom: dict[str, Any]
    nonconnector: bool
    workers: int


def _report(lines: Sequence[str], stream: Any = None) -> None:
    for line in lines:
        print(f"release: {line}", file=stream or sys.stderr)


def parse_workers(value: str | int) -> int:
    """A worker count is a positive integer; anything else raises ValueError."""
    workers = int(value)
    if workers < 1:
        raise ValueError(f"worker count must be at least 1, found: {value}")
    return workers


def default_workers(environ: Mapping[str, str] = os.environ) -> int:
    raw = environ.get(ENV_WORKERS, "").strip()
    try:
        return parse_workers(raw) if raw else DEFAULT_WORKERS
    except ValueError as error:
        raise ValueError(f"{ENV_WORKERS} must be a positive integer, found: {raw!r}") from error


def needs_refresh(layout: Layout, spec: Mapping[str, Any], nonconnector: bool) -> bool:
    """Refresh when the spec names proof or this article's selector evidence exists."""
    return bool(spec.get("proof")) or evidence_path(layout, nonconnector).is_file()


def _missing_bom_message(layout: Layout) -> str:
    """Say why the BOM is missing and which command builds it."""
    command = f"`{BOM_BUILD_COMMAND} {layout.article.relative_to(layout.root).as_posix()}`"
    refused = layout.bom.with_name(layout.bom.name + ".refused")
    if refused.exists():
        return (
            f"production BOM was refused at the last build ({refused}); "
            f"fix the BOM spec or research inputs, then run {command}"
        )
    return f"production BOM not found; expected {layout.bom}; build it with {command}"


def _resolve(article: Path, root: Path) -> Layout:
    try:
        return Layout.for_article(article, root)
    except LayoutError as error:
        raise ReleaseStop(2, [str(error)]) from error


def _prepare(article: Path, root: Path, workers: int) -> _Run:
    """Resolve the layout and run id, require the inputs, and hash the article once."""
    layout = _resolve(article, root)
    for label, path in (("article", layout.article), ("BOM spec", layout.bom_spec)):
        if not path.is_file():
            raise ReleaseStop(2, [f"{label} not found; expected {path}"])
    if not layout.bom.is_file():
        raise ReleaseStop(2, [_missing_bom_message(layout)])
    try:
        article_bytes = layout.article.read_bytes()
        spec, _binding = read_spec_bound(layout)
        run_id = load_or_create_run_id(layout)
        old_bom = load_bom(layout.bom)
    except (OSError, ValueError, SpecFileError) as error:
        raise ReleaseStop(2, [str(error)]) from error
    sha = hashlib.sha256(article_bytes).hexdigest()
    return _Run(layout, run_id, article_bytes, sha, spec, old_bom, is_nonconnector(spec), workers)


def _refresh(run: _Run, refresher: Refresher) -> None:
    if not needs_refresh(run.layout, run.spec, run.nonconnector):
        return
    try:
        refresher(run.layout, run.nonconnector, run.old_bom)
    except PinnedSelectionRejected as error:
        _retire_stale_bom(run.layout)
        stop = ReleaseStop(1, [f"BOM rebuild refused: {error}"], check="bom_refused", bom_retired=True)
        stop.lines.append(_record_failure(run, stop))
        raise stop from error
    except Exception as error:  # noqa: BLE001 - any other refresh failure leaves the evidence stale
        raise ReleaseStop(2, [
            f"customer-proof selector refresh failed: {type(error).__name__}: {error}",
            "the bound selector evidence was not refreshed; fix the cause and release again",
        ]) from error


def _prior_facts(layout: Layout, old_bom: Mapping[str, Any]) -> dict[str, Mapping[str, Any]] | None:
    """The old BOM's facts, only when it is still the file the pipeline wrote (its hash was recorded)."""
    recorded = stored_bom_sha256(layout)
    if recorded is None or file_sha256(layout.bom) != recorded:
        return None
    facts = old_bom.get("facts") if isinstance(old_bom.get("facts"), list) else []
    return {str(fact["id"]): fact for fact in facts if isinstance(fact, Mapping) and "id" in fact}


def _rebuild(run: _Run, transport: Any) -> tuple[dict[str, Any], str]:
    """Rebuild and write the BOM; a refused or failed rebuild retires the earlier BOM, as bom_build does.

    Facts verified by the previous BOM survive an unreachable page (truth then warns); a lost
    quote or a gone page still refuses.
    """
    layout = run.layout
    try:
        bom = build_bom(
            layout, transport=transport, claim_loader=load_validated_claim_set, prior_facts=_prior_facts(layout, run.old_bom)
        )
        _write_bom(layout, bom)
        return bom, file_sha256(layout.bom)
    except (SpecFileError, BuildEnvironmentError, OSError) as error:
        _retire_stale_bom(layout)
        lines = [f"BOM rebuild failed: {line}" for line in str(error).splitlines()]
        raise ReleaseStop(2, lines, check="bom_build_failed", bom_retired=True) from error
    except ValueError as error:
        _retire_stale_bom(layout)
        lines = [f"BOM rebuild refused: {line}" for line in str(error).splitlines()]
        raise ReleaseStop(1, lines, check="bom_refused", bom_retired=True) from error


def _carried_findings(bom: Mapping[str, Any]) -> list[Finding]:
    """One warning per fact kept from an earlier verification, so the record always shows it."""
    return [
        Finding(
            "fact_carried_forward", "warn",
            f"fact {fact.get('id')} ({fact.get('url')}) was not re-verified: its page is unreachable "
            f"({fact.get('release_check')}); carried forward from the verification at {fact.get('verified_at')}",
            None,
        )
        for fact in bom.get("facts") or []
        if isinstance(fact, Mapping) and fact.get("carried_forward") is True
    ]


def _run_checks(run: _Run, bom: Mapping[str, Any], transport: Any) -> tuple[list[Any], dict[str, Any]]:
    """Truth and coverage beside scoring; scoring is submitted first so the slow jobs overlap."""
    text = run.article_bytes.decode("utf-8")
    jobs: dict[str, Callable[[], Any]] = {
        "scores": lambda: score_article(run.layout.article, bom, workers=run.workers),
        "truth": lambda: check_truth(text, bom, transport=transport),
        "coverage": lambda: check_coverage(text, bom),
    }
    try:
        if run.workers <= 1:
            results = {name: job() for name, job in jobs.items()}
        else:
            with ThreadPoolExecutor(max_workers=run.workers) as pool:
                futures = {name: pool.submit(job) for name, job in jobs.items()}
                results = {name: future.result() for name, future in futures.items()}
    except ScoringPreflightError as error:
        raise ReleaseStop(2, [f"scoring preflight: {error}"]) from error
    return [*results["truth"], *results["coverage"], *_carried_findings(bom)], results["scores"]


def _score_lines(scores: Mapping[str, Any]) -> list[str]:
    gates = scores.get("gates") or {}
    lines = []
    for key, gate_name in _SCORE_LINES:
        gate = gates.get(gate_name) or {}
        extra = f", critical {scores.get('seo_critical', 0)}" if key == "seo" else ""
        verdict = "pass" if gate.get("passed") else "FAIL"
        lines.append(f"{key} {float(scores.get(key) or 0):.1f} (min {gate.get('threshold')}{extra}) {verdict}")
    return lines


def _at(line: Any) -> str:
    return f" line {line}" if line else ""


def _summary(record: Mapping[str, Any], path: Path) -> None:
    blocks = [row for row in record["findings"] if row["severity"] != "warn"]
    lines = [f"BLOCK {row['check']}{_at(row['line'])}: {row['message']}" for row in blocks]
    lines += _score_lines(record["scores"])
    lines.append(f"{record['warns']} warning(s); record: {path}")
    lines.append("PASSED" if record["passed"] else f"BLOCKED ({record['blocks']} block finding(s))")
    _report(lines, sys.stdout)


def _current_article_sha(layout: Layout) -> str:
    return file_sha256(layout.article) if layout.article.is_file() else "missing"


def _check_and_record(run: _Run, transport: Any) -> int:
    scope = nullcontext(transport) if transport is not None else PublicHttpTransport()
    with scope as shared:
        bom, bom_sha = _rebuild(run, shared)
        findings, scores = _run_checks(run, bom, shared)
    if _current_article_sha(run.layout) != run.article_sha:
        raise ReleaseStop(2, ["article changed during release; release it again"])
    path = write_record(
        run.layout, run.run_id, article_sha256=run.article_sha, bom_sha256=bom_sha,
        findings=findings, scores=scores, bom=bom, workers=run.workers,
    )
    record = json.loads(path.read_text(encoding="utf-8"))
    _summary(record, path)
    return 0 if record["passed"] else 1


def _failure_bom_file(layout: Layout, stop: ReleaseStop) -> Path | None:
    """The refused BOM after a refused rebuild (None if it was not moved aside); else the current BOM."""
    if stop.bom_retired:
        refused = layout.bom.with_name(layout.bom.name + ".refused")
        return refused if refused.is_file() and not layout.bom.exists() else None
    return layout.bom if layout.bom.is_file() else None


def _record_failure(run: _Run, stop: ReleaseStop) -> str:
    """Write a failing record so an older pass never stays the latest record; return a report line."""
    bom_file = _failure_bom_file(run.layout, stop)
    try:
        path = write_record(
            run.layout, run.run_id, article_sha256=run.article_sha,
            bom_sha256=file_sha256(bom_file) if bom_file else None, bom_path=bom_file,
            findings=[Finding(stop.check, "block", line, None) for line in stop.lines],
            scores=None, bom=None, workers=run.workers,
        )
    except Exception as error:  # noqa: BLE001 - report it; the release already failed
        return f"could not write the failure record: {type(error).__name__}: {error}"
    return f"failure recorded: {path}"


def _release(article: Path, root: Path, *, workers: int, transport: Any, refresher: Refresher) -> int:
    run = _prepare(article, root, workers)
    _refresh(run, refresher)
    try:
        return _check_and_record(run, transport)
    except ReleaseStop as stop:
        stop.lines.append(_record_failure(run, stop))
        raise
    except Exception as error:  # noqa: BLE001 - recorded as a failure, then reported without a traceback
        stop = ReleaseStop(2, [f"unexpected error: {type(error).__name__}: {error}"])
        stop.lines.append(_record_failure(run, stop))
        raise stop from error


def run_release(
    article: str | Path,
    root: str | Path,
    *,
    workers: int,
    transport: Any = None,
    refresher: Refresher | None = None,
) -> int:
    """Run one release and return its exit code; no exception or traceback escapes."""
    try:
        return _release(
            Path(article), Path(root), workers=parse_workers(workers), transport=transport,
            refresher=refresher or refresh_selector_evidence,
        )
    except ReleaseStop as stop:
        _report(stop.lines)
        return stop.code
    except Exception as error:  # noqa: BLE001 - the CLI must never leak a traceback
        _report([f"unexpected error: {type(error).__name__}: {error}"])
        return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="release", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("article", type=Path)
    parser.add_argument("--workspace-root", type=Path, default=None)
    parser.add_argument("--workers", type=parse_workers, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exit_request:
        return int(exit_request.code or 0)
    try:
        workers = args.workers if args.workers is not None else default_workers()
    except ValueError as error:
        _report([str(error)])
        return 2
    return run_release(args.article, (args.workspace_root or Path.cwd()).resolve(), workers=workers)


if __name__ == "__main__":
    sys.exit(main())
