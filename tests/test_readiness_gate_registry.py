import json
from pathlib import Path
from types import SimpleNamespace

from data_sources.modules import blog_strategy_plan_guard, schema_handoff_guard
from data_sources.modules.blog_gate_inventory import BLOG_GATE_DESCRIPTORS
from data_sources.modules.readiness.common import ARTICLE_GATES
from data_sources.modules.readiness.gate_registry import (
    NON_ARTICLE_EXECUTORS,
    SPECIAL_ARTICLE_EXECUTORS,
    assert_gate_executor_invariant,
)
from data_sources.modules.readiness.gates import (
    CONTENT_GATE_NAMES,
    ContentGateInputs,
    run_content_gate,
)
from tests.test_blog_strategy_plan_guard import article
from tests.test_editorial_plan_v2 import v2_plan


ROOT = Path(__file__).resolve().parents[1]


class CapturedInputs:
    def __init__(self, root: Path, values: dict[str, object]) -> None:
        self.workspace_root = root
        self.values = values

    def optional_snapshot(self, label: str):
        return SimpleNamespace() if label in self.values else None

    def json_object(self, label: str):
        return self.values[label]


def test_every_declared_readiness_gate_has_an_executor() -> None:
    article_names = {name for name, _, _ in ARTICLE_GATES}
    declared = {descriptor.name for descriptor in BLOG_GATE_DESCRIPTORS}

    assert_gate_executor_invariant(article_names, CONTENT_GATE_NAMES)
    assert declared == NON_ARTICLE_EXECUTORS | article_names
    assert article_names - SPECIAL_ARTICLE_EXECUTORS <= CONTENT_GATE_NAMES
    assert {"blog_strategy", "schema_handoff"} <= article_names


def test_current_inventory_includes_strategy_and_schema_gates() -> None:
    from data_sources.modules.blog_gate_inventory import expected_blog_gate_inventory

    archived = expected_blog_gate_inventory(visible_faq=False, connector_required=False)
    current = expected_blog_gate_inventory(
        visible_faq=False,
        connector_required=False,
        current_strategy=True,
    )

    assert "blog_strategy" not in archived
    assert "schema_handoff" not in archived
    assert "blog_strategy" in current
    assert "schema_handoff" in current


def test_current_strategy_and_schema_adapters_record_passing_execution(
    tmp_path: Path,
) -> None:
    plan = v2_plan()
    for field in ("serp_evidence_artifact", "related_query_paa_artifact"):
        evidence = tmp_path / plan["search_strategy"][field]
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text("verified evidence\n", encoding="utf-8")
    index = json.loads(
        (ROOT / "context" / "commercial-pillar-index.json").read_text(encoding="utf-8")
    )
    captured = CapturedInputs(
        tmp_path,
        {"editorial_plan": plan, "commercial_pillar_index": index},
    )
    content = article().replace(
        "last_updated: 2026-08-05\n---",
        "last_updated: 2026-08-05\n"
        "schema_notes:\n"
        "  - BlogPosting\n"
        "  - BreadcrumbList\n"
        "  - ImageObject for the featured image or logo\n"
        "  - Organization as publisher reference only, not a separate full schema block\n"
        "---",
    )
    inputs = ContentGateInputs(
        article_content=content,
        proof_content="",
        article_path=tmp_path / "drafts" / "article.md",
        proof_sidecar_path=None,
        context_pack_path=None,
        context_receipt_path=None,
        vault_root=None,
        runtime_policy={
            "assembly_date": "2026-09-08",
            "commercial_pillar_index": "context/commercial-pillar-index.json",
        },
        captured=captured,
        validated_claim_set=None,
        transport=None,
    )

    assert run_content_gate("blog_strategy", blog_strategy_plan_guard, inputs) == []
    assert run_content_gate("schema_handoff", schema_handoff_guard, inputs) == []
