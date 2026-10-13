"""Tests for the page-1 coverage map built from top-10 outlines."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from data_sources.modules.production import serp_coverage as sc
from data_sources.modules.production.layout import Layout


def test_extract_outline_keeps_order_and_drops_chrome():
    html = (
        "<html><body><nav><h2>Menu</h2></nav><header><h2>Head</h2></header>"
        "<h2> First </h2><h3>Sub</h3><aside><h3>Side</h3></aside><h2></h2>"
        "<h2>Second</h2><footer><h2>Foot</h2></footer>"
        "<script>var x;</script><noscript><h2>NoJs</h2></noscript></body></html>"
    )
    assert sc.extract_outline(html) == [(2, "First"), (3, "Sub"), (2, "Second")]


def test_normalize_heading():
    assert sc.normalize_heading("1. What Is FSM Software?") == "what is fsm software"
    assert sc.normalize_heading("2)  Pricing,   Costs!") == "pricing costs"


def _outlines(pages: dict[str, list[str]]) -> dict[str, list[tuple[int, str]]]:
    return {url: [(2, heading) for heading in headings] for url, headings in pages.items()}


def test_must_when_half_or_more_of_four_pages():
    outlines = _outlines({
        "u1": ["Pricing", "Only One"], "u2": ["Pricing?"], "u3": ["Other"], "u4": ["Other 2"],
    })
    result = sc.build_coverage(outlines, [])
    assert result["topics"] == [
        {"topic": "pricing", "heading": "Pricing", "pages": 2, "suggested": "must"}
    ]


def test_should_when_two_of_five_and_single_page_omitted():
    outlines = _outlines({
        "u1": ["Pricing", "Solo"], "u2": ["Pricing"], "u3": ["x"], "u4": ["y"], "u5": ["z"],
    })
    result = sc.build_coverage(outlines, [])
    assert result["topics"] == [
        {"topic": "pricing", "heading": "Pricing", "pages": 2, "suggested": "should"}
    ]


def test_topics_sorted_and_heading_is_most_common_original():
    outlines = _outlines({
        "u1": ["B topic", "A topic"], "u2": ["b topic", "A Topic"], "u3": ["B Topic", "a topic"],
        "u4": ["B topic"],
    })
    topics = sc.build_coverage(outlines, [])["topics"]
    assert [t["topic"] for t in topics] == ["b topic", "a topic"]
    assert topics[0]["heading"] == "B topic"
    assert topics[0]["pages"] == 4


def test_page_counted_once_per_topic():
    outlines = _outlines({"u1": ["Pricing", "Pricing"], "u2": ["x"], "u3": ["y"]})
    assert sc.build_coverage(outlines, [])["topics"] == []


def test_pages_map_and_unreachable_excluded_from_denominator():
    outlines = _outlines({"u1": ["Pricing"], "u2": ["Pricing"], "u3": ["z"]})
    result = sc.build_coverage(outlines, [], unreachable=["bad1", "bad2"])
    assert result["unreachable"] == ["bad1", "bad2"]
    assert result["pages"]["u1"] == [[2, "Pricing"]]
    assert result["topics"][0]["suggested"] == "must"  # 2 of 3 fetched, not 2 of 5


def test_uncovered_questions():
    outlines = _outlines({"u1": ["Field service software pricing"], "u2": ["Features"]})
    questions = [
        "How much does field service software cost per technician?",
        "What is field service software pricing?",
        "What is it?",
        "",
    ]
    result = sc.build_coverage(outlines, questions)
    assert result["uncovered_questions"] == [
        "How much does field service software cost per technician?",
        "What is it?",
        "",
    ]


class FakeResponse:
    def __init__(self, status_code: int, text: str = ""):
        self.status_code = status_code
        self.text = text


class FakeTransport:
    """request_many raises for the whole batch if any URL is bad."""

    def __init__(self, pages: dict[str, FakeResponse | Exception]):
        self.pages = pages
        self.calls: list[list[str]] = []

    def request_many(self, method, urls, *, policy, headers):
        assert method == "GET"
        assert headers["User-Agent"]
        urls = list(urls)
        self.calls.append(urls)
        out = []
        for url in urls:
            page = self.pages[url]
            if isinstance(page, Exception):
                raise page
            out.append(page)
        return out

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None


def test_fetch_outlines_single_batch_call():
    transport = FakeTransport({
        "a": FakeResponse(200, "<h2>A</h2>"), "b": FakeResponse(200, "<h2>B</h2><h3>C</h3>"),
    })
    outlines, unreachable = sc.fetch_outlines(["a", "b"], transport=transport)
    assert transport.calls == [["a", "b"]]
    assert outlines == {"a": [(2, "A")], "b": [(2, "B"), (3, "C")]}
    assert unreachable == []


def test_fetch_outlines_falls_back_per_url_on_batch_failure():
    transport = FakeTransport({
        "a": FakeResponse(200, "<h2>A</h2>"),
        "bad": RuntimeError("boom"),
        "gone": FakeResponse(404, "<h2>X</h2>"),
    })
    outlines, unreachable = sc.fetch_outlines(["a", "bad", "gone"], transport=transport)
    assert transport.calls[0] == ["a", "bad", "gone"]
    assert transport.calls[1:] == [["a"], ["bad"], ["gone"]]
    assert outlines == {"a": [(2, "A")]}
    assert unreachable == ["bad", "gone"]


def test_fetch_outlines_status_error_in_batch_is_unreachable():
    transport = FakeTransport({"a": FakeResponse(200, "<h2>A</h2>"), "b": FakeResponse(500)})
    outlines, unreachable = sc.fetch_outlines(["a", "b"], transport=transport)
    assert list(outlines) == ["a"]
    assert unreachable == ["b"]


def test_evidence_urls_in_position_order_capped_and_skipping_empty():
    results = [{"position": 12 - i, "url": f"u{i}"} for i in range(12)]
    results.append({"position": 99, "url": ""})
    urls = sc.evidence_urls({"results": results})
    assert len(urls) == 10
    assert urls[0] == "u11"


def _workspace(tmp_path: Path, *, with_evidence: bool = True, paa: list[str] | None = None) -> Layout:
    (tmp_path / "drafts").mkdir()
    article = tmp_path / "drafts" / "fsm-software-2026-10-13.md"
    article.write_text("# x\n", encoding="utf-8")
    layout = Layout.for_article(article, tmp_path)
    layout.serp_evidence.parent.mkdir(parents=True, exist_ok=True)
    if with_evidence:
        layout.serp_evidence.write_text(json.dumps({
            "schema": "simpro-serp-evidence/v1",
            "query": "fsm software",
            "results": [
                {"position": 2, "url": "https://b.example/", "title": "b", "result_type": "organic"},
                {"position": 1, "url": "https://a.example/", "title": "a", "result_type": "organic"},
            ],
        }), encoding="utf-8")
    if paa is not None:
        layout.paa_artifact.write_text(json.dumps({"eligible_questions": paa}), encoding="utf-8")
    return layout


def _patch_transport(monkeypatch, transport):
    monkeypatch.setattr(sc, "PublicHttpTransport", lambda *a, **k: transport)


def test_cli_writes_coverage(tmp_path, monkeypatch):
    layout = _workspace(tmp_path, paa=["What is fsm software?"])
    transport = FakeTransport({
        "https://a.example/": FakeResponse(200, "<h2>What is FSM software</h2>"),
        "https://b.example/": FakeResponse(200, "<h2>1. What is FSM software?</h2>"),
    })
    _patch_transport(monkeypatch, transport)
    assert sc.main([str(layout.article), "--workspace-root", str(tmp_path)]) == 0
    assert transport.calls == [["https://a.example/", "https://b.example/"]]
    payload = json.loads(layout.serp_coverage.read_text(encoding="utf-8"))
    assert payload["schema"] == "simpro-serp-coverage/v1"
    assert payload["query"] == "fsm software"
    assert payload["serp_evidence"] == {
        "path": "research/serp-evidence-fsm-software-2026-10-13.json",
        "sha256": hashlib.sha256(layout.serp_evidence.read_bytes()).hexdigest(),
    }
    assert payload["topics"][0]["suggested"] == "must"
    assert payload["uncovered_questions"] == []
    assert payload["unreachable"] == []


def test_cli_without_paa_artifact_has_no_questions(tmp_path, monkeypatch):
    layout = _workspace(tmp_path)
    _patch_transport(monkeypatch, FakeTransport({
        "https://a.example/": FakeResponse(200, "<h2>A</h2>"),
        "https://b.example/": FakeResponse(200, "<h2>A</h2>"),
    }))
    assert sc.main([str(layout.article), "--workspace-root", str(tmp_path)]) == 0
    assert json.loads(layout.serp_coverage.read_text(encoding="utf-8"))["uncovered_questions"] == []


def test_cli_missing_evidence_exits_2(tmp_path, monkeypatch):
    layout = _workspace(tmp_path, with_evidence=False)
    _patch_transport(monkeypatch, FakeTransport({}))
    assert sc.main([str(layout.article), "--workspace-root", str(tmp_path)]) == 2
    assert not layout.serp_coverage.exists()


def test_cli_invalid_evidence_exits_2(tmp_path, monkeypatch):
    layout = _workspace(tmp_path)
    layout.serp_evidence.write_text("[1]", encoding="utf-8")
    _patch_transport(monkeypatch, FakeTransport({}))
    assert sc.main([str(layout.article), "--workspace-root", str(tmp_path)]) == 2


def test_cli_layout_error_exits_2(tmp_path):
    assert sc.main([str(tmp_path / "nope.md"), "--workspace-root", str(tmp_path)]) == 2


def test_cli_no_fetchable_page_exits_2(tmp_path, monkeypatch):
    layout = _workspace(tmp_path)
    _patch_transport(monkeypatch, FakeTransport({
        "https://a.example/": FakeResponse(404), "https://b.example/": FakeResponse(500),
    }))
    assert sc.main([str(layout.article), "--workspace-root", str(tmp_path)]) == 2
    assert not layout.serp_coverage.exists()


@pytest.mark.parametrize("paa_body", ["not json", '{"eligible_questions": "x"}'])
def test_cli_bad_paa_artifact_exits_2(tmp_path, monkeypatch, paa_body):
    layout = _workspace(tmp_path)
    layout.paa_artifact.write_text(paa_body, encoding="utf-8")
    _patch_transport(monkeypatch, FakeTransport({}))
    assert sc.main([str(layout.article), "--workspace-root", str(tmp_path)]) == 2
