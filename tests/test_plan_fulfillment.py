from copy import deepcopy
import hashlib

import pytest

from data_sources.modules.editorial_plan.plan_fulfillment import check_fulfillment
from tests.test_editorial_plan_v2 import final_article, rule_ids, v2_plan


EXCERPT = "Use a field service scheduling sequence to make each dispatch workflow explicit."


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def fulfillment(plan_hash: str, article: str) -> dict:
    return {
        "schema": "simpro-blog-plan-fulfillment/v1",
        "editorial_plan_sha256": plan_hash,
        "article_sha256": digest(article),
        "contributions": [
            {
                "contribution_id": "constraint-first-checklist",
                "actual_excerpt": EXCERPT,
            }
        ],
    }


def findings(payload: dict, *, article: str | None = None, plan: dict | None = None):
    current_plan = plan or v2_plan()
    current_article = article or final_article()
    return check_fulfillment(
        payload,
        editorial_plan=current_plan,
        editorial_plan_sha256="a" * 64,
        article_content=current_article,
    )


def test_valid_freely_worded_excerpt_fulfills_planned_contribution() -> None:
    article = final_article()
    assert findings(fulfillment("a" * 64, article), article=article) == []


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (
            lambda payload: payload.update({"editorial_plan_sha256": "b" * 64}),
            "plan_fulfillment_plan_hash_mismatch",
        ),
        (
            lambda payload: payload.update({"article_sha256": "b" * 64}),
            "plan_fulfillment_article_hash_mismatch",
        ),
        (
            lambda payload: payload.update({"contributions": []}),
            "plan_fulfillment_contribution_missing",
        ),
        (
            lambda payload: payload["contributions"].append(
                dict(payload["contributions"][0])
            ),
            "plan_fulfillment_contribution_duplicate",
        ),
        (
            lambda payload: payload["contributions"].append(
                {"contribution_id": "extra", "actual_excerpt": "An extra visible contribution excerpt."}
            ),
            "plan_fulfillment_contribution_extra",
        ),
        (
            lambda payload: payload["contributions"][0].update({"actual_excerpt": "too short"}),
            "plan_fulfillment_excerpt_not_substantive",
        ),
    ],
)
def test_fulfillment_rejects_invalid_bindings(mutate, expected: str) -> None:
    article = final_article()
    payload = fulfillment("a" * 64, article)
    mutate(payload)
    assert expected in rule_ids(findings(payload, article=article))


def test_fulfillment_rejects_hidden_excerpt() -> None:
    article = final_article().replace(
        EXCERPT,
        "The visible section uses different language.",
    ).replace(
        "## Scheduling constraints",
        f"<!-- {EXCERPT} -->\n\n## Scheduling constraints",
    )
    payload = fulfillment("a" * 64, article)
    payload["article_sha256"] = digest(article)

    assert "plan_fulfillment_excerpt_not_visible" in rule_ids(
        findings(payload, article=article)
    )


def test_fulfillment_rejects_excerpt_in_wrong_section() -> None:
    article = final_article().replace(EXCERPT, "The planned section uses different language.")
    article += f"\n## Unplanned appendix\n\n{EXCERPT}\n"
    payload = fulfillment("a" * 64, article)
    payload["article_sha256"] = digest(article)

    assert "plan_fulfillment_excerpt_wrong_section" in rule_ids(
        findings(payload, article=article)
    )


def test_fulfillment_requires_v2_plan() -> None:
    plan = deepcopy(v2_plan())
    plan["schema"] = "simpro-blog-editorial-plan/v1"
    payload = fulfillment("a" * 64, final_article())

    assert "plan_fulfillment_editorial_plan_schema_invalid" in rule_ids(
        findings(payload, plan=plan)
    )
