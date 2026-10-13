"""Page-1 coverage map: which topics the top-10 Google results cover.

Reads saved SERP evidence, fetches each result, extracts its H2/H3 outline, and
counts how many fetched pages cover each topic. Claude uses the map to choose
the must and should sections of the production BOM.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.production.layout import Layout, LayoutError
from data_sources.modules.public_http import SOURCE_VISIBLE_TEXT_POLICY, PublicHttpTransport
from data_sources.modules.source_support.common import DEFAULT_USER_AGENT

COVERAGE_SCHEMA = "simpro-serp-coverage/v1"
MAX_RESULTS = 10
QUESTION_COVERAGE_THRESHOLD = 0.6
_STOPWORDS = frozenset(
    "a an the is are what how why do does to of for in on and or can i you your".split()
)
_CHROME_TAGS = ("nav", "header", "footer", "aside", "script", "style", "noscript")
_LIST_NUMBER = re.compile(r"^\s*\d+\s*[.)]\s*")
_NON_WORD = re.compile(r"[^\w\s]")

Outline = list[tuple[int, str]]


def extract_outline(html: str) -> Outline:
    """Return (level, text) for each H2/H3 outside page chrome, in document order."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(list(_CHROME_TAGS)):
        tag.decompose()
    outline: Outline = []
    for heading in soup.find_all(["h2", "h3"]):
        text = " ".join(heading.get_text(" ").split())
        if text:
            outline.append((int(heading.name[1]), text))
    return outline


def normalize_heading(text: str) -> str:
    """Lowercase, drop a leading list number and punctuation, collapse whitespace."""
    without_number = _LIST_NUMBER.sub("", text.lower())
    return " ".join(_NON_WORD.sub(" ", without_number).split())


def _tokens(text: str) -> frozenset[str]:
    return frozenset(normalize_heading(text).split()) - _STOPWORDS


def _topic_counts(outlines: Mapping[str, Outline]) -> tuple[Counter[str], dict[str, Counter[str]]]:
    pages: Counter[str] = Counter()
    displays: dict[str, Counter[str]] = {}
    for outline in outlines.values():
        seen: set[str] = set()
        for _level, text in outline:
            topic = normalize_heading(text)
            if not topic:
                continue
            displays.setdefault(topic, Counter())[text] += 1
            if topic not in seen:
                seen.add(topic)
                pages[topic] += 1
    return pages, displays


def _suggestion(pages: int, fetched: int) -> str | None:
    if pages * 2 >= fetched:
        return "must"
    return "should" if pages >= 2 else None


def _topics(outlines: Mapping[str, Outline]) -> list[dict[str, Any]]:
    fetched = len(outlines)
    pages, displays = _topic_counts(outlines)
    rows = []
    for topic, count in pages.items():
        suggested = _suggestion(count, fetched)
        if suggested is None:
            continue
        heading = displays[topic].most_common(1)[0][0]
        rows.append({"topic": topic, "heading": heading, "pages": count, "suggested": suggested})
    return sorted(rows, key=lambda row: (-row["pages"], row["topic"]))


def _covered(question: str, heading_tokens: Sequence[frozenset[str]]) -> bool:
    wanted = _tokens(question)
    if not wanted:
        return False
    best = max((len(wanted & tokens) / len(wanted) for tokens in heading_tokens), default=0.0)
    return best >= QUESTION_COVERAGE_THRESHOLD


def build_coverage(
    outlines: Mapping[str, Outline],
    paa_questions: Sequence[str],
    *,
    unreachable: Iterable[str] = (),
) -> dict[str, Any]:
    """Count topic coverage across fetched pages; unreachable pages never count."""
    heading_tokens = [
        _tokens(text) for outline in outlines.values() for _level, text in outline
    ]
    return {
        "pages": {
            url: [[level, text] for level, text in outline] for url, outline in outlines.items()
        },
        "unreachable": list(unreachable),
        "topics": _topics(outlines),
        "uncovered_questions": [q for q in paa_questions if not _covered(q, heading_tokens)],
    }


