"""One-pass release check: refresh same-day inputs, rebuild the BOM, check, score, and record.

Usage: python -m data_sources.modules.production.release <article> [--workspace-root DIR] [--workers N]

Steps: refresh the customer-proof selector evidence from the inputs recorded in it; rebuild the
production BOM (live fact checks and the selector-first check run again); run the truth and
coverage checks in a thread pool while the scorer runs; write one release record. Publishers
trust only that record (see ``record.verify_publishable``). Release never writes the
customer-proof usage ledger; publishing records proof use.

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
from pathlib import Path
from typing import Any

from data_sources.modules.production.bom import BuildEnvironmentError, SpecFileError, load_bom
from data_sources.modules.production.bom_build import _retire_stale_bom, _write_bom, build_bom
from data_sources.modules.production.coverage import check_coverage
from data_sources.modules.production.layout import Layout, LayoutError, load_or_create_run_id
from data_sources.modules.production.record import file_sha256, write_record
from data_sources.modules.production.scoring import ScoringPreflightError, score_article
from data_sources.modules.production.selector_refresh import refresh_selector_evidence
from data_sources.modules.production.truth import check_truth
from data_sources.modules.public_http import PublicHttpTransport
from data_sources.modules.vault_claim_receipts import load_validated_claim_set

ENV_WORKERS = "SEOMACHINE_RELEASE_WORKERS"
DEFAULT_WORKERS = 2
_SCORE_LINES = (("content", "content_quality"), ("seo", "seo_quality"), ("aeo_geo", "aeo_geo"))

BOM_BUILD_COMMAND = "python -m data_sources.modules.production.bom_build"

Refresher = Callable[[Layout, Mapping[str, Any]], Any]


class ReleaseStop(Exception):
    """Stop the release with an exit code and one message line per reason."""

    def __init__(self, code: int, lines: Sequence[str]):
        super().__init__("\n".join(lines))
        self.code, self.lines = code, list(lines)


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


def needs_refresh(bom: Mapping[str, Any]) -> bool:
    """Refresh unless the BOM has neither proof nor bound selector evidence."""
    evidence = (bom.get("customer_proof") or {}).get("evidence")
    return bool(bom.get("proof")) or isinstance(evidence, Mapping)


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


def _prepare(article: Path, root: Path) -> tuple[Layout, str, bytes, dict[str, Any]]:
    """Resolve the layout and run id, require the inputs, and hash the article once."""
    try:
        layout = Layout.for_article(article, root)
    except LayoutError as error:
        raise ReleaseStop(2, [str(error)]) from error
    for label, path in (("article", layout.article), ("BOM spec", layout.bom_spec)):
        if not path.is_file():
            raise ReleaseStop(2, [f"{label} not found; expected {path}"])
    if not layout.bom.is_file():
        raise ReleaseStop(2, [_missing_bom_message(layout)])
    try:
        article_bytes = layout.article.read_bytes()
        run_id = load_or_create_run_id(layout)
        bom = load_bom(layout.bom)
    except (OSError, ValueError) as error:
        raise ReleaseStop(2, [str(error)]) from error
    return layout, run_id, article_bytes, bom


def _refresh(layout: Layout, bom: Mapping[str, Any], refresher: Refresher) -> None:
    if not needs_refresh(bom):
        return
    try:
        refresher(layout, bom)
    except Exception as error:  # noqa: BLE001 - any refresh failure leaves the evidence stale
        raise ReleaseStop(2, [
            f"customer-proof selector refresh failed: {type(error).__name__}: {error}",
            "the bound selector evidence was not refreshed; fix the cause and release again",
        ]) from error


def _rebuild(layout: Layout, transport: Any) -> tuple[dict[str, Any], str]:
    """Rebuild and write the BOM; a refused or failed rebuild retires the earlier BOM, as bom_build does."""
    try:
        bom = build_bom(layout, transport=transport, claim_loader=load_validated_claim_set)
        _write_bom(layout, bom)
        return bom, file_sha256(layout.bom)
    except (SpecFileError, BuildEnvironmentError, OSError) as error:
        _retire_stale_bom(layout)
        raise ReleaseStop(2, [f"BOM rebuild failed: {line}" for line in str(error).splitlines()]) from error
    except ValueError as error:
        _retire_stale_bom(layout)
        raise ReleaseStop(1, [f"BOM rebuild refused: {line}" for line in str(error).splitlines()]) from error


def _run_checks(
    layout: Layout, text: str, bom: Mapping[str, Any], transport: Any, workers: int
) -> tuple[list[Any], dict[str, Any]]:
    """Truth and coverage beside scoring; scoring is submitted first so the slow jobs overlap."""
    jobs: dict[str, Callable[[], Any]] = {
        "scores": lambda: score_article(layout.article, bom, workers=workers),
        "truth": lambda: check_truth(text, bom, transport=transport),
        "coverage": lambda: check_coverage(text, bom),
    }
    try:
        if workers <= 1:
            results = {name: job() for name, job in jobs.items()}
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {name: pool.submit(job) for name, job in jobs.items()}
                results = {name: future.result() for name, future in futures.items()}
    except ScoringPreflightError as error:
        raise ReleaseStop(2, [f"scoring preflight: {error}"]) from error
    return [*results["truth"], *results["coverage"]], results["scores"]


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
    blocks = [row for row in record["findings"] if row["severity"] == "block"]
    lines = [f"BLOCK {row['check']}{_at(row['line'])}: {row['message']}" for row in blocks]
    lines += _score_lines(record["scores"])
    lines.append(f"{record['warns']} warning(s); record: {path}")
    lines.append("PASSED" if record["passed"] else f"BLOCKED ({record['blocks']} block finding(s))")
    _report(lines, sys.stdout)


def _release(
    article: Path, root: Path, *, workers: int, transport: Any, refresher: Refresher
) -> int:
    layout, run_id, article_bytes, old_bom = _prepare(article, root)
    start_sha = hashlib.sha256(article_bytes).hexdigest()
    _refresh(layout, old_bom, refresher)
    scope = nullcontext(transport) if transport is not None else PublicHttpTransport()
    with scope as shared:
        bom, bom_sha = _rebuild(layout, shared)
        findings, scores = _run_checks(layout, article_bytes.decode("utf-8"), bom, shared, workers)
    if not layout.article.is_file() or file_sha256(layout.article) != start_sha:
        raise ReleaseStop(2, ["article changed during release; nothing was recorded, release it again"])
    path = write_record(
        layout, run_id, article_sha256=start_sha, bom_sha256=bom_sha,
        findings=findings, scores=scores, bom=bom, workers=workers,
    )
    record = json.loads(path.read_text(encoding="utf-8"))
    _summary(record, path)
    return 0 if record["passed"] else 1


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
