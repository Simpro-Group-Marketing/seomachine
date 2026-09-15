from copy import deepcopy
from datetime import date
from pathlib import Path

import pytest

from data_sources.modules.blog_strategy_plan_guard import check_content
from data_sources.modules.commercial_pillar_index import load_index
from tests.test_editorial_plan_v2 import final_article, rule_ids, v2_plan


ROOT = Path(__file__).resolve().parents[1]
INDEX = load_index(ROOT / "context" / "commercial-pillar-index.json")


def article() -> str:
    return final_article().replace(
        "title: Field Service Scheduling Guide",
        "title: Field Service Scheduling Guide\nbrand: Simpro\nmarket: US",
        1,
    ).replace(
        "[field service software](/field-service-management-software/)",
        "[field service management software](https://www.simprogroup.com/)",
    )


def findings(plan: dict | None = None, content: str | None = None):
    return check_content(
        content or article(),
        editorial_plan=plan or v2_plan(),
        index=INDEX,
        today=date(2026, 9, 8),
    )


def test_structured_plan_strategy_passes_without_sidecar_strategy_blocks() -> None:
    assert findings() == []


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("commercial_pillar_url", "https://www.simprogroup.com/pricing", "blog_strategy_pillar_url_mismatch"),
        ("planned_anchor_text", "learn more", "blog_strategy_planned_anchor_keyword_missing"),
        ("planned_h2_section", "Another section", "blog_strategy_planned_h2_mismatch"),
        ("status", "blocked", "blog_strategy_pillar_status_blocked"),
    ],
)
def test_structured_plan_enforces_commercial_decisions(
    field: str,
    value: str,
    expected: str,
) -> None:
    plan = deepcopy(v2_plan())
    plan["commercial_strategy"][field] = value

    assert expected in rule_ids(findings(plan))


def test_article_must_contain_exact_canonical_destination_and_anchor() -> None:
    content = article().replace(
        "[field service management software](https://www.simprogroup.com/)",
        "[learn more](https://www.simprogroup.com/?utm_source=blog)",
    )
    ids = rule_ids(findings(content=content))

    assert "blog_strategy_pillar_link_noncanonical" in ids
    assert "blog_strategy_pillar_link_missing" in ids


def test_current_strategy_rejects_archived_v1_plan() -> None:
    plan = v2_plan()
    plan["schema"] = "simpro-blog-editorial-plan/v1"

    assert "blog_strategy_editorial_plan_invalid" in rule_ids(findings(plan))


def test_current_commercial_strategy_is_not_applied_to_non_simpro_blog() -> None:
    non_simpro = article().replace("brand: Simpro", "brand: BigChange").replace(
        "https://www.simprogroup.com/", "https://www.bigchange.com/"
    )

    assert findings(v2_plan(), content=non_simpro) == []
