"""Shared helpers for the release command tests: a workspace, check stand-ins, and transports."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.production import bom_build, release
from data_sources.modules.production.layout import Layout
from data_sources.modules.production.scoring import score_gates
from data_sources.modules.production.truth_text import Finding
from tests.production_bom_support import (
    ARTICLE,
    FACT_PAGE,
    FACT_URL,
    good_transport,
    make_workspace,
    nonconnector_spec,
    response,
)
from tests.production_scoring_support import scorer_result

ARTICLE_TEXT = "# Crew Time Tracking Guide\n\nCrews log time from any phone.\n"
LINKED_ARTICLE_TEXT = (
    "# Crew Time Tracking Guide\n\n"
    f"More than 24,000 trade businesses worldwide use [field service tools]({FACT_URL}) to run jobs.\n"
)


def workspace(root: Path, *, text: str = ARTICLE_TEXT) -> Layout:
    """A nonconnector workspace with an article and a BOM built from its spec."""
    layout = make_workspace(root, spec=nonconnector_spec())
    layout.article.parent.mkdir(parents=True, exist_ok=True)
    layout.article.write_text(text, encoding="utf-8", newline="\n")
    atomic_write_json(layout.bom, bom_build.build_bom(layout, transport=good_transport()))
    return layout


class PageTransport:
    """Answers each URL from (status, body) or an exception, with a fresh response per request."""

    def __init__(self, replies: dict[str, Any] | None = None):
        self.replies = replies if replies is not None else {FACT_URL: (200, FACT_PAGE)}

    def _one(self, url: str):
        reply = self.replies[url]
        if isinstance(reply, Exception):
            raise reply
        status, body = reply
        return response(url, status, body)

    def request_many(self, method, urls, **kwargs):
        return [self._one(url) for url in urls]

    def request(self, method, url, **kwargs):
        return self._one(url)


class Checks:
    """Stand-ins for truth, coverage, and scoring that record how they were called."""

    def __init__(self, monkeypatch, *, real_truth: bool = False):
        self.calls: list[tuple] = []
        self.truth_findings: list[Finding] = []
        self.coverage_findings: list[Finding] = []
        self.scores = score_gates(scorer_result())
        self.on_score = None
        self.on_truth = None
        if not real_truth:
            monkeypatch.setattr(release, "check_truth", self.truth)
        monkeypatch.setattr(release, "check_coverage", self.coverage)
        monkeypatch.setattr(release, "score_article", self.score)

    def truth(self, article, bom, *, transport):
        self.calls.append(("truth", transport))
        if self.on_truth:
            self.on_truth()
        return list(self.truth_findings)

    def coverage(self, article, bom):
        self.calls.append(("coverage",))
        return list(self.coverage_findings)

    def score(self, article_path, bom, *, workers):
        self.calls.append(("score", workers))
        if self.on_score:
            self.on_score(article_path)
        return copy.deepcopy(self.scores)


def noop_refresher(*_args: Any) -> None:
    return None


def run(layout: Layout, *, workers: int = 2, refresher: Any = noop_refresher, transport: Any = None) -> int:
    return release.run_release(
        ARTICLE, layout.root, workers=workers, transport=transport or good_transport(), refresher=refresher,
    )


def release_dirs(layout: Layout) -> list[Path]:
    folder = layout.root / "research" / "releases"
    return sorted(folder.iterdir()) if folder.is_dir() else []