def _request(transport: Any, urls: list[str]) -> list[Any]:
    return transport.request_many(
        "GET",
        urls,
        policy=SOURCE_VISIBLE_TEXT_POLICY,
        headers={"User-Agent": DEFAULT_USER_AGENT},
    )


def _responses(urls: list[str], transport: Any) -> list[Any]:
    """Fetch all URLs at once; if the batch raises, fetch each alone and keep exceptions."""
    try:
        return _request(transport, urls)
    except Exception:
        pass
    results: list[Any] = []
    for url in urls:
        try:
            results.append(_request(transport, [url])[0])
        except Exception as error:
            results.append(error)
    return results


def _outline_of(response: Any) -> Outline | None:
    if isinstance(response, Exception) or response.status_code >= 400:
        return None
    try:
        return extract_outline(response.text)
    except Exception:
        return None


def fetch_outlines(urls: Sequence[str], *, transport: Any) -> tuple[dict[str, Outline], list[str]]:
    """Return outlines of reachable pages and the URLs that could not be fetched."""
    ordered = list(dict.fromkeys(urls))
    outlines: dict[str, Outline] = {}
    unreachable: list[str] = []
    for url, response in zip(ordered, _responses(ordered, transport), strict=True):
        outline = _outline_of(response)
        if outline is None:
            unreachable.append(url)
        else:
            outlines[url] = outline
    return outlines, unreachable


def evidence_urls(evidence: Mapping[str, Any]) -> list[str]:
    """Return up to ten result URLs in position order, skipping empty ones."""
    results = evidence.get("results")
    if not isinstance(results, list):
        raise ValueError("SERP evidence has no results list")
    rows = [
        row for row in results if isinstance(row, dict) and isinstance(row.get("position"), int)
    ]
    rows.sort(key=lambda row: row["position"])
    urls = [str(row.get("url") or "").strip() for row in rows]
    return [url for url in urls if url][:MAX_RESULTS]


def _read_json_object(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"{label} {path} cannot be read as JSON: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} {path} is not a JSON object")
    return value, raw


def _paa_questions(layout: Layout) -> list[str]:
    if not layout.paa_artifact.exists():
        return []
    artifact, _raw = _read_json_object(layout.paa_artifact, "PAA artifact")
    questions = artifact.get("eligible_questions")
    if not isinstance(questions, list) or not all(isinstance(q, str) for q in questions):
        raise ValueError(
            f"PAA artifact {layout.paa_artifact} eligible_questions must be a list of text"
        )
    return questions


def _evidence_binding(layout: Layout, raw: bytes) -> dict[str, str]:
    return {
        "path": layout.serp_evidence.relative_to(layout.root).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="serp_coverage", description=__doc__)
    parser.add_argument("article", type=Path)
    parser.add_argument("--workspace-root", type=Path, default=None)
    return parser


def _build(layout: Layout) -> dict[str, Any]:
    evidence, raw = _read_json_object(layout.serp_evidence, "SERP evidence")
    urls = evidence_urls(evidence)
    if not urls:
        raise ValueError(f"SERP evidence {layout.serp_evidence} lists no result URLs")
    questions = _paa_questions(layout)
    with PublicHttpTransport() as transport:
        outlines, unreachable = fetch_outlines(urls, transport=transport)
    if not outlines:
        raise ValueError(
            "no top-10 page could be fetched; a coverage map with zero pages is not evidence"
        )
    coverage = build_coverage(outlines, questions, unreachable=unreachable)
    return {
        "schema": COVERAGE_SCHEMA,
        "query": evidence.get("query"),
        "serp_evidence": _evidence_binding(layout, raw),
        **coverage,
    }


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exit_request:
        return int(exit_request.code or 0)
    root = (args.workspace_root or Path.cwd()).resolve()
    try:
        layout = Layout.for_article(args.article, root)
        payload = _build(layout)
        atomic_write_json(layout.serp_coverage, payload)
    except (LayoutError, ValueError, OSError) as error:
        print(f"serp_coverage: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
