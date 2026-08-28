from __future__ import annotations

import hashlib
import json
from pathlib import Path

from data_sources.modules import editorial_plan_guard, industry_cluster_link_policy
from data_sources.modules.seo_quality_rater import SEOQualityRater
from tests.test_editorial_plan_guard import article_plan


INDUSTRY_URL = "https://www.simprogroup.com/industries/plumbing-software"
TRAINING_URL = "https://www.simprogroup.com/blog/informational-resources-for-plumbing-contractors"
GROW_URL = "https://www.simprogroup.com/blog/how-to-grow-plumbing-business"
RESOURCE_ID = "res-6a89de98838b57a3821bfaeb59403191"
DEFAULT_SENTENCE = (
    "Use exactly two contextual internal body links before the FAQ: "
    "plumbing training and licensing resources and grow a plumbing business."
)


def _rules(findings) -> set[str]:
    return {finding["rule_id"] for finding in findings}


def _fixture(
    tmp_path: Path,
    *,
    include_industry_link: bool = True,
    include_industry_plan: bool = True,
    extra_link: bool = False,
    duplicate_link: bool = False,
) -> tuple[Path, Path, Path, dict]:
    brief = tmp_path / "research" / "brief.md"
    plan_path = tmp_path / "research" / "plan.json"
    article = tmp_path / "rewrites" / "texas.md"
    brief.parent.mkdir(parents=True, exist_ok=True)
    article.parent.mkdir(parents=True, exist_ok=True)
    brief.write_text(f"# Brief\n\n{DEFAULT_SENTENCE}\n", encoding="utf-8")
    body = (
        f"Texas plumbing license requirements start with registration. Use these [plumbing training and licensing resources]({TRAINING_URL}) "
        f"and learn how to [grow a plumbing business]({GROW_URL})."
    )
    if include_industry_link:
        body += f" The commercial next step is [plumbing contractor software]({INDUSTRY_URL})."
    if extra_link:
        body += " See [plumbing margin guide](https://www.simprogroup.com/blog/plumbing-business-profit-margin-guide)."
    if duplicate_link:
        body += f" Review [plumbing training and licensing resources]({TRAINING_URL}) again."
    article.write_text(
        "---\nartifact_type: blog\nbrand: Simpro\ntitle: Texas plumbing license\n"
        "objective: Explain Texas plumbing license requirements.\naudience: Texas plumbing apprentices and contractors\n"
        "region: US\nlast_updated: 2026-08-26\n---\n# Texas plumbing license\n\n"
        f"{body}\n\n[TSBPE](https://tsbpe.texas.gov/license-types/) explains license types.\n",
        encoding="utf-8",
    )
    plan = article_plan()
    plan.update({"brand": "Simpro", "topic": "Texas plumbing license", "date": "2026-08-26"})
    plan["meta"].update({"meta_title": "Texas Plumbing License | Simpro", "primary_keyword": "Texas plumbing license"})
    plan["keyword_decision"]["selected_primary_keyword"] = "Texas plumbing license"
    plan["reader_contract"].update({"primary_reader": "Texas plumbing apprentices and contractors", "decision_task_helped": "Understand Texas plumbing license requirements."})
    plan["sections"][0].update({"heading": "Texas plumbing license", "strategic_angle": "Explain the license path clearly."})
    plan["original_contributions"][0] = {"description": "Texas licensing pathway summary", "final_section": "Texas plumbing license", "visible_evidence": "Texas plumbing license requirements start with registration."}
    plan["entity_map"] = {"primary": ["Texas plumbing license"], "supporting": ["registration"]}
    plan["internal_link_plan"] = [
        {"target": TRAINING_URL, "role": "supporting", "rationale": "Brief-selected licensing resource."},
        {"target": GROW_URL, "role": "supporting", "rationale": "Brief-selected business growth resource."},
    ]
    if include_industry_plan:
        plan["internal_link_plan"].append({"target": INDUSTRY_URL, "role": "down_funnel", "rationale": "Required plumbing industry cluster link for a single-trade Simpro article."})
        plan["industry_cluster_link_policy"] = {"status": "required", "industry": "plumbing", "target": INDUSTRY_URL, "anchor": "plumbing contractor software", "placement": "intro_first_300_words", "vault_vertical_query": "plumbing contractor software industry page vertical profile Simpro industries plumbing-software", "required_resource_ids": [RESOURCE_ID], "rationale": "Single-trade Simpro plumbing articles must reinforce the plumbing industry page."}
    plan["link_policy_override"] = {"brief_path": brief.as_posix(), "brief_sha256": hashlib.sha256(brief.read_bytes()).hexdigest(), "source_sentence": DEFAULT_SENTENCE, "exact_count": 2, "scope": "pre_faq_body"}
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    return brief, plan_path, article, plan


