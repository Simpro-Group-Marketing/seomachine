from __future__ import annotations

import json
from pathlib import Path

from scripts import research_competitor_gaps


def _config(tmp_path: Path, payload: dict) -> None:
    (tmp_path / "config").mkdir(); (tmp_path / "config" / "competitors.json").write_text(json.dumps(payload), encoding="utf-8")


def test_competitor_gaps_root_config_terms_cache_and_zero_difficulty(tmp_path: Path, monkeypatch):
    _config(tmp_path, {"direct_competitors": ["example.com"], "content_competitors": ["blog.example.com"], "relevant_terms": ["plumbing"]})
    monkeypatch.setattr(research_competitor_gaps, "REPO_ROOT", tmp_path)
    research_competitor_gaps.load_relevant_terms.cache_clear()
    assert research_competitor_gaps.load_competitors() == (["example.com"], ["blog.example.com"])
    assert research_competitor_gaps.is_relevant_keyword("plumbing license") is True
    assert research_competitor_gaps.is_relevant_keyword("accounting software") is False
    assert research_competitor_gaps.display_metric(0) == "0"
    assert research_competitor_gaps.display_metric(None) == "Unknown"
