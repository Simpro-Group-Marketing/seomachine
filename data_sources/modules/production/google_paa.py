"""Record the Google SERP PAA fallback capture when AnswerSocrates is unavailable.

Usage:
  python -m data_sources.modules.production.google_paa --query Q --run-id R --google-country au
      --page-url U --collected-at ISO --questions-file F --answersocrates-state STATE
      --answersocrates-text-file T --answersocrates-url A --answersocrates-observed-at ISO
      --output O [--workspace-root DIR]

The questions file is a JSON list of the "People also ask" question texts read from the live Google
results page in the user's main Chrome window, in page order (an empty list when Google shows no PAA
box). The text file holds the AnswerSocrates blocker text saved unedited from its live tab. The
capture goes to the layout's PAA artifact path; see ``paa_provenance/google_serp.py`` for the
contract and the provenance caveat. Exit codes: 0 recorded, 2 error (one line on stderr).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.editorial_plan.contracts import SERP_APPROVED_GOOGLE_COUNTRIES, _rfc3339_utc
from data_sources.modules.execution_attestation import attest_mapping
from data_sources.modules.paa_provenance.contracts import ANSWERSOCRATES_BLOCKER_STATES
from data_sources.modules.paa_provenance.google_serp import (
    GOOGLE_SERP_PAA_COLLECTOR,
    GOOGLE_SERP_PAA_SCHEMA,
    blocker_error,
)


def _google_search_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if parsed.scheme != "https" or not (host == "www.google.com" or host.startswith("www.google.com.")):
        raise ValueError(f"page url must be a https://www.google.com[.cc]/search URL, found: {url!r}")
    if parsed.path != "/search":
        raise ValueError(f"page url path must be /search, found: {parsed.path!r}")
    return url


def _questions(path: Path) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise ValueError(f"questions file {path} is unreadable: {error}") from error
    if not isinstance(payload, list) or not all(isinstance(item, str) for item in payload):
        raise ValueError("questions file must be a JSON list of question text")
    questions: list[str] = []
    for item in (" ".join(text.split()) for text in payload):
        if not item.endswith("?"):
            raise ValueError(f"not a question (must end in '?'): {item!r}")
        if item.casefold() not in {question.casefold() for question in questions}:
            questions.append(item)
    return questions


def _blocker(args: argparse.Namespace) -> dict[str, str]:
    try:
        text = args.answersocrates_text_file.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as error:
        raise ValueError(f"AnswerSocrates blocker text file is unreadable: {error}") from error
    blocker = {"state": args.answersocrates_state, "observed_text": text, "page_url": args.answersocrates_url,
               "observed_at": args.answersocrates_observed_at}
    error = blocker_error(blocker, collection_date=args.collected_at[:10], collected_at=args.collected_at)
    if error:
        raise ValueError(error)
    return blocker


def build_capture(args: argparse.Namespace) -> dict[str, Any]:
    """Return the unsigned capture after checking every input."""
    query = " ".join(str(args.query).split())
    if not query:
        raise ValueError("query must be non-empty text")
    if not str(args.run_id).strip():
        raise ValueError("run id must be non-empty text")
    collected = _rfc3339_utc(args.collected_at)
    if collected is None:
        raise ValueError(f"collected-at must be an RFC 3339 UTC time like {datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}")
    if collected > datetime.now(timezone.utc):
        raise ValueError(f"collected-at {args.collected_at} is in the future")
    return {
        "schema": GOOGLE_SERP_PAA_SCHEMA,
        "collector": dict(GOOGLE_SERP_PAA_COLLECTOR),
        "query": query,
        "google_country": args.google_country,
        "page_url": _google_search_url(args.page_url),
        "collected_at": args.collected_at,
        "collection_date": args.collected_at[:10],
        "run_receipt": {"run_id": args.run_id},
        "eligible_questions": _questions(args.questions_file),
        "answersocrates_blocker": _blocker(args),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="google_paa", description=__doc__)
    for flag in ("--query", "--run-id", "--page-url", "--collected-at", "--answersocrates-url",
                 "--answersocrates-observed-at"):
        parser.add_argument(flag, required=True)
    parser.add_argument("--google-country", required=True, choices=sorted(SERP_APPROVED_GOOGLE_COUNTRIES))
    parser.add_argument("--answersocrates-state", required=True, choices=sorted(ANSWERSOCRATES_BLOCKER_STATES))
    parser.add_argument("--questions-file", required=True, type=Path)
    parser.add_argument("--answersocrates-text-file", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workspace-root", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exit_request:
        return int(exit_request.code or 0)
    root = (args.workspace_root or Path.cwd()).resolve()
    try:
        capture = build_capture(args)
        atomic_write_json(args.output, attest_mapping(capture, purpose=GOOGLE_SERP_PAA_SCHEMA, workspace_root=root))
    except (OSError, ValueError) as error:
        print(f"google_paa: {error}", file=sys.stderr)
        return 2
    print(f"google_paa: recorded {len(capture['eligible_questions'])} question(s) to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