def test_valid_exact_link_override_allows_additive_industry_link(tmp_path: Path):
    _, plan_path, article, plan = _fixture(tmp_path)
    rules = _rules(editorial_plan_guard.check_file(plan_path, article_path=article, assembly_date="2026-08-26"))
    assert "editorial_plan_link_policy_override_count_mismatch" not in rules
    assert "editorial_plan_link_policy_override_target_set_mismatch" not in rules
    assert industry_cluster_link_policy.editorial_plan_findings(plan, brand="simpro") == []
    assert editorial_plan_guard.internal_link_guidelines_from_plan(plan) == {"min_internal_links": 3, "optimal_internal_links": 3, "max_internal_links": 3, "require_down_funnel_link": True}
    result = SEOQualityRater(editorial_plan_guard.internal_link_guidelines_from_plan(plan))._score_links(article.read_text(encoding="utf-8"), internal_count=3, external_count=5, brand="simpro")
    assert not any("internal links" in item for item in result["critical"] + result["warnings"] + result["suggestions"])


def test_exact_link_override_blocks_missing_single_trade_industry_link(tmp_path: Path):
    _, plan_path, article, _ = _fixture(tmp_path, include_industry_link=False)
    rules = _rules(editorial_plan_guard.check_file(plan_path, article_path=article, assembly_date="2026-08-26"))
    assert {"editorial_plan_link_policy_override_count_mismatch", "editorial_plan_link_policy_override_target_set_mismatch"} <= rules
    assert "industry_cluster_link_missing" in _rules(industry_cluster_link_policy.check_file(article, editorial_plan=plan_path))


def test_exact_link_override_blocks_surplus_or_duplicate_internal_targets(tmp_path: Path):
    _, surplus_plan, surplus_article, _ = _fixture(tmp_path / "surplus", extra_link=True)
    _, duplicate_plan, duplicate_article, _ = _fixture(tmp_path / "duplicate", duplicate_link=True)
    assert {"editorial_plan_link_policy_override_count_mismatch", "editorial_plan_link_policy_override_target_set_mismatch"} <= _rules(editorial_plan_guard.check_file(surplus_plan, article_path=surplus_article, assembly_date="2026-08-26"))
    assert "editorial_plan_link_policy_override_duplicate_target" in _rules(editorial_plan_guard.check_file(duplicate_plan, article_path=duplicate_article, assembly_date="2026-08-26"))


def test_brief_sentence_variants_do_not_suppress_industry_link(tmp_path: Path):
    for index, sentence in enumerate((
        "Add 1-2 internal links to another blog post that is relevant.",
        "Use only these two brief-requested internal links:",
        'Include exactly two contextual internal links before the FAQ: "plumbing training and licensing resources" and "grow a plumbing business", using only their selected Simpro destinations.',
    )):
        brief, plan_path, article, plan = _fixture(tmp_path / str(index))
        brief.write_text(f"# Brief\n\n{sentence}\n", encoding="utf-8")
        plan["link_policy_override"].update({"brief_sha256": hashlib.sha256(brief.read_bytes()).hexdigest(), "source_sentence": sentence, "exact_count": 2})
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        assert not industry_cluster_link_policy.link_policy_override_prohibits_industry_link(plan)
        assert editorial_plan_guard.check_file(plan_path, article_path=article, assembly_date="2026-08-26") == []
        assert industry_cluster_link_policy.editorial_plan_findings(plan, brand="simpro") == []


def test_override_count_must_be_supported_by_sentence_and_not_exceed_seven(tmp_path: Path):
    _, plan_path, article, plan = _fixture(tmp_path)
    for invalid_count in (3, 8):
        plan["link_policy_override"]["exact_count"] = invalid_count
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        assert "editorial_plan_field_invalid" in _rules(editorial_plan_guard.check_file(plan_path, article_path=article, assembly_date="2026-08-26"))


def test_forged_override_does_not_suppress_industry_policy(tmp_path: Path):
    _, _, _, plan = _fixture(tmp_path, include_industry_plan=False)
    plan["link_policy_override"]["brief_sha256"] = "0" * 64
    assert "editorial_plan_industry_cluster_link_missing" in _rules(industry_cluster_link_policy.editorial_plan_findings(plan, brand="simpro"))
