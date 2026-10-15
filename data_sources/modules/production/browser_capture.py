"""Chrome capture recorders for the PAA and SERP research lanes.

Usage:
  python -m data_sources.modules.production.browser_capture paa --query Q --run-id R --page-url U
      --page-title T --text-file F --started-at ISO --completed-at ISO --output O [--workspace-root DIR]
  python -m data_sources.modules.production.browser_capture serp --query Q --run-id R --google-country au
      --results-file F --collected-at ISO --output O [--evidence-output E] [--workspace-root DIR]

Fallback for when the Playwright CLI session or DataForSEO is unavailable. ``paa`` writes a
``simpro-answersocrates-chrome-connector-capture/v1`` capture from AnswerSocrates page text saved
verbatim from the user's main Chrome window; ``paa_provenance_guard.py record --raw-capture-input``
then records it. The ``People Also Ask`` section is derived mechanically: the one line that reads
exactly "People Also Ask" (or "People Also Asked"), then every following non-blank line that ends in
"?" until the first line that does not. Blocker observations are DOM-scoped and plain text carries
no scope, so they stay empty; a page with no such questions is refused, not recorded as blocked.
``serp`` writes a ``simpro-serp-raw-capture/v1`` capture from organic results read from the Google
results page DOM, and with ``--evidence-output`` also builds the ``simpro-serp-evidence/v1`` file.

Provenance caveat: the execution attestation proves this workspace wrote the record and that it is
unchanged since then. It does not prove that Chrome served it. The collector name is self-declared,
and no automated check can tell a faithful capture from typed text (as with ``page_capture``).
Times are the real capture times, RFC 3339 UTC with a trailing Z.
Exit codes: 0 recorded, 2 error (one line on stderr).
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.editorial_plan.contracts import (
    SERP_APPROVED_GOOGLE_COUNTRIES,
    SERP_RAW_CAPTURE_ATTESTATION_PURPOSE,
    SERP_RAW_CAPTURE_SCHEMA,
    _rfc3339_utc,
)
from data_sources.modules.editorial_plan.serp_capture import build_serp_evidence
from data_sources.modules.editorial_plan.serp_raw import (
    _playwright_request_valid,
    _validate_normalized_response,
)
from data_sources.modules.execution_attestation import attest_mapping
from data_sources.modules.paa_provenance.contracts import (
    ANSWERSOCRATES_CHROME_CONNECTOR_RAW_CAPTURE_SCHEMA as PAA_SCHEMA,
    ANSWERSOCRATES_CHROME_CONNECTOR_TOOL,
    ANSWERSOCRATES_PAGE_URLS,
)
from data_sources.modules.paa_provenance.observations import _derive_answersocrates_observations

SERP_COLLECTOR = {"name": "research_serp_analysis:chrome_connector", "version": "1.0.0"}
PAA_HEADINGS = frozenset({"people also ask", "people also asked"})
_ROW_KEYS = frozenset({"position", "url", "title"})
_RESULTS_KEYS = frozenset({"organic_results", "features"})


def _inside(root: Path, path: str | Path, label: str) -> Path:
    """Resolve a path (relative paths start at the workspace root) and require it to stay inside."""
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label} is outside the workspace: {path}") from error
    return candidate


def _read_text(path: Path, label: str) -> str:
    try:
        return path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ValueError(f"{label} cannot be read as UTF-8 text: {error}") from error


def _require_query(query: str) -> str:
    if not query.strip() or query != query.strip():
        raise ValueError("query must be non-empty text without leading or trailing spaces")
    return query


def _require_run_id(run_id: str) -> str:
    try:
        canonical = str(uuid.UUID(run_id))
    except ValueError:
        canonical = None
    if canonical != run_id:
        raise ValueError(f"run id must be a lowercase hyphenated UUID, found: {run_id!r}")
    return run_id


def _require_time(value: str, label: str) -> datetime:
    parsed = _rfc3339_utc(value)
    if parsed is None:
        raise ValueError(f"{label} must be an RFC 3339 UTC time like 2026-10-15T08:00:00Z, found: {value!r}")
    if parsed > datetime.now(timezone.utc):
        raise ValueError(f"{label} {value} is in the future")
    return parsed


def paa_sections(text: str) -> list[dict[str, Any]]:
    """Derive the People Also Ask section from verbatim page text, one block element per line."""
    lines = [line.strip() for line in text.splitlines()]
    starts = [index for index, line in enumerate(lines) if line.casefold() in PAA_HEADINGS]
    if len(starts) != 1:
        found = "no" if not starts else "more than one"
        raise ValueError(
            f"page text has {found} line reading exactly 'People Also Ask'; save the page text with its line breaks"
        )
    items: list[str] = []
    for line in lines[starts[0] + 1:]:
        if not line:
            continue
        if not line.endswith("?"):
            break
        if line.casefold() not in {item.casefold() for item in items}:
            items.append(line)
    return [{"heading": lines[starts[0]], "items": items}]


def build_paa_capture(
    *, query: str, run_id: str, page_url: str, page_title: str, text: str, started_at: str, completed_at: str
) -> dict[str, Any]:
    """Return the unsigned Chrome-connector AnswerSocrates capture, validated as the recorder will."""
    _require_query(query)
    _require_run_id(run_id)
    if page_url not in ANSWERSOCRATES_PAGE_URLS:
        raise ValueError(f"page url must be one of {sorted(ANSWERSOCRATES_PAGE_URLS)}, found: {page_url!r}")
    if not page_title.strip():
        raise ValueError("page title must be non-empty text")
    if not text.strip():
        raise ValueError("page text is empty")
    started = _require_time(started_at, "started-at")
    if _require_time(completed_at, "completed-at") <= started:
        raise ValueError("completed-at must be later than started-at")
    browser_output = {
        "page_url": page_url,
        "page_title": page_title,
        "body_text": text,
        "sections": paa_sections(text),
        "blocker_observations": [],
    }
    raw_response = {"stdout": json.dumps(browser_output, ensure_ascii=False), "stderr": "", "returncode": 0}
    _derive_answersocrates_observations(raw_response)  # the recorder's own parse; raises if no questions
    return {
        "schema": PAA_SCHEMA,
        "collector": dict(ANSWERSOCRATES_CHROME_CONNECTOR_TOOL),
        "query": query,
        "run_id": run_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "page_url": page_url,
        "raw_response": raw_response,
    }


def _result_row(row: object) -> dict[str, Any]:
    if not isinstance(row, Mapping) or set(row) != _ROW_KEYS:
        raise ValueError(f"each organic result must have exactly position, url, and title: {row!r}")
    position, url, title = row["position"], row["url"], row["title"]
    if not isinstance(position, int) or isinstance(position, bool):
        raise ValueError(f"organic result position must be an integer: {position!r}")
    parsed = urlparse(url) if isinstance(url, str) else None
    if parsed is None or parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError(f"organic result url must be an absolute http(s) URL, found: {url!r}")
    if not isinstance(title, str) or not title.strip():
        raise ValueError(f"organic result title must be non-empty text at position {position}")
    return {"position": position, "title": title, "url": url}


def _results_payload(value: object) -> tuple[list[Any], list[Any]]:
    if isinstance(value, list):
        return value, []
    if isinstance(value, Mapping) and "organic_results" in value and set(value) <= _RESULTS_KEYS:
        rows, features = value["organic_results"], value.get("features", [])
        if isinstance(rows, list) and isinstance(features, list):
            return rows, features
    raise ValueError("results file must be a list of organic results or an object with organic_results and features")


def parse_serp_results(value: object) -> dict[str, Any]:
    """Validate extracted organic results and return the raw response, rows ordered by position."""
    rows, features = _results_payload(value)
    if not rows:
        raise ValueError("results file has no organic results (empty)")
    ordered = sorted((_result_row(row) for row in rows), key=lambda row: row["position"])
    if [row["position"] for row in ordered] != list(range(1, len(ordered) + 1)):
        raise ValueError("organic result positions must be exactly 1..N with no gaps or duplicates")
    if any(not isinstance(item, str) or not item.strip() for item in features):
        raise ValueError("features must be non-empty strings")
    raw_response = {"organic_results": ordered, "features": features}
    _validate_normalized_response(raw_response)
    return raw_response


def build_serp_capture(
    *, query: str, run_id: str, google_country: str, results: object, collected_at: str
) -> dict[str, Any]:
    """Return the unsigned Chrome-connector raw SERP capture, validated as the evidence build will."""
    _require_query(query)
    _require_run_id(run_id)
    _require_time(collected_at, "collected-at")
    locale = {"hl": "en", "gl": google_country, "pws": "0"}
    url = "https://www.google.com/search?" + urlencode({"q": query, **locale})
    if not _playwright_request_valid(url, locale, query=query):
        raise ValueError(f"Google search request is not approved for country {google_country!r}")
    return {
        "schema": SERP_RAW_CAPTURE_SCHEMA,
        "collector": dict(SERP_COLLECTOR),
        "query": query,
        "collected_at": collected_at,
        "run_id": run_id,
        "request": {"url": url, "locale": locale},
        "raw_response": parse_serp_results(results),
    }


def record_paa(args: argparse.Namespace, root: Path) -> list[Path]:
    text_path = _inside(root, args.text_file, "text file")
    output = _inside(root, args.output, "output")
    capture = build_paa_capture(
        query=args.query, run_id=args.run_id, page_url=args.page_url, page_title=args.page_title,
        text=_read_text(text_path, "text file"), started_at=args.started_at, completed_at=args.completed_at,
    )
    atomic_write_json(output, attest_mapping(capture, purpose=PAA_SCHEMA, workspace_root=root))
    return [output]


def record_serp(args: argparse.Namespace, root: Path) -> list[Path]:
    results_path = _inside(root, args.results_file, "results file")
    output = _inside(root, args.output, "output")
    evidence_output = _inside(root, args.evidence_output, "evidence output") if args.evidence_output else None
    try:
        results = json.loads(_read_text(results_path, "results file"))
    except json.JSONDecodeError as error:
        raise ValueError(f"results file is not valid JSON: {error}") from error
    capture = build_serp_capture(
        query=args.query, run_id=args.run_id, google_country=args.google_country,
        results=results, collected_at=args.collected_at,
    )
    signed = attest_mapping(capture, purpose=SERP_RAW_CAPTURE_ATTESTATION_PURPOSE, workspace_root=root)
    atomic_write_json(output, signed)
    if evidence_output is None:
        return [output]
    evidence = build_serp_evidence(
        raw_capture_path=output, workspace_root=root, must_have_sections=[], competitor_gaps=[]
    )
    atomic_write_json(evidence_output, evidence)
    return [output, evidence_output]


def _paa_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="browser_capture paa", description=__doc__)
    for flag in ("--query", "--run-id", "--page-url", "--page-title", "--started-at", "--completed-at"):
        parser.add_argument(flag, required=True)
    parser.add_argument("--text-file", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workspace-root", type=Path, default=None)
    return parser


def _serp_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="browser_capture serp", description=__doc__)
    for flag in ("--query", "--run-id", "--collected-at"):
        parser.add_argument(flag, required=True)
    parser.add_argument("--google-country", required=True, choices=sorted(SERP_APPROVED_GOOGLE_COUNTRIES))
    parser.add_argument("--results-file", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--evidence-output", type=Path, default=None)
    parser.add_argument("--workspace-root", type=Path, default=None)
    return parser


_COMMANDS: dict[str, tuple[Callable[[], argparse.ArgumentParser], Callable[..., list[Path]]]] = {
    "paa": (_paa_parser, record_paa),
    "serp": (_serp_parser, record_serp),
}


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] not in _COMMANDS:
        print("browser_capture: usage: browser_capture {paa,serp} [options]; see --help", file=sys.stderr)
        return 2
    build_parser, record = _COMMANDS[arguments[0]]
    try:
        args = build_parser().parse_args(arguments[1:])
    except SystemExit as exit_request:
        return int(exit_request.code or 0)
    root = (args.workspace_root or Path.cwd()).resolve()
    try:
        written = record(args, root)
    except (ValueError, OSError) as error:
        print(f"browser_capture: {' '.join(str(error).split())}", file=sys.stderr)
        return 2
    for path in written:
        print(f"browser_capture: recorded {path.relative_to(root).as_posix()}")
    return 0


__all__ = ["build_paa_capture", "build_serp_capture", "main", "paa_sections", "parse_serp_results"]

if __name__ == "__main__":
    raise SystemExit(main())
