"""End to end: a blog reaches a passing release record from judgment files alone.

The judgment files are a BOM spec, the article, a saved Semrush transcript and decision, and saved
research captures. The real CLIs run in order (keyword_record, serp_coverage, bom_build, release);
only the network and the clock are faked. Truth, coverage, and scoring are never stubbed.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import pytest
from data_sources.modules import simpro_vault_client, vault_claim_receipts
from data_sources.modules.production import bom_build, keyword_record, release, selector_refresh, serp_coverage
from data_sources.modules.production.layout import Layout
from data_sources.modules.production.record import verify_publishable
from data_sources.modules.public_http import PublicHttpTransport
from tests.production_acceptance_support import (
    DECISION_PATH,
    FACT_ID,
    OFF_BOM_SENTENCE,
    TRANSCRIPT_PATH,
    FakeWeb,
    write_judgment_files,
)
from tests.production_scoring_support import ARTICLE, OWNED_URL, TODAY

LEDGER = Path("config") / "customer-proof-usage-ledger.json"
REAL_LEDGER = Path(__file__).resolve().parents[1] / LEDGER


class FixedDate(date):
    @classmethod
    def today(cls):
        return cls.fromisoformat(TODAY)


class Pipeline:
    """The four CLIs run in process against one tmp workspace and one fake web."""

    def __init__(self, layout: Layout, web: FakeWeb, vault_calls: list[str]):
        self.layout, self.web, self.vault_calls = layout, web, vault_calls

    @property
    def root(self) -> Path:
        return self.layout.root

    def run_inputs(self) -> None:
        where = ["--workspace-root", str(self.root)]
        assert keyword_record.main([
            "--decision", str(self.root / DECISION_PATH), "--transcript", str(self.root / TRANSCRIPT_PATH),
            "--output", str(self.layout.keyword_decision), "--shortlist-output", str(self.layout.keyword_shortlist),
            *where,
        ]) == 0
        assert serp_coverage.main([ARTICLE, *where]) == 0
        assert bom_build.main([ARTICLE, *where]) == 0

    def release(self) -> int:
        return release.main([ARTICLE, "--workspace-root", str(self.root), "--workers", "1"])

    def records(self) -> list[dict]:
        folders = sorted((self.root / "research" / "releases").iterdir(), key=lambda path: int(path.name.rsplit("-", 1)[1]))
        return [json.loads((folder / "release-record.json").read_text(encoding="utf-8")) for folder in folders]

    def verify(self) -> dict:
        return verify_publishable(self.layout.article, self.root)


@pytest.fixture(autouse=True)
def _clock(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)
    monkeypatch.setattr(selector_refresh, "date", FixedDate)


@pytest.fixture
def vault_calls(monkeypatch) -> list[str]:
    """Any vault client or claim loader call raises and is recorded; the nonconnector path needs none."""
    calls: list[str] = []

    def refuse(name):
        def call(*_args, **_kwargs):
            calls.append(name)
            raise AssertionError(f"vault must not be called: {name}")

        return call

    monkeypatch.setattr(simpro_vault_client.SimproVaultClient, "__init__", refuse("SimproVaultClient"))
    for module in (vault_claim_receipts, bom_build, release):
        monkeypatch.setattr(module, "load_validated_claim_set", refuse(f"{module.__name__}.load_validated_claim_set"))
    return calls


@pytest.fixture
def pipeline(tmp_path, monkeypatch, vault_calls) -> Pipeline:
    web = FakeWeb()
    monkeypatch.setattr(PublicHttpTransport, "request_many", lambda _s, _m, urls, **_k: [web._one(url) for url in urls])
    monkeypatch.setattr(PublicHttpTransport, "request", lambda _s, _m, url, **_k: web._one(url))
    return Pipeline(write_judgment_files(tmp_path), web, vault_calls)


@pytest.fixture
def released(pipeline) -> Pipeline:
    pipeline.run_inputs()
    assert pipeline.release() == 0, pipeline.records()
    return pipeline


def _sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _blocks(record: dict) -> list[dict]:
    return [row for row in record["findings"] if row["severity"] == "block"]


def test_judgment_files_alone_reach_a_passing_release_record(pipeline):
    real_ledger_before = _sha(REAL_LEDGER)
    pipeline.run_inputs()
    ledger_before = _sha(pipeline.root / LEDGER)

    assert pipeline.release() == 0
    (record,) = pipeline.records()
    scores = record["scores"]
    assert record["passed"] is True and record["blocks"] == 0
    assert scores["content"] >= 85 and scores["seo"] >= 90 and scores["seo_critical"] == 0 and scores["aeo_geo"] >= 90
    assert record["article"]["sha256"] == _sha(pipeline.layout.article)
    pipeline.verify()
    assert pipeline.vault_calls == []
    assert _sha(pipeline.root / LEDGER) == ledger_before and _sha(REAL_LEDGER) == real_ledger_before


def test_editing_the_released_article_makes_it_unpublishable(released):
    article = released.layout.article
    article.write_text(article.read_text(encoding="utf-8") + "\nOne more line.\n", encoding="utf-8", newline="\n")
    with pytest.raises(ValueError):
        released.verify()


def test_off_bom_citation_with_a_number_blocks_the_release(released):
    article = released.layout.article
    original = article.read_text(encoding="utf-8")
    article.write_text(original + OFF_BOM_SENTENCE, encoding="utf-8", newline="\n")
    assert released.release() == 1

    first, newest = released.records()
    assert first["passed"] is True and newest["passed"] is False
    blocks = _blocks(newest)
    assert {row["check"] for row in blocks} >= {"claim_numbers"}, blocks
    assert any("73" in row["message"] for row in blocks), blocks
    with pytest.raises(ValueError):
        released.verify()

    article.write_text(original, encoding="utf-8", newline="\n")
    assert released.release() == 0
    assert released.records()[-1]["passed"] is True
    released.verify()


def test_fact_page_that_lost_its_quote_refuses_naming_the_fact(released, capsys):
    released.web.replies[OWNED_URL] = (200, "<html><body><p>This page was rewritten.</p></body></html>")
    assert released.release() == 1
    newest = released.records()[-1]
    messages = " ".join(row["message"] for row in _blocks(newest))
    assert newest["passed"] is False and FACT_ID in messages and OWNED_URL in messages
    assert FACT_ID in capsys.readouterr().err
    with pytest.raises(ValueError):
        released.verify()


def test_unreachable_fact_page_carries_the_original_verification_with_a_warning(released):
    (original,) = json.loads(released.layout.bom.read_text(encoding="utf-8"))["facts"]
    released.web.replies[OWNED_URL] = (403, "")
    assert released.release() == 0
    newest = released.records()[-1]
    warnings = [row["message"] for row in newest["findings"] if row["severity"] == "warn"]
    assert newest["passed"] is True and newest["warns"] >= 1
    assert any(FACT_ID in text and original["verified_at"] in text for text in warnings), warnings
    released.verify()
