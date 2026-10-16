from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sources.modules.readiness.common import ARTICLE_GATES
from data_sources.modules.readiness.gate_registry import (
    ARTICLE_GATE_INVENTORY,
    CONNECTOR_GATE_NAMES,
    assert_landing_gate_invariant,
    expected_landing_gate_inventory,
)
from data_sources.modules.readiness.gates import (
    CONTENT_GATE_NAMES,
    ContentGateInputs,
)


class CapturedInputs:
    def __init__(self, root: Path, values: dict[str, object]) -> None:
        self.workspace_root = root
        self.values = values

    def optional_snapshot(self, label: str):
        return SimpleNamespace() if label in self.values else None

    def json_object(self, label: str):
        return self.values[label]


def test_every_landing_gate_has_a_content_adapter_in_inventory_order() -> None:
    article_names = [name for name, _, _ in ARTICLE_GATES]

    assert_landing_gate_invariant(article_names, CONTENT_GATE_NAMES)
    assert article_names == [name for name, _ in ARTICLE_GATE_INVENTORY]
    assert set(article_names) == CONTENT_GATE_NAMES


def test_connector_gates_extend_the_inventory_only_when_context_is_required() -> None:
    without = expected_landing_gate_inventory(connector_required=False)
    with_connector = expected_landing_gate_inventory(connector_required=True)

    assert CONNECTOR_GATE_NAMES == {"vault_brand_language", "named_feature_status", "fred_authority"}
    assert not CONNECTOR_GATE_NAMES & set(without)
    assert [name for name in with_connector if name not in without] == [
        "vault_brand_language", "named_feature_status", "fred_authority",
    ]
    assert without[-1] == with_connector[-1] == "landing_page_scorer"


@pytest.mark.parametrize(
    "articles,adapters",
    [
        (["context_boundary"], CONTENT_GATE_NAMES),
        ([name for name, _ in reversed(ARTICLE_GATE_INVENTORY)], CONTENT_GATE_NAMES),
        ([name for name, _ in ARTICLE_GATE_INVENTORY], CONTENT_GATE_NAMES | {"blog_strategy"}),
    ],
    ids=["missing-gate", "reordered", "orphan-adapter"],
)
def test_gate_registry_drift_fails_at_import_time(articles, adapters) -> None:
    with pytest.raises(RuntimeError, match="readiness gate registry drift"):
        assert_landing_gate_invariant(articles, adapters)


def _metric_inputs(tmp_path: Path, transport: object | None) -> ContentGateInputs:
    return ContentGateInputs(
        article_content="# Article\n",
        proof_content="proof",
        article_path=tmp_path / "drafts" / "article.md",
        proof_sidecar_path=None,
        context_pack_path=None,
        context_receipt_path=None,
        vault_root=None,
        captured=CapturedInputs(tmp_path, {}),
        validated_claim_set=None,
        transport=transport,
    )


class _RecordingMetricModule:
    def __init__(self) -> None:
        self.fetcher = "unset"
        self.fetch_transport = "unset"

    def check_content(self, content, source_path=None, fetcher=None, proof_content=None):
        self.fetcher = fetcher
        return []

    def fetch_source_text(self, url, *, transport=None):
        self.fetch_transport = transport
        return "text"


def test_metric_gate_routes_fetches_through_the_run_transport(tmp_path: Path) -> None:
    from data_sources.modules.readiness import gates

    transport = object()
    module = _RecordingMetricModule()

    assert gates._metric(module, _metric_inputs(tmp_path, transport)) == []

    assert callable(module.fetcher)
    assert module.fetcher("https://example.com/x") == "text"
    assert module.fetch_transport is transport


def test_metric_gate_leaves_fetcher_unset_without_a_transport(tmp_path: Path) -> None:
    from data_sources.modules.readiness import gates

    module = _RecordingMetricModule()

    assert gates._metric(module, _metric_inputs(tmp_path, None)) == []

    assert module.fetcher is None
